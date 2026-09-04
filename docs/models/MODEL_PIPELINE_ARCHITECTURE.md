# SatQuery AI — Model Pipeline & Execution Architecture

This document diagrams the complete multi-model pipeline architecture of SatQuery AI, showing how specialist models, reasoners, evidence adjudication, and database persistence coordinate to answer complex Earth observation queries.

---

## 1. Master System Pipeline Architecture

```mermaid
graph TD
    User["User Query + Satellite Rasters"] --> API["FastAPI Endpoint (/api/analyze)"]
    API --> JobInit["Job Initialization (UUID & Input Validation)"]
    JobInit --> Analyzer["Input Modality & Metadata Analyzer"]
    
    Analyzer --> Intent["Intent Classification & Parameter Extraction"]
    Intent --> Planner["Autonomous Agent Planner (DAG Generation)"]
    
    subgraph ModelSpecialists ["Model Registry & Specialist Execution"]
        Planner --> Router["Capability Router"]
        Router -->|Grounding Task| DINO_V4["Grounding DINO + V4 Reasoner + SAM 2.1"]
        Router -->|Temporal Change| CF_CDVQA["ChangeFormerV6 + CDVQA"]
        Router -->|Optical/SAR Fusion| DOFA_Fusion["DOFA + CrossAttentionFusionNet"]
        Router -->|Conversational VQA| VLM["General RS-VLM (BLIP-VQA)"]
        Router -->|Multimodal Sentinel| BEN["BigEarthNet-v2.0 (12-Channel)"]
        Router -->|Zero-Shot / Retrieval| CLIP["RemoteCLIP (ViT-B/32)"]
    end
    
    DINO_V4 --> Val["Output Validator (Range, Shape, Nan/Inf Checks)"]
    CF_CDVQA --> Val
    DOFA_Fusion --> Val
    VLM --> Val
    BEN --> Val
    CLIP --> Val
    
    Val --> Evidence["Evidence Engine (Polygons, Heatmaps, Statistics)"]
    Evidence --> Adjudicator["Evidence Adjudicator (Cross-Model Discrepancy Detection)"]
    
    Adjudicator --> Visuals["Visual Analytics Engine (15 Layer Modes)"]
    Visuals --> Results["Results Compiler (/api/jobs/{id}/results)"]
    
    Results --> Frontend["Next.js Production Frontend (:3000)"]
    Results --> DB[("PostgreSQL 16 Relational Persistence (10 Tables)")]
```

---

## 2. Object Grounding Pipeline (Grounding DINO + V4 + SAM 2.1)

```mermaid
graph TD
    subgraph GroundingInput
        Img["Optical Image (H x W x 3)"]
        Query["Referring Query: 'the white car in the bottom-middle'"]
    end

    Query --> Parse["parse_v4_query()"]
    Parse --> CleanPrompt["Clean Prompt: 'car.'"]
    Parse --> Modifiers["Extracted Attributes: {color: 'white', position: 'bottom-middle'}"]
    
    Img --> DINO["Grounding DINO (Swin-T Backbone)"]
    CleanPrompt --> DINO
    DINO --> RawBoxes["Raw Detector Candidate Boxes"]
    
    RawBoxes --> NMS["NMS Deduplication (IoU >= 0.50)"]
    Modifiers --> V4Scorer["V4 Multi-Attribute Geometric Scorer"]
    NMS --> V4Scorer
    
    V4Scorer --> TopBox["Disambiguated Top-1 Bounding Box [x1, y1, x2, y2]"]
    TopBox --> SAM2["SAM 2.1 Mask Decoder (Hiera Backbone)"]
    Img --> SAM2
    
    SAM2 --> Mask["High-Resolution Binary Mask {0, 1}"]
    Mask --> Vector["Contour Vectorization -> GeoJSON Polygon"]
    Mask --> Stats["Pixel Area Accounting (sq meters / sq km)"]
```

---

## 3. Bi-Temporal Change Detection & CDVQA Pipeline

