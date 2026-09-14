# SatQuery AI — Frontend Guide

Complete technical documentation of the frontend architecture, components, data flow, and design decisions.

---

## 1. Tech Stack

| Technology | Purpose |
|---|---|
| Next.js 16 (App Router) | Framework, routing, SSR/SSG |
| React 19 | UI components |
| TypeScript | Type safety |
| Tailwind CSS 4 | Utility-first styling |
| React Query (TanStack) | Server state, caching, polling |
| Zustand | Client state (command palette) |
| Geist Font | Typography (Sans + Mono) |
| MUI X Charts | Data visualization |
| Lucide React | Icons |
| Framer Motion | Animations (available, not used yet) |

---

## 2. Project Structure

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root layout (header + providers)
│   ├── page.tsx                  # Command Center (main workspace)
│   ├── providers.tsx             # React Query provider
│   ├── globals.css               # Design tokens + base styles
│   ├── analysis/[jobId]/page.tsx # Analysis result workspace
│   ├── visual-analytics/[jobId]/page.tsx # Layer inspection
│   ├── video/[jobId]/page.tsx    # Video intelligence
│   ├── jobs/page.tsx             # Job history list
│   ├── models/page.tsx           # Model observatory
│   └── system/page.tsx           # System diagnostics
│
├── components/
│   ├── layout/
│   │   ├── AppHeader.tsx         # Top nav bar (brand, nav, status pills)
│   │   ├── EmptyState.tsx        # Reusable empty state
│   │   └── StatusBadge.tsx       # Status indicator badge
│   │
│   ├── map/
│   │   └── MapViewer.tsx         # Central imagery canvas + layer toggles
│   │
│   ├── upload/
│   │   └── UploadPanel.tsx       # File drop zone + raster list
│   │
│   ├── query/
│   │   └── QueryBar.tsx          # Input bar + task selector + run button
│   │
│   ├── results/
│   │   └── ResultsPanel.tsx      # Answer/metrics/metadata tabs
│   │
│   ├── trace/
│   │   └── ExecutionTrace.tsx    # Pipeline execution timeline
│   │
│   ├── charts/
│   │   ├── MetricsChart.tsx      # Bar chart (MUI X)
│   │   └── PieMetrics.tsx        # Donut chart (MUI X)
│   │
│   ├── terminal/
│   │   └── TerminalConsole.tsx   # Debug terminal interface
│   │
│   └── ui/                       # Reusable primitives
│       ├── badge.tsx             # Status badges
│       ├── button.tsx            # Button variants
│       ├── card.tsx              # Card container
│       ├── separator.tsx         # Divider
│       ├── tabs.tsx              # Tab navigation
│       ├── glow-card.tsx         # Hover glow effect card
│       ├── animated-gradient-text.tsx # Animated gradient text
│       ├── shimmer-button.tsx    # Button with shimmer
│       ├── particle-background.tsx # Canvas particle system
│       ├── CommandPalette.tsx    # ⌘K command palette
│       └── CommandPaletteContext.tsx # Palette state context
│
├── hooks/
│   └── useSystem.ts              # React Query hooks (health, models, jobs, results)
│
└── lib/
    ├── api.ts                    # Backend API client
    ├── endpoints.ts              # API endpoint definitions
    ├── types.ts                  # TypeScript interfaces (mirrors backend schemas)
    ├── utils.ts                  # cn() utility (clsx + tailwind-merge)
    └── localJobs.ts              # localStorage job cache (legacy, being removed)
```

---

## 3. Design System

### 3.1 Color Tokens (globals.css)

```css
/* Surface stack — 4 levels of depth */
--s0: #060608;    /* void / page background */
--s1: #0c0c10;    /* base panel background */
--s2: #101015;    /* raised surface */
--s3: #15151c;    /* elevated element */
--s4: #1c1c26;    /* top-level widget */

/* Border system — visible on dark backgrounds */
--b0: #1e1e2a;    /* hairline / structural */
--b1: #2a2a38;    /* panel edge */
--b2: #3a3a4a;    /* element border */
--b3: #4a4a5c;    /* interactive border */

/* Text scale — optimized for dark theme contrast */
--t0: #fafafa;    /* primary / headings */
--t1: #d4d4dc;    /* secondary body */
--t2: #a1a1b5;    /* muted labels */
--t3: #71718a;    /* hints / tertiary */
--t4: #4a4a5e;    /* faint — still readable */

