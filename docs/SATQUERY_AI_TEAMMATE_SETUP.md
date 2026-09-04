# SatQuery AI — Teammate Setup & Reproducible Deployment Guide

> **Document Version**: 2.0.0  
> **Target Audience**: Platform Engineers, Machine Learning Researchers, Full-Stack Developers  
> **Scope**: Local Bare-Metal, Docker Compose, GPU Acceleration, PostgreSQL Database, and Full Multimodal Model Stack

---

## 1. Project Overview
**SatQuery AI** is an advanced, production-grade agentic remote-sensing intelligence platform designed for Earth Observation (EO). It synthesizes state-of-the-art vision-language models, foundation encoders, bi-temporal change transformers, and segmentation networks to answer complex natural-language queries over satellite, aerial, and radar imagery:
- **Zero-Shot Object Grounding**: Grounding DINO + V4 Spatial Reasoner + SAM 2.1.
- **Bi-Temporal Change Detection**: ChangeFormerV6 (Siamese MiT-B2) with pixel-level area accounting and vector polygonization.
- **Change Visual Question Answering (CDVQA)**: Siamese ResNet-18 + CEM cross-attention reasoning.
- **Multisensor Foundation Embeddings**: DOFA ViT-Base with dynamic wavelength conditioning across optical ($0.49\text{--}0.665\,\mu\text{m}$) and SAR ($55,000\,\mu\text{m}$).
- **Optical-SAR Cross-Attention Fusion**: Dedicated cross-modal transformer fusing optical and radar polarizations for surface roughness and built-up index estimation.
- **General RS Vision-Language Model**: BLIP-VQA transformer for conversational scene understanding.
- **Multimodal Land-Cover Classification**: BigEarthNet-v2.0 12-channel ResNet-50.

---

## 2. System Requirements
- **Operating System**: Windows 11 (64-bit), Ubuntu 22.04+ LTS, or macOS (Apple Silicon M1/M2/M3 with MPS fallback).
- **Disk Space**: 
  - Minimum 15 GB free disk space (Codebase: ~50 MB, Checkpoints: ~3.9 GB, Docker base images & dependencies: ~8 GB).
- **Network**: Broadband internet connection for initial model weight downloads from HuggingFace.

---

## 3. Hardware Requirements
- **CPU**: Multi-core processor (Intel Core i5/i7/i9 10th gen+, AMD Ryzen 5000+, or Apple Silicon).
- **RAM**:
  - Minimum: 16 GB System RAM.
  - Recommended: 24 GB+ System RAM.
- **GPU (Recommended for fast inference)**:
  - NVIDIA RTX GPU with compute capability $\ge 7.5$ (e.g. RTX 3060, RTX 4060, RTX 5050 Laptop GPU, A100, T4).
  - Minimum VRAM: 6 GB. Recommended: 8 GB+ GDDR6.
- **CPU Fallback**: Fully supported. All models gracefully run on CPU if no CUDA GPU is detected.

---

## 4. Software Requirements
| Software | Required Version | Verification Command |
| :--- | :--- | :--- |
| **Python** | 3.11 or 3.12 (Python 3.14 supported for bare-metal) | `python --version` |
| **Node.js** | 18.x or 20.x LTS | `node --version` |
| **npm** | 9.x or 10.x | `npm --version` |
| **Docker & Compose** | Docker Desktop 4.25+ / Compose v2 | `docker --version; docker compose version` |
| **PostgreSQL** | 15+ or 16+ (Docker or local service) | `psql --version` |
| **Git** | 2.30+ | `git --version` |

---

## 5. Git Clone
Clone the repository to your local workspace:
```bash
git clone https://github.com/satquery/satquery-ai.git
cd satquery-ai
```

---

