import pytest
import numpy as np
from PIL import Image

from backend.app.workflows.grounding import run_grounding_pipeline, GroundingWorkflow
from backend.app.models.sam2 import SAM2Result
from backend.app.agent.state import AgentState
from backend.app.schemas.agent import JobStatus, TaskType
from backend.app.schemas.responses import AnalyzeResponse


class MockGroundingDINOAdapter:
    def __init__(self, boxes=None):
        self.name = "grounding_dino"
        self.boxes = boxes if boxes is not None else [
            {"xyxy": [10.0, 10.0, 30.0, 30.0], "score": 0.88, "label": "vehicle"},
            {"xyxy": [100.0, 100.0, 150.0, 150.0], "score": 0.75, "label": "vehicle"}
        ]

    def predict(self, image_or_context, prompt, box_threshold=0.25, text_threshold=0.25):
        return {"boxes": self.boxes}


class MockSAM2Adapter:
    def __init__(self, score=0.92):
        self.name = "sam2"
        self.score = score

    def predict(self, image_or_context, box, multimask_output=True):
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[10:30, 10:30] = 1
        return SAM2Result(
            mask=mask,
            score=self.score,
            scores=[0.80, self.score, 0.65],
            pixel_count=400,
            masks=[{"binary_mask": mask, "score": self.score, "pixel_count": 400}],
            boxes=[box],
            confidence=self.score,
            answer="Mock mask",
            model_name="sam2",
            metadata={"mock": True}
        )


def test_grounding_pipeline_execution():
    img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    query = "the small vehicle on the top-left"

    result = run_grounding_pipeline(
        image=img,
        query=query,
        grounding_adapter=MockGroundingDINOAdapter(),
        sam2_adapter=MockSAM2Adapter(score=0.94)
    )

    # Verify return structure
    assert result["task"] == "grounding"
    assert "answer" in result
    assert result["selected_box"] == [10.0, 10.0, 30.0, 30.0]
    assert result["segmentation_mask"] is not None
    assert result["grounding_score"] == 0.88
    assert result["sam2_score"] == 0.94
    assert result["strategy"] == "V4_RELATIONAL"
    assert "evidence" in result
    assert "trace" in result

    # Check evidence structure
    ev = result["evidence"]
    assert ev["target_category"] == "vehicle"
    assert ev["mask_pixel_count"] == 400
    assert ev["grounding_confidence"] == 0.88
    assert ev["sam2_confidence"] == 0.94

    # Check trace steps
    trace_steps = [step["step"] for step in result["trace"]]
    assert "validate_image" in trace_steps
    assert "receive_query" in trace_steps
    assert "parse_query" in trace_steps
    assert "call_grounding_dino" in trace_steps
    assert "obtain_candidate_boxes" in trace_steps
    assert "run_grounding_reasoner" in trace_steps
    assert "select_target_candidate" in trace_steps
    assert "call_sam2" in trace_steps
    assert "receive_segmentation_mask" in trace_steps
    assert "build_visual_evidence" in trace_steps
    assert "complete_pipeline" in trace_steps


@pytest.mark.asyncio
async def test_grounding_workflow_class(tmp_path):
    # Save a test image
    img_path = tmp_path / "test_grounding.png"
    Image.new("RGB", (100, 100)).save(img_path)

    state = AgentState(
        request_id="req_grounding_test",
        query="the vehicle",
        image_paths=[str(img_path)]
    )

    workflow = GroundingWorkflow()
    # Mock adapters via monkeypatch or directly testing run_grounding_pipeline
    # Here we test run() directly
    res = workflow.run(
        image=str(img_path),
        query="the vehicle",
        grounding_adapter=MockGroundingDINOAdapter(),
        sam2_adapter=MockSAM2Adapter()
    )
    assert res["task"] == "grounding"
    assert res["strategy"] == "V4_RELATIONAL"