/* Brand accent — electric indigo-blue */
--accent: hsl(222, 88%, 62%);
--accent-dim: hsla(222, 88%, 62%, 0.12);
--accent-glow: hsla(222, 88%, 62%, 0.25);
--accent-text: hsl(222, 88%, 72%);

/* Semantic colors */
--green: hsl(142, 68%, 52%);     /* success */
--amber: hsl(38, 92%, 56%);      /* warning */
--red: hsl(0, 80%, 66%);         /* error */
--purple: hsl(264, 72%, 68%);    /* detection */
--cyan: hsl(190, 80%, 55%);      /* index */
```

### 3.2 Typography

- **Font**: Geist Sans (body) + Geist Mono (data/labels)
- **Scale**: 9px (micro) → 10px (small) → 11px (body) → 12px (default) → 13px (input) → 16px (metric)
- **Weights**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- **Pattern**: Mono font for all data, code, labels, and status text

### 3.3 Component Classes

```css
.panel-header     /* 38px height, flex between, border-bottom */
.panel-label      /* 10px mono, uppercase, tracking-wider */
.status-dot       /* 5px circle for status indicators */
.status-pill      /* 10px mono, border, colored background */
.kbd-chip         /* Keyboard shortcut display */
.font-mono-data   /* Monospace for data display */
```

---

## 4. Data Flow

### 4.1 Backend Connection

```
Frontend (Next.js) → API_BASE (localhost:8000) → FastAPI Backend
```

**API Base**: Configured via `NEXT_PUBLIC_API_BASE_URL` env var, defaults to `http://localhost:8000`

### 4.2 Key API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | System health check |
| `/api/models` | GET | List all model capabilities |
| `/api/upload` | POST | Upload raster images |
| `/api/analyze` | POST | Run analysis query |
| `/api/jobs` | GET/DELETE | List/clear job history |
| `/api/jobs/{id}` | GET | Get job status |
| `/api/results/{id}` | GET | Get analysis result |
| `/api/analysis/{id}/layers` | GET | Get available visualization layers |
| `/api/analysis/{id}/visualizations/{layer}` | GET | Render layer image |
| `/api/analysis/{id}/inspect-pixel` | POST | Inspect pixel values |
| `/api/analysis/{id}/histogram/{layer}` | GET | Get layer histogram |
| `/api/video/upload` | POST | Upload video |
| `/api/video/analyze` | POST | Run video analysis |
| `/api/video/{id}` | GET | Get video job result |
| `/api/video/{id}/stream` | GET | Stream video file |

### 4.3 State Management

**React Query** handles all server state:
- `useHealth()` — Polls `/api/health` every 30s
- `useModels()` — Polls `/api/models` every 30s
- `useJob(jobId)` — Fetches job status, polls while RUNNING
- `useAnalysisResult(jobId)` — Fetches result with retry + polling
- `useLayers(jobId)` — Fetches available visualization layers
- `useHistogram(jobId, layerId)` — Fetches layer histogram

**Local state** (`useState`) for:
- Current query text
- Active task type
- Upload rasters/video
- UI state (modals, panels, etc.)

**Zustand** for:
- Command palette open/close state

### 4.4 Caching Strategy

| Data | staleTime | gcTime | refetchOnMount | Notes |
|---|---|---|---|---|
| Health | 15s | — | true | Polls every 30s |
| Models | 15s | — | true | Polls every 30s |
| Jobs | 5min | 10min | false | No refetch on navigation |
| Results | 30s | — | true | Polls while loading |
| Layers | 30s | — | true | Per-job |

---

## 5. Pages

### 5.1 Command Center (`/`)

**Layout**: 3-column workspace + bottom query bar

```
┌─────────────────────────────────────────────────┐
│ [Upload] [      MapViewer      ] [Results]      │
│  Panel                        Panel             │
├─────────────────────────────────────────────────┤
│ [QueryBar: input + task selector + Run]         │
│ [ExecutionTrace: pipeline steps]                │
└─────────────────────────────────────────────────┘
```

**Workflow**:
1. User drops files in UploadPanel → rasters stored in state
2. User types query in QueryBar
3. User clicks Run → `api.analyze()` called
4. Job ID returned → MapViewer fetches layers
5. Results appear in ResultsPanel
6. Auto-redirects to `/analysis/{jobId}` after 1.2s

