"""A bi-temporal pair must reach the change model earlier-first, whatever order the client sent.

Browsers' file pickers and the re-prompt route (POST /jobs/{id}/reuse-source, which sorts) both
deliver "after.png" before "before.png" alphabetically. ChangeFormer reads the first image as T1, so
the same LEVIR scene measured 11.35 % the right way round and 5.06 % reversed (Q-061).
"""
from backend.app.artifacts.temporal_order import chronological


def test_before_after_pair_is_reordered():
    assert chronological(["x/after.png", "x/before.png"]) == ["x/before.png", "x/after.png"]
    assert chronological(["satquery_change_after.png", "satquery_change_before.png"]) == [
        "satquery_change_before.png", "satquery_change_after.png"]


def test_already_ordered_pair_is_unchanged():
    assert chronological(["before.png", "after.png"]) == ["before.png", "after.png"]
    assert chronological(["2_change_t1_before.png", "2_change_t2_after.png"]) == [
        "2_change_t1_before.png", "2_change_t2_after.png"]


def test_other_hints_and_dates():
    assert chronological(["post_flood.tif", "pre_flood.tif"]) == ["pre_flood.tif", "post_flood.tif"]
    assert chronological(["scene_t2.png", "scene_t1.png"]) == ["scene_t1.png", "scene_t2.png"]
    assert chronological(["delhi_2023.png", "delhi_2016.png"]) == ["delhi_2016.png", "delhi_2023.png"]
    assert chronological(["img_2020-05-01.tif", "img_2019-12-31.tif"]) == ["img_2019-12-31.tif", "img_2020-05-01.tif"]


def test_no_hint_keeps_client_order():
    assert chronological(["b.png", "a.png"]) == ["b.png", "a.png"]
    assert chronological(["optical.png", "sar.png"]) == ["optical.png", "sar.png"]


def test_single_image_and_contradictory_hints_are_untouched():
    assert chronological(["after.png"]) == ["after.png"]
    # both look "earlier": no basis to reorder
    assert chronological(["before_a.png", "before_b.png"]) == ["before_a.png", "before_b.png"]
    # substrings are not tokens: "newark" is not "new", "preview" is not "pre"
    assert chronological(["preview.png", "newark.png"]) == ["preview.png", "newark.png"]
