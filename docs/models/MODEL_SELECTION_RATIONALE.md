# SatQuery AI — Model Selection Rationale & Architectural Decisions

This document outlines the engineering rationale behind every model selection in **SatQuery AI**, detailing alternative architectures evaluated, task compatibility, dataset alignment, computational trade-offs, and open-source licensing.

---

## 1. Grounding DINO + V4 Reasoner + SAM 2.1 (Object Grounding & Segmentation)
- **Why Selected for SatQuery**: Provides decoupled, open-vocabulary object localization and pixel-perfect boundary polygonization in $< 2.5\text{s}$ under $3\text{ GB VRAM}$.
- **What It Replaces**: Monolithic 7B Vision-Language Models (GeoChat-7B, EarthDial-7B).
- **Why Not Alternatives**:
  - *GeoChat-7B / EarthDial-7B*: Require 14–16 GB VRAM (triggering immediate OOM on consumer GPUs) and can only output coarse text bounding boxes, not polygon masks.
  - *YOLOv8 / YOLOv10*: Closed-vocabulary detectors restricted to fixed classes (e.g. 80 COCO classes); fail on arbitrary satellite referring expressions.
  - *Original SAM 1 (ViT-B)*: 3x heavier, 2.5x slower, zero native video tracking capabilities.
- **Task Fit**: Grounding DINO extracts candidate proposals; V4 Reasoner resolves linguistic and spatial referring constraints; SAM 2.1 generates dense binary masks and propagates them across video frames.
- **License**: Apache 2.0 (Commercial and research friendly).

---

## 2. ChangeFormerV6 (Bi-Temporal Spatial Change Detection)
- **Why Selected for SatQuery**: Captures long-range spatial context across multi-year satellite acquisitions via Siamese hierarchical Mix Transformer (MiT-B2) encoders without losing high-resolution structural edges.
- **What It Replaces**: Pure CNN Siamese networks (FC-Siam-diff, FC-Siam-conc, UNet).
- **Why Not Alternatives**:
  - *FC-Siam-diff / UNet*: Limited convolutional receptive fields create high false-alarm rates over agricultural fields and blur building boundary edges.
  - *BIT (Bitemporal Image Transformer)*: Uses standard CNN tokens; ChangeFormer's pure transformer encoder achieves higher IoU on benchmark LEVIR-CD.
- **Computational Fit**: Compact 13.5M parameter footprint executing in 0.874s on RTX 5050 GPU (164 MB checkpoint).
- **License**: MIT License.

---

## 3. CDVQA (Change Detection Visual Question Answering)
- **Why Selected for SatQuery**: Directly answers conversational change questions (*"What was built?"*, *"Did vegetation increase?"*) using a specialized Change Enhancing Module (CEM) that cross-attends $T_1$ and $T_2$ visual differences before conditioning on the question.
- **What It Replaces**: Generic Single-Image VLMs (BLIP, LLaVA).
- **Why Not Alternatives**:
  - *Generic VLMs*: Fail at temporal reasoning because they lack cross-attention difference modules; they confuse $T_1$ and $T_2$ features or simply describe the second image in isolation.
- **Task Fit**: Answers semantic questions (*WHAT happened?*), perfectly complementing ChangeFormer's spatial masks (*WHERE did it happen?*).
- **Training Fit**: Trained in-house by SatQuery on 48,000 question-answer triplets from the official SECOND-CDVQA benchmark.
- **License**: MIT License.

---

## 4. DOFA (Dynamic Earth Observation Foundation Model)
- **Why Selected for SatQuery**: Overcomes the physical sensor gap between optical reflectance and active microwave radar backscatter using Dynamic Wavelength-conditioned Patch Embeddings.
- **What It Replaces**: Separate, incompatible single-sensor encoders.
- **Why Not Alternatives**:
  - *SatMAE / Prithvi*: Restricted strictly to optical multispectral channels (Sentinel-2 / Landsat); cannot process microwave SAR backscatter ($55,000\,\mu\text{m}$).
- **Task Fit**: Ingests optical RGB ($0.49\text{--}0.665\,\mu\text{m}$) and SAR C-band ($55,000\,\mu\text{m}$) to produce unified 768-dimensional token embeddings for downstream cross-attention fusion.
- **License**: Apache 2.0 License.

---

## 5. Optical-SAR Cross-Attention Fusion Model
- **Why Selected for SatQuery**: Provides a genuine learned neural cross-modal fusion architecture ($Q_{\text{opt}} \to K/V_{\text{sar}}$ and $Q_{\text{sar}} \to K/V_{\text{opt}}$) predicting land cover, surface roughness, and built-up structural density.
- **What It Replaces**: Simple visual overlays and late probability averaging.
- **Task Fit**: Enables operators to verify ambiguous optical ground features with all-weather radar penetration.
- **License**: Apache 2.0 (SatQuery AI Proprietary Design).

---

## 6. RemoteCLIP (RS Zero-Shot Classification & Retrieval)
- **Why Selected for SatQuery**: Pretrained on remote-sensing caption datasets (RSICD, RSITMD, UCM), aligning nadir satellite textures with free-form user text prompts.
- **What It Replaces**: Standard OpenAI CLIP (ViT-B/32).
- **Why Not Alternatives**:
  - *OpenAI CLIP*: Suffers an 18–25% accuracy penalty on satellite imagery due to nadir perspective shift.
- **Task Fit**: Provides rapid zero-shot classification across arbitrary user category lists.
- **License**: MIT License.

---

## 7. BigEarthNet-v2.0 (12-Channel Sentinel Multimodal Baseline)
- **Why Selected for SatQuery**: Official benchmark model from BIFOLD trained on 590,000 Sentinel-1/Sentinel-2 tile pairs across Europe.
- **Task Fit**: Ingests all 10 Sentinel-2 optical bands and 2 Sentinel-1 SAR polarizations simultaneously to predict 19 Corine Land Cover categories.
- **License**: MIT License.

---

## 8. General RS-VLM (BLIP-VQA Base)
- **Why Selected for SatQuery**: Provides responsive (< 1s), conversational single-image VQA with a compact 1.54 GB footprint that executes comfortably on consumer hardware alongside the specialist stack.
- **What It Replaces**: 7B+ LLMs requiring 14 GB+ VRAM.
- **License**: BSD 3-Clause.

---

## 9. Evidence Adjudicator (Deterministic Meta-Reasoner)
- **Why Selected for SatQuery**: Eliminates silent hallucination and black-box voting. Implements transparent, hardcoded rules based on physical spatial ground truth to detect and resolve cross-model contradictions.
- **What It Replaces**: Opaque neural meta-classifiers or simple unweighted averaging.
- **License**: Apache 2.0 (SatQuery AI Proprietary Design).
