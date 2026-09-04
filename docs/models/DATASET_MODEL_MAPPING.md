# SatQuery AI — Dataset-to-Model Mapping Matrix

This document maps all training, evaluation, and benchmark datasets used across SatQuery AI, clearly distinguishing upstream training data from SatQuery in-house training, validation, and runtime testing.

---

## 1. Master Dataset Mapping Table

| Dataset Name | Associated Model(s) | Primary Task | Role in SatQuery | Sensor / Modality | Ground-Truth Annotations | Scale / Split |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **VRSBench** | Grounding DINO, V1–V4 Reasoner | Referring Expression Grounding | **SatQuery Evaluation** | High-Res Optical Aerial ($0.1\text{--}0.5\text{ m}$) | Bounding boxes + Natural Language Referring Expressions | 29,614 images / 120k annotations (100 sample records evaluated) |
| **SECOND** | CDVQA | Semantic Change Detection & VQA | **SatQuery In-House Training** | Multi-City Aerial Stereo Pairs ($0.5\text{--}2.0\text{ m}$) | Pixel semantic change masks across 6 classes | 4,662 stereo pairs ($512 \times 512$) |
| **CDVQA Dataset** | CDVQA | Change Visual Question Answering | **SatQuery In-House Training** | Bi-Temporal Aerial ($T_1, T_2$) + Question Text | 19-class discrete answer labels | 100,000+ QA triplets (8k train pairs, 2k test pairs) |
| **LEVIR-CD** | ChangeFormerV6 | Bi-Temporal Surface Change | Upstream Pre-Training & Verification | Google Earth Ultra-High-Res ($0.5\text{ m}$) | Binary change masks ($0$: unchanged, $1$: changed) | 637 pairs ($1024 \times 1024$), 31,333 change instances |
| **BigEarthNet-MM** | BigEarthNet-v2.0 | Multimodal Land-Cover Classification | Upstream Pre-Training & Verification | Sentinel-2 Optical (10 bands) + Sentinel-1 SAR (2 bands) | 19 Corine Land Cover multi-label classes | 590,326 pairs across 10 European nations |
| **SA-V / SA-1B** | SAM 2.1 | Promptable Segmentation & Video | Upstream Pre-Training | Optical Video & Images | 642.6k masklets on 50.9k videos; 11M static images | 50.9K video sequences |
| **MultiSensor EO** | DOFA | Multisensor Foundation Pre-Training | Upstream Pre-Training | Sentinel-1, Sentinel-2, Landsat-8/9, PlanetScope | Masked Auto-Encoding across continuous wavelengths | Millions of satellite patches |
| **RSICD / RSITMD** | RemoteCLIP | Remote-Sensing Image-Text Retrieval | Upstream Pre-Training | Satellite & Aerial Optical Imagery | Multi-sentence natural language descriptive captions | ~15,000 captioned satellite scenes |
| **VQA-v2 / COCO** | General RS-VLM (BLIP) | Conversational Visual Question Answering | Upstream Pre-Training | Natural & Aerial Visible Imagery | Free-form natural language question-answer pairs | 1M+ QA pairs |
| **SatQuery Real Bi-Temporal Pair** | ChangeFormer, CDVQA | Runtime Integration & Accuracy Verification | **SatQuery Benchmark Pair** | High-Res Optical Bi-Temporal ($T_1, T_2$) | Authentic ground truth change raster | `datasets/samples/real_pair/` |
| **SatQuery Optical-SAR Pair** | DOFA, Optical-SAR Fusion | Cross-Modal Synthesis & Modality Verification | **SatQuery Benchmark Pair** | Sentinel-2 Optical RGB + Sentinel-1 C-Band SAR | Verified surface land-cover and radar roughness | `datasets/samples/optical_sar_pair/` |
| **SatQuery Aerial Video** | SAM 2.1 Video, Tracker | Video Patrol & Trajectory Grounding | **SatQuery Benchmark Video** | Aerial Drone Footage (MP4) | Grounded vehicle bounding boxes and keyframes | `datasets/samples/video/` |

---

## 2. Dataset Separation & Ethical Governance

SatQuery AI strictly enforces ethical boundaries regarding datasets:
1. **Zero Ground-Truth Leakage**: Ground-truth masks and annotations are never passed into model inference pipelines. In scripts like `evaluate_grounding_vrsbench.py`, ground-truth coordinates are loaded strictly post-prediction to compute Intersection-over-Union (IoU).
2. **Clear Training vs Evaluation Designation**:
   - **Trained by SatQuery**: CDVQA (on official SECOND/CDVQA dataset), Optical-SAR Fusion (on DOFA embeddings).
   - **Pre-Trained by Upstream Authors**: Grounding DINO, SAM 2.1, ChangeFormer, DOFA, RemoteCLIP, BigEarthNet, General RS-VLM.
   - **Evaluated Only**: VRSBench (used to benchmark V1, V2, V3, and V4 reasoning strategies).
