# Clarity agent — handoff for the next session

**Written:** 2026-10-03. **For:** a fresh Claude Code session that runs this work as
subagent-driven development (`superpowers:writing-plans`, then `superpowers:subagent-driven-development`).
**Read first:** this file. Then, as needed, `project/plan-2026-09-30-restoration-core.md` (the plan that
built the core) and `project/spec-2026-09-21-restoration-framework.md` (the binding spec).

"Clarity" is what the user calls the input-restoration package that runs inside agent
orchestration: denoising, salt-and-pepper removal, deblocking, upscaling, contrast/colour, and flare
handling. In code it is `backend/app/restoration/`.

---

## 1. Where things stand

| Item | State |
|---|---|
| Code | `backend/app/restoration/` on branch **`feat/restoration-core`**, HEAD **`4206244`**. Worktree `/home/natsu/dev/isro/.claude/worktrees/restoration-core`, forked from `prototype` `b158729`. **Not merged.** Nothing is wired into the agent DAG. |
| Modules | `schemas.py` contracts + honesty validators · `registry.py` stage registry · `detectors.py` 11 metrics + `assess()` · `planner.py` decision table `dt@1` · `correction.py` fused LUT contrast/colour (`photometric_correct`) · `impulse.py` switching median (`impulse_denoise`) · `stages.py` refusing stages `gaussian_denoise`, `super_resolve` · `executor.py` `execute_plan()` + `build_receipt()` |
| Tests | 98 restoration unit tests. Worktree suite `-m "not models"`: **611 passed, 10 failed**. The 10 are pre-existing and need git-ignored checkpoints absent from a worktree: 3 `test_geotiff_georeferencing`, 5 `test_registry_refusal_state`, 1 `test_optical_sar_safety`, 1 `integration/test_pipeline_end_to_end`. A gate is "same 10 failures by name". |
| Transcript | `project/qna.md` **Q-065** in the main checkout. It is uncommitted, next to the user's uncommitted Q-060..Q-064. Never commit `qna.md` from the worktree, because that would fork the append-only record. |
| Demo check tool | `scripts/clarity/demo_check.py` + `demo_check.html` in the worktree, **uncommitted**. Run: `systemd-run --user --scope -q --slice=satquery.slice -p MemoryMax=3G /home/natsu/dev/isro/.venv/bin/python scripts/clarity/demo_check.py <out_dir>`. Then copy the html to `<out_dir>/index.html` and publish the directory. |
| Review page | https://claude.ai/artifact/2nFkjp5TkSay85Ees1J76r (private). It shows a before/after slider, side-by-side and difference ×6 views, measurements, and native-resolution crops for all 36 cases. **Republish to the same URL**: from a new session, `Artifact` read it first, then publish with `url` and `root=<out_dir>`. |
| Python | `/home/natsu/dev/isro/.venv/bin/python` (3.11, numpy 2.4, scipy 1.17, opencv 5.0, torch 2.14, transformers 5.16, pyproj 3.7). The worktree has no venv of its own. |

## 2. The user's decision

**Do not integrate into the pipeline until it visibly works on `demo_resources/`.** The user verifies
by eye on the review page. Integration (old "Plan 2") comes only after the user signs off on the
page.

## 3. What the demo check found (measured 2026-09-30, reproduced 2026-10-03)

Real inputs: 26 demo images plus 6 video frames, 30 in total. **21 of 30 were modified.** Most of
that is false positives.

| Finding | Evidence |
|---|---|
| **Colour balance (grey-world) fires on normal scenes** | 13 real images, gain ratio 1.12–1.62 against a threshold of 1.15. Houses-with-trees comes out darker and bluer, with the grass washed out. A cast cannot be separated from genuine scene colour, so it **must become report-only**. |
| **The salt-and-pepper detector flags real content at 0.5 m** | LEVIR 101 "after" (a clean image): 2,079 candidates; the crop shows windshield glints, car highlights and dark specks. Clean real images measure 0.0005–0.0034, above the 0.001 gate. Injected 1% measures 0.0089. |
| **Change pairs corrected unevenly** | LEVIR 101 and 105: "after" modified, "before" not. This manufactures change for ChangeFormer (spec §4.4). |
| **SAR treated as optical** | Sentinel-1: speckle reads as 6.7% salt-and-pepper; the median and colour correction run on backscatter. |
| Salt-and-pepper repair itself works | Stress tests, PSNR against the original: airport 1% 25.1 → 41.8 dB, 5% 17.9 → 32.8 dB; street 1% 25.0 → 31.1 dB (lower because colour balance also fired). |
| Contrast stretch | Fired only on genuinely flat images: storage tanks (range 0.22), hazy drone frames (0.15). Plausibly correct. Its effect on the models is not measured. |

## 4. Scope for the next plan

### 4A. Calibrate the existing stages (do first)

Every item needs a test, and a re-run of the demo check afterwards.

1. `grey_world_gain` becomes **NOT_CALIBRATED** (report-only; the planner refuses to gate on it).
   `planner.DECISION_TABLE` row 7 goes, or `validate_table` will raise.
2. **Salt-and-pepper:**
   - raise `impulse_gate` 0.001 → **0.005** (`configs/app.yaml`);
   - count only pixels pinned exactly at the extremes, by dropping the `dev >= 2*dev_dn` alternative
     in `impulse_candidates` (spec §3.1 clause 5);
   - re-measure the clean-image floor and the injected recovery, and record both.
