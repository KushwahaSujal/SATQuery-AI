# SatQuery AI — Real Sentinel-2 Demo Pair & AOI

This directory contains an authentic, georeferenced satellite remote-sensing before/after pair and an Area of Interest (AOI) polygon prepared for the SatQuery AI demonstration.

---

## 1. Provenance & Technical Metadata

Both images were extracted from genuine European Space Agency (ESA) Copernicus Sentinel-2B Level-2A products hosted on the AWS Element84 Open Data STAC catalog.

> [!NOTE]
> **TCI Visual Asset Specification**:
> The demo GeoTIFFs are derived from the official **Sentinel-2 Level-2A True Color Image (TCI) visual asset** (`TCI.tif`).
> They are **3-band RGB `uint8` visual rasters** representing cartographic true-color imagery (channels corresponding to Sentinel-2 Red=`B04`, Green=`B03`, Blue=`B02`).
> They should **not** be confused with the original 12/16-bit quantitative multispectral BOA surface reflectance bands (e.g. `B04.tif`, `B08.tif`), which are stored separately in the upstream L2A archive.

| Attribute | Before Acquisition | After Acquisition | Verification Status |
| :--- | :--- | :--- | :--- |
| **Product ID** | `S2B_30SYJ_20240414_0_L2A` | `S2B_30SYJ_20240723_0_L2A` | `VERIFIED` (ESA Product ID) |
| **Platform** | Sentinel-2B | Sentinel-2B | `VERIFIED` (`properties.platform`) |
| **Sensor / Instrument** | MultiSpectral Instrument (MSI) | MultiSpectral Instrument (MSI) | `VERIFIED` (`properties.instruments`) |
| **Processing Level** | Level-2A (BOA Reflectance Product) | Level-2A (BOA Reflectance Product) | `VERIFIED` (`collection: sentinel-2-l2a`) |
| **Source Asset** | True Color Image (`visual` / `TCI.tif`) | True Color Image (`visual` / `TCI.tif`) | `VERIFIED` (`assets.visual.href`) |
| **Processing Baseline**| `05.10` | `05.11` | `VERIFIED` (`properties.s2:processing_baseline`) |
| **Acquisition Datetime**| `2024-04-14T11:00:15.798000Z` | `2024-07-23T11:00:18.195000Z` | `VERIFIED` (`properties.datetime`) |
| **MGRS Granule** | `30SYJ` | `30SYJ` | `VERIFIED` (`properties.grid:code`) |
| **Geographic Region** | Albufera / Valencia, Spain | Albufera / Valencia, Spain | `VERIFIED` |
| **Scene Cloud Cover** | 0.003971% | 0.006702% | `VERIFIED` (`properties.eo:cloud_cover`) |
| **CRS** | `EPSG:32630` (UTM Zone 30N) | `EPSG:32630` (UTM Zone 30N) | `VERIFIED` (GeoTIFF header / `rasterio`) |
| **Pixel Dimensions** | 512 x 512 pixels | 512 x 512 pixels | `VERIFIED` (GeoTIFF header) |
| **Ground Resolution** | 10.0 m / pixel | 10.0 m / pixel | `VERIFIED` (Pixel size `[10.0, 10.0]`) |
| **Spatial Extent** | `(727960.0, 4354920.0, 733080.0, 4360040.0)` | `(727960.0, 4354920.0, 733080.0, 4360040.0)` | `VERIFIED` (Native UTM Bounds) |
| **Total Coverage** | 5.12 km x 5.12 km (26.21 km²) | 5.12 km x 5.12 km (26.21 km²) | `VERIFIED` |
| **Band Count** | 3 (Red=B04, Green=B03, Blue=B02) | 3 (Red=B04, Green=B03, Blue=B02) | `VERIFIED` (Visual TCI Bands) |
| **Data Type** | `uint8` visual imagery | `uint8` visual imagery | `VERIFIED` (Raster data type) |
| **Pixel Grid Alignment**| Identical transform, resolution, CRS | Identical transform, resolution, CRS | `VERIFIED` (100.0% spatial overlap) |
| **File Size** | 706.18 KB (`before.tif`) | 812.99 KB (`after.tif`) | `VERIFIED` (On-disk size) |