## 6. Environment File Setup
Create your local `.env` configuration file from the provided template:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```
Open `.env` and verify that the database credentials and ports match your local environment.

---

## 7. Docker Installation
If running via Docker:
1. **Windows**: Download and run `Docker Desktop Installer.exe` (located in `C:\Users\<user>\Downloads` or from [docker.com](https://www.docker.com/products/docker-desktop/)).
   - Ensure the **WSL 2 backend** option is checked during installation.
   - Start Docker Desktop and ensure the whale icon is running in the system tray.
2. **Ubuntu / Linux**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   ```

---

## 8. NVIDIA GPU Setup (Optional but Recommended)
For GPU acceleration inside Docker containers on Windows / Linux:
1. Ensure the latest NVIDIA Game Ready / Studio Driver is installed.
2. On Windows: Docker Desktop with WSL 2 automatically forwards the host NVIDIA GPU to containers.
3. On Linux: Install the **NVIDIA Container Toolkit**:
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```
4. In `docker-compose.yml`, uncomment lines under `deploy.resources.reservations.devices` to pass the GPU to the backend container.

---

## 9. Model Checkpoint Downloads
Model weights are not stored in Git. Follow [docs/SATQUERY_AI_MODEL_DATA_SETUP.md](file:///c:/Users/user/Desktop/SATQuery/satquery-ai/docs/SATQUERY_AI_MODEL_DATA_SETUP.md) or run:
```bash
# 1. Create target directories
mkdir -p checkpoints/grounding_dino checkpoints/sam2 checkpoints/changeformer \
         checkpoints/cdvqa checkpoints/dofa checkpoints/optical_sar \
         checkpoints/remoteclip checkpoints/bigearthnet checkpoints/general_rs_vlm

# 2. RemoteCLIP (605 MB)
curl -L -C - "https://huggingface.co/chendelong/RemoteCLIP/resolve/main/RemoteCLIP-ViT-B-32.pt" \
     -o checkpoints/remoteclip/RemoteCLIP-ViT-B-32.pt

# 3. BigEarthNet v2.0 (94.5 MB)
curl -L -C - "https://huggingface.co/BIFOLD-BigEarthNetv2.0/resnet50-all-v0.2.0/resolve/main/model.safetensors" \
     -o checkpoints/bigearthnet/model.safetensors

# 4. DOFA Multisensor Foundation Model (552 MB)
curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/DOFA_ViT_base_e100.pth" \
     -o checkpoints/dofa/DOFA_ViT_base_e100.pth
curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/weight_generator_1000_0.01_er50k.pt" \
     -o checkpoints/dofa/weight_generator_1000_0.01_er50k.pt
curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/modeling_dofa.py" \
     -o checkpoints/dofa/modeling_dofa.py
curl -L -C - "https://huggingface.co/earthflow/DOFA/resolve/main/config.json" \
     -o checkpoints/dofa/config.json

