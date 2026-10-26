# Restoration Core Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `backend/app/restoration/`. It is a pure, in-memory library that measures input
quality, plans corrections, runs them and emits an honest receipt. It is not wired into the agent
DAG yet.

**Architecture:** There are six small modules. `schemas.py` holds the pydantic contracts.
`detectors.py` turns an array into a `QualityAssessment`. `planner.py` is a pure function from an
assessment to a `RestorationPlan`. `registry.py` plus the stage modules hold the correction stages.
`executor.py` runs a plan and builds the `RestorationReceipt`. Everything works on
`(bands, H, W)` numpy arrays, so there is no file I/O and no DAG in this plan. Plan 2 (below) wires
it in.

**Tech Stack:** Python 3.11, numpy 2.4, scipy 1.17 (`ndimage`), pydantic 2.13, pytest. No new
dependency.

**Spec:** `project/spec-2026-09-21-restoration-framework.md` (read §1–§5, §7, §8, §9.1 before starting).

## Global Constraints

- No new dependency. Only numpy, scipy and opencv-python-headless may be used (spec §1.2).
- Array layout is `(bands, height, width)`. dtype and shape are preserved by every stage (spec §2.1).
- Invalid (nodata / non-finite) pixels stay **bit-identical** through every stage (spec §2.1 rule 4).
- A detector that cannot measure returns `value=None` plus a reason. It never returns `0.0` (spec §3).
- Every threshold lives in `configs/app.yaml` under `restoration:`, never in code (spec §3.1).
- There are no geometric changes: `is_geometric=True` is unrepresentable (spec §1.2).
- `max_confidence_multiplier` stays at or below 1.0, and every v1 multiplier is 1.0 (spec §7.3).
- Learned super-resolution never runs. `super_resolve` only returns `NOT_CONFIGURED` (spec §1.2).
- Do not touch `agent/`, `orchestration/`, `workflows/` or any adapter in this plan.
- Run tests with `.venv/bin/python -m pytest`. Baseline: `-m "not models"` gives **573 passed,
  3 failed** (the three GDAL failures in `test_geotiff_georeferencing.py`).
- The working tree has unrelated uncommitted changes. Every commit must `git add` **only** the
  files that task names.

## Deviations from the spec (decided while planning; recorded in Q-065)

| # | Spec says | This plan does | Why |
|---|---|---|---|
| D1 | `max_similar_neighbours = 2` | default **1** | A pixel on a 1-px bright line has exactly 2 similar neighbours (along the line). With 2, the line counts as "isolated" and gets flagged, so the §9.1 road-tile guard would fail. With 1, line pixels are safe and a lone impulse (0–1 same-polarity neighbours) is still caught. |
| D2 | `exceeds_threshold = value >= threshold` for every metric | a `direction: "above" \| "below"` field on `QualityMetric` | `dynamic_range_p2_p98` is bad when **low**. The spec's own §2.11 example (0.21 vs 0.30 → `exceeds: true`) cannot come out of the spec's validator. |
| D3 | Row 5: `black_level_dn > 0` fires the offset term | black level is a **parameter** of `photometric_correct` and triggers nothing | p0.5 > 0 on nearly every real image, so row 5 would make "no action" almost impossible. The §3.2 table already says "no gate; a parameter". |
| D4 | `mask_invalid` is a stage at order 10 | no stage. `build_valid_mask()` is called once by the detectors and the executor | §4.3 and §9.1 both require a clean plan to have `stages == []`, which a mandatory stage contradicts. |
| D5 | `gsd_m` has basis PRINCIPLED with no threshold, yet row 10 gates on it | `gsd_m` threshold is `sr_recommend_gsd_m`, basis **PROVISIONAL** | §3.4 forbids gating on NOT_CALIBRATED, and a metric with no threshold cannot gate at all. The value is read from metadata; the 2.0 m threshold is an assumption, and PROVISIONAL says exactly that. |
| D6 | the switching median lives in `stages.py` | it lives in `restoration/impulse.py` | Two owners (Ushnik's registry, Ayushman's median) should not edit one file. |
| D7 | the naive chain quantises at every step, and fused must match within 1 DN | the naive reference computes in float64 and quantises **once** | Per-step quantisation error is amplified by the stretch factor (up to ~3× here), so the 1 DN bound would not hold for the naive chain. The test proves fused == composed transfer function, which is the real claim. |
| D8 | tiled apply uses `RasterTiler` | row strips inside `correction.py` | The LUT is pointwise, so overlap and stitching are unnecessary. Strips give the same memory bound in fewer lines. |
| D9 | diagonal colour matrix `M` applied as a matmul | the diagonal gains are folded into the per-band LUT and recorded as `gain` in the receipt | For a diagonal `M`, `M @ x` is per-band scaling, i.e. pointwise. A general 3×3 is not needed in v1. |

## Decisions to confirm before Plan 2 wires this into jobs

These are not blockers for this plan, because nothing here touches a user's job. They **are**
blockers for wiring.

1. **uint16 dynamic range.** With `dn_max = 65535` (spec §2.1 rule 3), a Sentinel-2 L2A scene
   (values of roughly 0–10000) measures `dynamic_range ≈ 0.1`. That is under the 0.30 gate, so
   every S2 scene would be stretched. Spec §10.8 is still open.
2. **Grey-world on vegetation.** A green-dominant scene is a genuine colour, not a cast. Expect
   `grey_world_gain > 1.15` on healthy vegetation, which the correction would then "fix". Spec §10.5.
3. **`gsd_m > 2 m`** marks every Sentinel scene as `DEGRADED` with a `NOT_CONFIGURED`
   `super_resolve` stage. That is truthful, but it is noisy.
4. **Signed and float rasters** (from the final review, measured). SAR dB floats and int16 data
   read `saturation_low` ≈ 0.73, which triggers a false "clipped values are lost" warning. The
   int16 stretch fires and `transfer` clips to `[0, dn_max]`, remapping signed data (DEM, SAR)
   into non-negative DN. Proposal: for non-unsigned dtypes, `saturation_low` becomes
   NOT_APPLICABLE and `photometric_correct` refuses.
5. **Stage memory bound** (measured with tracemalloc on 4-band 768×768). `execute_plan` peaks at
   93 B per spatial pixel, `delta_stats` at 84, `photometric_correct` at 84, and `assess` at 50.
   Extrapolated, not measured: Sentinel-2 10980² 4-band is about 11 GB, far above the 2.5 GB guard.
   The fix is per-strip `delta_stats`, `impulse_candidates` and median with a 1-row halo, plus
   hashing without `tobytes`. This must land before Plan 2 routes real scenes through it.
6. **Per-image stage attribution.** `StageReceipt` has no `image_index`, and `build_receipt`'s
   "addressed" set is global, so a pair's image-0 correction would mark image 1 as corrected.
   Add `image_index`, stamped from `plan.image_index` in `execute_plan`, and compute residuals per
   image. This must land before temporal pairs.
7. **`_tiles` overlap on elongated rasters** (measured). At 300×3000 it reports
   `sample_fraction` 0.655 against 0.256 unique coverage. Space the tiles per axis, or compute the
   fraction from a coverage mask.
8. **Offset term on a constant band** (reproduced in the final fix re-review). A band constant at
   a nonzero value has black level = the value, so the offset term blackens the whole band. The
   receipt is honest (APPLIED, `terms_applied == ["offset"]`, fraction 1.0), but the model is handed
   an all-black band and no warning says so. The fix is to skip the offset per band when that
   band's black-level percentile equals its maximum, mirroring the stretch guard, and to warn.

## File structure

| File | Responsibility |
|---|---|
| `backend/app/config.py` (modify) | `RestorationSettings` + loader + `config_hash()` |
| `configs/app.yaml` (modify) | the `restoration:` block, every value commented as ASSUMPTION |
| `backend/app/restoration/__init__.py` | package docstring; imports `stages` so all stages register |
| `backend/app/restoration/schemas.py` | enums + `QualityMetric`, `QualityAssessment`, `PlannedStage`, `RestorationPlan`, `StageReceipt`, `ConfidenceAdvice`, `RestoredInput`, `RestorationReceipt` |
| `backend/app/restoration/registry.py` | `register_stage`, `STAGE_REGISTRY`, `STAGE_ORDER`, `StageSpec`, `not_configured()`, `delta_stats()` |
| `backend/app/restoration/stages.py` | `gaussian_denoise` + `super_resolve` NOT_CONFIGURED stages; imports `correction` and `impulse` |
| `backend/app/restoration/detectors.py` | `build_valid_mask`, `compute_dn_max`, `impulse_candidates`, every metric, `assess()` |
| `backend/app/restoration/planner.py` | `DECISION_TABLE`, `plan()` |
| `backend/app/restoration/correction.py` | `fit_photometric`, `build_lut`, `apply_fused`, `apply_naive`, stage `photometric_correct` |
| `backend/app/restoration/impulse.py` | stage `impulse_denoise` (switching median) — **owner: Ayushman** |
| `backend/app/restoration/executor.py` | `execute_plan()`, `build_receipt()`, `STAGE_ADDRESSES` |
| `tests/unit/restoration_fixtures.py` | synthetic image builders shared by the tests |
| `tests/unit/test_restoration_*.py` | one test file per module |

## Follow-on plans (not in this document)

- **Plan 2 — DAG wiring.** `agent/tools/restoration.py` (`assess_quality`, `restore_input`), the
  five registration edits (spec §6.1), the GeoTIFF writer with its georeferencing hard gate
  (§6.4), the cache key (§6.5), the user-visible warning + `REVIEW_REQUIRED` (§8.3), joint fitting
  for temporal pairs (§4.4), and `out_of_measured_range`. Settle the three decisions above first.
- **Plan 3 — Video.** Per-sampled-frame hook in `workflows/video_analysis.py`, plan held fixed after
  `video_assess_frames` (§4.4).
- **Plan 4 — Confidence critique agent** that consumes `confidence_advice` (§7).
- **Plan 5 — Calibration runs** (§9.2, §9.3): the impulse-gate sweep, stretch vs no-stretch on a
  trained segmenter. Heavy jobs go in `satquery.slice`, one at a time.
- **Plan 6 — Clarity models** (learned upscaling + real-noise denoising). These fill the
  `super_resolve` (90) and `gaussian_denoise` (30) slots, which refuse until then. The shortlist
  below comes from Hub metadata checked on 2026-09-30. **No weights were downloaded and nothing was
  measured.**

  | Slot | Candidate | Why | Licence / size | Caveat |
  |---|---|---|---|---|
  | SR, Sentinel-2 | `tacofoundation/SEN2SR` → `SEN2SRLite/NonReference_RGBN_x4` (B02,B03,B04,B08, 10 m → 2.5 m) | Trained on Sentinel-2. It has a **low-frequency hard-constraint layer** that keeps the input's low-frequency content, so it sharpens without changing radiometry (Aybar et al., RSE 2026). This is the "preserve originality" property, by construction. | CC0 weights, MIT code; SPAN CNN, 472 k params | Imports `sen2sr` (`CNNSR`, `HardConstraint`). Vendor those two classes (ChangeFormer precedent) rather than add `sen2sr`/`mlstac`. Needs L2A reflectance /10000 and the NIR band, so it does not apply to RGB PNGs. |
  | SR, RGB aerial / uploads | `caidas/swin2SR-classical-sr-x2-64`, `…-realworld-sr-x4-64-bsrgan-psnr`, `…-compressed-sr-x4-48` | Already loadable through the installed `transformers` (`Swin2SRForImageSuperResolution`): **no new dependency**. These are PSNR-oriented, not GAN. | Apache-2.0; ~49 MB (lightweight x2: 4 MB) | Trained on natural photos, not overhead imagery. It gives no consistency guarantee, so wrap it in our own low-frequency back-projection (downsample(SR) must equal input), the same idea as SEN2SR's constraint. |
  | Denoise, real noise | SCUNet `scunet_color_real_psnr` (`cszn/SCUNet`, mirror `deepinv/scunet`) | Blind real-noise denoiser, PSNR-oriented. | Apache-2.0; 72 MB | Trained on camera noise, not satellite sensor noise. Measure before trusting it. |
  | **Rejected** | Real-ESRGAN, SUPIR, DiffBIR, `isp-uv-es/opensr-model` (2.1 GB diffusion) | GAN/diffusion upscalers invent texture, and invented roofs or cars become fabricated detections (`rules.md` §1.2). | — | — |

  **Routing rule (decided 2026-09-30).** Never stack the models. Upscaling is decided per
  *consumer*, not per image: upscale only when the input GSD is coarser than the routed model's
  `trained_gsd_m` (`configs/models.yaml`). EuroSAT and flood are trained at 10 m, so a 10 m scene
  going to them is never upscaled. This replaces spec row 10's fixed `gsd_m > 2.0` for
  *executing* SR. Row 10 stays as the advisory in this plan, and the switch lives in Plan 2's
  `restore_input`, which knows the routed model. Order of adoption:
  1. SEN2SR, only for Sentinel-2 L2A going to a 0.5 m model.
  2. Swin2SR ×2 as an **experiment** on VRSBench small-car recall with Grounding DINO. It is
     enabled only if recall rises.
  3. SCUNet is deferred until the noise detector flags real uploads.
  4. LEVIR-CD pairs and drone video get no learned stage: pairs must be treated jointly, and
     video has no GPU headroom.
  5. SAR speckle needs a classical Lee filter, not any of these models. That is a separate stage
     that fits Ayushman's rule-based fusion.

  Three requirements come before any of these can run:
  1. **Spec §1.2 must change.** SR is a geometric change. Boxes, masks and GeoJSON must map back by
     the scale factor, and the GeoTIFF transform must be rescaled. `is_geometric` then becomes
     allowed for exactly this stage.
  2. **Gate on downstream scores, not PSNR.** Li et al. 2026 (arXiv 2605.00310) found that SR
     metric gains "often do not correlate with gains in task performance, and the correlations can
     be negative". A model is enabled only if it improves a routed segmenter's or detector's
     held-out score, and the result is recorded either way.
  3. `verify_checkpoints.py` entries, 8 GB GPU co-residency with the loaded models, and one heavy
     job at a time.

---

### Task 1: Settings block and config hash

**Files:**
- Modify: `backend/app/config.py` (imports at lines 1–5; new class after `TrainedSegmenterRoutingSettings` ~line 164; `Config.__init__` ~line 216; new loader after `_load_trained_segmenter_routing_config`)
- Modify: `configs/app.yaml` (append block)
- Test: `tests/unit/test_restoration_config.py`

**Interfaces:**
- Produces: `backend.app.config.RestorationSettings` (fields below) with `.config_hash() -> str`
  (16 hex chars), and `settings.restoration`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_config.py
from backend.app.config import RestorationSettings, settings


def test_settings_load_from_app_yaml():
    cfg = settings.restoration
    assert isinstance(cfg, RestorationSettings)
    assert cfg.impulse_gate == 0.001
    assert cfg.impulse_max_similar_neighbours == 1


