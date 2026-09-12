# Project Working Docs

Backend team's working documentation. Separate from `docs/`, which holds the team's
public-facing specification and model dossiers.

**Start here each session:** [`memory.md`](memory.md) — live state, what's done, what's next.

| File | What it's for |
|---|---|
| [memory.md](memory.md) | Live project state, build scorecard, session history. Read first, update last. |
| [decisions.md](decisions.md) | Why the code is the way it is. Every non-trivial change gets an entry. |
| [flow.md](flow.md) | Execution map — entry points, call chains, and what changed each session. |
| [prd.md](prd.md) | Requirements: what we're building, for whom, and the mandatory SIH scope. |
| [architecture.md](architecture.md) | The system as the code actually is — stack, layout, request lifecycle. |
| [restructure.md](restructure.md) | Codebase reorganisation plan (S0–S6) and its measured justification. |
| [phases.md](phases.md) | Development phases, ordered by what fails the evaluation first. |
| [rules.md](rules.md) | Working agreement: libraries, conventions, error handling, AI boundaries. |
| [design.md](design.md) | Visual system — palette, typography, provenance badges, layout. |
| [qna.md](qna.md) | Change verification record. Major changes get a written Q&A before merge. |
| [handoff/ask-ayushman.md](handoff/ask-ayushman.md) | What we need from the other backend dev, and why. |
| [handoff/ppt-results.md](handoff/ppt-results.md) | Measured results for the presentation round. |

## Conventions

- Numbers in these docs are **measured**, never estimated. If something isn't measured it says
  `NOT MEASURED`.
- Where `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md` and the source disagree, these docs follow the
  **source** and flag the divergence.
- Major changes are recorded in `qna.md`, a transcript that never gates the work — see `rules.md` §6.
