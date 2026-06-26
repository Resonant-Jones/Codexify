# Codexify Repo Orientation Report

**Date:** 2026-06-26  
**Lens:** Cartographer  
**Area inspected:** Codexify repo top-level orientation  
**Status:** `draft`  
**Report type:** report-only learning artifact

## Purpose

This report helps Zac understand the broad shape of the Codexify repo without requiring him to manually read the entire codebase. It is a top-level Cartographer scan — a terrain map, not a deep analysis.

This is not a task proposal. It is not implementation guidance. It does not override `docs/architecture/00-current-state.md`. It is a learning artifact meant to build Zac's mental map of where things live and why they matter.

## Files And Areas Read

- `docs/architecture/00-current-state.md` — current release-truth anchor.
- `docs/architecture/README.md` — architecture KB entrypoint and doc map.
- `docs/collaborators/zac/README.md` — Zac's RAG source entrypoint.
- `docs/collaborators/zac/source-map.md` — deeper pointers for Zac's agent.
- `docs/collaborators/zac/safe-and-sensitive-zones.md` — sensitive zone map.
- Top-level repo listing (all files and directories).
- `guardian/` top-level files and key subdirectories.
- `frontend/src/` top-level and features/components.
- `tests/` top-level directories.
- `config/` and `config/supported_profiles/`.
- `docs/` top-level directories.
- `scripts/` top-level.
- `docker-compose.yml` service list.

## Top-Level Repo Map

| Path | Likely Responsibility | Why Zac Might Care | Caution / Boundary |
|---|---|---|---|
| `guardian/` | Backend application (FastAPI). The main server: routes, core logic, workers, DB models, queue, continuity, command bus, identity, memory, retrieval. | This is where the architectural weight lives. Most architecture-sensitive boundaries are here. | High blast radius. Many sensitive zones. Proposal-required for most changes. |
| `frontend/` | React frontend application. UI shell, persona studio, settings, chat, workspace, connectors. | Good place for low-risk UI exploration and visual polish observation. | Built with pnpm and Vite. Contains its own test harnesses (Vitest, Playwright, Cypress). |
| `tests/` | Test suites for backend, frontend, contracts, and integration. | Essential for understanding what is proven and what is not. | Tests prove only their own surface. Test presence does not equal feature completeness. |
| `docs/architecture/` | Architecture KB: 00-current-state, ADRs, contracts, proof artifacts, Continuity docs. | The canonical truth layer. Read here before making architecture claims. | The single most important directory for understanding Codexify's contracts and boundaries. |
| `docs/collaborators/zac/` | Zac's RAG source directory: lenses, prompts, templates, report archive. | Zac's home base. Start here for any agent-assisted exploration. | Docs-only. No runtime authority. |
| `config/` | Supported profiles, feature flags, route-surface config. | Defines what is and is not active in the supported beta profile. | Profile activation is a release decision, not an implementation task. |
| `scripts/` | Dev scripts, proof harnesses, audits, builds. | Useful for understanding local dev workflow and live-proof evidence. | Some scripts are dev-only. Not all are release-supported paths. |
| `docker-compose.yml` | Supported local Docker Compose stack. Defines all services. | The canonical supported install path for local beta. | Changing Compose topology is architecture-impacting. |
| `Makefile` | Build, test, lint, dev commands. | Entrypoint for local development workflow. | Contains multiple targets; not all are release-relevant. |
| `backend/` | Docker build context for backend images. Dockerfiles, compiled runtime. | Mostly Docker build infrastructure. | Not the source of backend truth — `guardian/` is. |
| `tools/` | Tool definitions and configurations. | Supplementary tooling. | Verify against current runtime before assuming active. |
| `skills/` | Agent skill definitions. | Related to agent capability surfaces. | Docs-only or scaffold-only unless proven active. |
| `plugins/` | Plugin definitions and hosts. | Extension architecture. | Verify against current supported profile before assuming active. |
| `src-tauri/` | Desktop shell (Tauri). Native launcher and packaged app. | Desktop distribution layer. | Packaged desktop path is separate from the supported Docker Compose path. |
| `mobile/` | Mobile Scout companion (future). | iOS Scout contract exists but runtime is not shipped. | Doc-only contracts. Not supported beta. |
| `node_modules/` | Frontend dependencies (pnpm). | Build-time only. | Do not touch manually. |
| `requirements/` | Python dependencies. | Backend dependency specification. | Changes affect the full backend dependency tree. |
| `cypress/` | Cypress E2E test config and specs. | Frontend integration testing. | May require running services. |

