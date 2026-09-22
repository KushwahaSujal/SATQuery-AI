/**
 * Catalog of the sample assets committed to this repo under `demo_resources/`.
 *
 * Every entry below corresponds to files that exist on disk (verified by listing
 * `demo_resources/` — 54 files, 35 MB). Byte sizes and pixel dimensions were read
 * from the files themselves; prompts, measured results and caveats are quoted from
 * `demo_resources/README.md`. Nothing here is inferred: fields the README does not
 * state (acquisition dates for the VRSBench scenes, ground resolution, sensor,
 * cloud cover, licence, accuracy) are simply absent rather than filled in.
 *
 * Hardcoding is deliberate — these files are committed to the repo, so the list is
 * a static fact about the tree, not a stand-in for an API. There is no datasets API.
 */

export const DEMO_RESOURCES_ROOT = "demo_resources";

/** How the measurements in this catalog were produced, per demo_resources/README.md. */
export const MEASUREMENT_PROVENANCE =
  "All results below were measured on 2026-09-15 on the prototype branch with the real models (RTX 3070, 8 GB), through the HTTP API and, for one case, the web UI.";

export const ROUTING_NOTE =
  "All masking prompts route to workflow_grounding with grounding_dino + sam2. Only the top-ranked instance goes through the verification agent; extra instances are detector boxes that passed the colour/relation checks.";

export type DemoCategoryId =
  | "masking"
  | "change_detection"
  | "optical_sar"
  | "video"
  | "known_weak";

export interface DemoCategory {
  id: DemoCategoryId;
  label: string;
  folder: string;
  /** Short, honest framing of what the folder is for. */
  blurb: string;
  /** True for folder 5 — kept visible on purpose. */
  knownWeak?: boolean;
}

export const DEMO_CATEGORIES: DemoCategory[] = [
  {
    id: "masking",
    label: "Masking",
    folder: "1_masking",
    blurb: "Single images. Each was run through the grounding + SAM2 masking workflow.",
  },
  {
    id: "change_detection",
    label: "Change detection",
    folder: "2_change_detection",
    blurb: "Before/after pairs. Upload both files (before then after) in one upload.",
  },
  {
    id: "optical_sar",
    label: "Optical + SAR",
    folder: "3_optical_sar",
    blurb: "One co-registered optical/SAR pair. The fusion head is not configured and the system refuses.",
  },
  {
    id: "video",
    label: "Video",
    folder: "4_video",
    blurb: "Two clips for the video workflow.",
  },
  {
    id: "known_weak",
    label: "Known weak",
    folder: "5_known_weak",
    blurb:
      "Kept in the repo, and kept visible here, so nobody picks these by accident. The README marks every one of them as a known failure. Not for demos.",
    knownWeak: true,
  },
];

export type FileRole =
  | "input"
  | "before"
  | "after"
  | "ground_truth"
  | "aoi"
  | "expected_output";

export interface DemoFile {
  /** Path relative to demo_resources/, exactly as it is on disk. */
  path: string;
  role: FileRole;
  label: string;
  /** On-disk size in bytes. */
  bytes: number;
  /** Pixel dimensions, read from the PNG header. Absent for non-PNG files. */
  pixels?: string;
  /** False for GeoTIFF: browsers cannot render it. */
  previewable: boolean;
}

export interface DemoRun {
  prompt: string;
  /** Measured result, quoted from the README. */
  result: string;
  note?: string;
  /** Path (relative to demo_resources/) of the overlay the backend produced. */
  overlay?: string;
}

export interface DemoMetaField {
  label: string;
  value: string;
}

