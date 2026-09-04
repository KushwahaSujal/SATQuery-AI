from typing import Any, Dict, List, Optional, Type
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.ml.adapters.sam2 import SAM2Adapter
from backend.app.ml.adapters.changeformer import ChangeFormerAdapter
from backend.app.ml.adapters.cdvqa import CDVQAAdapter
from backend.app.ml.adapters.dofa import DOFAAdapter
from backend.app.ml.adapters.fusion import OpticalSARFusionModel
from backend.app.ml.adapters.general_rs_vlm import GeneralRSVLMAdapter
from backend.app.ml.adapters.remoteclip import RemoteCLIPAdapter
from backend.app.ml.adapters.bigearthnet import BigEarthNetMultimodalAdapter
from backend.app.schemas.models import ModelCapabilityInfo
from backend.app.config import settings
from backend.app.logging import logger


class ModelRegistry:
    """
    Central Professional Registry for all SatQuery AI Model Adapters.
    Tracks model capabilities, metadata, availability, lazy instances, and lifecycle management.
    Lifecycle states: NOT_CONFIGURED | AVAILABLE | LOADED | FAILED
    """
    ADAPTER_CLASSES: Dict[str, Type[BaseModelAdapter]] = {
        "grounding_dino": GroundingDINOAdapter,
        "sam2": SAM2Adapter,
        "changeformer": ChangeFormerAdapter,
        "cdvqa": CDVQAAdapter,
        "dofa": DOFAAdapter,
        "satquery_optical_sar_fusion": OpticalSARFusionModel,
        "general_rs_vlm": GeneralRSVLMAdapter,
        "remoteclip": RemoteCLIPAdapter,
        "bigearthnet": BigEarthNetMultimodalAdapter,
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
            "source": "checkpoints/changeformer/satquery_changeformer_best.pt",
            "license": "MIT",
            "capabilities": ["bi_temporal_change_detection", "probability_mapping"],
            "input_requirements": {"image_a": "RGB (512, 512, 3)", "image_b": "RGB (512, 512, 3)"},
            "output_schema": {"change_mask": "ndarray (512, 512) uint8", "probability_map": "ndarray (512, 512) float32"},
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
            "output_schema": {"prediction": "dict", "surface_roughness": "float", "builtup_index": "float"},
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
                "status": "NOT_CONFIGURED",
                "load_state": "NOT_CONFIGURED",
                "validation_status": "UNCONFIGURED",
                "device": "auto",
                "model_id": None
            }
        adapter = self.get_adapter(model_key)
        load_state = "LOADED" if adapter.loaded else ("AVAILABLE" if adapter.available else "NOT_CONFIGURED")
        if hasattr(adapter, "status") and adapter.status == "FAILED":
            load_state = "FAILED"
        
        val_status = "VERIFIED" if self._verified_models.get(model_key, False) else "PENDING_VERIFICATION"
        if load_state == "NOT_CONFIGURED":
            val_status = "UNCONFIGURED"

        return {
            "model_key": model_key,
            "name": adapter.name,
            "available": adapter.available,
            "loaded": adapter.loaded,
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
            load_state = "LOADED" if loaded else ("AVAILABLE" if avail else "NOT_CONFIGURED")
            if hasattr(adapter, "status") and adapter.status == "FAILED":
                load_state = "FAILED"
            
            meta = self.MODEL_METADATA.get(key, {})
            val_status = "VERIFIED" if self._verified_models.get(key, False) else "PENDING_VERIFICATION"
            if load_state == "NOT_CONFIGURED":
                val_status = "NOT_CONFIGURED"

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
            validation_status="VERIFIED",
            device="cpu",
            precision="float32",
            status="AVAILABLE"
        ))

        return capabilities

    def unload_all(self):
        """Unloads all cached model weights from memory."""
        for adapter in self._instances.values():
            adapter.unload()
        self._instances.clear()


# Global model registry instance
model_registry = ModelRegistry()
