# frontend-v2 Audit — Sandipan's New Design

**Date:** 2026-09-21
**Scope:** `frontend-v2/` (the new template Sandipan pushed on `af110b1`/`prototype`), compared against the older, already-wired `frontend/`.
**Method:** Full read of every page/component/hook/lib file, `npm install` + `next dev` boot, Playwright screenshots (desktop 1440px + mobile 390px, light preference, backend offline) across `/`, `/analysis`, `/datasets`, `/reports`, `/history`, `/documentation`, `/video/[jobId]`, plus a repo-wide grep for mock/dead-code markers.

This is the working doc — check items off as we fix them together.

> **Status note (2026-09-21, added by the executing session):** §§1-9 below are preserved **verbatim** as written by the analysis session. They have now been re-verified against real code — see **§10**, which records what held up, what was wrong, and what §§1-9 missed. Where §10 contradicts §§1-9, §10 is current. §§1-9 are not edited, so the original reasoning stays inspectable.

---

## Mission — this new design eventually replaces `prototype`'s frontend, one piece at a time

Set expectations before anything else: **`frontend-v2`'s design and layout is the intended final look of the product.** The goal is not to maintain two frontends forever — it is to gradually replace `prototype`'s current frontend with this one, page by page and component by component, fixing every bug/UX/logic/redundancy issue in §§1-9 along the way, until `frontend-v2`'s polish and `prototype`'s honesty meet in the middle.

Why "one piece at a time" instead of a straight swap — the honest tradeoff between the two right now:

- **`prototype`'s current frontend** is crude and not visually polished, but it is **functional and honest** — what it shows is backed by something real.
- **`frontend-v2`** has the professional, finished *look and concept* this product should end up with — but, as documented above, it's riddled with real bugs, broken UX, logic errors, and redundant/duplicated code, and at least one full page (Datasets) and several smaller bits (Home's stats/HUD overlay) are **decorative and not backed by anything real**.

So the replacement is a controlled trade, not a coat of paint: every time a piece of `prototype` gets replaced with its `frontend-v2` equivalent, that equivalent must first be fixed to `prototype`'s standard of "actually works and shows real data" — not just prettier.

### Hard constraint: no invented features