export interface DemoResource {
  id: string;
  name: string;
  category: DemoCategoryId;
  /** Folder within demo_resources/ that holds this entry's input files. */
  folder: string;
  /** Where the imagery came from, per the README's Sources section. */
  provenance: string;
  /** Scene description, quoted or condensed from the README. */
  description?: string;
  files: DemoFile[];
  runs: DemoRun[];
  /** Path of the image to show as the thumbnail; omitted when nothing is previewable. */
  thumbnail?: string;
  /** Explains what the thumbnail actually is, when it is not the input itself. */
  thumbnailCaption?: string;
  /** Verbatim caveat from the README. */
  caveat?: string;
  /** For known-weak entries: what goes wrong, quoted from the README. */
  failure?: string;
  /** Approximate duration as the README gives it (videos only). */
  duration?: string;
  /** Extra documented metadata, each value traceable to a file in the repo. */
  meta?: DemoMetaField[];
  /** Source of the `meta` block, shown next to it. */
  metaSource?: string;
  /** Set when the README records no measured run for this entry. */
  notMeasured?: boolean;
}

export const DEMO_RESOURCES: DemoResource[] = [
  // ---------------------------------------------------------------- 1_masking
  {
    id: "P0725_street",
    name: "Street with houses, trees and cars",
    category: "masking",
    folder: "1_masking",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    description:
      "A street with an orange-tile-roofed house, grey houses, trees along the road, parked cars, a jetty.",
    thumbnail: "1_masking/street_houses_trees_cars__P0725_0005.png",
    files: [
      {
        path: "1_masking/street_houses_trees_cars__P0725_0005.png",
        role: "input",
        label: "Input image",
        bytes: 501791,
        pixels: "512 x 512",
        previewable: true,
      },
      { path: "1_masking/expected_outputs/P0725__mask_trees.png", role: "expected_output", label: "Overlay: mask trees", bytes: 531801, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0725__mark_trees_near_houses.png", role: "expected_output", label: "Overlay: mark trees near houses", bytes: 531815, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0725__mark_cars_near_houses.png", role: "expected_output", label: "Overlay: mark cars near houses", bytes: 534769, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0725__find_cars_near_red_house.png", role: "expected_output", label: "Overlay: find cars near red house", bytes: 536475, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0725__mask_houses_near_cars.png", role: "expected_output", label: "Overlay: mask houses near cars", bytes: 525663, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0725__mask_houses.png", role: "expected_output", label: "Overlay: mask houses", bytes: 525073, pixels: "512 x 512", previewable: true },
    ],
    runs: [
      { prompt: "mask trees", result: "8 trees", note: "Street trees and yard trees", overlay: "1_masking/expected_outputs/P0725__mask_trees.png" },
      { prompt: "mark trees near houses", result: "9 trees", note: "Also shown in the web UI: 9 masks, confidence 87.7%", overlay: "1_masking/expected_outputs/P0725__mark_trees_near_houses.png" },
      { prompt: "mark cars near houses", result: "11 masks", note: "Most on real cars; 2 false positives on rooftops", overlay: "1_masking/expected_outputs/P0725__mark_cars_near_houses.png" },
      { prompt: "find cars near red house", result: "3 cars", note: "Only cars beside the orange-tile house", overlay: "1_masking/expected_outputs/P0725__find_cars_near_red_house.png" },
      { prompt: "mask houses near cars", result: "3 houses", note: "Correctly drops the jetty", overlay: "1_masking/expected_outputs/P0725__mask_houses_near_cars.png" },
      { prompt: "mask houses", result: "4 masks", note: "Misses the grey houses; masks the jetty as a house", overlay: "1_masking/expected_outputs/P0725__mask_houses.png" },
      { prompt: "mark houses near trees", result: "4 houses", note: "Same set as “mask houses”" },
      { prompt: "mask cars near white houses", result: "1 car, with a message", note: "No white houses here; answer says no instance satisfied the conditions" },
    ],
  },
  {
    id: "P0897_suburb",
    name: "Suburb with white roofs and red cars",
    category: "masking",
    folder: "1_masking",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    description:
      "A suburb with ~25 houses (5 with white roofs), small cars, two red cars beside a big white house.",
    thumbnail: "1_masking/suburb_white_houses_red_cars__P0897_0048.png",
    caveat:
      "Colour prompt tip from the README: white, red and dark work on roofs and red cars. White cars score low (small masks with shadow) — avoid “mask white cars”.",
    files: [
      { path: "1_masking/suburb_white_houses_red_cars__P0897_0048.png", role: "input", label: "Input image", bytes: 533596, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0897__mask_white_houses.png", role: "expected_output", label: "Overlay: mask white houses", bytes: 576347, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0897__mask_red_cars.png", role: "expected_output", label: "Overlay: mask red cars", bytes: 577332, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0897__mask_cars_near_white_houses.png", role: "expected_output", label: "Overlay: mask cars near white houses", bytes: 577125, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0897__mark_cars_near_houses.png", role: "expected_output", label: "Overlay: mark cars near houses", bytes: 576240, pixels: "512 x 512", previewable: true },
    ],
    runs: [
      { prompt: "mask white houses", result: "5 houses", note: "Exactly the white roofs (colour checked on mask pixels)", overlay: "1_masking/expected_outputs/P0897__mask_white_houses.png" },
      { prompt: "mask red cars", result: "2 cars", note: "The two red cars", overlay: "1_masking/expected_outputs/P0897__mask_red_cars.png" },
      { prompt: "mask cars near white houses", result: "5 cars", note: "Each beside a white building; the red cars were not proposed by the detector for “cars”", overlay: "1_masking/expected_outputs/P0897__mask_cars_near_white_houses.png" },
      { prompt: "mark cars near houses", result: "15 cars", note: "Small masks along the streets", overlay: "1_masking/expected_outputs/P0897__mark_cars_near_houses.png" },
    ],
  },
  {
    id: "P0173_airport",
    name: "Airport apron with light aircraft",
    category: "masking",
    folder: "1_masking",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    description: "Airport apron with six light aircraft.",
    thumbnail: "1_masking/airport_airplanes__P0173_0003.png",
    files: [
      { path: "1_masking/airport_airplanes__P0173_0003.png", role: "input", label: "Input image", bytes: 434137, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0173__mask_airplanes.png", role: "expected_output", label: "Overlay: mask airplanes", bytes: 434335, pixels: "512 x 512", previewable: true },
    ],
    runs: [
      { prompt: "mask airplanes", result: "9 masks", note: "Every plane cleanly masked — the README calls this the best single demo image", overlay: "1_masking/expected_outputs/P0173__mask_airplanes.png" },
    ],
  },
  {
    id: "P0331_houses_trees",
    name: "Large houses with trees",
    category: "masking",
    folder: "1_masking",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    description: "Large houses with big trees beside them.",
    thumbnail: "1_masking/houses_with_trees__P0331_0004.png",
    files: [
      { path: "1_masking/houses_with_trees__P0331_0004.png", role: "input", label: "Input image", bytes: 483787, pixels: "512 x 512", previewable: true },
      { path: "1_masking/expected_outputs/P0331__mark_trees_near_houses.png", role: "expected_output", label: "Overlay: mark trees near houses", bytes: 529412, pixels: "512 x 512", previewable: true },
    ],
    runs: [
      { prompt: "mark trees near houses", result: "4 trees", note: "Each tree next to a house", overlay: "1_masking/expected_outputs/P0331__mark_trees_near_houses.png" },
    ],
  },

  // ------------------------------------------------------- 2_change_detection
  {
    id: "levir_scene_100",
    name: "LEVIR scene 100",
    category: "change_detection",
    folder: "2_change_detection/levir_scene_100",
    provenance: "LEVIR-CD test scene at 1024² (datasets/raw/ayushman_levircd_1024)",
    description: "Before/after pair with the dataset's own change label included.",
    thumbnail: "2_change_detection/expected_outputs/levir_100__detect_building_changes.png",
    thumbnailCaption: "Backend overlay for “detect building changes”",
    files: [
      { path: "2_change_detection/levir_scene_100/before.png", role: "before", label: "Before", bytes: 2078264, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_100/after.png", role: "after", label: "After", bytes: 1968522, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_100/ground_truth_change.png", role: "ground_truth", label: "Ground truth (dataset label)", bytes: 22221, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/expected_outputs/levir_100__detect_building_changes.png", role: "expected_output", label: "Overlay: detect building changes", bytes: 2661691, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/expected_outputs/levir_100__has_any_new_building_been_constructed.png", role: "expected_output", label: "Overlay: has any new building been constructed?", bytes: 2661691, pixels: "1024 x 1024", previewable: true },
    ],
    runs: [
      { prompt: "detect building changes", result: "118,997 px changed (11.35%), ChangeFormer native mode", overlay: "2_change_detection/expected_outputs/levir_100__detect_building_changes.png" },
      { prompt: "has any new building been constructed?", result: "“Yes — building change is detected … 11.35%”", note: "CDVQA set aside as uninformative (two-agent adjudication)", overlay: "2_change_detection/expected_outputs/levir_100__has_any_new_building_been_constructed.png" },
    ],
  },
  {
    id: "levir_scene_101",
    name: "LEVIR scene 101",
    category: "change_detection",
    folder: "2_change_detection/levir_scene_101",
    provenance: "LEVIR-CD test scene at 1024² (datasets/raw/ayushman_levircd_1024)",
    description: "Extra LEVIR pair, ground truth included.",
    thumbnail: "2_change_detection/levir_scene_101/before.png",
    thumbnailCaption: "Before frame",
    notMeasured: true,
    caveat: "The README records no measured run for this pair: “not re-run for this README”. No result is claimed here.",
    files: [
      { path: "2_change_detection/levir_scene_101/before.png", role: "before", label: "Before", bytes: 1605769, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_101/after.png", role: "after", label: "After", bytes: 1971541, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_101/ground_truth_change.png", role: "ground_truth", label: "Ground truth (dataset label)", bytes: 8281, pixels: "1024 x 1024", previewable: true },
    ],
    runs: [],
  },
  {
    id: "levir_scene_105",
    name: "LEVIR scene 105",
    category: "change_detection",
    folder: "2_change_detection/levir_scene_105",
    provenance: "LEVIR-CD test scene at 1024² (datasets/raw/ayushman_levircd_1024)",
    description: "Extra LEVIR pair, ground truth included.",
    thumbnail: "2_change_detection/levir_scene_105/before.png",
    thumbnailCaption: "Before frame",
    notMeasured: true,
    caveat: "The README records no measured run for this pair: “not re-run for this README”. No result is claimed here.",
    files: [
      { path: "2_change_detection/levir_scene_105/before.png", role: "before", label: "Before", bytes: 1377224, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_105/after.png", role: "after", label: "After", bytes: 1944061, pixels: "1024 x 1024", previewable: true },
      { path: "2_change_detection/levir_scene_105/ground_truth_change.png", role: "ground_truth", label: "Ground truth (dataset label)", bytes: 12601, pixels: "1024 x 1024", previewable: true },
    ],
    runs: [],
  },
  {
    id: "real_pair",
    name: "Real pair (256²)",
    category: "change_detection",
    folder: "2_change_detection/real_pair",
    provenance: "Copy of datasets/samples/real_pair",
    thumbnail: "2_change_detection/expected_outputs/real_pair__detect_changes.png",
    thumbnailCaption: "Backend overlay for “detect changes”",
    files: [
      { path: "2_change_detection/real_pair/before.png", role: "before", label: "Before", bytes: 131272, pixels: "256 x 256", previewable: true },
      { path: "2_change_detection/real_pair/after.png", role: "after", label: "After", bytes: 129859, pixels: "256 x 256", previewable: true },
      { path: "2_change_detection/real_pair/ground_truth_change.png", role: "ground_truth", label: "Ground truth (dataset label)", bytes: 1075, pixels: "256 x 256", previewable: true },
      { path: "2_change_detection/expected_outputs/real_pair__detect_changes.png", role: "expected_output", label: "Overlay: detect changes", bytes: 154361, pixels: "256 x 256", previewable: true },
    ],
    runs: [{ prompt: "detect changes", result: "16,685 px changed (25.46%)", overlay: "2_change_detection/expected_outputs/real_pair__detect_changes.png" }],
  },
  {
    id: "sentinel2_valencia",
    name: "Sentinel-2 Valencia (GeoTIFF + AOI)",
    category: "change_detection",
    folder: "2_change_detection/sentinel2_valencia",
    provenance: "Copy of datasets/samples/ (Sentinel-2 provenance in datasets/samples/demo/README.md)",
    description:
      "GeoTIFF before/after pair with an AOI polygon. Use it to show GeoTIFF + AOI handling, not change detection.",
    thumbnail: "2_change_detection/expected_outputs/sentinel2__detect_changes_0px.png",
    thumbnailCaption:
      "Backend overlay for “detect changes” (0 px changed). The .tif inputs cannot be rendered in a browser.",
    caveat:
      "0 px changed. The AOI is applied (trace: “Area of interest applied, 7,588 px, 0.7588 km²”), but ChangeFormer, trained on 0.5 m building change, finds nothing on 10 m farmland. Use it to show GeoTIFF + AOI handling, not change detection.",
    meta: [
      { label: "Platform / sensor", value: "Sentinel-2B, MultiSpectral Instrument (MSI)" },
      { label: "Product IDs", value: "S2B_30SYJ_20240414_0_L2A → S2B_30SYJ_20240723_0_L2A" },
      { label: "Acquisition", value: "2024-04-14T11:00:15Z → 2024-07-23T11:00:18Z" },
      { label: "Source asset", value: "Level-2A True Color Image (TCI), 3-band uint8 RGB" },
      { label: "CRS / resolution", value: "EPSG:32630 (UTM 30N), 10.0 m/px, 512 x 512" },
      { label: "Scene cloud cover", value: "0.003971% (before), 0.006702% (after)" },
      { label: "AOI", value: "Albufera Agricultural Parcel Basin, Valencia, Spain — MGRS 30SYJ, 75.88 ha" },
    ],
    metaSource:
      "From datasets/samples/demo/README.md (ESA STAC metadata) and the AOI properties inside aoi.geojson.",
    files: [
      { path: "2_change_detection/sentinel2_valencia/before.tif", role: "before", label: "Before (GeoTIFF)", bytes: 723128, previewable: false },
      { path: "2_change_detection/sentinel2_valencia/after.tif", role: "after", label: "After (GeoTIFF)", bytes: 832506, previewable: false },
      { path: "2_change_detection/sentinel2_valencia/aoi.geojson", role: "aoi", label: "Area of interest (GeoJSON)", bytes: 1314, previewable: false },
      { path: "2_change_detection/expected_outputs/sentinel2__detect_changes_0px.png", role: "expected_output", label: "Overlay: detect changes (0 px)", bytes: 517796, pixels: "512 x 512", previewable: true },
    ],
    runs: [
      {
        prompt: "detect changes (with or without the AOI)",
        result: "0 px changed",
        note: "The AOI is applied; ChangeFormer finds nothing on 10 m farmland",
        overlay: "2_change_detection/expected_outputs/sentinel2__detect_changes_0px.png",
      },
    ],
  },

  // ----------------------------------------------------------- 3_optical_sar
  {
    id: "optical_sar_pair",
    name: "Optical + SAR pair",
    category: "optical_sar",
    folder: "3_optical_sar",
    provenance: "Copy of datasets/samples/optical_sar_pair",
    description: "Upload both files together and prompt “analyze this optical and SAR pair”.",
    thumbnail: "3_optical_sar/optical_sentinel2.png",
    thumbnailCaption: "Optical image of the pair",
    caveat:
      "Routes to optical_sar_analysis (DOFA + fusion head) and honestly refuses — the fusion head is NOT_CONFIGURED (uncalibrated weights). Demo it only as “the system refuses rather than invents”.",
    files: [
      { path: "3_optical_sar/optical_sentinel2.png", role: "input", label: "Optical (Sentinel-2)", bytes: 129200, pixels: "256 x 256", previewable: true },
      { path: "3_optical_sar/sentinel1_sar_cband.png", role: "input", label: "SAR (Sentinel-1 C-band)", bytes: 160649, pixels: "256 x 256", previewable: true },
    ],
    runs: [
      {
        prompt: "analyze this optical and SAR pair",
        result: "Refused: fusion head NOT_CONFIGURED",
        note: "Routes to optical_sar_analysis (DOFA + fusion head); the weights are uncalibrated, so the system refuses rather than inventing an answer",
      },
    ],
  },

  // ------------------------------------------------------------------ 4_video
  {
    id: "real_aerial_footage",
    name: "Real aerial footage",
    category: "video",
    folder: "4_video",
    provenance: "Copy of datasets/samples/video",
    duration: "~23 s",
    thumbnail: "4_video/real_aerial_footage.mp4",
    files: [{ path: "4_video/real_aerial_footage.mp4", role: "input", label: "Video (mp4)", bytes: 2811553, previewable: true }],
    runs: [
      {
        prompt: "find all vehicles",
        result: "2 events: 14.88–18.72 s and 25.44–27.36 s",
        note: "A third candidate (4.80–8.16 s) was dropped because the verification agent confirmed 0/3 frames",
      },
    ],
  },
  {
    id: "derived_patrol",
    name: "Derived patrol clip",
    category: "video",
    folder: "4_video",
    provenance: "Copy of datasets/samples/video",
    duration: "~4 s",
    thumbnail: "4_video/derived_patrol.mp4",
    files: [{ path: "4_video/derived_patrol.mp4", role: "input", label: "Video (mp4)", bytes: 102462, previewable: true }],
    runs: [
      {
        prompt: "find all vehicles",
        result: "0 events",
        note: "Trees and dirt, no vehicles — kept to show the absence of false positives",
      },
    ],
  },

  // ------------------------------------------------------------- 5_known_weak
  {
    id: "weak_parking_lot_dark",
    name: "Dark parking lot",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/parking_lot_dark__P1178_0048.png",
    failure: "Dark image; masks a kerb, misses the cars.",
    files: [
      { path: "5_known_weak/parking_lot_dark__P1178_0048.png", role: "input", label: "Input image", bytes: 248820, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/P1178__mask_cars.png", role: "expected_output", label: "Overlay: mask cars", bytes: 228772, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask cars", result: "Known failure: masks a kerb, misses the cars", overlay: "5_known_weak/expected_outputs/P1178__mask_cars.png" }],
  },
  {
    id: "weak_houses_pools",
    name: "Houses with swimming pools",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/houses_pools__P0060_0005.png",
    failure: "Pools masked, but house roofs too.",
    files: [
      { path: "5_known_weak/houses_pools__P0060_0005.png", role: "input", label: "Input image", bytes: 493960, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/P0060__mask_swimming_pools.png", role: "expected_output", label: "Overlay: mask swimming pools", bytes: 485099, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask swimming pools", result: "Known failure: pools masked, but house roofs too", overlay: "5_known_weak/expected_outputs/P0060__mask_swimming_pools.png" }],
  },
  {
    id: "weak_lakeshore_boats",
    name: "Lakeshore boats",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/lakeshore_boats__P0019_0062.png",
    failure: "Masks small boats/cars on the beach, not ships.",
    files: [
      { path: "5_known_weak/lakeshore_boats__P0019_0062.png", role: "input", label: "Input image", bytes: 453498, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/P0019__mask_ships.png", role: "expected_output", label: "Overlay: mask ships", bytes: 484047, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask ships", result: "Known failure: masks small boats/cars on the beach, not ships", overlay: "5_known_weak/expected_outputs/P0019__mask_ships.png" }],
  },
  {
    id: "weak_storage_tanks",
    name: "Storage tanks (greyscale)",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/storage_tanks_grayscale__P1234_0022.png",
    failure: "2 of 8 tanks masked.",
    files: [
      { path: "5_known_weak/storage_tanks_grayscale__P1234_0022.png", role: "input", label: "Input image", bytes: 321088, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/P1234__mask_storage_tanks.png", role: "expected_output", label: "Overlay: mask storage tanks", bytes: 199493, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask storage tanks", result: "Known failure: 2 of 8 tanks", overlay: "5_known_weak/expected_outputs/P1234__mask_storage_tanks.png" }],
  },
  {
    id: "weak_tennis_courts",
    name: "Tennis courts",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/tennis_courts__P0175_0001.png",
    failure: "Masks the grass field instead.",
    files: [
      { path: "5_known_weak/tennis_courts__P0175_0001.png", role: "input", label: "Input image", bytes: 469969, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/P0175__mask_tennis_courts.png", role: "expected_output", label: "Overlay: mask tennis courts", bytes: 443499, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask tennis courts", result: "Known failure: masks the grass field instead", overlay: "5_known_weak/expected_outputs/P0175__mask_tennis_courts.png" }],
  },
  {
    id: "weak_trees_over_house",
    name: "Trees over a house",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/trees_over_house__06405_0000.png",
    failure: "Tree mask swallows the house roof.",
    files: [
      { path: "5_known_weak/trees_over_house__06405_0000.png", role: "input", label: "Input image", bytes: 481577, pixels: "512 x 512", previewable: true },
      { path: "5_known_weak/expected_outputs/06405__mask_trees.png", role: "expected_output", label: "Overlay: mask trees", bytes: 471272, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "mask trees", result: "Known failure: tree mask swallows the house roof", overlay: "5_known_weak/expected_outputs/06405__mask_trees.png" }],
  },
  {
    id: "weak_vehicle_wrong_box",
    name: "Vehicle, wrong box verified",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/vehicle_wrong_box__05865_0000.png",
    failure: "Verified the wrong box (Q-008 §3, Q-014).",
    caveat: "No expected-output overlay is committed for this image.",
    files: [
      { path: "5_known_weak/vehicle_wrong_box__05865_0000.png", role: "input", label: "Input image", bytes: 467732, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "find the vehicle", result: "Known failure: verified the wrong box (Q-008 §3, Q-014)" }],
  },
  {
    id: "weak_largest_building_disputed",
    name: "Largest building, disputed",
    category: "known_weak",
    folder: "5_known_weak",
    provenance: "VRSBench validation set (datasets/raw/vrsbench/images/Images_val)",
    thumbnail: "5_known_weak/largest_building_disputed__05945_0000.png",
    failure: "Verification agent disputes it (reads “ground track field”).",
    caveat: "No expected-output overlay is committed for this image.",
    files: [
      { path: "5_known_weak/largest_building_disputed__05945_0000.png", role: "input", label: "Input image", bytes: 510687, pixels: "512 x 512", previewable: true },
    ],
    runs: [{ prompt: "segment the largest building", result: "Known failure: the verification agent disputes it (reads “ground track field”)" }],
  },
];

/** URL for a demo_resources file, served by the repo-local streaming route. */
export function demoResourceUrl(relativePath: string): string {
  const encoded = relativePath.split("/").map(encodeURIComponent).join("/");
  return `/api/demo-resources/${encoded}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isVideoPath(relativePath: string): boolean {
  return relativePath.toLowerCase().endsWith(".mp4");
}

/** Total number of files referenced by this catalog (README excluded). */
export const CATALOGUED_FILE_COUNT = DEMO_RESOURCES.reduce(
  (total, entry) => total + entry.files.length,
  0,
);

export const CATEGORY_COUNTS: Record<DemoCategoryId, number> = DEMO_CATEGORIES.reduce(
  (acc, category) => {
    acc[category.id] = DEMO_RESOURCES.filter((entry) => entry.category === category.id).length;
    return acc;
  },
  {} as Record<DemoCategoryId, number>,
);
