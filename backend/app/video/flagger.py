"""
SatQuery AI — VideoFlagger
Temporal aggregation and event flagging engine.
Groups multi-frame candidate detections into continuous event intervals,
filters transient single-frame noise, computes transparent heuristic event scores,
and saves keyframe/overlay artifacts.
"""
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import uuid
import numpy as np
from PIL import Image, ImageDraw

from backend.app.schemas.video import VideoFlag, VideoFlagConfig
from backend.app.config import settings, VideoEventScoringSettings
from backend.app.geo.rendering import save_image
from backend.app.logging import logger


def draw_mask_outline(image: Image.Image, mask: np.ndarray, color_rgb=(0, 230, 150), thickness: int = 2) -> Image.Image:
    """Draws only the boundary of a binary mask, leaving the object's own pixels (and colour) untouched."""
    from scipy import ndimage
    m = np.squeeze(mask) > 0
    out = np.array(image.convert("RGB"))
    if m.shape != out.shape[:2] or not m.any():
        return image
    edge = m & ~ndimage.binary_erosion(m, iterations=thickness)
    out[edge] = color_rgb
    return Image.fromarray(out)


class FrameDetection:
    """Represents an individual frame detection event."""
    def __init__(
        self,
        frame_index: int,
        timestamp_sec: float,
        box_2d: List[float],  # [ymin, xmin, ymax, xmax] normalized 0-1
        label: str,
        detector_score: float,
        reasoning_score: float = 1.0,
        segmentation_score: float = 0.0,
        mask: Optional[np.ndarray] = None,
        reason: str = "Query-matched detection",
        image: Optional[Image.Image] = None
    ):
        self.frame_index = frame_index
        self.timestamp_sec = timestamp_sec
        self.box_2d = box_2d
        self.label = label
        self.detector_score = float(detector_score)
        self.reasoning_score = float(reasoning_score)
        self.segmentation_score = float(segmentation_score)
        self.mask = mask
        self.reason = reason
        self.image = image


