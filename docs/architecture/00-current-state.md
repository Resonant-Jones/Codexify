## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-11

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in local-stack beta hardening for the single-node workflow. The present operating focus is keeping the Docker Compose path, the core chat/RAG loop, the ingestion path, and the newer control surfaces stable enough to ship without widening the deployment promise.

## What changed recently

- Chat worker turn-lock and `turn_id` handling were hardened across failure paths.
- Local model handling was updated for current Qwen variants, and model identities were normalized.
- Assistant message audio artifact generation landed on the chat worker path.
- Approval rail, approval inbox, action center, persona settings, prompt inspector, and cron controls landed in the UI.
- ChatGPT import embedding diagnostics, degradation reporting, and retry support were added.
- Beta shell treatment and gate state for unfinished features were added.

## Current supported reality

- Supported install path is the local Docker Compose stack with `frontend`, `backend`, `db`, `redis`, and the required workers.
- The present release promise is local-first thread chat with persisted messages, worker-backed completions, RAG/context assembly, and document/media ingestion.
- Postgres is the system of record; Redis-backed workers are required for completion, embedding, and cron behavior.
- Frontend behavior assumes the backend API plus SSE/task-event surfaces are available.
- Current operator/control surfaces are beta-gated UI on top of the same runtime described in the rest of this KB.

## Not yet true / do not assume

- Do not assume non-Compose deployment is a supported path.
- Do not assume every provider shown in the catalog is runtime-executable.
- Do not assume `/tools` and the command bus are a fully unified surface.
- Do not assume federation or sync durability are part of the present release promise.
- Do not assume public multi-user internet exposure is the default supported mode.
- Do not assume older roadmap text defines this week's release scope.

## Active blockers

- Provider catalog and runtime support are not fully aligned.
- Tool execution still spans command bus behavior and legacy `/tools` behavior.
- Release health still depends on Redis plus worker availability, not just API boot.
- Document embedding failure recovery is weaker than the main happy path.
- Docs build is not locally runnable in the current repo state because MkDocs tooling/config is missing.

## This week’s priorities

1. Keep the Docker Compose local stack bootable and green.
2. Verify chat completion, turn-lock, and task-event behavior on current local model paths.
3. Keep document upload -> embed -> retrieval behavior observable and recoverable.
4. Reduce ambiguity between command bus behavior and legacy `/tools` behavior.
5. Keep provider selection and runtime capability reporting in sync.

## Release definition right now

- [ ] Local Docker Compose stack boots cleanly.
- [ ] A user can create a thread, send a message, and receive an assistant turn.
- [ ] Redis-backed chat worker and task events operate without stuck turns.
- [ ] Document upload reaches `ready` and becomes part of retrievable context.
- [ ] Current beta UI/control surfaces do not regress the core chat loop.
- [ ] No unsupported deployment or provider path is implied as part of the milestone.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