Some of what's in `frontend-v2` is UI for capabilities the tool doesn't actually have — it was designed/hallucinated as if a backend existed for it when one may not (the Datasets catalog is the clearest example: fictional entries, dead filters, `alert()`-based "downloads"; the Home page's fabricated stats and hardcoded detection boxes are the same pattern in miniature). **Do not silently wire these up, fake a backend for them, or quietly drop them during replacement.** If a piece of `frontend-v2` implies a feature or data source that doesn't demonstrably exist in the backend today, stop and ask the user before doing anything with it — build it for real only with explicit go-ahead, since there's a real chance no backend exists to support it at all.

---

## 0. Handover log — read this first if you're a fresh session

This file is being handed to a differently-authorized Claude session (one with working GitHub push/PR access) to actually execute the fixes below. The session that wrote §§1-9 could read/analyze/run the app locally but **could not push to GitHub** (org access issue, details below). Nothing in §§1-9 has been applied to the code yet — it is 100% analysis, zero fixes. Everything below is what that session needs to know to pick this up cold.

### 0.1 What actually happened, in order

1. User asked "Sandipan pushed new frontend design, is it true?" → confirmed via `git log --all --format='%an %s'` that Sandipan Majumder had pushed a second, newer frontend at `frontend-v2/` (parallel to the existing wired-up `frontend/`), most recently on 2026-09-20 (`af110b1 add social icons`, `5c66de7 add documentation page`).
2. User asked for a full audit — real vs. mock, polish, reactivity, breaking/misaligned/overlapping issues, missing features — written to an md file for iterative joint refinement toward "presentation ready."
3. That audit was produced by: reading every file under `frontend-v2/src/`; running `npm install` (fresh — `node_modules` did not exist) and `next dev -p 3100` in the background; writing a small Playwright script (see §0.3) to screenshot every route at desktop (1440×900) and mobile (390×844) with the backend intentionally **not** running (to see honest loading/error/empty states); grepping for `alert(`, `TODO`, `mock`, `Math.random`, hardcoded Tailwind color classes, etc.; and cross-checking every `components/ui/*` and `components/layout/*` file against the rest of the tree to find orphaned/dead code. Findings became §§1-8.
4. User asked for a second pass specifically on redundancy/duplication/information-density/"AI slop" aesthetics. That became §9, produced the same way (usage-grep every constant/component, read the remaining unread pages, quantify glow/gradient/blur usage across the tree).
5. User then asked to log the whole session + handover context into this same file (this section) so an "authorised Claude session" (one that can actually push/PR) can execute against it without the original conversation.

### 0.2 Repository state right now — important, don't skip this

- Working directory used: `/home/user/SATQuery-AI` (repo root), frontend code at `frontend-v2/`.
- Branch: `claude/sandipan-frontend-design-hxzo8x`, currently checked out, working tree clean.
- **This branch does not exist on `origin` anymore.** Early in the session, `git fetch origin --prune` reported `- [deleted] (none) -> origin/claude/sandipan-frontend-design-hxzo8x`. It was likely already merged into `prototype` and cleaned up server-side. The local branch was kept as-is per instructions (never force-push/delete on a hunch) and has **no upstream tracking ref** — `git push -u origin claude/sandipan-frontend-design-hxzo8x` is what was attempted, not a push to an existing PR branch.
- Two local commits exist on this branch that are **not on any remote**:
  - `65c56f9` — docs(frontend-v2): add audit of Sandipan's new template (§§1-8)
  - `050ea55` — docs(frontend-v2): add redundancy/clutter/AI-slop pass to audit (§9)
  - Both touch only `frontend-v2/FRONTEND_V2_AUDIT.md` (this file). No application code has been changed or committed anywhere in this session.
- Every `git push` attempt failed identically:
  ```
  remote: Claude doesn't have GitHub access to KushwahaSujal/SATQuery-AI for your organization.
  fatal: unable to access '...': The requested URL returned error: 403
  ```
  This is an org-level GitHub App / connector permission issue, not a network blip — retrying doesn't help. Fix path: an org admin installs the Claude GitHub App (https://github.com/apps/claude/installations/select_target) or the user reconnects GitHub in claude.ai settings. **If you (the new session) have push access, your first move should be to decide whether to keep building on this exact branch (it has real commits worth keeping) or restart it from current `main`/`prototype` per the branch-recovery instructions your own harness gives you** — check whether `af110b1`'s work already landed on `prototype`/`main` before assuming this branch is still the right base.
- `frontend-v2/package-lock.json` was touched by the `npm install` in this session but **deliberately reverted** (`git checkout --`) before committing, because the fresh install pruned ~130 lines the checked-in lockfile had (likely platform-specific optional deps) and that wasn't this task's call to make. Same for `frontend-v2/AGENTS.md` / `frontend-v2/CLAUDE.md` — auto-regenerated by `next dev` on every boot, removed rather than committed since they're boilerplate, not part of the ask. **If you run `npm install`/`next dev` yourself, expect these same two files to reappear and the lockfile to want to shrink again — that's normal, not a new problem to investigate.**

### 0.3 How to reproduce the live-app checks yourself

- Backend was **not running** for any of this — all findings about mock vs. real data came from reading `frontend-v2/src/lib/api.ts`/`endpoints.ts` and matching them against page code, not from a live backend response. If you want to verify against a running backend, that's still untested territory.
- `frontend-v2/node_modules/` already exists from this session's `npm install` — no need to redo it unless it's gone in your environment.
- Dev server: `cd frontend-v2 && npm run dev -- -p 3100` (was left running in the background on port 3100 in this session's container; it will not persist into a new session/container).
- Screenshot approach used (no `playwright-core` in the project, but a global `playwright` package was available at `/opt/node22/lib/node_modules/playwright`): a throwaway script in the scratchpad dir launched `chromium` at `/opt/pw-browsers/chromium` (per this environment's pre-installed browser), visited `/`, `/analysis`, `/datasets`, `/reports`, `/history`, `/documentation`, `/video/fake-job-id` at 1440×900, then `/`, `/analysis`, `/datasets` again at 390×844, and captured console/page errors. That script and its output images lived in this session's scratchpad (`/tmp/claude-0/.../scratchpad/shots*`) and **will not exist in a new session** — regenerate if you need fresh screenshots.

### 0.4 What's NOT been verified yet (be careful)

- No item in §§1-9 has been fixed or even attempted — this is pure analysis.
- Nothing was checked against a **live backend**. All "real vs mock" conclusions are from static code reading (matching `api.ts` calls against page usage), which is reliable for "does this page call a real endpoint" but has not confirmed the backend actually returns well-formed data for every one of those endpoints today.
- The theme-default bug (§4.2) was confirmed by screenshot in a headless browser with **no explicit OS dark-mode preference set** — that's a reasonable proxy for "many real users/judges," but wasn't tested against next-themes' actual system-preference-detection edge cases beyond that one data point.
- Line numbers cited throughout (e.g. `page.tsx:559-610`) match the file state as of commit `050ea55` — if the branch gets rebased or files change before you start, re-verify line numbers before editing blind.

### 0.5 What to actually do

Work §8's ordered list, using §9 as additional input on the same priority tiers (dedupe constants and delete dead components as part of "cleanup pass," fold the Documentation slimdown into whichever pass touches that page). Commit and push as you go — this session couldn't, you can. Once pushed, open a PR against whatever base branch is correct after you've checked §0.2's note about `prototype`/`main`.

### 0.6 Working method — replace one-by-one against `prototype`, not a rewrite

`prototype` is the baseline every change gets measured against. Concretely:

- Don't do a big-bang rewrite of `frontend-v2`. Work the §8/§9 punch list **one item at a time**: pick one bug/redundancy/slop item, fix or replace just that piece of buggy code/logic/UX, verify it against how `prototype`'s current frontend-v2 behaves (or should behave) before moving to the next item.
- For each item: diff the affected component/page against what's on `prototype` first, so you know exactly what's being replaced and don't accidentally reintroduce something that was already fixed there since this branch was cut.
- Land each fix (or small related batch — e.g. "delete all 8 unused components" is one batch, "dedupe TASK_LABELS across 3 files" is one batch) as its own commit, pushed incrementally, rather than queuing everything into one giant diff. This keeps every step individually comparable against `prototype` and reviewable/revertable on its own.
- After each push, the expectation is a visible, checkable improvement over the corresponding piece of `prototype`'s frontend — not just "code changed," but the specific bug/redundancy called out in this doc is now demonstrably gone when compared side-by-side.
- Re-check §0.2 before the first push: confirm whether `prototype` already absorbed some of what `af110b1` had, so you're replacing against the *current* `prototype`, not a stale mental model of it.

---

## 1. Verdict in one paragraph

The design language is strong and the *data layer is mostly real*, not a Figma-to-JSX shell: Home, Reports, History, Documentation and the Analysis job view all genuinely call `frontend-v2/src/lib/api.ts`, which mirrors the real backend contract (`/api/jobs`, `/api/analyze`, `/api/analysis/{id}/layers`, etc.) and renders honest empty/loading states instead of fabricating numbers. That said, it is still a **template**, not presentation-ready: one whole page (Datasets) is 100% decorative mock data, the theme system silently defaults to light mode with broken contrast on several badges, the app has **no mobile/tablet layout at all**, the global search bar every page wires up doesn't exist in the DOM, and there's a real duplicate-render bug in the results view. None of this is cosmetic-only — several items would visibly break a live demo.

---

## 2. What's REAL (backend-wired, no fake data)

| Page/area | Status |
|---|---|
| `lib/api.ts` / `lib/endpoints.ts` | Faithful mirror of the backend contract (upload, analyze, jobs, layers, histogram, export, video). No fabricated fields. |
| Home (`/`) — Recent Analyses | Pulls from `useJobs()` → `/api/jobs`. Real. |
| Reports (`/reports`) | Real jobs list + `/api/results/{id}` detail panel, real download/report URLs, real before/after slider using actual layer artifacts. |
| History (`/history`) | Same as Reports: real list, real bulk-delete via `DELETE /api/jobs`, real execution trace, real confidence ring. |
| Documentation (`/documentation`) | Curated doc index is hand-written metadata, but actual markdown content is fetched live via `/api/documentation` + `/api/documentation/content` — not fabricated. |
| Analysis chat (`/analysis`) | Real upload (`uploadRasters`/`uploadVideo` with progress), real `analyze()` call, real Zustand store (`useAnalysisStore`) driving job state. |
| Analysis result (`/analysis/[jobId]`) | Real job polling, real layers/artifacts, real video stream, real execution trace tab. Correct "awaiting completion" / "no artifact" fallbacks — no placeholder numbers. |
| Video (`/video/[jobId]`) | Real job/result hooks, honest "No events detected" state, real models-executed list. |

**Takeaway:** don't rebuild the data layer — it's the strongest part of this template. The work is UI polish, not re-wiring.

---

## 3. What's MOCK / decorative

| Location | What's fake | Evidence |
|---|---|---|
| **`/datasets` page** (entire page) | All 6 datasets are a hardcoded `DATASETS` array (`app/datasets/page.tsx:33-148`) — Delhi/Sentinel/RISAT/etc. are fictional demo entries, not from the backend. | — |
| Datasets filter counts | Pills show `All: 124, Optical: 68, SAR: 32…` (`page.tsx:157-163`) while only 6 items actually exist in the array. | Counts don't reconcile with visible cards — will look broken the moment someone counts. |
| Datasets "Region/Resolution/Sort" dropdowns | Render as buttons with chevrons but have **no `onClick`** — pure decoration. | `page.tsx:253-287` |
| Datasets download actions | `onClick={() => alert(...)}` — literal browser `alert()` popups, not downloads. | `page.tsx:371`, `page.tsx:559` |
| Datasets preview "carousel" | Numbers cycle (`1/4 → 2/4…`) but there's only one background div — no image ever changes. | `page.tsx:448-467` |
| Dataset thumbnails everywhere | `.sat-crop-*` / `.sat-preview-*` classes are explicitly labeled `/* Synthetic Satellite Terrain Textures */` — CSS gradients standing in for real imagery. | `globals.css:451-517` |
| Home hero stats row | `98% Detection Accuracy`, `12x Faster`, `2,500+ Analyses Run`, `47 Data Sources` — hardcoded marketing numbers, not telemetry. | `app/page.tsx:30-35` |
| Home hero video overlay | Fixed "WATER BODY" / "BUILT-UP" boxes and a fixed lat/long readout drawn over the background video — looks like a live detection but is static decoration on every load. | `app/page.tsx:435-443` |

**Action needed:** decide whether Datasets becomes a real backend-driven catalog (needs a `/api/datasets`-style endpoint that doesn't exist yet) or gets explicitly reframed as a "sample gallery" so it stops pretending to be live inventory.

---

## 4. Confirmed bugs (would show up in a live demo)

### 4.1 Duplicate render in the Analysis results panel — **P0**
`app/analysis/[jobId]/page.tsx:559-610`: the "Detected events" `<Card>` for video jobs is placed **inside** the `spatial.boxes.map(...)` loop instead of next to it. If a video job has, say, 5 detected boxes, the "Detected events" card renders 5 times, stacked. Needs to be hoisted outside the `.map()`.

### 4.2 Theme silently defaults to light mode + breaks contrast — **P0**
- The app actually mounts `components/Providers.tsx` → `@/providers` (a hand-rolled theme hook), **not** `app/providers.tsx` (which uses `next-themes` + mounts `CommandPalette`). `app/providers.tsx` is dead code — see §6.
- The live `useTheme()` (`src/providers.tsx:19-30`) defaults `mode` to `"system"` and follows `prefers-color-scheme`. Any machine/browser reporting a light preference (common on projector/demo laptops, judge laptops, CI screenshotting) gets the **light** palette by default, not the dark "mission console" look the whole design language (scan-sweep, glow, satellite HUD) was built for.
- In light mode, badge/pill backgrounds across Reports and History use **hardcoded Tailwind dark-shade utilities** (`bg-cyan-950/70`, `bg-blue-950/70`, `bg-purple-950/60`, `bg-rose-950/60`, `bg-amber-950/60`) instead of the `--surface`/`--cyan` design tokens. Result: washed-out, low-contrast pills — confirmed in the Reports screenshot where the active "All Reports" tab text is barely legible.
- **Fix:** pick one theme system (delete the other), default to `dark` regardless of OS preference (or make the toggle actually persist and default sanely), and replace every hardcoded `bg-*-950/*` badge color with the theme tokens already defined for exactly this purpose.

### 4.3 No mobile/tablet layout anywhere — **P0**
`Sidebar.tsx` is a hard `w-60 min-w-[15rem] max-w-[15rem]` with zero responsive classes and no collapse/hamburger state. On a 390px viewport the sidebar eats ~60% of the screen and body copy visibly clips ("Analyz…", "Descri be…", buttons cut off at the edge — confirmed via screenshot on Home, Analysis, Datasets). There is no breakpoint handling anywhere in `layout/`. If this is meant to be demoed on anything but a full desktop monitor, this needs a real mobile nav (drawer/hamburger) before anything else.

### 4.4 Global search bar doesn't exist — **P1**
Every page (`Home`, `Datasets`, `Reports`, `History`, `Documentation`) passes `searchPlaceholder` + `onSearch` into `<TopBar>`, but the actual `<input>` in `TopBar.tsx:77-105` is **entirely commented out**. The `⌘K` hint that used to advertise the command palette is commented out too. Net effect: the topbar search that every page's copy implies exists is just... not there. (Each page does have its own local search input further down, so search isn't *totally* broken, just the global one promised by the topbar.)

### 4.5 Documentation search bar visually breaks — **P1**
`app/documentation/page.tsx`: the search input (`flex-1 min-w-0`) sits next to a non-wrapping row of 7 category filter pills. On desktop (1440px) this squeezes the input so hard the placeholder text is clipped to `"Search b"` (confirmed via screenshot). Needs `flex-wrap` on the filter row or a fixed minimum width reserved for the input.

### 4.6 Video player layout — **P2**
`/video/[jobId]`: the "VIDEO FEED" panel is a tall black box, but the actual `<video>` element renders as a smaller box vertically centered inside it, leaving large dead black bars above/below and no poster image while empty. Needs the video element to fill its container (`object-cover`/`h-full w-full`) and a poster/placeholder frame for the pre-load state.

### 4.7 Follow-up questions don't work — **P2**
The Analysis chat empty-state advertises "Follow-up questions" as a capability (`ChatView.tsx:122`), but the actual follow-up composer in the job results panel is commented out (`app/analysis/[jobId]/page.tsx:696-709`). Either wire it to a real follow-up-turn endpoint or remove the promise from the empty-state copy.

### 4.8 Unpositioned decorative background — **P3**
`ChatView.tsx:55-62`: the subtle grid-texture `<div className="absolute inset-0 ...">` sits inside a parent that is **not** `relative` (`h-full min-h-0 flex-1 flex flex-col ... overflow-hidden` — no `relative`). It happens to look fine today only because no closer positioned ancestor exists yet, but it's one wrapping `relative` div away (e.g. inside a modal/portal) from painting over the wrong region. Add `relative` to the parent explicitly instead of relying on ancestor luck.

---

## 5. Dead code / duplication (confuses future work, should be deleted)

Confirmed via grep — **zero** other files reference these:
- `components/layout/AppHeader.tsx` — a whole second header component (with its own CommandPalette trigger) that nothing renders.
- `app/providers.tsx` — a second Providers tree (next-themes + React Query + CommandPalette) that `layout.tsx` never imports. **This is why the command palette (⌘K) doesn't actually open in the running app** despite `CommandPalette.tsx`/`CommandPaletteContext.tsx` existing and looking complete.
- `components/layout/Rail.tsx`, `components/layout/EmptyState.tsx`, `components/analysis/ResultsView.tsx` — unused.
- `components/layout/StatusBadge.tsx` **and** `components/ui/StatusBadge.tsx` — two competing status-badge components, neither actually imported by a page.
- `app/reports/page.tsx:488-512` — a ~25-line commented-out "Export Formats" block left in source.

**Recommendation:** delete all of the above rather than "fix" them — they're template scaffolding, not in-progress features, and every one of them adds confusion about which theme/header/badge system is canonical.

---

## 6. Missing vs. the older `frontend/` (already-wired app)

- No **System / Diagnostics** page — old `frontend/` has `components/system/ConnectionPanel.tsx` for backend/model health; frontend-v2 only shows a small "AI Ready · x/y" pill in the topbar (itself currently invisible-ish, see §4.2 contrast issue) with nowhere to drill in.
- No top-level **History** nav item in the sidebar — reachable only via "View all" link or a recent-item click, unlike Home/New Analysis/Datasets/Reports which are first-class nav entries.
- No nav entry at all for **Video Intelligence** — the route (`/video/[jobId]`) exists and is fully wired, but there is no way to reach it from navigation; it's only reachable if a video job ID is already known.
- Old frontend's `hooks/useSegmentPlayer.ts` and `components/video/TrackOverlay.tsx` (frame-accurate track overlay scrubbing) have no equivalent in v2's simpler video page.

---

## 7. Genuine strengths (keep these)

- Motion/animation system (`framer-motion` stagger/fade variants) is consistent and tasteful, not overused.
- Design tokens (`globals.css` `:root`/`.light`) are a real, fairly complete system — the problem is *inconsistent use* (hardcoded Tailwind shades bypassing the tokens), not the tokens themselves.
- Before/after comparison slider (Reports & History detail panels) is a nice, real, working interaction against real artifact URLs.
- Documentation page's live-fetch-with-cache pattern (`documentCache`/`documentRequests` refs) is solid engineering, not template filler.
- Empty/loading states are honest everywhere in the wired pages — no fabricated confidence scores or fake box counts when data is absent.

---

## 8. Proposed order of attack

1. **P0 — Theme default + contrast** (§4.2): pick one provider tree, delete the other, default to dark, fix hardcoded badge colors.
2. **P0 — Mobile layout** (§4.3): collapsible sidebar / hamburger nav, at minimum a `sm:` breakpoint that hides the sidebar behind a toggle.
3. **P0 — Duplicate-render bug** (§4.1): one-line structural fix in `analysis/[jobId]/page.tsx`.
4. **P1 — Global search** (§4.4): either restore the real `<input>` in `TopBar` and wire it to something meaningful, or remove the dead `onSearch`/`searchPlaceholder` props from every caller so the API isn't lying.
5. **P1 — Documentation search layout** (§4.5): quick flex/wrap fix.
6. **Cleanup pass** (§5): delete the ~6 orphaned files; this also resolves the ⌘K confusion for free (either wire the real CommandPalette in, or delete it too — currently it's Schrödinger's feature).
7. **Decide Datasets' fate** (§3): real catalog vs. explicitly-labeled sample gallery.
8. **P2/P3 polish**: video player fill, follow-up composer, background-div positioning.
9. **Parity pass** (§6): System/diagnostics page, History + Video nav entries.
10. **Redundancy/clutter/slop pass** (§9, below): delete the unused component library, consolidate the triple-duplicated constants, thin out Documentation, cut the decorative filler.

---

## 9. Redundancy, clutter & "AI slop" pass

A second pass specifically for: duplicated logic, unused scaffolding, information crammed onto single screens, and generic AI-template aesthetics (as opposed to actual bugs, covered above).

### 9.1 The same constants are hand-copied 3 times, each slightly wrong

- **`TASK_LABELS`** (task-id → human label) is independently redefined in `components/layout/Sidebar.tsx`, `app/reports/page.tsx`, and `app/history/page.tsx` — three different shapes (`string`, `{label, type}`, `{label, category}`) for what should be one lookup table. Fix a label in one place, the other two silently stay wrong.
- **`STATUS_MAP` / `STATUS_LABEL` / `STATUS_DOT` / `STATUS_PILL`** (job status → color/label) are redefined again in `reports/page.tsx`, `history/page.tsx`, and `analysis/[jobId]/page.tsx` — with **different status keys covered** in each (Reports handles 5 states, History 8, the job page 10). A status that reports correctly on one page can fall back to a wrong default on another.
- Framer-motion `stagger`/`fadeUp`/`rowVariant`/`cardVariant` animation variant objects are copy-pasted verbatim across `history`, `datasets`, `reports`, and `documentation` pages — identical code, four places.
- **Fix:** one `lib/taskLabels.ts`, one `lib/statusMap.ts`, one `lib/motionVariants.ts`. Nothing here needs to be page-specific.

### 9.2 `Reports` and `History` are near-duplicate pages

Side by side, `app/reports/page.tsx` and `app/history/page.tsx` share: the same job-list-with-filter-tabs layout, the same before/after comparison slider implementation, the same status pill rendering, the same thumbnail logic for bi-temporal vs single-image jobs. They differ mainly in which columns/actions show. This should be one `<JobList>` component taking a `mode` prop, not ~500 duplicated lines each — right now a fix to the slider or thumbnail logic has to be made twice and will drift.

### 9.3 A whole unused component library is sitting in `components/ui/`

Usage-checked every file in `components/ui/` against the rest of the app. **Genuinely never rendered anywhere:**
`AnimatedBeam`, `AnimatedGradientText`, `AuroraText`, `ConfidenceRing`, `Dialog` (+ 8 sub-parts), `GlowCard`, `Marquee`, `ParticleBackground` — 8 components, none imported by any page.

Worse: the shadcn-style core primitives **`Button` and `Select`** are exported from the barrel and presumably meant to be the standard button/dropdown — but grep confirms **zero pages actually render them**. Every page hand-rolls its own `<button className="...">` and its own custom dropdown markup instead (see the dead "All Regions"/"All Resolutions" dropdown buttons in §3 of the original audit — they'd have real keyboard/a11y behavior for free if they used `<Select>`). So there are two parallel, disconnected UI systems in the same codebase: a proper primitive kit nobody uses, and ad-hoc inline-Tailwind markup everywhere.

A handful of the "visual effects" components are used exactly **once** each (`BorderBeam` — one icon on Reports; `ShimmerButton` — one CTA on Home; `NumberTicker` — one stats row on Home) — scattered flourishes rather than a deliberate pattern.

**Recommendation:** delete the 8 unused files outright. For `Button`/`Select`, either commit to using them everywhere and delete the ad-hoc versions, or delete them too — don't keep an unused "correct" version alongside dozens of copies of the wrong version.

### 9.4 Documentation page: 12 stacked content sections, several re-documenting the same thing twice

One continuous scroll on `/documentation` contains: hero + 4 stat tiles, search bar, 7 category filter pills, a doc-card grid, a "Quick Start Commands" block, an "API Reference Matrix" block, a "Workflow Functionality" block, a "Model Dossier Map" block — plus a right rail with **4 more** cards (Table of Contents, Readiness Notes, Primary Workflows, "Best Next Read"). That's 12 distinct card sections on one page.

Several of these **duplicate content that already lives in the linked markdown files**, just re-typed as hardcoded JS objects in the page itself:
- "API Reference Matrix" (`apiEndpoints`, `documentation/page.tsx:293-302`) duplicates what's already fully specified in the linked "Frontend API Contract" doc.
- "Model Dossier Map" (`modelFamilies`) duplicates the linked "Model Dossier Index."
- "Workflow Functionality" (`workflows`) duplicates the linked "Execution Flow Map."
- The 280-line `docDetails` object (purpose/contents/keyDetails/useWhen per doc, `documentation/page.tsx:347-627`) is a hand-written *summary of a summary* for docs the page already links to and can fetch and render in full via `MarkdownPreview`.

This is documentation about documentation — a lot of hardcoded prose duplicating source-of-truth files it sits three clicks away from. Cut it down to: hero, search/filter, doc grid, reader. Let the actual markdown carry the API/workflow/model details instead of re-authoring them a second time in JSX.

- **"Best Next Read"** sidebar box gives the same static, generic advice ("Start with the API contract for UI work...") regardless of what's selected or searched — filler copy, not a real recommendation engine.

### 9.5 Conflicting data sources, and the wrong one wins

`documentation/page.tsx:837-842`: `allDocs` merges the hand-curated `docResources` array with live `repositoryDocs` fetched from the backend, via `new Map([...docResources, ...repositoryDocs])` keyed by path. Since `repositoryDocs` is spread **after** `docResources`, and `Map` keeps the last value for a duplicate key, **the generic backend-derived metadata silently overwrites the curated summaries/tags/status whenever the backend is reachable** (backend-derived status is just `path.startsWith("project/") ? "Live State" : "Reference"` — much thinner than the hand-written entries). Backwards: the polished copy this page was clearly designed around only appears when the backend is *offline*. Either drop the duplication (curated metadata should win) or drop the curated array (trust the live index).

### 9.6 Decorative filler repeated on every single page

- The **"Connect with Us"** GitHub/YouTube icon row and the **"Better insights for a healthier planet / AI-powered remote sensing for a sustainable future"** mission-statement card are pinned to the bottom of `Sidebar.tsx` and render, unchanged, on every route in the app (Home, Analysis, Datasets, Reports, History, Documentation, Video). It's permanent vertical space spent on static marketing copy that never varies with context — a classic generated-template filler pattern rather than product UI.
- Home hero: fake scanline/corner-bracket/crosshair "HUD" decorations plus hardcoded "WATER BODY"/"BUILT-UP" bounding boxes and a fixed lat/long readout drawn over a stock background video (already flagged as mock data in §3) — visually it's cosmetic "AI demo" theater rather than functional UI, and it's the very first thing anyone sees.
- `ChatInput.tsx`: three separate "Video" analysis-type menu entries (Video Analysis / Video Grounding / Video Change, `ChatInput.tsx:18-20`) all share the **exact same SVG icon path**, copy-pasted — presented as 3 distinct choices in a picker with zero visual differentiation.
- `ChatInput.tsx:135-146`: a numbered-badge overlay for attached images is commented out in place rather than removed, referencing `attachedImageLabels` — a prop that's threaded all the way from `ChatView` down but never actually rendered anywhere now.

### 9.7 Quantified "glow-and-gradient" aesthetic

Across ~7,150 lines of page/component TSX: **17** distinct `shadow-[0_0_Npx_rgba(...)]` glow declarations, **18** `backdrop-blur` usages, **14** `bg-gradient-to-*` fills, **55** `rounded-xl`/`rounded-2xl` usages. Nearly every panel, pill, and button gets its own glow/blur/gradient treatment — which reads as a generated "sci-fi SaaS" aesthetic applied uniformly rather than a deliberate hierarchy where glow means something (e.g., "active"/"live"/"alert"). Worth deciding on 2-3 places glow is *meaningful* (e.g., a running job, a live status dot) and removing it as default decoration everywhere else — it'll read as more intentional with less of it, not more.

---

## 10. Verification pass — §§1-9 re-checked against real code (2026-09-21)

Run by the executing session before touching any code, at the user's instruction ("re-verify audit claims first"). §§1-9 were written in a different checkout (`/home/user/SATQuery-AI`, branch now deleted); this pass re-checks them in `/home/natsu/dev/isro` against `frontend-v2/` as imported from `origin/main` (`af110b1`) and against **`prototype`'s** backend.

### 10.0 Corrections to §0.2 — the repo situation is not what §0.2 assumed

| §0.2 assumption | Reality |
|---|---|
| "`af110b1` was likely already merged into `prototype`" | **False.** `git merge-base --is-ancestor af110b1 origin/prototype` → no. `af110b1` is the **tip of `origin/main`**. |
| implied: `prototype` and `main` are close | They have **diverged hard**: `main` is 18 commits ahead of `prototype`, `prototype` is **54** ahead of `main`. `main`'s 18 are Sandipan's UI work; `prototype`'s 54 are the backend work (evidence/verifier, EuroSAT routing, Q-04x). |
| "frontend code at `frontend-v2/`" on the working branch | `frontend-v2/` existed **only on `origin/main`**. `prototype` had just `frontend/`. |
| `FRONTEND_V2_AUDIT.md` committed at `65c56f9`/`050ea55` | Those commits died with the deleted branch. The file was **not in any tree**; this copy was re-created from the handover text. |

**How `frontend-v2` was brought in:** `git checkout origin/main -- frontend-v2` onto a branch off `prototype` (`feat/frontend-v2-into-prototype`) — the **directory only**. A real `main`→`prototype` merge was rejected because `main`'s 18 commits also carry backend edits (`analysis.py` +102, `video.py` +135, `documentation.py` new, `planner.py`, `db/session.py`, `state.py`, `schemas/agent.py`) that would collide head-on with `prototype`'s 54 commits of backend work. Importing the directory keeps the frontend question separate from a backend merge fight.

### 10.1 The live-backend gap §0.4 warned about — now closed

All 25 endpoints in `lib/endpoints.ts` were diffed against `prototype`'s registered routes. **23 of 25 exist.** The two that do not:

- `/api/documentation`
- `/api/documentation/content`

`prototype`'s router (`backend/app/api/v1/router.py`) registers only `system, uploads, video, visualization, artifacts, analysis`. `documentation.py` **exists only on `main`**.

**This falsifies §2's Documentation row.** "Content is fetched live via `/api/documentation`" is true against *main's* backend and **false against `prototype`'s**, where both calls 404.

Two knock-on consequences:
- The Documentation page's live-fetch is dead on `prototype` until that endpoint is ported.
- It **masks §9.5**: with `repositoryDocs` always empty, the `Map` merge can never overwrite the curated entries, so curated metadata always wins. The §9.5 bug is real in the code but currently unreachable on `prototype` — it will appear the moment the endpoint is ported. Fix it *before* porting, not after.

Also verified sound (no bug): the `"auto"` sentinel in the task picker is correctly stripped at `stores/useAnalysisStore.ts:179` and mapped to `override_task` at `lib/api.ts:295`, matching `AnalyzeRequest` (`backend/app/schemas/requests.py:5-16`). §2's "don't rebuild the data layer" verdict holds.

### 10.2 NEW — P0 that §9.1 filed as a redundancy nit: Reports reports running jobs as "Completed"

`app/reports/page.tsx:190`:
```ts
const status = STATUS_MAP[report.status] || STATUS_MAP.COMPLETED;
```
and again at `:315`: `{STATUS_MAP[result.status]?.label || "Completed"}`.

Reports' `STATUS_MAP` covers 5 keys: `COMPLETED, RUNNING, PENDING, QUEUED, FAILED`. `prototype`'s backend (`backend/app/schemas/agent.py:6-13`) emits `QUEUED, VALIDATING, PLANNING, RUNNING, GENERATING_EVIDENCE, COMPLETED, FAILED`.

So a job in **`VALIDATING`, `PLANNING` or `GENERATING_EVIDENCE`** falls through to `STATUS_MAP.COMPLETED` and is rendered with a green "Completed" pill while it is still running. That is not a styling inconsistency — the Reports page asserts a job is finished when it is not, and the row invites a click through to a report that does not exist yet. For a project whose whole stance is structural honesty, this is the most serious item in the document.

(Also: `PENDING` appears in both frontend `STATUS_MAP`s but is **not** in `prototype`'s enum; `History` labels the same states "Processing" where Reports says "In Progress".)

**Re-tiered to P0.** It belongs above §8-item-5, not in the §10-item-10 cleanup pass.

### 10.3 Confirmed exactly as written

| Item | Verification |
|---|---|
| §4.2 theme | All three sub-claims hold. `layout.tsx:5` mounts `@/components/Providers`; `app/providers.tsx` has **zero** importers; `providers.tsx` seeds `useState<ThemeMode>("system")` and follows `prefers-color-scheme`. |
| §4.3 mobile | `Sidebar.tsx:124` is `w-60 min-w-[15rem] max-w-[15rem]`. Stronger than stated: the **entire** `components/layout/` tree contains exactly **one** responsive utility — `hidden sm:flex` on the AI-Ready pill, `TopBar.tsx:110`. |
| §4.4 global search | Confirmed. Whole search `<div>` incl. the `⌘K` `<kbd>` commented out, `TopBar.tsx:76-105`. |
| §4.7 follow-up composer | Confirmed commented out, `app/analysis/[jobId]/page.tsx:695-709`. |
| §4.8 unpositioned background | Confirmed. Parent `ChatView.tsx:55` has no `relative`; child at `:57` is `absolute inset-0`. |
| §5 dead code | Confirmed: `AppHeader`, `Rail`, `EmptyState`, `ResultsView`, both `StatusBadge`s, `app/providers.tsx` — zero importers each. `CommandPalette` is referenced *only* by the two dead files (`app/providers.tsx`, `AppHeader.tsx`) — Schrödinger's feature, exactly as described. Commented "Export Formats" block confirmed at `reports/page.tsx:487-512`. |
| §9.1 `TASK_LABELS` | Confirmed: 3 definitions, 3 different shapes — `Sidebar.tsx:16` (`string`), `reports/page.tsx:17` (`{label,type}`), `history/page.tsx:19` (`{label,category}`). |
| §9.1 status key counts | Confirmed **exactly**: Reports 5, History 8, job page 10 (`STATUS_LABEL`/`STATUS_DOT`/`STATUS_PILL`, all keyed by `JobStatus`). |
| §9.3 the 8 unused | All 8 confirmed at zero JSX usage outside `components/ui/`. |
| §9.3 `Button`/`Select` | Confirmed dead: zero imports **and** zero JSX usages anywhere outside their own definition files. |
| §9.3 used-once | Confirmed: `BorderBeam` ×1 (`reports/page.tsx:105`), `ShimmerButton` ×1 (`page.tsx:571`), `NumberTicker` ×1 (`page.tsx:470`). |
| §9.5 merge order | Confirmed verbatim at `documentation/page.tsx:838-839` — `[...docResources, ...repositoryDocs]`, last-wins. (But see §10.1: unreachable on `prototype` today.) |
| §9.6 video icons | Confirmed: `video_vqa`, `video_grounding`, `video_change` share a byte-identical SVG path, `ChatInput.tsx:18-20`. |
| §3 datasets | Confirmed: `DATASETS` at `datasets/page.tsx:33`, `All: 124` at `:158`, `alert()` at `:371` and `:559`. |
| §3 home stats | Confirmed hardcoded at `app/page.tsx:29-34` — 98/12x/2500+/47. |

### 10.4 Corrected — claims that were wrong or incomplete

**§4.1 is worse than described.** The `Detected events` `<Card>` is not merely inside the `.map()` — it is the **third flex child of each region row** (`app/analysis/[jobId]/page.tsx:559-608`), sitting alongside the label `<span>` and score `<span>` inside a `flex items-center justify-between` div. Two distinct defects, not one:
1. It renders once per region, **capped at 8** by `spatial.boxes.slice(0, 8)` — so "5 boxes → 5 copies" is right only below 8.
2. A block-level Card is being laid out as a flex item in a row sized for a label and a percentage.

The fix must hoist it out of the `Detected Regions` Card **entirely**, not just out of the map — video events are not a per-region concern. Still P0.

**§9.1's motion-variant claim is wrong.** They are *not* "copy-pasted verbatim / identical code, four places." The values have drifted:

| page | `staggerChildren` | `delayChildren` |
|---|---|---|
| history | 0.07 | 0.1 |
| datasets | 0.07 | 0.05 |
| reports | 0.06 | 0.05 |
| documentation | 0.05 | 0.04 |

`rowVariant` differs too — history `x:-12`/0.4s vs reports `x:-8`/0.35s. So extracting `lib/motionVariants.ts` is **not** a pure refactor: it forces a canonical-timing decision that will visibly change the animation feel of three of the four pages. Do it deliberately, or keep per-page overrides.

**§4.5's diagnosis is wrong** (symptom plausible, mechanism misread). The filter row **already** has `overflow-x-auto` with `whitespace-nowrap` pills (`documentation/page.tsx:1010`), and the outer container is `flex flex-col lg:flex-row` (`:989`) — so it stacks below `lg`. It clips not for lack of wrapping, but because the pill container is a flex item with default `min-width:auto`: it refuses to shrink below its min-content width, `overflow-x-auto` never engages, and the `flex-1 min-w-0` search input (`:990`) absorbs the entire shortfall. **Fix is `min-w-0` on the pill container**, not `flex-wrap`.

**§9.3's dead list is incomplete.** `Input` (`components/ui/input.tsx`) is also at zero usage and the audit missed it. Full confirmed-dead set at zero JSX usage outside `components/ui/`: `Button`, `Select` (+6 sub-parts), `Dialog` (+9 sub-parts), `Input`, `GlowCard`, `ParticleBackground`, `AnimatedGradientText`, `AnimatedBeam`, `AuroraText`, `Marquee`, `ConfidenceRing`, `StatusBadge`. Note `SpotlightCard` (×3), `BlurFade` (×6), `Badge` (×4), `Separator` (×4), `Skeleton` (×3), `Tabs`, `Progress`, `Tooltip`, `Card` **are** used — do not sweep them up.

**NEW — the picker cannot request a capability the backend just gained.** `ChatInput.tsx`'s `ANALYSIS_TYPES` never offers `single_image_classification` — the EuroSAT capability routed by `abaa376 feat: route EuroSAT as a capability` — nor `video_grounding_tracking`. Both are valid `TaskType`s on `prototype`. The reverse direction is clean: every picker value except the `"auto"` sentinel is a real backend task.

**Latent, not live:** `endpoints.artifacts(jobId, path)` builds a 2-segment path while `prototype`'s route is `/api/artifacts/{request_id}/{artifact_type}/{filename}` (3 segments) — but the helper has **zero call sites**, so nothing breaks today. Don't wire it without fixing the shape.

### 10.5 Still unverified — do not treat as confirmed

This pass read code; it did **not** boot the app. `node_modules/` from §0.3 does not exist in this checkout, and no dev server or browser was run. Therefore these remain §0.4-grade claims:

- §4.2's *visual* contrast assertion (the "All Reports" tab being barely legible). The hardcoded `bg-*-950/*` utilities are real in source; how bad they look in light mode is not re-measured here.
- §4.5's `"Search b"` clipping — mechanism identified above, pixel symptom not re-observed.
- §4.6 video-player dead bars, and §4.3's specific mobile clipping strings ("Analyz…", "Descri be…").
- §9.7's counts (17 glows / 18 blurs / 14 gradients / 55 rounded) — not re-counted.
- Whether the 23 reachable endpoints **return well-formed data**, as opposed to merely existing. Route existence is now proven; response shape is not.

### 10.6 §6 parity re-checked — confirmed, and it understates the gap

§6 was not covered by the first verification pass. Re-checked now against `frontend/` (the wired app) on
the same branch.

**Confirmed as written:** `frontend/src/app/system/` + `components/system/ConnectionPanel.tsx`,
`hooks/useSegmentPlayer.ts` and `components/video/TrackOverlay.tsx` all exist in the old frontend and
have **no** equivalent in v2. v2's sidebar has 5 nav entries (`/`, `/analysis`, `/datasets`, `/reports`,
`/documentation`) — no History, no Video, exactly as described.

**§6 missed three whole routes.** Full route diff:

| old `frontend/` route | v2 | note |
|---|---|---|
| `/` | yes | — |
| `/analysis/[jobId]` | yes | — |
| `/jobs` | covered | v2 splits it into `/history` + `/reports` |
| `/models` | **absent** | 59-line model registry page. v2 has no models route; only the Documentation page's hardcoded "Model Dossier Map" (which §9.4 already flags as duplicated prose). |
| `/system` | **absent** | 89-line diagnostics page — the §6 item. |
| `/visual-analytics/[jobId]` | **absent** | **276 lines.** The largest single omission in the whole audit and unmentioned by §6. |
| `/video/[jobId]` | yes | unreachable from nav (§6) |

**The visual-analytics gap is load-bearing, not cosmetic.** `frontend-v2/src/hooks/useSystem.ts` defines
`usePixelInspector` (`:106`) and `useHistogram` (`:113`) — and both have **zero consumers** anywhere in
v2. `endpoints.legend` has **zero** references outside `endpoints.ts`. So v2 ships no pixel inspection,
no histogram, and no legend UI at all, while the old frontend references them 4 / 12 / 13 times and has
a dedicated page for them. All three endpoints exist and work on `prototype` (§10.1) — this is working
backend capability with the UI removed, the mirror image of the §3 problem where v2 has UI with no
backend.

For comparison, every other hook in `useSystem.ts` (`useHealth`, `useModels`, `useJob`,
`useAnalysisResult`, `useVideoResult`, `useLayers`) does have consumers — the two orphans are precisely
the visual-analytics pair.

**Revised §10.7 item 9:** the parity pass is bigger than "System page + two nav entries." It is
`/system`, `/models`, and `/visual-analytics/[jobId]` — and the last of those needs the two orphaned
hooks wired to a real layer inspector, not written from scratch.

### 10.7 Revised order of attack

§8 stands, with these amendments:

0. **NEW P0 — Reports' false "Completed"** (§10.2). Smallest fix, worst consequence, and it is the one item that contradicts the project's honesty stance. Do it first.
1. §8-1 theme (§4.2) — unchanged.
2. §8-2 mobile (§4.3) — unchanged; note there is exactly one responsive class to build from.
3. §8-3 duplicate render (§4.1) — now a two-part structural fix, not one line (§10.4).
4. §8-4 global search (§4.4) — unchanged.
5. §8-5 documentation search (§4.5) — use `min-w-0`, not `flex-wrap` (§10.4).
6. §8-6 cleanup — now **13 dead `ui/` exports + 6 dead files**, `Input` included (§10.4).
7. **Before any Documentation work:** decide the `/api/documentation` port (§10.1), and fix §9.5's merge order *first* so porting the endpoint doesn't immediately regress the curated copy.
8. §8-7 Datasets' fate — unchanged, still needs the user's call per the hard constraint.
9. Remaining §8-8/9/10 polish and parity.
10. **NEW, low:** expose `single_image_classification` (EuroSAT) and `video_grounding_tracking` in the picker (§10.4), so the UI can reach what the backend can now do.

---

*Next: §10.7 item 0, then §8 top-to-bottom, one commit per item.*