# 5. General RS-VLM (1.54 GB)
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Salesforce/blip-vqa-base', local_dir='checkpoints/general_rs_vlm', allow_patterns=['*.json', '*.txt', '*.safetensors'])
print('General RS-VLM download complete.')
"
```

---

## 10. Dataset Downloads
Benchmark datasets are included in the repository under `datasets/samples/`:
- `datasets/samples/real_pair/`: Bi-temporal change detection and CDVQA benchmark images.
- `datasets/samples/optical_sar_pair/`: Aligned optical and SAR radar imagery.
- `datasets/samples/video/`: Video surveillance footage for temporal tracking.

---

## 11. Directory Structure
```text
satquery-ai/
├── backend/
│   ├── app/
│   │   ├── agent/             # Autonomous agent controller, planning, tools
│   │   ├── api/               # FastAPI endpoints & routes
│   │   ├── db/                # PostgreSQL SQLAlchemy models & Alembic migrations
│   │   ├── evidence/          # Spatial vectorization, bounding boxes, adjudication
│   │   ├── geo/               # Raster inspection, CRS reprojection, statistics
│   │   ├── models/            # Neural adapters (Grounding, SAM2, ChangeFormer, DOFA, etc.)
│   │   ├── orchestration/     # DAG dependency graph & capability routing
│   │   └── video/             # Keyframe extraction & temporal analysis
│   ├── requirements.txt       # Backend dependencies
│   └── Dockerfile             # Production backend container definition
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js 14 App Router (layout, page, globals.css)
│   │   └── components/        # React UI panels (Results, Viewer, Layers, Status)
│   ├── package.json           # Node.js dependencies
│   └── Dockerfile             # Multi-stage production container definition
├── checkpoints/               # Model weights (host-mounted, excluded from Git)
├── configs/
│   └── models.yaml            # Master model registry configuration
├── datasets/                  # Benchmark test pairs and video samples
├── docs/                      # Technical contracts and onboarding guides
├── results/                   # Persisted run outputs, GeoTIFFs, and PDF audit reports
├── tests/                     # 120+ Pytest automated verification suite
├── .env.example               # Configuration template
├── docker-compose.yml         # Container orchestration manifest
└── alembic.ini                # Database migration configuration
```

---

## 12. Environment Variables
Refer to `.env.example` for all configurable keys:
- `SATQUERY_DEVICE`: Set to `auto` (default), `cuda`, or `cpu`.
- `DATABASE_URL`: Connection string for PostgreSQL (`postgresql+asyncpg://satquery:satquery@postgres:5432/satquery`).
- `BACKEND_API_URL`: Internal container communication URL (`http://backend:8000`).
- `NEXT_PUBLIC_API_BASE_URL`: Browser-facing API endpoint (`http://localhost:8000`).

---

## 13. Database Setup
PostgreSQL handles persistent tracking of analysis jobs, execution steps, models run, visualization layers, and video flags.
- When using Docker Compose, the `postgres` service starts automatically on port `5432`.
- When using local bare-metal, ensure a PostgreSQL instance is running on `localhost:5432` with user `satquery` and database `satquery`.

---

## 14. Database Migrations
Apply the initial schema using Alembic:
```bash
# In Docker:
docker compose exec backend alembic upgrade head

# On Bare-Metal:
alembic upgrade head
```
This generates all 10 relational tables: `analysis_jobs`, `uploaded_files`, `model_runs`, `execution_steps`, `analysis_results`, `evidence_artifacts`, `visualization_layers`, `spatial_extents`, `video_analyses`, and `video_flags`.

---

## 15. Starting the Stack

### Option A: Via Docker Compose (Recommended for Production)
```bash
# 1. Build container images
docker compose build

# 2. Launch services in the background
docker compose up -d

# 3. Apply database migrations
docker compose exec backend alembic upgrade head
```

### Option B: Via Local Bare-Metal (Recommended for Active Development)
```bash
# 1. Start backend in terminal 1
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. Start frontend in terminal 2
cd frontend
npm start -- -p 3000
```

---

## 16. Verifying Services
Check the running containers and health status:
```bash
docker compose ps
```
Both `satquery-postgres`, `satquery-backend`, and `satquery-frontend` must show `Up (healthy)`.

---

## 17. Frontend URL
Open your browser and navigate to:
**`http://localhost:3000`**

---

## 18. Backend URL
Verify the API root:
**`http://localhost:8000/api/health`**  
Expected JSON output:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "device": "cuda",
  "models_available": {
    "general_rs_vlm": true,
    "grounding_dino": true,
    "sam2": true,
    "changeformer": true,
    "cdvqa": true,
    "dofa": true,
    "satquery_optical_sar_fusion": true,
    "remoteclip": true,
    "bigearthnet": true
  },
  "database_connected": true
}
```

---

## 19. Swagger / OpenAPI Documentation
Interactive REST API documentation is available at:
**`http://localhost:8000/docs`**

---

## 20. Database / pgAdmin Access
To inspect the relational database externally:
- **Host**: `localhost`
- **Port**: `5432`
- **Maintenance Database**: `satquery`
- **Username**: `satquery`
- **Password**: *(Refer to your `.env` file)*

---