3. **SAR exclusion:** inputs whose modality is SAR skip every optical stage, and the receipt says so.
   The modality comes from metadata or the caller. Check how `state.modalities` is set in the DAG
   before choosing.
4. **Change pairs:** both dates get the identical correction, fitted jointly, or neither is
   corrected (spec §4.4). This needs a pair-level entry point, plus `StageReceipt.image_index`
   (plan Decision #6).
5. The open "Decisions to confirm" #1–#8 in `project/plan-2026-09-30-restoration-core.md`:
   - uint16 dynamic range;
   - signed and float semantics;
   - stage memory (93 B/px measured);
   - `_tiles` overlap;
   - offset blackening a constant band.
   Fold in the ones that block the items above. Ask the user about any that need a product call.

### 4B. Missing Clarity stages (the user asked for these on 2026-10-03)

| Stage | Proposal | Notes |
|---|---|---|
| **RGB / sensor noise reduction** | Classical non-local means (`cv2.fastNlMeansDenoisingColored`, no new dependency), gated on the measured `gaussian_noise_sigma_dn`. It fills the existing `gaussian_denoise` slot (order 30). | The estimator reads ~11% low (17.79 for a true σ = 20). Calibrate the gate with injected noise. SCUNet (Apache-2.0, 72 MB) replaces it only if it scores better. |
| **Pixelation / JPEG blockiness** | A new detector (blockiness = discontinuity across the 8×8 grid relative to inside blocks) plus a classical deblocking filter that smooths across block boundaries only. | It needs a new `STAGE_ORDER` slot. Put it before the impulse stage, because compression artefacts confuse the median. Learned option later: FBCNN or `caidas/swin2SR-compressed-sr-x4-48`. |
| **Upscaling** | Swin2SR ×2 (`caidas/swin2SR-classical-sr-x2-64`, Apache-2.0, ~49 MB, loads via the installed `transformers`) for RGB. SEN2SR (`tacofoundation/SEN2SR`, `SEN2SRLite/NonReference_RGBN_x4`, CC0, 0.47 M params, has a low-frequency hard constraint) for Sentinel-2. **Preview-only first.** | It changes the pixel grid, so it breaks spec §1.2 "no geometric change". Boxes, masks and GeoJSON need mapping back before any model consumes it. Routing rule: upscale only when the input GSD is coarser than the routed model's `trained_gsd_m`. Never GAN or diffusion (Real-ESRGAN, SUPIR, DiffBIR are rejected because they invent texture). Weights must pass `scripts/verify_checkpoints.py`. |
| **Lens flare** | **Detect and warn only**: large, low-frequency, near-saturated blobs. **No removal.** | Removal paints pixels the sensor never captured, which the project forbids. It is relevant to drone video, not satellites. |
| (exists) Salt-and-pepper, contrast stretch | Keep; calibrated per 4A. | |

### 4C. Make every stage visible

- Add a stress case per stage type to `demo_check.py`:
  - injected Gaussian RGB noise at 2–3 σ levels;
  - JPEG quality 10/20 for blockiness;
  - a 2× downscale of a clean image, upscaled back and scored against the original;
  - a synthetic flare;
  - the existing salt-and-pepper and low-contrast cases.
- Re-run on all real demo images too. Clean images should come out **untouched**, and that is the
  headline number to report: N of 30 modified, and why.
- Republish to the same artifact URL. Put a per-stage index on the page so the user can jump to
  "noise reduction", "deblocking", "upscaling" and so on directly.

## 5. Hard rules (from the user, the spec and project memory)

- **Nothing fabricates output.**
  - No 0.0 or other stand-in for an unmeasured value.
  - Never APPLIED without a measured change.
  - Never claim a degradation is fixed when it isn't.
  - Refusals carry a reason (`NOT_CONFIGURED`).
  - Learned stages stay refusing until verified **and** measured on our data.
- **One heavy job at a time.** The machine has 14 GB and has frozen three times. Model downloads,
  model runs and full test suites each run alone, inside `satquery.slice`.
- **Parallel subagents are fine for light work.** Parallelise independent tasks in separate git
  worktrees. Parallel agents run only `pytest tests/unit -k restoration`, and the controller runs the
  full suite once after merging.
- **Work on `feat/restoration-core`** or a branch off it, never on `prototype` directly. The main
  checkout has unrelated uncommitted user work.
- **`project/qna.md` is a stenographic record.** Append a Q-entry for each major change, with
  measured numbers verbatim and unflattering ones included. It never gates anything. Append it in
  the main checkout only.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `git add` only
  the files a task names.
- Thresholds live in `configs/app.yaml` under `restoration:`, never in code.

## 6. How to start the next session

1. Read this file, then `git -C /home/natsu/dev/isro/.claude/worktrees/restoration-core log --oneline -18`.
2. Re-run the demo check once to confirm the baseline: 21 of 30 modified.
3. Use `superpowers:writing-plans` to write `project/plan-<date>-clarity-v2.md` covering 4A → 4B → 4C.
   - Calibration (4A) goes first.
   - Each new stage gets a stress test plus a demo-check row.
   - Upscaling is its own heavy-job task.
4. Execute it with `superpowers:subagent-driven-development`:
   - keep a ledger;
   - review each task;
   - make the final whole-branch review on the most capable model.
5. End by republishing the review page and asking the user to verify it. Integration into the
   pipeline comes only after the user signs off.