### 5.2 Analysis Workspace (`/analysis/[jobId]`)

**Layout**: 2-column (canvas + detail panel) + trace

Shows:
- Query text
- Spatial analysis overlay image
- Answer, metrics (confidence, regions, pixels, area)
- Evidence boxes with scores
- Pipeline models used
- Execution trace

### 5.3 Visual Analytics (`/visual-analytics/[jobId]`)

**Layout**: 3-column (layers + canvas + inspector)

Features:
- Layer list (true_color, ndvi, change_overlay, etc.)
- Canvas with click-to-inspect pixel
- Pixel telemetry panel (coordinates, NDVI, probability)
- Histogram/distribution toggle
- Export buttons (PNG, GeoTIFF, GeoJSON)
- Opacity slider

### 5.4 Video Intelligence (`/video/[jobId]`)

**Layout**: 2-column (player + events)

Features:
- Video player with stream URL
- Event timeline with clickable dots
- Detected events list with scores
- Models executed
- Empty/error states based on workflow_reason

### 5.5 Jobs History (`/jobs`)

**Layout**: Full-width table

Features:
- Filter by status (ALL, RUNNING, COMPLETED, FAILED)
- Clear all jobs
- Click to open analysis/visual-analytics
- Cached with React Query (no refetch on navigation)

### 5.6 Model Observatory (`/models`)

**Layout**: Grid of model cards

Shows all registered models with:
- Name, task, device
- Status (NOT_CONFIGURED, AVAILABLE, LOADED, FAILED)
- Capabilities, description

### 5.7 System Diagnostics (`/system`)

**Layout**: System health dashboard

Shows:
- API status
- Database connection
- Device info
- Environment
- Model availability matrix

---

## 6. Components Detail

### 6.1 MapViewer

**Purpose**: Central imagery display with layer switching

**Props**: `rasters`, `video`, `jobId`

**Flow**:
1. Shows uploaded raster preview (local blob URL)
2. After analysis, fetches layers from backend
3. Layer toggles (RGB/NDVI/SAR) only appear for available layers
4. Clicking toggle switches image URL to backend visualization
5. Legend overlay appears for spectral indices

**Image URL logic**:
```
if jobId && selectedBackendLayer:
  → /api/analysis/{jobId}/visualizations/{layer}
else:
  → raster.preview_url (local blob)
```

### 6.2 QueryBar

**Purpose**: Input for natural language queries

**Features**:
- `>_` prompt glyph with focus glow
- Suggestion chips (Building damage, Flood extent, NDVI change, Vehicle count)
- Task selector dropdown (AUTO, VQA, GROUNDING, CHANGE, etc.)
- Run button with loading state
- Enter hint badge when focused

**Task routing**: Backend handles task detection automatically. Dropdown is for explicit override.

### 6.3 ResultsPanel

**Purpose**: Display analysis results in tabs

**Tabs**:
- **Answer**: Answer text + quick metrics (confidence, regions, pixels, task)
- **Metrics**: Pie chart + detailed metric rows
- **Metadata**: Task, job_id, models, workflow, reason

**Data source**: `result.evidence.spatial.statistics` for metrics

### 6.4 ExecutionTrace

**Purpose**: Show pipeline execution steps

**Features**:
- Horizontal scrollable timeline
- Auto-scroll to latest step
- Color-coded status (green=success, red=error, blue=running)
- Duration badges
- Handles all backend statuses: success, warning, error, running, skipped

### 6.5 CommandPalette (⌘K)

**Purpose**: Quick navigation

**Commands**:
- Navigation: Command Center, Jobs, Models, System
- Actions: Upload, Analyze, Clear Jobs

---

## 7. Backend Integration

### 7.1 Types Alignment

All frontend types in `types.ts` mirror backend Pydantic schemas:

| Frontend Type | Backend Schema |
|---|---|
| `AnalysisResult` | `AnalyzeResponse` |
| `EvidencePackage` | `EvidencePackage` |
| `SpatialEvidence` | `SpatialEvidence` |
| `AreaStatistics` | `AreaStatistics` |
| `TraceStep` | `ExecutionStep` |
| `TaskType` | `TaskType` enum |
| `JobStatus` | `JobStatus` enum |
| `PixelInspectionResponse` | Inspector output |
| `HistogramResponse` | Histogram output |

### 7.2 Task Type Mapping

Frontend sends `override_task` parameter to backend:

