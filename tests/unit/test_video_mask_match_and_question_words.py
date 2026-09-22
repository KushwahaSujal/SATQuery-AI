"""Video keyframes: a propagated mask is attached only to its own detection; question words are not a class."""

import numpy as np
import pytest

from backend.app.workflows.grounding_reasoner import parse_v4_query
from backend.app.workflows.video_analysis import _mask_fits_box


def _mask(h, w, x1, y1, x2, y2):
    m = np.zeros((h, w), dtype=np.uint8)
    m[y1:y2, x1:x2] = 1
    return m


def test_mask_inside_its_box_matches():
    mask = _mask(432, 768, 320, 170, 490, 430)            # the red car
    box = [170 / 432, 320 / 768, 430 / 432, 490 / 768]    # its own box
    assert _mask_fits_box(mask, box)


def test_mask_of_another_object_does_not_match():
    # Keyframe 198 of satquery_white_cars.mp4: box on the silver car, tracked mask on the red car.
    mask = _mask(432, 768, 330, 250, 490, 432)
    silver_car_box = [0.002, 0.149, 0.523, 0.346]
    assert not _mask_fits_box(mask, silver_car_box)


def test_empty_or_missing_mask_does_not_match():
    assert not _mask_fits_box(None, [0.1, 0.1, 0.5, 0.5])
    assert not _mask_fits_box(np.zeros((10, 10)), [0.1, 0.1, 0.5, 0.5])


def test_tiny_mask_inside_a_huge_box_does_not_match():
    mask = _mask(100, 100, 10, 10, 14, 14)
    assert not _mask_fits_box(mask, [0.0, 0.0, 1.0, 1.0])


@pytest.mark.parametrize("query, prompt", [
    ("when does a red car appear?", "red car."),
    ("what time is the white car shown in the video?", "white car."),
    ("find the white car", "white car."),
    ("find all vehicles", "vehicles."),
])
def test_question_words_are_not_part_of_the_class(query, prompt):
    assert parse_v4_query(query)["clean_prompt"] == prompt