def test_config_hash_is_stable_and_sensitive():
    a, b = RestorationSettings(), RestorationSettings()
    assert a.config_hash() == b.config_hash()
    assert len(a.config_hash()) == 16
    assert RestorationSettings(impulse_gate=0.002).config_hash() != a.config_hash()
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'RestorationSettings'`

- [ ] **Step 3: Implement**

In `backend/app/config.py`, change the imports to:

```python
import hashlib
import json
import os
```

(keep the rest). Add after `TrainedSegmenterRoutingSettings`:

```python
class RestorationSettings(BaseModel):
    """Input quality assessment and restoration (project/spec-2026-09-21-restoration-framework.md).
    Every number here is an ASSUMPTION until the spec §9.3 experiments run. Which thresholds may gate
    a stage is decided in restoration/detectors.py (METRIC_BASIS), not here."""
    enabled: bool = True
    impulse_gate: float = 0.001
    impulse_dev_dn_u8: float = 40.0
    impulse_max_similar_neighbours: int = 1
    impulse_extreme_tol_dn_u8: float = 2.0
    saturation_gate: float = 0.02
    dynamic_range_gate: float = 0.30
    grey_world_ratio_gate: float = 1.15
    gaussian_sigma_gate_fraction: float = 0.04
    sr_recommend_gsd_m: float = 2.0
    nodata_warn_fraction: float = 0.5
    nodata_unassessable_fraction: float = 0.95
    full_scan_megapixels: float = 16.0
    black_level_percentile: float = 0.5
    stretch_low_percentile: float = 2.0
    stretch_high_percentile: float = 98.0
    gamma: float = 1.0
    video_assess_frames: int = 5
    announce_fraction: float = 0.001

    def config_hash(self) -> str:
        """sha256 of the whole block, 16 hex chars. Goes into every assessment and, in Plan 2, the cache key."""
        blob = json.dumps(self.model_dump(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]
```

In `Config.__init__`, after `self.trained_segmenter_routing = ...`:

```python
        self.restoration = self._load_restoration_config()
```

After `_load_trained_segmenter_routing_config`:

```python
    def _load_restoration_config(self) -> RestorationSettings:
        raw = self._load_yaml("app.yaml").get("restoration", {})
        return RestorationSettings(**raw) if raw else RestorationSettings()
```

Append to `configs/app.yaml`:

```yaml

# Input quality assessment and restoration (project/spec-2026-09-21-restoration-framework.md).
# Every value is an ASSUMPTION, not measured; spec §9.3 lists the experiments that would calibrate them.
restoration:
  enabled: true
  impulse_gate: 0.001                 # fraction of valid pixels; PROVISIONAL gate for impulse_denoise
  impulse_dev_dn_u8: 40.0             # |x - median3x3| in uint8 DN, scaled by dn_max/255 for other dtypes
  impulse_max_similar_neighbours: 1   # 2 would flag 1-px roads (a line pixel has 2 similar neighbours)
  impulse_extreme_tol_dn_u8: 2.0
  saturation_gate: 0.02
  dynamic_range_gate: 0.30            # (p98 - p2) / dn_max, below this fires the stretch
  grey_world_ratio_gate: 1.15
  gaussian_sigma_gate_fraction: 0.04  # of dn_max; gaussian_denoise is NOT_CONFIGURED anyway
  sr_recommend_gsd_m: 2.0             # super_resolve is NOT_CONFIGURED; this only decides whether to say so
  nodata_warn_fraction: 0.5
  nodata_unassessable_fraction: 0.95
  full_scan_megapixels: 16.0
  black_level_percentile: 0.5
  stretch_low_percentile: 2.0
  stretch_high_percentile: 98.0
  gamma: 1.0
  video_assess_frames: 5
  announce_fraction: 0.001
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_config.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py configs/app.yaml tests/unit/test_restoration_config.py
git commit -m "feat(restoration): settings block and config hash"
```

(If `git diff --cached backend/app/config.py` shows unrelated hunks, stage only this task's hunks with `git add -p`.)

---

### Task 2: Schemas — the contracts

**Files:**
- Create: `backend/app/restoration/__init__.py`, `backend/app/restoration/schemas.py`
- Test: `tests/unit/test_restoration_schemas.py`

**Interfaces:**
- Produces: every name in spec §2.2–§2.8, plus `QualityMetric.direction: Literal["above","below"]`
  (D2) and `QualityAssessment.metric(name) -> Optional[QualityMetric]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_schemas.py
import pytest
from pydantic import ValidationError

from backend.app.restoration.schemas import (
    ConfidenceAdvice, DegradationKind, DetectorStatus, QualityAssessment, QualityMetric,
    RestorationReceipt, RestorationStatus, RestoredInput, StageReceipt, StageStatus, ThresholdBasis,
)


def _metric(**kw):
    base = dict(name="m", kind=DegradationKind.IMPULSE_NOISE, unit="fraction", detector_version="t@1")
    base.update(kw)
    return QualityMetric(**base)


def _applied(frac=0.1, **kw):
    base = dict(stage_id="s", stage_version="s@1", status=StageStatus.APPLIED, order=20,
                fraction_modified=frac)
    base.update(kw)
    return StageReceipt(**base)


def test_measured_requires_value():
    with pytest.raises(ValidationError, match="MEASURED requires a value"):
        _metric(value=None)


def test_failed_must_not_carry_value():
    with pytest.raises(ValidationError, match="must not carry a value"):
        _metric(status=DetectorStatus.FAILED, value=0.0, reason="x")


def test_failed_requires_reason():
    with pytest.raises(ValidationError, match="requires a reason"):
        _metric(status=DetectorStatus.FAILED)


def test_exceeds_above_and_below():
    assert _metric(value=0.01, threshold=0.001).exceeds_threshold is True
    assert _metric(value=0.21, threshold=0.30, direction="below").exceeds_threshold is True
    assert _metric(value=0.50, threshold=0.30, direction="below").exceeds_threshold is False
    assert _metric(value=0.5).exceeds_threshold is None


def test_gate_eligible_follows_basis():
    assert _metric(value=1.0, threshold_basis=ThresholdBasis.PROVISIONAL).gate_eligible is True
    assert _metric(value=1.0, threshold_basis=ThresholdBasis.NOT_CALIBRATED).gate_eligible is False


def test_non_applied_stage_requires_reason():
    with pytest.raises(ValidationError, match="requires a reason"):
        StageReceipt(stage_id="s", stage_version="s@0", status=StageStatus.NOT_CONFIGURED, order=90)


def test_applied_stage_requires_fraction_modified():
    with pytest.raises(ValidationError, match="fraction_modified"):
        StageReceipt(stage_id="s", stage_version="s@1", status=StageStatus.APPLIED, order=20)


def test_geometric_stage_is_unrepresentable():
    with pytest.raises(ValidationError, match="geometric"):
        _applied(is_geometric=True)


def test_confidence_multiplier_cannot_exceed_one():
    with pytest.raises(ValidationError):
        ConfidenceAdvice(max_confidence_multiplier=1.01)


def _inp(modified):
    return RestoredInput(image_index=0, original_path="a", consumed_path="b" if modified else "a",
                         was_modified=modified)


def test_receipt_input_modified_must_match_stages():
    with pytest.raises(ValidationError, match="input_modified"):
        RestorationReceipt(receipt_id="r", job_id="j", input_modified=True, stages=[_applied(frac=0.0)],
                           inputs=[_inp(True)])
    with pytest.raises(ValidationError, match="input_modified"):
        RestorationReceipt(receipt_id="r", job_id="j", input_modified=False, stages=[_applied(frac=0.1)])


def test_receipt_modified_needs_modified_input():
    with pytest.raises(ValidationError, match="no RestoredInput"):
        RestorationReceipt(receipt_id="r", job_id="j", input_modified=True, stages=[_applied()],
                           inputs=[_inp(False)])


def test_receipt_counts_and_roundtrip():
    nc = StageReceipt(stage_id="super_resolve", stage_version="none@0",
                      status=StageStatus.NOT_CONFIGURED, order=90, reason="off")
    r = RestorationReceipt(receipt_id="r", job_id="j", status=RestorationStatus.PARTIAL,
                           input_modified=True, stages=[_applied(), nc], inputs=[_inp(True)])
    assert (r.stages_planned, r.stages_applied, r.stages_not_configured) == (2, 1, 1)
    assert r.geometry_preserved is True
    again = RestorationReceipt.model_validate_json(r.model_dump_json())
    assert again.model_dump() == r.model_dump()


def test_assessment_metric_lookup():
    qa = QualityAssessment(assessment_id="qa", image_index=0, image_path="p", width=2, height=2, bands=1,
                           dtype="uint8", dn_max=255.0, valid_pixel_count=4, total_pixel_count=4,
                           metrics=[_metric(value=0.0)], detector_config_hash="0" * 16)
    assert qa.metric("m").value == 0.0
    assert qa.metric("absent") is None
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration'`

- [ ] **Step 3: Implement**

`backend/app/restoration/__init__.py`:

```python
"""
SatQuery AI — input quality assessment and restoration.

Spec: project/spec-2026-09-21-restoration-framework.md. Plan: project/plan-2026-09-30-restoration-core.md.
Pure in-memory library over (bands, H, W) arrays: detectors -> planner -> stages -> receipt.
"""
```

(Task 3 adds the `stages` import here.)

`backend/app/restoration/schemas.py`: copy spec §2.2–§2.8 verbatim, with these exact changes:

1. Header and imports:

```python
"""
Restoration contracts (spec §2). Pydantic because the receipt crosses the API boundary.

The model_validators make the dishonest states unconstructible: a metric carrying a value it did
not measure, a non-APPLIED stage without a reason, an APPLIED stage that does not say how much it
changed, a geometric stage, and a receipt whose input_modified disagrees with its stages.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator
```

2. In `QualityMetric`, add after `threshold_basis`:

```python
    direction: Literal["above", "below"] = "above"   # "below": the metric is bad when LOW (D2)
```

   and replace the `exceeds_threshold` lines of `_honesty` with:

```python
        if self.value is not None and self.threshold is not None:
            if self.direction == "above":
                self.exceeds_threshold = self.value >= self.threshold
            else:
                self.exceeds_threshold = self.value < self.threshold
        else:
            self.exceeds_threshold = None
```

3. Give `QualityAssessment.metric` a body:

```python
    def metric(self, name: str) -> Optional[QualityMetric]:
        return next((m for m in self.metrics if m.name == name), None)
```

4. Leave out the `StageFn` / `STAGE_REGISTRY` / `register_stage` block of §2.9, which goes to
   `registry.py` in Task 3. Everything else goes in unchanged, including all three `_honesty` /
   `_counts_and_honesty` validators.

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_schemas.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/__init__.py backend/app/restoration/schemas.py tests/unit/test_restoration_schemas.py
git commit -m "feat(restoration): schemas with honesty validators"
```

---
### Task 3: Stage registry and the two NOT_CONFIGURED stages

**Files:**
- Create: `backend/app/restoration/registry.py`, `backend/app/restoration/stages.py`
- Modify: `backend/app/restoration/__init__.py` (add one import)
- Test: `tests/unit/test_restoration_stage_registry.py`

**Interfaces:**
- Consumes: `StageReceipt`, `StageStatus`, `ThresholdBasis`, `QualityAssessment` (Task 2).
- Produces:
  - `StageFn = Callable[[np.ndarray, np.ndarray, QualityAssessment, Dict[str, Any]], Tuple[np.ndarray, StageReceipt]]`
  - `StageSpec(stage_id: str, order: int, version: str, fusable: bool, fn: StageFn)` (frozen dataclass)
  - `STAGE_ORDER: Dict[str, int]`, `STAGE_REGISTRY: Dict[str, StageSpec]`
  - `register_stage(stage_id, *, order, version, fusable=False)`
  - `get_stage(stage_id) -> Optional[StageSpec]`
  - `not_configured(stage_id, version, order, reason, params=None) -> StageReceipt`
  - `delta_stats(before, after, valid) -> Dict[str, float | int]` with keys `pixels_total`, `pixels_modified`, `fraction_modified`, `max_abs_delta_dn`, `mean_abs_delta_dn`
  - registered stages `gaussian_denoise` (order 30) and `super_resolve` (order 90)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_stage_registry.py
import numpy as np
import pytest

from backend.app.restoration import registry
from backend.app.restoration.registry import (
    STAGE_ORDER, STAGE_REGISTRY, delta_stats, get_stage, register_stage,
)
from backend.app.restoration.schemas import QualityAssessment, StageStatus


@pytest.fixture
def scratch_registry(monkeypatch):
    monkeypatch.setattr(registry, "STAGE_REGISTRY", dict(STAGE_REGISTRY))
    monkeypatch.setattr(registry, "STAGE_ORDER", {**STAGE_ORDER, "test_stage": 99})
    return registry


def _qa():
    return QualityAssessment(assessment_id="qa", image_index=0, image_path="p", width=4, height=4, bands=1,
                             dtype="uint8", dn_max=255.0, valid_pixel_count=16, total_pixel_count=16,
                             detector_config_hash="0" * 16)


def test_duplicate_id_raises(scratch_registry):
    scratch_registry.register_stage("test_stage", order=99, version="t@1")(lambda *a: None)
    with pytest.raises(RuntimeError, match="Duplicate stage"):
        scratch_registry.register_stage("test_stage", order=99, version="t@1")(lambda *a: None)


def test_wrong_order_raises(scratch_registry):
    with pytest.raises(RuntimeError, match="order"):
        scratch_registry.register_stage("test_stage", order=5, version="t@1")(lambda *a: None)


def test_unknown_stage_id_raises(scratch_registry):
    with pytest.raises(RuntimeError, match="STAGE_ORDER"):
        scratch_registry.register_stage("not_in_table", order=1, version="t@1")(lambda *a: None)


def test_every_registered_stage_matches_spec_order():
    assert {"gaussian_denoise", "super_resolve"} <= set(STAGE_REGISTRY)
    for sid, spec in STAGE_REGISTRY.items():
        assert spec.order == STAGE_ORDER[sid]


@pytest.mark.parametrize("sid", ["gaussian_denoise", "super_resolve"])
def test_not_configured_stages_return_input_untouched(sid):
    arr = np.arange(16, dtype=np.uint8).reshape(1, 4, 4)
    out, receipt = get_stage(sid).fn(arr, np.ones((4, 4), bool), _qa(), {})
    assert out is arr
    assert receipt.status is StageStatus.NOT_CONFIGURED
    assert receipt.reason and receipt.warnings


def test_super_resolve_says_it_did_not_upscale():
    _, receipt = get_stage("super_resolve").fn(np.zeros((1, 4, 4), np.uint8), np.ones((4, 4), bool), _qa(), {})
    assert "NOT upscaled" in receipt.reason


def test_delta_stats_ignores_invalid_pixels():
    before = np.zeros((2, 2, 2), np.uint8)
    after = before.copy()
    after[:, 0, 0] = 10          # valid pixel changed in both bands
    after[0, 1, 1] = 200         # invalid pixel (must not count)
    valid = np.array([[True, True], [True, False]])
    s = delta_stats(before, after, valid)
    assert s["pixels_total"] == 3 and s["pixels_modified"] == 1
    assert s["fraction_modified"] == pytest.approx(1 / 3)
    assert s["max_abs_delta_dn"] == 10.0
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_stage_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration.registry'`

- [ ] **Step 3: Implement**

`backend/app/restoration/registry.py`:

```python
"""
Restoration stage registry (spec §2.9).

Mirrors agent/tools/base.py::register_tool: a decorator, not a hand-maintained dict, because a stage
that is written but not registered fails silently. Duplicate ids and orders that disagree with
STAGE_ORDER (spec §4.1) raise at import time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from backend.app.restoration.schemas import QualityAssessment, StageReceipt, StageStatus

StageFn = Callable[[np.ndarray, np.ndarray, QualityAssessment, Dict[str, Any]], Tuple[np.ndarray, StageReceipt]]

#: Spec §4.1. The order is forced (impulses before the fitted stretch, SR last), not a preference.
#: mask_invalid is not a stage (plan D4): build_valid_mask() runs before any stage.
STAGE_ORDER: Dict[str, int] = {
    "impulse_denoise": 20,
    "gaussian_denoise": 30,
    "destripe": 40,
    "photometric_correct": 50,
    "super_resolve": 90,
}


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    order: int
    version: str
    fusable: bool
    fn: StageFn


STAGE_REGISTRY: Dict[str, StageSpec] = {}


def register_stage(stage_id: str, *, order: int, version: str,
                   fusable: bool = False) -> Callable[[StageFn], StageFn]:
    def decorator(fn: StageFn) -> StageFn:
        if stage_id not in STAGE_ORDER:
            raise RuntimeError(f"Stage '{stage_id}' is not in STAGE_ORDER {sorted(STAGE_ORDER)}; add it there first")
        if STAGE_ORDER[stage_id] != order:
            raise RuntimeError(f"Stage '{stage_id}' registered at order {order}, STAGE_ORDER says {STAGE_ORDER[stage_id]}")
        if stage_id in STAGE_REGISTRY:
            raise RuntimeError(f"Duplicate stage registration for '{stage_id}'")
        STAGE_REGISTRY[stage_id] = StageSpec(stage_id, order, version, fusable, fn)
        return fn

    return decorator


def get_stage(stage_id: str) -> Optional[StageSpec]:
    return STAGE_REGISTRY.get(stage_id)


def not_configured(stage_id: str, version: str, order: int, reason: str,
                   params: Optional[Dict[str, Any]] = None) -> StageReceipt:
    """The receipt for a stage that exists in the plan but cannot run. Never silence (spec §8.2)."""
    return StageReceipt(stage_id=stage_id, stage_version=version, status=StageStatus.NOT_CONFIGURED,
                        reason=reason, order=order, params=params or {},
                        warnings=[f"{stage_id} NOT_CONFIGURED: {reason}"])


def delta_stats(before: np.ndarray, after: np.ndarray, valid: np.ndarray) -> Dict[str, Any]:
    """How much a stage changed, over valid pixels only. A pixel counts as modified if any band changed."""
    delta = np.abs(after.astype(np.float64) - before.astype(np.float64))[:, valid]   # (bands, n_valid)
    n_valid = int(valid.sum())
    n_mod = int(np.any(delta > 0, axis=0).sum())
    return {
        "pixels_total": n_valid,
        "pixels_modified": n_mod,
        "fraction_modified": n_mod / max(n_valid, 1),
        "max_abs_delta_dn": float(delta.max()) if delta.size else 0.0,
        "mean_abs_delta_dn": float(delta.mean()) if delta.size else 0.0,
    }
```

`backend/app/restoration/stages.py`:

```python
"""
Stages that exist so they can say NOT_CONFIGURED (spec §8.2). A silently absent stage would be
indistinguishable from one that ran. Importing this module registers every stage.
"""
from __future__ import annotations

from backend.app.restoration.registry import not_configured, register_stage


@register_stage("gaussian_denoise", order=30, version="none@0")
def gaussian_denoise(arr, valid_mask, assessment, params):
    return arr, not_configured(
        "gaussian_denoise", "none@0", 30,
        "Gaussian denoising is not implemented; gaussian_noise_sigma_dn exceeded its PROVISIONAL gate "
        "but the image was NOT denoised.", params)


@register_stage("super_resolve", order=90, version="none@0")
def super_resolve(arr, valid_mask, assessment, params):
    return arr, not_configured(
        "super_resolve", "none@0", 90,
        "Learned super-resolution is disabled on this deployment: no Real-ESRGAN or SwinIR checkpoint "
        "has been verified with scripts/verify_checkpoints.py and no held-out score has been measured "
        "(project/split-ushnik-ayushman.md, Ayushman #4). The image was NOT upscaled.", params)
```

Add to the end of `backend/app/restoration/__init__.py`:

```python
from backend.app.restoration import stages  # noqa: E402,F401  (side effect: registers every stage)
```

- [ ] **Step 4: Run the new tests and the Task 2 tests**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_stage_registry.py tests/unit/test_restoration_schemas.py -v`
Expected: all pass (8 + 13)

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/registry.py backend/app/restoration/stages.py backend/app/restoration/__init__.py tests/unit/test_restoration_stage_registry.py
git commit -m "feat(restoration): stage registry; gaussian_denoise and super_resolve report NOT_CONFIGURED"
```

---

### Task 4: Detector core — valid mask, dn_max, sampling, impulse density, `assess()`

**Files:**
- Create: `backend/app/restoration/detectors.py`, `tests/unit/restoration_fixtures.py`
- Test: `tests/unit/test_restoration_detectors.py`

**Interfaces:**
- Consumes: `RestorationSettings` (Task 1); schemas (Task 2); `backend.app.geo.metadata.RasterMetadata`.
- Produces:
  - `METRIC_BASIS: Dict[str, ThresholdBasis]` (all 11 metric names; the planner validates against it)
  - `build_valid_mask(arr, nodata) -> np.ndarray[bool] (H, W)`
  - `compute_dn_max(arr, valid) -> float`
  - `impulse_params(dn_max, cfg) -> {"dev_dn": float, "extreme_tol_dn": float, "max_similar_neighbours": int}`
  - `impulse_candidates(band, valid, dn_max, *, dev_dn, extreme_tol_dn, max_similar_neighbours) -> np.ndarray[bool]`
    (Task 8's median uses **this same function**, so the detector and the stage agree on what an impulse is)
  - `assess(arr, meta, cfg, *, job_id, image_index, image_path, source_kind=SourceKind.RASTER, frame_index=None, timestamp_sec=None) -> QualityAssessment`
  - internals Task 5 extends: `_Ctx`, `_Detector`, `_DETECTORS: List[_Detector]`, `_pooled(ctx, b)`
  - fixtures: `smooth_image`, `inject_salt_pepper`, `bright_lines`, `meta_for`

- [ ] **Step 1: Write the shared fixtures**

```python
# tests/unit/restoration_fixtures.py
"""Synthetic imagery for the restoration tests. Ground truth is the injected corruption (spec §9.3)."""
import numpy as np
from scipy import ndimage

from backend.app.geo.metadata import RasterMetadata


def smooth_image(h=256, w=256, bands=3, lo=60, hi=190, seed=0, dtype=np.uint8):
    """Low-frequency texture in [lo, hi]: no pixel is near 0 or dn_max, no pixel is an outlier."""
    rng = np.random.default_rng(seed)
    out = np.empty((bands, h, w), dtype=dtype)
    for b in range(bands):
        f = ndimage.gaussian_filter(rng.random((h, w)), 4)
        f = (f - f.min()) / (f.max() - f.min())
        out[b] = np.round(lo + f * (hi - lo)).astype(dtype)
    return out


def inject_salt_pepper(img, density, seed=1, salt_only=False, region=None):
    """Corrupts round(density * eligible) pixels in every band. Returns (corrupted, positions (H, W) bool)."""
    rng = np.random.default_rng(seed)
    bands, h, w = img.shape
    eligible = np.flatnonzero(region.ravel()) if region is not None else np.arange(h * w)
    n = int(round(density * eligible.size))
    pick = rng.choice(eligible, size=n, replace=False)
    top = np.iinfo(img.dtype).max
    vals = np.full(n, top, dtype=img.dtype) if salt_only else np.where(rng.random(n) < 0.5, top, 0).astype(img.dtype)
    out = img.copy()
    flat = out.reshape(bands, -1)
    flat[:, pick] = vals
    mask = np.zeros(h * w, dtype=bool)
    mask[pick] = True
    return out, mask.reshape(h, w)


def bright_lines(h=256, w=256, bands=3):
    """1-px roads: a vertical and a diagonal 255 line on a 20 field. Not salt-and-pepper."""
    img = np.full((bands, h, w), 20, dtype=np.uint8)
    img[:, :, 100] = 255
    idx = np.arange(min(h, w))
    img[:, idx, idx] = 255
    return img


def meta_for(arr, nodata=None, resolution=None):
    return RasterMetadata(filepath="synthetic.tif", filename="synthetic.tif", format="TIFF",
                          width=arr.shape[2], height=arr.shape[1], bands=arr.shape[0], dtype=str(arr.dtype),
                          nodata=nodata, resolution=resolution)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/test_restoration_detectors.py
import numpy as np
import pytest

from backend.app.config import RestorationSettings
from backend.app.restoration import detectors
from backend.app.restoration.detectors import assess, build_valid_mask, compute_dn_max
from backend.app.restoration.schemas import DetectorStatus, QualityVerdict
from tests.unit.restoration_fixtures import bright_lines, inject_salt_pepper, meta_for, smooth_image

CFG = RestorationSettings()


def _assess(arr, cfg=CFG, **meta_kw):
    return assess(arr, meta_for(arr, **meta_kw), cfg, job_id="t", image_index=0, image_path="synthetic.tif")


def test_valid_mask_excludes_nodata_and_nonfinite():
    arr = np.ones((2, 2, 2), np.float32)
    arr[0, 0, 0] = np.nan
    arr[1, 1, 1] = -9999
    assert build_valid_mask(arr, -9999).tolist() == [[False, True], [True, False]]


def test_dn_max_by_dtype():
    v = np.ones((2, 2), bool)
    assert compute_dn_max(np.zeros((1, 2, 2), np.uint8), v) == 255.0
    assert compute_dn_max(np.zeros((1, 2, 2), np.uint16), v) == 65535.0
    f = np.linspace(0, 1, 10000, dtype=np.float32).reshape(1, 100, 100)
    assert compute_dn_max(f, np.ones((100, 100), bool)) == pytest.approx(0.9999, abs=1e-3)


@pytest.mark.parametrize("density", [0.001, 0.01, 0.05])
def test_impulse_density_recovers_injected_fraction(density):
    noisy, _ = inject_salt_pepper(smooth_image(512, 512), density)
    m = _assess(noisy).metric("impulse_density")
    assert m.status is DetectorStatus.MEASURED
    assert abs(m.value - density) / density <= 0.15          # TARGET, spec §9.1
    if density > CFG.impulse_gate:                          # at exactly the gate, pixel rounding decides
        assert m.exceeds_threshold is True


def test_clean_image_measures_near_zero():
    m = _assess(smooth_image(512, 512)).metric("impulse_density")
    assert m.value < 1e-4 and m.exceeds_threshold is False


def test_one_pixel_roads_are_not_salt_and_pepper():
    """The clause-4 guard (spec §3.1): thin bright structures have similar neighbours along the line."""
    assert _assess(bright_lines()).metric("impulse_density").value < 0.0005


def test_nodata_excluded_from_numerator_and_denominator():
    img = smooth_image(256, 256)
    img[:, :, :128] = 0                                   # nodata=0 on the left half
    right = np.zeros((256, 256), bool)
    right[:, 128:] = True
    noisy, _ = inject_salt_pepper(img, 0.01, salt_only=True, region=right)
    qa = _assess(noisy, nodata=0)
    assert qa.valid_pixel_count == 256 * 128
    assert qa.metric("nodata_fraction").value == pytest.approx(0.5)
    assert abs(qa.metric("impulse_density").value - 0.01) / 0.01 <= 0.15


def test_sampled_estimate_reports_its_sample_fraction():
    noisy, _ = inject_salt_pepper(smooth_image(512, 512), 0.01)
    m = _assess(noisy, cfg=RestorationSettings(full_scan_megapixels=0.07)).metric("impulse_density")
    assert m.sample_fraction == pytest.approx(0.25)
    assert abs(m.value - 0.01) / 0.01 <= 0.25
    assert "NOT MEASURED" in m.notes


def test_detector_exception_is_failed_not_zero(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("synthetic failure")
    monkeypatch.setattr(detectors, "impulse_candidates", boom)
    qa = _assess(smooth_image())
    m = qa.metric("impulse_density")
    assert m.status is DetectorStatus.FAILED and m.value is None and "synthetic failure" in m.reason
    assert qa.metric("nodata_fraction").status is DetectorStatus.MEASURED
    assert any("impulse_density" in w for w in qa.warnings)


def test_all_nodata_is_unassessable():
    qa = _assess(np.zeros((3, 32, 32), np.uint8), nodata=0)
    assert qa.verdict is QualityVerdict.UNASSESSABLE
    assert qa.metric("nodata_fraction").value == 1.0


def test_assessment_identity_fields():
    arr = smooth_image(64, 64)
    qa = assess(arr, meta_for(arr), CFG, job_id="job9", image_index=2, image_path="x.tif", frame_index=7)
    assert qa.assessment_id == "qa_job9_2_f7"
    assert (qa.width, qa.height, qa.bands, qa.dtype) == (64, 64, 3, "uint8")
    assert qa.detector_config_hash == CFG.config_hash()
```

- [ ] **Step 3: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_detectors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration.detectors'`

- [ ] **Step 4: Implement**

```python
# backend/app/restoration/detectors.py
"""
Quality detectors (spec §3). Every detector works on (bands, H, W) in native DN, restricted to the
valid mask. A detector that cannot measure returns value=None with a reason. It never returns 0.0,
because a fabricated zero reads as "measured clean".
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import ndimage

from backend.app.config import RestorationSettings
from backend.app.geo.metadata import RasterMetadata
from backend.app.logging import logger
from backend.app.restoration.schemas import (
    DegradationKind, DetectorStatus, QualityAssessment, QualityMetric, QualityVerdict, SourceKind,
    ThresholdBasis,
)

P, V, N = ThresholdBasis.PRINCIPLED, ThresholdBasis.PROVISIONAL, ThresholdBasis.NOT_CALIBRATED

#: Spec §3.2/§3.3, with plan D5 for gsd_m. The planner refuses to gate on a NOT_CALIBRATED name.
METRIC_BASIS: Dict[str, ThresholdBasis] = {
    "impulse_density": V, "nodata_fraction": P, "saturation_high": P, "saturation_low": P,
    "dynamic_range_p2_p98": V, "black_level_dn": P, "grey_world_gain": V,
    "gaussian_noise_sigma_dn": V, "blur_laplacian_variance": N, "stripe_score": N, "gsd_m": V,
}

_TILE = 256


def build_valid_mask(arr: np.ndarray, nodata: Optional[float]) -> np.ndarray:
    """True where every band is finite and not equal to nodata (spec §2.1 rule 4)."""
    valid = np.ones(arr.shape[1:], dtype=bool)
    if np.issubdtype(arr.dtype, np.floating):
        valid &= np.all(np.isfinite(arr), axis=0)
    if nodata is not None and not np.isnan(nodata):
        valid &= ~np.any(arr == nodata, axis=0)
    return valid


def compute_dn_max(arr: np.ndarray, valid: np.ndarray) -> float:
    """Full-scale value (spec §2.1 rule 3): the dtype max for integers, the measured p99.99 for floats."""
    if np.issubdtype(arr.dtype, np.integer):
        return float(np.iinfo(arr.dtype).max)
    vals = arr[:, valid]
    if vals.size == 0:
        raise ValueError("no valid pixels to measure a float dn_max")
    dn_max = float(np.percentile(vals, 99.99))
    if dn_max <= 0:
        raise ValueError(f"float raster p99.99 is {dn_max}; no positive full-scale value")
    return dn_max


def impulse_params(dn_max: float, cfg: RestorationSettings) -> Dict[str, float]:
    scale = dn_max / 255.0
    return {"dev_dn": cfg.impulse_dev_dn_u8 * scale,
            "extreme_tol_dn": cfg.impulse_extreme_tol_dn_u8 * scale,
            "max_similar_neighbours": cfg.impulse_max_similar_neighbours}


def impulse_candidates(band: np.ndarray, valid: np.ndarray, dn_max: float, *, dev_dn: float,
                       extreme_tol_dn: float, max_similar_neighbours: int) -> np.ndarray:
    """
    Spec §3.1 clauses 1-5. A pixel is an impulse iff it is far from its 3x3 median, has at most
    `max_similar_neighbours` of 8 neighbours within dev_dn of itself, and is extreme or very far off.
    Invalid pixels are median-filled for the filter and NaN for the neighbour test, so nodata neither
    leaks into the median nor counts as a similar neighbour. Out-of-raster neighbours are NaN too.
    """
    if not valid.any():
        return np.zeros(band.shape, dtype=bool)
    x = band.astype(np.float32)
    filled = x.copy()
    filled[~valid] = np.median(x[valid])
    med = ndimage.median_filter(filled, size=3, mode="nearest")
    dev = np.abs(x - med)

    x_nan = np.where(valid, x, np.nan)
    padded = np.pad(x_nan, 1, mode="constant", constant_values=np.nan)
    h, w = x.shape
    similar = np.zeros(x.shape, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            if dy == 1 and dx == 1:
                continue
            similar += np.abs(x - padded[dy:dy + h, dx:dx + w]) < dev_dn   # NaN compares False
    isolated = similar <= max_similar_neighbours
    extreme = (x <= extreme_tol_dn) | (x >= dn_max - extreme_tol_dn)
    return valid & (dev >= dev_dn) & isolated & (extreme | (dev >= 2 * dev_dn))


@dataclass
class _Ctx:
    arr: np.ndarray                                   # the full raster
    valid: np.ndarray                                 # the full valid mask
    tiles: List[Tuple[np.ndarray, np.ndarray]]        # what detectors examine (spec §3.5)
    sample_fraction: float
    dn_max: float
    meta: RasterMetadata
    cfg: RestorationSettings


@dataclass(frozen=True)
class _Detector:
    name: str
    kind: DegradationKind
    unit: str
    version: str
    fn: Callable[[_Ctx], QualityMetric]


def _tiles(arr: np.ndarray, valid: np.ndarray, budget_px: float) -> Tuple[List[Tuple[np.ndarray, np.ndarray]], float]:
    """Whole raster under the budget, else a regular grid of tiles totalling about the budget."""
    _, h, w = arr.shape
    if h * w <= budget_px:
        return [(arr, valid)], 1.0
    th, tw = min(_TILE, h), min(_TILE, w)
    side = int(np.ceil(np.sqrt(max(1, int(budget_px // (th * tw))))))
    ys = np.unique(np.linspace(0, h - th, side).astype(int))
    xs = np.unique(np.linspace(0, w - tw, side).astype(int))
    tiles = [(arr[:, y:y + th, x:x + tw], valid[y:y + th, x:x + tw]) for y in ys for x in xs]
    return tiles, min(1.0, sum(v.size for _, v in tiles) / (h * w))


def _pooled(ctx: _Ctx, b: int) -> np.ndarray:
    """All examined valid values of band b, float64."""
    return np.concatenate([t[b][v].astype(np.float64) for t, v in ctx.tiles])


def _sampled_note(ctx: _Ctx) -> str:
    return "" if ctx.sample_fraction >= 1.0 else "; estimated on a tile sample, sampling error NOT MEASURED"


def _m_nodata(ctx: _Ctx) -> QualityMetric:
    frac = 1.0 - int(ctx.valid.sum()) / ctx.valid.size
    return QualityMetric(name="nodata_fraction", kind=DegradationKind.MISSING_DATA, value=frac, unit="fraction",
                         threshold=ctx.cfg.nodata_warn_fraction, threshold_basis=METRIC_BASIS["nodata_fraction"],
                         detector_version="nodata@1")


def _m_impulse(ctx: _Ctx) -> QualityMetric:
    p = impulse_params(ctx.dn_max, ctx.cfg)
    per_band: Dict[str, float] = {}
    for b in range(ctx.arr.shape[0]):
        cand = sum(int(impulse_candidates(t[b], v, ctx.dn_max, **p).sum()) for t, v in ctx.tiles)
        n = sum(int(v.sum()) for _, v in ctx.tiles)
        per_band[str(b)] = cand / max(n, 1)
    return QualityMetric(
        name="impulse_density", kind=DegradationKind.IMPULSE_NOISE, value=max(per_band.values()),
        unit="fraction", per_band=per_band, reduction="max_over_bands", threshold=ctx.cfg.impulse_gate,
        threshold_basis=METRIC_BASIS["impulse_density"], sample_fraction=ctx.sample_fraction,
        detector_version="impulse@1",
        notes=f"8-neighbour isolation test, dev_dn={p['dev_dn']:.4g}, "
              f"max_similar_neighbours={p['max_similar_neighbours']}{_sampled_note(ctx)}")


_DETECTORS: List[_Detector] = [
    _Detector("nodata_fraction", DegradationKind.MISSING_DATA, "fraction", "nodata@1", _m_nodata),
    _Detector("impulse_density", DegradationKind.IMPULSE_NOISE, "fraction", "impulse@1", _m_impulse),
]


def _run(d: _Detector, ctx: _Ctx) -> QualityMetric:
    try:
        return d.fn(ctx)
    except Exception as e:  # a broken detector is reported, never allowed to take the job down (spec §6.3)
        logger.warning(f"restoration detector {d.name} failed: {e}")
        return QualityMetric(name=d.name, kind=d.kind, status=DetectorStatus.FAILED, unit=d.unit,
                             threshold_basis=METRIC_BASIS[d.name], sample_fraction=0.0,
                             detector_version=d.version, reason=f"{type(e).__name__}: {e}")


def assess(arr: np.ndarray, meta: RasterMetadata, cfg: RestorationSettings, *, job_id: str, image_index: int,
           image_path: str, source_kind: SourceKind = SourceKind.RASTER, frame_index: Optional[int] = None,
           timestamp_sec: Optional[float] = None) -> QualityAssessment:
    t0 = time.perf_counter()
    if arr.ndim == 2:
        arr = arr[np.newaxis]
    bands, h, w = arr.shape
    valid = build_valid_mask(arr, meta.nodata)
    n_valid = int(valid.sum())
    base = dict(
        assessment_id=f"qa_{job_id}_{image_index}" + (f"_f{frame_index}" if frame_index is not None else ""),
        source_kind=source_kind, image_index=image_index, image_path=image_path, frame_index=frame_index,
        timestamp_sec=timestamp_sec, width=w, height=h, bands=bands, dtype=str(arr.dtype), nodata=meta.nodata,
        valid_pixel_count=n_valid, total_pixel_count=h * w, detector_config_hash=cfg.config_hash())

    if n_valid == 0:
        dn_max = float(np.iinfo(arr.dtype).max) if np.issubdtype(arr.dtype, np.integer) else 0.0
        ctx = _Ctx(arr, valid, [], 0.0, dn_max, meta, cfg)
        return QualityAssessment(**base, dn_max=dn_max, metrics=[_m_nodata(ctx)],
                                 verdict=QualityVerdict.UNASSESSABLE,
                                 warnings=["Quality could not be assessed: the raster has no valid pixels."],
                                 duration_ms=(time.perf_counter() - t0) * 1000)

    dn_max = compute_dn_max(arr, valid)
    tiles, frac = _tiles(arr, valid, cfg.full_scan_megapixels * 1e6)
    ctx = _Ctx(arr, valid, tiles, frac, dn_max, meta, cfg)
    metrics = [_run(d, ctx) for d in _DETECTORS]

    degradations: List[DegradationKind] = []
    for m in metrics:
        if m.gate_eligible and m.exceeds_threshold and m.kind not in degradations:
            degradations.append(m.kind)
    nodata = next(m for m in metrics if m.name == "nodata_fraction")
    if nodata.value is not None and nodata.value >= cfg.nodata_unassessable_fraction:
        verdict = QualityVerdict.UNASSESSABLE
    else:
        verdict = QualityVerdict.DEGRADED if degradations else QualityVerdict.CLEAN

    return QualityAssessment(
        **base, dn_max=dn_max, metrics=metrics, verdict=verdict, degradations_detected=degradations,
        advisories=[f"{m.name}={m.value:.4g} is measured but its threshold is NOT_CALIBRATED; it gates nothing."
                    for m in metrics if m.status is DetectorStatus.MEASURED
                    and m.threshold_basis is ThresholdBasis.NOT_CALIBRATED],
        warnings=[f"{m.name} {m.status.value}: {m.reason}" for m in metrics
                  if m.status in (DetectorStatus.NOT_CONFIGURED, DetectorStatus.FAILED)],
        duration_ms=(time.perf_counter() - t0) * 1000)
```

- [ ] **Step 5: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_detectors.py -v`
Expected: 12 passed. If a recovery case misses the ±15% target, **do not widen the tolerance**.
Print `m.value` next to the injected density, record both numbers, and stop to report. The target
is the spec's claim, and missing it is a finding.

- [ ] **Step 6: Commit**

```bash
git add backend/app/restoration/detectors.py tests/unit/restoration_fixtures.py tests/unit/test_restoration_detectors.py
git commit -m "feat(restoration): valid mask, dn_max, tile sampling, impulse density detector"
```

---

### Task 5: The remaining detectors

**Files:**
- Modify: `backend/app/restoration/detectors.py` (add metric functions; extend `_DETECTORS`; add `import warnings`)
- Test: `tests/unit/test_restoration_detectors.py` (append)

**Interfaces:**
- Consumes: `_Ctx`, `_Detector`, `_pooled`, `_sampled_note`, `impulse_params`, `impulse_candidates` (Task 4).
- Produces: metrics named `saturation_high`, `saturation_low`, `dynamic_range_p2_p98` (direction
  `below`), `black_level_dn`, `grey_world_gain`, `gaussian_noise_sigma_dn`, `blur_laplacian_variance`,
  `stripe_score`, `gsd_m`. `photometric_correct` (Task 7) reads nothing from these. It refits on the
  post-impulse array.

- [ ] **Step 1: Append the failing tests**

```python
# appended to tests/unit/test_restoration_detectors.py
from backend.app.restoration.schemas import DegradationKind, ThresholdBasis


def test_clean_image_is_clean_and_complete():
    img = smooth_image(256, 256, lo=10, hi=245)
    img[1] = img[0]
    img[2] = img[0]            # a grey scene: grey-world gains are exactly 1, no fixture luck involved
    qa = _assess(img)
    names = {m.name for m in qa.metrics}
    assert names == set(detectors.METRIC_BASIS)
    assert qa.verdict is QualityVerdict.CLEAN, [(m.name, m.value) for m in qa.metrics if m.exceeds_threshold]


def test_saturation_is_reported():
    img = smooth_image(128, 128)
    img[:, :20, :] = 255                                   # ~15.6% clipped high
    qa = _assess(img)
    assert qa.metric("saturation_high").value == pytest.approx(20 / 128)
    assert DegradationKind.SATURATION_CLIPPING in qa.degradations_detected


def test_low_dynamic_range_fires_below_threshold():
    qa = _assess(smooth_image(128, 128, lo=100, hi=150))   # range ~0.18 of 255
    m = qa.metric("dynamic_range_p2_p98")
    assert m.direction == "below" and m.value < 0.30 and m.exceeds_threshold is True
    assert DegradationKind.LOW_DYNAMIC_RANGE in qa.degradations_detected


def test_black_level_is_a_parameter_not_a_gate():
    m = _assess(smooth_image(128, 128)).metric("black_level_dn")
    assert m.value >= 60 and m.threshold is None and m.exceeds_threshold is None


def test_grey_world_detects_a_colour_cast():
    img = smooth_image(128, 128)
    img[0] = np.clip(img[0].astype(int) + 60, 0, 255).astype(np.uint8)   # red cast
    m = _assess(img).metric("grey_world_gain")
    assert m.value > 1.15 and m.exceeds_threshold is True


def test_grey_world_not_applicable_on_one_band():
    m = _assess(smooth_image(64, 64, bands=1)).metric("grey_world_gain")
    assert m.status is DetectorStatus.NOT_APPLICABLE and m.value is None and m.reason


def test_gaussian_noise_sigma_is_measured():
    rng = np.random.default_rng(3)
    clean = smooth_image(256, 256)
    noisy = np.clip(clean + rng.normal(0, 20, clean.shape), 0, 255).astype(np.uint8)
    s_clean = _assess(clean).metric("gaussian_noise_sigma_dn").value
    s_noisy = _assess(noisy).metric("gaussian_noise_sigma_dn").value
    assert s_clean < 2.0
    assert 12.0 < s_noisy < 25.0     # smoke range; x - median3x3 underestimates sigma, NOT a calibration


def test_blur_and_stripes_are_advisories_that_gate_nothing():
    # Flat field + iid noise: column means of a smooth texture are correlated and would blur the contrast.
    rng = np.random.default_rng(4)
    img = np.clip(120 + rng.normal(0, 5, (3, 128, 128)), 0, 255).astype(np.uint8)
    striped = img.copy()
    striped[:, :, ::8] = np.clip(striped[:, :, ::8].astype(int) + 30, 0, 255).astype(np.uint8)
    clean_qa, striped_qa = _assess(img), _assess(striped)
    for qa in (clean_qa, striped_qa):
        for name in ("blur_laplacian_variance", "stripe_score"):
            m = qa.metric(name)
            assert m.threshold_basis is ThresholdBasis.NOT_CALIBRATED
            assert m.gate_eligible is False and m.exceeds_threshold is None
            assert any(a.startswith(name) for a in qa.advisories)
    assert striped_qa.metric("stripe_score").value > 2 * clean_qa.metric("stripe_score").value


def test_gsd_read_from_projected_metre_crs_only():
    arr = smooth_image(32, 32)
    utm = assess(arr, meta_for(arr, resolution=[10.0, 10.0]).model_copy(update={"crs": "EPSG:32614"}),
                 CFG, job_id="t", image_index=0, image_path="p")
    assert utm.metric("gsd_m").value == 10.0 and utm.metric("gsd_m").exceeds_threshold is True
    geo = assess(arr, meta_for(arr, resolution=[0.0001, 0.0001]).model_copy(update={"crs": "EPSG:4326"}),
                 CFG, job_id="t", image_index=0, image_path="p")
    assert geo.metric("gsd_m").status is DetectorStatus.NOT_APPLICABLE
    assert _assess(arr).metric("gsd_m").status is DetectorStatus.NOT_APPLICABLE   # no CRS at all
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_detectors.py -v`
Expected: the Task 4 tests pass. The new ones FAIL (`AttributeError: 'NoneType' object has no attribute 'value'`, or the name-set assertion).

- [ ] **Step 3: Implement**

Add `import warnings` to the imports. Add these functions after `_m_impulse`:

```python
def _not_applicable(ctx: _Ctx, name: str, kind: DegradationKind, unit: str, version: str, reason: str) -> QualityMetric:
    return QualityMetric(name=name, kind=kind, status=DetectorStatus.NOT_APPLICABLE, unit=unit,
                         threshold_basis=METRIC_BASIS[name], sample_fraction=0.0, detector_version=version,
                         reason=reason)


def _saturation(ctx: _Ctx, name: str, clipped: Callable[[np.ndarray], np.ndarray]) -> QualityMetric:
    per_band = {str(b): float(np.mean(clipped(_pooled(ctx, b)))) for b in range(ctx.arr.shape[0])}
    return QualityMetric(name=name, kind=DegradationKind.SATURATION_CLIPPING, value=max(per_band.values()),
                         unit="fraction", per_band=per_band, threshold=ctx.cfg.saturation_gate,
                         threshold_basis=METRIC_BASIS[name], sample_fraction=ctx.sample_fraction,
                         detector_version="saturation@1")


def _m_saturation_high(ctx: _Ctx) -> QualityMetric:
    return _saturation(ctx, "saturation_high", lambda v: v >= ctx.dn_max)


def _m_saturation_low(ctx: _Ctx) -> QualityMetric:
    return _saturation(ctx, "saturation_low", lambda v: v <= 0)


def _m_dynamic_range(ctx: _Ctx) -> QualityMetric:
    per_band = {}
    for b in range(ctx.arr.shape[0]):
        lo, hi = np.percentile(_pooled(ctx, b), [ctx.cfg.stretch_low_percentile, ctx.cfg.stretch_high_percentile])
        per_band[str(b)] = float((hi - lo) / ctx.dn_max)
    return QualityMetric(name="dynamic_range_p2_p98", kind=DegradationKind.LOW_DYNAMIC_RANGE,
                         value=min(per_band.values()), unit="dimensionless", per_band=per_band,
                         reduction="min_over_bands", direction="below", threshold=ctx.cfg.dynamic_range_gate,
                         threshold_basis=METRIC_BASIS["dynamic_range_p2_p98"], sample_fraction=ctx.sample_fraction,
                         detector_version="dynrange@1")


def _m_black_level(ctx: _Ctx) -> QualityMetric:
    per_band = {str(b): float(np.percentile(_pooled(ctx, b), ctx.cfg.black_level_percentile))
                for b in range(ctx.arr.shape[0])}
    return QualityMetric(name="black_level_dn", kind=DegradationKind.BRIGHTNESS_BIAS, value=max(per_band.values()),
                         unit="dn", per_band=per_band, threshold_basis=METRIC_BASIS["black_level_dn"],
                         sample_fraction=ctx.sample_fraction, detector_version="blacklevel@1",
                         notes="a parameter of photometric_correct, not a gate (plan D3)")


def _m_grey_world(ctx: _Ctx) -> QualityMetric:
    bands = ctx.arr.shape[0]
    if bands < 3:
        return _not_applicable(ctx, "grey_world_gain", DegradationKind.COLOR_CAST, "dimensionless", "greyworld@1",
                               f"grey-world needs at least 3 bands; this raster has {bands}")
    means = [float(_pooled(ctx, b).mean()) for b in range(3)]
    if min(means) <= 0:
        return _not_applicable(ctx, "grey_world_gain", DegradationKind.COLOR_CAST, "dimensionless", "greyworld@1",
                               f"a band mean is not positive ({means}); a gain is undefined")
    target = sum(means) / 3
    gains = [target / m for m in means]
    return QualityMetric(name="grey_world_gain", kind=DegradationKind.COLOR_CAST, value=max(gains) / min(gains),
                         unit="dimensionless", per_band={str(b): g for b, g in enumerate(gains)},
                         reduction="max_gain_over_min_gain", threshold=ctx.cfg.grey_world_ratio_gate,
                         threshold_basis=METRIC_BASIS["grey_world_gain"], sample_fraction=ctx.sample_fraction,
                         detector_version="greyworld@1", notes="first three bands only")


def _m_gaussian_noise(ctx: _Ctx) -> QualityMetric:
    p = impulse_params(ctx.dn_max, ctx.cfg)
    per_band = {}
    for b in range(ctx.arr.shape[0]):
        parts = []
        for t, v in ctx.tiles:
            if not v.any():
                continue
            x = t[b].astype(np.float32)
            filled = x.copy()
            filled[~v] = np.median(x[v])
            resid = x - ndimage.median_filter(filled, size=3, mode="nearest")
            parts.append(resid[v & ~impulse_candidates(t[b], v, ctx.dn_max, **p)])
        r = np.concatenate(parts) if parts else np.empty(0)
        if r.size == 0:
            raise ValueError("no non-impulse valid pixels to estimate noise from")
        per_band[str(b)] = float(1.4826 * np.median(np.abs(r - np.median(r))))
    return QualityMetric(name="gaussian_noise_sigma_dn", kind=DegradationKind.GAUSSIAN_NOISE,
                         value=max(per_band.values()), unit="dn", per_band=per_band,
                         threshold=ctx.cfg.gaussian_sigma_gate_fraction * ctx.dn_max,
                         threshold_basis=METRIC_BASIS["gaussian_noise_sigma_dn"],
                         sample_fraction=ctx.sample_fraction, detector_version="gnoise@1",
                         notes="1.4826 x MAD of x - median3x3, impulse candidates excluded" + _sampled_note(ctx))


def _luma(t: np.ndarray) -> np.ndarray:
    return t[: min(3, t.shape[0])].astype(np.float64).mean(axis=0)


def _m_blur(ctx: _Ctx) -> QualityMetric:
    vals = []
    for t, v in ctx.tiles:
        inner = ndimage.binary_erosion(v, border_value=0)   # 4-connected, matching laplace's stencil
        vals.append(ndimage.laplace(_luma(t), mode="nearest")[inner])
    lap = np.concatenate(vals)
    if lap.size == 0:
        raise ValueError("no interior valid pixels for a Laplacian")
    return QualityMetric(name="blur_laplacian_variance", kind=DegradationKind.BLUR,
                         value=float(lap.var() / ctx.dn_max ** 2), unit="dimensionless", reduction="luminance",
                         threshold_basis=METRIC_BASIS["blur_laplacian_variance"],
                         sample_fraction=ctx.sample_fraction, detector_version="blur@1",
                         notes="advisory only: scene-content dependent, no calibration on our imagery")


def _m_stripe(ctx: _Ctx) -> QualityMetric:
    scores = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # all-nodata rows/columns -> NaN means
        for t, v in ctx.tiles:
            luma = np.where(v, _luma(t), np.nan)
            total = np.nanvar(luma)
            if not np.isfinite(total) or total == 0:
                scores.append(0.0)                               # a flat tile has no stripes: measured, not assumed
                continue
            col = np.nanvar(np.nanmean(luma, axis=0))
            row = np.nanvar(np.nanmean(luma, axis=1))
            scores.append(float(max(col, row) / total))
    return QualityMetric(name="stripe_score", kind=DegradationKind.STRIPING, value=max(scores),
                         unit="dimensionless", reduction="max_over_tiles_of_max_row_col",
                         threshold_basis=METRIC_BASIS["stripe_score"], sample_fraction=ctx.sample_fraction,
                         detector_version="stripe@1", notes="advisory only: period is sensor-specific, not calibrated")


def _m_gsd(ctx: _Ctx) -> QualityMetric:
    """Read, never estimated. Degrees are refused rather than converted, as in Q-063."""
    res, crs = ctx.meta.resolution, ctx.meta.crs
    na = lambda reason: _not_applicable(ctx, "gsd_m", DegradationKind.LOW_RESOLUTION, "m", "gsd@1", reason)
    if not res or not crs:
        return na("raster carries no georeferenced ground sample distance; GSD was not estimated")
    import pyproj
    c = pyproj.CRS.from_user_input(crs)
    unit = (c.axis_info[0].unit_name if c.axis_info else "").lower()
    if not c.is_projected or unit not in ("metre", "meter", "m"):
        return na(f"CRS {crs} is not a projected metre CRS; resolution {res[0]} is not metres")
    return QualityMetric(name="gsd_m", kind=DegradationKind.LOW_RESOLUTION, value=float(abs(res[0])), unit="m",
                         threshold=ctx.cfg.sr_recommend_gsd_m, threshold_basis=METRIC_BASIS["gsd_m"],
                         detector_version="gsd@1", notes="read from RasterMetadata.resolution; not estimated")
```

Replace `_DETECTORS` with:

```python
_DETECTORS: List[_Detector] = [
    _Detector("nodata_fraction", DegradationKind.MISSING_DATA, "fraction", "nodata@1", _m_nodata),
    _Detector("impulse_density", DegradationKind.IMPULSE_NOISE, "fraction", "impulse@1", _m_impulse),
    _Detector("saturation_high", DegradationKind.SATURATION_CLIPPING, "fraction", "saturation@1", _m_saturation_high),
    _Detector("saturation_low", DegradationKind.SATURATION_CLIPPING, "fraction", "saturation@1", _m_saturation_low),
    _Detector("dynamic_range_p2_p98", DegradationKind.LOW_DYNAMIC_RANGE, "dimensionless", "dynrange@1", _m_dynamic_range),
    _Detector("black_level_dn", DegradationKind.BRIGHTNESS_BIAS, "dn", "blacklevel@1", _m_black_level),
    _Detector("grey_world_gain", DegradationKind.COLOR_CAST, "dimensionless", "greyworld@1", _m_grey_world),
    _Detector("gaussian_noise_sigma_dn", DegradationKind.GAUSSIAN_NOISE, "dn", "gnoise@1", _m_gaussian_noise),
    _Detector("blur_laplacian_variance", DegradationKind.BLUR, "dimensionless", "blur@1", _m_blur),
    _Detector("stripe_score", DegradationKind.STRIPING, "dimensionless", "stripe@1", _m_stripe),
    _Detector("gsd_m", DegradationKind.LOW_RESOLUTION, "m", "gsd@1", _m_gsd),
]
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_detectors.py -v`
Expected: 21 passed. Record the measured `s_noisy` for σ=20 in the Q-065 entry (Task 10). It is the
estimator's bias on this fixture, and it must be reported as that and nothing more.

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/detectors.py tests/unit/test_restoration_detectors.py
git commit -m "feat(restoration): saturation, dynamic range, grey-world, noise, blur, stripe and GSD detectors"
```

---

### Task 6: Planner — decision table `dt@1`

**Files:**
- Create: `backend/app/restoration/planner.py`
- Test: `tests/unit/test_restoration_planner.py`

**Interfaces:**
- Consumes: `METRIC_BASIS`, `impulse_params` (Task 4); `STAGE_ORDER` (Task 3); `WorkflowError` (`backend/app/exceptions.py:145`).
- Produces:
  - `DecisionRow(row: int, metric: str, stage_id: str, term: Optional[str] = None)`
  - `DECISION_TABLE`, `DECISION_TABLE_VERSION = "dt@1"`
  - `validate_table(table, basis) -> None` (raises `WorkflowError`; it also runs at import)
  - `plan(assessment, cfg, *, plan_id=None) -> RestorationPlan`
  - `photometric_correct` params: `{"terms": [...], "black_level_percentile", "stretch_low_percentile", "stretch_high_percentile", "gamma"}`, where `terms` is `["offset"] + gain? + stretch?` in chain order
  - `impulse_denoise` params: `{"window": 3, "dev_dn", "extreme_tol_dn", "max_similar_neighbours"}`

Temporal-pair joint fitting (spec §4.4) is **not** here. It belongs to Plan 2, where pairs exist.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_planner.py
import pytest

from backend.app.config import RestorationSettings
from backend.app.exceptions import WorkflowError
from backend.app.restoration import detectors
from backend.app.restoration.planner import DecisionRow, plan, validate_table
from backend.app.restoration.schemas import QualityAssessment, QualityMetric, QualityVerdict, ThresholdBasis

CFG = RestorationSettings()
_KIND = {d.name: d.kind for d in detectors._DETECTORS}


def _m(name, value, threshold=None, direction="above", basis=None):
    return QualityMetric(name=name, kind=_KIND[name], value=value, unit="x", threshold=threshold,
                         direction=direction, threshold_basis=basis or detectors.METRIC_BASIS[name],
                         detector_version="t@1")


def _qa(*metrics, verdict=QualityVerdict.CLEAN):
    return QualityAssessment(assessment_id="qa_t_0", image_index=0, image_path="p", width=8, height=8, bands=3,
                             dtype="uint8", dn_max=255.0, valid_pixel_count=64, total_pixel_count=64,
                             metrics=list(metrics), verdict=verdict, detector_config_hash="0" * 16)


CLEAN = [_m("impulse_density", 0.0, 0.001), _m("dynamic_range_p2_p98", 0.6, 0.30, "below"),
         _m("grey_world_gain", 1.02, 1.15), _m("gaussian_noise_sigma_dn", 1.0, 10.2),
         _m("saturation_high", 0.0, 0.02), _m("blur_laplacian_variance", 0.0004),
         _m("stripe_score", 0.01)]


def _ids(p):
    return [s.stage_id for s in p.stages]


def test_all_clean_is_noop():
    p = plan(_qa(*CLEAN), CFG)
    assert p.is_noop and p.stages == [] and "impulse_density" in p.rationale


def test_row2_impulse_only():
    p = plan(_qa(_m("impulse_density", 0.02, 0.001), *CLEAN[1:]), CFG)
    assert _ids(p) == ["impulse_denoise"]
    s = p.stages[0]
    assert s.order == 20 and s.threshold_basis is ThresholdBasis.PROVISIONAL and s.triggered_by == ["impulse_density"]
    assert s.params["window"] == 3 and s.params["dev_dn"] == pytest.approx(40.0)
    assert s.params["max_similar_neighbours"] == 1


def test_rows_6_7_fuse_into_one_photometric_stage_after_impulse():
    p = plan(_qa(_m("impulse_density", 0.02, 0.001), _m("dynamic_range_p2_p98", 0.21, 0.30, "below"),
                 _m("grey_world_gain", 1.4, 1.15)), CFG)
    assert _ids(p) == ["impulse_denoise", "photometric_correct"]
    photo = p.stages[1]
    assert photo.fused and photo.order == 50
    assert photo.params["terms"] == ["offset", "gain", "stretch"]
    assert photo.triggered_by == ["dynamic_range_p2_p98", "grey_world_gain"]


def test_row3_gaussian_and_row10_super_resolve_are_planned():
    p = plan(_qa(_m("gaussian_noise_sigma_dn", 20.0, 10.2), _m("gsd_m", 10.0, 2.0)), CFG)
    assert _ids(p) == ["gaussian_denoise", "super_resolve"]


@pytest.mark.parametrize("metric", [_m("saturation_high", 0.2, 0.02), _m("nodata_fraction", 0.6, 0.5)])
def test_rows_8_and_11_produce_no_stage(metric):
    assert plan(_qa(metric, verdict=QualityVerdict.DEGRADED), CFG).stages == []


def test_not_calibrated_advisories_produce_no_stage():
    assert plan(_qa(_m("blur_laplacian_variance", 1e-9), _m("stripe_score", 0.9)), CFG).stages == []


def test_table_row_on_not_calibrated_metric_raises():
    with pytest.raises(WorkflowError, match="NOT_CALIBRATED"):
        validate_table((DecisionRow(99, "stripe_score", "destripe"),), detectors.METRIC_BASIS)


def test_runtime_gate_on_not_calibrated_metric_raises():
    rogue = _m("impulse_density", 0.02, 0.001, basis=ThresholdBasis.NOT_CALIBRATED)
    with pytest.raises(WorkflowError, match="NOT_CALIBRATED"):
        plan(_qa(rogue), CFG)


def test_unassessable_is_noop():
    p = plan(_qa(_m("impulse_density", 0.02, 0.001), verdict=QualityVerdict.UNASSESSABLE), CFG)
    assert p.is_noop and p.stages == []
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_planner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration.planner'`

- [ ] **Step 3: Implement**

```python
# backend/app/restoration/planner.py
"""
Planner (spec §4): a pure function of one QualityAssessment and the config. No I/O, no arrays, which
is what makes every row of the decision table testable on hand-built assessments.

Rows 4, 8, 9 and 11 of spec §4.2 deliberately produce no stage. They are measurable and unfixable
(saturation is irreversible), and the executor reports them as residual degradations or warnings.
Row 1 (mask_invalid) is not a stage (plan D4). Row 5 (black level) is a parameter (plan D3).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from backend.app.config import RestorationSettings
from backend.app.exceptions import WorkflowError
from backend.app.restoration.detectors import METRIC_BASIS, impulse_params
from backend.app.restoration.registry import STAGE_ORDER
from backend.app.restoration.schemas import (
    DetectorStatus, PlannedStage, QualityAssessment, QualityMetric, QualityVerdict, RestorationPlan,
    ThresholdBasis,
)


@dataclass(frozen=True)
class DecisionRow:
    row: int                     # spec §4.2 row number
    metric: str
    stage_id: str
    term: Optional[str] = None   # the photometric_correct term this row contributes


DECISION_TABLE_VERSION = "dt@1"
DECISION_TABLE: Tuple[DecisionRow, ...] = (
    DecisionRow(2, "impulse_density", "impulse_denoise"),
    DecisionRow(3, "gaussian_noise_sigma_dn", "gaussian_denoise"),
    DecisionRow(6, "dynamic_range_p2_p98", "photometric_correct", "stretch"),
    DecisionRow(7, "grey_world_gain", "photometric_correct", "gain"),
    DecisionRow(10, "gsd_m", "super_resolve"),
)


def validate_table(table: Iterable[DecisionRow], basis: Mapping[str, ThresholdBasis]) -> None:
    """Spec §3.4: a stage may only be gated by a PRINCIPLED or PROVISIONAL metric. Loud, at import."""
    for r in table:
        if r.metric not in basis:
            raise WorkflowError(f"decision row {r.row} references unknown metric '{r.metric}'")
        if basis[r.metric] is ThresholdBasis.NOT_CALIBRATED:
            raise WorkflowError(f"decision row {r.row} gates '{r.stage_id}' on NOT_CALIBRATED metric "
                                f"'{r.metric}' (spec §3.4)")
        if r.stage_id not in STAGE_ORDER:
            raise WorkflowError(f"decision row {r.row} names unknown stage '{r.stage_id}'")


validate_table(DECISION_TABLE, METRIC_BASIS)


def _params(stage_id: str, terms: List[str], qa: QualityAssessment, cfg: RestorationSettings) -> Dict[str, Any]:
    if stage_id == "impulse_denoise":
        return {"window": 3, **impulse_params(qa.dn_max, cfg)}
    if stage_id == "photometric_correct":
        return {"terms": ["offset"] + [t for t in ("gain", "stretch") if t in terms],
                "black_level_percentile": cfg.black_level_percentile,
                "stretch_low_percentile": cfg.stretch_low_percentile,
                "stretch_high_percentile": cfg.stretch_high_percentile,
                "gamma": cfg.gamma}
    return {}


def _describe(m: QualityMetric) -> str:
    op = "<" if m.direction == "below" else ">="
    return f"{m.name} {m.value:.4g} {op} {m.threshold:.4g} ({m.threshold_basis.value})"


def plan(assessment: QualityAssessment, cfg: RestorationSettings, *, plan_id: Optional[str] = None) -> RestorationPlan:
    pid = plan_id or f"plan_{assessment.assessment_id}"
    if assessment.verdict is QualityVerdict.UNASSESSABLE:
        return RestorationPlan(plan_id=pid, image_index=assessment.image_index, is_noop=True,
                               rationale="Quality could not be assessed; the image is left unchanged.",
                               decision_table_version=DECISION_TABLE_VERSION)

    fired: Dict[str, List[Tuple[DecisionRow, QualityMetric]]] = {}
    for r in DECISION_TABLE:
        m = assessment.metric(r.metric)
        if m is None or m.status is not DetectorStatus.MEASURED or not m.exceeds_threshold:
            continue
        if m.threshold_basis is ThresholdBasis.NOT_CALIBRATED:
            raise WorkflowError(f"metric '{m.name}' is NOT_CALIBRATED and cannot gate '{r.stage_id}' (spec §3.4)")
        fired.setdefault(r.stage_id, []).append((r, m))

    stages = []
    for sid, hits in fired.items():
        bases = {m.threshold_basis for _, m in hits}
        stages.append(PlannedStage(
            stage_id=sid, order=STAGE_ORDER[sid],
            params=_params(sid, [r.term for r, _ in hits if r.term], assessment, cfg),
            triggered_by=[m.name for _, m in hits],
            threshold_basis=ThresholdBasis.PROVISIONAL if ThresholdBasis.PROVISIONAL in bases else ThresholdBasis.PRINCIPLED,
            fused=sid == "photometric_correct"))
    stages.sort(key=lambda s: s.order)

    if not stages:
        checked = ", ".join(f"{m.name}={m.value:.4g}" for m in assessment.metrics
                            if m.gate_eligible and m.value is not None)
        rationale = f"No correction gate fired; checked {checked or 'no gate-eligible metric'}."
    else:
        rationale = "; ".join(f"{_describe(m)} -> {sid}" for sid, hits in fired.items() for _, m in hits) + "."
    return RestorationPlan(plan_id=pid, image_index=assessment.image_index, stages=stages, is_noop=not stages,
                           rationale=rationale, decision_table_version=DECISION_TABLE_VERSION)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_planner.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/planner.py tests/unit/test_restoration_planner.py
git commit -m "feat(restoration): decision-table planner that refuses NOT_CALIBRATED gates"
```

---

### Task 7: The fused photometric pass (`photometric_correct`)

**Files:**
- Create: `backend/app/restoration/correction.py`
- Modify: `backend/app/restoration/stages.py` (append one import)
- Test: `tests/unit/test_restoration_fused.py`

**Interfaces:**
- Consumes: `register_stage`, `delta_stats` (Task 3); `StageReceipt`, `StageStatus` (Task 2); planner params (Task 6).
- Produces:
  - `fit_photometric(arr, valid, dn_max, params) -> Dict` with keys `terms, dn_max, black_level[], gain[], stretch_lo[], stretch_hi[], gamma, warnings[]` (all plain floats, JSON-safe)
  - `transfer(x: float64 array, b: int, fit) -> float64 array` (the scalar `f_b`)
  - `build_lut(fit, b, dtype) -> np.ndarray` (unsigned integer dtypes only)
  - `apply_fused(arr, valid, fit, strip_rows=512) -> (out, "lut" | "analytic")`
  - stage `photometric_correct` (order 50, version `fused_lut@1`, `fusable=True`). Its receipt
    `params` hold everything `apply_fused` needs, so the output can be reproduced from the receipt alone.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_fused.py
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.app.config import RestorationSettings
from backend.app.restoration.correction import apply_fused, fit_photometric
from backend.app.restoration.registry import get_stage
from backend.app.restoration.detectors import assess
from backend.app.restoration.schemas import StageStatus
from tests.unit.restoration_fixtures import meta_for, smooth_image

ALL_TERMS = {"terms": ["offset", "gain", "stretch"], "black_level_percentile": 0.5,
             "stretch_low_percentile": 2.0, "stretch_high_percentile": 98.0, "gamma": 1.0}


def _naive(arr, valid, fit):
    """Independent step-by-step chain in float64, quantised once (plan D7)."""
    dn_max = fit["dn_max"]
    out = arr.astype(np.float64).copy()
    for b in range(arr.shape[0]):
        y = out[b] - fit["black_level"][b]
        y = y * fit["gain"][b]
        y = (y - fit["stretch_lo"][b]) / (fit["stretch_hi"][b] - fit["stretch_lo"][b]) * dn_max
        y = np.clip(y, 0, dn_max)
        if fit["gamma"] != 1.0:
            y = dn_max * (y / dn_max) ** (1.0 / fit["gamma"])
        out[b] = y
    q = np.round(out).astype(arr.dtype) if np.issubdtype(arr.dtype, np.integer) else out.astype(arr.dtype)
    return np.where(valid, q, arr)


def _fit(dn_max, bands=3):
    return {"terms": ["offset", "gain", "stretch"], "dn_max": dn_max, "black_level": [7.3] * bands,
            "gain": [1.1, 0.95, 1.0][:bands], "stretch_lo": [20.0 * dn_max / 255] * bands,
            "stretch_hi": [180.0 * dn_max / 255] * bands, "gamma": 1.2}


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16])
def test_fused_equals_naive_chain_within_1dn(dtype):
    rng = np.random.default_rng(0)
    dn_max = float(np.iinfo(dtype).max)
    arr = rng.integers(0, int(dn_max) + 1, size=(3, 64, 64), dtype=dtype)
    valid = np.ones((64, 64), bool)
    fused, kind = apply_fused(arr, valid, _fit(dn_max))
    assert kind == "lut"
    assert np.abs(fused.astype(np.int64) - _naive(arr, valid, _fit(dn_max)).astype(np.int64)).max() <= 1


