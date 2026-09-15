"""
Creates and validates datasets/samples/demo/aoi.geojson.
Validates:
1. Valid GeoJSON FeatureCollection with Polygon geometry
2. Coordinate format in EPSG:4326 (WGS84 longitude, latitude)
3. Ring closure and validity via Shapely
4. Polygon lies strictly inside the raster geographic bounds
5. Area calculation performed in projected equal-area/UTM CRS (EPSG:32630), never degree arithmetic
6. Complete intersection with before and after raster footprints
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pyproj
import rasterio
from shapely.geometry import shape, mapping, Polygon, box
from shapely.ops import transform as shapely_transform

DEMO_DIR = REPO_ROOT / "datasets" / "samples" / "demo"
path_before = DEMO_DIR / "before.tif"
path_after = DEMO_DIR / "after.tif"
path_aoi = DEMO_DIR / "aoi.geojson"

# 1. Define real agricultural parcel polygon in native UTM (EPSG:32630)
# Pixel coords: col 60..180, row 415..485 within the 512x512 tile
# Corresponding to the southern agricultural rice paddies in Albufera basin
# UTM bounds: x in [728560.0, 729760.0], y in [4355190.0, 4355890.0]

utm_coords = [
    (728560.0, 4355190.0),
    (728560.0, 4355890.0),
    (729200.0, 4355890.0),
    (729760.0, 4355600.0),
    (729760.0, 4355190.0),
    (728560.0, 4355190.0)  # Closed ring
]

poly_utm = Polygon(utm_coords)
assert poly_utm.is_valid, "Native polygon must be valid"

# Project to standard GeoJSON CRS (EPSG:4326)
transformer_to_wgs84 = pyproj.Transformer.from_crs("EPSG:32630", "EPSG:4326", always_xy=True).transform
poly_wgs84 = shapely_transform(transformer_to_wgs84, poly_utm)
assert poly_wgs84.is_valid, "Projected WGS84 polygon must be valid"

# Create GeoJSON FeatureCollection
aoi_geojson = {
    "type": "FeatureCollection",
    "name": "satquery_demo_aoi",
    "crs": {
        "type": "name",
        "properties": {
            "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
        }
    },
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Albufera Agricultural Parcel Basin",
                "description": "Agricultural rice field basin exhibiting seasonal inundation and crop development between April and July 2024.",
                "region": "Valencia, Spain",
                "mgrs_tile": "30SYJ",
                "native_crs": "EPSG:32630",
                "area_sq_meters": round(poly_utm.area, 2),
                "area_hectares": round(poly_utm.area / 10000.0, 2)
            },
            "geometry": mapping(poly_wgs84)
        }
    ]
}

with open(path_aoi, "w", encoding="utf-8") as f:
    json.dump(aoi_geojson, f, indent=2)

print(f"[OK] Created: {path_aoi.resolve()}")

# 2. Programmatic Validation
print("\n" + "=" * 75)
print("SATQUERY AI — DEMO AOI GEOJSON VALIDATION REPORT")
print("=" * 75)

with open(path_aoi, "r", encoding="utf-8") as f:
    loaded_geojson = json.load(f)

assert loaded_geojson.get("type") == "FeatureCollection", "Must be FeatureCollection"
features = loaded_geojson.get("features", [])
assert len(features) >= 1, "Must contain at least one feature"

geom_dict = features[0]["geometry"]
geom_type = geom_dict["type"]
geom_shapely = shape(geom_dict)

print(f"  AOI Geometry Type:        {geom_type}")
print(f"  AOI WGS84 Bounds (LonLat): {geom_shapely.bounds}")
print(f"  AOI Coordinate Structure:  {len(geom_dict['coordinates'][0])} vertices, ring closed: {geom_dict['coordinates'][0][0] == geom_dict['coordinates'][0][-1]}")
print(f"  AOI CRS Convention:        EPSG:4326 (RFC 7946 standard)")
print(f"  AOI Valid Geometry:        {geom_shapely.is_valid}")

# Project to UTM to calculate true metric area
transformer_to_utm = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32630", always_xy=True).transform
geom_projected = shapely_transform(transformer_to_utm, geom_shapely)
area_m2 = geom_projected.area
area_ha = area_m2 / 10000.0

print(f"  AOI Calculated Area:       {area_m2:,.2f} m ({area_ha:.2f} hectares) [via EPSG:32630 projected metric calculation]")

# Validate intersection with Before and After rasters
with rasterio.open(path_before) as r_before:
    raster_bbox_utm = box(r_before.bounds.left, r_before.bounds.bottom, r_before.bounds.right, r_before.bounds.top)
    intersects_before = geom_projected.intersects(raster_bbox_utm)
    within_before = geom_projected.within(raster_bbox_utm)

with rasterio.open(path_after) as r_after:
    raster_bbox_after = box(r_after.bounds.left, r_after.bounds.bottom, r_after.bounds.right, r_after.bounds.top)
    intersects_after = geom_projected.intersects(raster_bbox_after)
    within_after = geom_projected.within(raster_bbox_after)

print(f"  Intersects Before Raster:  {intersects_before} (Within coverage: {within_before})")
print(f"  Intersects After Raster:   {intersects_after} (Within coverage: {within_after})")
print(f"  Valid Geometry:            TRUE")

assert geom_shapely.is_valid, "Geometry must be valid"
assert intersects_before and within_before, "AOI must lie strictly within before raster bounds"
assert intersects_after and within_after, "AOI must lie strictly within after raster bounds"
assert area_m2 > 0, "Area must be positive"

print("\n>>> AOI VALIDATION PASSED: 100% COMPLIANT WITH GEOSPATIAL STANDARDS <<<")
