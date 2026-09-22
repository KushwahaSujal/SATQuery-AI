"""Tile indexes for binary segmentation sources under datasets/raw/, plus one shared Dataset.

Each source is a function split -> list[(image_path, mask_path, gsd_m[, loader])]. Tiles are
resampled to a common ground sampling distance on load, so a road is the same number of pixels
wide whichever source it came from. That target is per *task*, not global: 0.5 m (TARGET_GSD_M)
suits sub-metre road/building sources, while the 10 m Sentinel-2 water tiles and the 30 m
Landsat cloud patches are trained at their own native resolution (see WATER/CLOUD notes below)
rather than being upsampled 20-60x into imagery that has no such detail in it.

Sources without an official labelled val/test split get a deterministic 90/5/5 split by a hash
of the tile id, so the split never changes between runs or machines.

Three task families live here, each with its own taxonomy and its own target GSD, wired together
by SEG_TASKS at the bottom: binary segmentation (SOURCES/SegTiles), land cover
(LANDCOVER_SOURCES/LandCoverTiles, 0.5 m) and ISPRS very-high-resolution urban
(ISPRS_SOURCES/IsprsTiles, 0.1 m).
"""

from __future__ import annotations

import hashlib
import warnings
from functools import lru_cache
from pathlib import Path

import albumentations as A
import cv2
import numpy as np
import rasterio
import torch
from PIL import Image
from rasterio.windows import Window
from torch.utils.data import Dataset

# Massachusetts GeoTIFFs trigger one "unknown TIFF tag" warning per read (tens of MB of log).
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
# ISPRS label tiles carry no geotransform (the imagery does); rasterio warns once per open.
warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)

RAW = Path(__file__).resolve().parents[2] / "datasets/raw"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32) * 255
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32) * 255
TARGET_GSD_M = 0.5  # default target for the sub-metre sources; --target-gsd overrides per task
WATER_GSD_M = 10.0  # Sentinel-2 visible bands
CLOUD_GSD_M = 30.0  # Landsat 8 OLI reflective bands

# image, mask, gsd, and optionally the name of the pixel loader (default "rgb", see _READERS).
Item = tuple[Path, Path, float] | tuple[Path, Path, float, str]


def hash_split(tile_id: str) -> str:
    b = int(hashlib.sha1(tile_id.encode()).hexdigest(), 16) % 100
    return "test" if b < 5 else "val" if b < 10 else "train"


@lru_cache(None)
def _deepglobe_roads() -> dict[str, list[Item]]:
    out: dict[str, list[Item]] = {"train": [], "val": [], "test": []}
    # Only the official train split ships masks; valid/test are unlabelled.
    for sat in sorted((RAW / "deepglobe_roads/train").glob("*_sat.jpg")):
        tile = sat.name[: -len("_sat.jpg")]
        out[hash_split(tile)].append((sat, sat.with_name(f"{tile}_mask.png"), 0.5))
    return out


def _mnih(root: Path) -> dict[str, list[Item]]:
    """Massachusetts roads/buildings (Mnih 2013, 1 m): official train/val/test, tiff/<split>{,_labels}."""
    out = {}
    for split in ("train", "val", "test"):
        imgs = sorted((root / "tiff" / split).glob("*.tif*"))
        labels = {p.stem: p for p in (root / "tiff" / f"{split}_labels").glob("*.tif*")}
        out[split] = [(p, labels[p.stem], 1.0) for p in imgs if p.stem in labels]
    return out


@lru_cache(None)
def _massachusetts_roads():
    return _mnih(RAW / "massachusetts_roads")


@lru_cache(None)
def _massachusetts_buildings():
    return _mnih(RAW / "massachusetts_buildings")


@lru_cache(None)
def _whu_building():
    root = RAW / "whu_building"
    return {s: [(p, root / s / "Mask" / p.name, 0.3) for p in sorted((root / s / "Image").glob("*.png"))]
            for s in ("train", "val", "test")}


@lru_cache(None)
def _spacenet3_roads():
    out: dict[str, list[Item]] = {"train": [], "val": [], "test": []}
    # Rasterised by training/segmentation/prepare_spacenet3.py.
    for img in sorted((RAW / "spacenet3_roads/prepared/images").glob("*.png")):
        out[hash_split(img.stem)].append((img, img.parent.parent / "masks" / img.name, 0.3))
    return out


