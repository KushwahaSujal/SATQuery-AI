# PPT Workflow Slide — Source Assets

Everything here is the **actual input and output** of the run that
`project/handoff/ppt-results.md` §1 reports. Nothing is reconstructed or mocked.

**Job:** `results/showcase-3096b285` · **Run:** 2026-09-04

## The query

> *"The ship is positioned at the top edge of the image, within the waters adjacent to the upper harbor."*

**Image:** `P0331_0012.png` — 512×512, VRSBench official validation split
(`xiang709/VRSBench`, `Images_val`)

## Files

| File | What it is |
|---|---|
| `01-input.png` | The raw input image, untouched. Harbour scene: two long piers, water, a small boat moored at the top edge. |
| `02-output-overlay.png` | The system's answer rendered as evidence — the SAM 2.1 segmentation mask (teal) over the boat the query referred to. |
| `03-segmentation-mask.png` | The binary mask alone (633 bytes), 1,270 pixels. |
| `04-evidence.geojson` | Polygon boundary of the detection, machine-readable. |
| `05-audit-report.pdf` | Auto-generated audit report for the job. |
| `06-execution-trace.json` | All 26 observable execution steps with timings. |

## The numbers on this exact run

| | |
|---|---|
| Capability routed to | `single_image_grounding` |
| Routing confidence | **0.98** |
| Entities parsed | `object=ship · position=top · relation=within · reference=harbor` |
| Models invoked | Grounding DINO → V4 reasoner → SAM 2.1 |
| Predicted box | `[334.0, 0.9, 383.7, 60.5]` |
| Ground truth (VRSBench) | `[332.8, 0.0, 384.0, 56.3]` |
| **IoU** | **0.891** |
| Mask area | 1,270 px |
| Detector confidence | 0.3008 |
| SAM 2 mask score | 0.8977 |
| Latency | 7,531 ms cold · **314 ms warm** |
| Warnings / errors | 0 / 0 |

## Suggested slide layout

```
   01-input.png            →   02-output-overlay.png
   "user uploads this"         "system returns this"
   + the query text            + IoU 0.891 vs VRSBench ground truth

   underneath: the 6-stage DAG, or a few rows of 06-execution-trace.json
```

The strongest point to make is not the mask — it's that **routing happened before
any model loaded**: the system parsed `ship / top / within / harbor` and chose the
grounding specialist at 0.98 confidence deterministically, with no LLM in the path.
That is the agentic requirement, demonstrated.

## Reproduce

```bash
python scripts/showcase_workflow.py \
  --image P0331_0012.png \
  --query "The ship is positioned at the top edge of the image, within the waters adjacent to the upper harbor."
```
