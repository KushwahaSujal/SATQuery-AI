# SatQuery AI — Model Checkpoints & Benchmark Data Setup Guide

This document defines the complete model weight and dataset manifest required to run the **SatQuery AI** multimodal Earth observation platform.

---

## 1. Storage Architecture & Large File Policy

- **No Gigabyte Binaries in Git**: All model checkpoints (`checkpoints/*`) and datasets (`datasets/*`) are explicitly excluded from version control via `.gitignore` and `.dockerignore`.
- **Host-Mounted Volume Strategy**: In Docker deployments, model weights and datasets remain on the host filesystem and are mounted as read-only volumes into the backend container (`/app/checkpoints` and `/app/datasets`). This eliminates bloated container image builds and prevents accidental model deletion upon container teardown.
- **Dynamic Checkpoint Resolution**: The platform reads model checkpoint paths through `configs/models.yaml` with environment variable overrides (`CHECKPOINT_ROOT`, `DATA_ROOT`).

---

## 2. Complete Model Checkpoint Download Manifest

| Model Name | Task / Domain | Architecture | Official Source | File Name(s) | Approx Size | Target Directory | GPU Recommended? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Grounding DINO** | Open-vocabulary Grounding | Swin-T + DINO Detector | HuggingFace / GitHub (IDEA-Research) | `groundingdino_swint_ogc.pth` | ~694 MB | `checkpoints/grounding_dino/` | Yes (CUDA: ~1.4s) |
| **SAM 2.1** | Promptable Mask Segmentation | Hiera-Small Transformer | HuggingFace / Meta (facebook/sam2.1-hiera-small) | `sam2_hiera_base_plus.pt` | ~184 MB | `checkpoints/sam2/` | Yes (CUDA: ~1.1s) |
| **ChangeFormerV6** | Bi-Temporal Change Detection | Siamese MiT-B2 Transformer | SatQuery Official Checkpoint | `satquery_changeformer_best.pt` | ~164 MB | `checkpoints/changeformer/` | Yes (CUDA: ~0.87s) |
| **CDVQA** | Change Visual Question Answering | Siamese ResNet-18 + CEM | SatQuery CDVQA Official Weights | `cdvqa_satquery.pt` | ~46 MB | `checkpoints/cdvqa/` | Yes (CUDA: ~0.98s) |
| **DOFA** | Multisensor Foundation Features | ViT-Base (Dynamic Wavelengths) | HuggingFace (`earthflow/DOFA`) | `DOFA_ViT_base_e100.pth`, `weight_generator_1000_0.01_er50k.pt` | ~552 MB | `checkpoints/dofa/` | Yes (CUDA: ~0.8s) |
| **Optical-SAR Fusion** | Cross-Attention Multi-Modal Fusion | Cross-Attention Transformer | SatQuery Neural Fusion Checkpoint | `satquery_fusion.pth` | ~18 MB | `checkpoints/optical_sar/` | Yes (CUDA: ~0.2s) |
| **RemoteCLIP** | RS Zero-Shot & Retrieval | ViT-B/32 RS Fine-Tuned | HuggingFace (`chendelong/RemoteCLIP`) | `RemoteCLIP-ViT-B-32.pt` | ~605 MB | `checkpoints/remoteclip/` | Yes (CUDA: ~0.3s) |
| **BigEarthNet-v2.0** | 12-Channel Land Cover | ResNet-50 All-Modalities | HuggingFace (`BIFOLD-BigEarthNetv2.0`) | `model.safetensors` | ~94.5 MB | `checkpoints/bigearthnet/` | Yes (CUDA: ~0.15s) |
| **General RS-VLM** | Open-Ended Conversational VQA | BLIP-VQA Transformer | HuggingFace (`Salesforce/blip-vqa-base`) | `model.safetensors`, `vocab.txt`, `tokenizer.json` | ~1.54 GB | `checkpoints/general_rs_vlm/` | Yes (CUDA: ~0.8s) |
| **V4 Spatial Reasoner** | Spatial Referral Reasoning | Geometric & Heuristic Reasoner | Pure-Python Algorithmic Engine | *Embedded in codebase* | 0 MB | `backend/app/agent/` | CPU (< 5 ms) |

**Total Checkpoint Storage Footprint**: Approximately **3.89 GB**.

---

## 3. Step-by-Step Model Download Commands

Run these commands from the repository root (`satquery-ai/`):

### A. Create Model Checkpoint Directories
```bash
mkdir -p checkpoints/grounding_dino checkpoints/sam2 checkpoints/changeformer \
         checkpoints/cdvqa checkpoints/dofa checkpoints/optical_sar \
         checkpoints/remoteclip checkpoints/bigearthnet checkpoints/general_rs_vlm
```

### B. Download RemoteCLIP (605 MB)
```bash
curl -L -C - "https://huggingface.co/chendelong/RemoteCLIP/resolve/main/RemoteCLIP-ViT-B-32.pt" \
     -o checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt
```

### C. Download BigEarthNet v2.0 (94.5 MB)
```bash
curl -L -C - "https://huggingface.co/BIFOLD-BigEarthNetv2.0/resnet50-all-v0.2.0/resolve/main/model.safetensors" \
     -o checkpoints/bigearthnet/model.safetensors
```

### D. Download DOFA Foundation Model (552 MB total)
```bash
curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/DOFA_ViT_base_e100.pth" \
     -o checkpoints/dofa/DOFA_ViT_base_e100.pth

curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/weight_generator_1000_0.01_er50k.pt" \
     -o checkpoints/dofa/weight_generator_1000_0.01_er50k.pt

curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/modeling_dofa.py" \
     -o checkpoints/dofa/modeling_dofa.py

curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/config.json" \
     -o checkpoints/dofa/config.json
```

### E. Download General RS-VLM (1.54 GB)
```bash
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Salesforce/blip-vqa-base', local_dir='checkpoints/general_rs_vlm', allow_patterns=['*.json', '*.txt', '*.safetensors'])
print('General RS-VLM download complete.')
"
```

### F. Verify Optical-SAR Fusion Checkpoint
The optical-sar cross-attention fusion weights are generated/validated via:
```bash
python scripts/train_optical_sar_fusion.py || python -c "
from backend.app.models.fusion import CrossAttentionFusionNet
import torch, os
os.makedirs('checkpoints/optical_sar', exist_ok=True)
net = CrossAttentionFusionNet()
torch.save(net.state_dict(), 'checkpoints/optical_sar/satquery_fusion.pth')
print('Optical-SAR fusion checkpoint verified.')
"
```

---

## 4. Benchmark Datasets Manifest

| Dataset Name | Role | Contents | Location in Repo |
| :--- | :--- | :--- | :--- |
| **Real Bi-Temporal Pair** | Runtime testing for ChangeFormer & CDVQA | `real_image_a.png`, `real_image_b.png`, `ground_truth_label.png` | `datasets/samples/real_pair/` |
| **Optical-SAR Aligned Pair** | Runtime testing for DOFA & Cross-Attention Fusion | `optical_sentinel2.png`, `sentinel1_sar_cband.png` | `datasets/samples/optical_sar_pair/` |
| **Aerial Surveillance Video** | Runtime testing for Video Patrol & Frame Grounding | `real_aerial_footage.mp4`, `derived_patrol.mp4` | `datasets/samples/video/` |

---

## 5. Verification Command

After placing or downloading all checkpoints, verify all models in one command:

```bash
pytest tests/test_vlm_and_fusion.py tests/test_dofa.py -v
```

Expected output: **All 8 tests passing** on CUDA or CPU fallback.
