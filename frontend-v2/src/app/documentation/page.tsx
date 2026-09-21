"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Boxes,
  Braces,
  CheckCircle2,
  Check,
  ChevronDown,
  Clock3,
  Code2,
  Database,
  FileText,
  Filter,
  GitBranch,
  Layers3,
  Map as MapIcon,
  PlayCircle,
  Radar,
  Route,
  Satellite,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Video,
  X,
} from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { api } from "@/lib/api";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } } };
const itemVariant = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

type DocCategory = "All" | "Start" | "Backend" | "Frontend" | "API" | "Models" | "Operations" | "Project";

interface DocResource {
  title: string;
  path: string;
  category: Exclude<DocCategory, "All">;
  summary: string;
  tags: string[];
  status: "Authoritative" | "Live State" | "Reference" | "Research" | "Setup";
  sections: string;
  searchText?: string;
}

interface DocDetail {
  purpose: string;
  contents: string[];
  keyDetails: string[];
  useWhen: string[];
}

const hiddenDocumentPaths = new Set([
  ".commandcode/taste/taste.md",
  ".commandcode/taste/user-taste-profile/taste.md",
  ".pytest_cache/README.md",
  "frontend-v2/.commandcode/taste/taste.md",
  "frontend-v2/.commandcode/taste/user-taste-profile/taste.md",
  "frontend/AGENTS.md",
  "frontend/CLAUDE.md",
  "frontend/README.md",
  "frontend/SATQUERY_AI_FRONTEND_API_CONTRACT.md",
  "frontend/FRONTEND_POLISH.md",
  "frontend/SatQuery_FRONTEND_POLISH_2026-09-14.md",
  "project/handoff/ask-ayushman.md",
  "project/handoff/ppt-assets/README.md",
  "project/handoff/ppt-results.md",
  "project/memory.md",
  "project/plan-2026-09-14-agent-parity-geo.md",
  "project/split-ushnik-ayushman.md",
  "project/tasks.md",
  "project/decisions.md",
  "project/design.md",
  "project/phases.md",
  "project/prd.md",
  "project/qna.md",
  "project/restructure.md",
  "project/rules.md",
  "third_party/GeoChat/README.md",
  "third_party/GeoChat/docs/Customize_Component.md",
  "third_party/GeoChat/docs/Data.md",
  "third_party/GeoChat/docs/Evaluation.md",
  "third_party/GeoChat/docs/LoRA.md",
  "third_party/GeoChat/docs/MODEL_ZOO.md",
]);

const categories: DocCategory[] = ["All", "Start", "Backend", "Frontend", "API", "Models", "Operations", "Project"];

const docResources: DocResource[] = [
  {
    title: "Master Technical Documentation",
    path: "docs/SATQUERY_AI_MASTER_DOCUMENTATION.md",
    category: "Backend",
    summary: "Full product specification covering architecture, model strategy, workflows, deployment, mentor-defense notes, and scientific constraints.",
    tags: ["architecture", "models", "specification", "deployment"],
    status: "Authoritative",
    sections: "29 major sections",
  },
  {
    title: "Frontend API Contract",
    path: "docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md",
    category: "API",
    summary: "The UI integration source of truth: model inventory, upload, analyze, visual analytics, video APIs, error codes, and JSON schemas.",
    tags: ["api", "schemas", "frontend", "errors"],
    status: "Authoritative",
    sections: "7 contract areas",
  },
  {
    title: "Teammate Setup Guide",
    path: "docs/SATQUERY_AI_TEAMMATE_SETUP.md",
    category: "Operations",
    summary: "Reproducible setup for hardware, environment variables, checkpoints, Docker, database, frontend, backend, smoke tests, and troubleshooting.",
    tags: ["setup", "docker", "checkpoints", "postgres"],
    status: "Setup",
    sections: "47 setup sections",
  },
  {
    title: "Model Data Setup",
    path: "docs/SATQUERY_AI_MODEL_DATA_SETUP.md",
    category: "Operations",
    summary: "Checkpoint and dataset placement rules for Grounding DINO, SAM 2.1, ChangeFormer, CDVQA, DOFA, RemoteCLIP, BigEarthNet, and fusion weights.",
    tags: ["checkpoints", "datasets", "weights"],
    status: "Setup",
    sections: "model assets",
  },
  {
    title: "Architecture Reality Map",
    path: "project/architecture.md",
    category: "Backend",
    summary: "Code-first architecture reference for FastAPI, orchestration, model adapters, workflows, DB schema, request lifecycle, and deployment topology.",
    tags: ["backend", "flow", "database", "orchestration"],
    status: "Live State",
    sections: "6 verified sections",
  },
  {
    title: "Execution Flow Map",
    path: "project/flow.md",
    category: "Backend",
    summary: "Call-chain walkthrough for POST /api/analyze, tool fan-out, grounding, video, visual analytics, known traps, and session changes.",
    tags: ["agent", "routing", "trace", "tools"],
    status: "Live State",
    sections: "8 flow sections",
  },
  {
    title: "Pre-Demo Baseline",
    path: "project/pre-demo.md",
    category: "Project",
    summary: "Measured readiness record with working features, blockers, demo caveats, browser verification notes, and honest scorecards.",
    tags: ["demo", "verification", "blockers", "metrics"],
    status: "Live State",
    sections: "measured baseline",
  },
  {
    title: "Frontend Guide",
    path: "frontend/FRONTEND_GUIDE.md",
    category: "Frontend",
    summary: "Frontend architecture, design tokens, pages, components, data flow, React Query usage, caching, accessibility, and development commands.",
    tags: ["nextjs", "react", "design system", "components"],
    status: "Reference",
    sections: "12 frontend sections",
  },
  {
    title: "Frontend Polish Handoff",
    path: "frontend/FRONTEND_POLISH.md",
    category: "Frontend",
    summary: "Known UI polish, backend-contract mismatches, dead controls, logic errors, visual issues, and frontend feature planning notes.",
    tags: ["ui", "contract", "polish", "bugs"],
    status: "Reference",
    sections: "7 audit sections",
  },
  {
    title: "Frontend V2 Demo Run",
    path: "frontend-v2/DEMO_RUN.md",
    category: "Frontend",
    summary: "Three-command end-to-end demo instructions, backend smoke test, UI verification path, layer viewer checks, and failure triage.",
    tags: ["frontend-v2", "demo", "smoke test"],
    status: "Setup",
    sections: "4 verification steps",
  },
  {
    title: "Model Dossier Index",
    path: "docs/models/README.md",
    category: "Models",
    summary: "Index for every model dossier, grouped by grounding, segmentation, change analysis, multisensor fusion, VLMs, and evaluated candidates.",
    tags: ["models", "research", "index"],
    status: "Research",
    sections: "27 dossier links",
  },
  {
    title: "Model Pipeline Architecture",
    path: "docs/models/MODEL_PIPELINE_ARCHITECTURE.md",
    category: "Models",
    summary: "Pipeline diagrams and step-level model interaction for object grounding, change detection, optical-SAR fusion, and video patrol.",
    tags: ["pipeline", "grounding", "change", "video"],
    status: "Research",
    sections: "5 pipelines",
  },
  {
    title: "Model Comparison Matrix",
    path: "docs/models/MODEL_COMPARISON_MATRIX.md",
    category: "Models",
    summary: "Active model matrix, evaluated candidates, historical strategies, compute footprint, and high-level selection comparison.",
    tags: ["matrix", "benchmarks", "selection"],
    status: "Research",
    sections: "3 matrices",
  },
  {
    title: "Training Status",
    path: "docs/models/MODEL_TRAINING_STATUS.md",
    category: "Models",
    summary: "Training status table and in-house CDVQA details, including measured adaptation evidence and checkpoint provenance.",
    tags: ["training", "cdvqa", "status"],
    status: "Research",
    sections: "training table",
  },
  {
    title: "Root README",
    path: "README.md",
    category: "Start",
    summary: "Project overview, key capabilities, quick start for Postgres, backend, frontend, tests, and canonical documentation links.",
    tags: ["quick start", "overview", "readme"],
    status: "Reference",
    sections: "quick start",
  },
  {
    title: "Fresh Clone Demo Setup",
    path: "DEMO_SETUP.md",
    category: "Start",
    summary: "Fresh clone path for model weights, backend startup, frontend startup, and demo resources.",
    tags: ["demo", "clone", "setup"],
    status: "Setup",
    sections: "5 setup steps",
  },
  {
    title: "Decisions Log",
    path: "project/decisions.md",
    category: "Project",
    summary: "Engineering decisions, open findings, measured caveats, and places where code reality intentionally overrides older public docs.",
    tags: ["decisions", "risks", "truth"],
    status: "Live State",
    sections: "100+ decisions",
  },
  {
    title: "Development Phases",
    path: "project/phases.md",
    category: "Project",
    summary: "Roadmap from environment ground truth through model blockers, measurement, routing robustness, hardening, and conference paper work.",
    tags: ["roadmap", "phases", "planning"],
    status: "Live State",
    sections: "P0-P6",
  },
];

