"""Q-015: "mask trees" must reach SAM 2, send "trees." to the detector, and segment every instance."""
import numpy as np
import pytest
from PIL import Image

from backend.app.orchestration.intent_classifier import IntentClassifier
from backend.app.workflows.grounding import _wants_all_instances, run_grounding_pipeline
from backend.app.workflows.grounding_reasoner import parse_v4_query
from tests.models.test_grounding_workflow import AlwaysVerifies, MockGroundingDINOAdapter


@pytest.mark.parametrize("query", ["mask trees", "Mask trees in this image", "mask all the trees",
                                   "mask the buildings", "segment trees", "mark the trees"])
def test_mask_queries_route_to_grounding(query):
    assert IntentClassifier.classify_intent(query, num_inputs=1).task == "single_image_grounding"


@pytest.mark.parametrize("query,target,reference", [("mark trees near houses", "tree", "house"),
                                                     ("mark houses near trees", "house", "tree"),
                                                     ("mask houses near cars", "house", "car")])
def test_relational_target_is_the_object_before_the_relation(query, target, reference):
    e = IntentClassifier.extract_entities(query)
    assert (e.object_class, e.reference_object) == (target, reference)


def test_counting_question_still_routes_to_vqa():
    assert IntentClassifier.classify_intent("how many buildings are in this image?", num_inputs=1).task == "single_image_vqa"


@pytest.mark.parametrize("query,prompt", [("mask trees", "trees."), ("mask all the trees", "trees."),
                                          ("mask the buildings", "buildings.")])
def test_mask_verb_is_not_sent_to_the_detector(query, prompt):
    assert parse_v4_query(query)["clean_prompt"] == prompt


@pytest.mark.parametrize("query,strategy,expected", [
    ("mask trees", "detector_confidence", True),
    ("segment all buildings", "detector_confidence", True),
    ("find the largest building", "detector_confidence", False),
    ("find the red car", "multi_attribute_ranking", False),
    ("find the second ship", "ordinal_second", False),
])
def test_wants_all_instances(query, strategy, expected):
    assert _wants_all_instances(query, strategy) is expected


@pytest.mark.parametrize("query,expected", [
    ("mask houses near cars", True),
    ("mark trees near houses", True),
    ("find the largest house near the road", False),
    ("the car on the left", False),
])
def test_relational_plural_queries_keep_all_instances(query, expected):
    assert _wants_all_instances(query, "multi_attribute_ranking", parse_v4_query(query)) is expected


def test_near_uses_edge_gap_and_excludes_reference_itself():
    from backend.app.workflows.grounding import _satisfies_relation
    house, car = [100, 100, 300, 300], [305, 150, 325, 170]  # touching, centres 135 px apart
    assert _satisfies_relation(house, [car], "near", 512, 512)
    assert not _satisfies_relation([0, 0, 20, 20], [car], "near", 512, 512)
    assert not _satisfies_relation(car, [car], "near", 512, 512)


class BoxMaskSAM2:
    """Returns a mask covering exactly the prompt box, so combined masks are checkable."""

    def __init__(self):
        self.calls = 0

    def predict(self, image_or_context, box, multimask_output=True):
        self.calls += 1
        m = np.zeros((200, 200), np.uint8)
        x1, y1, x2, y2 = [int(v) for v in box]
        m[y1:y2, x1:x2] = 1
        return {"mask": m, "score": 0.9, "scores": [0.9], "pixel_count": int(m.sum())}


TREES = [
    {"xyxy": [10.0, 10.0, 30.0, 30.0], "score": 0.80, "label": "tree"},
    {"xyxy": [100.0, 100.0, 140.0, 140.0], "score": 0.70, "label": "tree"},
    {"xyxy": [150.0, 20.0, 170.0, 40.0], "score": 0.60, "label": "tree"},
]


def test_mask_trees_segments_every_detected_tree():
    sam2 = BoxMaskSAM2()
    res = run_grounding_pipeline(Image.new("RGB", (200, 200)), "mask trees",
                                 grounding_adapter=MockGroundingDINOAdapter(TREES), sam2_adapter=sam2,
                                 verifier=AlwaysVerifies())
    assert res["evidence"]["instance_count"] == 3
    assert len(res["instance_boxes"]) == 3
    assert int(res["segmentation_mask"].sum()) == 20 * 20 + 40 * 40 + 20 * 20
    assert res["answer"].startswith("Segmented 3 instances of tree")


def test_single_target_query_keeps_one_mask():
    res = run_grounding_pipeline(Image.new("RGB", (200, 200)), "find the largest tree",
                                 grounding_adapter=MockGroundingDINOAdapter(TREES), sam2_adapter=BoxMaskSAM2(),
                                 verifier=AlwaysVerifies())
    assert res["evidence"]["instance_count"] == 1
    assert len(res["instance_boxes"]) == 1


class ColouredScene:
    """Two white and two dark 'houses' on a green lawn; each mock box -> a mask exactly covering it."""
    WHITE = [[10.0, 10.0, 50.0, 50.0], [120.0, 10.0, 160.0, 50.0]]
    DARK = [[10.0, 120.0, 50.0, 160.0], [120.0, 120.0, 160.0, 160.0]]

    @classmethod
    def image(cls):
        arr = np.zeros((200, 200, 3), np.uint8)
        arr[:] = (40, 120, 40)
        for b in cls.WHITE:
            arr[int(b[1]):int(b[3]), int(b[0]):int(b[2])] = (235, 235, 235)
        for b in cls.DARK:
            arr[int(b[1]):int(b[3]), int(b[0]):int(b[2])] = (60, 60, 60)
        return Image.fromarray(arr)

    @classmethod
    def boxes(cls):
        # dark houses score higher, so the detector's top pick is the wrong colour
        return ([{"xyxy": b, "score": 0.9, "label": "house"} for b in cls.DARK]
                + [{"xyxy": b, "score": 0.5, "label": "house"} for b in cls.WHITE])


def test_colour_is_checked_on_every_instance_including_the_top_one():
    res = run_grounding_pipeline(ColouredScene.image(), "mask white houses",
                                 grounding_adapter=MockGroundingDINOAdapter(ColouredScene.boxes()),
                                 sam2_adapter=BoxMaskSAM2(), verifier=AlwaysVerifies())
    assert sorted(res["instance_boxes"]) == sorted(ColouredScene.WHITE)
    assert int(res["segmentation_mask"].sum()) == 2 * 40 * 40
    assert res["evidence"]["instance_filters"]["dropped_by_color"] == 2
    assert "top-ranked box did not satisfy" in res["answer"]


def test_no_matching_colour_keeps_top_candidate_and_says_so():
    boxes = [{"xyxy": b, "score": 0.9, "label": "house"} for b in ColouredScene.DARK]
    res = run_grounding_pipeline(ColouredScene.image(), "mask white houses",
                                 grounding_adapter=MockGroundingDINOAdapter(boxes),
                                 sam2_adapter=BoxMaskSAM2(), verifier=AlwaysVerifies())
    assert res["evidence"]["instance_count"] == 1
    assert res["answer"].startswith("No instance satisfied every condition")
