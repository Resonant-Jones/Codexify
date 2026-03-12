# Claude Code Guidance for Codexify

This file guides Claude Code style work inside the Codexify repo. It emphasizes repo-grounded edits, small blast radius, and architectural clarity.

## Purpose

This document provides operational guidance for AI-assisted coding sessions within Codexify. All edits should:

- Be grounded in the actual repo structure and existing patterns
- Maintain a small blast radius - change only what is necessary
- Prioritize architectural clarity over cleverness
- Respect established boundaries between subsystems

## Repo Structure

The Codexify repository is organized into these major areas:

### guardian/
The Guardian layer handles routing, request mediation, and external interface concerns. Contains agents, API route handlers, command bus infrastructure, and cognition components. Should not invent new backend abstractions casually.

### backend/
Core server-side logic including RAG services, TTS services, vector store operations, and database migrations. Scripts and utility tooling live here. Treat storage/API/domain expansion as earned, not assumed.

### frontend/
React/TypeScript application code. Contains the UI layer, component library, and client-side state management. Avoid duplicate product surfaces - check existing implementations before adding new ones.

### docs/
Documentation including architecture decisions, audit reports, campaign materials, CLI references, and development guides.

### tests/
Backend tests live in `tests/` covering routes, core systems, memory, plugins, realtime, and server components. Frontend tests live in `frontend/tests/`. Always identify neighboring tests before editing code.

### Other notable directories:
- `codex_runner/` - Task execution infrastructure
- `codex_tasks/` - Task definitions and handling
- `codexify/` - Core Codexify module
- `flows/` - Workflow definitions
- `config/` - Configuration files
- `services/` - External service integrations
- `plugins/` - Plugin system
- `scripts/` - Operational scripts

## Architectural Boundaries

- **Guardian routes** should not invent new backend abstractions casually. Prefer routing to existing services.
- **Prefer existing runtime rails** before adding new subsystems. Check what is already wired and working.
- **Avoid duplicate product surfaces**. Search for existing implementations before creating new ones.
- **Treat storage/API/domain expansion as earned, not assumed**. New tables, routes, or domain types require clear justification.
- **Respect the migration flow**: `guardian/db/migrations` is symlinked to `backend/migrations`.

## Working Style

- **Inspect before editing**. Read the relevant files first. Understand the patterns in use.
- **Prefer the smallest truthful fix**. A direct change beats a decorative adapter.
- **Avoid reviving dead abstractions** unless required by current contracts. Check if code is actually imported and used.
- **Distinguish runtime-proof from type/spec presence**. A type definition or stub does not mean capability exists.
- **Avoid broad refactors** unless explicitly requested. Stay focused on the task at hand.
- **Verify mount/import/runtime paths** before assuming behavior. Check actual wiring, not just declarations.

## Testing Rules

Run tests appropriate to the work:

| Work Type | Test Command |
|-----------|--------------|
| Backend-oriented | `pytest -v` |
| Frontend-oriented | `pnpm test` |
| Mixed (backend + frontend) | Run both commands |
| Docs-only | No automated tests apply - state this explicitly |

Always run tests from the repo root. For targeted test runs, use `pytest -v tests/<path>` or `pnpm test -- <pattern>`.

## Output Contract

All agent outputs must include:

1. **Summary of changes** - What was done and why
2. **Files changed** - List of modified/created/deleted files
3. **Test results** - Output from test commands or explicit note when no tests apply
4. **Git commit hash** - The commit that contains the changes

## Safety / Change Discipline

- **Do not silently widen scope**. If the task grows, say so and ask for confirmation.
- **Do not add new architecture to solve a local issue**. Prefer direct fixes.
- **Verify mount/import/runtime paths before assuming behavior**. Check that code is actually wired in.
- **Prefer direct fixes over decorative adapters**. Deletion, direct wiring, or a thin shim are usually better than speculative abstraction.
- **Do not commit sensitive files**. Avoid committing `.env`, credentials, or secrets.
