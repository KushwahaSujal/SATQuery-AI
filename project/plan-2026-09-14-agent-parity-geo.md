# Tonight's build — two-agent verification & backtracking, GeoTIFF, GeoJSON AOI

**Date:** 2026-09-14 (demo 2026-09-15) · **Branch:** `refactor/s0-remove-dead-layers` from `dee8e53`
**Scope (user, 2026-09-14):** two agents compare confidence → pick best or backtrack and re-evaluate;
GeoTIFF input; GeoJSON input. Everything else in the audit waits for a decision after this.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Ground truth this plan is built on (measured tonight, not assumed)

| Fact | Evidence |
|---|---|
| Detection is a single chain: Grounding DINO → V4 reasoner → SAM 2. No second opinion, no backtracking. | `workflows/grounding.py:62-330` |
| `EvidenceAdjudicator` is called by nothing, and returns constant confidences (0.88, 0.35, `or 0.5`). | `grep -rn EvidenceAdjudicator backend/app` → only `evidence/__init__.py` |
| Absent objects are "found": "find the airplane" on road footage → 3 airplane flags, event score up to 0.74. | `scratchpad/audit_video2.py` run |
| RemoteCLIP weights are real: 302 tensors, 0 missing, 0 unexpected. | adapter load log |
| **Contrastive RemoteCLIP separates true vs wrong class on real RS crops: AUC 0.955.** Top-3 rank in a 33-label RS vocabulary accepts 78.2% of true labels and 5.9% of wrong labels (973 VRSBench GT crops, 40/class). Raw similarity alone: AUC 0.928. | `results/evaluations/remoteclip_verifier_probe_20260914.json` |
| GeoTIFF: `rasterio` absent → `tifffile` fallback hard-codes `crs=None`, `transform=None`. A real UTM-14N GeoTIFF reads as `is_georeferenced=False`. | `geo/raster.py:84-124`; probe on `scratchpad/geo/levir_100_A_utm14n.tif` |
| GeoJSON is output-only; no request field or upload type accepts it. | `schemas/requests.py:5-10`, `config.py` allowed extensions |
| ChangeFormer at native 1024 OOMs when other models are resident on the 8 GB GPU. | audit run, `run_change_detection` error |

---

## Phase 1 · Verification agent + backtracking on still-image grounding `[ ]`

**Deliverable:** the same query goes to two independent agents — **Grounding DINO** (detector
confidence) and **RemoteCLIP** (contrastive verification confidence). The system picks the best
candidate both agree on, backtracks to the next candidate on disagreement, re-evaluates with a
relaxed detector threshold if all are rejected, and reports NOT_FOUND rather than a wrong mask.
Every attempt is visible in the trace with both confidences.

1. `backend/app/evidence/verifier.py` — `DetectionVerifier.verify(image, box, target_label)` →
   `VerificationVerdict(accepted, target_probability, target_rank, top_alternatives, crop_box)`.
   Contrastive softmax over RS vocabulary ∪ target; accept iff rank ≤ `top_k`.
2. `configs/app.yaml` `agent_verification:` — `enabled`, `top_k: 3`, `crop_pad: 0.2`,
   `min_crop_side: 48`, `max_candidates: 5`, `relaxed_box_threshold: 0.15`, `vocabulary: [...]`.
   Loaded via `config.py` (rules §3: no magic numbers).
3. `workflows/grounding.py` — after the reasoner ranks candidates, walk its order:
   - verify → **ACCEPT** first verified candidate → SAM 2 on that box;
   - rejected → record **BACKTRACK**, try the next;
   - all rejected → **RE-EVALUATE**: rerun Grounding DINO once at `relaxed_box_threshold`, re-rank,
     verify again;
   - still none → **NOT_FOUND** answer, no mask, deliberation attached.
   Deliberation is `evidence["agent_deliberation"]` + one trace step per attempt.
4. Answer text drops "with high precision" and states both agents' confidences.
5. **Verify:** unit tests with fake adapters for ACCEPT / BACKTRACK / RE-EVALUATE / NOT_FOUND; live
   run on a VRSBench image with present vs absent class; VRSBench grounding eval must not regress
   below the recorded mIoU 0.3532 / R@0.5 0.398 on 299 records (report the new number either way).

