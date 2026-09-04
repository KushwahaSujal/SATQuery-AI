# SatQuery AI — Comprehensive Model Comparison Matrix

This matrix provides a technical comparison across every neural network, foundation model, vision-language architecture, and algorithmic reasoning engine in the **SatQuery AI** platform.

---

## 1. Active & Implemented Model Matrix

| Model / Component | Primary Task | Input Modality | Output Type | Parameters | Checkpoint Filename | Checkpoint Size | SatQuery Trained? | Primary Training Dataset | Official Benchmark | SatQuery Measured Latency | SatQuery Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Grounding DINO** | Open-Vocabulary Object Grounding | Optical RGB + Text | Normalized Bounding Boxes + Logits | ~172M | `groundingdino_swint_ogc.pth` | 694 MB | NO (Upstream Pretrained) | Objects365, GoldG, Cap4M | 52.5 AP (COCO minival) | 1.408s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **V4 Spatial Reasoner** | Referring Expression & Spatial Disambiguation | Bounding Box Proposals + Query + Pixels | Disambiguated Top-1 Box + Attribute Scores | 0 (Algorithmic) | *Code Implemented* | 0 MB | NO (Deterministic) | None | N/A | < 5 ms (CPU) | **IMPLEMENTED & VERIFIED** |
| **SAM 2.1** | Sub-Pixel Polygon Mask Segmentation & Video Tracking | Image / Video + Box Prompt | High-Resolution Binary Mask ($H \times W, \{0, 1\}$) | ~46M (Hiera-S) | `sam2_hiera_base_plus.pt` | 184 MB | NO (Upstream Pretrained) | SA-V (50.9K videos), SA-1B (11M images) | 75.0 J&F (SA-V) | 1.105s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **ChangeFormerV6** | Bi-Temporal Surface Change Detection | Dual Registered Optical Rasters ($T_1, T_2$) | Dense Change Mask + Probability Heatmap | ~13.5M | `satquery_changeformer_best.pt` | 164 MB | Fine-Tuned / Verified | LEVIR-CD, DSIFN-CD | 90.4% F1, 82.5% IoU | 0.874s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **CDVQA** | Bi-Temporal Change Visual Question Answering | Dual Optical Rasters ($T_1, T_2$) + Question | 19-Class Closed Vocabulary Answer | ~23.8M | `cdvqa_satquery.pt` | 46 MB | **YES (Trained In-House)** | SECOND + CDVQA (48k pairs) | 72.1% OA (Upstream) | 0.983s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **DOFA** | Multisensor Wavelength Foundation Embeddings | Optical, Multispectral, or SAR Radar | 197 Tokens $\times$ 768-dim Visual Embeddings | ~111M | `DOFA_ViT_base_e100.pth` | 552 MB | NO (Upstream Pretrained) | MultiSensor EO (S1, S2, Landsat, GaoFen) | 89.2% Top-1 (Linear Probe) | 0.812s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **Optical-SAR Fusion** | Cross-Attention Multi-Modal Synthesis | Aligned Optical RGB + SAR Radar ($VV, VH$) | 19 Land Cover Classes + Roughness + Built-Up | ~4.7M (+ DOFA) | `satquery_fusion.pth` | 18 MB | **YES (Designed In-House)** | Pretrained DOFA Embeddings | N/A | 0.210s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **RemoteCLIP** | RS Zero-Shot Categorization & Scene Retrieval | Optical Raster + Candidate Text Labels | Zero-Shot Category + Cosine Similarity | ~151M | `RemoteCLIP-ViT-B-32.pt` | 605 MB | NO (Upstream Pretrained) | RSICD, RSITMD, UCM, Sydney | 84.2% Top-1 (UCM) | 0.285s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **BigEarthNet-v2.0** | 12-Channel Land-Cover Classification | 10 Sentinel-2 Optical + 2 Sentinel-1 SAR Bands | 19 Corine Multi-Label Probabilities | ~23.5M | `model.safetensors` | 94.5 MB | NO (Upstream Pretrained) | BigEarthNet-MM (590k S1/S2 pairs) | 86.4% mAP (All-Modalities) | 0.152s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **General RS-VLM** | Open-Ended Conversational Scene VQA | Optical Satellite Image + Free-Form Question | Natural Language Text Answer | ~385M | `model.safetensors` | 1.54 GB | NO (Upstream Pretrained) | VQA-v2, COCO, Visual Genome | 78.25% (VQA-v2) | 0.820s (CUDA) | **IMPLEMENTED & VERIFIED** |
| **Evidence Adjudicator** | Multi-Model Anomaly Detection & Adjudication | Multi-Model Predictions (Masks, Answers, Indices) | Adjudicated Consensus + Audit Trail | 0 (Algorithmic) | *Code Implemented* | 0 MB | NO (Deterministic) | None | N/A | < 0.5 ms (CPU) | **IMPLEMENTED & VERIFIED** |

---

## 2. Evaluated Candidates & Historical Strategies

| Model / Strategy | Type | Parameter Count | VRAM Requirement | Why Evaluated | Outcome / Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V1 Grounding** | Algorithmic Strategy | 0 | Negligible | Baseline detector confidence | **HISTORICAL BASELINE**: Fails on 78% of referring queries. Replaced by V4. |
| **V2 Grounding** | Algorithmic Strategy | 0 | Negligible | Lexical prompt cleaning | **HISTORICAL STEPPING STONE**: Improved IoU (+29%), but lacked spatial awareness. |
| **V3 Grounding** | Algorithmic Strategy | 0 | Negligible | Static spatial quadrant anchors | **HISTORICAL PREDECESSOR**: Showed static weights penalize non-spatial queries. Led to V4. |
| **GeoChat-7B** | Multimodal LLM | 7.2B | ~14.5 GB | Grounded RS conversations | **EVALUATED CANDIDATE**: Exceeds 8 GB laptop GPU limits. Retained in `third_party/GeoChat/`. |
| **EarthDial-7B** | Multimodal LLM | 7.2B | ~14.5 GB | Multi-turn satellite dialogue | **NOT ADOPTED**: High VRAM; cannot output dense polygon masks. |
| **RSCoVLM-7.5B** | Multimodal LLM | 7.5B | ~15.0 GB | High accuracy on RSVQA | **NOT ADOPTED**: High VRAM; cannot perform bi-temporal change detection. |

---

## 3. Computational Footprint Summary

- **Total Disk Space for Checkpoints**: **~3.89 GB**
- **Total Peak VRAM with Full Specialist Stack**: **~4.8 GB** (Comfortably fits inside 8 GB GDDR6 on NVIDIA GeForce RTX 5050 Laptop GPU)
- **End-to-End Latency Profile**:
  - Grounding Pipeline (DINO + V4 + SAM 2): **~2.5 seconds**
  - Bi-Temporal Change & VQA Pipeline (ChangeFormer + CDVQA + Adjudicator): **~1.8 seconds**
  - Multisensor Fusion Pipeline (DOFA + Cross-Attention Fusion): **~1.0 second**
  - Single-Image Conversational VQA (General RS-VLM): **~0.8 seconds**