def test_fused_equals_naive_on_real_sample():
    arr = np.transpose(np.array(Image.open(Path("tests/data/sample_t1.png")).convert("RGB")), (2, 0, 1)).copy()
    valid = np.ones(arr.shape[1:], bool)
    fit = fit_photometric(arr, valid, 255.0, ALL_TERMS)
    fused, _ = apply_fused(arr, valid, fit)
    assert np.abs(fused.astype(int) - _naive(arr, valid, fit).astype(int)).max() <= 1


def test_tiled_equals_whole_exactly():
    arr = smooth_image(100, 90)
    valid = np.ones((100, 90), bool)
    fit = fit_photometric(arr, valid, 255.0, ALL_TERMS)
    assert np.array_equal(apply_fused(arr, valid, fit, strip_rows=7)[0], apply_fused(arr, valid, fit, strip_rows=10**6)[0])


def test_invariants_and_nodata_bit_identical():
    arr = smooth_image(64, 64, lo=100, hi=150)
    valid = np.ones((64, 64), bool)
    valid[:10, :10] = False
    arr[:, :10, :10] = 0
    fit = fit_photometric(arr, valid, 255.0, ALL_TERMS)
    out, _ = apply_fused(arr, valid, fit)
    assert out.dtype == arr.dtype and out.shape == arr.shape
    assert np.array_equal(out[:, ~valid], arr[:, ~valid])


