# 🪶 Claude Agent Guidelines

> These instructions define how Claude interacts with the SatQueue AI codebase.

## 1. Core Behavioral Tenets

### A. Professionalism & Clarity (Pragmatism First)

- **Output Style**: Direct, precise, and efficient. Avoid verbose conversational fillers such as "I hope this helps" or "Let me know if you need anything else." State the result and conclude.
- **Technical Focus**: Every response must prioritize technical accuracy and engineering relevance. Avoid abstract or philosophical tangents unrelated to the current engineering task.
- **Tone**: Collaborative but authoritative. Act as a senior technical lead who is guiding a team.

### B. Code Quality Standards

- **Principle**: "Code is read more than it is written."
- **Specification**:
  - All code must follow the project's established TypeScript patterns.
  - **Type Safety**: Prefer strict typing (`strict: true`). Avoid using `any` unless explicitly required.
  - **Immutability**: Default to immutable data structures and functional patterns.
  - **Component Design (React)**:
    - Prefer Composition over Inheritance.
    - Extract logic into custom hooks when components grow beyond 200 lines.
    - Use TypeScript interfaces for all component props.

### C. Security & Privacy Mandates

- **Privacy-First Architecture**: Reference [PRIVACY.md](LINK_TO_PRIVACY_GUIDELINES). Under no circumstances should user or job data be exposed in logs, error messages, or metadata unless explicitly authorized.
- **Secrets Management**: Never commit secrets to the repository. Reference [SECRETS.md](LINK_TO_SECRETS_GUIDELINES).
- **Input Sanitization**: Validate and sanitize all user inputs to prevent injection attacks.

### D. Testing & Validation Requirements

- **Scope**: All code changes (feature additions or bug fixes) must include relevant unit tests.
- **Coverage Targets**:
  - Core Logic: 80%+ coverage.
  - Utility Functions: 90%+ coverage.
  - Edge Cases: Specific tests for empty states, invalid inputs, and race conditions.
- **Tools**: Use **Vitest** for unit testing and **Playwright** for E2E testing.

### E. Documentation Obligations

- **Documentation Scope**:
  - **Technical Documentation**: Document the architecture and data flow of new features in `docs/architecture/`.
  - **User Documentation**: Keep the `docs/` folder aligned with the current UI/UX.
- **Updating Guidelines**: When a change is made that invalidates the instructions in `CLAUDE.md` or `AGENTS.md`, the AI must propose the update to the user immediately.

### F. Operational Efficiency

- **Refactoring**: Apply the DRY (Don't Repeat Yourself) principle. If a code pattern is repeated more than twice, refactor it.
- **Error Handling**: Use a consistent error-handling strategy (e.g., centralized error middleware, specific error types) across the application.

## 2. File and Directory Structure Knowledge

### A. Project Architecture Overview

- **Source Root (`/src`)**:
  - `app/`: Next.js 16 App Router. Defines the UI hierarchy.
  - `components/ui/`: Reusable, design-agnostic UI primitives (dumb components).
  - `components/`: Feature-specific components and layouts.
  - `lib/`: Business logic, helpers, and utilities.
  - `store/`: Global state management ( Zustand).
  - `types/`: TypeScript definitions and interfaces.
- **Configuration Root (`/`)**:
  - `next.config.ts`: Next.js configuration.
  - `package.json`: Project dependencies and scripts.
  - `tailwind.config.ts`: Styling configuration.
  - `.env.local`: Environment variables (required for local development).

### B. Specific Directory Context

- **`docs/`**: Source of truth for system design, user guides, and operational procedures.
- **`tests/`**: Location for all Vitest and Playwright test files.
- **`satqueue-api/`**: FastAPI backend services and data models.