## 21. First Model Test (Quick Verification)
Run the automated VLM and fusion test suite:
```bash
pytest tests/test_vlm_and_fusion.py -v
```
All 4 tests should pass in under 15 seconds.

---

## 22. Grounding Test (Grounding DINO + SAM 2.1)
- **Upload**: Single image (`datasets/samples/real_pair/real_image_b.png`).
- **Query**: `"Highlight the vehicle in the image."`
- **Expected Result**: Single image grounding task selected; bounding box coordinates generated; SAM 2.1 mask segmented.

---

## 23. Change Detection Test (ChangeFormerV6)
- **Upload**: Two images: `real_image_a.png` (Before) and `real_image_b.png` (After).
- **Query**: `"Show where new buildings were constructed between these dates."`
- **Expected Result**: 15,534 changed pixels detected; 23.70% change ratio; continuous probability heatmap and GeoJSON generated.

---

## 24. CDVQA Test (Change Visual Question Answering)
- **Upload**: Two images: `real_image_a.png` and `real_image_b.png`.
- **Query**: `"What changed between these two acquisition dates?"`
- **Expected Result**: CDVQA Siamese network answers `"10% to 20% change."`.

---

## 25. Multispectral Test (BigEarthNet-v2.0)
- **Upload**: `real_image_b.png`.
- **Query**: `"Classify land cover using multispectral representations."`
- **Expected Result**: 12-channel classification predicting land-cover categories.

---

## 26. SAR & Optical-SAR Fusion Test
- **Upload**: `datasets/samples/optical_sar_pair/optical_sentinel2.png` and `sentinel1_sar_cband.png`.
- **Query**: `"Perform joint optical-SAR cross-attention fusion and evaluate terrain cover and radar roughness."`
- **Expected Result**: Identified `Permanently irrigated land`, SAR roughness index: `0.524`, built-up index: `0.364`.

---

## 27. Video Test (Video Frame Grounding)
- **Upload**: `datasets/samples/video/derived_patrol.mp4`.
- **Query**: `"Track vehicle activity across this video sequence."`
- **Expected Result**: Video sampled at uniform frame intervals; objects detected; keyframe summary produced.

---

## 28. Visualization Test
In the web interface:
1. Use the **Layer Selector** dropdown to switch between *RGB Preview*, *Change Probability Heatmap*, *Binary Mask*, and *Change Vector Overlay*.
2. Adjust the **Opacity Slider** (0% to 100%).
3. Click anywhere on the imagery to inspect pixel coordinates, raw reflectance, and probability values in the **Pixel Inspector**.

---

## 29. API Test via curl
```bash
# 1. Check health
curl -s http://localhost:8000/api/health

# 2. Check model capabilities
curl -s http://localhost:8000/api/models
```

---

## 30. Common Errors & Fixes
- **Error: `ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5432)`**:
  - *Cause*: PostgreSQL service is not started.
  - *Fix*: Run `docker compose up -d postgres` or start the local PostgreSQL Windows service.
- **Error: `ModuleNotFoundError: No module named 'backend'`**:
  - *Cause*: `PYTHONPATH` does not point to the repository root.
  - *Fix*: Set `PYTHONPATH=.` before running scripts.

---

## 31. GPU Troubleshooting
- Verify CUDA availability:
  ```bash
  python -c "import torch; print('CUDA Available:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
  ```