def _qa(arr):
    return assess(arr, meta_for(arr), RestorationSettings(), job_id="t", image_index=0, image_path="p")


def test_stage_stretches_low_contrast_and_receipt_reproduces_output():
    arr = smooth_image(128, 128, lo=100, hi=150)
    valid = np.ones((128, 128), bool)
    out, receipt = get_stage("photometric_correct").fn(arr, valid, _qa(arr), ALL_TERMS)
    assert receipt.status is StageStatus.APPLIED and receipt.fused
    assert receipt.params["transfer"] == "lut" and receipt.params["lut_entries"] == 256
    lo, hi = np.percentile(out[0], [2, 98])
    assert (hi - lo) / 255 > 0.9
    assert receipt.fraction_modified > 0.5
    again, _ = apply_fused(arr, valid, receipt.params)
    assert np.array_equal(again, out)                         # reproducible from the receipt alone


def test_float_raster_takes_the_analytic_branch():
    arr = (smooth_image(64, 64, lo=100, hi=150).astype(np.float32) / 255.0)
    out, receipt = get_stage("photometric_correct").fn(arr, np.ones((64, 64), bool), _qa(arr), ALL_TERMS)
    assert out.dtype == np.float32
    assert receipt.params["transfer"] == "analytic" and receipt.params["lut_entries"] == 0


