"""CPU-only checks for the ISPRS 2D semantic-labelling data layer (training/segmentation/datasets.py).

No GPU, no model weights. The tests that touch the raw tiles skip when datasets/raw is absent, so
the suite still runs on a machine without the 55 GB download; the decoding and split tests are
pure logic and always run.
"""
import numpy as np
import pytest

from training.segmentation.datasets import (
    IGNORE,
    ISPRS_CLASSES,
    ISPRS_GSD_M,
    ISPRS_SOURCES,
    IsprsTiles,
    decode_isprs_label,
    isprs_split,
    read_isprs,
)

# The ISPRS colour code, straight from the dataset description (docs/complexscenes_revision_v4.pdf).
ISPRS_COLOURS = {
    "impervious": (255, 255, 255),
    "building": (0, 0, 255),
    "low_vegetation": (0, 255, 255),
    "tree": (0, 255, 0),
    "car": (255, 255, 0),
    "clutter": (255, 0, 0),
}


def _have(source: str) -> bool:
    try:
        return len(ISPRS_SOURCES[source]("train")) > 0
    except (FileNotFoundError, OSError):
        return False


needs_data = pytest.mark.skipif(not _have("isprs_potsdam"), reason="datasets/raw ISPRS tiles absent")


# ------------------------------------------------------------------------------ label decoding
def test_decode_maps_the_six_isprs_colours_to_their_class_indices():
    rgb = np.array([[ISPRS_COLOURS[c] for c in ISPRS_CLASSES]], np.uint8)
    assert decode_isprs_label(rgb).tolist() == [list(range(len(ISPRS_CLASSES)))]


def test_decode_yields_exactly_six_classes_and_nothing_else():
    rgb = np.array([[ISPRS_COLOURS[c] for c in ISPRS_CLASSES]], np.uint8)
    assert sorted(np.unique(decode_isprs_label(rgb)).tolist()) == [0, 1, 2, 3, 4, 5]
    assert len(ISPRS_CLASSES) == 6


def test_decode_sends_unused_cube_corners_to_ignore():
    # Black is the no-data value of the *_noBoundary eroded label sets; magenta is unused.
    rgb = np.array([[(0, 0, 0), (255, 0, 255)]], np.uint8)
    assert decode_isprs_label(rgb).tolist() == [[IGNORE, IGNORE]]


def test_decode_tolerates_the_two_off_palette_potsdam_tiles():
    # top_potsdam_6_7_label.tif codes most cars (252,255,0); top_potsdam_4_12_label.tif was
    # re-encoded lossily and uses e.g. (9,222,221) for cyan and (225,227,227) for white.
    rgb = np.array([[(252, 255, 0), (9, 222, 221), (225, 227, 227)]], np.uint8)
    assert decode_isprs_label(rgb).tolist() == [[4, 2, 0]]


def test_decode_is_not_confused_by_channel_order():
    # cv2.imread would hand back BGR; the registry reads through rasterio in band order, so the
    # asymmetric pair low_vegetation (0,255,255) / car (255,255,0) must not swap.
    rgb = np.array([[(0, 255, 255), (255, 255, 0)]], np.uint8)
    bgr = rgb[..., ::-1].copy()
    assert decode_isprs_label(rgb).tolist() == [[2, 4]]
    assert decode_isprs_label(bgr).tolist() == [[4, 2]]


# ---------------------------------------------------------------------------------------- split
def test_isprs_split_is_deterministic_and_covers_only_the_three_names():
    ids = [f"potsdam_{r}_{c}" for r in range(2, 8) for c in range(7, 16)]
    first = [isprs_split(i) for i in ids]
    assert first == [isprs_split(i) for i in ids]
    assert set(first) <= {"train", "val", "test"}


@pytest.mark.parametrize("source", sorted(ISPRS_SOURCES))
@needs_data
def test_splits_are_disjoint_and_cover_every_tile(source):
    splits = {s: ISPRS_SOURCES[source](s) for s in ("train", "val", "test")}
    ids = {s: {img.stem for img, *_ in items} for s, items in splits.items()}
    assert ids["train"] & ids["val"] == set()
    assert ids["train"] & ids["test"] == set()
    assert ids["val"] & ids["test"] == set()
    total = sum(len(v) for v in ids.values())
    assert total == len(set().union(*ids.values()))
    assert total == (38 if source.startswith("isprs_potsdam") else 33)
    assert all(len(v) > 0 for v in ids.values()), "every split must have at least one tile"


