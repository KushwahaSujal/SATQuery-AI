# Work split — Ushnik · Ayushman

**Cut 2026-09-14, the night before the demo**, against what is committed at `cd4ef93` on
`refactor/s0-remove-dead-layers`. Measured state: `pre-demo.md` and `qna.md` Q-007 to Q-011.

**How it is cut:** by file ownership, so neither of you blocks or overwrites the other. Ushnik takes
the agent, orchestration and evidence layers plus anything that needs the whole pipeline running.
Ayushman takes model- and data-side work where his training background is the advantage. Estimates
are guesses, not measurements.

**Working agreement**
- Branch off `refactor/s0-remove-dead-layers`: `feat/ayushman-<topic>`, `feat/ushnik-<topic>`.
- Before any PR: `pytest -q` → **180 passed, 0 failed** is the baseline to beat.
- Anything >3 files, a model/dataset swap, or a claim for the demo/paper → a `qna.md` entry, written as
  you go. It never blocks the merge.
- Never fabricate a number. If it wasn't measured, write `NOT MEASURED`.

| Area | Owner | Hands off |
|---|---|---|
| `agent/`, `orchestration/`, `evidence/adjudicator.py`, `evidence/verifier.py`, `workflows/` | Ushnik | Ayushman |
| `ml/adapters/fusion/`, `ml/adapters/bigearthnet.py`, `ml/adapters/cdvqa/`, `checkpoints/`, `training/`, `scripts/evaluate_*` | Ayushman | Ushnik |
| `ml/adapters/changeformer/` | Ushnik edits; Ayushman supplies checkpoints and numbers | — |
| `frontend/src/components/**` | Sandipan (D-111) | both |

---

## Tonight — before the demo

### Ushnik
1. **ChangeFormer ⇄ CDVQA adjudication** (plan phase 3, ~1 h). Wire `EvidenceAdjudicator` into
   `run_change_vqa`, remove its invented constant confidences (0.88, 0.35, `or 0.5`), and read
   ChangeFormer's real metadata keys.
   - *Why:* CDVQA currently says "60% to 70% change" on a pair where ChangeFormer measured ~4.6%, and
     nothing flags the disagreement. This is the two-agent story for change detection.
   - *Done when:* a conflicting pair shows `CONFLICT` with both confidences in the trace, and each rule
     has a unit test.
2. **Routing fixes** (~30 min).
   - "describe this image" → `single_image_caption`, not VQA.
   - "compute NDVI" → an explicit "not supported yet" answer, not BLIP's "No."
3. **Full demo rehearsal over HTTP** (~45 min, after 1 and 2).
   - Start the real server, close Chrome (it held 333 MB of GPU memory), and run every demo query once
     in order: VQA, grounding, change + AOI GeoTIFF, video.
   - Save the responses to `results/evaluations/demo_rehearsal_20260915/`.
   - Whatever breaks there is tonight's last fix.

### Ayushman
1. **Stop Optical–SAR inventing results** (~30 min, `ml/adapters/fusion/`). Until rule-based fusion
   exists, `run_optical_sar` returns a `NOT_CONFIGURED` result stating that the fusion head was never
   trained, not "Permanently irrigated land (52.5%)".
   - *Done when:* the audit query answers with NOT_CONFIGURED and a test asserts it.
   - He has already confirmed in writing that the head was never trained (`pre-demo.md` §1.1).
2. **Build the demo inputs** (~45 min, `datasets/samples/demo/`, git-ignored if large).
   - A real georeferenced GeoTIFF pair: Sentinel-2 or any source with a genuine CRS — not our
     re-georeferenced LEVIR scene.
   - A `.geojson` area of interest drawn over a real change in it.
   - One query per demo item, with the expected answer written down *before* running it.
   - Hand them to Ushnik for the rehearsal.
3. **Mentor Q&A sheet on ChangeFormer** (~30 min). One page from his own reports: dataset, split,
   frozen threshold, test IoU 0.7386 / F1 0.8496, what the 0.435 threshold means, and the two failure
   panels in `results/evaluations/mentor/` (roof repaint, demolition).
   - Include the limit: it detects **building** change only, and out-of-domain accuracy is NOT MEASURED.

---

## Demo day

| | Ushnik | Ayushman |
|---|---|---|
| Drives | Agent orchestration: routing, trace, two-agent deliberation, AOI | Change detection model + Q&A on training |
| Answers | "Why believe the verifier?" (Q-009 §5), OOM recovery (Q-010), GeoTIFF/AOI accuracy (Q-011) | "Is the checkpoint real?" (Q-007), threshold selection, failure cases |
| Says first | The verifier rejects one real close-up car in the demo video; attribute answers can be DISPUTED | Building change only; not measured outside LEVIR-CD |

---

## After the demo

### Ushnik
1. **Restoration framework** — `backend/app/restoration/`: schemas, quality detectors, planner, the
   fused single-pass matrix/LUT correction, and the `assess_quality` / `restore_input` DAG nodes. The
   design is already agreed in this session's brainstorm; write the spec first.
2. **Confidence critique agent** — rule-based. It consumes model scores, the verifier's verdict and the
   restoration receipt, and can only hold or lower confidence.
3. **Verifier crop at image edges** — the black-padded crops behind the DISPUTED results on
   `05945_0000.png`. Re-measure with the cached harness before changing anything; the numbers in Q-009
   must stay reproducible.
4. **SAM 2 video masks** — propagation runs forward from one anchor, so earlier events get no mask
   (`pre-demo.md` §2.1e).

### Ayushman
1. **Rule-based Optical–SAR fusion** (`pre-demo.md` §1.1, Option A, 1–2 days): NDVI/NDWI from optical
   plus VH/VV from SAR → water / urban / bare soil / vegetation, with a labelled evaluation. Mandatory
   requirement #5.
2. **Remote-sensing adaptation evidence** (`pre-demo.md` §1.2, mandatory requirement #1): make
   `bigearthnet` produce real predictions with a measured score on its test split. Ushnik wires it into a
   capability and DAG branch once the adapter's `predict` works.
3. **Salt-and-pepper removal** — switching median, stills and video, gated by measured impulse
   density. Self-contained in `restoration/stages.py`; build it against Ushnik's schemas.
4. **Learned super-resolution** (post-demo, as agreed): pick Real-ESRGAN or SwinIR, verify the weights
   are real with `scripts/verify_checkpoints.py`, and measure on a held-out set before it goes anywhere
   near the pipeline. It stays disabled until then.
5. **ChangeFormer outside LEVIR-CD** — Sentinel-2 band order into the model and a measured score on
   one labelled non-LEVIR pair. Until then the Q-011 caveat stands.

---

## Hand-offs between you

- Ayushman → Ushnik tonight: demo GeoTIFF pair + AOI + expected answers (Ayushman #2), before the
  rehearsal.
- Ushnik → Ayushman after the demo: `restoration/schemas.py` before Ayushman starts salt-and-pepper.
- Ayushman → Ushnik after the demo: a working `bigearthnet` `predict` with its test score, before
  Ushnik wires the capability.
- Ushnik → Sandipan: the new response fields to surface — `evidence.metadata.agent_deliberation`
  (decision / DISPUTED), `evidence.metadata.aoi`, `POST /api/upload/aoi`, video `warnings`.
