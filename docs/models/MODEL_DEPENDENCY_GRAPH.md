# SatQuery AI — Model Dependency Graph & Interaction Topology

This document maps the inter-model data dependencies, execution chains, and artifact transfers across the specialist neural networks and algorithmic engines in **SatQuery AI**.

---

## 1. Global Inter-Model Dependency Topology

```mermaid
graph TD
    UserQuery["Natural-Language Query + Sat Rasters"]
    
    subgraph Ingestion ["1. Ingestion & Analysis"]
        UserQuery --> IntentRouter["Intent Router & Modality Detector"]
    end

    subgraph GroundingStream ["2. Grounding & Segmentation Chain"]
        IntentRouter -->|grounding| DINO["Grounding DINO (Open-Vocabulary Boxes)"]
        DINO -->|Candidate Proposals| V4["V4 Spatial Reasoner (NMS & Attribute Ranking)"]
        V4 -->|Top-1 Target Box| SAM2["SAM 2.1 (Sub-Pixel Polygon Mask)"]
        SAM2 --> MaskVector["Contour Vectorizer & GeoJSON"]
    end

    subgraph TemporalStream ["3. Bi-Temporal Change & VQA Chain"]
        IntentRouter -->|temporal_vqa| ChangeFormer["ChangeFormerV6 (Dense Change Map)"]
        IntentRouter -->|temporal_vqa| CDVQA["CDVQA (19-Class Semantic Answer)"]
        ChangeFormer --> AreaCalc["Pixel Area Statistics Engine"]
    end

    subgraph CrossModalStream ["4. Optical-SAR Multimodal Chain"]
        IntentRouter -->|cross_modal| DOFA["DOFA Foundation Model (Wavelength Embeddings)"]
        DOFA -->|768-dim Optical & SAR Embeds| FusionNet["Optical-SAR CrossAttentionFusionNet"]
        FusionNet --> Indices["Roughness & Built-Up Indices"]
    end

    subgraph SingleImageStream ["5. General Understanding Chain"]
        IntentRouter -->|vqa| GeneralVLM["General RS-VLM (BLIP-VQA)"]
        IntentRouter -->|zero_shot| RemoteCLIP["RemoteCLIP (RS Embedding hypersphere)"]
        IntentRouter -->|12_channel| BigEarthNet["BigEarthNet-v2.0 (ResNet-50 12-channel)"]
    end

    subgraph AdjudicationEngine ["6. Adjudication & Integrity Check"]
        MaskVector --> Adjudicator["Evidence Adjudicator"]
        AreaCalc --> Adjudicator
        CDVQA --> Adjudicator
        Indices --> Adjudicator
        GeneralVLM --> Adjudicator
        Adjudicator --> AuditRecord["Audited Adjudication Verdict"]
    end

    subgraph VideoChain ["7. Video Patrol Tracking Chain"]
        IntentRouter -->|video| VideoSampler["Uniform Temporal Keyframe Sampler"]
        VideoSampler --> DINO
        DINO -->|Init Box| SAM2_Video["SAM 2.1 Video Memory Predictor"]
        SAM2_Video --> Tracker["Centroid Trajectory & Event Flagger"]
        Tracker --> AuditRecord
    end

    subgraph Deliverables ["8. Deliverables & Persistence"]
        AuditRecord --> Visualizer["Visual Analytics Engine (15 Layer Modes)"]
        Visualizer --> DB[("PostgreSQL 16 Storage")]
        Visualizer --> APIOutput["FastAPI Response Payload"]
    end
```

---

## 2. Detailed Dependency Specifications

### A. Grounding $\to$ Reasoning $\to$ Segmentation
- **Source**: `GroundingDINOAdapter`
- **Payload Transferred**: List of unnormalized candidate bounding boxes `[x1, y1, x2, y2]`, detection confidence scores, and matched text labels.
- **Consumer**: `V4 Spatial Reasoner` (`run_v4_reasoning`)
- **Transformation**: Applies NMS deduplication (IoU $\ge 0.50$), evaluates spatial anchors, relative areas, dominant colors, and reference object landmarks to select exactly one target box.
- **Payload Transferred**: Single disambiguated bounding box `[x1, y1, x2, y2]`.
- **Final Consumer**: `SAM2Adapter` (`predict_mask_from_box`)
- **Terminal Deliverable**: 2D binary segmentation mask ($0/1$) and vector GeoJSON polygon.

---

### B. ChangeFormer + CDVQA $\to$ Evidence Adjudicator
- **Spatial Specialist**: `ChangeFormerAdapter` produces `change_ratio` (float), `changed_pixels` (int), and continuous probability heatmap.
- **Semantic Specialist**: `CDVQAAdapter` produces `answer` (string) and `confidence` (float).
- **Consumer**: `EvidenceAdjudicator.adjudicate()`
- **Adjudication Logic**:
  - Compares spatial change ratio against CDVQA answer semantics.
  - If ChangeFormer $> 5\%$ change and CDVQA claims `"no change"`, the adjudicator flags `REVIEW_REQUIRED` and overrides the conversational answer using physical spatial pixel evidence.
  - If harmonious, produces `adjudication_status="NO_CONFLICT"` with boosted consensus confidence.

---

### C. DOFA $\to$ Optical-SAR Cross-Attention Fusion
- **Foundation Encoder**: `DOFAAdapter` generates 768-dimensional token embeddings for optical visible bands and Sentinel-1 SAR C-band microwave backscatter ($55,000\,\mu\text{m}$).
- **Consumer**: `CrossAttentionFusionNet` in `OpticalSARFusionModel`.
- **Interaction**: Optical tokens query SAR radar tokens ($Q_{\text{opt}} \to K_{\text{sar}}, V_{\text{sar}}$) and SAR tokens query optical tokens ($Q_{\text{sar}} \to K_{\text{opt}}, V_{\text{opt}}$).
- **Terminal Deliverable**: 19-class Corine land-cover distribution, SAR surface roughness index ($[0, 1]$), and structural built-up index ($[0, 1]$).