```mermaid
graph TD
    subgraph BiTemporalInputs
        T1["Pre-Change Raster T1 (2021)"]
        T2["Post-Change Raster T2 (2023)"]
        Question["User Query: 'Show newly built structures'"]
    end

    subgraph SpatialStream ["Spatial Specialist: ChangeFormerV6"]
        T1 --> CF_In["512x512 Resized & Normalized"]
        T2 --> CF_In
        CF_In --> CF["Siamese MiT-B2 Transformer"]
        CF --> Logits["Bitemporal Logits"]
        Logits --> Heatmap["Continuous Probability Heatmap [0, 1]"]
        Logits --> BinaryMask["Binary Change Mask {0, 1} (Threshold=0.5)"]
    end

    subgraph SemanticStream ["Semantic Specialist: CDVQA"]
        T1 --> CDVQA_In["256x256 Resized & Normalized"]
        T2 --> CDVQA_In
        Question --> TextEnc["GRU Question Tokenizer"]
        CDVQA_In --> CDVQA_Net["Siamese ResNet-18 + CEM Attention"]
        TextEnc --> CDVQA_Net
        CDVQA_Net --> Answer["19-Class Answer: 'buildings' (Conf: 88%)"]
    end

    BinaryMask --> Adjudicator["Evidence Adjudicator"]
    Answer --> Adjudicator
    Heatmap --> Adjudicator

    Adjudicator --> Verdict{"Discrepancy Check"}
    Verdict -->|Mask matches Text| CleanOutput["Verdict: NO_CONFLICT (Harmonious)"]
    Verdict -->|Contradiction Detected| ReviewOutput["Verdict: REVIEW_REQUIRED (Physical Spatial Override)"]
```

---

## 4. Optical-SAR Cross-Modal Fusion Pipeline

```mermaid
graph TD
    subgraph CrossModalInputs
        Opt["Optical Sentinel-2 RGB (0.49, 0.56, 0.665 um)"]
        SAR["SAR Sentinel-1 Radar (VV, VH at 55,000 um)"]
    end

    Opt --> DOFA["DOFA Foundation Model (Dynamic Wavelengths)"]
    SAR --> DOFA
    
    DOFA --> OptEmbed["Optical Embeddings (197 x 768)"]
    DOFA --> SAREmbed["SAR Embeddings (197 x 768)"]

    OptEmbed --> FusionNet["CrossAttentionFusionNet"]
    SAREmbed --> FusionNet

    subgraph CrossAttentionCore
        FusionNet --> Cross1["Q_opt -> K_sar, V_sar"]
        FusionNet --> Cross2["Q_sar -> K_opt, V_opt"]
        Cross1 --> JointConcat["Residual LayerNorm + Concat (1536-dim)"]
        Cross2 --> JointConcat
    end

    JointConcat --> Head1["19-Class Corine Land Cover Head"]
    JointConcat --> Head2["SAR Surface Roughness Head (Sigmoid)"]
    JointConcat --> Head3["Structural Built-Up Head (Sigmoid)"]

    Head1 --> Out1["Land Cover: 'Permanently irrigated land' (52.5%)"]
    Head2 --> Out2["Roughness Index: 0.524"]
    Head3 --> Out3["Built-Up Index: 0.364"]
```

---

## 5. Video Patrol Pipeline

```mermaid
graph TD
    Video["Aerial / Drone MP4 Footage"] --> Decoder["Video Decoder (OpenCV / PyAV)"]
    Decoder --> Sampler["Uniform Temporal Sampler (1 fps / Keyframes)"]
    
    Sampler --> Keyframes["Extracted Keyframe Image Sequence"]
    Keyframes --> DINO_V4["Grounding DINO + V4 (Initial Target Localization)"]
    
    DINO_V4 --> InitBox["Keyframe 0 Target Bounding Box"]
    InitBox --> SAM2_Video["SAM 2.1 Video Predictor (Memory Bank Attention)"]
    Keyframes --> SAM2_Video
    
    SAM2_Video --> PropagatedMasks["Temporally Propagated Mask Sequence"]
    PropagatedMasks --> Tracker["Centroid & Trajectory Tracker"]
    Tracker --> Flagger["Event Flagger (Speed Anomaly / Perimeter Breach)"]
    
    Flagger --> VideoReport["Interactive Video Audit Package & Keyframe Badges"]
```
