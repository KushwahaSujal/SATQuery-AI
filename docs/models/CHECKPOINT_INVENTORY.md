# SatQuery AI — Checkpoint Inventory

This inventory documents all model weights and neural checkpoints required by **SatQuery AI**, detailing their storage footprint, source provenance, verification status, and local file paths.

---

## 1. Checkpoint Master Inventory Table

| Model Key | Checkpoint Filename | Local File Path | Size on Disk | Weight Format | Origin | Source URL / Repository | Architecture | Verified on Disk? | Real Inference Tested? | Runtime Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `grounding_dino` | `groundingdino_swint_ogc.pth` | `checkpoints/grounding_dino/groundingdino_swint_ogc.pth` | 694 MB | PyTorch `.pth` | Official Upstream | IDEA-Research / HuggingFace | Swin-T + BERT-Base | YES | YES (1.408s) | **AVAILABLE** |
| `sam2` | `sam2_hiera_base_plus.pt` | `checkpoints/sam2/sam2_hiera_base_plus.pt` | 184 MB | PyTorch `.pt` | Official Upstream | Meta AI Research / GitHub | Hiera-Small / Base+ | YES | YES (1.105s) | **AVAILABLE** |
| `changeformer` | `satquery_changeformer_best.pt` | `checkpoints/changeformer/satquery_changeformer_best.pt` | 164 MB | PyTorch `.pt` | SatQuery Verified | SatQuery / Bandara & Patel | Siamese MiT-B2 | YES | YES (0.874s) | **AVAILABLE** |
| `cdvqa` | `cdvqa_satquery.pt` | `checkpoints/cdvqa/cdvqa_satquery.pt` | 46 MB | PyTorch `.pt` | **SatQuery Trained** | SatQuery AI (`training/vqa/`) | Siamese ResNet-18 + CEM + GRU | YES | YES (0.983s) | **AVAILABLE** |
| `dofa` | `DOFA_ViT_base_e100.pth` | `checkpoints/dofa/DOFA_ViT_base_e100.pth` | 447.6 MB | PyTorch `.pth` | Official Upstream | TUM / `earthflow/DOFA` | 12-Layer ViT-Base (768-dim) | YES | YES (0.812s) | **AVAILABLE** |
| `dofa_generator` | `weight_generator_1000_0.01_er50k.pt` | `checkpoints/dofa/weight_generator_1000_0.01_er50k.pt` | 104.4 MB | PyTorch `.pt` | Official Upstream | TUM / `earthflow/DOFA` | Wavelength Hypernetwork | YES | YES (Included in DOFA) | **AVAILABLE** |
| `satquery_optical_sar_fusion` | `satquery_fusion.pth` | `checkpoints/optical_sar/satquery_fusion.pth` | 18.8 MB | PyTorch `.pth` | **SatQuery Designed** | SatQuery AI (`backend/app/models/fusion.py`) | CrossAttentionFusionNet | YES | YES (0.210s) | **AVAILABLE** |
| `remoteclip` | `RemoteCLIP-ViT-B-32.pt` | `checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt` | 605.2 MB | PyTorch `.pt` | Official Upstream | `chendelong/RemoteCLIP` | ViT-B/32 CLIP | YES | YES (0.285s) | **AVAILABLE** |
| `bigearthnet` | `model.safetensors` | `checkpoints/bigearthnet/model.safetensors` | 94.5 MB | Safetensors | Official Upstream | BIFOLD / TU Berlin | 12-Channel ResNet-50 | YES | YES (0.152s) | **AVAILABLE** |
| `general_rs_vlm` | `model.safetensors` | `checkpoints/general_rs_vlm/model.safetensors` | 1.538 GB | Safetensors | Official Upstream | Salesforce / HuggingFace | ViT-Base + Cross-Attn Decoder | YES | YES (0.820s) | **AVAILABLE** |

---

## 2. Storage Aggregation

- **Total Weight Files**: 10 files across 8 model checkpoints.
- **Combined Disk Footprint**: **3.896 GB**.
- **Storage Location**: Local directory `./checkpoints` on host filesystem.
- **Volume Policy**: Mounted as read-only volume (`./checkpoints:/app/checkpoints:ro`) in Docker Compose. Checkpoint binaries are **never** committed to Git or baked into production Docker images.

---

## 3. Configuration Binding

Every checkpoint path is mapped through `configs/models.yaml` with environment variable overrides:
```yaml
# configs/models.yaml snippet
models:
  general_rs_vlm:
    checkpoint_path: "checkpoints/general_rs_vlm"
  grounding_dino:
    checkpoint_path: "checkpoints/grounding_dino/groundingdino_swint_ogc.pth"
  sam2:
    checkpoint_path: "checkpoints/sam2/sam2_hiera_base_plus.pt"
  changeformer:
    checkpoint_path: "checkpoints/changeformer/satquery_changeformer_best.pt"
  cdvqa:
    checkpoint_path: "checkpoints/cdvqa/cdvqa_satquery.pt"
  dofa:
    checkpoint_path: "checkpoints/dofa/DOFA_ViT_base_e100.pth"
  satquery_optical_sar_fusion:
    checkpoint_path: "checkpoints/optical_sar/satquery_fusion.pth"
  remoteclip:
    checkpoint_path: "checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt"
  bigearthnet:
    checkpoint_path: "checkpoints/bigearthnet/model.safetensors"
```
