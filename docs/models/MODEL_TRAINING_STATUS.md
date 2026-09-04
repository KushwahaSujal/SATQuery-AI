# SatQuery AI — Model Training Status

This document explicitly defines the training origin, fine-tuning status, optimization hyperparameters, and checkpoint provenance for every model and reasoning component in SatQuery AI.

---

## 1. Master Training Status Table

| Model / Component | Trained by Upstream? | Trained by SatQuery? | Fine-Tuned by SatQuery? | Training Dataset | Epochs | Optimizer | Learning Rate | Checkpoint Path | Validation Score | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Grounding DINO** | **YES** (IDEA-Research) | **NO** | **NO** | Objects365, GoldG, Cap4M | Upstream (NOT VERIFIED) | AdamW (Upstream) | 1e-4 / 1e-5 (Upstream) | `checkpoints/grounding_dino/groundingdino_swint_ogc.pth` | 52.5 AP (COCO) | **UPSTREAM PRETRAINED** |
| **V1–V4 Reasoners** | **NO** (Algorithmic) | **NO** | **NO** | None (Rule-based) | N/A | None | None | *No Checkpoint (Code)* | 0.2371 mIoU (V4) | **DETERMINISTIC ENGINE** |
| **SAM 2.1** | **YES** (Meta AI) | **NO** | **NO** | SA-V, SA-1B | Upstream (NOT VERIFIED) | AdamW (Upstream) | Upstream (NOT VERIFIED) | `checkpoints/sam2/sam2_hiera_base_plus.pt` | 75.0 J&F (SA-V) | **UPSTREAM PRETRAINED** |
| **ChangeFormerV6** | **YES** (Bandara & Patel) | **NO** | **YES (Verified/Fine-tuned)** | LEVIR-CD, DSIFN-CD | 200 (Upstream) | AdamW | 1e-4 | `checkpoints/changeformer/satquery_changeformer_best.pt` | 90.4% F1 | **VERIFIED CHECKPOINT** |
| **CDVQA** | **YES** (Yuan et al. paper) | **YES (In-House Trained)** | **YES** | SECOND + CDVQA (48k pairs) | 5 | AdamW | 1e-3 (Cosine Decay) | `checkpoints/cdvqa/cdvqa_satquery.pt` | 68.63% Val OA (69.50% Test OA) | **SATQUERY TRAINED** |
| **DOFA** | **YES** (TUM / EarthFlow) | **NO** | **NO** | MultiSensor EO | 100 | AdamW | 1.5e-4 (Upstream) | `checkpoints/dofa/DOFA_ViT_base_e100.pth` | 89.2% Top-1 | **UPSTREAM PRETRAINED** |
| **Optical-SAR Fusion** | **NO** | **YES (In-House Designed)** | **YES** | DOFA Cross-Modal Embeddings | N/A | PyTorch AdamW | 1e-4 | `checkpoints/optical_sar/satquery_fusion.pth` | 52.5% Top-1 | **SATQUERY DESIGNED** |
| **RemoteCLIP** | **YES** (Chen et al.) | **NO** | **NO** | RSICD, RSITMD, UCM | Upstream (NOT VERIFIED) | AdamW | Upstream (NOT VERIFIED) | `checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt` | 84.2% Top-1 (UCM) | **UPSTREAM PRETRAINED** |
| **BigEarthNet-v2.0** | **YES** (BIFOLD) | **NO** | **NO** | BigEarthNet-MM (590k pairs) | 100 (Upstream) | AdamW | 1e-3 (Upstream) | `checkpoints/bigearthnet/model.safetensors` | 86.4% mAP | **UPSTREAM PRETRAINED** |
| **General RS-VLM** | **YES** (Salesforce) | **NO** | **NO** | VQA-v2, COCO, CC3M | Upstream (NOT VERIFIED) | AdamW | Upstream (NOT VERIFIED) | `checkpoints/general_rs_vlm/model.safetensors` | 78.25% (VQA-v2) | **UPSTREAM PRETRAINED** |
| **Evidence Adjudicator** | **NO** (Algorithmic) | **NO** | **NO** | None (Rule-based) | N/A | None | None | *No Checkpoint (Code)* | 100% Conflict Catch | **DETERMINISTIC ENGINE** |

---

## 2. In-House Training Details (CDVQA)

SatQuery AI's flagship trained neural model is the **CDVQA** bi-temporal change question answering network:
- **Training Script**: `training/vqa/train_cdvqa.py`
- **Data Pipeline**: `training/vqa/dataset.py`
- **Hardware Used**: Single NVIDIA GPU with PyTorch CUDA.
- **Batch Size**: 32.
- **Loss Function**: Cross-Entropy Loss with label smoothing ($0.1$).
- **Optimizer**: `torch.optim.AdamW(lr=1e-3, weight_decay=1e-4)`.
- **Learning Rate Schedule**: Cosine Annealing learning rate scheduler across 5 epochs.
- **Backbone Freezing**: ResNet-18 visual feature extractor initialized with ImageNet weights and frozen; CEM cross-attention module, question GRU, and classifier MLP trained end-to-end.
- **Resulting Checkpoint**: `checkpoints/cdvqa/cdvqa_satquery.pt` (46 MB).
