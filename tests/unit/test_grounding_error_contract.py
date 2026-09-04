
import pytest
from backend.app.workflows.grounding_reasoner import parse_v4_query
from backend.app.agent.state import AgentState
from backend.app.agent.tools import inference as tools_inference
from backend.app.exceptions import SatQueryException, InferenceError


def test_parse_v4_query_directive_stripping():
    q = "Highlight the small red vehicle located at the bottom middle of the image."
    parsed = parse_v4_query(q)
    assert parsed["category"] == "vehicle"
    assert parsed["clean_prompt"] == "vehicle."
    assert parsed["position"] == "bottom-middle"
    assert parsed["size"] == "small"
    assert parsed["color"] == "red"


def test_run_segmentation_with_empty_boxes():
    state = AgentState(
        request_id="test_empty_boxes",
        query="Highlight the car",
        image_paths=["datasets/samples/real_pair/real_image_a.png"]
    )
    # Ensure no bounding boxes are present
    state.evidence.spatial.boxes = []
    state.evidence.spatial.has_mask = False
    
    # ToolRegistry.run_segmentation should gracefully return without raising InvalidInputError
    tools_inference.run_segmentation(state)
    assert not state.evidence.spatial.has_mask


def test_satquery_exception_to_dict_contract():
    exc = InferenceError(
        message="Model inference failure",
        model_name="grounding_dino",
        details={"workflow": "grounding"}
    )
    d = exc.to_dict()
    assert "error" in d
    assert d["error"]["code"] == "MODEL_INFERENCE_ERROR"
    assert d["error"]["workflow"] == "grounding"
    assert d["error"]["message"] == "Model inference failure"
