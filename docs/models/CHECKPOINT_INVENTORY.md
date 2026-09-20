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
| `eurosat_classifier` | `best_model.pt` | `checkpoints/eurosat_efficientnet_b0/best_model.pt` | 47 MB | PyTorch `.pt` | **Delivered 2026-09-20** | Ayushman delivery / EuroSAT RGB (Sentinel-2) | EfficientNet-B0, `Linear(1280, 10)` head | YES — sha256 `dbbfa69d…12347`, **no manifest was supplied**, hash computed here | YES — `strict=True` load + forward to `(1, 10)` | **AVAILABLE** |
| `flood_segmenter` | `best.pt`, `last.pt` | `checkpoints/flood_seg/{best.pt,last.pt}` | 45 MB (2 x 23,442,311 B) | PyTorch `.pt` | **Delivered 2026-09-20** | Ayushman delivery / Sen1Floods11 (no upstream repo — trained from scratch) | U-Net from scratch, 16-channel input, 2 classes | YES — both sha256 match `SHA256SUMS.json` | LOADS ONLY — `strict=True` passes, **no mask is ever returned** | **NOT_CONFIGURED** (training-time normalisation unknown, Q-041 §5) |
| *(none — not registered)* | `PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` | `checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` | 3.7 GB | PyTorch Lightning `.ckpt` | **Delivered 2026-09-20** | Ayushman delivery / terratorch + Prithvi-EO-2.0 300M, HLS Burn Scars | ViT-L (24 x 1024) + `UNetDecoder` 512/256/128/64, 2 classes | YES — sha256 and byte size match `model_manifest.json` | NO — cannot be loaded; no adapter exists | **UNAVAILABLE** (`terratorch`, `lightning`, `einops` missing — deliberately not installed, Q-041 §6) |

---

## 2. Storage Aggregation

- **Total Weight Files**: 14 files across 11 model checkpoints.
- **Combined Disk Footprint**: **7.884 GB** — 3.896 GB for the ten original files plus **3.987 GB**
  (3,987,324,579 bytes) for the three checkpoints delivered 2026-09-20 (project/qna.md Q-041).
- **The 2026-09-20 delivery, measured with `du`/`ls` rather than taken from the delivery notes**:

| Directory | `du -sh` | Exact bytes | Files |
| :--- | :--- | :--- | :--- |
| `checkpoints/eurosat_efficientnet_b0` | 47 MB | 48,724,792 | `best_model.pt` |
| `checkpoints/flood_seg` | 45 MB | 46,884,622 | `best.pt`, `last.pt` — 23,442,311 B each |
| `checkpoints/burnscars_seg` | 3.7 GB | 3,891,715,165 | the `.ckpt` — 3.62 GiB |

  The burn-scar `.ckpt` alone is just under half the whole footprint (3.892 of 7.884 GB), and about
  two thirds of it is AdamW optimiser state: stripped to `state_dict` it is about 1.2 GB, or ~650 MB
  at fp16. Neither the flood nor the burn-scar checkpoint serves anything today — see
  `docs/models/flood.md` and `docs/models/burnscars.md`.
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
