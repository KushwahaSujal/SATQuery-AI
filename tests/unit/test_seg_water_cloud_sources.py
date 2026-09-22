"""
Unit tests for the water_bodies and cloud95 binary-segmentation sources.

CPU only, no GPU and no checkpoints: they walk the source indexes under datasets/raw/ and load a
handful of tiles, checking shapes, dtypes, binarised masks, a non-trivial foreground fraction and
that the three splits are disjoint. Skipped when the raw data is not downloaded.
"""
import numpy as np
import pytest

from training.segmentation.datasets import (
    CLOUD_GSD_M,
    RAW,
    TARGET_GSD_M,
    WATER_GSD_M,
    SOURCES,
    SegTiles,
    _load,
    read_crop,
    read_pair,
)

SPLITS = ("train", "val", "test")

# (source, its native GSD, the raw directory it needs, how many tiles to actually decode)
CASES = [
    ("water_bodies", WATER_GSD_M, RAW / "water_bodies_s2/Water Bodies Dataset", 12),
    ("cloud95", CLOUD_GSD_M, RAW / "cloud95_landsat8", 12),
]


def _items(source: str, raw_dir):
    if not raw_dir.exists():
        pytest.skip(f"{raw_dir} not downloaded")
    return {s: SOURCES[source](s) for s in SPLITS}


@pytest.mark.parametrize("source,gsd,raw_dir,n", CASES)
def test_index_is_populated_and_paths_exist(source, gsd, raw_dir, n):
    items = _items(source, raw_dir)
    for split in SPLITS:
        assert items[split], f"{source}/{split} is empty"
    # Both sources are hash_split 90/5/5, so train dominates but val and test are not slivers.
    total = sum(len(items[s]) for s in SPLITS)
    assert len(items["train"]) > total * 0.7
    assert min(len(items["val"]), len(items["test"])) > total * 0.01
    for split in SPLITS:
        for img, mask, item_gsd, *_ in items[split][:n]:
            assert img.exists() and mask.exists()
            assert item_gsd == gsd


@pytest.mark.parametrize("source,gsd,raw_dir,n", CASES)
def test_splits_are_disjoint(source, gsd, raw_dir, n):
    items = _items(source, raw_dir)
    seen = {s: {i[0] for i in items[s]} for s in SPLITS}
    for split in SPLITS:
        assert len(seen[split]) == len(items[split]), f"{source}/{split} has duplicate tiles"
    assert not seen["train"] & seen["val"]
    assert not seen["train"] & seen["test"]
    assert not seen["val"] & seen["test"]


def test_cloud95_splits_do_not_share_a_landsat_scene():
    """Patches overlap within a scene, so a scene straddling train and test would leak."""
    items = _items("cloud95", RAW / "cloud95_landsat8")
    scenes = {s: {p.stem.split("_by_", 1)[1].split("_", 1)[1] for p, *_ in items[s]} for s in SPLITS}
    assert not scenes["train"] & scenes["val"]
    assert not scenes["train"] & scenes["test"]
    assert not scenes["val"] & scenes["test"]
    assert len(scenes["train"]) >= 10


@pytest.mark.parametrize("source,gsd,raw_dir,n", CASES)
def test_read_pair_shapes_dtypes_and_binary_masks(source, gsd, raw_dir, n):
    items = _items(source, raw_dir)["train"][:n]
    fg = []
    for item in items:
        img, mask, valid = read_pair(*item, target_gsd=gsd)
        assert img.ndim == 3 and img.shape[2] == 3 and img.dtype == np.uint8
        assert mask.shape == img.shape[:2] and mask.dtype == np.float32
        assert valid.shape == img.shape[:2] and valid.dtype == np.float32
        assert set(np.unique(mask)) <= {0.0, 1.0}
        assert set(np.unique(valid)) <= {0.0, 1.0}
        # Neither source uses the white-pixel no-data convention, so every pixel must count.
        assert valid.mean() == 1.0
        fg.append(float(mask.mean()))
    assert 0.02 < float(np.mean(fg)) < 0.98, f"{source} foreground fraction looks degenerate: {fg}"
    assert max(fg) > 0.05, f"{source} has no tile with real foreground: {fg}"


@pytest.mark.parametrize("source,gsd,raw_dir,n", CASES)
def test_read_pair_keeps_native_resolution_at_its_own_target(source, gsd, raw_dir, n):
    """At target_gsd == the source GSD nothing is resampled.

    The 0.5 m default would scale a water tile 20x and a cloud patch 60x per axis — 400-3600x the
    pixels, from imagery that holds no such detail. That is why these two get their own target;
    the blown-up read is asserted arithmetically rather than run, because it would not fit in RAM.
    """
    item = _items(source, raw_dir)["train"][0]
    raw_img, raw_mask = _load(item[0], item[1], *item[3:])
    img, mask, _ = read_pair(*item, target_gsd=gsd)
    assert img.shape == raw_img.shape
    assert mask.shape == raw_mask.shape
    assert round(img.shape[0] * gsd / TARGET_GSD_M) > img.shape[0] * 10


@pytest.mark.parametrize("source,gsd,raw_dir,n", CASES)
def test_read_crop_and_dataset_tensors(source, gsd, raw_dir, n):
    items = _items(source, raw_dir)["train"][:n]
    rng = np.random.default_rng(0)
    for item in items[:4]:
        img, mask, valid = read_crop(*item, crop=256, rng=rng, target_gsd=gsd)
        assert img.shape == (256, 256, 3) and img.dtype == np.uint8
        assert mask.shape == (256, 256) and set(np.unique(mask)) <= {0.0, 1.0}
        assert valid.shape == (256, 256)

    ds = SegTiles(items, crop=256, train=True, target_gsd=gsd)
    x, m, v = ds[0]
    assert tuple(x.shape) == (3, 256, 256) and x.dtype.is_floating_point
    assert tuple(m.shape) == (1, 256, 256) and tuple(v.shape) == (1, 256, 256)
    assert float(m.min()) >= 0.0 and float(m.max()) <= 1.0


@pytest.mark.parametrize("source,raw_dir", [("deepglobe_roads", RAW / "deepglobe_roads"),
                                            ("whu_building", RAW / "whu_building")])
def test_existing_sources_still_default_to_half_metre(source, raw_dir):
    """The loader change added an optional 4th Item field and a per-task target; the three-field
    sources must still resolve to exactly the old call."""
    if not raw_dir.exists():
        pytest.skip(f"{raw_dir} not downloaded")
    item = SOURCES[source]("train")[0]
    assert len(item) == 3
    img, mask, valid = read_pair(*item)
    explicit = read_pair(*item, target_gsd=TARGET_GSD_M)
    assert np.array_equal(img, explicit[0]) and np.array_equal(mask, explicit[1])
    assert np.array_equal(valid, explicit[2])
    assert img.dtype == np.uint8 and mask.dtype == np.float32


def test_cloud95_rgb_is_never_pure_white():
    """A saturated cloud must not be mistaken for the white no-data padding used by read_crop."""
    items = _items("cloud95", RAW / "cloud95_landsat8")["train"]
    worst = 0
    for item in items[:12]:
        img, _, _ = read_pair(*item, target_gsd=CLOUD_GSD_M)
        worst = max(worst, int(img.max()))
    assert worst <= 254
