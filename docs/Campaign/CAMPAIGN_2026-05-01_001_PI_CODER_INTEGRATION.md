# CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION

## Campaign Metadata

- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: pi_coder_integration
- **Date**: 2026-05-01
- **Sequence**: 001
- **Owner**: resonant_jones
- **Risk**: MED
- **Depends on**: ADR-020 (Guardian Mediated Coding Agent Execution Contract)
- **Branch strategy**: Per-campaign branch

## Objective

Implement the Guardian → Pi → Codex Runner delegation pipeline per ADR-020:

1. Define the coding-task envelope schema
2. Create Pi tool wrapper for Codex Runner
3. Wire into existing Guardian queue infrastructure
4. Implement result ingestion back to thread

## Campaign Tasks

| Task ID | Description | Prerequisite |
|---------|-------------|--------------|
| TASK-2026-05-01-001 | Define CodingTaskEnvelope schema | None |
| TASK-2026-05-01-002 | Create Pi tool wrapper for Codex Runner | TASK-001 |
| TASK-2026-05-01-003 | Implement delegation queue integration | TASK-002 |
| TASK-2026-05-01-004 | Implement result ingestion and thread injection | TASK-003 |

## Discovery Reason

Integrating Pi SDK as Codexify's native coding agent per ADR-020 and the solo operator's vision for a three-layer system: Guardian (orchestration), Pi (execution), Codex Runner (campaign tool).

## Technical Context

- ADR-020 defines Guardian as identity/persistence owner
- Pi SDK provides the execution substrate
- Codex Runner provides campaign/audit infrastructure
- Existing queue: Redis-backed with task events via SSE
- Postgres: source of truth for durable state

## Files to Modify

- `guardian/agents/` - New coding agent integration layer
- `guardian/queue/` - Task definitions for delegation
- `guardian/routes/agent_orchestration.py` - Delegation endpoints
- `codex_runner/src/` - Pi tool wrapper
- `docs/architecture/` - ADR for integration contract