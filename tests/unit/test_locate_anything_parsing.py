"""
Unit tests for LocateAnything answer parsing and availability checks.
No weights, no GPU: parse_boxes / is_truncated are pure functions.
"""

import importlib.util

import pytest

from backend.app.ml.adapters import locate_anything as la
from backend.app.ml.adapters.locate_anything import (
    LocateAnythingAdapter,
    is_truncated,
    parse_boxes,
)

END = "<|im_end|>"


def test_parses_normal_boxes_into_pixel_space():
    text = f"<ref>airplane</ref><box><0><96><188><443></box><box><518><445><998><910></box>{END}"
    boxes, stats = parse_boxes(text, 512, 512, "airplane")

    assert stats == {"raw_box_count": 2, "dropped_degenerate": 0, "dropped_duplicate": 0}
    assert [b["xyxy"] for b in boxes] == [
        [0.0, 49.15, 96.26, 226.82],
        [265.22, 227.84, 510.98, 465.92],
    ]
    first = boxes[0]
    assert set(first) == {"xyxy", "bbox", "box_2d", "score", "label"}
    assert first["bbox"] == first["xyxy"] and first["bbox"] is not first["xyxy"]
    # box_2d is [ymin, xmin, ymax, xmax] normalized to 0..1
    assert first["box_2d"] == [0.096, 0.0, 0.443, 0.188]
    assert first["score"] == 0.5
    assert first["label"] == "airplane"


def test_non_square_image_scales_axes_independently():
    boxes, _ = parse_boxes(f"<box><100><200><300><400></box>{END}", 1000, 500, "car")
    assert boxes[0]["xyxy"] == [100.0, 100.0, 300.0, 200.0]
    assert boxes[0]["box_2d"] == [0.2, 0.1, 0.4, 0.3]


def test_none_box_yields_no_boxes():
    text = f"<ref>airplane</ref><box>None</box>{END}"
    boxes, stats = parse_boxes(text, 512, 512, "airplane")
    assert boxes == []
    assert stats["raw_box_count"] == 0
    assert is_truncated(text) is False


def test_degenerate_and_reversed_boxes_are_dropped():
    text = (
        "<box><10><10><10><50></box>"   # zero width
        "<box><10><50><60><50></box>"   # zero height
        "<box><831><0><483><1></box>"   # reversed x (seen in a runaway answer)
        "<box><20><20><40><40></box>"   # valid
        + END
    )
    boxes, stats = parse_boxes(text, 100, 100, "x")
    assert [b["xyxy"] for b in boxes] == [[2.0, 2.0, 4.0, 4.0]]
    assert stats == {"raw_box_count": 4, "dropped_degenerate": 3, "dropped_duplicate": 0}


def test_exact_duplicates_are_dropped():
    text = "<box><1><2><300><400></box>" * 3 + "<box><1><2><300><401></box>" + END
    boxes, stats = parse_boxes(text, 1000, 1000, "x")
    assert len(boxes) == 2
    assert stats == {"raw_box_count": 4, "dropped_degenerate": 0, "dropped_duplicate": 2}


def test_coordinates_are_clipped_to_image_bounds():
    text = f"<box><900><950><1200><1000></box>{END}"
    boxes, _ = parse_boxes(text, 200, 100, "x")
    assert boxes[0]["xyxy"] == [180.0, 95.0, 200.0, 100.0]
    assert boxes[0]["box_2d"] == [0.95, 0.9, 1.0, 1.0]


def test_box_that_is_empty_after_clipping_is_degenerate():
    boxes, stats = parse_boxes(f"<box><1000><10><1500><20></box>{END}", 100, 100, "x")
    assert boxes == []
    assert stats["dropped_degenerate"] == 1


def test_point_format_is_ignored():
    text = f"<ref>car</ref><box><120><340></box><box><5><6><50><60></box>{END}"
    boxes, stats = parse_boxes(text, 100, 100, "car")
    assert len(boxes) == 1
    assert stats["raw_box_count"] == 1


def test_truncated_flag():
    assert is_truncated("<box><1><2><3><4></box><box><1><2><3><5></box>") is True
    assert is_truncated("<box><1><2><3><4></box>" + END) is False
    assert is_truncated("") is True


def test_empty_answer():
    boxes, stats = parse_boxes("", 10, 10, "x")
    assert boxes == [] and stats["raw_box_count"] == 0


def test_unavailable_when_peft_missing(monkeypatch):
    real = importlib.util.find_spec

    def fake(name, *args, **kwargs):
        return None if name == "peft" else real(name, *args, **kwargs)

    monkeypatch.setattr(la.importlib.util, "find_spec", fake)
    adapter = LocateAnythingAdapter()
    assert adapter.is_available() is False
    assert "peft" in adapter._unavailable_reason()


def test_bitsandbytes_only_required_when_quantizing(monkeypatch):
    real = importlib.util.find_spec

    def fake(name, *args, **kwargs):
        return None if name == "bitsandbytes" else real(name, *args, **kwargs)

    monkeypatch.setattr(la.importlib.util, "find_spec", fake)
    adapter = LocateAnythingAdapter()
    monkeypatch.setattr(adapter.config, "quantization", "4bit")
    assert "bitsandbytes" in adapter._missing_dependencies()
    monkeypatch.setattr(adapter.config, "quantization", "none")
    assert "bitsandbytes" not in adapter._missing_dependencies()


def test_invalid_quantization_is_unavailable(monkeypatch):
    adapter = LocateAnythingAdapter()
    monkeypatch.setattr(adapter.config, "quantization", "3bit")
    assert adapter.is_available() is False
    assert "invalid quantization" in adapter._unavailable_reason()


def test_configured_quantization_is_valid():
    assert LocateAnythingAdapter().quantization in ("none", "8bit", "4bit")


@pytest.mark.parametrize("value, expected", [(None, la._DEFAULT_QUANTIZATION), ("none", "none"), ("8BIT", "8bit")])
def test_quantization_normalization(monkeypatch, value, expected):
    adapter = LocateAnythingAdapter()
    monkeypatch.setattr(adapter.config, "quantization", value)
    assert adapter.quantization == expected
