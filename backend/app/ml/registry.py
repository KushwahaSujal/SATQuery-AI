import torch
from typing import Any, Dict, List, Optional, Tuple, Type
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.ml.adapters.changeformer import ChangeFormerAdapter
from backend.app.ml.adapters.cdvqa import CDVQAAdapter
from backend.app.ml.adapters.dofa import DOFAAdapter
from backend.app.ml.adapters.eurosat import EuroSatLandCoverAdapter
from backend.app.ml.adapters.flood_segmenter import FloodSegmenterAdapter
from backend.app.ml.adapters.fusion import OpticalSARFusionModel
from backend.app.ml.adapters.general_rs_vlm import GeneralRSVLMAdapter
from backend.app.ml.adapters.scene_vlm import SceneVLMAdapter
from backend.app.ml.adapters.remoteclip import RemoteCLIPAdapter
from backend.app.ml.adapters.bigearthnet import BigEarthNetMultimodalAdapter
from backend.app.ml.adapters.binary_segmenter import (
    BuildingSegmenterAdapter,
    CloudSegmenterAdapter,
    RoadSegmenterAdapter,
    WaterSegmenterAdapter,
)
from backend.app.ml.adapters.landcover_segmenter import (
    IsprsPotsdamSegmenterAdapter,
    IsprsVaihingenSegmenterAdapter,
    LandCoverSegmenterAdapter,
)
from backend.app.ml.adapters.crater_detector import CraterDetectorAdapter
from backend.app.schemas.models import ModelCapabilityInfo
from backend.app.config import settings
from backend.app.logging import logger


# ---- the serving protocol (Q-045) --------------------------------------------------------------
#
# `adapter.available` only ever answered "is the checkpoint file on disk?". Two adapters load their
# real checkpoints and then refuse to produce an output on purpose — the flood segmenter because the
# training-time normalisation was never documented (Q-041 §5, gated by `preprocessing` since Q-044),
# the optical-SAR fusion head because it was never trained — and both were therefore listed as
# AVAILABLE, which reads as "this works".
#
# The probes below answer "will a request to this adapter return a result?" by reading the adapter's
# own live state. They are ordered; the first that applies decides; if none applies the adapter is
# treated as serving, which is the correct default for every other model in the registry.
#
# Deliberately NOT a set of model keys. A key list would have to be edited the moment
# configs/models.yaml sets `preprocessing: "bn_recovered_p2p98"` and the flood segmenter starts
# serving, and whoever flipped that key would have no reason to look here — the registry would go on
# reporting a refusal that no longer happens. Every probe re-reads the adapter on every call, so the
# reported state follows the gate with no edit here.


def _probe_declared_serving(adapter: BaseModelAdapter) -> Optional[Tuple[bool, Optional[str]]]:
    """Protocol proper: an adapter publishing `serving` (bool, or callable) is believed.

    Nothing implements this yet — `BaseModelAdapter` is owned elsewhere and neither refusing adapter
    was in scope to edit. It is first in the order so that an adapter which later declares `serving`
    (and optionally `refusal_reason`) overrides every heuristic below it, and so that the heuristics
    can be deleted once all refusing adapters declare it.
    """
    declared = getattr(adapter, "serving", None)
    if declared is None:
        return None
    if callable(declared):
        try:
            declared = declared()
        except Exception as e:                                    # a broken probe must not decide
            logger.warning(f"{type(adapter).__name__}.serving() raised {type(e).__name__}: {e}")
            return None
    if bool(declared):
        return True, None
    reason = getattr(adapter, "refusal_reason", None)
    if callable(reason):
        try:
            reason = reason()
        except Exception:
            reason = None
    return False, str(reason) if reason else (
        f"{type(adapter).__name__} declares serving=False: a request returns a refusal, not a result."
    )


def _probe_is_configured(adapter: BaseModelAdapter) -> Optional[Tuple[bool, Optional[str]]]:
    """`is_configured` False means the adapter's own predict() returns a refusal (fusion head)."""
    if not hasattr(adapter, "is_configured"):
        return None
    if bool(getattr(adapter, "is_configured")):
        return True, None
    return False, (
        f"{type(adapter).__name__}.is_configured is False, so predict() returns "
        f"status='NOT_CONFIGURED' and no prediction. The checkpoint exists and loads; the head it "
        f"contains was never trained, so there is nothing to serve."
    )