@lru_cache(None)
def _water_bodies():
    """Kaggle "Water Bodies Dataset": Sentinel-2 RGB jpgs (~10 m) with a jpg mask of the same name.

    No official split, so hash_split on the tile id. Tile sizes vary from a few pixels to ~2000;
    the 21 tiles under 32 px on a side are dropped, because after padding to a crop they would be
    almost entirely no-data. Masks are jpg-compressed greyscale, so values are not exactly 0/255 —
    _finish's > 127 rule binarises them.
    """
    root = RAW / "water_bodies_s2/Water Bodies Dataset"
    out: dict[str, list[Item]] = {"train": [], "val": [], "test": []}
    for img in sorted((root / "Images").glob("*.jpg")):
        mask = root / "Masks" / img.name
        if not mask.exists():
            continue
        with Image.open(img) as probe:  # header only; decoding all 2841 tiles here would cost ~30 s
            if min(probe.size) < 32:
                continue
        out[hash_split(img.stem)].append((img, mask, WATER_GSD_M))
    return out


# Only the "additional to 38-Cloud" half of the 95-Cloud release is on disk; 38-Cloud's own train
# and test imagery was not downloaded (datasets/raw/cloud95_landsat8 holds its metadata only).
_CLOUD95 = RAW / "cloud95_landsat8/95-cloud_training_only_additional_to38-cloud"


@lru_cache(None)
def _cloud95():
    """95-Cloud (Landsat 8, 30 m): 384x384 per-band 16-bit patches plus a binary cloud gt.

    Restricted to the shipped non-empty patch list, which excludes patches that are entirely
    scene-border no-data. "Non-empty" is about the image, not the label: cloud-free patches stay
    in, and are the negatives a cloud detector needs.

    The official 38-Cloud test scenes are not on disk (see _CLOUD95), so the split is hash_split on
    the Landsat *scene* id parsed out of the patch name — every patch of a scene lands in the same
    split, so adjacent overlapping patches cannot leak between train and test.
    """
    out: dict[str, list[Item]] = {"train": [], "val": [], "test": []}
    red_dir, gt_dir = _CLOUD95 / "train_red_additional_to38cloud", _CLOUD95 / "train_gt_additional_to38cloud"
    lines = (_CLOUD95 / "training_patches_95-cloud_nonempty.csv").read_text().splitlines()
    for line in lines[1:]:  # header is "name"
        patch = line.strip()
        gt = gt_dir / f"gt_{patch}.TIF"
        if not patch or not gt.exists():  # the list also covers the 38-Cloud half, which is absent
            continue
        scene = patch.split("_by_", 1)[1].split("_", 1)[1]  # patch_<r>_<c>_by_<R>_<C>_<scene id>
        out[hash_split(scene)].append((red_dir / f"red_{patch}.TIF", gt, CLOUD_GSD_M, "cloud95"))
    return out


SOURCES = {
    "deepglobe_roads": lambda s: _deepglobe_roads()[s],
    "massachusetts_roads": lambda s: _massachusetts_roads()[s],
    "spacenet3_roads": lambda s: _spacenet3_roads()[s],
    "whu_building": lambda s: _whu_building()[s],
    "massachusetts_buildings": lambda s: _massachusetts_buildings()[s],
    "water_bodies": lambda s: _water_bodies()[s],
    "cloud95": lambda s: _cloud95()[s],
}


def _read_rgb(path: Path) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def _read_cloud95(red: Path) -> np.ndarray:
    """RGB from 95-Cloud's three 16-bit band patches, addressed by the red band's path.

    The 16 -> 8 bit scale is fixed (>> 8), not a per-patch stretch: a per-patch stretch would leak
    the label, since an overcast patch and a clear one would end up with the same histogram. The
    cap at 254 keeps a bright cloud from becoming pure white, which _finish reads as no-data.
    """
    patch = red.name[len("red_"):]
    bands = [cv2.imread(str(_CLOUD95 / f"train_{b}_additional_to38cloud" / f"{b}_{patch}"), cv2.IMREAD_UNCHANGED)
             for b in ("red", "green", "blue")]
    return np.minimum(np.stack(bands, axis=-1) >> 8, 254).astype(np.uint8)


