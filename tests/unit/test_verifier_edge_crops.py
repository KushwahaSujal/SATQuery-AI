"""
Verifier crop geometry at the image edges (Q-046).

`PIL.Image.crop` fills out-of-bounds coordinates with black, so the pre-Q-046 geometry handed
RemoteCLIP fabricated pixels whenever the padded square left the frame — the cause of the two
DISPUTED answers on `05945_0000.png` recorded in Q-009 §3. These tests pin the repaired geometry:
every crop stays inside the frame, stays square, still contains the whole box, and contains no
pixel that is not in the source image. They need no weights — `DetectionVerifier.crop` is pure
geometry — so the verifier is constructed with a stub adapter.
"""
import numpy as np
import pytest
from PIL import Image

from backend.app.evidence.verifier import DetectionVerifier

W = H = 200


def verifier(crop_mode="inset"):
    # `crop` never touches the adapter; a sentinel proves it stays unused.
    return DetectionVerifier(clip_adapter=object(), crop_mode=crop_mode)


def image():
    """No pure-black pixel anywhere, so any black pixel in a crop must have been fabricated."""
    rng = np.random.default_rng(0)
    arr = rng.integers(1, 256, size=(H, W, 3), dtype=np.uint16).astype(np.uint8)
    arr = np.clip(arr, 1, 255)
    return Image.fromarray(arr, mode="RGB")


def assert_clean(img, crop_img, cb, box=None):
    """The crop is inside the frame, is the region the box names, and fabricates nothing."""
    assert cb[0] >= 0 and cb[1] >= 0 and cb[2] <= img.size[0] and cb[3] <= img.size[1], cb
    assert cb[2] > cb[0] and cb[3] > cb[1], cb
    assert crop_img.size == (cb[2] - cb[0], cb[3] - cb[1])
    arr = np.asarray(crop_img)
    assert not (arr.sum(axis=2) == 0).any(), "crop contains fabricated black pixels"
    np.testing.assert_array_equal(arr, np.asarray(img)[cb[1]:cb[3], cb[0]:cb[2]])
    if box is not None:
        assert cb[0] <= box[0] and cb[1] <= box[1] and cb[2] >= box[2] and cb[3] >= box[3], \
            f"crop {cb} lost part of box {box}"


# --------------------------------------------------------------- the legacy defect it replaces
def test_legacy_pad_mode_fabricates_black_and_is_reproducible():
    """The `pad` mode exists only so the harness can re-measure the old numbers; it must still
    reproduce the defect, otherwise the before/after comparison means nothing."""
    img = image()
    crop_img, cb = verifier("pad").crop(img, [0.0, 0.0, 20.0, 20.0])
    assert cb[0] < 0 and cb[1] < 0, cb
    arr = np.asarray(crop_img)
    assert (arr.sum(axis=2) == 0).any(), "pad mode should still fabricate black"
    assert (arr.sum(axis=2) == 0).mean() > 0.5


def test_crop_mode_is_validated():
    with pytest.raises(ValueError):
        DetectionVerifier(clip_adapter=object(), crop_mode="reflect")


# ------------------------------------------------------------------------------- every edge
@pytest.mark.parametrize("box,name", [
    ([0.0, 80.0, 20.0, 120.0], "left"),
    ([180.0, 80.0, 200.0, 120.0], "right"),
    ([80.0, 0.0, 120.0, 20.0], "top"),
    ([80.0, 180.0, 120.0, 200.0], "bottom"),
])
def test_box_touching_each_edge(box, name):
    img = image()
    crop_img, cb = verifier().crop(img, box)
    assert_clean(img, crop_img, cb, box)
    assert cb[2] - cb[0] == cb[3] - cb[1], f"{name}: crop is not square: {cb}"


@pytest.mark.parametrize("box,name", [
    ([0.0, 0.0, 20.0, 20.0], "top-left"),
    ([180.0, 0.0, 200.0, 20.0], "top-right"),
    ([0.0, 180.0, 20.0, 200.0], "bottom-left"),
    ([180.0, 180.0, 200.0, 200.0], "bottom-right"),
])
def test_box_in_each_corner(box, name):
    img = image()
    crop_img, cb = verifier().crop(img, box)
    assert_clean(img, crop_img, cb, box)
    assert cb[2] - cb[0] == cb[3] - cb[1], f"{name}: crop is not square: {cb}"