def test_constant_band_stretch_is_skipped_with_a_warning():
    arr = np.full((3, 16, 16), 90, np.uint8)
    fit = fit_photometric(arr, np.ones((16, 16), bool), 255.0, ALL_TERMS)
    assert fit["stretch_lo"] == [0.0] * 3 and fit["stretch_hi"] == [255.0] * 3
    assert any("constant" in w for w in fit["warnings"])
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_fused.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration.correction'`

- [ ] **Step 3: Implement**

```python
# backend/app/restoration/correction.py
"""
The fused single-pass photometric correction (spec §5).

Per band, offset -> gain -> stretch -> gamma -> clip is pointwise and spatially invariant, so it is
one scalar function f_b. On an unsigned integer dtype, f_b is a lookup table of dn_max + 1 entries
(256 for uint8) and applying it is one np.take per pixel. Grey-world gains are a diagonal matrix,
so they fold into the same table (plan D9). Floats and signed ints have no finite non-negative
domain, so f_b is evaluated analytically per pixel instead.

Fitting happens on the array this stage receives, i.e. AFTER impulse_denoise. Salt-and-pepper sits
exactly on the percentiles the stretch is fitted on (spec §4.1 point 2).
"""
from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import numpy as np

from backend.app.restoration.registry import delta_stats, register_stage
from backend.app.restoration.schemas import StageReceipt, StageStatus

_FIT_BUDGET_PX = 4_000_000


def fit_photometric(arr: np.ndarray, valid: np.ndarray, dn_max: float, params: Dict[str, Any]) -> Dict[str, Any]:
    terms = list(params["terms"])
    bands = arr.shape[0]
    step = max(1, int(np.ceil(np.sqrt(int(valid.sum()) / _FIT_BUDGET_PX))))   # strided sample for huge rasters
    sub, sub_valid = arr[:, ::step, ::step], valid[::step, ::step]
    y = [sub[b][sub_valid].astype(np.float64) for b in range(bands)]
    warnings = []

    black = [float(np.percentile(y[b], params["black_level_percentile"])) if "offset" in terms else 0.0
             for b in range(bands)]
    y = [y[b] - black[b] for b in range(bands)]

    gain = [1.0] * bands
    if "gain" in terms and bands >= 3:
        means = [float(y[b].mean()) for b in range(3)]
        if min(means) > 0:
            target = sum(means) / 3
            gain[:3] = [target / m for m in means]
        else:
            warnings.append(f"grey-world gain skipped: a band mean after offset is not positive ({means})")
    y = [y[b] * gain[b] for b in range(bands)]

    lo, hi = [0.0] * bands, [float(dn_max)] * bands
    if "stretch" in terms:
        for b in range(bands):
            p_lo, p_hi = np.percentile(y[b], [params["stretch_low_percentile"], params["stretch_high_percentile"]])
            if p_hi - p_lo > 0:
                lo[b], hi[b] = float(p_lo), float(p_hi)
            else:
                warnings.append(f"band {b} is constant over p{params['stretch_low_percentile']}-"
                                f"p{params['stretch_high_percentile']}; its stretch was skipped")
    return {"terms": terms, "dn_max": float(dn_max), "black_level": black, "gain": gain,
            "stretch_lo": lo, "stretch_hi": hi, "gamma": float(params["gamma"]), "warnings": warnings}


def transfer(x: np.ndarray, b: int, fit: Dict[str, Any]) -> np.ndarray:
    """f_b over float64 input, in native DN."""
    dn_max = fit["dn_max"]
    y = (x - fit["black_level"][b]) * fit["gain"][b]
    y = (y - fit["stretch_lo"][b]) / (fit["stretch_hi"][b] - fit["stretch_lo"][b]) * dn_max
    y = np.clip(y, 0.0, dn_max)
    if fit["gamma"] != 1.0:
        y = dn_max * (y / dn_max) ** (1.0 / fit["gamma"])
    return y


def _quantise(y: np.ndarray, dtype: np.dtype) -> np.ndarray:
    return np.round(y).astype(dtype) if np.issubdtype(dtype, np.integer) else y.astype(dtype)


def build_lut(fit: Dict[str, Any], b: int, dtype: np.dtype) -> np.ndarray:
    n = int(np.iinfo(dtype).max) + 1
    return _quantise(transfer(np.arange(n, dtype=np.float64), b, fit), dtype)


def apply_fused(arr: np.ndarray, valid: np.ndarray, fit: Dict[str, Any], strip_rows: int = 512) -> Tuple[np.ndarray, str]:
    """One pass over the pixels, in row strips (plan D8). Invalid pixels are copied through untouched."""
    use_lut = np.issubdtype(arr.dtype, np.unsignedinteger)
    luts = [build_lut(fit, b, arr.dtype) for b in range(arr.shape[0])] if use_lut else None
    out = arr.copy()
    for b in range(arr.shape[0]):
        for y0 in range(0, arr.shape[1], strip_rows):
            src, v = arr[b, y0:y0 + strip_rows], valid[y0:y0 + strip_rows]
            new = np.take(luts[b], src) if use_lut else _quantise(transfer(src.astype(np.float64), b, fit), arr.dtype)
            out[b, y0:y0 + strip_rows] = np.where(v, new, src)
    return out, "lut" if use_lut else "analytic"


@register_stage("photometric_correct", order=50, version="fused_lut@1", fusable=True)
def photometric_correct(arr, valid_mask, assessment, params):
    t0 = time.perf_counter()
    fit = fit_photometric(arr, valid_mask, assessment.dn_max, params)
    out, kind = apply_fused(arr, valid_mask, fit)
    recorded = {k: v for k, v in fit.items() if k != "warnings"}
    recorded.update(transfer=kind, lut_entries=int(np.iinfo(arr.dtype).max) + 1 if kind == "lut" else 0)
    return out, StageReceipt(
        stage_id="photometric_correct", stage_version="fused_lut@1", status=StageStatus.APPLIED, order=50,
        params=recorded, fused=True, warnings=fit["warnings"], **delta_stats(arr, out, valid_mask),
        duration_ms=(time.perf_counter() - t0) * 1000)
```

