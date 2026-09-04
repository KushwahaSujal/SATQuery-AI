# PRD — SatQuery AI

**Problem Statement:** SIH26167 / SIH26-26167
**Title:** SatQuery AI — An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries
**Organization:** ISRO / Department of Space · **Category:** Software · **Theme:** Space Technology
**Repo:** https://github.com/KushwahaSujal/SATQuery-AI
**This doc owner:** backend pair (natsu + Ayushman). Frontend is owned by the rest of the team.

---

## 1. What we are building

A **web application backed by an agentic remote-sensing AI service**. A user uploads one or two
satellite images (or a video), types a question in plain English, and gets back:

- a **textual answer**,
- **visual evidence** (boxes, masks, change maps, overlays) drawn on the imagery,
- a **confidence** figure,
- an **auditable execution summary** naming the task, the models/tools chosen, and the parameters,
- **downloadable artifacts** (PNG + legend, GeoTIFF, GeoJSON, PDF report).

The differentiator demanded by the problem statement is **not** the individual models. It is the
**agentic controller**: the system must decide, on its own, which specialist to run based on the
query and the shape of the input, then combine the outputs into one evidence-grounded answer.

---

## 2. Target users

| User | Need | What they get |
|---|---|---|
| **Non-expert analyst** (disaster cell, municipal planner, forest officer) | Answers from satellite data without knowing GIS, band math, or model names | Natural-language Q&A over uploaded imagery with a map overlay |
| **GIS/remote-sensing analyst** | Faster triage than ArcGIS/QGIS/ENVI for routine questions | Indices, SAR backscatter, change masks, pixel inspector, GeoTIFF/GeoJSON export back into their own tooling |
| **ISRO/SAC evaluator** (the actual grader) | Verify the five mandatory capabilities on held-out Cartosat-2S + RISAT pairs | Reproducible workflow selection, benchmark-format outputs, observable trace |
| **Our own team** | Ship and defend this in a hackathon, then convert to a conference paper | Documented decisions, measured numbers, honest capability matrix |

---

## 3. Mandatory scope (verbatim from the problem statement)

Each of these is **required**; failing any one fails the evaluation.

1. **Remote-sensing adaptation** — at least one visual or vision-language component must be
   fine-tuned or otherwise adapted on BigEarthNet or other open remote-sensing data.
   *A generic LLM/VLM without RS adaptation explicitly does not satisfy the requirement.*
2. **Single-image VQA** — mandatory baseline.
3. **One additional single-image task** — captioning/scene description **or** text-guided region grounding.
4. **Multi-image change analysis** — change description or change-VQA from a bi-temporal pair.
   Spatial change map optional but valuable.
5. **Cross-modal pair analysis** — extract complementary information from a co-registered
   optical/multispectral + SAR pair.
6. **Agentic orchestration** — automatically select, sequence, and execute the right specialists;
   validate inputs; emit an observable execution trace.

### Input scope

| Input | Formats | Tasks |
|---|---|---|
| Single image | GeoTIFF/TIFF (PNG/JPEG only for the prescribed benchmarks) | VQA, captioning, grounding |
| Cross-modal pair | Co-registered optical/multispectral + SAR | Joint extraction |
| Bi-temporal pair | Two co-registered scenes, different dates | Change detection, change description, change-VQA |

### Representative queries the system must answer

- "Describe the land-cover and major objects visible in this image."
- "Highlight the water body referred to in the query."
- "What changed between these two dates, and where did the change occur?"
- "Use the optical and SAR images together to identify built-up and water-covered regions."
- "Has the built-up area increased, decreased, or remained unchanged?"

### Evaluation

Public benchmarks on prescribed test splits (VRSBench, RSVQA, CDVQA) **plus** an undisclosed
ISRO/SAC set of pre-georeferenced, co-registered **Cartosat-2S optical + RISAT SAR** pairs with
reference answers, labels, boxes and masks. Scores are normalised before combining.

**Implication we must design for:** annotations are hidden and the sensors are Indian, not
Sentinel/Landsat. Anything that only works on the datasets we tuned against will collapse. Domain
shift is a first-class risk, not a footnote.

---

## 4. Feature list

### 4.1 Built and working (verified in code)