## Main System Areas

### Backend / Guardian

The `guardian/` directory is the FastAPI backend. It is the largest and most architecture-dense part of the repo.

**Key subdirectories:**
- `guardian/routes/` — FastAPI route modules. Over 30 route files covering chat, auth, media, codex, command bus, continuity operator, cron, delegations, federation, websocket, and more. The `continuity_operator.py` route is the completed six-route test-only operator surface.
- `guardian/core/` — canonical settings (`config.py`), dependencies/auth (`dependencies.py`), AI router (`ai_router.py`), chat completion service, DB layer, event bus, outbox, supported profile loader. This is the "engine room."
- `guardian/workers/` — background workers: chat completion, coding, delegation, cron, document embed, graph write, candidate ingest, eval. Workers consume Redis queues.
- `guardian/db/` — SQLAlchemy models (`models.py`), Alembic migrations, graph schema. The persistence layer.
- `guardian/queue/` — Redis queue primitives, task events, turn locks, document embed queue.
- `guardian/continuity/` — Continuity operator implementation: write actions, persistence adapter, compiler, contracts.
- `guardian/command_bus/` — Command bus and tool execution policy.
- `guardian/context/` — Context assembly for chat completion (broker, retrieval router).
- `guardian/memoryos/` — Memory and retrieval system: long-term, mid-term, short-term memory, embedders.
- `guardian/cognition/` — Identity contract and resolution.
- `guardian/identity/` — Identity data.
- `guardian/realtime/` — Real-time event delivery.
- `guardian/federation/` — Federation and cross-instance context/search.
- `guardian/sync/` — Sync and connector infrastructure.
- `guardian/tts/` — Text-to-speech.
- `guardian/vector/` — Vector store abstraction.
- `guardian/browser/` — Browser context capture (future).
- `guardian/retrieve/` — Retrieval pipelines.
- `guardian/services/` — Service layer: document parsing, account export, media signing.
- `guardian/knowledge_compiler/` — Knowledge compilation for Codex Wiki / LLM Wiki.
- `guardian/flows/` — Flow Builder primitives.

**Gateway file:** `guardian/guardian_api.py` — FastAPI app entrypoint. Route mounting, middleware, startup.

### Frontend

The `frontend/src/` directory is the React frontend. It is organized by feature and component.

**Key features:**
- `chat` — Chat thread interface.
- `personaStudio` — Persona/profile configuration.
- `settings` — User and system settings.
- `dashboard` — Main dashboard.
- `workspace` — Workspace surface (shelf, scratchpad, inspector).
- `flowBuilder` — Flow Builder authoring.
- `commandCenter` — Command Center / Observability (internal/dev-only).
- `guardian` — Guardian shell and chat portal.
- `memory` — Memory/personal facts UI.
- `connectors` — Connector configuration.
- `ttsConsole` — Text-to-speech console.
- `userProfile` — User profile.

**Key components:**
- `layout` — App shell, sidebar, navigation.
- `chat` — Chat UI components.
- `documents` — Document viewer.
- `auth` — Auth-related components.
- `diagnostics` — Diagnostic displays.

**Entrypoint:** `frontend/src/App.tsx` — React app root.

**Build tooling:** Vite (`frontend/src/package.json`), pnpm workspace (`pnpm-workspace.yaml`).

### Architecture Docs

`docs/architecture/` is the canonical architecture knowledge base.

**Key files:**
- `00-current-state.md` — **The release-truth anchor.** Read this first for any architecture claim. It is authoritative over older docs.
- `README.md` — Architecture KB entrypoint with full doc map.
- `agent-protocol-operations.md` — Agent-facing map for task rituals and workflows.
- `config-and-ops.md` — Env vars, config resolution, health checks, run commands.
- `data-and-storage.md` — Storage systems, key tables, invariants.
- `account-export-restore-contract.md` — Export artifact contract.
- `runtime-protocol-token-contract.md` — Canonical runtime tokens.
- `collab-chat-identity-contract.md` — Proposed collab chat identity.
- `runtime-diagrams-v1.md` — Runtime topology diagrams.
- `system-overview.md` — Runtime components and topology.
- `flows.md` — Critical trigger-to-output flows.

