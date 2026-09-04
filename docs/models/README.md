# SatQuery AI — Model Architecture & Research Dossier Index

Welcome to the **SatQuery AI Model Documentation and Research Dossier**. This repository of technical specifications provides full mathematical, architectural, provenance, and implementation details for every artificial intelligence model, foundation encoder, neural network, and algorithmic reasoning engine in the platform.

---

## 1. Master Technical Synthesis Dossiers

For high-level system evaluations, mentor inspections, and research audits, consult these cross-cutting dossiers:

- 📊 **[Model Comparison Matrix](MODEL_COMPARISON_MATRIX.md)**: Technical comparison of tasks, modalities, parameter counts, checkpoints, latency, and status.
- 🏗️ **[Model Pipeline Architecture](MODEL_PIPELINE_ARCHITECTURE.md)**: End-to-end dataflow diagrams from user input to PostgreSQL persistence.
- 💾 **[Checkpoint Inventory](CHECKPOINT_INVENTORY.md)**: Comprehensive inventory of all 10 local checkpoint files, sizes (3.89 GB total), and formats.
- 🗺️ **[Dataset-to-Model Mapping](DATASET_MODEL_MAPPING.md)**: Master mapping of training data, evaluation benchmarks, and sensor modalities.
- 🏋️ **[Model Training Status](MODEL_TRAINING_STATUS.md)**: Transparent breakdown of upstream pretrained models vs in-house trained models (CDVQA).
- 📈 **[Model Benchmarks & Evaluation](MODEL_BENCHMARKS.md)**: Rigorous division of official paper benchmarks vs SatQuery measured in-house results.
- ⚡ **[Computational Resource Requirements](MODEL_RESOURCE_REQUIREMENTS.md)**: CPU, RAM, GPU, VRAM, cold-load, and inference latency specifications.
- 🎯 **[Model Selection Rationale](MODEL_SELECTION_RATIONALE.md)**: Architectural decisions explaining why each model was selected over alternatives.
- 🕸️ **[Model Dependency Graph](MODEL_DEPENDENCY_GRAPH.md)**: Interaction topology, execution chains, and artifact transfers across specialists.

---

## 2. Individual Model Dossiers (By Functional Domain)

### A. Object Grounding & Spatial Referring
- 🎯 **[Grounding DINO](GROUNDING_DINO.md)**: Open-vocabulary target detection transformer (Swin-T + BERT-Base, 172M parameters, 52.5 AP).
- 🧠 **[V1 Grounding Strategy](V1_GROUNDING_STRATEGY.md)**: Baseline detector confidence selection ($0.1832\text{ mIoU}$).
- 🧠 **[V2 Grounding Strategy](V2_GROUNDING_STRATEGY.md)**: Query-aware semantic matching and prompt noise cleaning ($0.2371\text{ mIoU}$).
- 🧠 **[V3 Grounding Strategy](V3_GROUNDING_STRATEGY.md)**: Contextual spatial anchor heuristics and Gaussian decay ($0.2238\text{ mIoU}$).
- 🚀 **[V4 Grounding Reasoning Engine](V4_GROUNDING_REASONING.md)**: Production multi-attribute relational spatial reasoner ($0.2415\text{ mIoU}$, $< 5\text{ ms}$).

### B. Sub-Pixel Segmentation & Video Tracking
- ✂️ **[SAM 2.1 (Segment Anything Model 2)](SAM2_1.md)**: Meta AI foundation model for promptable polygon mask segmentation and video memory propagation (Hiera backbone, 46M parameters, 0.8889 mask IoU).

### C. Bi-Temporal Change Analysis & Change VQA
- 🔄 **[ChangeFormerV6](CHANGEFORMER_V6.md)**: Siamese Mix Transformer (MiT-B2, 13.5M parameters) for pixel-dense optical surface change detection (90.4% F1, 82.5% IoU).
- 💬 **[CDVQA](CDVQA.md)**: Siamese ResNet-18 + Change Enhancing Module (CEM) + GRU trained in-house on 48,000 SECOND-CDVQA triplets (69.50% test accuracy).

### D. Multisensor Foundation & Multimodal Fusion
- 🛰️ **[DOFA Foundation Model](DOFA.md)**: 12-layer Vision Transformer (111M parameters) with Dynamic Wavelength-conditioned Patch Embeddings ($0.49\,\mu\text{m}$ to $55,000\,\mu\text{m}$).
- 🔀 **[Optical-SAR Cross-Attention Fusion](OPTICAL_SAR_FUSION.md)**: Bi-directional cross-attention transformer predicting 19 land cover classes, surface roughness, and built-up density.
- 🌍 **[BigEarthNet-v2.0](BIGEARTHNET_MULTIMODAL.md)**: 12-channel Sentinel-1/Sentinel-2 ResNet-50 benchmark model (86.4% mAP).

### E. Vision-Language & Zero-Shot Classification
- 🗨️ **[General RS-VLM](GENERAL_RS_VLM.md)**: Compact 1.54 GB BLIP-VQA transformer for open-ended conversational remote-sensing scene understanding.
- 🏷️ **[RemoteCLIP](REMOTECLIP.md)**: ViT-B/32 vision-language foundation model for remote-sensing zero-shot categorization and image-text retrieval (84.2% UCM).

### F. Multi-Model Adjudication & Epistemic Governance
- ⚖️ **[Evidence Adjudicator](EVIDENCE_ADJUDICATOR.md)**: Deterministic, rule-based decision engine enforcing physical spatial evidence hierarchies and flagging cross-model contradictions (`REVIEW_REQUIRED`).

### G. Evaluated External Candidates (Not Configured in Production)
- 📚 **[GeoChat](GEOCHAT.md)**: CVPR 2024 7B grounded VLM (MBZUAI); retained in `third_party/GeoChat/` as an external reference; not configured in production due to 14 GB VRAM requirement.
- 📚 **[EarthDial](EARTHDIAL.md)**: 7.2B Vicuna satellite dialogue candidate; not adopted due to 14.5 GB VRAM footprint.
- 📚 **[RSCoVLM](RSCOVLM.md)**: 7.5B EVA-CLIP candidate; not adopted due to 15 GB VRAM footprint.

---

## 3. Verification Standards & Ethical Principles

Every document in this directory adheres to SatQuery AI's core principles:
1. **Zero Fabrication**: No benchmark numbers, parameters, or accuracies are invented. Unverifiable details are explicitly labeled `NOT VERIFIED`.
2. **Clear Provenance Tiers**:
   - `OFFICIAL / UPSTREAM`: Verified from published literature or official author repositories.
   - `SATQUERY IMPLEMENTATION`: Derived directly from source code in this repository.
   - `SATQUERY MEASURED`: Quantitatively timed or evaluated on local hardware (`RTX 5050 Laptop GPU`).
   - `EVALUATED CANDIDATE`: Inspected or benchmarked, but not configured for runtime deployment.
