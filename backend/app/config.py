import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


def _get_project_root() -> Path:
    # satquery-ai/backend/app/config.py -> satquery-ai/
    return Path(__file__).resolve().parent.parent.parent


try:
    from dotenv import load_dotenv
    _env_file = _get_project_root() / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass


class AppSettings(BaseModel):
    name: str = "SatQuery AI"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


class StorageSettings(BaseModel):
    results_dir: str = "results"
    max_upload_size_mb: int = 500
    allowed_extensions: List[str] = [".tif", ".tiff", ".png", ".jpg", ".jpeg"]


class TilingSettings(BaseModel):
    tile_size: int = 512
    overlap: int = 64
    max_dimension_no_tile: int = 2048


class DisplaySettings(BaseModel):
    percentile_min: float = 2.0
    percentile_max: float = 98.0
    preview_max_dim: int = 1024


class CoRegistrationSettings(BaseModel):
    max_resolution_diff_ratio: float = 0.1
    min_bounds_iou: float = 0.8


class GeospatialSettings(BaseModel):
    tiling: TilingSettings = Field(default_factory=TilingSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    co_registration: CoRegistrationSettings = Field(default_factory=CoRegistrationSettings)
    metric_projection_fallback: str = "EPSG:3857"


class DeviceSettings(BaseModel):
    preferred: str = "auto"
    fallback: str = "cpu"
    allow_cpu_for_heavy_models: bool = True


class ConcurrencySettings(BaseModel):
    gpu_lock_timeout_seconds: int = 120


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://satquery:satquery@localhost:5432/satquery"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


class VideoSamplingSettings(BaseModel):
    # 1.0 quantised event boundaries to +/-1s, which showed up as timestamps a few
    # seconds off the true appearance (project/pre-demo.md 3g).
    sample_fps: float = 2.0
    max_frames: int = 120
    analysis_stride: int = 1
    event_refinement_window: int = 3


class VideoEventScoringSettings(BaseModel):
    detector_weight: float = 0.4
    reasoning_weight: float = 0.3
    segmentation_weight: float = 0.2
    persistence_weight: float = 0.1

    def validate_weights(self) -> None:
        total = self.detector_weight + self.reasoning_weight + self.segmentation_weight + self.persistence_weight
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Video event scoring weights must sum to 1.0, got {total:.4f}")


class VideoFlagSettings(BaseModel):
    min_persistence_frames: int = 2
    min_persistence_seconds: float = 0.5
    max_gap_frames: int = 2
    max_gap_seconds: float = 1.5
    min_event_score: float = 0.20
    # Measured on real_aerial_footage.mp4: real vehicles score 0.67-0.89, while a
    # parking-line marking and a full-frame box both scored 0.28 (3g).
    min_detector_score: float = 0.35
    # A box covering nearly the whole frame is not an object detection.
    max_box_area_ratio: float = 0.90


class VideoSettings(BaseModel):
    allowed_extensions: List[str] = [".mp4", ".mov"]
    max_video_size_mb: int = 500
    sampling: VideoSamplingSettings = Field(default_factory=VideoSamplingSettings)
    event_scoring: VideoEventScoringSettings = Field(default_factory=VideoEventScoringSettings)
    flagging: VideoFlagSettings = Field(default_factory=VideoFlagSettings)


class VisualizationSettings(BaseModel):
    default_percentile_min: float = 2.0
    default_percentile_max: float = 98.0
    colormap: str = "turbo"
    export_formats: List[str] = Field(default_factory=lambda: ["png", "geotiff", "geojson", "pdf"])
    supported_indices: List[str] = Field(default_factory=lambda: ["NDVI", "NDWI", "NDBI"])


class ModelSpec(BaseModel):
    name: str
    version: Optional[str] = None
    task: str
    supported_tasks: List[str] = Field(default_factory=list)
    supported_modalities: List[str] = Field(default_factory=list)
    input_count: int = 1
    input_relationship: str = "single"  # single | temporal | cross_modal
    enabled: bool = True
    checkpoint_path: Optional[str] = None
    lora_adapter_path: Optional[str] = None
    config_path: Optional[str] = None
    device: str = "auto"
    precision: str = "float16"
    box_threshold: Optional[float] = None
    text_threshold: Optional[float] = None
    threshold: Optional[float] = None
    input_size: Optional[int] = None
    model_id: Optional[str] = None


class Config:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or _get_project_root()
        self.configs_dir = self.root_dir / "configs"
        
        self.app = self._load_app_config()
        self.storage = self._load_storage_config()
        self.geospatial = self._load_geo_config()
        self.device = self._load_device_config()
        self.concurrency = self._load_concurrency_config()
        self.database = self._load_database_config()
        self.video = self._load_video_config()
        self.visualization = self._load_visualization_config()
        self.models: Dict[str, ModelSpec] = self._load_models_config()
        self.workflows: Dict[str, Any] = self._load_workflows_config()
        self._apply_env_overrides()

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = self.configs_dir / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data or {}
        return {}

    def _load_visualization_config(self) -> VisualizationSettings:
        raw = self._load_yaml("app.yaml").get("visualization", {})
        return VisualizationSettings(**raw) if raw else VisualizationSettings()

    def _load_app_config(self) -> AppSettings:
        raw = self._load_yaml("app.yaml").get("app", {})
        return AppSettings(**raw) if raw else AppSettings()

    def _load_storage_config(self) -> StorageSettings:
        raw = self._load_yaml("app.yaml").get("storage", {})
        return StorageSettings(**raw) if raw else StorageSettings()

    def _load_geo_config(self) -> GeospatialSettings:
        raw = self._load_yaml("app.yaml").get("geospatial", {})
        return GeospatialSettings(**raw) if raw else GeospatialSettings()

    def _load_device_config(self) -> DeviceSettings:
        raw = self._load_yaml("models.yaml").get("device", {})
        return DeviceSettings(**raw) if raw else DeviceSettings()

    def _load_concurrency_config(self) -> ConcurrencySettings:
        raw = self._load_yaml("models.yaml").get("concurrency", {})
        return ConcurrencySettings(**raw) if raw else ConcurrencySettings()

    def _load_database_config(self) -> DatabaseSettings:
        raw = self._load_yaml("app.yaml").get("database", {})
        return DatabaseSettings(**raw) if raw else DatabaseSettings()

    def _load_video_config(self) -> VideoSettings:
        raw = self._load_yaml("app.yaml").get("video", {})
        cfg = VideoSettings(**raw) if raw else VideoSettings()
        cfg.event_scoring.validate_weights()
        return cfg

    def _load_models_config(self) -> Dict[str, ModelSpec]:
        raw_models = self._load_yaml("models.yaml").get("models", {})
        res = {}
        for k, v in raw_models.items():
            res[k] = ModelSpec(**v)
        return res

    def _load_workflows_config(self) -> Dict[str, Any]:
        return self._load_yaml("workflows.yaml")

    def _apply_env_overrides(self):
        if os.getenv("SATQUERY_ENV"):
            self.app.environment = os.getenv("SATQUERY_ENV")
        if os.getenv("SATQUERY_DEBUG"):
            self.app.debug = os.getenv("SATQUERY_DEBUG").lower() in ("true", "1")
        if os.getenv("SATQUERY_DEVICE"):
            self.device.preferred = os.getenv("SATQUERY_DEVICE")
        if os.getenv("SATQUERY_RESULTS_DIR"):
            self.storage.results_dir = os.getenv("SATQUERY_RESULTS_DIR")
        if os.getenv("SATQUERY_MAX_UPLOAD_MB"):
            self.storage.max_upload_size_mb = int(os.getenv("SATQUERY_MAX_UPLOAD_MB"))

        # Database overrides
        if os.getenv("DATABASE_URL"):
            self.database.url = os.getenv("DATABASE_URL")
        elif os.getenv("POSTGRES_USER") or os.getenv("POSTGRES_PASSWORD") or os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_DB"):
            u = os.getenv("POSTGRES_USER", "satquery")
            p = os.getenv("POSTGRES_PASSWORD", "satquery")
            h = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            db = os.getenv("POSTGRES_DB", "satquery")
            self.database.url = f"postgresql+asyncpg://{u}:{p}@{h}:{port}/{db}"

        # Specific model overrides
        if "general_rs_vlm" in self.models and os.getenv("GENERAL_RS_VLM_CHECKPOINT"):
            self.models["general_rs_vlm"].checkpoint_path = os.getenv("GENERAL_RS_VLM_CHECKPOINT")
        if "grounding_dino" in self.models and os.getenv("GROUNDING_DINO_CHECKPOINT"):
            self.models["grounding_dino"].checkpoint_path = os.getenv("GROUNDING_DINO_CHECKPOINT")
        if "grounding_dino" in self.models and os.getenv("GROUNDING_DINO_CONFIG"):
            self.models["grounding_dino"].config_path = os.getenv("GROUNDING_DINO_CONFIG")
        if "sam2" in self.models and os.getenv("SAM2_CHECKPOINT"):
            self.models["sam2"].checkpoint_path = os.getenv("SAM2_CHECKPOINT")
        if "sam2" in self.models and os.getenv("SAM2_CONFIG"):
            self.models["sam2"].config_path = os.getenv("SAM2_CONFIG")
        if "changeformer" in self.models and os.getenv("CHANGEFORMER_CHECKPOINT"):
            self.models["changeformer"].checkpoint_path = os.getenv("CHANGEFORMER_CHECKPOINT")
        if "cdvqa" in self.models and os.getenv("CDVQA_CHECKPOINT"):
            self.models["cdvqa"].checkpoint_path = os.getenv("CDVQA_CHECKPOINT")
        if "dofa" in self.models and os.getenv("DOFA_CHECKPOINT"):
            self.models["dofa"].checkpoint_path = os.getenv("DOFA_CHECKPOINT")
        if "satquery_optical_sar_fusion" in self.models and os.getenv("OPTICAL_SAR_FUSION_CHECKPOINT"):
            self.models["satquery_optical_sar_fusion"].checkpoint_path = os.getenv("OPTICAL_SAR_FUSION_CHECKPOINT")
        if "remoteclip" in self.models and os.getenv("REMOTECLIP_CHECKPOINT"):
            self.models["remoteclip"].checkpoint_path = os.getenv("REMOTECLIP_CHECKPOINT")


# Global singleton
settings = Config()