@needs_data
def test_potsdam_rgb_and_irrg_hold_out_the_same_tiles():
    """The two Potsdam variants are the same scenes; a tile in one's train set must never be in
    the other's test set, or a joint run would leak."""
    for split in ("train", "val", "test"):
        rgb = {p.stem.removesuffix("_RGB") for p, *_ in ISPRS_SOURCES["isprs_potsdam"](split)}
        irrg = {p.stem.removesuffix("_RGBIR") for p, *_ in ISPRS_SOURCES["isprs_potsdam_irrg"](split)}
        assert rgb == irrg


@needs_data
def test_registry_records_native_gsd_and_band_selection():
    img, label, gsd, bands = ISPRS_SOURCES["isprs_potsdam"]("train")[0]
    assert (gsd, bands) == (0.05, (1, 2, 3)) and img.exists() and label.exists()
    assert ISPRS_SOURCES["isprs_potsdam_irrg"]("train")[0][3] == (4, 1, 2)  # IR, R, G
    img, label, gsd, bands = ISPRS_SOURCES["isprs_vaihingen"]("train")[0]
    assert (gsd, bands) == (0.09, (1, 2, 3)) and img.exists() and label.exists()


# ----------------------------------------------------------------------------------------- crops
@pytest.mark.parametrize("source", sorted(ISPRS_SOURCES))
@needs_data
def test_crop_has_the_requested_shape_and_dtypes(source):
    item = ISPRS_SOURCES[source]("train")[0]
    img, mask = read_isprs(*item, crop=256, rng=np.random.default_rng(0))
    assert img.shape == (256, 256, 3) and img.dtype == np.uint8
    assert mask.shape == (256, 256) and mask.dtype == np.uint8
    assert set(np.unique(mask).tolist()) <= {0, 1, 2, 3, 4, 5, IGNORE}


@needs_data
def test_whole_tile_read_is_rescaled_to_the_target_gsd():
    img, mask, gsd, _ = ISPRS_SOURCES["isprs_potsdam"]("val")[0]
    out, m = read_isprs(img, mask, gsd, (1, 2, 3))
    assert out.shape[:2] == m.shape
    # 6000 px at 0.05 m -> 3000 px at 0.1 m.
    assert out.shape[:2] == (round(6000 * gsd / ISPRS_GSD_M),) * 2


@needs_data
def test_dataset_item_is_a_normalised_chw_tensor_and_an_int64_mask():
    ds = IsprsTiles(ISPRS_SOURCES["isprs_vaihingen"]("train")[:1], crop=192, train=True)
    x, m = ds[0]
    assert tuple(x.shape) == (3, 192, 192) and str(x.dtype) == "torch.float32"
    assert tuple(m.shape) == (192, 192) and str(m.dtype) == "torch.int64"
    assert abs(float(x.mean())) < 5.0  # normalised, not raw 0-255


# ------------------------------------------------------- hand-checked histogram for a named tile
@needs_data
def test_named_tile_histogram_matches_hand_checked_counts():
    """top_mosaic_09cm_area1: full-tile class pixel counts, counted once against the raw RGB
    label and recorded here. 1919 x 2569 = 4,930,111 pixels, none unlabelled.

    Counted with: rasterio.open(gt).read([1,2,3]) then an exact match against each of the six
    ISPRS colours -- i.e. by a different route than decode_isprs_label's thresholding, so the two
    agreeing is a real check on the decoder rather than a restatement of it.
    """
    expected = {"impervious": 1753163, "building": 1852765, "low_vegetation": 621535,
                "tree": 626123, "car": 76323, "clutter": 2}
    item = next(i for i in sum((ISPRS_SOURCES["isprs_vaihingen"](s)
                                for s in ("train", "val", "test")), [])
                if i[0].stem == "top_mosaic_09cm_area1")
    import rasterio

    with rasterio.open(item[1]) as d:
        mask = decode_isprs_label(d.read((1, 2, 3)).transpose(1, 2, 0))
    counts = np.bincount(mask.ravel(), minlength=256)
    assert mask.shape == (2569, 1919)
    assert counts[IGNORE] == 0
    assert {c: int(counts[i]) for i, c in enumerate(ISPRS_CLASSES)} == expected
    assert int(counts[:6].sum()) == 1919 * 2569