## Phase 2 · Same verification on video flags `[ ]`

1. `workflows/video_analysis.py` / `video/flagger.py` — verify each flag's peak-frame box crop
   against the flag label before emitting; rejected flags are dropped and listed in
   `warnings` with both scores.
2. **Verify:** `real_aerial_footage.mp4` — "find all vehicles" keeps its events; "find the airplane"
   drops to 0 flags. Existing video tests stay green.

## Phase 3 · Change-detection parity: ChangeFormer vs CDVQA `[ ]`

Prerequisite: change detection must run in the full app at all.

1. `adapter.py::_forward_logits` — on CUDA OOM: `empty_cache`, retry windowed at 512 then 256;
   record `inference_mode` + `oom_fallback` in metadata.
2. `evidence/adjudicator.py` — remove constant confidences (report `None` / derived-from-inputs
   only), read ChangeFormer's real metadata keys (`change_ratio_pct`, `change_pixel_count`,
   `quality_status`).
3. `agent/tools/inference.py::run_change_vqa` — call the adjudicator with both results; attach
   verdict (`adjudication_status`, `applied_rule`, both confidences, conflict details) to evidence
   and trace.
4. **Verify:** unit tests per rule (concordant change, concordant no-change, CDVQA-says-yes/mask-empty,
   mask-changed/CDVQA-says-no); live `temporal_change_vqa` on LEVIR 1024 scene 101 in-process with
   all models resident.

## Phase 4 · GeoTIFF georeferencing without rasterio `[ ]`

1. `geo/raster.py` tifffile path — parse GeoKeyDirectory (34735): `ProjectedCSTypeGeoKey` (3072) /
   `GeographicTypeGeoKey` (2048) → `EPSG:n`; transform from `ModelPixelScale` (33550) +
   `ModelTiepoint` (33922), or `ModelTransformation` (34264); bounds; nodata (42113).
2. Confirm downstream: `calculate_area_statistics` returns km²; `mask_to_geojson` path B emits map
   coordinates reprojected to EPSG:4326.
3. **Verify:** tests on generated GeoTIFFs (UTM 14N, EPSG:4326, no georef) asserting CRS, transform,
   bounds, area in m² = pixels × 0.25, GeoJSON coordinates inside expected lon/lat box; live
   `temporal_change_detection` on the georeferenced LEVIR pair.

## Phase 5 · GeoJSON area-of-interest input `[ ]`

1. `geo/aoi.py` — parse Feature / FeatureCollection / Polygon / MultiPolygon; CRS = EPSG:4326 per
   RFC 7946 unless a legacy `crs` member says otherwise; reproject with pyproj to raster CRS;
   world → pixel via inverse transform; rasterise with `cv2.fillPoly`.
   Structured errors: `AOI_REQUIRES_GEOREFERENCED_RASTER`, `AOI_OUTSIDE_RASTER`, `AOI_INVALID`.
2. Input paths: `AnalyzeRequest.aoi_geojson` (inline object) and `.geojson` upload.
3. Applied in `calculate_statistics` and grounding/change evidence: changed/segmented pixels and
   area **inside the AOI**, AOI area, AOI coverage; AOI outline drawn on overlays.
4. **Verify:** tests for inside / partially outside / fully outside / non-georeferenced raster /
   4326→UTM reprojection correctness; live run with an AOI covering half of LEVIR scene 100.

## Phase 6 · Record, verify, commit `[ ]`

- `project/qna.md` Q-008 (two-agent verification & backtracking, change adjudication) and Q-009
  (GeoTIFF georeferencing + GeoJSON AOI), measured numbers verbatim.
- Full `pytest -q`; in-process end-to-end run of every demo query with all models resident.
- One commit per phase.

## Order and cut line

1 → 2 → 4 → 5 → 3. If time runs out, **3 is the cut** (the change-detection OOM fix inside it is
small and goes first if the change demo is kept).