_READERS = {"rgb": _read_rgb, "cloud95": _read_cloud95}


def _load(img_path: Path, mask_path: Path, loader: str = "rgb") -> tuple[np.ndarray, np.ndarray]:
    return _READERS[loader](img_path), cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)


def _finish(img: np.ndarray, m: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mask = (m > 127).astype(np.float32)
    # Massachusetts tiles have pure-white no-data regions; exclude them from loss and metrics.
    valid = (~np.all(img == 255, axis=-1)).astype(np.float32)
    return img, mask, valid


def read_pair(img_path: Path, mask_path: Path, gsd: float, loader: str = "rgb",
              target_gsd: float = TARGET_GSD_M) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Whole tile resampled to target_gsd (evaluation)."""
    img, m = _load(img_path, mask_path, loader)
    if abs(gsd - target_gsd) > 1e-6:
        f = gsd / target_gsd
        size = (round(img.shape[1] * f), round(img.shape[0] * f))
        img = cv2.resize(img, size, interpolation=cv2.INTER_LINEAR if f > 1 else cv2.INTER_AREA)
        m = cv2.resize(m, size, interpolation=cv2.INTER_LINEAR)
    return _finish(img, m)


def read_crop(img_path: Path, mask_path: Path, gsd: float, loader: str = "rgb", *, crop: int,
              rng: np.random.Generator, scale_jitter: float = 0.3, target_gsd: float = TARGET_GSD_M):
    """Random crop×crop window at target_gsd (± scale jitter), cut from the original tile *before*
    resampling so a 1 m tile is never upsampled whole."""
    img, m = _load(img_path, mask_path, loader)
    f = gsd / target_gsd * rng.uniform(1 - scale_jitter, 1 + scale_jitter)
    win = max(1, round(crop / f))
    h, w = m.shape
    if h < win or w < win:  # pad with no-data (white image, empty mask)
        ph, pw = max(0, win - h), max(0, win - w)
        img = cv2.copyMakeBorder(img, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        m = cv2.copyMakeBorder(m, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=0)
        h, w = m.shape
    y, x = rng.integers(0, h - win + 1), rng.integers(0, w - win + 1)
    img, m = img[y:y + win, x:x + win], m[y:y + win, x:x + win]
    if win != crop:
        interp = cv2.INTER_LINEAR if crop > win else cv2.INTER_AREA
        img = cv2.resize(img, (crop, crop), interpolation=interp)
        m = cv2.resize(m, (crop, crop), interpolation=cv2.INTER_LINEAR)
    return _finish(img, m)


class SegTiles(Dataset):
    def __init__(self, items: list[Item], crop: int | None, train: bool,
                 target_gsd: float = TARGET_GSD_M):
        self.items, self.crop, self.train = items, crop, train
        self.target_gsd = target_gsd
        self.aug = A.Compose([
            A.D4(),
            A.ColorJitter(0.25, 0.25, 0.2, 0.03, p=0.6),
            A.GaussianBlur(blur_limit=(3, 5), p=0.1),
        ]) if train else None

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        if self.train:
            rng = np.random.default_rng(torch.randint(0, 2**31, ()).item())
            img, mask, valid = read_crop(*self.items[i], crop=self.crop, rng=rng,
                                         target_gsd=self.target_gsd)
            r = self.aug(image=img, masks=[mask, valid])
            img, (mask, valid) = r["image"], r["masks"]
        else:
            img, mask, valid = read_pair(*self.items[i], target_gsd=self.target_gsd)
        x = torch.from_numpy(((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1).copy())
        return x, torch.from_numpy(mask[None].copy()), torch.from_numpy(valid[None].copy())


# ------------------------------------------------------------------ land cover (multi-class)
# One taxonomy across sources; 255 = ignore (unlabelled / unknown).
LANDCOVER_CLASSES = ["other", "built_up", "agriculture", "rangeland", "forest", "water", "barren"]
IGNORE = 255

# DeepGlobe masks are RGB colour codes (class_dict.csv).
_DG_COLOURS = {(0, 255, 255): 1, (255, 255, 0): 2, (255, 0, 255): 3, (0, 255, 0): 4,
               (0, 0, 255): 5, (255, 255, 255): 6, (0, 0, 0): IGNORE}
# LoveDA: 0 ignore, 1 background, 2 building, 3 road, 4 water, 5 barren, 6 forest, 7 agricultural.
_LOVEDA_LUT = np.array([IGNORE, 0, 1, 1, 5, 6, 4, 2], np.uint8)
# OpenEarthMap: 0 unknown, 1 bareland, 2 rangeland, 3 developed space, 4 road, 5 tree, 6 water,
# 7 agriculture, 8 building.
_OEM_LUT = np.array([IGNORE, 6, 3, 1, 1, 4, 5, 2, 1], np.uint8)

LcItem = tuple[Path, Path, float, str]  # image, mask, gsd, mask decoder


def _decode_mask(path: Path, kind: str) -> np.ndarray:
    if kind == "deepglobe_rgb":
        rgb = cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        bits = (rgb > 127).astype(np.uint8)  # masks are near-binary per channel
        out = np.full(rgb.shape[:2], IGNORE, np.uint8)
        for (r, g, b), cls in _DG_COLOURS.items():
            out[(bits[..., 0] == (r > 0)) & (bits[..., 1] == (g > 0)) & (bits[..., 2] == (b > 0))] = cls
        return out
    idx = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if idx.ndim == 3:
        idx = idx[..., 0]
    lut = {"loveda": _LOVEDA_LUT, "oem": _OEM_LUT}[kind]
    return np.where(idx < len(lut), lut[np.minimum(idx, len(lut) - 1)], IGNORE).astype(np.uint8)


@lru_cache(None)
def _deepglobe_landcover():
    out: dict[str, list[LcItem]] = {"train": [], "val": [], "test": []}
    for sat in sorted((RAW / "deepglobe_landcover/train").glob("*_sat.jpg")):
        tile = sat.name[: -len("_sat.jpg")]
        out[hash_split(tile)].append((sat, sat.with_name(f"{tile}_mask.png"), 0.5, "deepglobe_rgb"))
    return out


@lru_cache(None)
def _loveda():
    """Official val (with masks) is our test; official train is hash-split into train/val.

    Uses the full Zenodo release (loveda_full, 2522 train tiles) when downloaded, else the HF mirror
    (1366 train tiles). Both have the same 1669 official val tiles, so test scores stay comparable."""
    full = RAW / "loveda_full"
    if (full / ".complete").exists():
        out: dict[str, list[LcItem]] = {"train": [], "val": [], "test": []}
        for official in ("Train", "Val"):
            for img in sorted(full.glob(f"{official}/*/images_png/*.png")):
                domain = img.parent.parent.name  # Urban / Rural
                item = (img, img.parent.parent / "masks_png" / img.name, 0.3, "loveda")
                if official == "Val":
                    out["test"].append(item)
                else:
                    out["val" if hash_split(f"{domain}_{img.stem}") != "train" else "train"].append(item)
        return out
    root = RAW / "loveda"
    out = {"train": [], "val": [], "test": []}
    for split, name in (("train", "train"), ("val", "val")):
        for img in sorted((root / f"urban:rural {name} images").glob("*.png")):
            item = (img, root / f"urban:rural {name} masks" / img.name, 0.3, "loveda")
            if split == "val":
                out["test"].append(item)
            else:
                out["val" if hash_split(img.stem) != "train" else "train"].append(item)
    return out


@lru_cache(None)
def _openearthmap():
    """Extracted by prepare_openearthmap.py; official val is our test, train is hash-split."""
    root = RAW / "openearthmap/prepared"
    out: dict[str, list[LcItem]] = {"train": [], "val": [], "test": []}
    for split in ("train", "val"):
        for img in sorted((root / split / "images").glob("*.png")):
            item = (img, root / split / "masks" / img.name, 0.5, "oem")
            if split == "val":
                out["test"].append(item)
            else:
                out["val" if hash_split(img.stem) != "train" else "train"].append(item)
    return out


LANDCOVER_SOURCES = {
    "deepglobe_landcover": lambda s: _deepglobe_landcover()[s],
    "loveda": lambda s: _loveda()[s],
    "openearthmap": lambda s: _openearthmap()[s],
}


def read_lc(img_path: Path, mask_path: Path, gsd: float, kind: str,
            crop: int | None = None, rng: np.random.Generator | None = None,
            scale_jitter: float = 0.3, target_gsd: float = TARGET_GSD_M):
    """(image, class-index mask) at target_gsd; a random crop×crop window when crop is given."""
    img = cv2.cvtColor(cv2.imread(str(img_path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    m = _decode_mask(mask_path, kind)
    f = gsd / target_gsd * (rng.uniform(1 - scale_jitter, 1 + scale_jitter) if crop else 1.0)
    if crop:
        win = max(1, round(crop / f))
        h, w = m.shape
        if h < win or w < win:
            ph, pw = max(0, win - h), max(0, win - w)
            img = cv2.copyMakeBorder(img, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            m = cv2.copyMakeBorder(m, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=IGNORE)
            h, w = m.shape
        y, x = rng.integers(0, h - win + 1), rng.integers(0, w - win + 1)
        img, m = img[y:y + win, x:x + win], m[y:y + win, x:x + win]
        size = (crop, crop)
    else:
        size = (round(img.shape[1] * f), round(img.shape[0] * f))
    if size != (img.shape[1], img.shape[0]):
        img = cv2.resize(img, size, interpolation=cv2.INTER_LINEAR if size[0] > img.shape[1] else cv2.INTER_AREA)
        m = cv2.resize(m, size, interpolation=cv2.INTER_NEAREST)
    return img, m


class LandCoverTiles(Dataset):
    def __init__(self, items: list[LcItem], crop: int | None, train: bool,
                 target_gsd: float = TARGET_GSD_M):
        self.items, self.crop, self.train = items, crop, train
        self.target_gsd = target_gsd
        self.aug = A.Compose([A.D4(), A.ColorJitter(0.25, 0.25, 0.2, 0.03, p=0.6)]) if train else None

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        if self.train:
            rng = np.random.default_rng(torch.randint(0, 2**31, ()).item())
            img, m = read_lc(*self.items[i], crop=self.crop, rng=rng, target_gsd=self.target_gsd)
            r = self.aug(image=img, mask=m)
            img, m = r["image"], r["mask"]
        else:
            img, m = read_lc(*self.items[i], target_gsd=self.target_gsd)
        x = torch.from_numpy(((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1).copy())
        return x, torch.from_numpy(m.astype(np.int64))


# ------------------------------------------------- ISPRS 2D semantic labelling (very high res)
# A task of its own, NOT folded into LANDCOVER_CLASSES: these tiles are 5-9 cm where the
# land-cover sources are 30-50 cm, and the taxonomy is different (a car class, and impervious
# surface split from building, neither of which the 7 shared classes express).
ISPRS_CLASSES = ["impervious", "building", "low_vegetation", "tree", "car", "clutter"]

# 0.1 m, chosen from what the two smallest structures in this data span (see
# docs/models/isprs_urban.md for the measurements):
#   * a labelled car component is 2.5 m x 4.2 m (Potsdam median axis-aligned bbox), i.e. 25 x 42 px
#     at 0.1 m but only 5 x 8 px at the 0.5 m land-cover GSD - below what a /32 encoder can place.
#   * ISPRS's own boundary tolerance is a 3 px erosion at native GSD = 0.15 m (Potsdam) / 0.27 m
#     (Vaihingen); at 0.1 m a roof edge is still ~3 px, so we do not train below their own
#     annotation precision.
# 0.1 m also keeps both cities on a *downsample* (0.05 -> 0.1 is an exact 2x box average,
# 0.09 -> 0.1 is 0.9x), so neither source is upsampled and no detail is invented.
ISPRS_GSD_M = 0.1

ISPRS_RAW = RAW / "isprs_potsdam_vaihingen"

# Every ISPRS label colour is a corner of the RGB cube, so one threshold per channel decodes them.
# Index is r*4 + g*2 + b of the thresholded channels; the two corners ISPRS does not use -
# black (the no-data value of the *_noBoundary eroded label sets) and magenta - become IGNORE.
_ISPRS_LUT = np.array([
    IGNORE,  # (0,0,0)       eroded boundary / no data
    1,       # (0,0,255)     building
    3,       # (0,255,0)     tree
    2,       # (0,255,255)   low vegetation
    5,       # (255,0,0)     clutter / background
    IGNORE,  # (255,0,255)   unused
    4,       # (255,255,0)   car
    0,       # (255,255,255) impervious surfaces
], np.uint8)

# image, label, gsd, 1-based band indices to read as the 3 network channels
IsprsItem = tuple[Path, Path, float, tuple[int, int, int]]


def decode_isprs_label(rgb: np.ndarray) -> np.ndarray:
    """RGB-coded ISPRS label -> class index array, IGNORE where unlabelled.

    Thresholding rather than exact colour matching is deliberate and load-bearing: two of the 38
    Potsdam label tiles are off-palette and an exact match silently drops their pixels.
    top_potsdam_4_12_label.tif was re-encoded lossily (24850 distinct colours, e.g. (9,222,221)
    for cyan) and matches nothing at all; top_potsdam_6_7_label.tif codes most of its cars
    (252,255,0) instead of (255,255,0). Both round to the right corner. Measured: with
    thresholding, 0 unknown pixels across all 71 label tiles and 0 pixels within 40 DN of the
    threshold, so the rounding is never close.
    """
    b = (rgb > 127).astype(np.uint8)
    return _ISPRS_LUT[b[..., 0] * 4 + b[..., 1] * 2 + b[..., 2]]


def isprs_split(tile_id: str) -> str:
    """Deterministic 70/15/15 by tile id. Same sha1 bucketing as hash_split, wider eval share.

    NOT the official ISPRS benchmark split: the official test tiles are the ones whose labels were
    withheld from participants, and we hold the COMPLETE ground truth, so scores here are not
    comparable to the ISPRS leaderboard (same caveat as the DeepGlobe split, project/qna.md Q-025).
    The land-cover 90/5/5 is wrong for this task at this tile count - it leaves Potsdam with 37
    train / 0 val / 1 test - and 'car' is ~1-2% of pixels, so per-class IoU needs more than one
    evaluation tile to mean anything. 70/15/15 gives Potsdam 29/5/4 and Vaihingen 22/5/6.
    """
    b = int(hashlib.sha1(tile_id.encode()).hexdigest(), 16) % 100
    return "test" if b < 15 else "val" if b < 30 else "train"


def _isprs_potsdam(subdir: str, suffix: str, bands: tuple[int, int, int]) -> dict[str, list[IsprsItem]]:
    """38 Potsdam tiles, 6000x6000 at 5 cm. Tile id is shared between the RGB and RGBIR variants
    so the two never disagree about which tiles are held out."""
    out: dict[str, list[IsprsItem]] = {"train": [], "val": [], "test": []}
    root = ISPRS_RAW / "Potsdam/Potsdam"
    for img in sorted((root / subdir / subdir).glob(f"*{suffix}.tif")):
        tile = img.stem[len("top_potsdam_"): -len(suffix)]
        label = root / "5_Labels_all" / f"top_potsdam_{tile}_label.tif"
        if label.exists():
            out[isprs_split(f"potsdam_{tile}")].append((img, label, 0.05, bands))
    return out


@lru_cache(None)
def _isprs_potsdam_rgb():
    return _isprs_potsdam("2_Ortho_RGB", "_RGB", (1, 2, 3))


@lru_cache(None)
def _isprs_potsdam_irrg():
    """Potsdam's 4-band ortho read as IR/R/G, i.e. Vaihingen's band order. Kept so a joint
    Potsdam+Vaihingen run is a flag change rather than a rewrite - see the doc for why the
    default is still one model per city."""
    return _isprs_potsdam("4_Ortho_RGBIR", "_RGBIR", (4, 1, 2))


@lru_cache(None)
def _isprs_vaihingen():
    """33 Vaihingen tiles, ~1900x2500 at 9 cm. Bands are IRRG, not RGB."""
    out: dict[str, list[IsprsItem]] = {"train": [], "val": [], "test": []}
    root = ISPRS_RAW / "Vaihingen/Vaihingen"
    gt = root / "ISPRS_semantic_labeling_Vaihingen_ground_truth_COMPLETE"
    for img in sorted((root / "ISPRS_semantic_labeling_Vaihingen/top").glob("*.tif")):
        label = gt / img.name
        if label.exists():
            area = img.stem[len("top_mosaic_09cm_"):]
            out[isprs_split(f"vaihingen_{area}")].append((img, label, 0.09, (1, 2, 3)))
    return out


ISPRS_SOURCES = {
    "isprs_potsdam": lambda s: _isprs_potsdam_rgb()[s],
    "isprs_potsdam_irrg": lambda s: _isprs_potsdam_irrg()[s],
    "isprs_vaihingen": lambda s: _isprs_vaihingen()[s],
}


def read_isprs(img_path: Path, label_path: Path, gsd: float, bands: tuple[int, int, int],
               crop: int | None = None, rng: np.random.Generator | None = None,
               scale_jitter: float = 0.2, target_gsd: float = ISPRS_GSD_M):
    """(image, class-index mask) at target_gsd; a random crop x crop window when crop is given.

    Unlike read_lc this never materialises the whole tile: a Potsdam tile is 6000x6000x3 (108 MB)
    and resampling it to pull one 512 px crop would dominate the data loader. The window is chosen
    in source pixels first and read through rasterio, so only the window is decoded - measured
    13 ms for a 1024 px window against 281 ms for the full tile.
    """
    with rasterio.open(img_path) as di, rasterio.open(label_path) as dl:
        h, w = di.height, di.width
        if crop:
            f = gsd / target_gsd * rng.uniform(1 - scale_jitter, 1 + scale_jitter)
            win = max(1, min(round(crop / f), h, w))  # clamped: Vaihingen tiles are only ~1900 px
            y, x = int(rng.integers(0, h - win + 1)), int(rng.integers(0, w - win + 1))
            window, size = Window(x, y, win, win), (crop, crop)
        else:
            f = gsd / target_gsd
            window = Window(0, 0, w, h)
            size = (max(1, round(w * f)), max(1, round(h * f)))
        img = di.read(bands, window=window).transpose(1, 2, 0)
        m = decode_isprs_label(dl.read((1, 2, 3), window=window).transpose(1, 2, 0))
    if size != (img.shape[1], img.shape[0]):
        interp = cv2.INTER_LINEAR if size[0] > img.shape[1] else cv2.INTER_AREA
        img = cv2.resize(img, size, interpolation=interp)
        m = cv2.resize(m, size, interpolation=cv2.INTER_NEAREST)
    return np.ascontiguousarray(img), m


class IsprsTiles(Dataset):
    """Same contract as LandCoverTiles (x, int64 mask), but windowed reads and no colour jitter.

    ColorJitter is dropped on purpose: half the channels here are near-infrared, where a hue or
    saturation shift is not a plausible nuisance transform, and the IR band is the main cue
    separating tree from low vegetation."""

    def __init__(self, items: list[IsprsItem], crop: int | None, train: bool,
                 target_gsd: float = ISPRS_GSD_M):
        self.items, self.crop, self.train = items, crop, train
        self.target_gsd = target_gsd
        self.aug = A.Compose([A.D4(), A.RandomBrightnessContrast(0.2, 0.2, p=0.5)]) if train else None

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        if self.train:
            rng = np.random.default_rng(torch.randint(0, 2**31, ()).item())
            img, m = read_isprs(*self.items[i], crop=self.crop, rng=rng, target_gsd=self.target_gsd)
            r = self.aug(image=img, mask=m)
            img, m = r["image"], r["mask"]
        else:
            img, m = read_isprs(*self.items[i], target_gsd=self.target_gsd)
        x = torch.from_numpy(((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1).copy())
        return x, torch.from_numpy(m.astype(np.int64))


# ------------------------------------------------------------------- multi-class task registry
# name -> (class list, source registry, default target GSD, Dataset class). train_landcover.py
# reads this so a new task needs no trainer edits; "landcover" reproduces the old defaults exactly.
SEG_TASKS: dict[str, tuple[list[str], dict, float, type[Dataset]]] = {
    "landcover": (LANDCOVER_CLASSES, LANDCOVER_SOURCES, TARGET_GSD_M, LandCoverTiles),
    "isprs_urban": (ISPRS_CLASSES, ISPRS_SOURCES, ISPRS_GSD_M, IsprsTiles),
}