**ADR directory:** `docs/architecture/adr/` — Architecture Decision Records (31+ ADRs).

**Continuity docs:** Multiple files covering the six-route operator phase — phase explainer, proof chain, handoff, hardening rerun, alignment audit.

**Proof artifacts:** Many date-stamped `2026-04-*-supported-path-proof.md` files provide live proof evidence for supported paths.

### Tests

`tests/` contains over 25 test directories covering virtually every backend subsystem. Key areas:
- `tests/continuity/` — Continuity operator regression guardrail (16 tests for the six-route surface).
- `tests/contracts/` — Contract validation tests.
- `tests/core/` — Core config, dependencies, coherence tests.
- `tests/command_bus/` — Command bus and tool execution.
- `tests/db/` — Database and migration tests.
- `tests/context/` — Context assembly tests.
- `tests/memoryos/` — Memory and retrieval tests.
- `tests/federation/` — Federation tests.
- `tests/identity/` — Identity tests.
- `tests/integration/` — Integration tests.

Frontend also has its own harnesses (Vitest, Playwright, Cypress) under `frontend/src/`.

### Config and Supported Profiles

`config/supported_profiles/` contains the profile manifests:
- `v1-local-core-web-mcp.yaml` — **The supported beta profile.** Defines what routes, providers, and capabilities are active in the supported local-first beta.
- `test-continuity.yaml` — Test-only profile that exposes the Continuity operator surface. Quarantined from supported beta.

### Collaborator Docs

`docs/collaborators/zac/` is Zac's dedicated RAG source directory with all the lenses, prompts, templates, and the report archive.

### Continuity-Related Work

The Continuity operator six-route surface is a significant recent workstream. Key files:
- `guardian/routes/continuity_operator.py` — Six FastAPI routes (write, packet readback, diagnostics, state readback, commit readback, link readback).
- `guardian/continuity/` — Write actions, persistence adapter, compiler.
- `tests/continuity/test_continuity_operator_six_route_surface.py` — 16-test regression guardrail.
- `docs/architecture/continuity-operator-*.md` — Phase explainer, handoff, proof chain, audit, rerun.
- `docs/architecture/adr/030-*.md` and `adr/031-*.md` — Continuity runtime and migration gates.

The Continuity surface is **test-only, quarantined, and explicitly not supported beta.** It must not be expanded without a new architecture-impact contract.

## Current Truth Anchors

Zac should remember these orientation principles:

1. `docs/architecture/00-current-state.md` is the release-truth anchor. If it conflicts with older docs, it wins.
2. Older docs may be useful context but are not automatically current truth. Check `00-current-state.md` before making claims.
3. Route presence is not release support. The supported beta profile (`v1-local-core-web-mcp.yaml`) defines what is actually supported.
4. The Continuity operator is test-only and quarantined. It is not supported beta behavior.
5. Zac should ask Resonant for constraints before touching any architecture-sensitive zone.
6. The supported install path is local Docker Compose, not the packaged desktop shell.
7. Docs-only contracts do not mean shipped runtime behavior.

## Safe Places To Explore First

These areas are lower-pressure for building familiarity:

- **Docs readability** — `docs/architecture/`, `docs/Ops/`, `docs/collaborators/zac/`. Look for stale wording, missing sections, orientation improvements.
- **Frontend UI observation** — `frontend/src/components/`, `frontend/src/features/`. Observe labels, empty states, visual flow. Low-risk polish candidates.
- **Dev-experience friction** — `Makefile`, `scripts/`, `docker-compose.yml`, READMEs. What is confusing to set up? What commands are missing docs?
- **Tests orientation** — `tests/`. What is tested? What is not? Where are the confidence gaps?
- **Setup and README clarity** — Top-level README, `CONTRIBUTING.md`, `SETUP_INSTRUCTIONS.md`. Are they current? Are they helpful?

## Sensitive Areas To Treat Carefully

These areas require proposal-before-change. Observations are welcome. Implementation without proposal is not.

