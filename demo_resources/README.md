# SatQuery AI — Demo Resources

Every image, image pair and video used to test the `prototype` branch, in one place, with the prompts
that were run and what came back. Upload from here during a demo instead of hunting through `datasets/`.

All results below were measured on 2026-09-15 on `prototype` with the real models (RTX 3070, 8 GB),
through the HTTP API and, for one case, the web UI. `expected_outputs/` holds the overlay the backend
produced for each prompt, so you can compare what appears on stage with what it should look like.

**Rules for the stage**

- Use **folders 1–4**. Folder **5 is known weak** — kept so nobody picks those images by accident.
- All masking prompts route to `workflow_grounding` with `grounding_dino` + `sam2`.
- Only the **top-ranked** instance goes through the verification agent; extra instances are detector boxes
  that passed the colour/relation checks. The trace says this (`segment_all_instances`).
- Don't run `pytest` while the server is up: both need the 8 GB GPU.

---

## 1. Masking (single image) — `1_masking/`

### `street_houses_trees_cars__P0725_0005.png`
VRSBench val. A street with an orange-tile-roofed house, grey houses, trees along the road, parked cars, a jetty.

| Prompt | Result | Notes |
|---|---|---|
| `mask trees` | 8 trees | Street trees and yard trees |
| `mark trees near houses` | 9 trees | Also shown in the web UI: 9 masks, confidence 87.7% |
| `mark cars near houses` | 11 masks | Most on real cars; **2 false positives on rooftops** |
| `find cars near red house` | 3 cars | Only cars beside the orange-tile house |
| `mask houses near cars` | 3 houses | Correctly drops the jetty |
| `mask houses` | 4 masks | Misses the grey houses; **masks the jetty as a house** |
| `mark houses near trees` | 4 houses | Same set as `mask houses` |
| `mask cars near white houses` | 1 car, with a message | No white houses here; answer says no instance satisfied the conditions |

### `suburb_white_houses_red_cars__P0897_0048.png`
VRSBench val. A suburb with ~25 houses (5 with white roofs), small cars, two red cars beside a big white house.

| Prompt | Result | Notes |
|---|---|---|
| `mask white houses` | 5 houses | Exactly the white roofs (colour checked on mask pixels) |
| `mask red cars` | 2 cars | The two red cars |
| `mask cars near white houses` | 5 cars | Each beside a white building; the red cars were not proposed by the detector for "cars" |
| `mark cars near houses` | 15 cars | Small masks along the streets |

**Colour prompt tip:** `white`, `red` and `dark` work on roofs and red cars. White *cars* score low
(small masks with shadow) — avoid `mask white cars`.

### `airport_airplanes__P0173_0003.png`
VRSBench val. Airport apron with six light aircraft.

| Prompt | Result | Notes |
|---|---|---|
| `mask airplanes` | 9 masks | Every plane cleanly masked — **best single demo image** |

### `houses_with_trees__P0331_0004.png`
VRSBench val. Large houses with big trees beside them.

| Prompt | Result | Notes |
|---|---|---|
| `mark trees near houses` | 4 trees | Each tree next to a house |

---

## 2. Change detection (image pairs) — `2_change_detection/`

Upload **both** files (`before` then `after`) in one upload.

| Pair | Prompt | Result |
|---|---|---|
| `levir_scene_100/` (1024², LEVIR-CD test) | `detect building changes` | 118,997 px changed (11.35%), ChangeFormer native mode |
| `levir_scene_100/` | `has any new building been constructed?` | "Yes — building change is detected … 11.35%"; CDVQA set aside as uninformative (two-agent adjudication) |
| `real_pair/` (256²) | `detect changes` | 16,685 px changed (25.46%) |
| `levir_scene_101/`, `levir_scene_105/` | `detect building changes` | Extra LEVIR pairs; ground truth included (`ground_truth_change.png`) — not re-run for this README |
| `sentinel2_valencia/` (`before.tif`, `after.tif`, `aoi.geojson`) | `detect changes` (with or without the AOI) | **0 px changed.** The AOI is applied (trace: "Area of interest applied, 7,588 px, 0.7588 km²"), but ChangeFormer, trained on 0.5 m building change, finds nothing on 10 m farmland. Use it to show GeoTIFF + AOI handling, **not** change detection. |

`ground_truth_change.png` files are the dataset labels, for showing the model against ground truth.

---

## 3. Optical + SAR pair — `3_optical_sar/`

Upload `optical_sentinel2.png` and `sentinel1_sar_cband.png` together, prompt `analyze this optical and SAR pair`.
Result: routes to `optical_sar_analysis` (DOFA + fusion head) and **honestly refuses** — the fusion head is
`NOT_CONFIGURED` (uncalibrated weights). Demo it only as "the system refuses rather than invents".

---

## 4. Video — `4_video/`

Use the video upload, prompt `find all vehicles`.

| Video | Result |
|---|---|
| `real_aerial_footage.mp4` | 2 events: 14.88–18.72 s and 25.44–27.36 s; a third (4.80–8.16 s) dropped because the verification agent confirmed 0/3 frames. ~23 s |
| `derived_patrol.mp4` | 0 events (trees and dirt, no vehicles) — shows no false positives. ~4 s |

---

## 5. Known weak — `5_known_weak/` (don't demo)

| Image | Prompt | What goes wrong |
|---|---|---|
| `parking_lot_dark__P1178_0048.png` | `mask cars` | Dark image; masks a kerb, misses the cars |
| `houses_pools__P0060_0005.png` | `mask swimming pools` | Pools masked, but house roofs too |
| `lakeshore_boats__P0019_0062.png` | `mask ships` | Masks small boats/cars on the beach, not ships |
| `storage_tanks_grayscale__P1234_0022.png` | `mask storage tanks` | 2 of 8 tanks |
| `tennis_courts__P0175_0001.png` | `mask tennis courts` | Masks the grass field instead |
| `trees_over_house__06405_0000.png` | `mask trees` | Tree mask swallows the house roof |
| `vehicle_wrong_box__05865_0000.png` | `find the vehicle` | Verified the wrong box (Q-008 §3, Q-014) |
| `largest_building_disputed__05945_0000.png` | `segment the largest building` | Verification agent disputes it (reads "ground track field") |

---

## Sources

- `P*.png`, `0*.png`: VRSBench validation set (`datasets/raw/vrsbench/images/Images_val`).
- `levir_scene_*`: LEVIR-CD test scenes at 1024² (`datasets/raw/ayushman_levircd_1024`).
- `real_pair`, `3_optical_sar`, `4_video`, `sentinel2_valencia`: copies of `datasets/samples/` (Sentinel-2 provenance
  in `datasets/samples/demo/README.md`).