| Frontend Value | Backend Value | Description |
|---|---|---|
| `unsupported` | (auto-detect) | Backend routes automatically |
| `single_image_vqa` | VQA | Visual question answering |
| `single_image_grounding` | GROUNDING | Ground language to image |
| `bi_temporal_change` | CHANGE | Detect change between images |
| `bi_temporal_change_vqa` | TEMPORAL VQA | VQA across temporal pairs |
| `single_image_caption` | CAPTION | Generate scene description |
| `video_grounding_tracking` | VIDEO | Video analysis |

### 7.3 Response Flow

```
POST /api/analyze
  → Backend runs pipeline (GroundingDINO → V4 Reasoner → SAM2)
  → Returns { job_id }
  → Frontend stores job_id, redirects to /analysis/{jobId}

GET /api/results/{jobId}
  → Returns AnalyzeResponse with:
    - answer, confidence, task
    - evidence: { spatial: { statistics: { changed_pixels, region_count, ... } } }
    - execution_trace: [{ step, status, duration_ms }]
    - models_used, warnings, errors
```

---

## 8. Key Design Decisions

### 8.1 Why No Fabricated Data

The audit found 36 instances of hardcoded/mocked data. All removed:
- No `?? 43` for regions
- No `"152.4k m²"` fallback
- No fake model names or latencies
- No invented pixel coordinates
- Show `—` or hide row when data absent

### 8.2 Why React Query Over useState+useEffect

- Automatic caching prevents empty flash on navigation
- Built-in retry with exponential backoff
- Background refetching for live data
- Deduplication of simultaneous requests
- Better loading/error state handling

### 8.3 Why Lazy Loading for Models

Models use lazy loading because:
- GPU memory is limited
- Not all models needed for every query
- Loading on first use avoids startup delay
- Memory freed when model unloaded

### 8.4 Why Layer Toggles Only Show Available

- No dead buttons cluttering UI
- Backend tells frontend what's available
- NDVI only if NIR band exists
- SAR only if input is SAR data

---

## 9. Error Handling

### 9.1 API Errors

- HTTP errors extracted from response body
- Backend sends `error.message` or `detail`
- Frontend shows in red error banner

### 9.2 Loading States

- Each page has explicit loading state with spinner
- React Query `isLoading` drives UI
- No flash of empty content

### 9.3 Empty States

- Each page has meaningful empty state
- Tells user what to do next
- No fabricated placeholder data

### 9.4 Result Not Found

- Shows "Result not available" with job status
- Polls with retry until result is ready
- Handles race condition between analysis completion and result fetch

---

## 10. Performance

### 10.1 Caching

- Jobs cached for 5 minutes (no refetch on navigation)
- Health/models cached for 15 seconds
- Results cached with 30s stale time
- `refetchOnWindowFocus: false` on jobs page

### 10.2 Image Loading

- Raster previews use blob URLs (instant)
- Backend visualizations loaded on demand
- Legend images loaded separately
- `key` prop forces re-render on layer switch

### 10.3 Bundle Size

- Geist font (self-hosted, no external requests)
- MUI X Charts (tree-shakeable)
- Lucide icons (individual imports)

---

## 11. Accessibility

### 11.1 Keyboard Navigation

- All interactive elements are focusable
- Command palette navigable with ↑↓ Enter Escape
- Query bar focusable with Enter to run

### 11.2 Focus States

- Custom focus ring: 1.5px accent color, 2px offset
- Applied via `*:focus-visible` in globals.css

### 11.3 Color Contrast

- Text tokens optimized for dark theme (WCAG AA)
- Semantic colors for status (green/amber/red)
- Status conveyed by icon + text, not color alone

### 11.4 Reduced Motion

- `prefers-reduced-motion` media query
- All animations respect user preference

---

## 12. Development

### 12.1 Running Locally

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

### 12.2 Environment Variables

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 12.3 Build Commands

```bash
npm run build    # Production build
npm run dev      # Development server
npm run lint     # ESLint check
npx tsc --noEmit # TypeScript check
```

### 12.4 File Naming Conventions

- Components: `PascalCase.tsx` (e.g., `MapViewer.tsx`)
- Hooks: `camelCase.ts` with `use` prefix (e.g., `useSystem.ts`)
- Types: `camelCase.ts` (e.g., `types.ts`)
- Pages: `page.tsx` in App Router convention
