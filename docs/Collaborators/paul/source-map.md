# Paul Source Map

**For:** Paul's agent - first paths into Codexify docs and code
**Last updated:** 2026-06-29

## Always Read First

Before exploring any area, orient from:

- `docs/collaborators/paul/README.md`
- `docs/collaborators/paul/agent-rag-brief.md`
- `docs/collaborators/paul/agent-startup-prompt.md`
- `docs/architecture/00-current-state.md`

## The First Path

If Paul does not name a specific area, take this path first:

1. `docs/architecture/00-current-state.md` - current release truth.
2. `docs/architecture/README.md` - architecture KB entrypoint and doc map.
3. `docs/architecture/system-overview.md` - current runtime components and critical paths.
4. `docs/architecture/flows.md` - trigger-to-output flows and failure modes.
5. `docs/architecture/data-and-storage.md` - storage, invariants, and hotspots.
6. `docs/architecture/modules-and-ownership.md` - module boundaries and ownership.
7. `docs/architecture/config-and-ops.md` - environment, config, and operational commands.

That path gives Paul a stable first map before he starts drilling into a specific boundary.

## If Paul Is Studying Memory or Long-Lived Context

Use these files first:

- `docs/architecture/collab-chat-identity-contract.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/delegation-runtime.md`
- `guardian/cognition/identity_contract.py`
- `guardian/cognition/identity_resolution.py`
- `guardian/routes/imprint.py`
- `guardian/memoryos/retriever.py`
- `guardian/routes/chat.py`

Study what persists, what is derived, what is intentionally forgetful, and where source-of-truth lives. The BIOME/CORAL lens fits here: growth plus selective decay.

## If Paul Is Studying Runtime Boundaries

Use these files first:

- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/README.md`
- `guardian/core/dependencies.py`
- `guardian/core/ai_router.py`
- `guardian/routes/chat.py`
- `guardian/queue/redis_queue.py`
- `guardian/queue/task_events.py`

These paths show where policy, routing, and execution meet.

## Study-Only Prompts

When Paul wants learning rather than a proposal, use:

- `docs/collaborators/paul/report-request-prompts.md`
- `docs/collaborators/paul/report-output-templates.md`

## Proposal Follow-Up

If a report points to a real change, use:

- `docs/collaborators/paul/proposal-template.md`
- `docs/collaborators/paul/exploration-proposal-protocol.md`
- `docs/collaborators/paul/safe-and-sensitive-zones.md`

## Note

Do not read this map as a backlog. It is a decision tree for finding the first useful file, not a list of obligations.