Append to `backend/app/restoration/stages.py`:

```python
from backend.app.restoration import correction  # noqa: E402,F401  (registers photometric_correct)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_fused.py tests/unit/test_restoration_stage_registry.py -v`
Expected: all pass (8 + 8)

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/correction.py backend/app/restoration/stages.py tests/unit/test_restoration_fused.py
git commit -m "feat(restoration): fused single-pass LUT photometric correction"
```

---

### Task 8: Switching median (`impulse_denoise`) — owner: Ayushman

Ayushman owns this task (`split-ushnik-ayushman.md`, Ayushman #3). It needs nothing from other tasks
except the registry (Task 3) and `impulse_candidates` (Task 4). If he takes it, Tasks 9–10 can use a
temporary branch in which it is absent: `execute_plan` then records `impulse_denoise` as
`NOT_CONFIGURED` ("no stage registered"), and that path is tested in Task 9.

**Files:**
- Create: `backend/app/restoration/impulse.py`
- Modify: `backend/app/restoration/stages.py` (append one import)
- Test: `tests/unit/test_restoration_impulse.py`

**Interfaces:**
- Consumes: `impulse_candidates` (Task 4), `register_stage`, `delta_stats`, `not_configured` (Task 3),
  params from the planner (`window`, `dev_dn`, `extreme_tol_dn`, `max_similar_neighbours`).
- Produces: stage `impulse_denoise` (order 20, version `switching_median@1`). Only candidate pixels
  change. Each one is replaced by the 3×3 median of its band.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_impulse.py
import numpy as np
import pytest

from backend.app.config import RestorationSettings
from backend.app.restoration.detectors import assess
from backend.app.restoration.registry import get_stage
from backend.app.restoration.schemas import StageStatus
from tests.unit.restoration_fixtures import bright_lines, inject_salt_pepper, meta_for, smooth_image

PARAMS = {"window": 3, "dev_dn": 40.0, "extreme_tol_dn": 2.0, "max_similar_neighbours": 1}
CFG = RestorationSettings()


def _run(arr, valid=None, params=PARAMS, nodata=None):
    valid = np.ones(arr.shape[1:], bool) if valid is None else valid
    qa = assess(arr, meta_for(arr, nodata=nodata), CFG, job_id="t", image_index=0, image_path="p")
    return get_stage("impulse_denoise").fn(arr, valid, qa, params)


def test_removes_salt_and_pepper():
    clean = smooth_image(256, 256)
    noisy, where = inject_salt_pepper(clean, 0.01)
    out, receipt = _run(noisy)
    err_before = np.abs(noisy.astype(int) - clean).mean()
    err_after = np.abs(out.astype(int) - clean).mean()
    assert err_after < 0.1 * err_before
    assert receipt.status is StageStatus.APPLIED
    assert receipt.fraction_modified == pytest.approx(0.01, rel=0.15)


def test_only_candidates_change():
    noisy, where = inject_salt_pepper(smooth_image(128, 128), 0.02)
    out, _ = _run(noisy)
    changed = np.any(out != noisy, axis=0)
    assert not (changed & ~where).any()


def test_leaves_one_pixel_roads_alone():
    img = bright_lines()
    out, receipt = _run(img)
    assert receipt.fraction_modified < 0.0005


def test_nodata_bit_identical_and_dtype_preserved():
    img = smooth_image(128, 128)
    img[:, :, :32] = 0
    valid = np.ones((128, 128), bool)
    valid[:, :32] = False
    right = ~np.zeros((128, 128), bool)
    right[:, :32] = False
    noisy, _ = inject_salt_pepper(img, 0.02, salt_only=True, region=right)
    out, _ = _run(noisy, valid=valid, nodata=0)
    assert out.dtype == noisy.dtype and out.shape == noisy.shape
    assert np.array_equal(out[:, ~valid], noisy[:, ~valid])


def test_uint16_scaled():
    clean = smooth_image(128, 128, lo=60 * 257, hi=190 * 257, dtype=np.uint16)
    noisy, _ = inject_salt_pepper(clean, 0.01)
    params = {**PARAMS, "dev_dn": 40.0 * 257, "extreme_tol_dn": 2.0 * 257}
    out, receipt = _run(noisy, params=params)
    assert np.abs(out.astype(np.int64) - clean).mean() < 0.1 * np.abs(noisy.astype(np.int64) - clean).mean()


def test_too_small_raster_is_not_configured_and_untouched():
    arr = np.zeros((1, 2, 2), np.uint8)
    out, receipt = get_stage("impulse_denoise").fn(arr, np.ones((2, 2), bool), None, PARAMS)
    assert out is arr and receipt.status is StageStatus.NOT_CONFIGURED and "3x3" in receipt.reason
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_impulse.py -v`
Expected: FAIL. `get_stage("impulse_denoise")` returns `None`, so the tests error with `AttributeError: 'NoneType' object has no attribute 'fn'`.