#: Accepted-value gates: an adapter property whose value must equal a class constant before the
#: adapter will serve. Named by gate, never by model, and read live — flipping the YAML key flips the
#: reported state. `preprocessing` is the flood serving gate from Q-044; its sole accepted value
#: lives on the adapter as `RECOVERED_PREPROCESSING`, so the accepted value is never restated here.
_ACCEPTED_VALUE_GATES: Tuple[Tuple[str, str], ...] = (
    ("preprocessing", "RECOVERED_PREPROCESSING"),
)


def _probe_accepted_value_gate(adapter: BaseModelAdapter) -> Optional[Tuple[bool, Optional[str]]]:
    """Refuses while a declared gate property does not hold the adapter's accepted value."""
    for prop, const_name in _ACCEPTED_VALUE_GATES:
        accepted = getattr(type(adapter), const_name, None)
        if accepted is None or not hasattr(adapter, prop):
            continue
        configured = getattr(adapter, prop, None)
        if configured == accepted:
            return True, None
        return False, (
            f"{type(adapter).__name__} serves only with {prop}={accepted!r}; configs/models.yaml "
            f"has {prop}={configured!r}, so predict() returns status='NOT_CONFIGURED' and no "
            f"output. The checkpoint is real and loads with strict=True."
        )
    return None


#: Evaluated in order against the live adapter; first applicable probe decides.
SERVING_PROBES: Tuple[Any, ...] = (
    _probe_declared_serving,
    _probe_is_configured,
    _probe_accepted_value_gate,
)


