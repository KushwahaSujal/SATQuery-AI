"""
SatQuery AI — VideoAnalysisWorkflow
Executes end-to-end video footage analysis:
VideoDecoder -> VideoSampler -> Task Routing -> Grounding DINO -> V4 Reasoning ->
SAM 2.1 Video Propagation -> VideoFlagger -> PostgreSQL persistence -> VideoAnalysisResponse.
"""
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
import time
import shutil
import numpy as np
from PIL import Image

from backend.app.schemas.video import (
    VideoMetadata,
    VideoSamplingConfig,
    VideoFlagConfig,
    VideoFlag,
    VideoAnalysisResponse,
)
from backend.app.schemas.agent import JobStatus, TaskType, ExecutionStep
from backend.app.video.decoder import VideoDecoder
from backend.app.video.sampler import VideoSampler
from backend.app.video.flagger import VideoFlagger, FrameDetection
from backend.app.workflows.grounding_reasoner import parse_v4_query, run_v4_reasoning, color_score
from backend.app.ml.registry import model_registry
from backend.app.artifacts.manager import artifact_manager
from backend.app.db.repositories.video_repository import VideoRepository
from backend.app.db.repositories.job_repository import JobRepository
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger


class VideoAnalysisWorkflow:
    """
    Production workflow for video analysis and important-moment flagging.
    Preserves all existing single-image and bi-temporal workflows.
    """

    @classmethod
    def route_video_query(cls, query: str) -> Tuple[TaskType, str]:
        """
        Inspects natural-language query to determine appropriate video task type.
        """
        q = query.lower().strip()
        if "track" in q:
            return TaskType.VIDEO_GROUNDING_TRACKING, "Query requests spatial target tracking across video footage."
        elif any(k in q for k in ["describe", "what is happening", "summary", "overview"]):
            return TaskType.VIDEO_VQA, "Query requests semantic visual interpretation of video footage."
        elif any(k in q for k in ["change", "scene change", "temporal difference"]):
            return TaskType.VIDEO_CHANGE, "Query requests scene-level event change detection."
        else:
            return TaskType.VIDEO_GROUNDING, "Query requests target localization and moment flagging across video footage."

    @classmethod
    async def execute(
        cls,
        video_path: Path,
        query: str,
        job_id: str,
        sampling_config: Optional[VideoSamplingConfig] = None,
        flagging_config: Optional[VideoFlagConfig] = None,
        db_session: Optional[Any] = None
    ) -> VideoAnalysisResponse:
        """
        Executes complete video analysis pipeline.
        """
        t0 = time.time()
        trace: List[ExecutionStep] = []
        models_used: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        sampling_cfg = sampling_config or VideoSamplingConfig()
        flagging_cfg = flagging_config or VideoFlagConfig()

        def add_trace(step: str, status: str = "success", model: Optional[str] = None, details: Optional[str] = None):
            ts = datetime.now(timezone.utc).isoformat()
            trace.append(ExecutionStep(
                timestamp=ts,
                step=step,
                status=status,
                model=model,
                details=details
            ))

        # Setup job artifacts directory
        dirs = artifact_manager.init_job_workspace(job_id)
        video_artifacts_dir = dirs["root"] / "video"
        video_artifacts_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Video Inspection & Metadata Extraction
            add_trace("Inspecting video stream", details=f"Decoding metadata for '{video_path.name}'.")
            with VideoDecoder(video_path) as decoder:
                meta = decoder.metadata
                add_trace(
                    "Video metadata verified",
                    details=f"{meta.width}x{meta.height}, {meta.fps:.2f} fps, {meta.frame_count} frames, {meta.duration_sec:.2f}s."
                )

                # 2. Task Routing
                task, route_reason = cls.route_video_query(query)
                add_trace(f"Task routed: {task.value}", details=route_reason)

                # 3. Frame Sampling
                add_trace("Sampling video frames", details=f"Target: {sampling_cfg.sample_fps} FPS, max {sampling_cfg.max_frames} frames.")
                sampled_frames = VideoSampler.sample_coarse_frames(decoder, config=sampling_cfg)
                add_trace(f"Sampled {len(sampled_frames)} frames for specialist analysis.")

                if not sampled_frames:
                    raise InvalidInputError(f"No frames could be extracted from video '{video_path.name}'.")

                # 4. Specialist Execution
                detections: List[FrameDetection] = []
                # Declared here, not inside the grounding branch: the completion status
                # below reads it for every task type.
                frame_errors: List[str] = []
                # Detections dropped because the region's pixels are not the colour asked for.
                rejected_by_colour = 0
                # Detections dropped as low-confidence or degenerate boxes.
                rejected_low_quality = 0
                best_rejected_colour_score = 0.0

                if task in (TaskType.VIDEO_GROUNDING, TaskType.VIDEO_GROUNDING_TRACKING):
                    gd_adapter = model_registry.get_adapter("grounding_dino")
                    models_used.append("grounding_dino")
                    v4_parsed = parse_v4_query(query)
                    target_label = v4_parsed.get("clean_prompt") or v4_parsed.get("category") or "vehicle"

                    add_trace(
                        "Running Grounding DINO candidate detection",
                        model="grounding_dino",
                        details=f"Parsed target: '{target_label}', directive keywords stripped."
                    )

                    # Detect across sampled frames
                    for frame_idx, ts_sec, pil_img in sampled_frames:
                        img_w, img_h = pil_img.size
                        try:
                            gd_res = gd_adapter.predict({
                                "image_pil": pil_img,
                                "query": target_label,
                                "box_threshold": 0.25,
                                "text_threshold": 0.25
                            })

                            raw_candidates = gd_res.boxes  # GroundingResult exposes boxes top-level, not in metadata
                            if raw_candidates:
                                # Apply V4 Reasoning Candidate Selection
                                v4_res = run_v4_reasoning(
                                    candidates=raw_candidates,
                                    query=query,
                                    img_shape=(img_h, img_w),
                                    image=pil_img,
                                    adapter=gd_adapter
                                )

                                sel_cand = v4_res.get("selected_box") if v4_res else None
                                if sel_cand:
                                    sel_box_2d = sel_cand.get("box_2d")
                                    if not sel_box_2d:
                                        x1, y1, x2, y2 = sel_cand["xyxy"]
                                        sel_box_2d = [y1 / img_h, x1 / img_w, y2 / img_h, x2 / img_w]

                                    # The composite lives on the selected candidate as
                                    # "reasoning_score" (singular). The old read looked for
                                    # "composite_score" inside "reasoning_scores", which holds
                                    # per-modifier keys (detector/position/size/color/relation)
                                    # and never that one -- so this silently defaulted to 1.0 for
                                    # every detection, making 30% of event_score a constant.
                                    reasoning_score = float(sel_cand.get("reasoning_score", 1.0))
                                    det_score = float(sel_cand.get("score", gd_res.confidence or 0.5))
                                    strategy = v4_res.get("strategy", "Candidate matches query")

                                    # Detector-quality gate. Grounding DINO at
                                    # box_threshold 0.25 also returns low-confidence
                                    # artefacts: on this clip a white parking-line marking
                                    # (24x43px) and a degenerate full-frame box both scored
                                    # 0.28, while real vehicles scored 0.67-0.89. Both
                                    # produced spurious events (project/pre-demo.md 3g).
                                    if det_score < flagging_cfg.min_detector_score:
                                        rejected_low_quality += 1
                                        continue
                                    _x1, _y1, _x2, _y2 = sel_cand["xyxy"]
                                    _area = abs(_x2 - _x1) * abs(_y2 - _y1)
                                    if _area > flagging_cfg.max_box_area_ratio * img_w * img_h:
                                        rejected_low_quality += 1
                                        continue

                                    # Colour gate. Grounding DINO returns a best-matching region
                                    # for any prompt and its confidence cannot separate present
                                    # from absent (measured 0.83-0.92 for red, white, yellow, blue
                                    # and green alike on this clip). Photometric colour
                                    # consistency can: present 0.97-1.00, absent 0.21-0.26.
                                    # Deterministic pixel statistics, no black-box scoring.
                                    if v4_parsed.get("color"):
                                        cs = color_score(
                                            sel_cand["xyxy"], pil_img, v4_parsed["color"]
                                        )
                                        if cs < flagging_cfg.min_colour_score:
                                            rejected_by_colour += 1
                                            best_rejected_colour_score = max(
                                                best_rejected_colour_score, cs
                                            )
                                            continue

                                    detections.append(FrameDetection(
                                        frame_index=frame_idx,
                                        timestamp_sec=ts_sec,
                                        box_2d=sel_box_2d,
                                        label=sel_cand.get("label", target_label),
                                        detector_score=det_score,
                                        reasoning_score=reasoning_score,
                                        reason=f"V4 Reasoning selected via {strategy}",
                                        image=pil_img
                                    ))
                        except Exception as e:
                            frame_errors.append(f"frame {frame_idx}: {e}")
                            logger.warning(f"Grounding failed on frame {frame_idx}: {e}")

                    if frame_errors:
                        add_trace(
                            f"Candidate detections found on {len(detections)} sampled frames; "
                            f"{len(frame_errors)} frame(s) failed.",
                            status="warning",
                            details=f"First failure -- {frame_errors[0]}",
                        )
                    else:
                        add_trace(f"Candidate detections found on {len(detections)} sampled frames.")

                    if rejected_low_quality:
                        add_trace(
                            f"Rejected {rejected_low_quality} low-quality candidate region(s)",
                            details=(
                                f"Below detector confidence {flagging_cfg.min_detector_score}, or "
                                f"covering more than {flagging_cfg.max_box_area_ratio:.0%} of the frame."
                            ),
                        )

                    if rejected_by_colour:
                        add_trace(
                            f"Colour gate rejected {rejected_by_colour} candidate region(s) that are "
                            f"not {v4_parsed['color']}",
                            details=(
                                f"Best colour-consistency score {best_rejected_colour_score:.3f} is "
                                f"below the {flagging_cfg.min_colour_score} threshold. The detector "
                                f"returns a best-matching region for any prompt; this checks whether "
                                f"the region's pixels are actually the requested colour."
                            ),
                        )

                    # 5. SAM 2.1 Video Propagation & Segmentation
                    if detections and model_registry.is_model_available("sam2"):
                        sam2_adapter = model_registry.get_adapter("sam2")
                        models_used.append("sam2")
                        add_trace(
                            "Running SAM 2.1 video mask propagation",
                            model="sam2",
                            details="Propagating target mask across video timeline."
                        )

                        # Write sampled frames into temp directory for official SAM2VideoPredictor
                        temp_frames_dir = video_artifacts_dir / "temp_frames"
                        temp_frames_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            frame_path_map = {}
                            for f_idx, _, img in sampled_frames:
                                frame_p = temp_frames_dir / f"{f_idx:06d}.jpg"
                                img.save(frame_p, quality=95)
                                frame_path_map[f_idx] = frame_p

                            # SAM2VideoPredictor indexes the frame directory POSITIONALLY
                            # (0..N-1 over the sorted files), not by original video frame
                            # number. Passing the original index (e.g. 60) into a 6-frame
                            # directory raised "index 60 is out of bounds for dimension 0 with
                            # size 6", was caught, and fell back to per-image prediction --
                            # which yielded ~9 mask pixels. Flags carried a box but no usable
                            # segmentation (project/pre-demo.md 2.1c).
                            pos_by_frame = {
                                f_idx: pos for pos, (f_idx, _, _) in enumerate(sampled_frames)
                            }
                            frame_by_pos = {pos: f_idx for f_idx, pos in pos_by_frame.items()}

                            # Identify highest confidence detection as propagation anchor
                            anchor_det = max(detections, key=lambda d: d.detector_score * 0.6 + d.reasoning_score * 0.4)
                            sam2_video_results = sam2_adapter.predict_video(
                                video_input=temp_frames_dir,
                                prompt_box=anchor_det.box_2d,
                                prompt_frame_idx=pos_by_frame[anchor_det.frame_index]
                            )

                            # If video propagation produced masks, attach them
                            if sam2_video_results:
                                # Results come back keyed by the same positional index, so map
                                # them back onto original frame numbers.
                                by_frame = {
                                    frame_by_pos[pos]: res
                                    for pos, res in sam2_video_results.items()
                                    if pos in frame_by_pos
                                }
                                for det in detections:
                                    if det.frame_index in by_frame:
                                        res_dict = by_frame[det.frame_index]
                                        det.mask = res_dict.get("mask")
                                        det.segmentation_score = float(res_dict.get("score", 0.90))
                            else:
                                # Documented fallback: apply SAM 2 image segmentation on peak anchor
                                img_res = sam2_adapter.predict({
                                    "image_pil": anchor_det.image,
                                    "boxes": [anchor_det.box_2d]
                                })
                                if img_res.masks:
                                    anchor_det.mask = img_res.masks[0].get("binary_mask")
                                    anchor_det.segmentation_score = float(img_res.masks[0].get("score", 0.85))

                        finally:
                            shutil.rmtree(temp_frames_dir, ignore_errors=True)

                # 6. Temporal Aggregation & Flagging
                add_trace("Aggregating detections and generating event flags")
                flags = VideoFlagger.generate_flags(
                    detections=detections,
                    job_id=job_id,
                    video_id=job_id,
                    artifacts_video_dir=video_artifacts_dir,
                    config=flagging_cfg
                )

                if not flags and rejected_by_colour and not detections:
                    # Everything the detector proposed failed the colour check, so the
                    # requested colour is not present. Say so, rather than reporting the
                    # nearest-looking object as if it matched.
                    workflow_reason = (
                        f"NOT_APPLICABLE: no {v4_parsed['color']} "
                        f"{v4_parsed.get('category') or 'object'} found in this footage. "
                        f"{rejected_by_colour} candidate region(s) were detected but none are "
                        f"{v4_parsed['color']} (best colour-consistency score "
                        f"{best_rejected_colour_score:.3f}, threshold "
                        f"{flagging_cfg.min_colour_score})."
                    )
                    add_trace("Analysis complete: NOT_APPLICABLE", details=workflow_reason)
                elif not flags and frame_errors and not detections:
                    # Every frame errored, so we never actually looked. Reporting this as
                    # "no relevant events" would claim a negative result we did not measure.
                    workflow_reason = (
                        f"DETECTION_FAILED: all {len(frame_errors)} sampled frame(s) failed during "
                        f"detection, so no conclusion about the target can be drawn. "
                        f"First failure -- {frame_errors[0]}"
                    )
                    add_trace("Analysis incomplete: DETECTION_FAILED", status="error", details=workflow_reason)
                elif not flags:
                    workflow_reason = "NO_RELEVANT_EVENTS_FOUND: No candidate detections satisfied temporal persistence and event score thresholds."
                    if frame_errors:
                        workflow_reason += f" ({len(frame_errors)} frame(s) also failed during detection.)"
                    add_trace("Analysis complete: NO_RELEVANT_EVENTS_FOUND", details=workflow_reason)
                else:
                    workflow_reason = f"Detected and flagged {len(flags)} important moment(s) with visual evidence."
                    add_trace(f"Generated {len(flags)} event flags", details=workflow_reason)

                # 7. PostgreSQL Persistence
                if db_session is not None:
                    try:
                        # Save VideoRecord
                        await VideoRepository.create_or_update_video(
                            session=db_session,
                            job_id=job_id,
                            filename=video_path.name,
                            file_path=str(video_path),
                            metadata=meta,
                            video_id=job_id
                        )

                        # Save keyframe records
                        saved_frame_records = []
                        for f in flags:
                            if f.keyframe_url:
                                saved_frame_records.append({
                                    "frame_index": f.peak_frame,
                                    "timestamp_sec": round(f.start_timestamp + (f.end_timestamp - f.start_timestamp) / 2.0, 3),
                                    "is_keyframe": True,
                                    "image_path": f.keyframe_url
                                })
                        if saved_frame_records:
                            await VideoRepository.save_video_frames(
                                session=db_session,
                                video_id=job_id,
                                frames=saved_frame_records
                            )

                        # Save VideoFlag records
                        await VideoRepository.save_video_flags(
                            session=db_session,
                            video_id=job_id,
                            flags=flags
                        )

                        # Update AnalysisJob status
                        await JobRepository.update_job_status(
                            session=db_session,
                            job_id=job_id,
                            status=JobStatus.COMPLETED.value,
                            task_type=task.value
                        )
                        logger.info(f"Successfully persisted video job '{job_id}' to PostgreSQL.")
                    except Exception as e:
                        logger.warning(f"Database persistence for video job '{job_id}' encountered error: {e}")
                        warnings.append(f"Database persistence warning: {e}")

                # Build response
                artifacts = artifact_manager.list_artifacts(job_id)

                return VideoAnalysisResponse(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    task=task,
                    workflow_reason=workflow_reason,
                    video_metadata=meta,
                    flags=flags,
                    models_used=models_used,
                    execution_trace=trace,
                    warnings=warnings,
                    errors=errors,
                    artifacts=artifacts
                )

        except Exception as e:
            logger.exception(f"VideoAnalysisWorkflow failed: {e}")
            add_trace(f"Video analysis error: {e}", status="error", details=str(e))
            errors.append(str(e))

            # Build minimal metadata fallback if decoding failed before metadata
            meta_fallback = VideoMetadata(
                filename=video_path.name,
                duration_sec=0.0,
                fps=0.0,
                width=0,
                height=0,
                frame_count=0
            )

            return VideoAnalysisResponse(
                job_id=job_id,
                status=JobStatus.FAILED,
                task=TaskType.UNSUPPORTED,
                workflow_reason=f"Pipeline aborted: {e}",
                video_metadata=meta_fallback,
                flags=[],
                models_used=models_used,
                execution_trace=trace,
                warnings=warnings,
                errors=errors,
                artifacts={}
            )