- [ ] **Step 3: Implement**

```python
# backend/app/restoration/impulse.py
"""
Switching median for salt-and-pepper (spec §3.1, §4.1 order 20). Owner: Ayushman.

"Switching": only pixels that impulse_candidates() flags are replaced; every other pixel is returned
bit-identical. That is what keeps a median from blurring 1-px roads and field boundaries. The detector
and this stage call the SAME candidate function, so what was measured is exactly what is corrected.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import ndimage

from backend.app.restoration.detectors import impulse_candidates
from backend.app.restoration.registry import delta_stats, not_configured, register_stage
from backend.app.restoration.schemas import StageReceipt, StageStatus, ThresholdBasis

_VERSION = "switching_median@1"


@register_stage("impulse_denoise", order=20, version=_VERSION)
def impulse_denoise(arr, valid_mask, assessment, params):
    t0 = time.perf_counter()
    if params.get("window", 3) != 3:
        return arr, not_configured("impulse_denoise", _VERSION, 20,
                                   f"only a 3x3 window is implemented; plan asked for {params['window']}", params)
    if arr.shape[1] < 3 or arr.shape[2] < 3:
        return arr, not_configured("impulse_denoise", _VERSION, 20,
                                   f"raster {arr.shape[2]}x{arr.shape[1]} is smaller than the 3x3 window", params)
    if not np.issubdtype(arr.dtype, np.integer):
        return arr, not_configured("impulse_denoise", _VERSION, 20,
                                   f"dtype {arr.dtype} is not supported; salt-and-pepper is an integer-DN defect",
                                   params)

    dn_max = float(np.iinfo(arr.dtype).max)
    out = arr.copy()
    for b in range(arr.shape[0]):
        cand = impulse_candidates(arr[b], valid_mask, dn_max, dev_dn=params["dev_dn"],
                                  extreme_tol_dn=params["extreme_tol_dn"],
                                  max_similar_neighbours=params["max_similar_neighbours"])
        if not cand.any():
            continue
        x = arr[b].astype(np.float32)
        x[~valid_mask] = np.median(x[valid_mask])          # nodata never enters a median
        med = ndimage.median_filter(x, size=3, mode="nearest")
        out[b][cand] = np.round(med[cand]).astype(arr.dtype)

    return out, StageReceipt(
        stage_id="impulse_denoise", stage_version=_VERSION, status=StageStatus.APPLIED, order=20,
        params=dict(params), triggered_by=["impulse_density"], threshold_basis=ThresholdBasis.PROVISIONAL,
        **delta_stats(arr, out, valid_mask), duration_ms=(time.perf_counter() - t0) * 1000)
```

Append to `backend/app/restoration/stages.py`:

```python
from backend.app.restoration import impulse  # noqa: E402,F401  (registers impulse_denoise)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_impulse.py tests/unit/test_restoration_stage_registry.py -v`
Expected: all pass (6 + 8)

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/impulse.py backend/app/restoration/stages.py tests/unit/test_restoration_impulse.py
git commit -m "feat(restoration): switching-median impulse_denoise stage"
```

---

### Task 9: Executor and receipt builder

**Files:**
- Create: `backend/app/restoration/executor.py`
- Test: `tests/unit/test_restoration_executor.py`

**Interfaces:**
- Consumes: every earlier task.
- Produces (this is the whole surface Plan 2's tools call):
  - `execute_plan(arr, valid, assessment, plan) -> (out: np.ndarray, receipts: List[StageReceipt])`.
    It runs the stages in `order` and feeds each stage the previous stage's output. It never raises:
    an exception, a shape or dtype change, or a nodata write turns into a `FAILED` receipt, and the
    stage's output is discarded. An unregistered stage id becomes `NOT_CONFIGURED`.
  - `build_receipt(*, job_id, assessments, plans, stages, inputs, cfg, receipt_id=None, total_duration_ms=0.0) -> RestorationReceipt`
  - `STAGE_ADDRESSES: Dict[str, FrozenSet[DegradationKind]]`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_restoration_executor.py
import numpy as np
import pytest

from backend.app.config import RestorationSettings
from backend.app.restoration.detectors import assess, build_valid_mask
from backend.app.restoration.executor import build_receipt, execute_plan
from backend.app.restoration.planner import plan
from backend.app.restoration.registry import STAGE_REGISTRY, StageSpec
from backend.app.restoration.schemas import (
    ConfidencePosture, DegradationKind, RestorationReceipt, RestorationStatus, RestoredInput, StageStatus,
)
from tests.unit.restoration_fixtures import inject_salt_pepper, meta_for, smooth_image

CFG = RestorationSettings()


def _grey(h=128, w=128, **kw):
    img = smooth_image(h, w, **kw)
    img[1] = img[0]
    img[2] = img[0]
    return img


def _pipeline(arr, meta=None):
    meta = meta or meta_for(arr)
    qa = assess(arr, meta, CFG, job_id="t", image_index=0, image_path="in.tif")
    p = plan(qa, CFG)
    out, stages = execute_plan(arr, build_valid_mask(arr, meta.nodata), qa, p)
    modified = any(s.status is StageStatus.APPLIED and s.fraction_modified > 0 for s in stages)
    inputs = [RestoredInput(image_index=0, original_path="in.tif",
                            consumed_path="in.restored.tif" if modified else "in.tif", was_modified=modified)]
    return out, build_receipt(job_id="t", assessments=[qa], plans=[p], stages=stages, inputs=inputs, cfg=CFG)


def _stage(r, sid):
    return next(s for s in r.stages if s.stage_id == sid)


def test_clean_image_is_untouched_but_fully_receipted():
    arr = _grey(lo=10, hi=245)
    out, r = _pipeline(arr)
    assert out is arr
    assert r.status is RestorationStatus.ASSESSED_NO_ACTION and r.input_modified is False and r.stages == []
    assert len(r.assessments) == 1 and r.plans[0].is_noop
    assert r.confidence_advice.posture is ConfidencePosture.NEUTRAL


def test_impulses_removed_before_the_stretch_is_fitted():
    noisy, _ = inject_salt_pepper(_grey(lo=100, hi=150), 0.02)   # 1% pepper, 1% salt: under the 2% saturation gate
    out, r = _pipeline(noisy)
    ids = [s.stage_id for s in r.stages]
    assert ids[:2] == ["impulse_denoise", "photometric_correct"]
    photo = _stage(r, "photometric_correct")
    assert photo.status is StageStatus.APPLIED
    assert photo.params["black_level"][0] > 50      # fitted on the de-impulsed image; 1% pepper would pin p0.5 at 0
    assert r.status is RestorationStatus.RESTORED and r.input_modified
    assert {"impulse_density", "dynamic_range_p2_p98"} <= set(r.provisional_gates_fired)
    assert r.confidence_advice.posture is ConfidencePosture.CAUTION
    assert r.confidence_advice.max_confidence_multiplier == 1.0
    assert any(w.startswith("Input image was corrected before analysis") for w in r.warnings)
    assert _stage(r, "impulse_denoise").input_sha256 != _stage(r, "impulse_denoise").output_sha256


def test_stage_exception_is_failed_and_pipeline_continues(monkeypatch):
    def boom(*a):
        raise RuntimeError("synthetic")
    monkeypatch.setitem(STAGE_REGISTRY, "photometric_correct",
                        StageSpec("photometric_correct", 50, "boom@1", True, boom))
    noisy, _ = inject_salt_pepper(_grey(lo=100, hi=150), 0.02)
    out, r = _pipeline(noisy)
    assert _stage(r, "photometric_correct").status is StageStatus.FAILED
    assert _stage(r, "impulse_denoise").status is StageStatus.APPLIED
    assert r.status is RestorationStatus.PARTIAL
    assert DegradationKind.LOW_DYNAMIC_RANGE in r.residual_degradations


def test_stage_that_writes_nodata_is_rejected(monkeypatch):
    def vandal(arr, valid, qa, params):
        out = arr.copy()
        out[:, ~valid] = 7
        return out, real.fn(arr, valid, qa, params)[1]     # the saved original, not the patched entry
    real = STAGE_REGISTRY["impulse_denoise"]
    monkeypatch.setitem(STAGE_REGISTRY, "impulse_denoise", StageSpec("impulse_denoise", 20, "vandal@1", False, vandal))
    img = _grey(lo=10, hi=245)
    img[:, :, :16] = 0
    right = np.ones((128, 128), bool)
    right[:, :16] = False
    noisy, _ = inject_salt_pepper(img, 0.02, salt_only=True, region=right)
    out, r = _pipeline(noisy, meta_for(noisy, nodata=0))
    s = _stage(r, "impulse_denoise")
    assert s.status is StageStatus.FAILED and "nodata" in s.reason
    assert out is noisy


def test_unregistered_stage_is_not_configured(monkeypatch):
    monkeypatch.delitem(STAGE_REGISTRY, "impulse_denoise")
    noisy, _ = inject_salt_pepper(_grey(lo=10, hi=245), 0.02)
    out, r = _pipeline(noisy)
    s = _stage(r, "impulse_denoise")
    assert s.status is StageStatus.NOT_CONFIGURED and "no stage is registered" in s.reason
    assert out is noisy and DegradationKind.IMPULSE_NOISE in r.residual_degradations


def test_coarse_gsd_plans_super_resolve_that_refuses():
    arr = _grey(lo=10, hi=245)
    meta = meta_for(arr, resolution=[10.0, 10.0]).model_copy(update={"crs": "EPSG:32614"})
    out, r = _pipeline(arr, meta)
    assert out is arr
    assert _stage(r, "super_resolve").status is StageStatus.NOT_CONFIGURED
    assert r.status is RestorationStatus.NOT_CONFIGURED and r.input_modified is False
    assert DegradationKind.LOW_RESOLUTION in r.residual_degradations
    assert any("NOT upscaled" in w for w in r.warnings)


def test_saturation_is_residual_with_no_stage():
    arr = _grey(lo=10, hi=245)
    arr[:, :20, :] = 255
    out, r = _pipeline(arr)
    assert DegradationKind.SATURATION_CLIPPING in r.residual_degradations
    assert all(s.stage_id != "saturation" for s in r.stages)
    assert any("no correction can recover" in w for w in r.warnings)
    assert r.confidence_advice.posture is ConfidencePosture.CAUTION


def test_unassessable_blocks_confidence():
    arr = np.zeros((3, 32, 32), np.uint8)
    out, r = _pipeline(arr, meta_for(arr, nodata=0))
    assert r.confidence_advice.blocking is True
    assert r.confidence_advice.posture is ConfidencePosture.DEGRADED


def test_receipt_is_json_safe_and_roundtrips():
    noisy, _ = inject_salt_pepper(_grey(lo=100, hi=150), 0.02)
    _, r = _pipeline(noisy)
    again = RestorationReceipt.model_validate_json(r.model_dump_json())
    assert again.model_dump(mode="json") == r.model_dump(mode="json")
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_executor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.restoration.executor'`

