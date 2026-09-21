"""Dispatch-only tests for routing plain "mark all roads" / "segment buildings" / "mask all water"
/ "mask the clouds" style queries to the trained U-Net segmenters (project/qna.md Q-025t, Q-026t,
Q-035, Q-038).

No checkpoints and no model I/O: `classify_trained_segmenter_target` is a pure function of the
parsed query, `_wants_all_instances`'s existing category-vs-single-target signal, and the
`trained_segmenter_routing.enabled` setting. `run_trained_segmenter_path` (the execution side, which
does load a checkpoint) is exercised for real in tests/models/test_grounding_trained_segmenter.py.
"""
import pytest

from backend.app.config import settings
from backend.app.ml.registry import model_registry
from backend.app.workflows.grounding import _wants_all_instances
from backend.app.workflows.grounding_reasoner import parse_v4_query
from backend.app.workflows.trained_segmenter import (
    MASK_NOUN_BY_MODEL,
    STRATEGY_BY_MODEL,
    TRAINED_SEGMENTER_EXCLUSIONS,
    TRAINED_SEGMENTER_TARGETS,
    classify_trained_segmenter_target,
)


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
    # Water (Q-035). "mask all water" is the canonical phrasing; the rest are the vocabulary
    # intent_classifier.py's own water group already recognises.
    ("mask all water", "water_segmenter"),
    ("mask water bodies", "water_segmenter"),
    ("find water bodies", "water_segmenter"),
    ("mask all lakes", "water_segmenter"),
    ("mask all rivers", "water_segmenter"),
    ("mask all ponds", "water_segmenter"),
    ("mask the reservoir", "water_segmenter"),
    # Cloud (Q-035). "cloud" is in no OBJECT_PATTERNS group; these reach the grounding pipeline
    # through the router's fallback noun-phrase extractor.
    ("mask the clouds", "cloud_segmenter"),
    ("mask all clouds", "cloud_segmenter"),
    ("segment clouds", "cloud_segmenter"),
    ("mask cloud cover", "cloud_segmenter"),
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
    "roads and buildings",             # multiple classes in one query
    "mask water and roads",            # two trained classes in one query -> ambiguous, fall back
    "mask all water bodies and buildings",
    # Compound nouns that merely contain a target word but name another object. A storage tank is
    # the detector's job; 95-Cloud labels cloud, not cloud shadow.
    "mask all water tanks",
    "mask the water tank",
    "mask all water towers",
    "mask the cloud shadows",
])
def test_qualified_or_unsupported_queries_fall_back_to_the_existing_pipeline(query):
    assert classify(query) is None


@pytest.mark.parametrize("query", [
    # Deliberately unrouted capabilities that DO have trained checkpoints and adapters. Land cover
    # returns a 7-class class-index map, which this pipeline's `segmentation_mask` contract (one
    # binary mask, consumed by fusion.py as `mask > 0`) cannot carry; the ISPRS models answer the
    # same classes as the 0.5 m ones but at 0.1 m and cannot be auto-selected without GSD/band
    # metadata. See docs/models/trained_segmenters.md.
    "mask land cover",
    "segment land cover",
    "show me the land cover",
    "mask all impervious surfaces",
    "mask all low vegetation",
])
def test_capabilities_with_checkpoints_but_no_route_fall_back(query):
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


def test_exclusions_block_compound_nouns_that_merely_contain_a_target_word():
    """The exclusion list, not a lucky wording, is what keeps "water tank" off the water model."""
    assert classify_trained_segmenter_target("x", {"category": "water tanks"}, True) is None
    assert classify_trained_segmenter_target("x", {"category": "water tower"}, True) is None
    assert classify_trained_segmenter_target("x", {"category": "cloud shadow"}, True) is None
    # The bare classes still route, so the exclusions are not simply disabling the vocabulary.
    assert classify_trained_segmenter_target("x", {"category": "water"}, True) == "water_segmenter"
    assert classify_trained_segmenter_target("x", {"category": "clouds"}, True) == "cloud_segmenter"


def test_word_boundaries_keep_unrelated_words_out():
    """"waterfront"/"watershed"/"cloudy" embed a target word but are not separate words, so `\\b`
    already excludes them and they need no exclusion-list entry."""
    for category in ("waterfront buildings", "watershed", "cloudy areas"):
        result = classify_trained_segmenter_target("x", {"category": category}, True)
        assert result != "water_segmenter"
        assert result != "cloud_segmenter"


def test_every_routable_target_has_a_strategy_and_is_registered():
    """A target with no strategy string would KeyError inside run_trained_segmenter_path, and one
    with no registry entry could never be dispatched."""
    for key in TRAINED_SEGMENTER_TARGETS:
        assert key in STRATEGY_BY_MODEL, f"{key} has no strategy string"
        assert key in MASK_NOUN_BY_MODEL, f"{key} has no answer noun"
        assert key in model_registry.ADAPTER_CLASSES, f"{key} is not a registered model"
    assert set(STRATEGY_BY_MODEL) == set(TRAINED_SEGMENTER_TARGETS)
    # Strategy strings must be distinct, or two models would be indistinguishable in the trace.
    assert len(set(STRATEGY_BY_MODEL.values())) == len(STRATEGY_BY_MODEL)


def test_exclusion_keys_name_real_targets():
    assert set(TRAINED_SEGMENTER_EXCLUSIONS) <= set(TRAINED_SEGMENTER_TARGETS)


def test_multi_class_and_isprs_models_are_registered_but_never_routed():
    """They are callable adapters (deliberate), but no vocabulary maps a query onto them.

    `eurosat_classifier` and `flood_segmenter` are here for two further reasons (project/qna.md
    Q-041): EuroSAT returns one scene label with neither a mask nor a box, so it cannot satisfy the
    grounding pipeline's response contract, and the flood model needs 16 co-registered S1+S2+DEM
    bands that the pipeline cannot supply and refuses to serve anyway.
    """
    for key in (
        "landcover_segmenter",
        "isprs_potsdam_segmenter",
        "isprs_vaihingen_segmenter",
        "eurosat_classifier",
        "flood_segmenter",
    ):
        assert key in model_registry.ADAPTER_CLASSES
        assert key not in TRAINED_SEGMENTER_TARGETS
        assert key not in STRATEGY_BY_MODEL
        assert key not in MASK_NOUN_BY_MODEL
        assert key not in TRAINED_SEGMENTER_EXCLUSIONS


def test_flag_disabled_falls_back_even_for_a_plain_category_request(monkeypatch):
    monkeypatch.setattr(settings.trained_segmenter_routing, "enabled", False)
    assert classify("mark all roads") is None
    assert classify("segment buildings") is None
    assert classify("mask all water") is None
    assert classify("mask the clouds") is None


def test_flag_enabled_by_default():
    assert settings.trained_segmenter_routing.enabled is True