class VideoFlagger:
    """
    Temporal clustering and evidence-based event flagger.
    Turns frame detections into structured important-moment flags.
    """

    @classmethod
    def compute_event_score(
        cls,
        detector_score: float,
        reasoning_score: float,
        segmentation_score: float,
        persistence_seconds: float,
        scoring_cfg: Optional[VideoEventScoringSettings] = None
    ) -> float:
        """
        Computes transparent heuristic event-ranking score from real signals.
        Documentation: Heuristic event-ranking score; not calibrated model probability.
        """
        cfg = scoring_cfg or settings.video.event_scoring
        cfg.validate_weights()

        # Normalize persistence factor up to 2.0 seconds saturation
        persistence_factor = min(1.0, max(0.0, persistence_seconds / 2.0))

        score = (
            cfg.detector_weight * float(detector_score) +
            cfg.reasoning_weight * float(reasoning_score) +
            cfg.segmentation_weight * float(segmentation_score) +
            cfg.persistence_weight * float(persistence_factor)
        )
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    @classmethod
    def cluster_detections(
        cls,
        detections: List[FrameDetection],
        config: Optional[VideoFlagConfig] = None
    ) -> List[List[FrameDetection]]:
        """
        Groups chronological frame detections into contiguous clusters based on max_gap_frames and max_gap_seconds.
        """
        if not detections:
            return []

        cfg = config or VideoFlagConfig()
        sorted_dets = sorted(detections, key=lambda d: d.frame_index)

        clusters: List[List[FrameDetection]] = []
        current_cluster: List[FrameDetection] = [sorted_dets[0]]

        for d in sorted_dets[1:]:
            prev_d = current_cluster[-1]
            frame_gap = d.frame_index - prev_d.frame_index
            time_gap = d.timestamp_sec - prev_d.timestamp_sec

            # Cluster on TIME. Frames are sampled with a stride, so consecutive
            # detections are typically ~12 frame indices apart and frame_gap almost
            # never satisfies max_gap_frames. The old condition was an OR, so the
            # frame test contributed nothing and an event's boundaries were set by
            # wherever the coarse sampling happened to land. The frame test is kept
            # only as an additional allowance for densely sampled (stride 1) runs.
            if time_gap <= cfg.max_gap_seconds or (
                frame_gap <= cfg.max_gap_frames and time_gap <= cfg.max_gap_seconds * 2
            ):
                current_cluster.append(d)
            else:
                clusters.append(current_cluster)
                current_cluster = [d]

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    @classmethod
    def generate_flags(
        cls,
        detections: List[FrameDetection],
        job_id: str,
        video_id: str,
        artifacts_video_dir: Path,
        config: Optional[VideoFlagConfig] = None,
        scoring_config: Optional[VideoEventScoringSettings] = None,
        verifier: Optional[Any] = None,
        target_label: Optional[str] = None,
        rejections: Optional[List[Dict[str, Any]]] = None
    ) -> List[VideoFlag]:
        """
        Aggregates frame detections, filters transient noise, extracts peak representative keyframes,
        draws spatial overlays, and returns finalized VideoFlag records.
        """
        cfg = config or VideoFlagConfig()
        scoring_cfg = scoring_config or settings.video.event_scoring
        scoring_cfg.validate_weights()

        clusters = cls.cluster_detections(detections, config=cfg)
        flags: List[VideoFlag] = []

        artifacts_video_dir.mkdir(parents=True, exist_ok=True)

        for cluster in clusters:
            start_frame = cluster[0].frame_index
            end_frame = cluster[-1].frame_index
            start_ts = round(cluster[0].timestamp_sec, 3)
            end_ts = round(cluster[-1].timestamp_sec, 3)
            duration_sec = round(end_ts - start_ts, 3)
            frame_span = len(cluster)

            # Persistence filter: drop transient noise. This is an OR — a cluster must
            # satisfy BOTH the frame count and the duration to survive. It used to be an
            # AND, so a two-frame 0.24s blip passed on frame count alone and became an
            # "event" (project/pre-demo.md 3g).
            if frame_span < cfg.min_persistence_frames or duration_sec < cfg.min_persistence_seconds:
                logger.info(
                    f"Filtered transient detection at frame {start_frame} ({duration_sec:.2f}s, {frame_span} frames). "
                    f"Requires >= {cfg.min_persistence_frames} frames or >= {cfg.min_persistence_seconds}s."
                )
                continue

            # Identify peak representative detection within the cluster
            # Peak is selected by highest composite detector + reasoning score
            peak_det = max(cluster, key=lambda d: d.detector_score * 0.6 + d.reasoning_score * 0.4)

            # Calculate transparent event score
            event_score = cls.compute_event_score(
                detector_score=peak_det.detector_score,
                reasoning_score=peak_det.reasoning_score,
                segmentation_score=peak_det.segmentation_score,
                persistence_seconds=duration_sec,
                scoring_cfg=scoring_cfg
            )

            if event_score < cfg.min_event_score:
                logger.info(
                    f"Cluster at {start_ts:.2f}s-{end_ts:.2f}s dropped due to low event score ({event_score:.3f} < {cfg.min_event_score})."
                )
                continue

            # Second-agent verification: RemoteCLIP checks the event's strongest detections. A single
            # crop confirms a real vehicle 55.5% of the time but an absent class only 3.5% of the time
            # (detection_verifier_3way_20260914.json), so requiring one confirmation among up to N
            # frames keeps real events while dropping hallucinated ones. The confirmed frame becomes
            # the keyframe, since it is the better evidence.
            verification: Optional[Dict[str, Any]] = None
            if verifier is not None:
                n_check = settings.agent_verification.video_frames_to_verify
                checked = sorted([d for d in cluster if d.image is not None], key=lambda d: -d.detector_score)[:n_check]
                results = []
                for det in checked:
                    w_img, h_img = det.image.size
                    ymin, xmin, ymax, xmax = det.box_2d
                    v = verifier.verify(det.image, [xmin * w_img, ymin * h_img, xmax * w_img, ymax * h_img],
                                        target_label or det.label)
                    results.append((det, v))
                confirmed = [(d, v) for d, v in results if v.status == "verified"]
                verification = {
                    "frames_checked": len(results),
                    "frames_verified": len(confirmed),
                    "statuses": [v.status for _, v in results],
                    "verifier_confidence": round(max((v.target_probability for _, v in results), default=0.0), 4),
                    "top_matches": [v.top_alternatives[0][0] for _, v in results],
                }
                if results and not confirmed:
                    logger.info(f"Cluster at {start_ts:.2f}s-{end_ts:.2f}s dropped: verification agent confirmed 0/{len(results)} frames.")
                    if rejections is not None:
                        rejections.append({
                            "start_timestamp": start_ts, "end_timestamp": end_ts,
                            "label": peak_det.label, "event_score": event_score,
                            "detector_score": round(peak_det.detector_score, 4), **verification,
                        })
                    continue
                if confirmed:
                    # Keyframe preference: a confirmed frame that also has a SAM 2 mask, then the original
                    # peak if it carries the mask, then the most confident confirmed frame. SAM 2 only
                    # masks some frames, and switching to an unmasked one silently dropped the mask.
                    with_mask = [dv for dv in confirmed if dv[0].mask is not None]
                    if with_mask:
                        peak_det = max(with_mask, key=lambda dv: dv[1].target_probability)[0]
                    elif peak_det.mask is None:
                        peak_det = max(confirmed, key=lambda dv: dv[1].target_probability)[0]

            flag_id = f"flag_{uuid.uuid4().hex[:8]}"

            # Generate and save keyframe and overlay artifacts
            keyframe_rel_url = None
            overlay_rel_url = None
            mask_rel_url = None

            if peak_det.image is not None:
                # 1. Representative keyframe
                kf_filename = f"{flag_id}_keyframe_frame_{peak_det.frame_index}.png"
                kf_path = artifacts_video_dir / kf_filename
                peak_det.image.save(kf_path)
                keyframe_rel_url = f"/api/artifacts/{job_id}/video/{kf_filename}"

                # 2. Keyframe with bounding box annotation
                annotated_img = peak_det.image.copy()
                draw = ImageDraw.Draw(annotated_img)
                w, h = annotated_img.size
                ymin, xmin, ymax, xmax = peak_det.box_2d
                box_px = [int(xmin * w), int(ymin * h), int(xmax * w), int(ymax * h)]

                # Emerald green box for detected vehicle/target
                draw.rectangle(box_px, outline=(0, 230, 150), width=3)
                label_text = f"{peak_det.label} ({event_score:.2f})"
                draw.text((box_px[0] + 4, max(0, box_px[1] - 16)), label_text, fill=(0, 230, 150))

                # 3. If SAM2 mask is present, outline it
                if peak_det.mask is not None:
                    bin_mask = (peak_det.mask > 0).astype(np.uint8)
                    # Outline, not a 45% fill: the fill tinted a red car green, so the colour the user asked for
                    # could not be checked on the keyframe (Q-019).
                    annotated_img = draw_mask_outline(annotated_img, bin_mask, color_rgb=(0, 230, 150))

                    # Save raw binary mask
                    mask_filename = f"{flag_id}_mask_frame_{peak_det.frame_index}.png"
                    mask_path = artifacts_video_dir / mask_filename
                    Image.fromarray((bin_mask * 255).astype(np.uint8)).save(mask_path)
                    mask_rel_url = f"/api/artifacts/{job_id}/video/{mask_filename}"

                ann_filename = f"{flag_id}_annotated_frame_{peak_det.frame_index}.png"
                ann_path = artifacts_video_dir / ann_filename
                annotated_img.save(ann_path)
                overlay_rel_url = f"/api/artifacts/{job_id}/video/{ann_filename}"

            flag = VideoFlag(
                flag_id=flag_id,
                video_id=video_id,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                start_frame=start_frame,
                end_frame=end_frame,
                peak_frame=peak_det.frame_index,
                label=peak_det.label,
                reason=peak_det.reason,
                event_score=event_score,
                keyframe_url=keyframe_rel_url,
                overlay_url=overlay_rel_url,
                mask_url=mask_rel_url,
                box_2d=peak_det.box_2d,
                model_scores={
                    "detector_score": round(peak_det.detector_score, 4),
                    "reasoning_score": round(peak_det.reasoning_score, 4),
                    "segmentation_score": round(peak_det.segmentation_score, 4),
                    "persistence_seconds": duration_sec,
                    "frame_span": frame_span,
                    **({"verifier_confidence": verification["verifier_confidence"],
                        "verified_frames": f"{verification['frames_verified']}/{verification['frames_checked']}"}
                       if verification else {}),
                },
                metadata={
                    "event_score_type": "heuristic_ranking_score",
                    "calibrated_model_probability": False,
                    "agent_verification": verification,
                    "peak_frame": peak_det.frame_index,
                    "job_id": job_id
                }
            )
            flags.append(flag)

        logger.info(f"VideoFlagger generated {len(flags)} event flags for job '{job_id}'.")
        return flags