- If CUDA returns `False` despite having an NVIDIA GPU, install the PyTorch CUDA wheel:
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
  ```

---

## 32. Model Checkpoint Troubleshooting
- If a model reports `NOT_CONFIGURED`, check `configs/models.yaml` to confirm the checkpoint file path exists on disk.
- Never manually edit model weights; verify checksums against the download manifest.

---

## 33. Database Troubleshooting
- Reset database schema cleanly:
  ```bash
  alembic downgrade base
  alembic upgrade head
  ```

---

## 34. Docker Troubleshooting
- Inspect container startup logs:
  ```bash
  docker compose logs backend
  docker compose logs postgres
  ```

---

## 35. How to Stop the Stack
```bash
docker compose down
```

---

## 36. How to Restart the Stack
```bash
docker compose restart
```

---

## 37. How to Rebuild Images Cleanly
```bash
docker compose build --no-cache
docker compose up -d
```

---

## 38. How to Reset Database (Destructive)
```bash
docker compose down -v
```
> [!WARNING]
> The `-v` flag deletes all persistent Docker volumes, including stored PostgreSQL database tables and job records!

---

## 39. Development Workflow
1. Create a feature branch: `git checkout -b feature/model-enhancement`.
2. Write unit tests under `tests/`.
3. Verify test coverage: `pytest -q`.
4. Ensure 100% clean compilation: `python -m compileall backend/app`.

---

## 40. Git Workflow
- Keep commits atomic and informative.
- Never use `git add .` indiscriminately; verify that large checkpoints or temporary files in `results/` are not staged.

---

## 41. Security Rules
- No plaintext credentials in Git.
- Passwords and secrets must only reside in local `.env` files.
- The backend validates uploaded file extensions and bounds strictly before processing.

---

## 42. Large File Rules
- Any file exceeding 50 MB must not be committed to Git.
- Use `checkpoints/` for weights and `datasets/` for sample rasters; both directories are covered by `.gitignore`.

---

## 43. Testing
Run the complete automated test suite:
```bash
pytest
```
Expected: **120 passed in ~40 seconds, 0 failed**.

---

## 44. API Contract Reference
For complete request/response schemas and endpoints, consult [docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md](file:///c:/Users/user/Desktop/SATQuery/satquery-ai/docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md).

---

## 45. Current Model Status
All 10 models and reasoning engines are verified **AVAILABLE** on CUDA:
- `general_rs_vlm`: AVAILABLE
- `grounding_dino`: AVAILABLE
- `sam2`: AVAILABLE
- `changeformer`: AVAILABLE
- `cdvqa`: AVAILABLE
- `dofa`: AVAILABLE
- `satquery_optical_sar_fusion`: AVAILABLE
- `remoteclip`: AVAILABLE
- `bigearthnet`: AVAILABLE
- `v4_spatial_reasoner`: AVAILABLE

---

## 46. Current Limitations
- Single-image queries require at least 1 image; bi-temporal change detection requires exactly 2 images covering the same spatial extent.
- Optical-SAR fusion requires one optical/multispectral image and one SAR radar image.

---

## 47. Project Architecture Diagram

```mermaid
graph TD
    User["Web Browser / Client (Host)"]
    
    subgraph Docker Network ["Docker Network (satquery-net)"]
        Frontend["Next.js 14 Frontend Container (:3000)"]
        Backend["FastAPI Backend Container (:8000)"]
        Postgres[("PostgreSQL 16 Container (:5432)")]
        
        Frontend -->|Server-Side Rewrites / Internal DNS| Backend
        Backend -->|asyncpg / SQLAlchemy 2.0| Postgres
    end

    User -->|Direct Browser HTTP Request| Frontend
    User -.->|Direct API Access| Backend
    
    subgraph Host Machine Storage ["Host Filesystem (Mounted Volumes)"]
        Checkpoints["/checkpoints (Model Weights :ro)"]
        Datasets["/datasets (Benchmark Rasters :ro)"]
        Results["/results (Uploads, GeoTIFFs, PDFs :rw)"]
        PGData["Named Volume (satquery_postgres_data)"]
    end

    Backend -->|Read Weights| Checkpoints
    Backend -->|Read Samples| Datasets
    Backend -->|Write Artifacts| Results
    Postgres -->|Persist Tables| PGData
    
    subgraph Compute Acceleration ["Host Hardware"]
        GPU["NVIDIA GPU (CUDA Passthrough / RTX 5050)"]
        CPU["Multi-Core Host CPU (Fallback Engine)"]
    end
    
    Backend -.->|PyTorch cu128| GPU
    Backend -.->|NumPy / Shapely / OpenCV| CPU
```