- Continuity operator (test-only, quarantined).
- Export/restore behavior.
- Account identity and provenance.
- Chat runtime semantics.
- Memory and persona boundaries.
- Provider routing and catalog.
- Retrieval and context assembly.
- Auth and remote access.
- Queue, worker, and acceptance semantics.
- Supported profile activation (`v1-local-core-web-mcp.yaml`).
- Project Pulse (not yet implemented).
- Graph / Neo4j mount semantics.
- `guardian/core/` — most files in core are architecture-sensitive.

## What Seems Important

For Zac, the most important orientation takeaways:

1. **Codexify is large but well-organized.** The backend follows a clear pattern (routes → core → workers → DB), and the frontend follows a feature-based structure. You do not need to read everything. You need to know where to look.

2. **The architecture docs are the truth layer.** `docs/architecture/00-current-state.md` plus the ADRs and contracts tell you what is real, what is deferred, and what is unsupported. Start there for any architecture question.

3. **The Continuity operator is a significant recent workstream** that proves the architecture works in running code but remains deliberately quarantined from the supported beta. Understanding it gives context for the project's rhythm: contract → implementation → live proof → regression guardrail → documentation closure.

4. **Zac's RAG source directory is already well-provisioned.** The report-only lenses, prompts, templates, and archive give Zac a complete learning workflow without pressure to produce implementation.

5. **The supported beta is narrow and specific.** Only `v1-local-core-web-mcp` is supported. Only the local Docker Compose path is supported. Many docs describe future or planned work that is not yet shipped.

## What Is Confusing Or Unresolved

Honest unknowns from this light inspection:

- **Which routes are active in the supported beta profile?** The profile YAML defines this, but a deep route-by-route inspection was not done. The profile manifest at `config/supported_profiles/v1-local-core-web-mcp.yaml` is the canonical answer.
- **Which test suites run in CI vs locally only?** Some tests may require Docker Compose, Postgres, or Redis. The full test matrix was not inspected.
- **How much of the frontend component tree maps to currently active routes?** Some components may be scaffolding for deferred features. A deeper UI inspection would clarify this.
- **The relationship between `guardian/` and the compiled runtime in `backend/`** was not deeply traced. The compiled runtime uses PyInstaller and targets the packaged desktop path.
- **Several top-level directories (Codexify-Beta, codex_ralph_loop, codex_tasks, memory-bank, flows, etc.)** were not deeply inspected. Some may be archived, experimental, or operator-specific.

## What This Report Does Not Prove

- Does not prove runtime behavior — no services were run.
- Does not prove all modules are current — light filesystem inspection only.
- Does not prove release support — that is the role of `00-current-state.md` and supported profile manifests.
- Does not prove test coverage completeness — test directories were listed but not inspected for content.
- Does not prove architecture approval for future changes — every change needs its own task lane.
- Does not replace direct file inspection before work — this is an orientation map, not a substitute for reading the files you plan to change.

## Questions For Resonant

These are questions Zac might ask before deeper exploration:

1. Which area feels most valuable for Zac to explore first — UI feel, docs clarity, dev-experience, or test coverage?
2. Are there any modules Resonant considers especially sensitive right now beyond the documented sensitive zones?
3. Would a UI Naturalist report for the Persona Studio or app shell be useful, or should Zac start with a Doc Gardener pass on architecture docs?
4. Is there a specific pain point in the dev-experience (setup, test commands, linting) that Resonant knows about and would appreciate a report on?
5. Should the next report ladder up from this top-level map to a specific subsystem (e.g., `guardian/routes/` or `frontend/src/features/chat`)?

## Suggested Next Report

One of these, depending on what Resonant prefers:

- **UI Naturalist** — observe the frontend app shell and Persona Studio surfaces for labels, empty states, and visual feel.
- **Dev-Experience Mechanic** — document local setup flow, test commands, and friction points.
- **Doc Gardener** — inspect `docs/architecture/` for clarity, orientation value, and stale content.

This is not an assignment. It is a recommendation for where a next report would build useful familiarity.

## Bottom Line

Codexify should be approached by lenses, not all at once. The repo is large but well-organized: backend in `guardian/`, frontend in `frontend/src/`, truth in `docs/architecture/`, tests in `tests/`, and Zac's workflow in `docs/collaborators/zac/`.

Reports build familiarity. Proposals come later. Implementation comes only after constraints and the correct Codexify task lane. Zac's curiosity is the engine — this map just helps him navigate.
