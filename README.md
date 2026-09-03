# SatQuery AI — Agentic Remote-Sensing Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.0-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-104%20Passing-brightgreen.svg)]()

> **SatQuery AI** is an agentic, multi-modal Earth observation intelligence platform that transforms satellite, aerial, and SAR data into verifiable, actionable answers through natural language. Instead of relying on a single hallucination-prone monolithic VLM, SatQuery AI autonomously orchestrates decoupled specialist neural networks (GeoChat-7B, Grounding DINO, SAM 2.1, ChangeFormerV6, and CDVQA) alongside a 15-mode remote-sensing visual analytics engine and streaming video pipeline, backed by verifiable spatial evidence and zero-fabrication guarantees.

📖 **For exhaustive technical specifications, architectural diagrams, model details, and verified benchmarks, see the authoritative master document**:  
👉 **[`docs/SATQUERY_AI_MASTER_DOCUMENTATION.md`](docs/SATQUERY_AI_MASTER_DOCUMENTATION.md)**

---

## Key Capabilities

- **Single-Image Semantic VQA**: Natural-language remote-sensing scene understanding and captioning via **GeoChat-7B**.
- **Open-Vocabulary Visual Grounding**: Target feature localization and relational candidate selection via **Grounding DINO + V4 Reasoner**.
- **Promptable Spatial Segmentation**: Pixel-precise polygon mask generation and true metric ground area ($m^2, km^2$) via **SAM 2.1 Hiera Small**.
- **Bi-Temporal Spatial Change Detection**: Pixel-level change mask and continuous probability heatmap generation via **ChangeFormerV6**.
- **Bi-Temporal Change VQA**: Dual-model execution where **CDVQA** answers semantic change questions concurrently with ChangeFormer spatial evidence.
- **Scientific Visual Analytics (15 Modes)**: True Color, False Color CIR, Spectral Indices (NDVI, NDWI, NDBI) with zero-fabrication rules, SAR dual-pol ($VV/VH$) backscatter, probability heatmaps, 50-bin radiometric histograms, and interactive pixel inspection.
- **Aerial Video Footage Intelligence**: Streaming frame decoding, query-driven tracking, SAM 2.1 mask propagation, and heuristic event flagging.
- **Observable Evidence Pipeline**: Auditable PostgreSQL execution traces, GeoTIFF exports, GeoJSON boundaries, and publication-ready PNGs with scientific legends.

---

## Architecture at a Glance

```text
                               Natural Language Query & Satellite Raster / Video
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │ Deterministic Intent Router │
                                       └──────────────┬──────────────┘
                                                      │
         ┌───────────────────┬────────────────────────┼────────────────────────┬───────────────────┐
         ▼                   ▼                        ▼                        ▼                   ▼
┌─────────────────┐ ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ ┌─────────────────┐
│ Single-Image    │ │ Single-Image    │      │ Bi-Temporal     │      │ Bi-Temporal     │ │ Aerial Video    │
│ Semantic VQA    │ │ Target Grounding│      │ Spatial Change  │      │ Change VQA      │ │ Footage Tracking│
├─────────────────┤ ├─────────────────┤      ├─────────────────┤      ├─────────────────┤ ├─────────────────┤
│ GeoChat-7B      │ │ Grounding DINO  │      │ ChangeFormerV6  │      │ ChangeFormer    │ │ Grounding DINO  │
│ (Remote-Sensing │ │        ↓        │      │ (Siamese Trans- │      │        +        │ │        ↓        │
│ VLM Specialist) │ │ V4 Relational   │      │  former Mask    │      │ CDVQA           │ │ V4 Relational   │
│                 │ │        ↓        │      │  Generator)     │      │ (ResNet-18+CEM  │ │        ↓        │
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
                                       │ PostgreSQL 15 & Next.js 14  │
                                       └─────────────────────────────┘
```

---

## Quick Start

### 1. Database Setup
```bash
# Launch PostgreSQL with Docker
docker run -d --name satquery-pg -e POSTGRES_USER=satquery -e POSTGRES_PASSWORD=satquery_secret -e POSTGRES_DB=satquery_ai -p 5432:5432 postgres:15
```

### 2. Backend Installation & Execution
```bash
cd satquery-ai
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API documentation available at `http://localhost:8000/docs`.*

### 3. Frontend Installation & Execution
```bash
cd satquery-ai/frontend
npm install
npm run dev
```
*Web dashboard available at `http://localhost:3000`.*

### 4. Running the Test Suite
```bash
pytest -v
python scripts/smoke_test_visualization.py
```

---

## Documentation Links

All in-depth technical documentation, experimental measurements, and research citations are consolidated in:
- 📑 **[Master Technical Documentation](docs/SATQUERY_AI_MASTER_DOCUMENTATION.md)**
