"""Dispatch-only tests for routing plain "mark all roads" / "segment buildings" style queries to
the trained U-Net segmenters (project/qna.md Q-025t, Q-026t, Q-038).

No checkpoints and no model I/O: `classify_trained_segmenter_target` is a pure function of the
parsed query, `_wants_all_instances`'s existing category-vs-single-target signal, and the
`trained_segmenter_routing.enabled` setting. `run_trained_segmenter_path` (the execution side, which
does load a checkpoint) is exercised for real in tests/models/test_grounding_trained_segmenter.py.
"""
import pytest

from backend.app.config import settings
from backend.app.workflows.grounding import _wants_all_instances
from backend.app.workflows.grounding_reasoner import parse_v4_query
from backend.app.workflows.trained_segmenter import classify_trained_segmenter_target


def classify(query: str):
    """Mirrors exactly what run_grounding_pipeline does before candidate detection."""
    parsed = parse_v4_query(query)
    wants_all = _wants_all_instances(query, "", parsed)
    return classify_trained_segmenter_target(query, parsed, wants_all)


@pytest.mark.parametrize("query,expected", [
    ("mark all roads", "roads_segmenter"),
    ("segment buildings", "buildings_segmenter"),
    ("mask all the buildings", "buildings_segmenter"),
    ("find every road", "roads_segmenter"),
    ("show me the streets", "roads_segmenter"),
])
def test_plain_category_requests_route_to_the_trained_segmenter(query, expected):
    assert classify(query) == expected


@pytest.mark.parametrize("query", [
    "mark the largest building",       # ordinal/size qualifier
    "find the road near the school",   # relational qualifier
    "mask red cars",                   # wrong class entirely
    "mask red buildings",              # colour qualifier on a supported class
    "segment the road on the left",    # position qualifier
    "the second building from the left",  # ordinal qualifier
    "find a plane",                    # unsupported class, singular
    "find water bodies",               # unsupported class, plural
    "roads and buildings",             # multiple classes in one query
])
def test_qualified_or_unsupported_queries_fall_back_to_the_existing_pipeline(query):
    assert classify(query) is None


def test_relational_and_colour_qualifiers_are_rejected_even_if_wants_all_instances_is_true():
    """`_wants_all_instances` itself does not look at `relation` or `color` — the extra checks in
    `classify_trained_segmenter_target` are what block these, not a lucky wording of the query."""
    parsed_relation = {"category": "roads", "relation": "near", "reference_category": "school"}
    assert classify_trained_segmenter_target("roads near the school", parsed_relation, True) is None

    parsed_color = {"category": "buildings", "color": "red"}
    assert classify_trained_segmenter_target("red buildings", parsed_color, True) is None


def test_no_recognised_vocabulary_falls_back():
    parsed = {"category": "cars"}
    assert classify_trained_segmenter_target("mark all cars", parsed, True) is None


def test_multiple_classes_in_one_query_falls_back():
    parsed = {"category": "roads buildings"}
    assert classify_trained_segmenter_target("mark all roads buildings", parsed, True) is None


def test_wants_all_instances_false_always_falls_back_regardless_of_vocabulary():
    parsed = {"category": "roads", "size": "large"}
    assert classify_trained_segmenter_target("the large road", parsed, False) is None


def test_flag_disabled_falls_back_even_for_a_plain_category_request(monkeypatch):
    monkeypatch.setattr(settings.trained_segmenter_routing, "enabled", False)
    assert classify("mark all roads") is None
    assert classify("segment buildings") is None


def test_flag_enabled_by_default():
    assert settings.trained_segmenter_routing.enabled is True