- [ ] **Step 3: Implement**

```python
# backend/app/restoration/executor.py
"""
Runs a RestorationPlan over an in-memory array and builds the RestorationReceipt (spec §2.8, §7.3, §8).

execute_plan never raises. A stage that throws, changes shape or dtype, or writes a nodata pixel is
recorded as FAILED and its output is discarded, so the next stage and the model see the last good
array. Restoration must never be the reason a job dies (spec §6.3).
"""
from __future__ import annotations

import hashlib
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np

from backend.app.config import RestorationSettings
from backend.app.logging import logger
from backend.app.restoration.detectors import METRIC_BASIS
from backend.app.restoration.planner import DECISION_TABLE_VERSION
from backend.app.restoration.registry import get_stage, not_configured
from backend.app.restoration.schemas import (
    ConfidenceAdvice, ConfidencePosture, DegradationKind, DetectorStatus, PlannedStage, QualityAssessment,
    QualityVerdict, RestorationPlan, RestorationReceipt, RestorationStatus, RestoredInput, StageReceipt,
    StageStatus, ThresholdBasis,
)

K = DegradationKind
#: Which detected degradations an APPLIED stage counts as having addressed.
STAGE_ADDRESSES: Dict[str, FrozenSet[DegradationKind]] = {
    "impulse_denoise": frozenset({K.IMPULSE_NOISE}),
    "gaussian_denoise": frozenset({K.GAUSSIAN_NOISE}),
    "destripe": frozenset({K.STRIPING}),
    "photometric_correct": frozenset({K.LOW_DYNAMIC_RANGE, K.COLOR_CAST, K.BRIGHTNESS_BIAS}),
    "super_resolve": frozenset({K.LOW_RESOLUTION}),
}


def _sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _violation(before: np.ndarray, after: object, valid: np.ndarray) -> Optional[str]:
    if not isinstance(after, np.ndarray):
        return "stage returned no array"
    if after.shape != before.shape:
        return f"stage changed shape {before.shape} -> {after.shape}"
    if after.dtype != before.dtype:
        return f"stage changed dtype {before.dtype} -> {after.dtype}"
    if not np.array_equal(after[:, ~valid], before[:, ~valid], equal_nan=True):
        return "stage modified nodata pixels, which must stay bit-identical (spec §2.1)"
    return None


def _failed(ps: PlannedStage, version: str, reason: str) -> StageReceipt:
    return StageReceipt(stage_id=ps.stage_id, stage_version=version, status=StageStatus.FAILED, reason=reason,
                        order=ps.order, params=ps.params, warnings=[f"{ps.stage_id} FAILED: {reason}"])


def execute_plan(arr: np.ndarray, valid: np.ndarray, assessment: QualityAssessment,
                 plan: RestorationPlan) -> Tuple[np.ndarray, List[StageReceipt]]:
    cur, receipts = arr, []
    for ps in sorted(plan.stages, key=lambda s: s.order):
        spec = get_stage(ps.stage_id)
        new = cur
        if spec is None:
            r = not_configured(ps.stage_id, "none@0", ps.order,
                               f"no stage is registered under '{ps.stage_id}'; the image was not changed by it",
                               ps.params)
        else:
            try:
                new, r = spec.fn(cur, valid, assessment, dict(ps.params))
                bad = _violation(cur, new, valid)
                if bad:
                    new, r = cur, _failed(ps, spec.version, bad)
            except Exception as e:
                logger.warning(f"restoration stage {ps.stage_id} failed: {e}")
                new, r = cur, _failed(ps, spec.version, f"{type(e).__name__}: {e}")
        r = r.model_copy(update={"triggered_by": ps.triggered_by, "threshold_basis": ps.threshold_basis,
                                 "fused": ps.fused or r.fused})
        if r.status is StageStatus.APPLIED:
            r = r.model_copy(update={"input_sha256": _sha(cur), "output_sha256": _sha(new)})
            cur = new
        receipts.append(r)
    return cur, receipts


def _status(stages: List[StageReceipt]) -> RestorationStatus:
    if not stages:
        return RestorationStatus.ASSESSED_NO_ACTION
    applied = any(s.status is StageStatus.APPLIED for s in stages)
    not_run = [s for s in stages if s.status in (StageStatus.NOT_CONFIGURED, StageStatus.FAILED)]
    if applied:
        return RestorationStatus.PARTIAL if not_run else RestorationStatus.RESTORED
    if not_run and all(s.status is StageStatus.FAILED for s in not_run):
        return RestorationStatus.FAILED
    return RestorationStatus.NOT_CONFIGURED


def _unique(items):
    seen = []
    for i in items:
        if i not in seen:
            seen.append(i)
    return seen


def build_receipt(*, job_id: str, assessments: List[QualityAssessment], plans: List[RestorationPlan],
                  stages: List[StageReceipt], inputs: List[RestoredInput], cfg: RestorationSettings,
                  receipt_id: Optional[str] = None, total_duration_ms: float = 0.0) -> RestorationReceipt:
    applied = [s for s in stages if s.status is StageStatus.APPLIED]
    changed_ids = _unique(s.stage_id for s in applied if (s.fraction_modified or 0.0) > 0.0)
    addressed = set().union(*(STAGE_ADDRESSES.get(s.stage_id, frozenset()) for s in applied))
    residual = _unique(k for qa in assessments for k in qa.degradations_detected if k not in addressed)
    unmeasured = _unique(m.kind for qa in assessments for m in qa.metrics
                         if m.status in (DetectorStatus.NOT_CONFIGURED, DetectorStatus.FAILED))
    provisional = sorted({name for p in plans for ps in p.stages for name in ps.triggered_by
                          if METRIC_BASIS.get(name) is ThresholdBasis.PROVISIONAL})

    warnings: List[str] = [w for qa in assessments for w in qa.warnings]
    for qa in assessments:
        nd = qa.metric("nodata_fraction")
        if nd is not None and nd.exceeds_threshold:
            warnings.append(f"{nd.value:.0%} of image {qa.image_index} is nodata; results cover the valid part only.")
    if K.SATURATION_CLIPPING in residual:
        warnings.append(f"At least {cfg.saturation_gate:.0%} of valid pixels are clipped at 0 or full scale; "
                        "clipped values are lost and no correction can recover them.")
    warnings += [w for s in stages for w in s.warnings]
    if changed_ids:
        warnings.append(f"Input image was corrected before analysis: {', '.join(changed_ids)}.")

    blocking = any(qa.verdict is QualityVerdict.UNASSESSABLE for qa in assessments)
    reasons = []
    if blocking:
        reasons.append("image quality could not be assessed (UNASSESSABLE); no confidence is computable")
    if changed_ids:
        reasons.append(f"the model saw a corrected image ({', '.join(changed_ids)})")
    if provisional:
        reasons.append(f"corrections were triggered by PROVISIONAL, uncalibrated thresholds: {', '.join(provisional)}")
    if residual:
        reasons.append(f"degradations measured and not corrected: {', '.join(k.value for k in residual)}")
    posture = (ConfidencePosture.DEGRADED if blocking
               else ConfidencePosture.CAUTION if reasons else ConfidencePosture.NEUTRAL)

    return RestorationReceipt(
        receipt_id=receipt_id or f"rst_{job_id}", job_id=job_id, status=_status(stages),
        input_modified=bool(changed_ids), assessments=assessments, plans=plans, stages=stages, inputs=inputs,
        residual_degradations=residual, unmeasured_degradations=unmeasured, provisional_gates_fired=provisional,
        confidence_advice=ConfidenceAdvice(posture=posture, max_confidence_multiplier=1.0, blocking=blocking,
                                           reasons=reasons),
        detector_config_hash=cfg.config_hash(), decision_table_version=DECISION_TABLE_VERSION,
        total_duration_ms=total_duration_ms, warnings=_unique(warnings))
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_restoration_executor.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/restoration/executor.py tests/unit/test_restoration_executor.py
git commit -m "feat(restoration): plan executor with contract checks, and the restoration receipt"
```

---

### Task 10: Full-suite gate and the transcript entry

**Files:**
- Modify: `project/qna.md` (append Q-065; never edit an earlier entry)

- [ ] **Step 1: Run the restoration tests together**

Run: `.venv/bin/python -m pytest tests/unit -k restoration -q`
Expected: every restoration test passes (2 + 13 + 8 + 21 + 10 + 8 + 6 + 9 = 77).

- [ ] **Step 2: Run the whole non-model suite**

Run: `.venv/bin/python -m pytest -m "not models" -q 2>&1 | tail -3`
Expected: **650 passed, 3 failed** (573 + 77; the 3 are the GDAL failures in
`test_geotiff_georeferencing.py`). Any other failure is a regression, so stop and report it
instead of writing the entry.

- [ ] **Step 3: Record the measured numbers the entry needs**

```bash
.venv/bin/python - <<'PY'
import numpy as np
from backend.app.config import RestorationSettings
from backend.app.restoration.detectors import assess
from tests.unit.restoration_fixtures import bright_lines, inject_salt_pepper, meta_for, smooth_image
cfg = RestorationSettings()
qa = lambda a: assess(a, meta_for(a), cfg, job_id="q", image_index=0, image_path="p")
for d in (0.0, 0.001, 0.01, 0.05):
    n, _ = inject_salt_pepper(smooth_image(512, 512), d)
    print("impulse injected", d, "measured", round(qa(n).metric("impulse_density").value, 6))
print("1-px lines", qa(bright_lines()).metric("impulse_density").value)
rng = np.random.default_rng(3); c = smooth_image(256, 256)
print("sigma=20 measured", qa(np.clip(c + rng.normal(0, 20, c.shape), 0, 255).astype(np.uint8)).metric("gaussian_noise_sigma_dn").value)
PY
```

- [ ] **Step 4: Append Q-065 to `project/qna.md`**

Use the Q-064 header shape. The content must include:

- **Header:** `## Q-065 · Restoration core library: detectors, planner, fused LUT pass, switching median, receipt`,
  then the `**Date:**` line with today's date, the branch, and the commit hashes from Tasks 1–9,
  then a `**Files:**` list.
- **Q1 — Mechanism:** assess → plan → execute_plan → build_receipt, with file:line references to
  `detectors.py:assess`, `planner.py:plan`, `executor.py:execute_plan`.
- **Q2 — Rationale:** the deviation table D1–D9 from this plan, each with its one-line reason.
  D1 (`max_similar_neighbours` 2 → 1) goes first, because it is a change to a spec number.
- **Q3 — Blast radius:** none for users. Nothing is wired into the DAG, and nothing imports
  `backend.app.restoration` outside tests. State that explicitly.
- **Q4 — Verification:** the Step 2 test counts, and the Step 3 numbers **verbatim**, including the
  σ=20 estimate's bias. Label every threshold as ASSUMPTION / PROVISIONAL as the spec does.
- **Q5 — Defence:** "why not a neural denoiser?" Salt-and-pepper and a global stretch are exact
  classical operations. The learned stages (SR, real-noise denoise) have slots at orders 30/90 that
  refuse with a reason until the Clarity-models plan verifies and measures a checkpoint.
- **Q6 — Open before wiring:** the three "Decisions to confirm before Plan 2" from this plan.

- [ ] **Step 5: Commit**

```bash
git add project/qna.md
git commit -m "docs(qna): Q-065 restoration core library"
```

---

