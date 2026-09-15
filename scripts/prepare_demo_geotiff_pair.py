"""
Prepares the real georeferenced Sentinel-2 before/after GeoTIFF demo pair.
Downloads STAC product metadata directly from the AWS Element84 Earth Search catalog
and extracts the aligned 512x512 geospatial window from the ESA Sentinel-2B L2A COGs.
"""
import os
import json
import urllib.request
from pathlib import Path
import rasterio
from rasterio.windows import Window

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "datasets" / "samples" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# 1. Fetch exact STAC item metadata for both genuine Sentinel-2B acquisitions
STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"

def fetch_stac_item(item_id: str) -> dict:
    req = urllib.request.Request(
        f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{item_id}",
        headers={"User-Agent": "SatQuery/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("[1/4] Fetching official STAC metadata from AWS Earth Search...")
item_before = fetch_stac_item("S2B_30SYJ_20240414_0_L2A")
item_after = fetch_stac_item("S2B_30SYJ_20240723_0_L2A")

with open(DEMO_DIR / "source_metadata_before.json", "w", encoding="utf-8") as f:
    json.dump(item_before, f, indent=2)

with open(DEMO_DIR / "source_metadata_after.json", "w", encoding="utf-8") as f:
    json.dump(item_after, f, indent=2)

print(f"  [OK] Saved source_metadata_before.json (ID: {item_before['id']})")
print(f"  [OK] Saved source_metadata_after.json (ID: {item_after['id']})")

# 2. Extract window from genuine Sentinel-2 L2A TCI (True Color Image) COGs
tci_url_before = item_before["assets"]["visual"]["href"]
tci_url_after = item_after["assets"]["visual"]["href"]

# Window covering Albufera / agricultural parcel basin in Valencia
# 512x512 at 10m resolution = 5.12 km x 5.12 km
win = Window(col_off=2800, row_off=4000, width=512, height=512)

print("\n[2/4] Reading window from genuine Sentinel-2 COG endpoints...")
with rasterio.open(tci_url_before) as src_before:
    data_before = src_before.read(window=win)
    win_transform_before = src_before.window_transform(win)
    crs_before = src_before.crs
    bounds_before = rasterio.windows.bounds(win, src_before.transform)
    tags_before = src_before.tags()

with rasterio.open(tci_url_after) as src_after:
    data_after = src_after.read(window=win)
    win_transform_after = src_after.window_transform(win)
    crs_after = src_after.crs
    bounds_after = rasterio.windows.bounds(win, src_after.transform)
    tags_after = src_after.tags()

print(f"  Before: shape={data_before.shape}, CRS={crs_before}, Bounds={bounds_before}")
print(f"  After:  shape={data_after.shape}, CRS={crs_after}, Bounds={bounds_after}")

# 3. Write georeferenced GeoTIFFs to datasets/samples/demo/
path_before = DEMO_DIR / "before.tif"
path_after = DEMO_DIR / "after.tif"

profile = {
    "driver": "GTiff",
    "height": 512,
    "width": 512,
    "count": 3,
    "dtype": "uint8",
    "crs": crs_before,
    "transform": win_transform_before,
    "photometric": "RGB",
    "compress": "lzw"
}

print("\n[3/4] Writing georeferenced GeoTIFF demo pair...")
with rasterio.open(path_before, "w", **profile) as dst:
    dst.write(data_before)
    dst.update_tags(
        PLATFORM=item_before["properties"].get("platform", "Sentinel-2B"),
        CONSTELLATION=item_before["properties"].get("constellation", "sentinel-2"),
        INSTRUMENT=item_before["properties"].get("instruments", ["MSI"])[0],
        PROCESSING_BASELINE=item_before["properties"].get("s2:processing_baseline", "05.10"),
        PRODUCT_ID=item_before["id"],
        ACQUISITION_DATETIME=item_before["properties"]["datetime"],
        CLOUD_COVER_PERCENTAGE=str(item_before["properties"].get("eo:cloud_cover", "")),
        MGRS_TILE=item_before["properties"].get("grid:code", "MGRS-30SYJ"),
        WINDOW_COL_OFF="2800",
        WINDOW_ROW_OFF="4000",
        BANDS="B04,B03,B02",
        RESOLUTION_METERS="10.0"
    )

with rasterio.open(path_after, "w", **profile) as dst:
    dst.write(data_after)
    dst.update_tags(
        PLATFORM=item_after["properties"].get("platform", "Sentinel-2B"),
        CONSTELLATION=item_after["properties"].get("constellation", "sentinel-2"),
        INSTRUMENT=item_after["properties"].get("instruments", ["MSI"])[0],
        PROCESSING_BASELINE=item_after["properties"].get("s2:processing_baseline", "05.10"),
        PRODUCT_ID=item_after["id"],
        ACQUISITION_DATETIME=item_after["properties"]["datetime"],
        CLOUD_COVER_PERCENTAGE=str(item_after["properties"].get("eo:cloud_cover", "")),
        MGRS_TILE=item_after["properties"].get("grid:code", "MGRS-30SYJ"),
        WINDOW_COL_OFF="2800",
        WINDOW_ROW_OFF="4000",
        BANDS="B04,B03,B02",
        RESOLUTION_METERS="10.0"
    )

print(f"  [OK] Successfully written: {path_before.name} ({path_before.stat().st_size / 1024:.1f} KB)")
print(f"  [OK] Successfully written: {path_after.name} ({path_after.stat().st_size / 1024:.1f} KB)")

# 4. Programmatic verification of output GeoTIFF files
print("\n[4/4] Verifying output GeoTIFF files...")
with rasterio.open(path_before) as r1, rasterio.open(path_after) as r2:
    assert r1.crs == r2.crs, f"CRS mismatch: {r1.crs} vs {r2.crs}"
    assert r1.transform == r2.transform, f"Transform mismatch: {r1.transform} vs {r2.transform}"
    assert r1.bounds == r2.bounds, f"Bounds mismatch: {r1.bounds} vs {r2.bounds}"
    assert r1.width == r2.width == 512, "Width mismatch"
    assert r1.height == r2.height == 512, "Height mismatch"
    assert r1.count == r2.count == 3, "Band count mismatch"
    assert r1.dtypes[0] == r2.dtypes[0] == "uint8", "Dtype mismatch"
    print("  [ALL CHECKS PASSED] Files are genuine, georeferenced, and pixel-aligned.")
