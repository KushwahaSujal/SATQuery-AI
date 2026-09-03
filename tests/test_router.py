from backend.app.agent.router import DeterministicRouter
from backend.app.schemas.agent import TaskType
from backend.app.geo.metadata import RasterMetadata


def test_route_single_vqa():
    task, wid, reason, models = DeterministicRouter.classify_and_route(
        query="Describe the land-cover and major objects visible in this image.",
        num_images=1,
        modalities=["optical"],
        metadata_list=[]
    )
    assert task == TaskType.SINGLE_IMAGE_VQA
    assert "general_rs_vlm" in models


def test_route_single_grounding():
    task, wid, reason, models = DeterministicRouter.classify_and_route(
        query="Highlight the water body and solar panels.",
        num_images=1,
        modalities=["optical"],
        metadata_list=[]
    )
    assert task == TaskType.SINGLE_IMAGE_GROUNDING
    assert "grounding_dino" in models


def test_route_temporal_change():
    task, wid, reason, models = DeterministicRouter.classify_and_route(
        query="What changed between these two dates? Has the built-up area increased?",
        num_images=2,
        modalities=["optical", "optical"],
        metadata_list=[]
    )
    assert task == TaskType.BI_TEMPORAL_CHANGE_VQA
    assert "changeformer" in models


def test_route_optical_sar():
    task, wid, reason, models = DeterministicRouter.classify_and_route(
        query="Use both images to identify built-up and water-covered regions.",
        num_images=2,
        modalities=["optical", "sar"],
        metadata_list=[]
    )
    assert task == TaskType.OPTICAL_SAR_ANALYSIS
    assert "dofa" in models


def test_route_grounding_localization_intents():
    queries = [
        "highlight the runway",
        "locate the solar panels",
        "find the largest aircraft",
        "where is the storage tank",
        "identify the object at the corner",
        "show me the sports field",
        "point out the cargo vessel",
        "which vehicle is parked near the building",
        "which ship is docked at the pier",
        "which harbor is located along the coast"
    ]
    for q in queries:
        task, wid, reason, models = DeterministicRouter.classify_and_route(
            query=q,
            num_images=1,
            modalities=["optical"],
            metadata_list=[]
        )
        assert task == TaskType.SINGLE_IMAGE_GROUNDING, f"Query failed to route to grounding: '{q}' (got {task})"
        assert wid == "workflow_grounding"
        assert "grounding_dino" in models
        assert "sam2" in models


def test_temporal_change_queries_not_routed_to_grounding():
    queries = [
        "What changed between these images? Locate any new houses.",
        "Highlight the difference in built-up area between before and after.",
        "Has deforestation expansion occurred here?",
        "Where is the damage or destroyed structure after the disaster?",
        "What was changed in this area?"
    ]
    for q in queries:
        task, wid, reason, models = DeterministicRouter.classify_and_route(
            query=q,
            num_images=1,
            modalities=["optical"],
            metadata_list=[]
        )
        assert task != TaskType.SINGLE_IMAGE_GROUNDING, f"Temporal change query incorrectly routed to grounding: '{q}'"
        assert task in (TaskType.SINGLE_IMAGE_VQA, TaskType.BI_TEMPORAL_CHANGE, TaskType.BI_TEMPORAL_CHANGE_VQA)
