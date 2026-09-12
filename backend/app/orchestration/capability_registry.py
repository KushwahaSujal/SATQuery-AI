"""
SatQuery AI — Capability Registry
Maintains formal capability definitions, accepted inputs, required modalities,
required models, tool dependencies, and execution priority.
"""
from typing import Dict, List, Optional
from backend.app.orchestration.schemas import CapabilityDefinition, CapabilityPriority
from backend.app.logging import logger


class CapabilityRegistry:
    """
    Central authoritative registry for all agent capabilities.
    Allows dynamic lookup, dependency validation, and capability negotiation.
    """
    def __init__(self):
        self._capabilities: Dict[str, CapabilityDefinition] = {}
        self._register_default_capabilities()

    def register(self, cap: CapabilityDefinition) -> None:
        self._capabilities[cap.capability_id] = cap

    def get(self, capability_id: str) -> Optional[CapabilityDefinition]:
        return self._capabilities.get(capability_id)

    def list_all(self) -> List[CapabilityDefinition]:
        return sorted(list(self._capabilities.values()), key=lambda c: c.priority, reverse=True)

    def list_enabled(self) -> List[CapabilityDefinition]:
        return [c for c in self.list_all() if c.enabled]

    def _register_default_capabilities(self) -> None:
        defaults = [
            CapabilityDefinition(
                capability_id="single_image_grounding",
                name="Single-Image Spatial Grounding & Segmentation",
                description="Grounds user referral queries to open-vocabulary bounding boxes and generates pixel-precise segmentation masks using Grounding DINO, V4 reasoner, and SAM 2.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral"],
                output_types=["boxes", "masks", "overlays", "geojson", "report"],
                required_models=["grounding_dino", "sam2"],
                optional_models=["remoteclip"],
                required_tools=["inspect_raster", "validate_single_image", "run_grounding", "run_segmentation", "generate_overlay", "generate_report"],
                workflow="workflow_grounding",
                priority=CapabilityPriority.GROUNDING,
                validation_requirements={"min_images": 1, "max_images": 1}
            ),
            CapabilityDefinition(
                capability_id="temporal_change_vqa",
                name="Bi-Temporal Change Visual Question Answering",
                description="Performs cross-temporal change detection combined with categorical question answering over paired pre/post satellite scenes.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral"],
                output_types=["answer", "masks", "probability_map", "statistics", "overlays", "geojson", "report"],
                required_models=["changeformer", "cdvqa"],
                required_tools=["inspect_raster", "validate_temporal_pair", "run_change_detection", "calculate_statistics", "run_change_vqa", "generate_overlay", "generate_report"],
                workflow="workflow_temporal_change_vqa",
                priority=CapabilityPriority.TEMPORAL_CHANGE_VQA,
                validation_requirements={"min_images": 2, "max_images": 2, "require_co_registration": True}
            ),
            CapabilityDefinition(
                capability_id="temporal_change_detection",
                name="Bi-Temporal Change Mapping & Metric Area Calculation",
                description="Quantifies pixel and geographical square area changes between two temporal epochs using ChangeFormerV6.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral"],
                output_types=["masks", "probability_map", "statistics", "overlays", "geojson", "report"],
                required_models=["changeformer"],
                required_tools=["inspect_raster", "validate_temporal_pair", "run_change_detection", "calculate_statistics", "generate_overlay", "generate_report"],
                workflow="workflow_temporal_change",
                priority=CapabilityPriority.TEMPORAL_CHANGE,
                validation_requirements={"min_images": 2, "max_images": 2, "require_co_registration": True}
            ),
            CapabilityDefinition(
                capability_id="optical_sar_analysis",
                name="Optical-SAR Cross-Modal Fusion Analysis",
                description="Fuses co-registered Optical and Synthetic Aperture Radar (SAR) imagery for all-weather infrastructure and land cover analysis.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "sar"],
                output_types=["features", "classification", "report"],
                required_models=["dofa", "satquery_optical_sar_fusion"],
                required_tools=["inspect_raster", "validate_optical_sar_pair", "run_optical_sar", "generate_report"],
                workflow="workflow_optical_sar",
                priority=CapabilityPriority.OPTICAL_SAR,
                validation_requirements={"min_images": 2, "max_images": 2, "require_one_sar": True}
            ),
            CapabilityDefinition(
                capability_id="video_grounding_tracking",
                name="Video Aerial Surveillance Grounding & Tracking",
                description="Identifies and tracks spatial objects across aerial video footage, flagging key temporal event intervals.",
                accepted_input_types=["video/mp4", "video/avi", "video/quicktime", "video/x-matroska"],
                required_modalities=["video"],
                output_types=["video_flags", "keyframes", "boxes", "report"],
                required_models=["grounding_dino", "sam2"],
                required_tools=["inspect_video", "sample_keyframes", "run_video_detection", "cluster_events", "generate_video_artifacts"],
                workflow="workflow_video_grounding_tracking",
                priority=CapabilityPriority.VIDEO,
                validation_requirements={"min_duration_sec": 1.0}
            ),
            CapabilityDefinition(
                capability_id="video_grounding",
                name="Video Keyframe Event Grounding",
                description="Extracts candidate frames from video footage and localizes queried objects.",
                accepted_input_types=["video/mp4", "video/avi", "video/quicktime", "video/x-matroska"],
                required_modalities=["video"],
                output_types=["video_flags", "keyframes", "boxes"],
                required_models=["grounding_dino"],
                required_tools=["inspect_video", "sample_keyframes", "run_video_detection", "cluster_events"],
                workflow="workflow_video_grounding",
                priority=CapabilityPriority.VIDEO,
                validation_requirements={"min_duration_sec": 1.0}
            ),
            CapabilityDefinition(
                capability_id="multispectral_analysis",
                name="Multispectral Band & Index Analysis",
                description="Calculates normalized spectral indices (NDVI, NDWI, NDBI) and renders false-color composite layers from multi-band imagery.",
                accepted_input_types=["image/tiff", "image/x-tiff"],
                required_modalities=["multispectral"],
                output_types=["index_map", "composite", "legend", "histogram"],
                required_models=[],
                required_tools=["inspect_raster", "compute_spectral_indices", "render_composites"],
                workflow="workflow_multispectral",
                priority=CapabilityPriority.MULTISPECTRAL,
                validation_requirements={"min_bands": 4}
            ),
            CapabilityDefinition(
                capability_id="sar_analysis",
                name="SAR Polarimetric Analysis",
                description="Processes Synthetic Aperture Radar polarizations (VV, VH) with calibrated decibel conversion and ratio composites.",
                accepted_input_types=["image/tiff", "image/x-tiff"],
                required_modalities=["sar"],
                output_types=["polarization_layer", "db_layer", "legend", "histogram"],
                required_models=[],
                required_tools=["inspect_raster", "render_sar_polarization"],
                workflow="workflow_sar",
                priority=CapabilityPriority.SAR,
                validation_requirements={"min_bands": 1}
            ),
            CapabilityDefinition(
                capability_id="single_image_vqa",
                name="Single-Image Remote-Sensing VQA",
                description="Answers free-form natural language questions about land cover, scene composition, and visual features using General RS VLM.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral"],
                output_types=["answer", "report"],
                required_models=["general_rs_vlm"],
                required_tools=["inspect_raster", "validate_single_image", "run_vqa", "generate_report"],
                workflow="workflow_single_vqa",
                priority=CapabilityPriority.VQA,
                validation_requirements={"min_images": 1, "max_images": 1}
            ),
            CapabilityDefinition(
                capability_id="single_image_caption",
                name="Single-Image Scene Captioning",
                description="Generates descriptive scene summaries for satellite and aerial imagery using General RS VLM.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral"],
                output_types=["caption", "report"],
                required_models=["general_rs_vlm"],
                required_tools=["inspect_raster", "validate_single_image", "run_caption", "generate_report"],
                workflow="workflow_caption",
                priority=CapabilityPriority.CAPTION,
                validation_requirements={"min_images": 1, "max_images": 1}
            ),
            CapabilityDefinition(
                capability_id="visualization",
                name="Scientific Raster & Layer Visualization",
                description="Generates scientific false color, true color, heatmap, and split-screen comparison visual layers.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral", "sar"],
                output_types=["rendered_layer", "legend", "histogram"],
                required_models=[],
                required_tools=["render_layer", "generate_legend", "compute_histogram"],
                workflow="workflow_visualization",
                priority=CapabilityPriority.VISUALIZATION
            ),
            CapabilityDefinition(
                capability_id="pixel_inspection",
                name="Exact Pixel Inspector",
                description="Inspects exact digital numbers, geographical map coordinates, derived index values, and model state for queried pixels.",
                accepted_input_types=["image/png", "image/jpeg", "image/tiff"],
                required_modalities=["optical", "multispectral", "sar"],
                output_types=["pixel_telemetry"],
                required_models=[],
                required_tools=["inspect_pixel"],
                workflow="workflow_pixel_inspection",
                priority=CapabilityPriority.PIXEL_INSPECTION
            ),
            CapabilityDefinition(
                capability_id="report_generation",
                name="Scientific Evidence & Audit PDF Report Generation",
                description="Compiles structured provenance, telemetry, model metadata, and visual figures into an immutable PDF report.",
                accepted_input_types=["application/json"],
                required_modalities=[],
                output_types=["report_pdf"],
                required_models=[],
                required_tools=["generate_report"],
                workflow="workflow_report_generation",
                priority=CapabilityPriority.REPORT_GENERATION
            ),
        ]
        for c in defaults:
            self.register(c)
        self._validate_all()
        logger.info(f"CapabilityRegistry initialized with {len(self._capabilities)} capabilities.")

    def _validate_all(self) -> None:
        """
        Fails loudly at import time if a capability declares a tool that is not
        registered, or has no DAG branch.

        Previously neither was checked: DependencyChecker validates the tools on
        the *DAG nodes*, not `required_tools`, and a capability with no DAG branch
        silently fell through to a trivial inspect->report plan. That is how
        multispectral_analysis and sar_analysis came to route successfully and then
        do nothing (project/decisions.md D-104, D-105).
        """
        from backend.app.agent.tools import TOOL_REGISTRY
        from backend.app.orchestration.dependency_graph import DependencyGraph

        unknown_tools: dict = {}
        without_dag: list = []
        for cap in self._capabilities.values():
            missing = sorted({t for t in cap.required_tools if t not in TOOL_REGISTRY})
            if missing:
                unknown_tools[cap.capability_id] = missing
            if not DependencyGraph.has_branch_for(cap.capability_id):
                without_dag.append(cap.capability_id)

        # Warn rather than raise: some of these capabilities are reachable through
        # their own endpoint rather than the agent DAG (video_* runs via
        # /api/video/analyze -> VideoAnalysisWorkflow), and hard-failing at import
        # would take down capabilities that do work. The point is that the gap is
        # now visible on every boot instead of invisible forever.
        for cap_id, missing in sorted(unknown_tools.items()):
            logger.warning(
                f"Capability '{cap_id}' declares tools with no implementation: {missing}. "
                f"It cannot be executed by the agent DAG."
            )
        if without_dag:
            logger.warning(
                "Capabilities with no DAG branch fall back to a trivial "
                f"inspect_raster -> generate_report plan and produce no real output: "
                f"{sorted(without_dag)}"
            )
        if unknown_tools or without_dag:
            logger.warning(
                f"Capability health: {len(self._capabilities) - len(set(unknown_tools) | set(without_dag))}"
                f"/{len(self._capabilities)} capabilities are fully agent-executable. "
                f"See project/decisions.md D-104 and D-105."
            )


capability_registry = CapabilityRegistry()
