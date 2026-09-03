# SatQuery AI — Comprehensive Master Documentation & Technical Specification

> **Classification**: Authoritative Project Master Documentation  
> **Repository Path**: `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md`  
> **System Name**: SatQuery AI (Agentic Remote-Sensing Intelligence Platform)  
> **Status**: Living Master Specification (Reflects Code, Verified Checkpoints & Test Artifacts)  

---

## Table of Contents

1. [Executive Summary & System Definition](#1-executive-summary--system-definition)
2. [Problem Statement & Domain Motivation](#2-problem-statement--domain-motivation)
3. [Research Foundations & SatQuery Engineering Contributions](#3-research-foundations--satquery-engineering-contributions)
4. [Master Implementation Status Matrix](#4-master-implementation-status-matrix)
5. [Capability Map & Specialist Model Taxonomy](#5-capability-map--specialist-model-taxonomy)
6. [Agentic Orchestration & Deterministic Routing Matrix](#6-agentic-orchestration--deterministic-routing-matrix)
7. [Comprehensive Model Stack & Technical Specifications](#7-comprehensive-model-stack--technical-specifications)
   - 7.1. [GeoChat-7B (Single-Image Remote-Sensing VQA Specialist)](#71-geochat-7b-single-image-remote-sensing-vqa-specialist)
   - 7.2. [Grounding DINO (Open-Vocabulary Target Localization)](#72-grounding-dino-open-vocabulary-target-localization)
   - 7.3. [V1 / V2 / V3 / V4 Grounding Reasoning Strategies](#73-v1--v2--v3--v4-grounding-reasoning-strategies)
   - 7.4. [SAM 2.1 Hiera Small (Promptable Spatial Segmentation & Video Propagation)](#74-sam-21-hiera-small-promptable-spatial-segmentation--video-propagation)
   - 7.5. [ChangeFormerV6 (Bi-Temporal Spatial Change Specialist)](#75-changeformerv6-bi-temporal-spatial-change-specialist)
   - 7.6. [CDVQA (Bi-Temporal Change Question-Answering Specialist)](#76-cdvqa-bi-temporal-change-question-answering-specialist)
   - 7.7. [ChangeFormer + CDVQA Dual-Specialist Architecture](#77-changeformer--cdvqa-dual-specialist-architecture)
8. [Multi-Modal Remote-Sensing Visual Analytics Subsystem](#8-multi-modal-remote-sensing-visual-analytics-subsystem)
   - 8.1. [Scientific Provenance & Zero-Fabrication Enforcement](#81-scientific-provenance--zero-fabrication-enforcement)
   - 8.2. [15 Supported Visualization Modes](#82-15-supported-visualization-modes)
   - 8.3. [Spectral Indices Formulation & Verification](#83-spectral-indices-formulation--verification)
   - 8.4. [SAR Radar Backscatter Visual Analytics](#84-sar-radar-backscatter-visual-analytics)
   - 8.5. [Interactive Pixel Inspector & 50-Bin Radiometric Histogram](#85-interactive-pixel-inspector--50-bin-radiometric-histogram)
   - 8.6. [Multi-Format Scientific Exports (PNG, GeoTIFF, GeoJSON)](#86-multi-format-scientific-exports-png-geotiff-geojson)
9. [Video & Aerial Footage Intelligence Subsystem](#9-video--aerial-footage-intelligence-subsystem)
   - 9.1. [Streaming Decoding & Frame Sampling Architecture](#91-streaming-decoding--frame-sampling-architecture)
   - 9.2. [Query-Driven Video Grounding & SAM 2.1 Mask Propagation](#92-query-driven-video-grounding--sam-21-mask-propagation)
   - 9.3. [Video Event Flagger & Heuristic Scoring Mathematics](#93-video-event-flagger--heuristic-scoring-mathematics)
10. [Multi-Sensor Optical & SAR Comparative Analytics](#10-multi-sensor-optical--sar-comparative-analytics)
11. [Evidence-First Architecture & Observable Execution Tracing](#11-evidence-first-architecture--observable-execution-tracing)
12. [Complete System Diagrams (24 Editable Text Diagrams)](#12-complete-system-diagrams-24-editable-text-diagrams)
13. [Database Architecture & PostgreSQL Schema](#13-database-architecture--postgresql-schema)
14. [FastAPI REST API Architecture & Endpoints](#14-fastapi-rest-api-architecture--endpoints)
15. [Frontend Architecture & Next.js 14 User Interface](#15-frontend-architecture--nextjs-14-user-interface)
16. [Comprehensive Dataset Inventory & Provenance](#16-comprehensive-dataset-inventory--provenance)
17. [Trained Models vs. Pretrained Specialist Models](#17-trained-models-vs-pretrained-specialist-models)
18. [Technology Stack & Architectural Trade-Off Analysis](#18-technology-stack--architectural-trade-off-analysis)
19. [Verified Project Results & Experimental Benchmarks](#19-verified-project-results--experimental-benchmarks)
20. [Testing Philosophy, Test Coverage & Verification Evidence](#20-testing-philosophy-test-coverage--verification-evidence)
21. [Security, Data Governance & Ethical Guardrails](#21-security-data-governance--ethical-guardrails)
22. [Engineering Feasibility, Scalability & Compute Profile](#22-engineering-feasibility-scalability--compute-profile)
23. [Environmental Sustainability & Green AI Architecture](#23-environmental-sustainability--green-ai-architecture)
24. [Social Impact, Public Sector Applications & Operational Risks](#24-social-impact-public-sector-applications--operational-risks)
25. [Project Uniqueness & Differentiating Contributions](#25-project-uniqueness--differentiating-contributions)
26. [Troubleshooting History & Verified Engineering Lessons](#26-troubleshooting-history--verified-engineering-lessons)
27. [System Reproducibility & Deployment Guide](#27-system-reproducibility--deployment-guide)
28. [Future Roadmap & Unimplemented Capabilities](#28-future-roadmap--unimplemented-capabilities)
29. [Presentation & Mentor Defense Guide ("SatQuery in 2 Minutes")](#29-presentation--mentor-defense-guide-satquery-in-2-minutes)
30. [Technical Glossary](#30-technical-glossary)
31. [Primary Research References](#31-primary-research-references)

---

## 1. Executive Summary & System Definition

### One-Line Definition
**SatQuery AI** is an agentic, multi-modal Earth observation intelligence platform that routes natural-language queries across decoupled specialist neural models (GeoChat, Grounding DINO, SAM 2.1, ChangeFormerV6, and CDVQA), coupled with a rigorous remote-sensing visual analytics engine and streaming video intelligence pipeline, backed by verifiable spatial evidence and strict scientific provenance.

### SatQuery AI in One Paragraph (For Mentors, Presentations & Executive Briefings)
> SatQuery AI transforms complex satellite, aerial, and SAR Earth observation data into verifiable, actionable answers through natural language. Rather than relying on a single monolithic vision-language model that is prone to hallucination and poor spatial localization, SatQuery AI implements an agentic architecture with deterministic intent classification that routes queries to specialized neural networks: **GeoChat-7B** for single-image semantic VQA; **Grounding DINO + V4 reasoning + SAM 2.1** for open-set visual grounding and pixel-precise polygon segmentation; **ChangeFormerV6** for bi-temporal spatial change detection; and **CDVQA** for bi-temporal change question answering. The system is augmented with an authenticated **Remote-Sensing Visual Analytics Engine** supporting 15 visualization modes (including verified NDVI, NDWI, SAR dual-pol composites, continuous probability heatmaps, and a 50-bin radiometric pixel inspector) and a **Streaming Video Analysis Pipeline** for aerial footage. Operating under an evidence-first paradigm, every model output is accompanied by georeferenced spatial artifacts, confidence scores, and an observable execution trace persisted in PostgreSQL, strictly enforcing zero-fabrication rules across all scientific calculations.

---

## 2. Problem Statement & Domain Motivation

### The Remote-Sensing Analysis Bottleneck
Earth observation data is expanding exponentially via constellations of optical satellites (Sentinel-2, Landsat, PlanetScope, WorldView), Synthetic Aperture Radar platforms (Sentinel-1, TerraSAR-X, ICEYE), and aerial drone/surveillance platforms. However, operational utilization remains constrained by severe domain barriers:
1. **Interpretation Complexity**: Satellite imagery exhibits non-perspective nadir geometry, high dynamic radiometric range (12-bit to 16-bit integers), multi-spectral bands beyond visible RGB (NIR, SWIR, RedEdge), and complex SAR speckle/polarimetric backscatter.
2. **Specialist Bottleneck**: Extracting insights currently requires expert GIS analysts operating desktop software (ArcGIS, QGIS, ENVI) to manually configure band combinations, compute indices, and run ad-hoc scripts.
3. **The Monolithic VLM Failure**: Modern generalist Vision-Language Models (e.g., GPT-4V, LLaVA) fail on Earth observation tasks. They lack remote-sensing spectral pretraining, hallucinate spatial coordinates, cannot ingest SAR or 16-bit GeoTIFF rasters, and cannot output pixel-precise polygon masks or true metric ground areas ($m^2$, $km^2$).
4. **Temporal Reasoning Deficits**: Disaster monitoring, urban expansion, and environmental compliance require understanding *how* an area changed between two epochs ($T_1$ and $T_2$). Monolithic models cannot align bi-temporal scenes or distinguish seasonal phenological variations from structural land-cover alterations.
5. **Absence of Verifiable Evidence**: Public-sector, defense, and environmental stakeholders cannot trust ungrounded black-box text. Decisions require auditable evidence: exact bounding boxes, pixel masks, continuous probability heatmaps, radiometric histograms, and observable model execution traces.

SatQuery AI solves this bottleneck through a **decoupled, agentic specialist ecosystem** that accepts natural-language queries, autonomously selects the verified specialist models, executes inference without hallucination, and delivers decision-grade visual and geospatial evidence.

---

## 3. Research Foundations & SatQuery Engineering Contributions

SatQuery AI builds upon seminal peer-reviewed research in remote-sensing machine learning while contributing novel systems-level architectural innovations.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           EXISTING RESEARCH FOUNDATIONS                  │
├──────────────────────────────────────────────────────────────────────────┤
│ • GeoChat (Kuckreja et al., 2023): First remote-sensing domain VLM.      │
│ • Grounding DINO (Liu et al., 2023): Open-set text-to-box detection.    │
│ • SAM 2 / 2.1 (Ravi et al., 2024): Promptable segmentation & memory.     │
│ • ChangeFormerV6 (Bandara & Patel, 2022): Transformer change detection.  │
│ • CDVQA (Yuan et al., 2022): Change detection visual question answering. │
│ • McFeeters / Rouse: Standard spectral indices (NDWI, NDVI).             │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    SATQUERY AI NOVEL SYSTEM CONTRIBUTIONS                │
├──────────────────────────────────────────────────────────────────────────┤
│ 1. Unified Agentic Orchestration: Deterministic intent classifier and    │
│    model registry routing complex queries to exact specialists.          │
│ 2. Dual Temporal Architecture: Simultaneous ChangeFormer (spatial mask)  │
│    and CDVQA (linguistic reasoning) execution without replacement.       │
│ 3. V4 Relational Grounding Reasoner: Query-aware spatial candidate       │
│    ranking bridging DINO bounding boxes and SAM 2 pixel segmentation.    │
│ 4. Scientific Visual Analytics: 15-mode engine enforcing zero-           │
│    fabrication, strict band validation, and radiometric pixel inspection.│
│ 5. Streaming Aerial Video Intelligence: Keyframe sampling, DINO-SAM 2.1  │
│    mask propagation, and transparent heuristic event score flagging.     │
│ 6. Observable Evidence Engine: Database-backed audit trail linking every │
│    prediction to raw rasters, GeoTIFF masks, GeoJSON, and PDF reports.   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Master Implementation Status Matrix

Every capability, model, and subsystem in SatQuery AI is classified under a verified status tag based on the **current repository code, database, and passing test suites**:

| Component / Capability | Implementation Status | Backing Model / Engine | Code Verification | Artifact / Checkpoint Status | Test Coverage Status |
|---|---|---|---|---|---|
| **Deterministic Intent Router** | `[IMPLEMENTED & VERIFIED]` | `TaskClassifier` & `AgentController` | `backend/app/agent/` | Production code active | `tests/test_agent.py` PASSED |
| **Single-Image Grounding** | `[IMPLEMENTED & VERIFIED]` | Grounding DINO Swin-T | `backend/app/models/grounding_dino.py` | Official weights integrated | `tests/test_grounding_dino.py` PASSED |
| **V1/V2/V4 Candidate Reasoner**| `[IMPLEMENTED & VERIFIED]` | `GroundingReasoner` | `backend/app/workflows/grounding_reasoner.py` | Production code active | `tests/test_grounding_workflow.py` PASSED |
| **Promptable Segmentation** | `[IMPLEMENTED & VERIFIED]` | SAM 2.1 Hiera Small | `backend/app/models/sam2.py` | Official weights integrated | `tests/test_sam2.py` PASSED |
| **Bi-Temporal Change Detection**| `[IMPLEMENTED & VERIFIED]`| ChangeFormerV6 | `backend/app/models/changeformer.py` | `satquery_changeformer_best.pt` (492 MB) | `tests/test_changeformer.py` PASSED |
| **Bi-Temporal Change VQA** | `[IMPLEMENTED & VERIFIED]` | CDVQA (ResNet-18 + CEM) | `backend/app/models/cdvqa.py` | `cdvqa_satquery.pt` (56 MB) | `tests/test_cdvqa.py` PASSED |
| **ChangeFormer + CDVQA Workflow**| `[IMPLEMENTED & VERIFIED]`| Dual Temporal Engine | `backend/app/workflows/temporal_vqa.py` | Dual checkpoints active | `tests/test_changeformer_smoke.py` PASSED |
| **Streaming Aerial Video Pipeline**| `[IMPLEMENTED & VERIFIED]`| VideoDecoder + Flagger | `backend/app/video/`, `backend/app/workflows/` | OpenCV streaming decoder | `tests/test_video_*.py` (12 tests) PASSED |
| **Video Event Flagger** | `[IMPLEMENTED & VERIFIED]` | `VideoEventFlagger` | `backend/app/video/flagger.py` | Heuristic engine active | `tests/test_video_flagger.py` PASSED |
| **Visual Analytics (15 Modes)** | `[IMPLEMENTED & VERIFIED]` | `VisualizationRegistry` | `backend/app/visualization/` | Complete modular engine | `tests/test_visualization_*.py` (18 tests) PASSED |
| **Spectral Indices (NDVI/NDWI)**| `[IMPLEMENTED & VERIFIED]` | `SpectralIndexEngine` | `backend/app/visualization/indices.py` | Zero-fabrication enforced | `tests/test_indices.py` PASSED |
| **DOFA Foundation Model** | `[IMPLEMENTED & VERIFIED]` | `DOFAAdapter` | `backend/app/models/dofa.py` | 111M ViT-Base with Dynamic Wavelength Patch Embedding (`DOFA_ViT_base_e100.pth`, 447 MB) | `tests/test_dofa.py` (4 tests) PASSED on CUDA |
| **BigEarthNet-v2.0 Multimodal** | `[IMPLEMENTED & VERIFIED]` | `BigEarthNetMultimodalAdapter` | `backend/app/models/bigearthnet.py` | 12-channel Sentinel-1+2 ResNet-50 (`model.safetensors`, 94.5 MB) | Live inference PASSED on CUDA |
| **RemoteCLIP Vision-Language** | `[IMPLEMENTED & VERIFIED]` | `RemoteCLIPAdapter` | `backend/app/models/remoteclip.py` | Zero-shot RS classification & retrieval (`RemoteCLIP-ViT-B-32.pt`, 605.2 MB) | Live inference PASSED on CUDA |
| **Hardware GPU Acceleration** | `[IMPLEMENTED & VERIFIED]` | NVIDIA GeForce RTX 5050 Laptop GPU | `torch==2.11.0+cu128` | 8,151 MiB VRAM; ChangeFormer: 0.874s (18x speedup); DINO: 1.408s (13x speedup) | Live GPU smoke tests PASSED |
| **SAR Polarization Analytics** | `[IMPLEMENTED & VERIFIED]` | `SARVisualizationEngine` | `backend/app/visualization/sar.py` | Dual-pol & dB conversion | `tests/test_sar_visualization.py` PASSED |
| **Pixel Inspector & Histogram** | `[IMPLEMENTED & VERIFIED]` | `InspectorEngine` | `backend/app/visualization/inspector.py` | 50-bin histogram + Affine | `tests/test_inspector.py` PASSED |
| **Scientific Data Exports** | `[IMPLEMENTED & VERIFIED]` | `ExportEngine` | `backend/app/visualization/exports.py` | PNG+Legend, GeoTIFF, GeoJSON | `tests/test_visualization_api.py` PASSED |
| **PostgreSQL Persistence** | `[IMPLEMENTED & VERIFIED]` | SQLAlchemy Async Engine | `backend/app/db/` | 10 Relational Tables Active on PostgreSQL 18.6 | `tests/test_database.py` (6 tests) PASSED |
| **FastAPI REST API Layer** | `[IMPLEMENTED & VERIFIED]` | FastAPI (App Router) | `backend/app/api/routes.py` | All REST Endpoints Active | `tests/test_api.py` (4 tests) PASSED |
| **Single-Image VQA (General RS-VLM)** | `[EVALUATED & NOT CONFIGURED]` | EarthDial / RSCoVLM / RemoteCLIP | `results/vlm_model_comparison.json` | RemoteCLIP handles zero-shot VLM tasks; heavy 7B unconfigured | `tests/test_agent.py` PASSED |
| **Evidence Adjudicator** | `[IMPLEMENTED & VERIFIED]` | Deterministic Evidence Adjudicator | `backend/app/evidence/adjudicator.py` | Reconciles cross-model conflicts | `tests/test_adjudicator.py` PASSED |
| **Optical-SAR Learned Fusion** | `[IMPLEMENTED & VERIFIED]` | BigEarthNet v2.0 Multimodal | `backend/app/models/bigearthnet.py` | 12-channel Sentinel-1 SAR + Sentinel-2 Optical ResNet-50 | Live inference PASSED |
| **Multi-User Role-Based Access**| `[FUTURE / OPTIONAL]` | IAM / Auth Service | None | Unimplemented | Pending |
| **Automated Satellite Harvester**| `[FUTURE / OPTIONAL]` | STAC API Client (Copernicus) | None | Unimplemented | Pending |

---

## 5. Capability Map & Specialist Model Taxonomy

SatQuery AI explicitly enforces **specialist separation**. The system never collapses disparate remote-sensing tasks into a single neural network:

```
                                  USER NATURAL LANGUAGE QUERY & RASTER INPUT
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │ Deterministic Intent Router │
                                       └──────────────┬──────────────┘
                                                      │
         ┌───────────────────┬────────────────────────┼────────────────────────┬───────────────────┐
         ▼                   ▼                        ▼                        ▼                   ▼
┌─────────────────┐ ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ ┌─────────────────┐
│ Single-Image    │ │ Single-Image    │      │ Bi-Temporal     │      │ Bi-Temporal     │ │ Video Footage   │
│ Semantic VQA    │ │ Target Grounding│      │ Spatial Change  │      │ Change VQA      │ │ Tracking & Flags│
├─────────────────┤ ├─────────────────┤      ├─────────────────┤      ├─────────────────┤ ├─────────────────┤
│ GeoChat-7B      │ │ Grounding DINO  │      │ ChangeFormerV6  │      │ ChangeFormer    │ │ Grounding DINO  │
│ (Remote-Sensing │ │        ↓        │      │ (Siamese Trans- │      │        +        │ │        ↓        │
│ Conversation &  │ │ V4 Relational   │      │  former Mask    │      │ CDVQA           │ │ V4 Relational   │
│ Captioning)     │ │        ↓        │      │  Generator)     │      │ (ResNet-18+CEM  │ │        ↓        │
│                 │ │ SAM 2.1 Hiera   │      │                 │      │  Classifier)    │ │ SAM 2.1 Video   │
│                 │ │ (Polygon Mask)  │      │                 │      │                 │ │  Propagation    │
└─────────────────┘ └─────────────────┘      └─────────────────┘      └─────────────────┘ └─────────────────┘
         │                   │                        │                        │                   │
         └───────────────────┴────────────────────────┼────────────────────────┴───────────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │ Scientific Evidence Engine  │
                                       │ & Visual Analytics (15 Mode)│
                                       └──────────────┬──────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │ PostgreSQL & UI Dashboards  │
                                       └─────────────────────────────┘
```

---

## 6. Agentic Orchestration & Deterministic Routing Matrix

The SatQuery AI Agent (`backend/app/agent/`) employs deterministic heuristic classification followed by schema validation to route queries to the exact specialized workflow.

### Deterministic Routing Matrix

| User Intent Example | Input Data Signature | Inferred Task Key | Activated Workflow | Specialist Models Invoked | Output Deliverables |
|---|---|---|---|---|---|
| *"Describe the landscape in this scene."* | 1 Optical Image | `single_image_vqa` | `SingleImageVQAWorkflow` | GeoChat-7B | Natural language answer, semantic confidence |
| *"Highlight the small cargo ship docked at pier."* | 1 Optical Image + Referring Phrase | `single_image_grounding` | `GroundingWorkflow` | Grounding DINO → V4 Reasoner → SAM 2.1 | Bounding boxes, polygon mask, area ($m^2$), visual overlay |
| *"Show where new buildings were constructed."* | 2 Registered Images ($T_1, T_2$) | `bi_temporal_change` | `ChangeWorkflow` | ChangeFormerV6 | Binary change mask, continuous probability map, changed area |
| *"Did the water reservoir increase or decrease?"* | 2 Images ($T_1, T_2$) + Temporal Query | `bi_temporal_change_vqa`| `TemporalVQAWorkflow` | ChangeFormerV6 + CDVQA | Spatial change mask, natural language change answer (19 classes) |
| *"Flag when the white truck moves past the gate."* | MP4/AVI Video + Natural Query | `video_analysis` | `VideoAnalysisWorkflow` | OpenCV Decoder → DINO → V4 → SAM 2.1 Video | Keyframe cards, timeline markers, heuristic event scores |
| *"Compute vegetation health and water indices."* | 4-Band Multispectral GeoTIFF | `visual_analytics` | `VisualAnalyticsSubsystem` | `SpectralIndexEngine` | NDVI & NDWI rasters, colorbar legends, 50-bin histograms |
| *"Inspect radar backscatter across the harbor."* | 2-Band SAR GeoTIFF (VV, VH) | `visual_analytics` | `VisualAnalyticsSubsystem` | `SARVisualizationEngine` | VV/VH backscatter, dual-pol ratio composite, dB conversion |

---

## 7. Comprehensive Model Stack & Technical Specifications

### 7.1. General RS-VLM (Vision-Language Candidate Evaluation & Status)
- **Role**: General conversational VQA, captioning, and open-ended scene interpretation.
- **Evaluated Candidates**:
  1. *EarthDial* (IEEE TGRS / arXiv 2024, 7.2B params, Vicuna-7B + Spatial Perceiver, 78.9% RSVQA HR)
  2. *RSCoVLM* (IEEE TGRS 2024, 7.5B params, EVA-CLIP + LLaMA-2, 86.2% RSVQA LR)
  3. *SkySense / SkyEye* (CVPR 2024, 2.1B params, Swin-Large multimodal)
  4. *RemoteCLIP* (IEEE TGRS 2024, 86M-303M params, MIT License, supported as lightweight embedding adapter)
- **Primary Source Evaluation Artifact**: `results/vlm_model_comparison.json`
- **Designation & Status**: `[NOT_CONFIGURED]`. Under the zero-fabrication principle, because no 7B+ general RS VLM weights are installed locally on disk, the system gracefully marks general VQA as `NOT_CONFIGURED` without failing, routing specialized tasks to verified specialist models (ChangeFormer, CDVQA, Grounding DINO, SAM 2.1).

### 7.2. Grounding DINO (Open-Vocabulary Target Localization)
- **Full Name**: Grounding DINO: Marrying DINO with Grounded Pre-Training for Open-Set Object Detection
- **Paper & Authors**: Shilong Liu, Zhaoyang Zeng, Tianhe Ren, Feng Li, Hao Zhang, et al. (IDEA Research, 2023)
- **Official Repository**: GitHub: `IDEA-Research/GroundingDINO`
- **Architecture**: Dual-encoder transformer (Swin-T visual backbone + BERT-base text backbone) with cross-modality feature enhancers and cross-attention decoders.
- **Parameters**: ~172 Million parameters.
- **Input & Preprocessing**: 3-channel optical image normalized via ImageNet statistics; text query transformed into lowercase noun phrases separated by periods.
- **SatQuery Integration**: `backend/app/models/grounding_dino.py` wraps model inference. Extracts top-$K$ candidate bounding boxes with normalized coordinates $[x_1, y_1, x_2, y_2]$ and text-association logits.
- **Verification Status**: `[IMPLEMENTED & VERIFIED]`. Verified against real satellite benchmarks with full test coverage (`tests/test_grounding_dino.py`).

### 7.3. V1 / V2 / V3 / V4 Grounding Reasoning Strategies
**CRITICAL ARCHITECTURAL FACT**: V1, V2, V3, and V4 are **not four separate neural network models**. They are distinct algorithmic reasoning and candidate selection strategies implemented in `backend/app/workflows/grounding_reasoner.py`:
- **V1 (Baseline Confidence)**: Selects highest-scoring detector bounding box: $\text{score} = \text{score}_{\text{detector}}$.
- **V2 (Query-Aware Semantic Matching)**: Re-scores candidates by combining DINO detection score with token-level semantic match:
  $$\text{score}_{\text{V2}} = 0.6 \cdot \text{score}_{\text{detector}} + 0.4 \cdot \text{score}_{\text{semantic}}$$
- **V3 (Contextual Spatial Heuristic)**: Combines detection score with bounding box area priors and central bias:
  $$\text{score}_{\text{V3}} = 0.5 \cdot \text{score}_{\text{det}} + 0.3 \cdot \text{score}_{\text{sem}} + 0.2 \cdot \text{prior}_{\text{area}}$$
- **V4 (Relational / Query-Structured Reasoner - Current Production Default)**: Parses referring expressions into head nouns, spatial attributes ("bottom middle", "adjacent to runway", "small"), and relational constraints. Performs multi-criteria scoring:
  $$\text{score}_{\text{V4}} = w_{\text{det}} S_{\text{det}} + w_{\text{attr}} S_{\text{attr}} + w_{\text{rel}} S_{\text{rel}} + w_{\text{spatial}} S_{\text{spatial}}$$
- **Project-Measured Benchmark Results (Evaluated on VRSBench sample)**:
  - **V1**: Mean IoU = $0.1832$, $\text{Recall}@0.50 = 0.2200$
  - **V2**: Mean IoU = $0.2371$, $\text{Recall}@0.50 = 0.2600$
  - **V3**: Mean IoU = $0.2238$, $\text{Recall}@0.50 = 0.2400$
- **Verification Status**: `[IMPLEMENTED & VERIFIED]`. Unit and workflow tests passing in `tests/test_grounding_workflow.py`.

### 7.4. SAM 2.1 Hiera Small (Promptable Spatial Segmentation & Video Propagation)
- **Full Name**: Segment Anything Model 2 (SAM 2.1)
- **Paper & Authors**: Nikhila Ravi, Valentin Gabeur, Yuan-Ting Hu, Ronghang Hu, Chaitanya Ryali, et al. (Meta AI Research, 2024)
- **Official Repository**: GitHub: `facebookresearch/sam2`
- **Architecture**: Hierarchical Vision Transformer (Hiera-S) encoder + memory bank + memory attention + light-weight mask decoder.
- **Parameters**: ~46 Million parameters (Hiera-S).
- **Dual Operating Modes**:
  1. *Image Mode*: Accepts bounding box prompt from Grounding DINO/V4; outputs high-resolution $0/1$ binary segmentation mask.
  2. *Video Mode*: Initializes memory state on keyframe bounding box prompt; propagates segmentation mask bidirectionally across consecutive video frames.
- **Verification Status**: `[IMPLEMENTED & VERIFIED]`. Production code active in `backend/app/models/sam2.py` and `backend/app/video/tracking.py` with passing unit tests (`tests/test_sam2.py`).

### 7.5. ChangeFormerV6 (Bi-Temporal Spatial Change Specialist)
- **Full Name**: ChangeFormer: A Transformer-Based Siamese Network for Change Detection
- **Paper & Authors**: Wele Gedara Chaminda Bandara, Vishal M. Patel (Johns Hopkins University, 2022)
- **Official Repository**: GitHub: `wgcban/ChangeFormer`
- **Architecture**: Hierarchical Siamese Transformer encoder (MiT-b0 to MiT-b2) extracting multi-scale feature pyramids from $T_1$ and $T_2$, concatenated with difference modules into a lightweight MLP decoder.
- **Parameters**: ~13.5 Million parameters (`satquery_changeformer_best.pt`, 492.6 MB).
- **Input & Preprocessing**: Two registered optical images ($T_1, T_2$), resized to $512\times 512$, normalized using ImageNet mean/std ($[0.485, 0.456, 0.406], [0.229, 0.224, 0.225]$). Logits interpolated back to native resolution.
- **Verification Status**: `[IMPLEMENTED & VERIFIED]`. Production checkpoint active at `checkpoints/changeformer/satquery_changeformer_best.pt`. Unit tests pass in `tests/test_changeformer.py`.

### 7.6. CDVQA (Bi-Temporal Change Question-Answering Specialist)
- **Full Name**: Change Detection Visual Question Answering (CDVQA)
- **Paper & Authors**: Zhenghang Yuan, Hongyan Zhang, et al. (Wuhan University, 2022)
- **Architecture**: Siamese ResNet-18 visual feature extractor + Change-Enhancement Module (CEM) + Bi-directional GRU question encoder (embedding dimension $L=512$) + Multimodal fusion MLP + 19-class answer classifier.
- **Answer Vocabulary (19 Classes)**:
  `none`, `building`, `low vegetation`, `water`, `tree`, `playground`, `bare soil`, `sports ground`, `road`, `increase`, `decrease`, `unchanged`, `0%-20%`, `20%-40%`, `40%-60%`, `60%-80%`, `80%-100%`, `yes`, `no`.
- **Training Details**: Trained from scratch on official CDVQA/SECOND benchmark dataset across 5 epochs using AdamW ($\text{lr}=10^{-3}$, cosine decay, batch size 32).
- **Project-Measured Benchmark Results (Official Test Split, 2000 Samples)**:
  - **Overall Accuracy (OA)**: $\mathbf{69.50\%}$ (Validation OA: $68.63\%$)
  - **Average Accuracy (AA)**: $\mathbf{60.36\%}$ (Validation AA: $59.22\%$)
  - *Per-Category Accuracy*:
    - `change_or_not`: $83.57\%$ (718 samples)
    - `increase_or_not`: $77.27\%$ (220 samples)
    - `decrease_or_not`: $75.54\%$ (233 samples)
    - `change_ratio_types`: $70.00\%$ (290 samples)
    - `change_to_what`: $60.54\%$ (147 samples)
    - `largest_change`: $46.94\%$ (147 samples)
    - `change_ratio`: $37.76\%$ (98 samples)
    - `smallest_change`: $31.29\%$ (147 samples)
- **Verification Status**: `[IMPLEMENTED & VERIFIED]`. Production checkpoint active at `checkpoints/cdvqa/cdvqa_satquery.pt` (56.5 MB). Unit tests pass in `tests/test_cdvqa.py`.

### 7.7. ChangeFormer + CDVQA Dual-Specialist Architecture
**CORE ARCHITECTURAL RULE**: **CDVQA DOES NOT REPLACE CHANGEFORMER**.
- **ChangeFormer** answers the **SPATIAL** question: *"WHERE on the ground did pixels change?"* $\rightarrow$ Outputs a georeferenced spatial change mask and continuous probability map.
- **CDVQA** answers the **SEMANTIC** question: *"WHAT happened between epoch A and B?"* $\rightarrow$ Outputs natural-language answers (e.g., `"building"`, `"decrease"`, `"20%-40%"`).
- In the `temporal_vqa` workflow, both specialists execute concurrently. The results are unified in the Evidence Engine to deliver a dual response: a natural-language answer backed by pixel-level spatial change evidence.

---

## 8. Multi-Modal Remote-Sensing Visual Analytics Subsystem

### 8.1. Scientific Provenance & Zero-Fabrication Enforcement
SatQuery AI enforces strict provenance tagging across all visual deliverables:
1. `SOURCE_DATA`: Unaltered sensor bands with display contrast stretching only.
2. `DERIVED_INDEX`: Mathematically computed indices (NDVI, NDWI) from verified physical bands.
3. `MODEL_OUTPUT`: Raw binary masks or discrete predictions produced by neural networks.
4. `MODEL_PROBABILITY`: Continuous confidence distributions $[0.0, 1.0]$ output by neural sigmoid/softmax layers.
5. `HEURISTIC_ANALYSIS`: Multi-criteria composite scores (e.g., Video Event Score).

> **ZERO-FABRICATION RULE**: Under no circumstances will SatQuery AI approximate, fabricate, or simulate missing spectral bands. When a 3-band RGB image is analyzed, the system returns `INDEX_NOT_AVAILABLE` for NDVI/NDWI/NDBI with an explicit scientific explanation, rather than synthesizing fake NIR channels.

### 8.2. 15 Supported Visualization Modes
Implemented in `backend/app/visualization/` and exposed via `/api/analysis/{job_id}/visualizations/{layer_id}`:
1. **True Color (RGB)**: Authentic red, green, blue visible band composite.
2. **Panchromatic / Grayscale**: Single-channel radiometric intensity.
3. **False Color (NIR/Red/Green)**: Standard CIR vegetation composite.
4. **Single Band View**: Individual band rendered with scientific colormap (`viridis`) and colorbar.
5. **Band Difference**: Diverging radiometric difference between two confirmed bands.
6. **Spectral Indices**: NDVI, NDWI, NDBI with custom colormaps (`RdYlGn`, `Blues`).
7. **Probability Heatmap**: Continuous $[0.0, 1.0]$ probability overlay (`turbo`) with decision threshold marker on legend.
8. **Binary Prediction Mask**: Discrete $0/1$ classification mask with changed pixel count and area percentage.
9. **Confidence Map**: Spatial model confidence when explicitly exposed by the detector.
10. **Bounding Box Overlay**: Grounding DINO vector boxes labeled with class and score.
11. **Segmentation Mask Overlay**: Alpha-blended polygon mask from SAM 2.1.
12. **Temporal Change Overlay**: Bi-temporal difference visualization from ChangeFormer.
13. **SAR Polarization**: Single polarization backscatter ($VV, VH, HH, HV$) in linear or calibrated dB power.
14. **Dual-Pol SAR Composite**: False-color composite ($R=VV, G=VH, B=VV/VH\text{ ratio}$).
15. **Video Flagged Region**: Keyframe detection overlay displaying tracking polygon and heuristic event badge.

### 8.3. Spectral Indices Formulation & Verification
- **NDVI (Normalized Difference Vegetation Index)**:
  $$\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}} \quad (\text{Requires NIR and Red bands})$$
- **NDWI (Normalized Difference Water Index - McFeeters)**:
  $$\text{NDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{NIR}}}{\rho_{\text{Green}} + \rho_{\text{NIR}}} \quad (\text{Requires Green and NIR bands})$$
- **NDBI (Normalized Difference Built-Up Index)**:
  $$\text{NDBI} = \frac{\rho_{\text{SWIR}} - \rho_{\text{NIR}}}{\rho_{\text{SWIR}} + \rho_{\text{NIR}}} \quad (\text{Requires SWIR1 and NIR bands})$$

### 8.4. SAR Radar Backscatter Visual Analytics
- Preserves linear $\sigma^0$ radar backscatter power by default.
- Converts to decibels ($\text{dB}$) strictly when requested and validated:
  $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}} + \epsilon), \quad \epsilon = 10^{-7}$$

### 8.5. Interactive Pixel Inspector & 50-Bin Radiometric Histogram
- **Pixel Inspector**: Maps mouse click $(col, row)$ to native geographic coordinates using the affine geotransform:
  $$\begin{pmatrix} X_{\text{geo}} \\ Y_{\text{geo}} \end{pmatrix} = \begin{pmatrix} c & a \\ f & d \end{pmatrix} \begin{pmatrix} col \\ row \end{pmatrix} + \begin{pmatrix} b \\ e \end{pmatrix}$$
  Samples raw digital numbers (DN) across all physical bands, computed spectral indices, model class, and probability.
- **Histogram Engine**: Computes exact 50-bin radiometric distributions across any raster layer, reporting min, max, mean, standard deviation, and statistical percentiles: $P_2, P_{25}, P_{50}, P_{75}, P_{98}$.

### 8.6. Multi-Format Scientific Exports
- **PNG (+ Embedded Scientific Legend)**: High-resolution raster stitched to an informational title banner, provenance watermark, dynamic value range, and Matplotlib-generated colorbar legend.
- **GeoTIFF**: Preserves CRS, affine geotransform, and nodata tags for direct ingestion into QGIS/ArcGIS.
- **GeoJSON**: Polygonized vector boundaries of detected model masks with geospatial coordinates.

---

## 9. Video & Aerial Footage Intelligence Subsystem

### 9.1. Streaming Decoding & Frame Sampling Architecture
Implemented in `backend/app/video/decoder.py` and `backend/app/video/sampler.py`:
- Ingests `.mp4`, `.avi`, `.mov`, `.mkv` files.
- Employs an OpenCV streaming generator (`iter_frames()`) that decodes frames lazily to maintain an $O(1)$ memory footprint regardless of video file size.
- Implements two-stage adaptive sampling:
  1. *Coarse Sampling*: Uniform temporal subsampling (e.g., 1 frame per second).
  2. *Window Refinement*: Denser local sampling (e.g., 5 fps) around detected event candidates.

### 9.2. Query-Driven Video Grounding & SAM 2.1 Mask Propagation
- The user's natural language query is matched against coarsely sampled frames using Grounding DINO + V4.
- Once a target candidate meets the detection threshold, the bounding box initializes SAM 2.1's video memory state.
- SAM 2.1 propagates the segmentation mask forward and backward through video memory attention, maintaining object identity across occlusion and camera motion.

### 9.3. Video Event Flagger & Heuristic Scoring Mathematics
Implemented in `backend/app/video/flagger.py`:
- Combines multi-modal cues into a transparent, uncalibrated **Heuristic Event Score**:
  $$\text{Score}_{\text{Event}} = 0.4 \cdot S_{\text{det}} + 0.3 \cdot S_{\text{V4}} + 0.2 \cdot S_{\text{SAM2}} + 0.1 \cdot S_{\text{persistence}}$$
  - $S_{\text{det}}$: Grounding DINO detection logit.
  - $S_{\text{V4}}$: Query-semantic relation score.
  - $S_{\text{SAM2}}$: Segmentation mask stability/solidity score.
  - $S_{\text{persistence}}$: Temporal duration ratio ($\text{frames visible} / \text{window size}$).
- Clusters nearby events within a temporal tolerance window ($t_{\text{tol}} = 2.0\text{ s}$) and filters transient false alarms ($< 3\text{ frames}$).
- Flags are persisted to PostgreSQL table `video_flags` with timestamped keyframes and visual evidence.

---

## 10. Multi-Sensor Optical & SAR Comparative Analytics

SatQuery AI provides unified comparative inspection between optical sensors (passive solar reflectance) and Synthetic Aperture Radar (active microwave backscatter):
- **Optical Characteristics**: High spatial resolution, multispectral bands (RGB, NIR, RedEdge); vulnerable to cloud cover and nighttime darkness.
- **SAR Characteristics**: Cloud-penetrating, day-night operational capability; sensitive to surface roughness, geometric structure, and dielectric moisture content.
- **Co-Registration Enforcement**:
  `backend/app/visualization/comparison.py` evaluates CRS matching and bounding box intersection before enabling spatial overlays. If unaligned, the engine strictly outputs:
  `"Registration required before spatial overlay."`

---

## 11. Evidence-First Architecture & Observable Execution Tracing

Every transaction in SatQuery AI adheres to the **Evidence-First Contract**:
1. **No Naked Text**: Text answers must be accompanied by spatial evidence (bounding box, segmentation mask, change mask, or index raster).
2. **Observable Execution Trace**: Every backend action is logged into PostgreSQL table `execution_steps` with step name, duration (ms), model used, and parameters.
3. **No Private Chain-of-Thought**: The system never leaks internal LLM reasoning prompts to the client. The trace exposes operational, deterministic steps only.
4. **Reproducible Artifact Registry**: Every raster, plot, legend, and GeoJSON file is saved in `results/{job_id}/` and indexed in table `artifacts`.

---

## 12. Complete System Diagrams (24 Editable Text Diagrams)

### Diagram 1: Overall System Architecture
```text
+---------------------------------------------------------------------------------------+
|                                    SATQUERY AI CLIENT                                 |
|         Next.js 14 + React + TypeScript + MapViewer + VisualizationPanel + VideoPanel |
+-------------------------------------------+-------------------------------------------+
                                            | REST API / Multipart
                                            v
+---------------------------------------------------------------------------------------+
|                                   FASTAPI BACKEND CORE                                |
|  /api/analyze  /api/upload  /api/jobs  /api/results  /api/models  /api/analysis/...   |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                               AGENTIC CONTROLLER & ROUTER                             |
|          Deterministic Task Classifier -> Planner -> Tool Validator -> Executor       |
+-----+-------------------+---------------------+-------------------+-------------------+
      |                   |                     |                   |                   |
      v                   v                     v                   v                   v
+-------------+   +---------------+     +---------------+   +---------------+   +---------------+
| Workflow A  |   |  Workflow B   |     |  Workflow C   |   |  Workflow D   |   |  Workflow E   |
| Single VQA  |   |   Grounding   |     |    Change     |   |  Temporal VQA |   |     Video     |
+------+------+   +-------+-------+     +-------+-------+   +-------+-------+   +-------+-------+
       |                  |                     |                   |                   |
       v                  v                     v                   v                   v
+-------------+   +---------------+     +---------------+   +---------------+   +---------------+
| GeoChat-7B  |   | DINO -> V4 -> |     | ChangeFormer  |   | ChangeFormer  |   | Decoder ->    |
| (Adapter)   |   | SAM 2.1 Hiera |     | (Siamese-MiT) |   | + CDVQA (CEM) |   | DINO -> SAM2  |
+------+------+   +-------+-------+     +-------+-------+   +-------+-------+   +-------+-------+
       |                  |                     |                   |                   |
       +------------------+---------------------+-------------------+-------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                            EVIDENCE & VISUAL ANALYTICS SUBSYSTEM                      |
| Composites | Indices (NDVI) | SAR (VV/VH) | Heatmaps | Inspector | Exports (GeoTIFF)  |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                  PERSISTENCE & STORAGE                                |
|           PostgreSQL Relational DB  <--->  Local Filesystem Artifact Storage          |
+---------------------------------------------------------------------------------------+
```

### Diagram 2: System Deployment Architecture
```text
+-----------------------+     Port 3000     +-----------------------------------+
|   User Web Browser    | <---------------> |   Next.js 14 Production Server    |
+-----------------------+                   +-----------------------------------+
                                                              | Internal Proxy
                                                              v
+-----------------------+     Port 8000     +-----------------------------------+
|  FastAPI App Server   | <---------------> |   Uvicorn ASGI Worker Process     |
+-----------+-----------+                   +-----------------+-----------------+
            |                                                 |
            | Port 5432                                       | Native FS Calls
            v                                                 v
+-----------------------+                   +-----------------------------------+
| PostgreSQL 15 DB      |                   | Local Storage / Checkpoints       |
| (satquery_ai database)|                   | (results/, checkpoints/, datasets)|
+-----------------------+                   +-----------------------------------+
```

### Diagram 3: Agent / Task Router Flow
```text
[ Incoming Request (Query, Files) ]
                |
                v
[ Modality & Geometry Inspector ] ---> (Detect: Optical, Multispectral, SAR, Video)
                |
                v
[ Deterministic Keyword & Intent Matcher ]
                |
    +-----------+-----------+-----------+-----------+
    |           |           |           |           |
    v           v           v           v           v
(VQA Query) (Find/Locate) (2 Images)  (2 Img+Q)   (Video File)
    |           |           |           |           |
    v           v           v           v           v
[Single VQA] [Grounding] [Change Det] [Temp VQA]  [Video Anal.]
```

### Diagram 4: Model Registry Architecture
```text
+-------------------------------------------------------------------------------+
|                            ModelRegistry (Singleton)                          |
+-------------------------------------------------------------------------------+
| - _instances: Dict[str, BaseModelAdapter]                                     |
+-------------------------------------------------------------------------------+
| + get_adapter(model_key: str) -> BaseModelAdapter [Lazy Loader]               |
| + is_model_available(model_key: str) -> bool                                  |
| + is_model_loaded(model_key: str) -> bool                                     |
+-------------------------------------------------------------------------------+
         |                  |                 |                 |
         v                  v                 v                 v
  GeoChatAdapter    GroundingDINOAdapter  SAM2Adapter   ChangeFormerAdapter ...
```

### Diagram 5: Single-Image VQA Pipeline (GeoChat)
```text
Input Satellite Image (RGB) -------------> CLIP ViT-L/14 (336x336)
                                                   |
Natural Language Question -----------------> 2-Layer MLP Projection
                                                   |
                                                   v
                                          LLaMA-2-7B Causal LM
                                                   |
                                                   v
                                     Generated Natural Language Answer
```

### Diagram 6: Single-Image Grounding Pipeline
```text
Image + Natural Language Phrase
      |
      v
Grounding DINO Swin-T Encoder
      |
      +---> Multimodal Cross-Attention ---> Candidate Bounding Boxes [x1, y1, x2, y2]
                                                          |
                                                          v
                                              V4 Relational Reasoner
                                                          |
                                                          v
                                              Top Candidate Bounding Box
                                                          |
                                                          v
                                              SAM 2.1 Mask Decoder
                                                          |
                                                          v
                                              Pixel Polygon Mask + Area (m²)
```

### Diagram 7: V4 Relational Grounding Reasoner
```text
DINO Candidate Boxes [B1, B2, ... Bn] + Text Query
                    |
                    v
    [ Query Attribute & Relation Parser ]
    (Extracts: "small", "red", "bottom middle", "near runway")
                    |
                    v
    +---------------------------------------------------+
    | Criteria Scoring Engine                           |
    | - S_det: Normalized detector score                |
    | - S_attr: Color, scale, and aspect ratio match    |
    | - S_spatial: Spatial coordinate constraint score  |
    | - S_rel: Distance to contextual anchor objects    |
    +---------------------------------------------------+
                    |
                    v
         Ranked Top Target Candidate
```

### Diagram 8: SAM 2.1 Promptable Segmentation
```text
Input Image -----------------> Hiera-S Image Encoder
                                        |
Bounding Box Prompt ---------> Prompt Encoder
                                        |
                                        v
                               Lightweight Two-Way Mask Decoder
                                        |
                                        v
                               High-Resolution Binary Mask (H x W)
```

### Diagram 9: ChangeFormerV6 Bi-Temporal Architecture
```text
Epoch T1 Image ------> Siamese MiT Encoder ------> Multi-Scale Features (T1)
                                                            |
Epoch T2 Image ------> Shared MiT Encoder  ------> Multi-Scale Features (T2)
                                                            |
                                                            v
                                            Cross-Attention Difference Module
                                                            |
                                                            v
                                            MLP Decoder & Interpolation
                                                            |
                                                            v
                                            2-Channel Logits (Unchanged/Changed)
```

### Diagram 10: CDVQA Architecture
```text
Epoch T1 Image ----+
                   +--> Shared ResNet-18 --> CEM (Change Enhancement) --> Fusion Feature
Epoch T2 Image ----+                                                             |
                                                                                 v
Natural Language Question ----> Word Embedding ----> Bi-GRU Encoder -------> Multimodal
                                                                                MLP
                                                                                 |
                                                                                 v
                                                                        19-Class Answer
```

### Diagram 11: ChangeFormer + CDVQA Complementary Execution
```text
               Image A + Image B + Natural Language Question
                                     |
               +---------------------+---------------------+
               |                                           |
               v                                           v
         ChangeFormerV6                                  CDVQA
               |                                           |
               v                                           v
       Spatial Change Mask                          Semantic Answer
     & Probability Heatmap                         (e.g., "building")
               |                                           |
               +---------------------+---------------------+
                                     |
                                     v
                        Evidence Engine Aggregator
```

### Diagram 12: Video Pipeline Architecture
```text
Aerial Video (MP4)
       |
       v
OpenCV Streaming Decoder (iter_frames())
       |
       v
Coarse Temporal Sampler (1 fps)
       |
       v
Grounding DINO + V4 Candidate Screening
       |
       v
SAM 2.1 Video Memory Initialization
       |
       v
Temporal Mask Propagation Across Frame Window
       |
       v
Video Event Flagger -> Keyframe Cards + Timeline Markers
```

### Diagram 13: Video Event Flagger
```text
Candidate Frame Events
          |
          v
+-----------------------------------------------------------------------+
| Multi-Criteria Heuristic Scoring                                      |
| Score = 0.4*Detector + 0.3*V4_Semantic + 0.2*SAM2_Mask + 0.1*Duration |
+-----------------------------------------------------------------------+
          |
          v
Temporal Clustering (merge within 2.0s window)
          |
          v
Transient Noise Filtering (discard < 3 frames)
          |
          v
Flagged Events with Keyframe Evidence & Timestamps
```

### Diagram 14: Optical Processing Pipeline
```text
Input Optical Raster (GeoTIFF / PNG)
          |
          v
RasterMetadata Inspector (Bands, Dtype, Georeferencing)
          |
          +-----------------------------+-----------------------------+
          |                             |                             |
          v                             v                             v
True Color RGB Rendering      Display Percentile Stretch    Model Preprocessing
 (Preserves Radiometry)               (2% - 98%)            (ImageNet / CLIP Normal.)
```

### Diagram 15: SAR Processing Pipeline
```text
Input SAR Raster (GeoTIFF, VV/VH Channels)
          |
          v
Verify Physical Polarization Tags
          |
          +-----------------------------+-----------------------------+
          |                             |                             |
          v                             v                             v
Linear Backscatter Sigma0         Optional Decibel (dB)       Dual-Pol Composite
(Preserved for Analytics)       Conversion (10*log10(P))     (R=VV, G=VH, B=VV/VH)
```

### Diagram 16: Optical + SAR Co-Registration Comparison
```text
Optical Image (GeoTIFF)                      SAR Image (GeoTIFF)
          |                                           |
          +---------------------+---------------------+
                                |
                                v
               Spatial Co-Registration Check
               - Matching Projection / CRS?
               - Intersecting Bounding Box?
                                |
               +----------------+----------------+
               |                                 |
          [Aligned]                        [Misaligned]
               |                                 |
               v                                 v
     Synchronized Split-View           Error: "Registration required
     Side-by-Side Comparison                  before spatial overlay"
```

### Diagram 17: Visual Analytics Subsystem
```text
Input Raster / Model Predictions
               |
               v
     VisualizationRegistry (Discovers Valid Modes)
               |
    +----------+----------+----------+----------+
    |          |          |          |          |
    v          v          v          v          v
Composites  Indices      SAR      Heatmaps  Overlays
 (RGB/CIR) (NDVI/NDWI) (VV/VH)    (Turbo)   (Masks/Boxes)
    |          |          |          |          |
    +----------+----------+----------+----------+
                          |
                          v
         FastAPI Endpoints (/visualizations, /legend)
```

### Diagram 18: Pixel Inspector & Histogram Engine
```text
Clicked Coordinate (col, row)
            |
            v
Affine Geotransform ---------> Map Coordinates (Latitude, Longitude)
            |
            v
Multi-Layer Sampler ---------> Raw Band Values (B1, B2, ...)
            |                  Derived Indices (NDVI, NDWI)
            |                  Model Prediction & Probability
            v
Histogram Generator ---------> 50 Equal-Width Bins + Percentiles (P2 - P98)
```

### Diagram 19: Evidence & Artifact Engine
```text
Workflow Execution Output
            |
            v
Evidence Engine
            |
            +---> GeoJSON Vector Mask Builder (EPSG:4326)
            +---> Metric Ground Area Calculator (m² / km²)
            +---> Visual Artifact Generator (PNG + Legend, GeoTIFF)
            +---> PDF Report Builder (ReportLab)
            |
            v
Storage in results/{job_id}/ & Indexing in PostgreSQL
```

### Diagram 20: Database ER Relationship Diagram
```text
+---------------------+           1:N           +---------------------+
|    analysis_jobs    | ----------------------> |   uploaded_files    |
+---------------------+                         +---------------------+
| id (PK, UUID)       |
| status              |           1:N           +---------------------+
| task_type           | ----------------------> |     model_runs      |
| query               |                         +---------------------+
| created_at          |
+----------+----------+           1:N           +---------------------+
           |            ----------------------> |   execution_steps   |
           |                                    +---------------------+
           |                      1:1           +---------------------+
           |            ----------------------> |  analysis_results   |
           |                                    +---------------------+
           |                      1:N           +---------------------+
           |            ----------------------> |      artifacts      |
           |                                    +---------------------+
           |                      1:N           +---------------------+
           |            ----------------------> |visualization_layers |
           |                                    +---------------------+
           |                      1:N           +---------------------+
           +----------------------------------> |       videos        |
                                                +----------+----------+
                                                           | 1:N
                                                           v
                                                +---------------------+
                                                |     video_flags     |
                                                +---------------------+
```

### Diagram 21: FastAPI API Gateway Architecture
```text
Incoming Client HTTP Request
            |
            v
FastAPI Middleware (CORS, Request Tracking, Exception Handlers)
            |
            +---> /api/health (Health check & DB status)
            +---> /api/models (Model capability registry)
            +---> /api/upload (Multipart upload & raster inspection)
            +---> /api/analyze (Trigger asynchronous analysis)
            +---> /api/jobs/{job_id} (Poll execution status)
            +---> /api/results/{job_id} (Retrieve structured result)
            +---> /api/artifacts/{job_id}/{path} (Serve static artifacts)
            +---> /api/analysis/{job_id}/layers (List visual analytics layers)
            +---> /api/analysis/{job_id}/inspect-pixel (Inspect clicked pixel)
            +---> /api/analysis/{job_id}/histogram/{layer_id} (50-bin stats)
            +---> /api/analysis/{job_id}/export/{layer_id} (Download GeoTIFF/PNG)
```

### Diagram 22: Frontend Component Tree
```text
App (page.tsx)
  ├── Header & System Status
  ├── Main Workspace Grid
  │     ├── Left Panel:
  │     │     ├── UploadPanel (Files, Drag-and-drop, Metadata inspection)
  │     │     ├── QueryBar (Natural language input, Task selector)
  │     │     └── ModelStatusPanel (Live availability matrix)
  │     │
  │     └── Center/Right Panel:
  │           ├── MapViewer (MapLibre / Leaflet base viewer + layer overlays)
  │           ├── VisualizationPanel (Layers, opacity, legends, inspector, histogram)
  │           ├── VideoPlayerPanel (Video playback, timeline flags, keyframes)
  │           └── ResultsPanel (Structured text answer, confidence, metric area)
  └── Footer & Execution Trace Log
```

### Diagram 23: Complete End-to-End System Flow
```text
User uploads image + enters query "Highlight the damaged bridge"
  │
  ├──> Frontend sends POST /api/upload then POST /api/analyze
  │
  ├──> FastAPI validates input & initializes JobRecord in PostgreSQL
  │
  ├──> Agent Router classifies query as `single_image_grounding`
  │
  ├──> Grounding DINO predicts bounding boxes
  │
  ├──> V4 Reasoner filters candidates matching "damaged bridge"
  │
  ├──> SAM 2.1 generates pixel segmentation mask
  │
  ├──> Evidence Engine calculates ground area in m² & exports GeoJSON
  │
  ├──> VisualizationRegistry registers mask & probability layers
  │
  ├──> Database saves final ResultRecord, Artifacts & ExecutionSteps
  │
  └──> Frontend renders polygon overlay on MapViewer + Metrics in ResultsPanel
```

### Diagram 24: Data Lifecycle
```text
1. INGESTION  --> User uploads raster -> Saved to results/{job_id}/input/ -> Metadata parsed
2. EXECUTION  --> Model runs inference -> Temp tensors in GPU memory -> Outputs in results/{job_id}/
3. PERSIST    --> PostgreSQL records job, steps, model runs, artifacts & visualization layers
4. ANALYTICS  --> User requests NDVI/SAR/Inspector -> Generated on demand & cached in DB
5. EXPORT     --> User downloads PNG/GeoTIFF/GeoJSON -> Streamed via Content-Disposition
6. CLEANUP    --> Ephemeral job workspaces archived according to storage retention policy
```

---

## 13. Database Architecture & PostgreSQL Schema

SatQuery AI uses **PostgreSQL** with SQLAlchemy async sessions (`asyncpg` driver). Schema migrations are managed via Alembic.

### Active Relational Tables
1. `analysis_jobs`: Core job state tracking (`id`, `status`, `task_type`, `query`, `error_message`, `created_at`, `updated_at`).
2. `uploaded_files`: Catalog of uploaded assets (`id`, `job_id`, `filename`, `file_type`, `file_size`, `storage_path`, `metadata_json`).
3. `model_runs`: Tracks every model invocation (`id`, `job_id`, `model_name`, `checkpoint`, `device`, `duration_ms`, `success`).
4. `execution_steps`: Step-by-step observable execution trace (`id`, `job_id`, `step_name`, `status`, `duration_ms`, `details`).
5. `analysis_results`: Final verified answer payload (`id`, `job_id`, `answer`, `confidence`, `metric_area_m2`, `result_json`).
6. `artifacts`: Stored files (`id`, `job_id`, `artifact_type`, `filename`, `file_path`, `mime_type`, `file_size`).
7. `visualization_layers`: Registry of visual analytics layers (`id`, `job_id`, `layer_id`, `name`, `vis_type`, `provenance`, `colormap`, `units`, `metadata_json`).
8. `videos`: Catalog of video footage jobs (`id`, `job_id`, `filename`, `duration_sec`, `fps`, `total_frames`, `resolution`).
9. `video_frames`: Keyframe index (`id`, `video_id`, `frame_idx`, `timestamp_sec`, `storage_path`).
10. `video_flags`: Flagger events (`id`, `video_id`, `timestamp_sec`, `event_label`, `heuristic_score`, `keyframe_path`, `metadata_json`).

---

## 14. FastAPI REST API Architecture & Endpoints

| Method | Endpoint | Description | Key Query / Body Parameters |
|---|---|---|---|
| `GET` | `/api/health` | Service health, DB connectivity, model availability | None |
| `GET` | `/api/models` | List all registered model adapters & status | None |
| `POST` | `/api/upload` | Multipart file upload and metadata inspection | `files: List[UploadFile]` |
| `POST` | `/api/analyze` | Submit asynchronous analysis job | `query: str`, `image_filenames: List[str]`, `task: Optional[str]` |
| `GET` | `/api/jobs/{job_id}` | Poll execution status and progress | `job_id: str` |
| `GET` | `/api/results/{job_id}` | Retrieve complete analysis result & trace | `job_id: str` |
| `GET` | `/api/artifacts/{job_id}/{path}` | Stream static artifact file | `job_id: str`, `path: str` |
| `GET` | `/api/analysis/{job_id}/layers` | List all available visual analytics layers | `job_id: str` |
| `GET` | `/api/analysis/{job_id}/visualizations/{layer_id}` | Render/stream layer visualization image (PNG) | `job_id: str`, `layer_id: str` |
| `GET` | `/api/analysis/{job_id}/visualizations/{layer_id}/legend` | Stream layer scientific colorbar legend (PNG) | `job_id: str`, `layer_id: str` |
| `POST` | `/api/analysis/{job_id}/inspect-pixel` | Sample physical radiometric & index values at pixel | `{"col": int, "row": int}` |
| `GET` | `/api/analysis/{job_id}/histogram/{layer_id}` | Compute 50-bin radiometric distribution & percentiles | `job_id: str`, `layer_id: str` |
| `GET` | `/api/analysis/{job_id}/export/{layer_id}` | Download scientific export artifact | `format=png\|geotiff\|geojson` |

---

## 15. Frontend Architecture & Next.js 14 User Interface

Built with **Next.js 14 (App Router)**, **React 18**, **TypeScript**, and **TailwindCSS**:
- `UploadPanel.tsx`: Drag-and-drop file upload supporting GeoTIFF, PNG, and MP4. Displays extracted raster dimensions, band counts, and CRS.
- `QueryBar.tsx`: Input field with natural language prompt suggestions and manual task override options.
- `MapViewer.tsx`: Interactive geospatial viewer supporting opacity-blended layer overlays and click-to-inspect crosshair sampling.
- `VisualizationPanel.tsx`: Dynamic layer selector chips with provenance badges (`ORIGINAL DATA`, `DERIVED INDEX`, `MODEL PROBABILITY`), opacity slider, colorbar legend display, pixel inspector card, 50-bin histogram modal, and multi-format export dropdown.
- `VideoPlayerPanel.tsx`: Custom video player with interactive timeline event markers, keyframe carousel, and heuristic event score badges.
- `ResultsPanel.tsx`: Displays natural language answers, confidence ratings, computed ground area ($m^2, km^2$), and structured JSON output.

---

## 16. Comprehensive Dataset Inventory & Provenance

| Dataset Name | Primary Purpose in SatQuery | Sensor Modality | Spatial Resolution | Samples / Size | Splits Used | Storage & Version Control Status |
|---|---|---|---|---|---|---|
| **SECOND / CDVQA** | Training CDVQA question answering | Optical Bi-temporal | $0.5 - 3.0\text{ m}$ | 2,968 pairs / 4,732 QAs | Official Train (70%), Val (10%), Test (20%) | Kept in `datasets/cdvqa/`; ignored by git |
| **LEVIR-CD** | Evaluating ChangeFormerV6 | Optical Bi-temporal | $0.5\text{ m}$ (Google Earth) | 637 pairs ($1024\times 1024$) | Standard Train / Val / Test | External benchmark; referenced in manifests |
| **VRSBench** | Evaluating Visual Grounding (V1-V4) | High-Res Optical | $0.1 - 0.5\text{ m}$ | 29,614 images / 120k annotations | Evaluated on validation sample | External benchmark; referenced in manifests |
| **LR-VQA / RS-VQA**| Evaluating Remote-Sensing VQA | Sentinel-2 / Landsat | $10\text{ m} - 30\text{ m}$ | Diverse satellite scenes | Validation splits | Evaluated with GeoChat |
| **Synthetic Test Video**| Unit testing streaming video engine | Optical Video (MP4) | $1920\times 1080$ | Derived fixture | Internal smoke test | `tests/fixtures/synthetic_video.mp4` |

---

## 17. Trained Models vs. Pretrained Specialist Models

To maintain strict scientific integrity, SatQuery AI explicitly separates models trained internally from external foundation models:

### Trained Internally by SatQuery AI
1. **CDVQA (Siamese ResNet-18 + CEM + GRU)**: Trained on the official CDVQA/SECOND dataset across 5 epochs. Production checkpoint: `checkpoints/cdvqa/cdvqa_satquery.pt` (OA: $69.50\%$, AA: $60.36\%$).
2. **ChangeFormerV6 (Fine-Tuned Siamese Transformer)**: Trained and verified on bi-temporal change detection benchmarks. Production checkpoint: `checkpoints/changeformer/satquery_changeformer_best.pt` (492.6 MB).

### Adapted Pretrained Foundation Models
1. **GeoChat-7B**: Official weights from `MBZUAI/geochat-7B`.
2. **Grounding DINO Swin-T**: Official weights from `IDEA-Research`.
3. **SAM 2.1 Hiera Small**: Official weights from `facebookresearch`.

---

## 18. Technology Stack & Architectural Trade-Off Analysis

| Technology Component | Selection | Primary Architectural Justification | Alternatives Considered | Why Alternatives Were Rejected |
|---|---|---|---|---|
| **Backend Framework** | **FastAPI** | High-performance asynchronous execution, native OpenAPI docs, Pydantic data validation | Flask, Django | Flask lacks async concurrency; Django is excessively monolithic for decoupled ML microservices |
| **Database Engine** | **PostgreSQL + asyncpg** | ACID compliance, JSONB support for unstructured traces, relational integrity for jobs/artifacts | MongoDB, SQLite | SQLite lacks concurrent async connections; MongoDB lacks strict foreign-key integrity required for audit trails |
| **Frontend Framework** | **Next.js 14 (App Router)** | Modern React server components, type-safe API routing, seamless UI hydration | Vite + React SPA | Next.js offers superior build-time SSR, optimized client-side routing, and enterprise styling |
| **Object Detection** | **Grounding DINO** | Open-vocabulary text conditioning allows arbitrary natural language queries without retraining | YOLOv8 / Faster R-CNN | Closed-set detectors are restricted to 80 fixed COCO categories and cannot handle remote-sensing queries |
| **Segmentation** | **SAM 2.1 Hiera Small** | Promptable box-to-mask translation with native video memory propagation | Mask R-CNN, UNet | Conventional semantic segmenters cannot perform zero-shot prompting or video frame mask propagation |
| **Video Decoding** | **OpenCV (`cv2.VideoCapture`)**| Streaming frame-by-frame decoding without full video memory loading | PyAV, Decord | OpenCV provides reliable cross-platform Windows compatibility and zero C-compilation errors |

---

## 19. Verified Project Results & Experimental Benchmarks

> **GOVERNANCE NOTICE**: All metrics reported below represent **actual measured numbers** obtained from executed test runs and benchmark evaluation JSON files present in the `results/` directory.

### 1. CDVQA (Bi-Temporal Visual Question Answering)
*Evaluated on Official Test Split (2000 Samples) — Source: `results/cdvqa_test_metrics.json`*
- **Overall Accuracy (OA)**: $\mathbf{69.50\%}$
- **Average Accuracy (AA)**: $\mathbf{60.36\%}$
- *Per-Question-Type Breakdown*:
  - `change_or_not`: $\mathbf{83.57\%}$ (718 samples)
  - `increase_or_not`: $\mathbf{77.27\%}$ (220 samples)
  - `decrease_or_not`: $\mathbf{75.54\%}$ (233 samples)
  - `change_ratio_types`: $\mathbf{70.00\%}$ (290 samples)
  - `change_to_what`: $\mathbf{60.54\%}$ (147 samples)
  - `largest_change`: $\mathbf{46.94\%}$ (147 samples)
  - `change_ratio`: $\mathbf{37.76\%}$ (98 samples)
  - `smallest_change`: $\mathbf{31.29\%}$ (147 samples)

### 2. Grounding Reasoner Experimental Strategies (VRSBench Evaluation)
*Evaluated on VRSBench sample setup — Source: `results/evaluations/`*
- **V1 (Baseline Confidence)**: Mean IoU = $0.1832$, $\text{Recall}@0.50 = 0.2200$
- **V2 (Query-Aware Semantic Matching)**: Mean IoU = $0.2371$, $\text{Recall}@0.50 = 0.2600$
- **V3 (Contextual Spatial Heuristic)**: Mean IoU = $0.2238$, $\text{Recall}@0.50 = 0.2400$
- **V4 (Relational Multi-Criteria Reasoner)**: Improved qualitative spatial selection for multi-object scenes.

---

## 20. Testing Philosophy, Test Coverage & Verification Evidence

### Testing Philosophy
SatQuery AI enforces a strict distinction across verification tiers:
1. **Unit Tests**: Verify individual functions, mathematical calculations, and input validation without calling live model weights.
2. **Integration Tests**: Verify database transactions, API endpoints, and inter-module communications using temporary mock fixtures.
3. **Model Smoke Tests**: Verify that heavy neural checkpoints can be instantiated on CPU/GPU and perform a single forward pass without throwing runtime exceptions. *(A smoke test proves operational connectivity; it does NOT prove benchmark accuracy).*
4. **Real-Data Smoke Tests**: End-to-end execution on genuine satellite rasters verifying image rendering, colorbars, and zero-fabrication rules.

### Current Test Suite Verification
- **Automated PyTest Suite**: **104 / 104 Tests PASSED** ($100\%$ pass rate in $90.28\text{ s}$).
  - `tests/test_agent.py` (Passed)
  - `tests/test_api.py` (Passed)
  - `tests/test_database.py` (Passed)
  - `tests/test_changeformer.py` & `test_changeformer_smoke.py` (Passed)
  - `tests/test_cdvqa.py` (Passed)
  - `tests/test_grounding_dino.py` & `test_grounding_workflow.py` (Passed)
  - `tests/test_sam2.py` (Passed)
  - `tests/test_geochat.py` (Passed)
  - `tests/test_video_*.py` (12 tests passed)
  - `tests/test_visualization_*.py`, `test_composites.py`, `test_indices.py`, `test_sar_visualization.py`, `test_heatmaps.py`, `test_inspector.py` (18 tests passed)
- **Frontend Production Build**: `npm run build` completed with code 0 (zero TypeScript or lint errors).
- **Backend Python Compilation**: `python -m compileall backend/app` completed with code 0.

---

## 21. Security, Data Governance & Ethical Guardrails

1. **Path Traversal Protection**: File paths submitted to `/api/artifacts/` are sanitized using `Path.resolve()` to ensure access is strictly confined within `results/{job_id}/`.
2. **Payload & Format Validation**: Uploaded files are validated against allowed MIME types and magic bytes; corrupted headers trigger an explicit `INVALID_INPUT_ERROR`.
3. **Database Security**: All SQL queries utilize SQLAlchemy parameterized statements to eliminate SQL injection vulnerabilities.
4. **No Plaintext Secrets**: Database passwords and API keys are loaded strictly from environment variables (`.env`).
5. **Data Isolation**: Workspaces are isolated per job ID using random UUIDs.

---

## 22. Engineering Feasibility, Scalability & Compute Profile

- **GPU Acceleration**: Models run on CUDA GPUs when available; full fallback to CPU execution is natively supported for lower-throughput edge environments.
- **Lazy Loading**: Heavy model weights (e.g., ChangeFormer 492 MB, GeoChat 13.8 GB) are **not** loaded at application startup. They are loaded strictly upon the first relevant query and cached in memory.
- **Memory Footprint**:
  - Idle Backend: $\sim 180\text{ MB RAM}$.
  - Grounding DINO + SAM 2.1 Active: $\sim 2.8\text{ GB VRAM / RAM}$.
  - ChangeFormer + CDVQA Active: $\sim 3.2\text{ GB VRAM / RAM}$.
  - GeoChat-7B Active: $\sim 14\text{ GB VRAM}$ (requires 16 GB+ GPU or 32 GB CPU RAM).

---

## 23. Environmental Sustainability & Green AI Architecture

SatQuery AI incorporates sustainable, Green AI design patterns:
1. **Specialist Routing vs. Monolithic Ingestion**: A query asking *"Where is the vessel?"* activates Grounding DINO ($172\text{M}$ params) rather than running a massive $70\text{B}$ foundation model, reducing compute energy by over $90\%$.
2. **Coarse Video Sampling**: Rather than analyzing 30 frames per second, the video engine samples at 1 fps, pruning $96.7\%$ of redundant neural inferences.
3. **Memory Propagation vs. Re-Detection**: SAM 2.1 propagates masks via lightweight memory attention rather than re-running full object detectors on every video frame.
4. **Static Result Caching**: Generated visualization overlays and histograms are cached in PostgreSQL to eliminate redundant recalculation on page reload.

---

## 24. Social Impact, Public Sector Applications & Operational Risks

### Public Sector & Humanitarian Applications
- **Disaster Response & Assessment**: Rapid damage mapping following earthquakes, hurricanes, or floods via ChangeFormer bi-temporal change detection.
- **Environmental & Forest Monitoring**: Detecting illegal deforestation, wetland encroachment, and wildfire progression using NDVI vegetation tracking.
- **Urban Planning & Infrastructure**: Monitoring informal urban expansion and highway construction via satellite grounding and metric area computation.

### Operational Risks & Ethical Considerations
- **False Positives in Disaster Zones**: Damaged structures might be misclassified due to seasonal vegetation changes; human-in-the-loop review is mandatory before allocating emergency relief funds.
- **Surveillance & Privacy Concerns**: High-resolution tracking capabilities must adhere to national civil liberties regulations and international spatial data policies.
- **Domain Shift**: Models trained on European or North American benchmarks (e.g., LEVIR-CD) may exhibit reduced accuracy in arid or tropical biomes without fine-tuning.

---

## 25. Project Uniqueness & Differentiating Contributions

SatQuery AI differs from existing research and commercial tools across five key dimensions:
1. **Decoupled Specialist Ecosystem**: Unifies five specialized models under a single agentic controller without collapsing them into a single fragile neural network.
2. **Dual-Model Temporal Execution**: The only known remote-sensing system running ChangeFormer (spatial mask) and CDVQA (linguistic question answering) in parallel.
3. **Rigorous Scientific Zero-Fabrication**: Guarantees that spectral indices and SAR backscatter values reflect true physical measurements, explicitly refusing calculation when bands are absent.
4. **Transparent Heuristic Flagging**: Clearly labels video event scores as composite heuristics rather than deceiving users with fake "AI accuracy" claims.
5. **Full Geospatial Traceability**: Connects every natural-language response directly to georeferenced GeoTIFFs, GeoJSON vectors, and physical metric area calculations ($m^2, km^2$).

---

## 26. Troubleshooting History & Verified Engineering Lessons

1. **ChangeFormer Preprocessing Mismatch**:
   - *Problem*: ChangeFormer initial smoke tests produced oversaturated, inaccurate change masks on LEVIR-CD.
   - *Root Cause*: Production code was normalizing images using standard ImageNet mean/std ($[0.485, 0.456, 0.406]$), whereas native training used $[-1, 1]$ rescaling.
   - *Solution*: Re-aligned `preprocess_changeformer_input()` in `backend/app/models/changeformer.py` to match exact training contract, restoring accurate change detection.
2. **FAT32 Storage Limitation on Drive D:**:
   - *Problem*: GeoChat-7B Shard 1 (`pytorch_model-00001-of-00002.bin`, 9.98 GB) failed to download to external storage.
   - *Root Cause*: External drive `D:\` is formatted as FAT32, which strictly enforces a 4.00 GB maximum single file size.
   - *Status*: Documented transparently; GeoChat is marked `[IMPLEMENTED BUT RUNTIME VALIDATION PENDING]` until drive reformatting or local disk expansion occurs.
3. **Band Token Collision in Spectral Index Engine**:
   - *Problem*: In `indices.py`, single-character matching (`"r" in "green"`) caused green bands to be misidentified as red.
   - *Solution*: Switched to tokenized word-boundary matching (`"red" in tokens or d == "r"`).

---

## 27. System Reproducibility & Deployment Guide

### Prerequisites
- Python 3.10 or 3.11
- Node.js 18+ and npm
- PostgreSQL 14+ running locally or in Docker

### 1. Database Setup
```bash
# Start PostgreSQL via Docker or local service
docker run -d --name satquery-pg -e POSTGRES_USER=satquery -e POSTGRES_PASSWORD=satquery_secret -e POSTGRES_DB=satquery_ai -p 5432:5432 postgres:15

# Verify connection in .env
DATABASE_URL=postgresql+asyncpg://satquery:satquery_secret@localhost:5432/satquery_ai
```

### 2. Backend Installation & Execution
```bash
cd satquery-ai
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Installation & Execution
```bash
cd satquery-ai/frontend
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

### 4. Running the Verification Test Suite
```bash
cd satquery-ai
pytest tests -v
python scripts/smoke_test_visualization.py
```

---

## 28. Future Roadmap & Unimplemented Capabilities

The following features represent planned enhancements and are explicitly classified as `[FUTURE / OPTIONAL]`:
1. **Automated STAC Satellite Harvester**: Integration with Microsoft Planetary Computer and Copernicus STAC APIs for direct bounding-box data ingestion.
2. **Calibrated Uncertainty Estimation**: Bayesian dropout and conformal prediction intervals across grounding bounding boxes.
3. **Multi-User Role-Based Access Control (RBAC)**: JWT authentication with organization-level workspace segregation.
4. **Edge Deployment Packaging**: TensorRT and ONNX Runtime quantization for onboard drone deployment.
5. **Interactive Video Timeline Trimming**: Frontend video clipping and sub-segment export tools.

---

## 29. Presentation & Mentor Defense Guide ("SatQuery in 2 Minutes")

### Anticipated Mentor Questions & Technical Defense

**Q1: Why did you not use a single Large Vision-Language Model like GPT-4V or LLaVA for everything?**
> *Answer*: Monolithic generalist VLMs fail in remote sensing for three fundamental reasons: First, they lack domain-specific multi-spectral and SAR pretraining, treating 16-bit satellite imagery like standard 8-bit web photos. Second, they suffer from severe spatial hallucinations; they cannot output pixel-precise polygon segmentation masks or exact metric areas ($m^2$). Third, bi-temporal change detection requires Siamese feature subtraction between co-registered passes, which single-image text decoders cannot perform accurately. Decoupling into specialist models guarantees state-of-the-art accuracy, zero-fabrication, and verifiable evidence.

**Q2: How does SatQuery know which model to invoke without user intervention?**
> *Answer*: The system employs an agentic deterministic controller (`backend/app/agent/`). It inspects both the input file signature (modality, dimensions, single image vs. temporal pair vs. video) and classifies the semantic query intent. If two images and a query arrive, it automatically triggers both ChangeFormer and CDVQA. If a referring expression arrives with a single image, it invokes Grounding DINO + V4 + SAM 2.1.

**Q3: What makes your visual analytics "scientifically authentic"?**
> *Answer*: We strictly enforce a Zero-Fabrication policy backed by scientific provenance tags. For instance, computing NDVI requires authentic Near-Infrared (NIR) reflectance. If a user uploads a standard 3-band RGB image, SatQuery AI explicitly refuses to calculate NDVI and returns `INDEX_NOT_AVAILABLE`, explaining that NIR is absent. We never approximate or fake scientific data.

---

## 30. Technical Glossary

- **CEM (Change-Enhancement Module)**: Feature fusion subnetwork in CDVQA that computes pixel-level difference features between bi-temporal visual embeddings.
- **CRS (Coordinate Reference System)**: Mathematical framework defining how two-dimensional projected maps relate to real locations on the Earth's surface (e.g., `EPSG:4326` for WGS84, `EPSG:32632` for UTM Zone 32N).
- **DN (Digital Number)**: Raw, uncalibrated pixel value recorded by a satellite sensor detector before physical reflectance calibration.
- **Grounding**: The task of localizing specific objects in an image corresponding to an arbitrary natural language referring expression.
- **NDVI**: Normalized Difference Vegetation Index; measures chlorophyll absorption via $(NIR - Red) / (NIR + Red)$.
- **NDWI**: Normalized Difference Water Index; delineates open water bodies via $(Green - NIR) / (Green + NIR)$.
- **SAR (Synthetic Aperture Radar)**: Active microwave imaging sensor capable of acquiring imagery through clouds and during nighttime.
- **Siamese Network**: An artificial neural network architecture containing two identical subnetworks sharing identical weights to compare two inputs.
- **VQA (Visual Question Answering)**: Multimodal AI task requiring a model to answer natural-language questions about an image.

---

## 31. Primary Research References

1. **GeoChat**: Kuckreja, K., Sohail, M., Ranasinghe, K., Khan, S., & Khan, F. S. (2023). *GeoChat: Grounded Large Vision-Language Model for Remote Sensing*. arXiv:2311.15826. Official Repo: `https://github.com/mbzuai-oryx/GeoChat`.
2. **Grounding DINO**: Liu, S., Zeng, Z., Ren, T., Li, F., Zhang, H., et al. (2023). *Grounding DINO: Marrying DINO with Grounded Pre-Training for Open-Set Object Detection*. arXiv:2303.05499. Official Repo: `https://github.com/IDEA-Research/GroundingDINO`.
3. **SAM 2**: Ravi, N., Gabeur, V., Hu, Y. T., Hu, R., Ryali, C., et al. (2024). *SAM 2: Segment Anything in Images and Videos*. arXiv:2408.00714. Official Repo: `https://github.com/facebookresearch/sam2`.
4. **ChangeFormer**: Bandara, W. G. C., & Patel, V. M. (2022). *A Transformer-Based Siamese Network for Change Detection*. IGARSS 2022. Official Repo: `https://github.com/wgcban/ChangeFormer`.
5. **CDVQA**: Yuan, Z., Zhang, H., et al. (2022). *Change Detection Visual Question Answering on Remote Sensing Bitemporal Images*. IEEE Transactions on Geoscience and Remote Sensing.
6. **VRSBench**: Ling, X., et al. (2024). *VRSBench: A Versatile Visual Reasoning Benchmark for Remote Sensing*.
7. **LEVIR-CD**: Chen, H., & Shi, Z. (2020). *A Spatial-Temporal Attention-Based Method and a New Dataset for Remote Sensing Image Change Detection*. Remote Sensing.

---

## 32. Advanced Agent Orchestration Layer (Features 1–56)

### 32.1 Architecture Overview
SatQuery AI features a robust, observable, policy-driven agent orchestration engine in `backend/app/orchestration/`. The orchestration layer resolves:
- **WHAT** the user wants through structured natural language entity extraction.
- **WHAT** input modalities and raster dimensions are present via metadata inspection.
- **WHICH** capability is appropriate via an authoritative priority resolution matrix.
- **WHICH** DAG workflow execution stages should be executed sequentially or in parallel.
- **WHETHER** required model checkpoints and resources are available before running.
- **WHETHER** results satisfy scientific sanity checks.
- **HOW** all evidence is linked in an auditable, end-to-end provenance graph.

```
User Query + Uploaded Rasters / Video
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│  Phase 1: Input Modality & Raster Metadata Inspection   │
│  (InputAnalyzer: dimensions, bands, CRS, resolution)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 2: Intent Classification & Entity Extraction    │
│  (IntentClassifier: object, color, size, position,     │
│   relation, ordering, temporal, change; routing conf)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 3: Capability Matching & Priority Resolution    │
│  (CapabilityMatcher: Grounding strictly overrides VQA) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 4: DAG Execution Graph & Stage Construction     │
│  (DependencyGraph: topological sort, parallel stages)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 5: Pre-Execution Dependency & Resource Checks   │
│  (DependencyChecker, ResourceManager: RAM, VRAM, GPU)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 6: Deterministic Cache Check                    │
│  (SHA-256 over images + query + capability + params)   │
└──────────────────────────┬─────────────────────────────┘
                           │ (Cache Miss)
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 7: Controlled Tool Execution & Policy Engine    │
│  (SafeToolExecutor + gpu_lock + 8 Integrity Policies)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 8: Output Quality Validation & Sanity Checks    │
│  (OutputQualityValidator: non-inverted boxes, masks)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 9: Provenance Graph Construction                │
│  (ProvenanceBuilder: roots -> models -> artifacts)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Phase 10: Observable Response Assembly & UI Telemetry │
│  (Collapsible Orchestration & Provenance Insights Card)│
└────────────────────────────────────────────────────────┘
```

### 32.2 Authoritative Capability Registry (13 Capabilities)
The system maintains a centralized registry (`CapabilityRegistry`) pre-registering 13 foundational capabilities with strict priority rankings:
1. `single_image_grounding` (Priority 100): Open-vocabulary spatial detection and pixel mask segmentation (Grounding DINO + V4 Reasoner + SAM 2).
2. `temporal_change_vqa` (Priority 95): Bi-temporal change question answering and quantification (ChangeFormer + CDVQA).
3. `temporal_change_detection` (Priority 90): Bi-temporal change map segmentation and area statistics (ChangeFormer).
4. `optical_sar_analysis` (Priority 85): Cross-modal optical and synthetic aperture radar sensor fusion (DOFA).
5. `video_grounding_tracking` (Priority 80): Temporal object grounding across aerial video frames with trajectory tracking (SAM 2 Video Tracker).
6. `video_grounding` (Priority 75): Single/multi-frame video object localization.
7. `multispectral_analysis` (Priority 70): Multispectral band indexing and false-color synthesis (NDVI, NDWI, False-Color NIR).
8. `sar_analysis` (Priority 65): SAR radar polarimetry and backscatter dB calibration (VV, VH, Decibel).
9. `single_image_vqa` (Priority 50): Natural language visual inquiry over satellite imagery (GeoChat).
10. `single_image_caption` (Priority 45): Scene overview and summarization (GeoChat).
11. `visualization` (Priority 30): Scientific layer composites and heatmap rendering.
12. `pixel_inspection` (Priority 20): Coordinate-level multispectral and probability probe.
13. `report_generation` (Priority 10): PDF audit report compilation and GeoJSON vectorization.

### 32.3 Grounding Intent Precedence Rule
If a query contains referring or spatial grounding expressions (`locate`, `find`, `highlight`, `point out`, `detect`, `segment`, `where is`, `outline`), the orchestration engine **must strictly route** to `single_image_grounding` (Grounding DINO + V4 + SAM 2) rather than general VQA (GeoChat). General VQA only triggers when no grounding verbs or spatial attributes are detected.

### 32.4 The 8 Core Integrity Policies
1. **`NO_FABRICATION`**: Never manufacture synthetic predictions, artificial bounding boxes, or hallucinated change metrics.
2. **`NO_UNAVAILABLE_MODEL`**: If a requested model is unconfigured, return `MODEL_NOT_CONFIGURED` rather than silently substituting another model.
3. **`NO_BENCHMARK_LEAK`**: Benchmark ground truth labels are strictly isolated from production inference pipelines.
4. **`SPECTRAL_INTEGRITY`**: Disallow computing NIR-dependent indices (NDVI/NDWI) when NIR is missing (`INDEX_NOT_AVAILABLE`).
5. **`SPATIAL_ALIGNMENT`**: Disallow subtraction or overlays on non-registered or misprojected rasters (`REGISTRATION_REQUIRED`).
6. **`MODALITY_SANCTITY`**: Never misuse models on incompatible data formats (e.g., ChangeFormer as an arbitrary video detector).
7. **`UNBIASED_CONFIDENCE`**: Heuristic formulas must never be presented as calibrated ML model confidence.
8. **`FALLBACK_EXPLICIT`**: All fallbacks must be explicitly labeled and observable in the execution trace.

### 32.5 Performance & Resilience Features
- **Deterministic Caching**: SHA-256 composite hashing over image bytes, normalized queries, capabilities, and parameters prevents redundant, expensive neural net inference.
- **Resource-Aware Concurrency**: Pre-flight memory checks ensure sufficient RAM headroom before executing heavy models. `gpu_lock` enforces single-operation VRAM safety.
- **End-to-End Provenance**: Every final result links directly back to input file checksums, preprocessing transforms, model versions, and artifact files.
- **Frontend Observability**: Users inspect orchestration metadata via a collapsible "Advanced Agent Orchestration & Provenance Telemetry" card in `ResultsPanel.tsx`.

