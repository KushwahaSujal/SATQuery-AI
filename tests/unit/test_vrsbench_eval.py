from pathlib import Path
from scripts.evaluate_grounding_vrsbench import (
    compute_box_iou,
    normalize_gt_box,
    resolve_image_path,
    load_evaluation_records,
)


def test_compute_box_iou():
    # Exact match
    box1 = [10.0, 10.0, 50.0, 50.0]
    assert compute_box_iou(box1, box1) == 1.0

    # No overlap
    box2 = [60.0, 60.0, 100.0, 100.0]
    assert compute_box_iou(box1, box2) == 0.0

    # Half overlap: box1 area = 40*40=1600. box3 = [30, 10, 70, 50] (area 1600)
    # intersection: [30, 10, 50, 50] (20*40=800)
    # union: 1600 + 1600 - 800 = 2400. iou = 800/2400 = 1/3 = 0.333333
    box3 = [30.0, 10.0, 70.0, 50.0]
    iou = compute_box_iou(box1, box3)
    assert abs(iou - (1.0 / 3.0)) < 1e-4

    # Invalid box
    assert compute_box_iou([], [1, 2, 3, 4]) == 0.0


def test_normalize_gt_box():
    # XYWH format to XYXY
    xywh = [10, 20, 30, 40]
    assert normalize_gt_box(xywh, box_format="xywh") == [10, 20, 40, 60]

    # Relative normalized to absolute
    rel_xyxy = [0.1, 0.2, 0.5, 0.6]
    abs_box = normalize_gt_box(rel_xyxy, box_format="xyxy", img_w=100, img_h=100)
    assert abs_box == [10.0, 20.0, 50.0, 60.0]


def test_resolve_image_path():
    root = Path(__file__).resolve().parents[2]  # repo root (tests/unit/<file>)
    sample_dir = root / "datasets/samples/real_pair"
    resolved = resolve_image_path("real_image_b", [sample_dir])
    assert resolved is not None
    assert resolved.is_file()
    assert "real_image_b" in resolved.name


def test_load_evaluation_records():
    root = Path(__file__).resolve().parents[2]  # repo root (tests/unit/<file>)
    sample_rec_path = root / "datasets/samples/vrsbench_sample_records.json"
    records = load_evaluation_records(sample_rec_path)
    assert len(records) >= 1
    assert "image_id" in records[0]
    assert "query" in records[0]
    assert "bbox" in records[0]
