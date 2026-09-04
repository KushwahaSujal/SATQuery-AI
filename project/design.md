# Design — Visual System

The frontend is owned by the other half of the team. This file records **what the code already
establishes** so backend-produced artifacts (overlays, legends, colormaps, PDF reports) stay
consistent with the UI, and so nobody invents a second palette.

Sources of truth: `frontend/tailwind.config.js`, `frontend/src/app/globals.css`,
`frontend/src/app/layout.tsx`, and the colour constants in `backend/app/geo/rendering.py` +
`backend/app/visualization/`.

---

## 1. Theme

**Dark-only.** `<html className="dark">` is hard-coded in `layout.tsx` and Tailwind runs
`darkMode: "class"`. There is no light theme and no toggle. Rationale: this is an imagery-analysis
tool — a dark chrome keeps the eye on the raster and stops the UI competing with false-colour
composites for attention.

---

## 2. Colour

### Base (from `tailwind.config.js`)

| Token | Hex | Use |
|---|---|---|
| `background` | `#090D16` | app background (top of gradient) |
| `surface` | `#111827` | panels, cards |
| `surfaceBorder` | `#1F2937` | dividers, panel borders |

`globals.css` renders the body as a fixed vertical gradient `#090D16 → #0F172A` with foreground
text `rgb(241 245 249)` (slate-100).

### Accents (`theme.extend.colors.accent`)

| Token | Hex | Meaning in this product |
|---|---|---|
| `accent.blue` | `#3B82F6` | primary action, selection, links |
| `accent.cyan` | `#06B6D4` | grounding / detection results |
| `accent.emerald` | `#10B981` | success, model AVAILABLE/LOADED, vegetation |
| `accent.amber` | `#F59E0B` | warnings, `REVIEW_REQUIRED`, heuristic scores |
| `accent.rose` | `#F43F5E` | errors, failures, detected change |

### Semantic mapping — keep this stable across UI and generated artifacts

| Meaning | Colour | Where enforced |
|---|---|---|
| Detected change | red `rgb(255,59,48)` (default) / `rgb(239,68,68)` in the change tool | `geo/rendering.py:11`, `agent/registry.py:219` |
| Grounding / segmentation mask | emerald-cyan `rgb(0,230,150)` | `agent/registry.py:389` |
| Comparison panel background | `rgb(24,24,27)` | `geo/rendering.py:75` |
| Model status: LOADED / AVAILABLE | emerald | UI |
| Model status: NOT_CONFIGURED | slate/muted | UI |
| Model status: FAILED | rose | UI |

> **Inconsistency to fix:** the change overlay is red in two slightly different shades
> (`255,59,48` vs `239,68,68`) depending on which code path runs. Pick one — `#EF4444`
> (`239,68,68`, Tailwind red-500) matches the accent family better than the iOS-red default.

### Scientific colormaps (matplotlib — do not restyle)

| Layer | Colormap | Why |
|---|---|---|
| Probability heatmap | `turbo` | perceptually ordered, high dynamic range |
| Single band / generic raster | `viridis` | perceptually uniform, colour-blind safe |
| NDVI | `RdYlGn` | domain convention: red = bare, green = vegetated |
| NDWI | `Blues` | domain convention: water |
| Band difference | diverging | zero-centred |

These are conventions the remote-sensing community reads at a glance. **Never substitute a brand
palette for a scientific colormap** — and always ship the colorbar legend with the raster, since an
index image without a scale is not evidence.

### Scrollbar
6px, track `#0B0F19`, thumb `#1E293B`, hover `#334155`, 3px radius.

---

## 3. Typography

Currently the **system font stack** in `globals.css`:

```
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
```

No webfont is loaded — deliberate or not, it costs zero bytes and renders natively everywhere,
which matters for an offline demo. If the frontend team wants a typeface, **Inter** (UI) plus
**JetBrains Mono** (numeric/telemetry) is the natural fit; load via `next/font` so it stays
self-hosted and offline-safe.

**Monospace is required for:** pixel coordinates, DN values, lat/lon, area figures, confidence
scores, checkpoint paths, and the execution trace. Numbers that get compared column-to-column must
be tabular.

### Scale (Tailwind defaults, no overrides)
`text-xs` 12 (metadata, badges) · `text-sm` 14 (body, trace) · `text-base` 16 · `text-lg` 18 (panel
titles) · `text-xl`/`2xl` (page header). Weights: 400 body · 500 labels · 600 headings.

---

## 4. Layout

From `Diagram 22` and the component set in `frontend/src/components/`:

```
Header  (title · system status · model availability pill)
├─ Left rail   : UploadPanel · QueryBar · ModelStatusPanel · MetadataPanel
└─ Main region : MapViewer  (maplibre-gl, raster + overlay layers, click-to-inspect)
                 VisualizationPanel (layer chips, provenance badges, opacity, legend,
                                     pixel inspector, 50-bin histogram, export menu)
                 VideoPlayerPanel   (timeline event markers, keyframe carousel)
                 ResultsPanel       (answer · confidence · area m²/km² · JSON)
                 WorkflowDecisionPanel (capability chosen + routing reason + confidence)
                 TracePanel         (observable execution steps)
```

`WorkflowDecisionPanel` and `TracePanel` are the two components that **demonstrate the agentic
requirement to a judge**. They should be visible without scrolling, not buried in a tab.

---

## 5. Provenance badges

Every rendered layer carries a provenance tag (`visualization/provenance.py`). These must be
visually distinct — they are the zero-fabrication guarantee made legible:

| Tag | Meaning | Suggested colour |
|---|---|---|
| `SOURCE_DATA` | unaltered sensor bands, display stretch only | slate |
| `DERIVED_INDEX` | computed from real physical bands (NDVI/NDWI/NDBI) | emerald |
| `MODEL_OUTPUT` | discrete network prediction (binary mask, class) | cyan |
| `MODEL_PROBABILITY` | continuous [0,1] from a sigmoid/softmax | blue |
| `HEURISTIC_ANALYSIS` | composite hand-weighted score, **not** calibrated | amber |

Amber for heuristics is intentional: it should read as "interpret with care" at a glance.

---

## 6. Principles

1. **The imagery is the interface.** Chrome recedes; the raster does not compete with the UI.
2. **Evidence beside the claim.** A text answer never appears without its overlay, mask or index.
3. **Uncertainty is visible, not hidden.** Confidence, warnings, `REVIEW_REQUIRED` and
   `NOT_CONFIGURED` states are first-class UI, not error toasts.
4. **Scientific convention beats brand consistency** wherever the two conflict.
5. **Legends are mandatory** on every exported raster. A colour ramp without a scale is decoration.