const modelFamilies = [
  {
    name: "Grounding and Segmentation",
    icon: MapIcon,
    docs: ["GROUNDING_DINO.md", "V4_GROUNDING_REASONING.md", "SAM2_1.md"],
    detail: "Open-vocabulary detection, query-aware spatial reasoning, and promptable masks for still imagery and video keyframes.",
  },
  {
    name: "Temporal Change",
    icon: GitBranch,
    docs: ["CHANGEFORMER_V6.md", "CDVQA.md", "EVIDENCE_ADJUDICATOR.md"],
    detail: "Bi-temporal change masks, change visual question answering, identity probes, consistency checks, and evidence summarization.",
  },
  {
    name: "Multisensor Fusion",
    icon: Radar,
    docs: ["DOFA.md", "OPTICAL_SAR_FUSION.md", "BIGEARTHNET_MULTIMODAL.md"],
    detail: "Optical, SAR, multispectral, and foundation-model strategy with explicit caveats for untrained or unwired paths.",
  },
  {
    name: "Vision-Language Candidates",
    icon: Sparkles,
    docs: ["GENERAL_RS_VLM.md", "REMOTECLIP.md", "GEOCHAT.md", "EARTHDIAL.md", "RSCOVLM.md"],
    detail: "Adopted, optional, and evaluated VLM options with integration status, failure modes, and reproducibility notes.",
  },
];

const apiEndpoints = [
  { method: "GET", path: "/api/models", area: "Model inventory", detail: "Runtime availability, checkpoint status, device, precision, lifecycle states." },
  { method: "POST", path: "/api/upload", area: "Raster ingestion", detail: "Uploads GeoTIFF, TIFF, PNG, or JPEG and returns metadata, CRS, bounds, modality, and previews." },
  { method: "POST", path: "/api/analyze", area: "Agent workflow", detail: "Routes natural-language analysis into grounding, captioning, VQA, change detection, CDVQA, or fusion DAGs." },
  { method: "GET", path: "/api/analysis/{job_id}/layers", area: "Visual analytics", detail: "Discovers source, derived, probability, mask, overlay, SAR, video, and region-map layers." },
  { method: "POST", path: "/api/analysis/{job_id}/inspect-pixel", area: "Pixel inspector", detail: "Returns band DNs, coordinates, indices, prediction class, probability, and provenance for a pixel." },
  { method: "GET", path: "/api/analysis/{job_id}/histogram/{layer_id}", area: "Histogram", detail: "Computes authentic 50-bin distributions and summary statistics over valid pixels." },
  { method: "GET", path: "/api/analysis/{job_id}/export/{layer_id}", area: "Export", detail: "Exports PNG, GeoTIFF, or GeoJSON with preserved geospatial metadata where applicable." },
  { method: "POST", path: "/api/video/analyze", area: "Video intelligence", detail: "Runs frame sampling, Grounding DINO, SAM 2.1, event aggregation, and streamable results." },
];

const workflows = [
  {
    title: "Single-Image Grounding",
    steps: "inspect_raster -> validate_single_image -> run_grounding -> run_segmentation -> generate_overlay -> generate_report",
    models: "Grounding DINO, V4 reasoner, SAM 2.1",
  },
  {
    title: "Bi-Temporal Change Detection",
    steps: "inspect_raster -> validate_temporal_pair -> run_change_detection -> calculate_statistics -> generate_overlay -> generate_report",
    models: "ChangeFormerV6",
  },
  {
    title: "Bi-Temporal Change VQA",
    steps: "inspect_raster -> validate_temporal_pair -> run_change_detection -> run_change_vqa -> generate_overlay -> generate_report",
    models: "ChangeFormerV6, CDVQA",
  },
  {
    title: "Optical + SAR Analysis",
    steps: "inspect_raster -> validate_optical_sar_pair -> run_optical_sar -> generate_report",
    models: "DOFA, optical-SAR fusion path",
  },
  {
    title: "Video Grounding",
    steps: "upload video -> sample frames -> detect objects -> segment key regions -> aggregate flags -> stream results",
    models: "Grounding DINO, SAM 2.1",
  },
];

const commands = [
  { label: "Backend", command: ".\\.venv\\Scripts\\python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000" },
  { label: "Frontend v2", command: "cd frontend-v2 && npm run dev" },
  { label: "Backend smoke", command: "cd frontend-v2 && npm run demo:smoke" },
  { label: "Frontend build", command: "cd frontend-v2 && npm run build" },
  { label: "API docs", command: "http://localhost:8000/docs" },
];

const readiness = [
  { tone: "green", label: "Verified working", value: "ChangeFormer LEVIR-CD IoU 0.7385 / F1 0.8496; 10/10 HTTP demo queries completed; GeoTIFF and AOI paths verified." },
  { tone: "green", label: "Test record", value: "Project notes record 215 passed, 0 failed after the 2026-09-14 verification run." },
  { tone: "amber", label: "Do not oversell", value: "Optical-SAR learned head is documented as untrained; BigEarthNet and some RS adaptation paths need stronger live wiring evidence." },
  { tone: "amber", label: "Known UI/API caveats", value: "Older frontend docs flag field-contract mismatches; the API contract is the source of truth for current payloads." },
];