Complete official STAC item metadata JSON documents downloaded directly from the catalog are preserved in:
- `datasets/samples/demo/source_metadata_before.json`
- `datasets/samples/demo/source_metadata_after.json`

---

## 2. Epistemological Framework: Imagery vs. Facts vs. Annotations

To maintain strict adherence to zero-fabrication standards, this repository maintains rigorous distinctions between:

- **A. Authentic Satellite Imagery**: The pixel arrays in `before.tif` and `after.tif` are raw crops from official ESA Sentinel-2B Level-2A TCI products. They are not synthetic, generated, or artificially manipulated.
- **B. Independently Measurable Geospatial Facts**: The CRS (`EPSG:32630`), pixel resolution (10.0 m), bounding box coordinates, raster dimensions (512x512), acquisition datetimes, and projected polygon area (758,800.00 m²) are measurable mathematical and physical facts verified directly from file headers and metadata.
- **C. Pre-Inference Expected Physical/Visual Observations**: Human qualitative observations of visible landscape differences (e.g. dry fallow soil vs. water inundation and crop emergence) written *prior* to model inference.
- **D. Model-Generated Results**: Any downstream inference outputs (e.g., from ChangeFormer, CDVQA, or DOFA). These represent algorithmic predictions subject to evaluation, not ground truth.
- **E. Unavailable Ground-Truth Annotations**: Unlike synthetic benchmarks or curated benchmark datasets (e.g., LEVIR-CD), **there is NO human-annotated pixel-level ground truth change mask** for this natural satellite acquisition pair.
  - Exact quantitative changed pixel count: **`NOT MEASURED`**
  - Exact quantitative changed area: **`NOT MEASURED`**
  - Pixel-level ground-truth mask: **`NOT AVAILABLE`**

Under no circumstances should model-generated outputs be retroactively declared as benchmark ground truth.

---

## 3. Real Area of Interest (AOI) Specification

The AOI is defined in [`aoi.geojson`](file:///c:/Users/user/Desktop/SATQuery/satquery-ai/datasets/samples/demo/aoi.geojson) as a valid GeoJSON FeatureCollection.

- **Geometry Type**: `Polygon`
- **CRS Convention**: `EPSG:4326` (WGS84 longitude/latitude standard, RFC 7946)
- **Coordinates (WGS84)**:
  - Longitude range: `[-0.34884, -0.33480]`
  - Latitude range: `[39.31563, 39.32225]`
- **Calculated Metric Area**: **758,800.00 m² (75.88 hectares)**
  - Computed strictly via native projected UTM CRS (`EPSG:32630`), *never* via latitude/longitude degree arithmetic.
- **Spatial Relationship to Rasters**:
  - Intersects Before Raster: `True`
  - Lies Strictly Inside Raster Footprint: `True`
  - Intersects After Raster: `True`
  - Valid Geometry: `TRUE`

---

## 4. Pre-Inference Query & Expected Observation

Written **prior to running model inference** based on independently observable landscape changes:

### Intended Demo Query
> *"What land-cover and surface moisture change occurred within this agricultural AOI between April 2024 and July 2024?"*

### Pre-Inference Expected Physical/Visual Observation
1. **Seasonal Hydrological & Agricultural Transition**:
   - In the April 2024 acquisition, the parcel displays light-brown, dry, exposed tilled agricultural soil.
   - In the July 2024 acquisition, the parcel displays extensive dark water inundation and emergent bright green vegetative growth characteristic of summer rice cultivation in the Albufera wetland agricultural basin.
2. **Infrastructure Invariance**:
   - Surrounding drainage channels, canals, field boundaries, and access roads maintain exact pixel co-registration with zero spatial shift.
3. **Quantitative Metrics**:
   - Exact numerical percentage change: **`NOT MEASURED`** (No independent ground-truth vector annotation exists; zero-fabrication rules prohibit inventing a numerical value).