def test_edge_crop_keeps_the_requested_side_length():
    """The window is translated inward, not shrunk: the object keeps the scale the measured
    pad-1.0 geometry gives it, which is what the 973-crop probe was tuned at."""
    v = verifier()
    img = image()
    _, edge = v.crop(img, [0.0, 80.0, 40.0, 120.0])
    _, middle = v.crop(img, [80.0, 80.0, 120.0, 120.0])
    assert edge[2] - edge[0] == middle[2] - middle[0]


def test_crop_already_inside_the_frame_is_returned_unchanged():
    """Non-edge crops must be bit-identical to the pre-Q-046 geometry, so the Q-009 numbers for
    them cannot move: measured, the 262 in-frame crops of the probe are unchanged."""
    img = image()
    box = [80.0, 80.0, 120.0, 120.0]
    _, legacy = verifier("pad").crop(img, box)
    _, fixed = verifier("inset").crop(img, box)
    assert legacy == fixed


# ---------------------------------------------------------------------- degenerate geometry
def test_box_larger_than_the_image():
    img = image()
    crop_img, cb = verifier().crop(img, [-50.0, -50.0, 250.0, 250.0])
    assert_clean(img, crop_img, cb)
    assert cb == [0, 0, W, H], cb


def test_one_pixel_box():
    img = image()
    box = [100.0, 100.0, 101.0, 101.0]
    crop_img, cb = verifier().crop(img, box)
    assert_clean(img, crop_img, cb, box)
    # min_crop_side floors the window, so a 1 px box still gets a usable crop.
    assert cb[2] - cb[0] >= min(int(verifier().cfg.min_crop_side), W)


def test_one_pixel_box_in_the_corner():
    img = image()
    box = [0.0, 0.0, 1.0, 1.0]
    crop_img, cb = verifier().crop(img, box)
    assert_clean(img, crop_img, cb, box)


def test_box_entirely_outside_the_image():
    """A detector should never emit one, but the verifier must not hand RemoteCLIP a black square
    and let it score it as image content. The window is pulled back into the frame."""
    img = image()
    crop_img, cb = verifier().crop(img, [-300.0, -300.0, -260.0, -260.0])
    assert_clean(img, crop_img, cb)
    assert cb == [0, 0, cb[2], cb[3]] and cb[2] <= W and cb[3] <= H


def test_box_outside_on_the_far_side():
    img = image()
    crop_img, cb = verifier().crop(img, [400.0, 400.0, 440.0, 440.0])
    assert_clean(img, crop_img, cb)
    assert cb[2] == W and cb[3] == H, cb


def test_non_square_image_stays_square_and_inside():
    img = Image.fromarray(np.full((80, 300, 3), 7, dtype=np.uint8), mode="RGB")
    crop_img, cb = verifier().crop(img, [0.0, 0.0, 60.0, 60.0])
    assert_clean(img, crop_img, cb)
    assert cb[2] - cb[0] == cb[3] - cb[1] == 80, cb


def test_no_box_anywhere_fabricates_a_pixel():
    """A sweep over the frame: 11x11 box positions at three sizes, none may fabricate."""
    v, img = verifier(), image()
    for size in (8, 60, 180):
        for x in range(0, W - 1, 20):
            for y in range(0, H - 1, 20):
                box = [float(x), float(y), float(min(x + size, W)), float(min(y + size, H))]
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                crop_img, cb = v.crop(img, box)
                assert_clean(img, crop_img, cb, box)


# --------------------------------------------------------------------------- real inference
@pytest.mark.models
def test_real_verifier_no_longer_contradicts_the_edge_box_on_05945():
    """One real RemoteCLIP call each way on the `05945_0000.png` white car, the cheaper of the two
    boxes behind Q-009's DISPUTED results. Measured 2026-09-21:
    pad -> contradicted (best match 'roundabout'), inset -> unverified (best match 'grass field').
    """
    from pathlib import Path

    path = Path("tests/data/grounding/05945_0000.png")
    if not path.is_file():
        pytest.skip("demo image not present")
    img = Image.open(path).convert("RGB")
    box = [0.0, 312.2, 29.1, 379.9]
    v_inset = DetectionVerifier(crop_mode="inset")
    if not v_inset.is_available():
        pytest.skip("RemoteCLIP weights not available")
    _, cb = v_inset.crop(img, box)
    assert cb[0] >= 0 and cb[1] >= 0 and cb[2] <= img.size[0] and cb[3] <= img.size[1]
    assert v_inset.verify(img, box, "car").status != "contradicted"
    assert DetectionVerifier(clip_adapter=v_inset.clip, crop_mode="pad") \
        .verify(img, box, "car").status == "contradicted"