const docDetails: Record<string, DocDetail> = {
  "docs/SATQUERY_AI_MASTER_DOCUMENTATION.md": {
    purpose: "Authoritative technical specification for the whole SatQuery AI platform. It explains the product mission, agentic remote-sensing workflows, model stack, system architecture, deployment approach, reproducibility expectations, and presentation/mentor-defense framing.",
    contents: [
      "System overview, project motivation, target use cases, and non-functional principles.",
      "AI and ML model sections for grounding, segmentation, change detection, multimodal fusion, VQA, evidence adjudication, and evaluated candidates.",
      "Backend architecture, FastAPI surface, workflow orchestration, artifact persistence, and deployment notes.",
      "Reproducibility, testing, demo preparation, and presentation guidance.",
    ],
    keyDetails: [
      "Treat this as a high-level public artifact, but verify implementation-sensitive claims against project/architecture.md and project/pre-demo.md.",
      "The master doc links into the complete model dossier directory for deep mathematical and architecture details.",
      "Useful for onboarding, presentations, research framing, and explaining why the system is agentic rather than one monolithic VLM.",
    ],
    useWhen: ["Preparing the final report or PPT", "Explaining the system end to end", "Finding the canonical project narrative"],
  },
  "docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md": {
    purpose: "Frontend and backend integration contract. It defines the payloads, aliases, error shapes, endpoint behavior, model status vocabulary, and visual analytics response formats that UI code should trust.",
    contents: [
      "Model lifecycle endpoint: GET /api/models with NOT_CONFIGURED, AVAILABLE, LOADED, and FAILED states.",
      "Raster upload and analysis workflows: POST /api/upload and POST /api/analyze.",
      "Visual analytics APIs for layers, pixel inspection, histograms, and exports.",
      "Video upload, video analysis, results retrieval, and streaming endpoints.",
      "Standard structured JSON error envelope and error code matrix.",
    ],
    keyDetails: [
      "job_id and request_id are synchronized aliases; workflow and workflow_id are synchronized aliases.",
      "No fake boxes, masks, predictions, or synthetic confidence values should be shown in UI.",
      "Grounding DINO confidence is a detection score, SAM score is not IoU, and ChangeFormer probability maps are direct model outputs.",
    ],
    useWhen: ["Building frontend pages", "Debugging missing fields", "Adding API clients or TypeScript types"],
  },
  "docs/SATQUERY_AI_TEAMMATE_SETUP.md": {
    purpose: "Full reproducible setup and operations guide for a teammate joining the project from a fresh environment.",
    contents: [
      "Hardware, software, Docker, GPU, environment variable, and repository setup requirements.",
      "Checkpoint and dataset download guidance with expected directory structure.",
      "Backend, frontend, database, pgAdmin, Swagger, and Docker startup paths.",
      "Smoke tests for Grounding DINO, SAM 2.1, ChangeFormer, CDVQA, multispectral, SAR, video, and API calls.",
      "Troubleshooting sections for GPU, checkpoints, database, Docker, rebuilds, and resets.",
    ],
    keyDetails: [
      "Swagger/OpenAPI is available at http://localhost:8000/docs when backend is running.",
      "Model weights are not committed to Git and must be placed under checkpoints/.",
      "Useful as the operational runbook when a machine is newly provisioned or broken.",
    ],
    useWhen: ["Setting up a new laptop", "Debugging environment issues", "Preparing a reproducible demo machine"],
  },
  "docs/SATQUERY_AI_MODEL_DATA_SETUP.md": {
    purpose: "Asset and checkpoint placement guide for models and datasets that cannot live in Git.",
    contents: [
      "Where each model checkpoint belongs under checkpoints/.",
      "Expected model families: Grounding DINO, SAM 2.1, ChangeFormer, CDVQA, DOFA, RemoteCLIP, BigEarthNet, General RS-VLM, and optical-SAR fusion.",
      "Dataset placement patterns and verification hints.",
      "Notes about files that are placeholders versus real trained weights.",
    ],
    keyDetails: [
      "Use this before assuming a model is broken; many failures are missing checkpoint path issues.",
      "Pairs with scripts/verify_checkpoints.py and setup_checkpoints-related notes.",
      "Project notes warn that some older claims around fusion weights must be treated carefully.",
    ],
    useWhen: ["Installing checkpoints", "Verifying model availability", "Moving the project between machines"],
  },
  "project/architecture.md": {
    purpose: "Code-first architecture map. This is the best source for how the backend and frontend actually work in the repository rather than how older marketing docs describe them.",
    contents: [
      "Backend stack: FastAPI, Pydantic, SQLAlchemy async, Alembic, PyTorch, geospatial libraries, imaging, reports, and tests.",
      "Folder structure for backend/app, orchestration, models, workflows, geo, evidence, visualization, video, artifacts, DB, schemas, configs, scripts, tests, datasets, docs, checkpoints, and results.",
      "Image analysis lifecycle from POST /api/upload to POST /api/analyze and persistence.",
      "Routing table from inputs and query signals to capabilities and DAG tools.",
      "Model-to-capability wiring and known unwired/orphaned capabilities.",
    ],
    keyDetails: [
      "The orchestration layer builds a rich DAG plan, but execution is flattened through the legacy executor.",
      "Model loading is lazy; availability is initially a filesystem check.",
      "Database failures are non-fatal; filesystem artifacts remain the source of truth.",
    ],
    useWhen: ["Changing backend behavior", "Tracing a request", "Reconciling documentation against source"],
  },
  "project/flow.md": {
    purpose: "Execution map for the real backend call chains and workflow paths.",
    contents: [
      "Entry points and primary call chain for POST /api/analyze.",
      "Tool registry fan-out and agent controller behavior.",
      "Grounding pipeline from detection through reasoning and segmentation.",
      "Separate video path and visual analytics path.",
      "Known dead ends, traps, and session-level changes.",
    ],
    keyDetails: [
      "AgentState is the mutable context passed through tools.",
      "Trace capture is central to proving the orchestration is real.",
      "Useful for locating where a capability diverges from expected behavior.",
    ],
    useWhen: ["Debugging pipeline failures", "Explaining orchestration", "Adding new tools or workflows"],
  },
  "project/pre-demo.md": {
    purpose: "Measured demo readiness and truth record. It is the most honest source for what works, what is blocked, and what must not be oversold.",
    contents: [
      "Verified baseline measurements and test-suite records.",
      "Closed and open demo-critical issues.",
      "Browser UI walkthrough notes and field-contract mismatches.",
      "Video, color-query, timestamp, and robustness findings.",
      "Explicit blockers for optical-SAR, remote-sensing adaptation evidence, and model availability verification.",
    ],
    keyDetails: [
      "Records ChangeFormer LEVIR-CD IoU 0.7385 and F1 0.8496 after the 2026-09-14 run.",
      "Warns not to demo or oversell untrained optical-SAR learned fusion.",
      "Captures what judges or mentors are likely to notice first.",
    ],
    useWhen: ["Preparing demos", "Checking credibility claims", "Prioritizing last-mile fixes"],
  },
  "frontend/FRONTEND_GUIDE.md": {
    purpose: "Frontend architecture and development guide for the original frontend codebase and shared UI conventions.",
    contents: [
      "Tech stack, project structure, design tokens, typography, layout, and component classes.",
      "Data flow, backend connection, key API endpoints, state management, and caching strategy.",
      "Page-by-page guide for command center, analysis workspace, visual analytics, video intelligence, history, model observatory, and diagnostics.",
      "Component details for map viewer, query bar, results panel, execution trace, and command palette.",
      "Error handling, performance, accessibility, and local development commands.",
    ],
    keyDetails: [
      "Use its design guidance, but verify route names and active implementation against frontend-v2.",
      "Strong warning against fabricated data in the interface.",
      "Useful for preserving visual and interaction consistency.",
    ],
    useWhen: ["Building frontend features", "Understanding UI data flow", "Checking accessibility and UX expectations"],
  },
  "frontend/FRONTEND_POLISH.md": {
    purpose: "Frontend audit and polish handoff covering incorrect data, dead controls, contract mismatches, logic errors, technical errors, and visual issues.",
    contents: [
      "Inventory of fake or hardcoded UI data that should be removed or wired.",
      "Backend-contract mismatches where UI reads fields the API does not return.",
      "Dead controls that look clickable but do nothing.",
      "Logic, technical, and visual issues found during review.",
      "Backend features that still need UI exposure.",
    ],
    keyDetails: [
      "Use this as a risk checklist before demoing the UI.",
      "Several issues are planning notes rather than verified current bugs in frontend-v2.",
      "Pairs well with the API contract when repairing field names.",
    ],
    useWhen: ["Polishing UI", "Removing fake data", "Prioritizing visible product quality fixes"],
  },
  "frontend-v2/DEMO_RUN.md": {
    purpose: "Frontend-v2 end-to-end demo runbook for proving the UI talks to the backend correctly.",
    contents: [
      "Three-command quick path for backend, backend smoke, and frontend.",
      "Backend health verification and no-UI smoke test.",
      "Frontend UI verification against http://localhost:3000.",
      "Layer viewer verification and troubleshooting notes.",
      "Lists what is already wired and what remains future work.",
    ],
    keyDetails: [
      "Best practical file when someone asks how to run the current UI.",
      "Complements README quick start with frontend-v2 specifics.",
      "Use before a live walkthrough to catch backend or layer issues.",
    ],
    useWhen: ["Running frontend-v2 locally", "Checking demo readiness", "Troubleshooting UI/backend connection"],
  },
  "docs/models/README.md": {
    purpose: "Index and navigation map for all model research dossiers.",
    contents: [
      "Master synthesis dossiers: comparison matrix, dependency graph, pipeline architecture, benchmarks, resource requirements, and training status.",
      "Object grounding and spatial referring: Grounding DINO and V1-V4 strategies.",
      "Segmentation and tracking: SAM 2.1.",
      "Change analysis and VQA: ChangeFormer, CDVQA, and Evidence Adjudicator.",
      "Multisensor and multimodal: DOFA, optical-SAR fusion, BigEarthNet, RemoteCLIP, General RS-VLM, and evaluated candidates.",
    ],
    keyDetails: [
      "Use this as the table of contents for research/model questions.",
      "Dossiers include identity, architecture, inference contracts, validation, benchmarks, limitations, and references.",
      "Separates production models from evaluated but not adopted candidates.",
    ],
    useWhen: ["Researching a model", "Finding model-specific limitations", "Writing technical report sections"],
  },
  "docs/models/MODEL_PIPELINE_ARCHITECTURE.md": {
    purpose: "Model interaction and execution architecture for major AI pipelines.",
    contents: [
      "Master system pipeline architecture.",
      "Object grounding pipeline: Grounding DINO + V4 reasoner + SAM 2.1.",
      "Bi-temporal change detection and CDVQA pipeline.",
      "Optical-SAR cross-modal fusion pipeline.",
      "Video patrol pipeline.",
    ],
    keyDetails: [
      "This is the best model document for explaining how models work together rather than individually.",
      "Useful for diagrams, demo narration, and tracing dependencies.",
      "Should be cross-checked against project/architecture.md for current source wiring.",
    ],
    useWhen: ["Explaining model orchestration", "Drawing architecture diagrams", "Planning pipeline changes"],
  },
  "docs/models/MODEL_COMPARISON_MATRIX.md": {
    purpose: "Concise comparison of active, implemented, evaluated, and historical model choices.",
    contents: [
      "Active and implemented model matrix.",
      "Evaluated candidates and historical strategies.",
      "Computational footprint summary.",
    ],
    keyDetails: [
      "Good for quickly answering why one model was selected over another.",
      "Use together with MODEL_SELECTION_RATIONALE.md for deeper justification.",
      "Helpful for slides and mentor questions.",
    ],
    useWhen: ["Comparing models", "Preparing model selection explanations", "Summarizing compute tradeoffs"],
  },
  "docs/models/MODEL_TRAINING_STATUS.md": {
    purpose: "Training status record for model components and in-house training evidence.",
    contents: [
      "Master training status table.",
      "In-house CDVQA training details.",
      "Status of trained, untrained, external, deterministic, or not-configured components.",
    ],
    keyDetails: [
      "Important for proving remote-sensing adaptation honestly.",
      "CDVQA is the strongest in-repo trained RS model story.",
      "Do not treat every registered adapter as equally trained or validated.",
    ],
    useWhen: ["Answering training questions", "Separating trained from placeholder components", "Writing model status sections"],
  },
  "README.md": {
    purpose: "Repository landing document for a fast overview and minimal setup path.",
    contents: [
      "Project overview and key capabilities.",
      "Architecture at a glance.",
      "Database, backend, frontend, and test quick-start commands.",
      "Canonical documentation links.",
    ],
    keyDetails: [
      "Use it as the first stop, not the deepest truth source.",
      "Points to the master documentation for full details.",
      "Useful for visitors who need the project shape quickly.",
    ],
    useWhen: ["Starting from scratch", "Giving someone the repo overview", "Finding primary docs"],
  },
  "DEMO_SETUP.md": {
    purpose: "Fresh-clone demo setup for getting a demo environment running quickly.",
    contents: [
      "Clone instructions.",
      "Model weights transfer and placement.",
      "Backend startup.",
      "Frontend startup.",
      "Demo resources and expected overlays.",
    ],
    keyDetails: [
      "Designed for moving from a fresh checkout to a working demo.",
      "Model weights are explicitly out of Git.",
      "Links into demo_resources for prompts and expected outputs.",
    ],
    useWhen: ["Preparing a demo machine", "Restoring missing assets", "Checking demo inputs"],
  },
  "project/decisions.md": {
    purpose: "Engineering decision and reasoning log. It records why the project made certain architectural and implementation choices, plus open findings that still need decisions.",
    contents: [
      "Inherited decisions such as specialist models, deterministic routing, lazy loading, and filesystem-first artifacts.",
      "Session decisions around restructuring, Python versioning, transaction pooler support, and source-vs-doc truth.",
      "Open findings on VRSBench metrics, router accuracy, ChangeFormer, dependency pinning, dead code, RS adaptation, optical-SAR, capability routing, and config inconsistencies.",
    ],
    keyDetails: [
      "Where public docs and source disagree, this log explains the chosen truth model.",
      "Use before changing architecture so you do not re-litigate settled choices unknowingly.",
      "Open findings are not all equal; some are blockers, some are cleanup items.",
    ],
    useWhen: ["Understanding why choices were made", "Planning changes", "Finding unresolved risks"],
  },
  "project/phases.md": {
    purpose: "Development roadmap from ground-truth environment work through model blockers, measurement, routing, hardening, and publication work.",
    contents: [
      "Reality check and P0 environment baseline.",
      "P1 blockers for remote-sensing adaptation and optical-SAR cross-modal analysis.",
      "P2 measurement and benchmarks.",
      "P3 routing completeness and robustness.",
      "P4 ISRO/SAC readiness, P5 hardening/delivery, and P6 conference paper.",
    ],
    keyDetails: [
      "Good for deciding what to do next after a demo or audit.",
      "Makes blockers explicit instead of hiding them in long docs.",
      "Complements project/pre-demo.md for current execution state.",
    ],
    useWhen: ["Planning project work", "Prioritizing blockers", "Reviewing milestone scope"],
  },
};

