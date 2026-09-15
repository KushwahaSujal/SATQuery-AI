"""
Validation script for the real demo GeoTIFF pair.
Uses both backend.app.geo.raster.RasterInspector and rasterio directly.
Compares CRS, bounds, dimensions, resolution, transform, overlap, and bands.
Produces a side-by-side visual comparison for human verification.
"""
import sys
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import rasterio
from backend.app.geo.raster import RasterInspector

DEMO_DIR = REPO_ROOT / "datasets" / "samples" / "demo"
path_before = DEMO_DIR / "before.tif"
path_after = DEMO_DIR / "after.tif"

print("=" * 75)
print("SATQUERY AI — DEMO GEOTIFF PAIR VALIDATION REPORT")
print("=" * 75)

# 1. Inspect using Project's RasterInspector
meta_before = RasterInspector.inspect(path_before)
meta_after = RasterInspector.inspect(path_after)

def print_raster_report(label: str, path: Path, meta):
    with rasterio.open(path) as src:
        size_kb = path.stat().st_size / 1024
        print(f"\n--- {label} ---")
        print(f"  File Path:       {path.resolve()}")
        print(f"  File Size:       {size_kb:.2f} KB")
        print(f"  Format:          {meta.format}")
        print(f"  CRS:             {meta.crs}")
        print(f"  Dimensions:      {meta.width} x {meta.height}")
        print(f"  Band Count:      {meta.bands}")
        print(f"  Dtype:           {meta.dtype}")
        print(f"  Transform:       {meta.transform}")
        print(f"  Bounds:          {meta.bounds}")
        print(f"  Resolution:      {meta.resolution}")
        print(f"  Nodata:          {meta.nodata}")
        print(f"  Georeferenced:   {meta.is_georeferenced}")
        print(f"  Tags:            {json.dumps(meta.tags, indent=4)}")

print_raster_report("BEFORE ACQUISITION", path_before, meta_before)
print_raster_report("AFTER ACQUISITION", path_after, meta_after)

# 2. Programmatic Comparison
print("\n" + "=" * 75)
print("PROGRAMMATIC COMPARISON (BEFORE vs AFTER)")
print("=" * 75)

crs_equal = (meta_before.crs == meta_after.crs) and (meta_before.crs is not None)
bounds_equal = (meta_before.bounds == meta_after.bounds) and (meta_before.bounds is not None)
dims_equal = (meta_before.width == meta_after.width) and (meta_before.height == meta_after.height)
res_equal = (meta_before.resolution == meta_after.resolution)
transform_equal = (meta_before.transform == meta_after.transform)
bands_equal = (meta_before.bands == meta_after.bands)
dtype_equal = (meta_before.dtype == meta_after.dtype)
nodata_equal = (meta_before.nodata == meta_after.nodata)

# Compute geographic overlap
b1 = meta_before.bounds
b2 = meta_after.bounds
x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
overlap_area = x_overlap * y_overlap
total_area = (b1[2] - b1[0]) * (b1[3] - b1[1])
overlap_ratio = overlap_area / total_area if total_area > 0 else 0.0

print(f"  1. CRS Equality:            {crs_equal} ({meta_before.crs})")
print(f"  2. Spatial Bounds Equality: {bounds_equal} ({meta_before.bounds})")
print(f"  3. Raster Dimensions Match: {dims_equal} ({meta_before.width}x{meta_before.height})")
print(f"  4. Pixel Resolution Match:  {res_equal} ({meta_before.resolution})")
print(f"  5. Transform Match:         {transform_equal}")
print(f"  6. Geographic Overlap:      {overlap_ratio * 100:.1f}%")
print(f"  7. Band Compatibility:      {bands_equal} ({meta_before.bands} bands, {meta_before.dtype})")
print(f"  8. Nodata Compatibility:    {nodata_equal} (before={meta_before.nodata}, after={meta_after.nodata})")

assert crs_equal, "CRS check failed"
assert bounds_equal, "Bounds check failed"
assert dims_equal, "Dimensions check failed"
assert res_equal, "Resolution check failed"
assert transform_equal, "Transform check failed"
assert overlap_ratio == 1.0, "Overlap check failed"
assert bands_equal, "Band check failed"
assert dtype_equal, "Dtype check failed"

print("\n>>> ALL GEOSPATIAL ALIGNMENT & INTEGRITY ASSERTIONS PASSED <<<")

# 3. Generate Side-by-Side Visual Comparison
with rasterio.open(path_before) as s1, rasterio.open(path_after) as s2:
    arr1 = s1.read()  # (3, 512, 512)
    arr2 = s2.read()  # (3, 512, 512)

img1 = Image.fromarray(np.transpose(arr1, (1, 2, 0)), "RGB")
img2 = Image.fromarray(np.transpose(arr2, (1, 2, 0)), "RGB")

# Composite side-by-side image with header and annotations
canvas_w = 512 * 2 + 30
header_h = 70
canvas_h = 512 + header_h + 30
canvas = Image.new("RGB", (canvas_w, canvas_h), color=(24, 28, 36))
draw = ImageDraw.Draw(canvas)

# Place images
canvas.paste(img1, (10, header_h))
canvas.paste(img2, (512 + 20, header_h))

# Draw text headers
draw.text((15, 12), "SATQUERY AI — GENUINE SENTINEL-2 DEMO PAIR (MGRS 30SYJ, EPSG:32630)", fill=(255, 255, 255))
draw.text((15, 36), f"BEFORE: 2024-04-14 (Spring / S2B) | 512x512 px @ 10m GSD", fill=(100, 200, 255))
draw.text((512 + 25, 36), f"AFTER:  2024-07-23 (Summer / S2B) | 512x512 px @ 10m GSD", fill=(120, 255, 150))

preview_path = DEMO_DIR / "preview_comparison.png"
canvas.save(preview_path)
print(f"\n[OK] Visual comparison composite saved to: {preview_path.resolve()}")