| Feature | Where |
|---|---|
| Deterministic intent classification + entity extraction | `backend/app/orchestration/intent_classifier.py` |
| Capability registry (13 capabilities) with priority resolution | `orchestration/capability_registry.py`, `matcher.py` |
| DAG planner + topological stage computation | `orchestration/dependency_graph.py` |
| Pre-execution dependency / resource / whitelist validation | `orchestration/dependency_checker.py`, `resource_manager.py`, `agent/validator.py` |
| Tool registry (14 callable tools) + safe executor | `agent/registry.py`, `agent/executor.py` |
| Open-vocabulary grounding: Grounding DINO → V1–V4 reasoner → SAM 2.1 | `models/grounding_dino.py`, `workflows/grounding_reasoner.py`, `models/sam2.py` |
| Bi-temporal change detection (ChangeFormerV6) | `models/changeformer.py` |
| Bi-temporal change VQA (CDVQA, 19 classes) | `models/cdvqa.py`, `models/cdvqa_model.py` |
| Evidence engine: boxes, masks, polygons, area stats, GeoJSON, PDF | `backend/app/evidence/` |
| Visual analytics: composites, NDVI/NDWI/NDBI, SAR dual-pol, heatmaps, inspector, exports | `backend/app/visualization/` |
| Streaming video pipeline + heuristic event flagger | `backend/app/video/`, `workflows/video_analysis.py` |
| PostgreSQL persistence (10 tables) + Alembic | `backend/app/db/` |
| REST API (~25 endpoints) | `backend/app/api/routes.py` |
| Next.js 14 dashboard (11 components) | `frontend/src/` |

### 4.2 Required but **not** satisfied yet — these are the real backlog

| Gap | Why it matters | Severity |
|---|---|---|
| **VQA/captioning runs on `Salesforce/blip-vqa-base`** — a generic VLM with zero remote-sensing adaptation | Directly violates mandatory requirement #1. As it stands we fail the headline criterion. | **Blocker** |
| **BigEarthNet adapter exists but is wired into no capability and no DAG** | The prescribed adaptation dataset is unused. | **Blocker** |
| **Optical-SAR fusion head is randomly initialised** — the setup doc creates the checkpoint by saving an untrained `CrossAttentionFusionNet`; `scripts/train_optical_sar_fusion.py` is referenced but absent | Cross-modal analysis (requirement #5) currently emits noise dressed as land-cover predictions. | **Blocker** |
| `multispectral_analysis` and `sar_analysis` capabilities route but have no DAG branch | "Compute NDVI" silently degrades to inspect-raster + report. | High |
| Grounding accuracy is weak (best measured mIoU 0.2371, R@0.5 0.26 on a VRSBench sample) | Grounding is our chosen "additional single-image task" and it is scored. | High |
| No RSVQA / VRSBench captioning evaluation harness | Two of three prescribed public benchmarks are unmeasured. | High |
| Cartosat-2S / RISAT characteristics never tested | The graded set is exactly this. | High |

### 4.3 Explicitly out of scope

Multi-user auth/RBAC · automated STAC harvesting · edge/ONNX packaging · video timeline trimming ·
anything that requires training a foundation model from scratch.

---

## 5. Non-functional requirements

- **Zero fabrication.** Never synthesise a missing band, feature, or score. If NIR is absent,
  return `INDEX_NOT_AVAILABLE` with an explanation. This is a stated selling point of the project
  and it is currently violated by the fusion path — see §4.2.
- **Evidence-first.** No naked text answers; every response carries spatial evidence.
- **Observable trace only.** Persist step name, tool, model, parameters, duration, status.
  Never expose internal chain-of-thought — the problem statement says internal reasoning is
  neither required nor evaluated.
- **Graceful degradation.** A missing checkpoint produces a `NOT_CONFIGURED` status and a clear
  message, never a crash and never a fake answer.
- **CPU fallback.** Must run without a GPU, slower, for demo laptops.
- **Reproducibility.** `docker-compose up` plus a documented checkpoint fetch must reproduce the
  system on a clean machine.

---

## 6. Success criteria

**Hackathon:** all five mandatory capabilities demonstrable live on judge-supplied imagery; the
agentic trace visibly shows the routing decision; no fabricated numbers anywhere.

**Paper:** the contribution is the *orchestration layer* — deterministic capability routing with
pre-execution dependency verification and provenance-linked evidence — measured against a
monolithic-VLM baseline on VRSBench / RSVQA / CDVQA. Ablations: V1 vs V2 vs V3 vs V4 reasoning,
router accuracy, cost/energy per query vs a single large VLM.
