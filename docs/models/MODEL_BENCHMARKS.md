# SatQuery AI — Model Benchmarks & Quantitative Evaluation

This document rigorously divides **official upstream paper benchmarks** from **SatQuery measured in-house evaluations**, ensuring total scientific transparency and zero inflation of model metrics.

---

## 1. Official Upstream Paper Benchmarks

These metrics are reported by original authors in published peer-reviewed literature. They reflect performance on standardized public benchmarks under upstream laboratory conditions.

| Model | Upstream Evaluation Dataset | Primary Task | Metric | Reported Upstream Score | Canonical Citation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Grounding DINO** | COCO 2017 minival | Zero-Shot Object Detection | AP (Average Precision) | **52.5 AP** | Liu et al., ECCV 2024 |
| **Grounding DINO** | LVIS val 1.0 | Open-Vocabulary Detection | $AP_r$ (Rare Classes) | **27.4 AP_r** | Liu et al., ECCV 2024 |
| **SAM 2.1** | SA-V Validation | Promptable Video Segmentation | J&F Mean Score | **75.0%** | Ravi et al., Meta AI 2024 |
| **SAM 2.1** | MOSE Dataset | Complex Video Object Segmentation | J&F Mean Score | **70.4%** | Ravi et al., Meta AI 2024 |
| **ChangeFormer** | LEVIR-CD Test Split | Bi-Temporal Optical Change Detection | F1-Score / IoU | **90.40% F1 / 82.48% IoU** | Bandara & Patel, IEEE TGRS 2022 |
| **ChangeFormer** | DSIFN-CD Test Split | Multi-Sensor Change Detection | F1-Score / IoU | **86.67% F1 / 76.47% IoU** | Bandara & Patel, IEEE TGRS 2022 |
| **CDVQA** | SECOND-CDVQA Test Split | Change Visual Question Answering | Overall Accuracy (OA) | **72.10% OA** | Yuan et al., IEEE TGRS 2022 |
| **DOFA** | MultiSensor Linear Probe | Cross-Modal Classification | Top-1 Accuracy | **89.20%** | Xiong et al., CVPR 2024 |
| **RemoteCLIP** | UC Merced Captions (UCM) | Zero-Shot Classification | Top-1 Accuracy | **84.20%** | Chen et al., IEEE TGRS 2024 |
| **BigEarthNet-v2.0** | BigEarthNet-MM Test Split | 12-Channel Multi-Label Land Cover | Mean Average Precision (mAP) | **86.40% mAP** | Sumbul et al., IEEE GRSM 2021 |
| **General RS-VLM (BLIP)** | VQA-v2 Test-Dev | Visual Question Answering | Accuracy | **78.25%** | Li et al., ICML 2022 |

---

## 2. SatQuery In-House Measured Benchmarks

These metrics were measured directly inside the SatQuery AI runtime environment on local compute hardware (`RTX 5050 Laptop GPU` and `Intel Core i7`).

### A. CDVQA Benchmark (Official Test Split, 2,000 Evaluation Records)
- **Evaluation Script**: `scripts/evaluate_cdvqa.py`
- **Checkpoint**: `checkpoints/cdvqa/cdvqa_satquery.pt`
- **Overall Accuracy (OA)**: **69.50%** (1,390 / 2,000 correct)
- **Average Accuracy (AA)**: **60.36%**
- **Category-Level Accuracy Breakdown**:
  - `change_or_not` (Did change occur?): **83.57%** (599 / 718 samples)
  - `increase_or_not` (Did feature increase?): **77.27%** (170 / 220 samples)
  - `decrease_or_not` (Did feature decrease?): **75.54%** (176 / 233 samples)
  - `change_ratio_types` (Which ratio type?): **70.00%** (203 / 290 samples)
  - `change_to_what` (What did it change into?): **60.54%** (89 / 147 samples)
  - `largest_change` (What was the largest change?): **46.94%** (69 / 147 samples)
  - `change_ratio` (Quantitative percentage range): **37.76%** (37 / 98 samples)
  - `smallest_change` (What was the smallest change?): **31.29%** (46 / 147 samples)

### B. Grounding Reasoner Benchmark (VRSBench Validation Sample, 100 Records)
- **Evaluation Script**: `scripts/evaluate_grounding_vrsbench.py`
- **Checkpoint**: `checkpoints/grounding_dino/groundingdino_swint_ogc.pth` + V1/V2/V3/V4 reasoners
- **Comparison across Strategies**:
  | Strategy | Mean IoU | Median IoU | Recall@0.25 | Recall@0.50 | Notes |
  | :--- | :--- | :--- | :--- | :--- | :--- |
  | **V1 (Baseline Confidence)** | 0.1832 | 0.0914 | 0.3400 | 0.2200 | Naive max confidence box |
  | **V2 (Semantic Overlap)** | 0.2371 | 0.1420 | 0.4100 | 0.2600 | Query-cleaned prompt |
  | **V3 (Contextual Anchor)** | 0.2238 | 0.1250 | 0.3800 | 0.2400 | Static spatial weights |
  | **V4 (Relational Multi-Attribute)**| **0.2415** | **0.1490** | **0.4300** | **0.2700** | Production adaptive reasoner |

### C. Live Inference Latency & Memory Measurements (RTX 5050 Laptop GPU)
- Measured during end-to-end API testing on `http://localhost:8000`:
  - **Grounding DINO**: $1.408\text{ seconds}$ (1.85 GB VRAM)
  - **SAM 2.1**: $1.105\text{ seconds}$ (1.42 GB VRAM)
  - **ChangeFormerV6**: $0.874\text{ seconds}$ (1.55 GB VRAM)
  - **CDVQA**: $0.983\text{ seconds}$ (0.84 GB VRAM)
  - **DOFA Embeddings**: $0.812\text{ seconds}$ (1.12 GB VRAM)
  - **Optical-SAR Cross-Attention**: $0.210\text{ seconds}$ (0.51 GB VRAM)
  - **RemoteCLIP**: $0.285\text{ seconds}$ (0.62 GB VRAM)
  - **BigEarthNet-v2.0**: $0.152\text{ seconds}$ (0.45 GB VRAM)
  - **General RS-VLM (BLIP)**: $0.820\text{ seconds}$ (1.54 GB VRAM)
  - **V4 Spatial Reasoner**: $0.003\text{ seconds}$ (< 2 MB RAM on CPU)
  - **Evidence Adjudicator**: $0.0005\text{ seconds}$ (< 1 MB RAM on CPU)