function normalized(text: string) {
  return text.toLowerCase();
}

function categoryForPath(path: string): Exclude<DocCategory, "All"> {
  if (path.startsWith("docs/models/")) return "Models";
  if (path.startsWith("frontend") || path.startsWith("frontend-v2/")) return "Frontend";
  if (path.startsWith("project/")) return "Project";
  if (path.includes("API") || path.includes("api")) return "API";
  if (path.includes("SETUP") || path.includes("DEMO")) return "Start";
  if (path.startsWith("backend/")) return "Backend";
  return "Operations";
}

function fallbackDetail(doc: DocResource): DocDetail {
  return {
    purpose: doc.summary,
    contents: [`Live Markdown source contains ${doc.sections}.`, `Repository path: ${doc.path}.`],
    keyDetails: ["This entry is loaded directly from the repository documentation catalog.", "Use the live source reader below for the complete document."],
    useWhen: ["Reading the complete source", "Searching related repository documentation"],
  };
}

function MarkdownPreview({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let codeLines: string[] = [];
  let inCode = false;
  let codeLanguage = "";

  const inline = (value: string): ReactNode[] => {
    const parts = value.split(/(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g);
    return parts.map((part, index) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={index} className="rounded bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--cyan)]">{part.slice(1, -1)}</code>;
      }
      if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
        return <strong key={index} className="font-semibold text-[var(--heading)]">{part.slice(2, -2)}</strong>;
      }
      if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
        return <em key={index} className="italic text-[var(--text)]">{part.slice(1, -1)}</em>;
      }
      const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (link) {
        return <a key={index} href={link[2]} target="_blank" rel="noreferrer" className="font-medium text-[var(--cyan)] underline decoration-[var(--cyan)]/40 underline-offset-2 hover:text-[var(--primary-bright)]">{link[1]}</a>;
      }
      return part;
    });
  };

  const flushCode = () => {
    if (!codeLines.length) return;
    blocks.push(
      <div key={`code-${blocks.length}`} className="my-4 overflow-hidden rounded-lg border border-[var(--border)] bg-[#080e17] shadow-[var(--shadow-sm)]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-3 py-1.5">
          <span className="font-mono text-[9px] uppercase tracking-wider text-[var(--text-3)]">{codeLanguage || "code"}</span>
          <span className="text-[9px] text-[var(--text-4)]">Markdown code block</span>
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-[11px] leading-5 text-cyan-100"><code data-language={codeLanguage}>{codeLines.join("\n")}</code></pre>
      </div>,
    );
    codeLines = [];
  };

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (line.trim().startsWith("```")) {
      if (inCode) flushCode();
      inCode = !inCode;
      codeLanguage = line.trim().slice(3);
      index += 1;
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      index += 1;
      continue;
    }
    if (!line.trim()) {
      blocks.push(<div key={`space-${index}`} className="h-2" />);
      index += 1;
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      blocks.push(<hr key={index} className="my-5 border-[var(--border)]" />);
      index += 1;
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const styles = level === 1
        ? "mt-8 border-b border-[var(--border)] pb-2 text-2xl font-bold text-[var(--heading)]"
        : level === 2
          ? "mt-7 text-lg font-bold text-[var(--heading)]"
          : level === 3
            ? "mt-5 text-sm font-bold text-[var(--cyan)]"
            : "mt-4 text-xs font-semibold uppercase tracking-wide text-[var(--text-2)]";
      const Heading = level === 1 ? "h1" : level === 2 ? "h2" : level === 3 ? "h3" : "h4";
      blocks.push(<Heading key={index} className={styles}>{inline(heading[2])}</Heading>);
      index += 1;
      continue;
    }
    const listItem = line.match(/^(\s*)([-*]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[2]);
      const listItems: { text: string; indent: number }[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^(\s*)([-*]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[2]) !== ordered) break;
        listItems.push({ text: item[3], indent: item[1].length });
        index += 1;
      }
      blocks.push(
        ordered
          ? <ol key={`list-${index}`} className="my-3 list-decimal space-y-1 pl-6 text-[12px] leading-6 text-[var(--text-2)]">{listItems.map((item, itemIndex) => <li key={itemIndex} className={item.indent > 0 ? "ml-4" : ""}>{inline(item.text)}</li>)}</ol>
          : <ul key={`list-${index}`} className="my-3 space-y-1 text-[12px] leading-6 text-[var(--text-2)]">{listItems.map((item, itemIndex) => {
            const task = item.text.match(/^\[([ xX])\]\s+(.+)$/);
            return <li key={itemIndex} className={`flex gap-2 ${item.indent > 0 ? "ml-5" : ""}`}><span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${task?.[1].toLowerCase() === "x" ? "bg-[var(--green)]" : "bg-[var(--cyan)]"}`} />{task ? <span className={task[1].toLowerCase() === "x" ? "text-[var(--text-3)] line-through" : ""}>{inline(task[2])}</span> : <span>{inline(item.text)}</span>}</li>;
          })}</ul>,
      );
      continue;
    }
    if (line.trim().startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(<blockquote key={`quote-${index}`} className="my-4 border-l-2 border-[var(--cyan)] bg-[var(--cyan-glow)]/40 px-4 py-2 text-[12px] italic leading-6 text-[var(--text-2)]">{quoteLines.map((quoteLine, quoteIndex) => <p key={quoteIndex}>{inline(quoteLine)}</p>)}</blockquote>);
      continue;
    }
    if (line.trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        tableLines.push(lines[index]);
        index += 1;
      }
      const rows = tableLines
        .filter((tableLine) => !/^\s*\|?[\s:-]+(?:\|[\s:-]+)+\|?\s*$/.test(tableLine))
        .map((tableLine) => tableLine.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim()));
      blocks.push(
        <div key={`table-${index}`} className="my-4 overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full border-collapse text-left text-[11px]">
            <thead className="bg-[var(--surface-3)] text-[var(--heading)]"><tr>{(rows[0] ?? []).map((cell, cellIndex) => <th key={cellIndex} className="border-b border-[var(--border)] px-3 py-2 font-semibold whitespace-nowrap">{inline(cell)}</th>)}</tr></thead>
            <tbody>{rows.slice(1).map((row, rowIndex) => <tr key={rowIndex} className="odd:bg-[var(--surface-2)] even:bg-[var(--surface)]">{row.map((cell, cellIndex) => <td key={cellIndex} className="border-b border-[var(--border)] px-3 py-2 align-top leading-5 text-[var(--text-2)]">{inline(cell)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    blocks.push(<p key={index} className="text-[12px] leading-6 text-[var(--text-2)]">{inline(line)}</p>);
    index += 1;
  }
  if (inCode) flushCode();
  return <article className="documentation-markdown max-w-none">{blocks}</article>;
}

function statusClass(status: DocResource["status"]) {
  switch (status) {
    case "Authoritative":
      return "border-[var(--green)]/25 bg-[var(--green-bg)] text-[var(--green)]";
    case "Live State":
      return "border-[var(--amber)]/25 bg-[var(--amber-bg)] text-[var(--amber)]";
    case "Research":
      return "border-[var(--primary)]/25 bg-[var(--primary-glow)] text-[var(--primary-bright)]";
    case "Setup":
      return "border-[var(--cyan)]/25 bg-[var(--cyan-glow)] text-[var(--cyan)]";
    default:
      return "border-[var(--border)] bg-[var(--surface-3)] text-[var(--text-2)]";
  }
}

export default function DocumentationPage() {
  const [activeCategory, setActiveCategory] = useState<DocCategory>("All");
  const [searchDoc, setSearchDoc] = useState("");
  const [tocOpen, setTocOpen] = useState(true);
  const [selectedDocPath, setSelectedDocPath] = useState(docResources[1].path);
  const [repositoryDocs, setRepositoryDocs] = useState<DocResource[]>([]);
  const [documentContent, setDocumentContent] = useState("");
  const [contentLoading, setContentLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [readerOpen, setReaderOpen] = useState(false);
  const contentScrollRef = useRef<HTMLElement>(null);
  const documentCache = useRef(new Map<string, string>());
  const documentRequests = useRef(new Map<string, Promise<string>>());

  useEffect(() => {
    let cancelled = false;
    api.documentation().then(({ documents }) => {
      if (cancelled) return;
      setRepositoryDocs(documents.map((doc) => ({
        title: doc.title,
        path: doc.path,
        category: categoryForPath(doc.path),
        summary: doc.summary,
        tags: [categoryForPath(doc.path).toLowerCase(), "markdown", "repository"],
        status: doc.path.startsWith("project/") ? "Live State" : "Reference",
        sections: `${doc.sections} sections`,
        searchText: doc.search_text,
      })));
    }).catch(() => {
      // The curated index remains available when the backend is offline.
    });
    return () => { cancelled = true; };
  }, []);

  const allDocs = useMemo(() => {
    const merged = new Map<string, DocResource>(
      [...docResources, ...repositoryDocs].map((doc) => [doc.path, doc] as const),
    );
    return Array.from(merged.values()).filter((doc) => !hiddenDocumentPaths.has(doc.path));
  }, [repositoryDocs]);

  const filteredDocs = useMemo(() => {
    const q = normalized(searchDoc.trim());
    return allDocs.filter((doc) => {
      const categoryMatch = activeCategory === "All" || doc.category === activeCategory;
      if (!q) return categoryMatch;
      const haystack = normalized([doc.title, doc.path, doc.summary, doc.category, doc.status, ...doc.tags, doc.searchText ?? ""].join(" "));
      return categoryMatch && haystack.includes(q);
    });
  }, [activeCategory, allDocs, searchDoc]);

  const counts = useMemo(() => {
    return categories.reduce<Record<DocCategory, number>>((acc, category) => {
      acc[category] = category === "All" ? allDocs.length : allDocs.filter((doc) => doc.category === category).length;
      return acc;
    }, {} as Record<DocCategory, number>);
  }, [allDocs]);

  const firstResultPath = filteredDocs[0]?.path ?? "docs/SATQUERY_AI_FRONTEND_API_CONTRACT.md";
  const selectedDoc = allDocs.find((doc) => doc.path === selectedDocPath) ?? filteredDocs[0] ?? allDocs[0] ?? docResources[1];
  const selectedDetail = docDetails[selectedDoc.path] ?? fallbackDetail(selectedDoc);
  const loadDocument = (path: string) => {
    const cached = documentCache.current.get(path);
    if (cached !== undefined) return Promise.resolve(cached);

    const pending = documentRequests.current.get(path);
    if (pending) return pending;

    const request = api.documentationContent(path).then(({ content }) => {
      documentCache.current.set(path, content);
      documentRequests.current.delete(path);
      return content;
    }).catch((error) => {
      documentRequests.current.delete(path);
      throw error;
    });
    documentRequests.current.set(path, request);
    return request;
  };

  const prefetchDocument = (path: string) => {
    if (documentCache.current.has(path) || documentRequests.current.has(path)) return;
    void loadDocument(path).catch(() => undefined);
  };

  const selectDocument = (path: string) => {
    const cached = documentCache.current.get(path);
    setSelectedDocPath(path);
    setReaderOpen(true);

    if (cached !== undefined) {
      setDocumentContent(cached);
      setContentLoading(false);
    } else {
      setContentLoading(true);
      loadDocument(path)
        .then((content) => {
          setDocumentContent(content);
          setContentLoading(false);
        })
        .catch(() => {
          setDocumentContent("");
          setContentLoading(false);
        });
    }
  };

  useEffect(() => {
    let cancelled = false;
    const cached = documentCache.current.get(selectedDoc.path);
    if (cached !== undefined) {
      setDocumentContent(cached);
      setContentLoading(false);
      return () => { cancelled = true; };
    }
    setContentLoading(true);
    loadDocument(selectedDoc.path)
      .then((content) => { if (!cancelled) setDocumentContent(content); })
      .catch(() => { if (!cancelled) setDocumentContent(""); })
      .finally(() => { if (!cancelled) setContentLoading(false); });
    return () => { cancelled = true; };
  }, [selectedDoc.path]);

  const copyDocument = async () => {
    if (!documentContent) return;
    await navigator.clipboard.writeText(documentContent);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="bg-[var(--canvas)] text-[var(--text)] font-sans antialiased h-screen overflow-hidden flex flex-col selection:bg-[var(--cyan)]/30 selection:text-[var(--canvas)]"
    >
      <TopBar showBrand={true} searchPlaceholder="Search docs, models, endpoints, workflows, or setup..." onSearch={(q) => setSearchDoc(q)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="documentation" className="h-full" />

        <main ref={contentScrollRef} className="flex-1 overflow-y-auto scroll-smooth" data-purpose="documentation-content">
          <div className="px-6 py-5">
            <div className="max-w-[1480px] mx-auto grid grid-cols-12 gap-5">
              <section className="col-span-12 xl:col-span-9 space-y-5">
                <section className="border border-[var(--border)] bg-[var(--surface)] rounded-xl overflow-hidden shadow-lg" data-purpose="documentation-hero">
                  <div className="relative min-h-[260px] p-6 lg:p-7 overflow-hidden">
                    <div className="absolute inset-0 sat-preview-delhi-main opacity-40" />
                    <div className="absolute inset-0 bg-gradient-to-r from-[var(--surface)] via-[var(--surface)]/92 to-[var(--surface)]/52" />
                    <div className="absolute right-8 top-8 hidden lg:block text-[var(--cyan)]/80">
                      <Satellite className="h-28 w-28 drop-shadow-[0_0_24px_rgba(0,194,168,0.30)]" strokeWidth={1.4} />
                    </div>

                    <div className="relative z-10 max-w-3xl">
                      <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-[var(--cyan-glow)] border border-[var(--cyan)]/30 text-[var(--cyan)] text-[10px] font-semibold uppercase tracking-wider mb-4">
                        <BookOpen className="h-3.5 w-3.5" />
                        Repo-backed documentation hub
                      </div>
                      <h1 className="text-2xl lg:text-4xl font-bold text-[var(--heading)] tracking-tight leading-tight">SatQuery AI Documentation</h1>
                      <p className="text-sm text-[var(--text-2)] mt-3 leading-relaxed max-w-2xl">
                        A professional index of the backend, frontend, API contract, model dossiers, setup guides, verification notes, and known caveats already present across the repository markdown files.
                      </p>

                      <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          { label: "Markdown files indexed", value: String(allDocs.length), icon: FileText },
                          { label: "Model dossiers", value: "27", icon: Boxes },
                          { label: "API endpoint groups", value: "8", icon: Braces },
                          { label: "Workflow families", value: "5", icon: Route },
                        ].map((metric) => {
                          const Icon = metric.icon;
                          return (
                            <div key={metric.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)]/85 p-3">
                              <Icon className="h-4 w-4 text-[var(--cyan)] mb-2" />
                              <div className="text-lg font-bold text-[var(--heading)] leading-none">{metric.value}</div>
                              <div className="text-[10px] text-[var(--text-3)] mt-1 leading-snug">{metric.label}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
                    <div className="relative flex-1 min-w-0">
                      <Search className="h-4 w-4 text-[var(--text-3)] absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        value={searchDoc}
                        onChange={(e) => setSearchDoc(e.target.value)}
                        className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg pl-9 pr-3 py-2 text-xs text-[var(--text)] placeholder:text-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)]"
                        placeholder="Search by endpoint, model, guide, status, or file path..."
                        type="text"
                      />
                      {searchDoc && (
                        <button
                          type="button"
                          onClick={() => setSearchDoc("")}
                          aria-label="Clear documentation search"
                          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--text-3)] hover:bg-[var(--surface-3)] hover:text-[var(--heading)]"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
                      <Filter className="h-4 w-4 text-[var(--text-3)] shrink-0" />
                      {categories.map((category) => {
                        const active = activeCategory === category;
                        return (
                          <button
                            key={category}
                            onClick={() => setActiveCategory(category)}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition whitespace-nowrap ${
                              active
                                ? "bg-[var(--cyan-glow)] border-[var(--cyan)]/50 text-[var(--cyan)]"
                                : "bg-[var(--surface-2)] border-[var(--border)] text-[var(--text-2)] hover:border-[var(--border-strong)]"
                            }`}
                          >
                            <span>{category}</span>
                            <span className="text-[10px] opacity-70">{counts[category]}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </section>

                {readerOpen && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--scrim)] p-3 sm:p-6 lg:p-10" data-purpose="documentation-reader-overlay">
                <section className="flex max-h-full w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-[var(--cyan)]/40 bg-[var(--surface)] shadow-[var(--shadow-xl)]" data-purpose="live-markdown-reader">
                  <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0 text-[var(--cyan)]" />
                        <h2 className="truncate text-sm font-bold text-[var(--heading)]">{selectedDoc.title}</h2>
                      </div>
                      <p className="mt-0.5 text-[10px] text-[var(--text-3)]">
                        {selectedDetail.purpose}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="rounded-md border border-[var(--cyan)]/25 bg-[var(--cyan-glow)] px-2 py-1 font-mono text-[10px] text-[var(--cyan)]">
                        {contentLoading ? "Loading..." : `${documentContent.split(/\r?\n/).length} lines`}
                      </span>
                      <button
                        type="button"
                        onClick={copyDocument}
                        disabled={!documentContent || contentLoading}
                        className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[10px] font-semibold text-[var(--text-2)] transition hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)] disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {copied ? <Check className="h-3 w-3 text-[var(--green)]" /> : <FileText className="h-3 w-3" />}
                        {copied ? "Copied" : "Copy"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setReaderOpen(false)}
                        aria-label="Close document reader"
                        className="inline-flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] p-1.5 text-[var(--text-2)] transition hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)]"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
                    {contentLoading ? (
                      <div className="space-y-3 py-4">
                        {[80, 65, 90, 52].map((width) => <div key={width} style={{ width: `${width}%` }} className="h-3 animate-pulse rounded bg-[var(--surface-3)]" />)}
                      </div>
                    ) : documentContent ? (
                      <MarkdownPreview content={documentContent} />
                    ) : (
                      <div className="rounded-lg border border-dashed border-[var(--border)] p-8 text-center">
                        <FileText className="mx-auto mb-2 h-6 w-6 text-[var(--text-3)]" />
                        <p className="text-xs font-semibold text-[var(--heading)]">Document unavailable</p>
                        <p className="mt-1 text-[11px] text-[var(--text-3)]">Start the backend and select this document again.</p>
                      </div>
                    )}
                  </div>
                </section>
                  </div>
                )}

                <motion.section variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 gap-3.5" data-purpose="documentation-results">
                  {filteredDocs.map((doc) => (
                    <motion.article
                      key={doc.path}
                      variants={itemVariant}
                      role="button"
                      tabIndex={0}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectDocument(doc.path)}
                      onMouseEnter={() => prefetchDocument(doc.path)}
                      onFocus={() => prefetchDocument(doc.path)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          selectDocument(doc.path);
                        }
                      }}
                      className={`rounded-xl border bg-[var(--surface-2)] p-4 transition group cursor-pointer ${
                        selectedDoc.path === doc.path
                          ? "border-[var(--cyan)] shadow-[0_0_18px_rgba(0,194,168,0.16)]"
                          : "border-[var(--border)] hover:border-[var(--cyan)]/45"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-[9px] font-semibold uppercase tracking-wider ${statusClass(doc.status)}`}>{doc.status}</span>
                            <span className="text-[10px] text-[var(--text-3)]">{doc.category}</span>
                          </div>
                          <h2 className="text-sm font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)] transition-colors">{doc.title}</h2>
                          <p className="text-[11px] text-[var(--text-3)] mt-1.5 leading-relaxed">{doc.summary}</p>
                        </div>
                        <FileText className="h-4 w-4 text-[var(--text-3)] shrink-0 mt-1" />
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {doc.tags.map((tag) => (
                          <span key={tag} className="px-2 py-0.5 rounded-md bg-[var(--surface-3)] border border-[var(--border)] text-[10px] text-[var(--text-2)]">{tag}</span>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between gap-3">
                        <span className="font-mono text-[10px] text-[var(--text-3)] truncate" title={doc.path}>{doc.path}</span>
                        <span className="inline-flex items-center gap-1 text-[10px] text-[var(--cyan)] font-semibold shrink-0">
                          {selectedDoc.path === doc.path ? "Open now" : doc.sections}
                          <ArrowRight className="h-3 w-3" />
                        </span>
                      </div>
                    </motion.article>
                  ))}
                  {filteredDocs.length === 0 && (
                    <div className="md:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-8 text-center">
                      <Search className="h-8 w-8 text-[var(--text-3)] mx-auto mb-3" />
                      <h2 className="text-sm font-semibold text-[var(--heading)]">No documentation matched</h2>
                      <p className="text-xs text-[var(--text-3)] mt-1">Try a model name, endpoint, workflow, or broader category.</p>
                    </div>
                  )}
                </motion.section>

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-purpose="setup-and-api">
                  <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TerminalSquare className="h-4 w-4 text-[var(--cyan)]" />
                      <h2 className="text-sm font-bold text-[var(--heading)]">Quick Start Commands</h2>
                    </div>
                    <div className="space-y-2">
                      {commands.map((cmd) => (
                        <div key={cmd.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                          <div className="text-[10px] font-semibold text-[var(--text-3)] uppercase tracking-wider mb-1">{cmd.label}</div>
                          <code className="block font-mono text-[11px] text-[var(--text)] leading-relaxed break-words">{cmd.command}</code>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Code2 className="h-4 w-4 text-[var(--cyan)]" />
                      <h2 className="text-sm font-bold text-[var(--heading)]">API Reference Matrix</h2>
                    </div>
                    <div className="space-y-2 max-h-[430px] overflow-y-auto pr-1">
                      {apiEndpoints.map((endpoint) => (
                        <div key={`${endpoint.method}-${endpoint.path}`} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5 rounded-md bg-[var(--cyan-glow)] border border-[var(--cyan)]/25 text-[var(--cyan)] text-[10px] font-bold font-mono">{endpoint.method}</span>
                            <span className="font-mono text-[11px] text-[var(--heading)] truncate">{endpoint.path}</span>
                          </div>
                          <div className="text-[11px] font-semibold text-[var(--text)]">{endpoint.area}</div>
                          <p className="text-[10px] text-[var(--text-3)] mt-0.5 leading-relaxed">{endpoint.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4" data-purpose="workflow-section">
                  <div className="flex items-center gap-2 mb-3">
                    <Route className="h-4 w-4 text-[var(--cyan)]" />
                    <h2 className="text-sm font-bold text-[var(--heading)]">Workflow Functionality</h2>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {workflows.map((workflow) => (
                      <div key={workflow.title} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                        <h3 className="text-xs font-semibold text-[var(--heading)]">{workflow.title}</h3>
                        <p className="text-[10px] text-[var(--text-3)] mt-1 leading-relaxed">{workflow.steps}</p>
                        <div className="mt-2 inline-flex items-center gap-1.5 text-[10px] text-[var(--cyan)]">
                          <Layers3 className="h-3 w-3" />
                          {workflow.models}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4" data-purpose="model-dossiers">
                  <div className="flex items-center gap-2 mb-3">
                    <Database className="h-4 w-4 text-[var(--cyan)]" />
                    <h2 className="text-sm font-bold text-[var(--heading)]">Model Dossier Map</h2>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {modelFamilies.map((family) => {
                      const Icon = family.icon;
                      return (
                        <div key={family.name} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                          <div className="flex items-start gap-3">
                            <div className="h-8 w-8 rounded-lg border border-[var(--cyan)]/25 bg-[var(--cyan-glow)] flex items-center justify-center text-[var(--cyan)] shrink-0">
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="min-w-0">
                              <h3 className="text-xs font-semibold text-[var(--heading)]">{family.name}</h3>
                              <p className="text-[10px] text-[var(--text-3)] mt-1 leading-relaxed">{family.detail}</p>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-1.5 mt-3">
                            {family.docs.map((doc) => (
                              <span key={doc} className="font-mono text-[9px] px-2 py-0.5 rounded bg-[var(--surface-3)] border border-[var(--border)] text-[var(--text-2)]">{doc}</span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </section>

              <aside className="col-span-12 xl:col-span-3 space-y-5">
                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-[var(--cyan)]" />
                      <h2 className="text-xs font-bold text-[var(--heading)] tracking-wide">Table of Contents</h2>
                    </div>
                    <button onClick={() => setTocOpen((v) => !v)} className="p-1 rounded-md hover:bg-[var(--surface-hover)] text-[var(--text-3)]">
                      <ChevronDown className={`h-3.5 w-3.5 transition-transform ${tocOpen ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                  {tocOpen && (
                    <div className="space-y-1.5">
                      {["Searchable markdown index", "Quick start commands", "API reference matrix", "Workflow functionality", "Model dossier map", "Readiness and caveats"].map((item, index) => (
                        <div key={item} className="flex items-center gap-2 py-1 text-[11px] text-[var(--text-2)]">
                          <span className="w-5 font-mono text-[10px] text-[var(--text-3)]">{index + 1}.</span>
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center gap-2 mb-3">
                    <ShieldCheck className="h-4 w-4 text-[var(--cyan)]" />
                    <h2 className="text-xs font-bold text-[var(--heading)] tracking-wide">Readiness Notes</h2>
                  </div>
                  <div className="space-y-2.5">
                    {readiness.map((item) => (
                      <div key={item.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                        <div className="flex items-center gap-2 mb-1">
                          {item.tone === "green" ? <CheckCircle2 className="h-3.5 w-3.5 text-[var(--green)]" /> : <AlertTriangle className="h-3.5 w-3.5 text-[var(--amber)]" />}
                          <h3 className="text-[11px] font-semibold text-[var(--heading)]">{item.label}</h3>
                        </div>
                        <p className="text-[10px] text-[var(--text-3)] leading-relaxed">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center gap-2 mb-3">
                    <PlayCircle className="h-4 w-4 text-[var(--cyan)]" />
                    <h2 className="text-xs font-bold text-[var(--heading)] tracking-wide">Primary Workflows</h2>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: "Upload", icon: Server },
                      { label: "Analyze", icon: Braces },
                      { label: "Layers", icon: Layers3 },
                      { label: "Video", icon: Video },
                    ].map((item) => {
                      const Icon = item.icon;
                      return (
                        <div key={item.label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3 text-center">
                          <Icon className="h-4 w-4 text-[var(--cyan)] mx-auto mb-1.5" />
                          <div className="text-[10px] font-semibold text-[var(--text)]">{item.label}</div>
                        </div>
                      );
                    })}
                  </div>
                </section>

                <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock3 className="h-4 w-4 text-[var(--cyan)]" />
                    <h2 className="text-xs font-bold text-[var(--heading)] tracking-wide">Best Next Read</h2>
                  </div>
                  <p className="text-[11px] text-[var(--text-3)] leading-relaxed mb-3">
                    Start with the API contract for UI work, then read the architecture and pre-demo notes before changing backend behavior.
                  </p>
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
                    <div className="text-[10px] text-[var(--text-3)] mb-1">Current search target</div>
                    <div className="font-mono text-[10px] text-[var(--cyan)] break-words">{firstResultPath}</div>
                  </div>
                  <Link href="/analysis" className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--cyan)] px-3 py-2 text-xs font-semibold text-[var(--canvas)] hover:opacity-90 transition">
                    Open Analysis Workspace
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </section>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </motion.div>
  );
}