class ModelRegistry:
    """
    Central Professional Registry for all SatQuery AI Model Adapters.
    Tracks model capabilities, metadata, availability, lazy instances, and lifecycle management.
    Lifecycle states: NOT_CONFIGURED | AVAILABLE | PRESENT_NOT_SERVING | LOADED | FAILED

    NOT_CONFIGURED       the checkpoint is absent or the model is disabled in configs/models.yaml.
    AVAILABLE            the checkpoint is on disk; weights are not resident yet.
    LOADED               weights are resident and the model will answer a request.
    PRESENT_NOT_SERVING  the checkpoint is present and loadable, but the adapter deliberately
                         refuses to produce an output, so a request returns a refusal rather than a
                         result. Reported alongside `serving=False` and a `refusal_reason`, and kept
                         distinct from NOT_CONFIGURED on purpose: NOT_CONFIGURED means the weights
                         are not there, which is what ModelUnavailableError/HTTP 503 signals.
    FAILED               a load was attempted and failed.

    `available` keeps its original meaning throughout — "the checkpoint file exists" — because
    routing (backend/app/orchestration/dependency_checker.py) is built on it. Whether a model will
    actually answer is `serving`, resolved live by `serving_state()`.
    """
    ADAPTER_CLASSES: Dict[str, Type[BaseModelAdapter]] = {
        "grounding_dino": GroundingDINOAdapter,
        "sam2": SAM2Adapter,
        "changeformer": ChangeFormerAdapter,
        "cdvqa": CDVQAAdapter,
        "dofa": DOFAAdapter,
        "satquery_optical_sar_fusion": OpticalSARFusionModel,
        "general_rs_vlm": GeneralRSVLMAdapter,
        "scene_vlm": SceneVLMAdapter,
        "remoteclip": RemoteCLIPAdapter,
        "bigearthnet": BigEarthNetMultimodalAdapter,
        # Locally trained (Q-026, Q-028, Q-029, Q-030, Q-032, Q-035, Q-036, Q-037).
        # Auto-routed from backend/app/workflows/trained_segmenter.py:
        "roads_segmenter": RoadSegmenterAdapter,
        "buildings_segmenter": BuildingSegmenterAdapter,
        "water_segmenter": WaterSegmenterAdapter,
        "cloud_segmenter": CloudSegmenterAdapter,
        # Registered and callable, but deliberately not auto-routed — a multi-class class-index map
        # does not fit the grounding pipeline's single-binary-mask response contract, and the ISPRS
        # pair cannot be auto-selected without GSD/band metadata. See
        # docs/models/trained_segmenters.md.
        "landcover_segmenter": LandCoverSegmenterAdapter,
        "isprs_potsdam_segmenter": IsprsPotsdamSegmenterAdapter,
        "isprs_vaihingen_segmenter": IsprsVaihingenSegmenterAdapter,
        "crater_detector": CraterDetectorAdapter,
        # Same spirit, different reasons (Q-041). EuroSAT is scene-level: one label for the whole
        # tile, no mask and no box, so it cannot satisfy the grounding pipeline's response contract.
        # The flood segmenter loads its real checkpoint but NEVER serves a mask — the training-time
        # normalisation was never documented and no candidate preprocessing reproduced the delivered
        # IoU 0.6292, so predict() reports NOT_CONFIGURED; it also needs all 16 S1+S2+DEM bands,
        # which the pipeline cannot supply. See docs/models/eurosat/ and docs/models/flood/.
        "eurosat_classifier": EuroSatLandCoverAdapter,
        "flood_segmenter": FloodSegmenterAdapter,
    }

    MODEL_METADATA: Dict[str, Dict[str, Any]] = {
        "grounding_dino": {
            "family": "GroundingDINO",
            "source": "IDEA-Research/grounding-dino-base",
            "license": "Apache 2.0",
            "capabilities": ["zero_shot_grounding", "bounding_box_localization"],
            "input_requirements": {"image": "RGB (H, W, 3)", "text_prompt": "string ending in period"},
            "output_schema": {"boxes": "List[[x1, y1, x2, y2]] normalized", "scores": "List[float]"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "sam2": {
            "family": "Segment Anything 2.1",
            "source": "facebook/sam2.1-hiera-small",
            "license": "Apache 2.0",
            "capabilities": ["promptable_segmentation", "video_mask_propagation"],
            "input_requirements": {"image": "RGB (H, W, 3)", "box": "[x1, y1, x2, y2]"},
            "output_schema": {"mask": "ndarray (H, W) bool", "score": "float"},
            "device_requirements": {"min_vram_gb": 3.0, "preferred": "cuda"},
        },
        "changeformer": {
            "family": "ChangeFormerV6",
            "source": "checkpoints/changeformer/changeformer_v6_levir_levircd256_epoch20_best.pt",
            "license": "MIT",
            "capabilities": ["bi_temporal_change_detection", "probability_mapping"],
            "input_requirements": {"image_a": "RGB (H, W, 3), co-registered, native resolution", "image_b": "RGB (H, W, 3), same size as image_a"},
            "output_schema": {"change_mask": "ndarray (H, W) uint8", "probability_map": "ndarray (H, W) float32"},
            "device_requirements": {"min_vram_gb": 4.0, "preferred": "cuda"},
        },
        "cdvqa": {
            "family": "CDVQA ResNet18-CEM",
            "source": "checkpoints/cdvqa/cdvqa_satquery.pt",
            "license": "Academic / MIT",
            "capabilities": ["bi_temporal_change_vqa", "semantic_change_classification"],
            "input_requirements": {"image_a": "RGB (256, 256, 3)", "image_b": "RGB (256, 256, 3)", "question": "string"},
            "output_schema": {"answer": "string", "answer_class": "string", "confidence": "float"},
            "device_requirements": {"min_vram_gb": 1.5, "preferred": "cuda"},
        },
        "dofa": {
            "family": "DOFA Foundation Model",
            "source": "checkpoints/dofa/DOFA_ViT_large_e100.pth",
            "license": "MIT",
            "capabilities": ["cross_modal_representation", "optical_sar_encoding"],
            "input_requirements": {"optical": "RGB (H, W, 3)", "sar": "SAR (H, W, 2)"},
            "output_schema": {"features": "ndarray"},
            "device_requirements": {"min_vram_gb": 6.0, "preferred": "cuda"},
        },
        "satquery_optical_sar_fusion": {
            "family": "SatQuery Cross-Attention Fusion",
            "source": "checkpoints/optical_sar/satquery_fusion.pth",
            "license": "Proprietary",
            "capabilities": ["optical_sar_fusion_prediction", "multimodal_fusion", "cross_modal_analysis"],
            "input_requirements": {"optical": "RGB (H, W, 3)", "sar": "SAR (H, W, 2)"},
            # The fusion head was never trained, so predict() returns status NOT_CONFIGURED and none
            # of these keys. Kept here as the contract a trained head would have to satisfy.
            "output_schema": {"status": "NOT_CONFIGURED — no prediction is returned; the cross-attention fusion head is untrained (Q-045)"},
            "device_requirements": {"min_vram_gb": 4.0, "preferred": "cuda"},
        },
        "general_rs_vlm": {
            "family": "General RS-VLM (BLIP-VQA)",
            "source": "checkpoints/general_rs_vlm",
            "license": "BSD-3-Clause",
            "capabilities": ["single_image_vqa", "scene_understanding", "captioning"],
            "input_requirements": {"image": "RGB (H, W, 3)", "query": "string"},
            "output_schema": {"answer": "string", "confidence": "float"},
            "device_requirements": {"min_vram_gb": 3.0, "preferred": "cuda"},
        },
        "scene_vlm": {
            "family": "Qwen3-VL-4B-Instruct (4-bit NF4)",
            "source": "checkpoints/scene_vlm_qwen3vl4b_nf4",
            "license": "Apache-2.0",
            "capabilities": ["single_image_vqa", "scene_understanding", "captioning"],
            "input_requirements": {"image": "RGB (H, W, 3)", "query": "string"},
            "output_schema": {"answer": "string"},
            "device_requirements": {"min_vram_gb": 4.0, "preferred": "cuda"},
        },
        "remoteclip": {
            "family": "RemoteCLIP",
            "source": "checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt",
            "license": "MIT",
            "capabilities": ["zero_shot_classification", "cross_modal_retrieval"],
            "input_requirements": {"image": "RGB (224, 224, 3)", "text": "string"},
            "output_schema": {"similarity": "float"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "bigearthnet": {
            "family": "BigEarthNet-v2.0",
            "source": "checkpoints/bigearthnet/model.safetensors",
            "license": "Community Data License Agreement (CDLA-Permissive-1.0)",
            "capabilities": ["multimodal_land_cover", "optical_sar_analysis"],
            "input_requirements": {"optical": "Sentinel-2 bands", "sar": "Sentinel-1 dual-pol"},
            "output_schema": {"predictions": "list[dict]"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "roads_segmenter": {
            "family": "U-Net / ResNet-50 (smp)",
            "source": "checkpoints/roads_all_r50_seg/best.pt",
            "license": "MIT (code); per-dataset licences for DeepGlobe, Massachusetts, SpaceNet 3",
            "capabilities": ["road_segmentation", "binary_mask_segmentation"],
            "input_requirements": {"image": "RGB (H, W, 3), trained at 0.5 m GSD"},
            "output_schema": {"binary_mask": "ndarray (H, W) uint8", "probability_map": "ndarray (H, W) float32"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "buildings_segmenter": {
            "family": "U-Net / ResNet-50 (smp)",
            "source": "checkpoints/buildings_whu_ma_r50_seg/best.pt",
            "license": "MIT (code); per-dataset licences for WHU Building and Massachusetts",
            "capabilities": ["building_footprint_segmentation", "binary_mask_segmentation"],
            "input_requirements": {"image": "RGB (H, W, 3), trained at 0.5 m GSD"},
            "output_schema": {"binary_mask": "ndarray (H, W) uint8", "probability_map": "ndarray (H, W) float32"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "water_segmenter": {
            "family": "U-Net / ResNet-34 (smp)",
            "source": "checkpoints/water_seg/best.pt",
            "license": "MIT (code); Kaggle Water Bodies Dataset terms (Sentinel-2)",
            "capabilities": ["water_segmentation", "binary_mask_segmentation"],
            "input_requirements": {"image": "RGB (H, W, 3), trained at 10 m GSD (Sentinel-2)"},
            "output_schema": {"binary_mask": "ndarray (H, W) uint8", "probability_map": "ndarray (H, W) float32"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "cloud_segmenter": {
            "family": "U-Net / ResNet-34 (smp)",
            "source": "checkpoints/cloud_seg/best.pt",
            "license": "MIT (code); 95-Cloud / Landsat 8 dataset terms",
            "capabilities": ["cloud_segmentation", "binary_mask_segmentation"],
            "input_requirements": {"image": "RGB (H, W, 3), trained at 30 m GSD (Landsat 8)"},
            "output_schema": {"binary_mask": "ndarray (H, W) uint8", "probability_map": "ndarray (H, W) float32"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "landcover_segmenter": {
            "family": "U-Net / ResNet-50 (smp), 7-class head",
            "source": "checkpoints/landcover_full_r50_seg/best.pt",
            "license": "MIT (code); LoveDA and OpenEarthMap are non-commercial",
            "capabilities": ["land_cover_segmentation", "per_class_area_statistics"],
            "input_requirements": {"image": "RGB (H, W, 3), trained at 0.5 m GSD"},
            "output_schema": {"masks": "list[{binary_mask, label, area_pct}]", "class_map": "ndarray (H, W) uint8"},
            "device_requirements": {"min_vram_gb": 2.5, "preferred": "cuda"},
        },
        "isprs_potsdam_segmenter": {
            "family": "U-Net / ResNet-34 (smp), 6-class ISPRS head",
            "source": "checkpoints/isprs_potsdam_seg/best.pt",
            "license": "MIT (code); ISPRS/DGPF data, cite Cramer (2010)",
            "capabilities": ["urban_semantic_labelling", "per_class_area_statistics"],
            "input_requirements": {"image": "true-colour RGB (H, W, 3), trained at 0.1 m GSD"},
            "output_schema": {"masks": "list[{binary_mask, label, area_pct}]", "class_map": "ndarray (H, W) uint8"},
            "device_requirements": {"min_vram_gb": 2.5, "preferred": "cuda"},
        },
        "isprs_vaihingen_segmenter": {
            "family": "U-Net / ResNet-34 (smp), 6-class ISPRS head",
            "source": "checkpoints/isprs_vaihingen_seg/best.pt",
            "license": "MIT (code); ISPRS/DGPF data, cite Cramer (2010)",
            "capabilities": ["urban_semantic_labelling", "per_class_area_statistics"],
            "input_requirements": {"image": "IRRG (infrared/red/green) (H, W, 3), NOT RGB, trained at 0.1 m GSD"},
            "output_schema": {"masks": "list[{binary_mask, label, area_pct}]", "class_map": "ndarray (H, W) uint8"},
            "device_requirements": {"min_vram_gb": 2.5, "preferred": "cuda"},
        },
        "eurosat_classifier": {
            "family": "EfficientNet-B0 (torchvision)",
            "source": "checkpoints/eurosat_efficientnet_b0/best_model.pt",
            "license": "MIT (torchvision code); EuroSAT dataset terms (Sentinel-2, CC-BY 4.0)",
            "capabilities": ["land_cover_classification", "scene_classification"],
            "input_requirements": {"image": "RGB (H, W, 3), trained on Sentinel-2 at 10 m GSD, 64x64 upsampled to 224"},
            "output_schema": {"label": "str", "probabilities": "list[float] over 10 classes", "top_k": "list[{label, probability}]"},
            "device_requirements": {"min_vram_gb": 1.0, "preferred": "cuda"},
        },
        "flood_segmenter": {
            "family": "U-Net from scratch, 16-channel input (2-class head)",
            "source": "checkpoints/flood_seg/best.pt",
            "license": "MIT (code); Sen1Floods11 dataset terms (CC BY 4.0)",
            "capabilities": ["flood_segmentation"],
            "input_requirements": {"image": "16 co-registered channels (C, H, W): S1 VV, S1 VH, Sentinel-2 L1C B1-B12 incl. B8A (13 bands), Copernicus DEM; Sentinel-2 at 10 m GSD. RGB cannot satisfy this model."},
            # Gate-dependent on purpose, so this string does not go stale when the gate opens (Q-044).
            "output_schema": {
                "preprocessing: null (default)": "status NOT_CONFIGURED — no mask is returned; training-time normalisation unknown, delivered IoU 0.6292 not reproduced (Q-041 §5)",
                "preprocessing: bn_recovered_p2p98": "binary_mask, probability_map — served under normalisation recovered from the checkpoint's own BatchNorm statistics, provenance recovered_not_supplied (Q-044)",
            },
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
        "crater_detector": {
            "family": "YOLO11s (ultralytics)",
            "source": "checkpoints/craters_yolo/weights/best.pt",
            "license": "AGPL-3.0 (ultralytics); LU3M6TGT and Mars/Lunar dataset terms",
            "capabilities": ["crater_detection", "planetary_object_detection"],
            "input_requirements": {"image": "RGB (H, W, 3), lunar or Mars imagery, trained at 832 px"},
            "output_schema": {"boxes": "List[{xyxy:[x1,y1,x2,y2](px), score:float, label:str, box_2d:[...]}]"},
            "device_requirements": {"min_vram_gb": 2.0, "preferred": "cuda"},
        },
    }

    def __init__(self):
        self._instances: Dict[str, BaseModelAdapter] = {}
        self._verified_models: Dict[str, bool] = {}

    def get_adapter(self, model_key: str) -> BaseModelAdapter:
        """
        Retrieves or creates a singleton adapter instance for the given model key.
        Uses lazy loading: adapter instantiation does NOT load heavy model weights into memory.
        """
        if model_key not in self.ADAPTER_CLASSES:
            raise KeyError(f"Unknown model key '{model_key}'. Registered models: {list(self.ADAPTER_CLASSES.keys())}")
        
        if model_key not in self._instances:
            cls = self.ADAPTER_CLASSES[model_key]
            self._instances[model_key] = cls()
        return self._instances[model_key]

    def is_model_available(self, model_key: str) -> bool:
        """Checks whether the model's dependencies and weights/checkpoints are accessible."""
        if model_key not in self.ADAPTER_CLASSES:
            return False
        try:
            adapter = self.get_adapter(model_key)
            return bool(adapter.available)
        except Exception:
            return False

    def is_model_loaded(self, model_key: str) -> bool:
        """Returns True if the model weights are currently resident in memory."""
        if model_key not in self._instances:
            return False
        return bool(self._instances[model_key].loaded)

    def mark_verified(self, model_key: str, verified: bool = True) -> None:
        """Records whether live inference has been verified for this model."""
        self._verified_models[model_key] = verified

    def serving_state(self, model_key: str) -> Tuple[bool, Optional[str]]:
        """Whether a request to this model returns a result, and why not when it does not.

        Resolved live from the adapter by SERVING_PROBES, so the answer tracks
        configs/models.yaml without an edit here. Never loads weights. An unknown key, or an adapter
        that cannot even be instantiated, is not serving.
        """
        if model_key not in self.ADAPTER_CLASSES:
            return False, f"'{model_key}' is not a registered model."
        try:
            adapter = self.get_adapter(model_key)
        except Exception as e:
            return False, f"Adapter for '{model_key}' could not be instantiated: {type(e).__name__}: {e}"
        for probe in SERVING_PROBES:
            verdict = probe(adapter)
            if verdict is not None:
                return verdict
        return True, None

    def is_model_serving(self, model_key: str) -> bool:
        """True when the model will actually return an output.

        Distinct from `is_model_available()`, which stays "the checkpoint exists" because routing
        depends on that meaning. A model can be available and not serving.
        """
        return self.serving_state(model_key)[0]

    def list_refusals(self) -> Dict[str, str]:
        """Every registered model that loads but deliberately does not serve, mapped to its reason."""
        out: Dict[str, str] = {}
        for key in self.ADAPTER_CLASSES:
            serving, reason = self.serving_state(key)
            if not serving:
                out[key] = reason or "No reason reported."
        return out

    def _resolve_load_state(
        self, adapter: BaseModelAdapter, serving: bool
    ) -> str:
        """Single source of truth for the reported lifecycle state.

        Order matters. A missing checkpoint outranks everything (there is nothing to refuse), a
        failed load outranks a refusal, and a refusal outranks LOADED — the flood segmenter really
        does hold resident weights while refusing, and reporting LOADED there is the exact overstatement
        this exists to stop.
        """
        load_state = "LOADED" if adapter.loaded else ("AVAILABLE" if adapter.available else "NOT_CONFIGURED")
        if load_state != "NOT_CONFIGURED" and not serving:
            load_state = "PRESENT_NOT_SERVING"
        if getattr(adapter, "status", None) == "FAILED":
            load_state = "FAILED"
        return load_state

    def get_model_status(self, model_key: str) -> Dict[str, Any]:
        """
        Returns runtime status for a specific model key, exposing Part 6 fields:
        model_id, name, available, loaded, status, load_state, validation_status.
        Does NOT trigger heavy weight loading.
        """
        if model_key not in self.ADAPTER_CLASSES:
            return {
                "model_key": model_key,
                "name": model_key,
                "available": False,
                "loaded": False,
                "serving": False,
                "refusal_reason": f"'{model_key}' is not a registered model.",
                "status": "NOT_CONFIGURED",
                "load_state": "NOT_CONFIGURED",
                "validation_status": "UNCONFIGURED",
                "device": "auto",
                "model_id": None
            }
        adapter = self.get_adapter(model_key)
        serving, refusal_reason = self.serving_state(model_key)
        load_state = self._resolve_load_state(adapter, serving)

        val_status = "VERIFIED" if self._verified_models.get(model_key, False) else "PENDING_VERIFICATION"
        if load_state == "NOT_CONFIGURED":
            val_status = "UNCONFIGURED"
        elif load_state == "PRESENT_NOT_SERVING":
            # Not "pending": while the adapter refuses there is no inference to verify, so a
            # PENDING_VERIFICATION here would read as "verification is on its way".
            val_status = "NOT_APPLICABLE"

        return {
            "model_key": model_key,
            "name": adapter.name,
            "available": adapter.available,
            "loaded": adapter.loaded,
            "serving": serving,
            "refusal_reason": refusal_reason,
            "status": load_state,
            "load_state": load_state,
            "validation_status": val_status,
            "device": str(adapter.device),
            "model_id": getattr(adapter, "model_id", None)
        }

    def list_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns a mapping of all registered models and their live runtime statuses."""
        return {key: self.get_model_status(key) for key in self.ADAPTER_CLASSES}

    def list_capabilities(self) -> List[ModelCapabilityInfo]:
        """
        Returns comprehensive capability metadata and live runtime availability for all models.
        Strictly conforms to Part 6 and Part 50 specifications.
        Never reports READY/VERIFIED unless actual load/inference has been verified.
        Guarantees lazy evaluation without loading heavy weights.
        """
        capabilities: List[ModelCapabilityInfo] = []
        for key, spec in settings.models.items():
            if key not in self.ADAPTER_CLASSES:
                # If configured in yaml but not registered in adapter classes (e.g. general RS VLM pending or unconfigured)
                capabilities.append(ModelCapabilityInfo(
                    model_id=getattr(spec, "model_id", None) or key,
                    name=spec.name,
                    family=None,
                    version=spec.version,
                    task=spec.task,
                    capabilities=spec.supported_tasks,
                    supported_tasks=spec.supported_tasks,
                    supported_modalities=spec.supported_modalities,
                    input_count=spec.input_count,
                    input_relationship=spec.input_relationship,
                    adapter=None,
                    checkpoint=spec.checkpoint_path,
                    checkpoint_path=spec.checkpoint_path,
                    available=False,
                    availability=False,
                    loaded=False,
                    serving=False,
                    refusal_reason=f"'{key}' is configured in configs/models.yaml but no adapter is registered for it.",
                    load_state="NOT_CONFIGURED",
                    status="NOT_CONFIGURED",
                    validation_status="NOT_CONFIGURED",
                    device="auto",
                    precision=spec.precision
                ))
                continue

            adapter = self.get_adapter(key)
            avail = bool(adapter.available)
            loaded = bool(adapter.loaded)
            dev = str(adapter.device) if adapter else (spec.device or "auto")
            m_id = getattr(adapter, "model_id", None) or getattr(spec, "model_id", None)
            serving, refusal_reason = self.serving_state(key)
            load_state = self._resolve_load_state(adapter, serving)

            meta = self.MODEL_METADATA.get(key, {})
            val_status = "VERIFIED" if self._verified_models.get(key, False) else "PENDING_VERIFICATION"
            if load_state == "NOT_CONFIGURED":
                val_status = "NOT_CONFIGURED"
            elif load_state == "PRESENT_NOT_SERVING":
                val_status = "NOT_APPLICABLE"

            info = ModelCapabilityInfo(
                model_id=m_id or key,
                name=spec.name,
                family=meta.get("family"),
                version=spec.version,
                task=spec.task,
                capabilities=meta.get("capabilities", spec.supported_tasks),
                supported_tasks=spec.supported_tasks,
                supported_modalities=spec.supported_modalities,
                input_count=spec.input_count,
                input_relationship=spec.input_relationship,
                adapter=adapter.__class__.__name__,
                checkpoint=spec.checkpoint_path,
                checkpoint_path=spec.checkpoint_path,
                source=meta.get("source"),
                license=meta.get("license"),
                input_requirements=meta.get("input_requirements", {}),
                output_schema=meta.get("output_schema", {}),
                device_requirements=meta.get("device_requirements", {}),
                lazy_load=True,
                availability=avail,
                available=avail,
                load_state=load_state,
                loaded=loaded,
                serving=serving,
                refusal_reason=refusal_reason,
                validation_status=val_status,
                last_error=getattr(adapter, "last_error", None),
                latency=getattr(adapter, "last_latency", None),
                memory=getattr(adapter, "memory_mb", None),
                device=dev,
                precision=spec.precision,
                status=load_state
            )
            capabilities.append(info)

        # Explicitly represent V4 query-aware spatial/heuristic reasoning module (non-neural algorithmic strategy)
        capabilities.append(ModelCapabilityInfo(
            model_id="v4_spatial_reasoner",
            name="V4 reasoning",
            family="Heuristic Spatial Reasoner",
            version="4.0",
            task="grounding_reasoning",
            capabilities=["spatial_grounding_reasoning", "referral_ranking", "relational_filtering"],
            supported_tasks=["spatial_grounding_reasoning", "referral_ranking", "relational_filtering"],
            supported_modalities=["optical_rgb"],
            input_count=1,
            input_relationship="single",
            adapter="GroundingReasonerV4",
            checkpoint=None,
            checkpoint_path=None,
            source="internal",
            license="Proprietary",
            input_requirements={"boxes": "List[[x1, y1, x2, y2]]", "query": "string"},
            output_schema={"selected_box": "[x1, y1, x2, y2]", "strategy": "string"},
            device_requirements={"preferred": "cpu"},
            lazy_load=False,
            availability=True,
            available=True,
            load_state="AVAILABLE",
            loaded=True,
            serving=True,
            validation_status="VERIFIED",
            device="cpu",
            precision="float32",
            status="AVAILABLE"
        ))

        return capabilities

    def release_gpu_memory(self, exclude: Tuple[str, ...] = ()) -> List[str]:
        """
        Unloads every loaded adapter except `exclude`, in place, and returns CUDA cache to the driver.

        Instances stay registered (other objects hold references to them) and reload lazily on their
        next predict. Besides the base `unload()`, any attribute holding a torch Module or a SAM 2
        predictor is cleared, because not every adapter keeps its weights in `_model` (DOFA uses
        `_dofa_model`). Used as the recovery step after a CUDA out-of-memory error: on an 8 GB GPU the
        resident models alone can leave too little headroom for ChangeFormer at native resolution.
        """
        import gc

        released: List[str] = []
        for key, adapter in self._instances.items():
            if key in exclude:
                continue
            holds_weights = bool(getattr(adapter, "_loaded", False))
            try:
                adapter.unload()
            except Exception as e:
                logger.warning(f"unload() failed for '{key}': {e}")
            for name, value in list(vars(adapter).items()):
                if isinstance(value, torch.nn.Module) or name in ("_predictor", "_video_predictor", "_dofa_model"):
                    if value is not None:
                        holds_weights = True
                    setattr(adapter, name, None)
            adapter._loaded = False
            if holds_weights:
                released.append(key)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.warning(f"Released GPU memory held by: {released or 'nothing'} (kept: {list(exclude)})")
        return released

    def unload_all(self):
        """Unloads all cached model weights from memory."""
        for adapter in self._instances.values():
            adapter.unload()
        self._instances.clear()


# Global model registry instance
model_registry = ModelRegistry()
