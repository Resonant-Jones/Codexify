# Guardian Maturity Program

## Purpose

The Guardian Maturity Program is the organized execution scaffold for bringing Guardian's UI and operational experience into alignment with Codexify's current runtime architecture.

This is a **planning and governance scaffold**. It does not implement runtime behavior, create backend routes, add frontend components, or widen the release promise.

## Reading Order

1. [`00-program-charter.md`](./00-program-charter.md) — program purpose, scope, invariants, wave structure
2. [`01-campaign-map.md`](./01-campaign-map.md) — campaign enumeration (C00–C14) with status, dependencies, risk
3. [`02-domain-dependency-graph.md`](./02-domain-dependency-graph.md) — dependency graph and wave rationale
4. [`03-proof-gates.md`](./03-proof-gates.md) — proof categories and gate decision rules
5. [`04-release-boundary.md`](./04-release-boundary.md) — explicit denial of unsupported claims

## Release Truth Authority

[`docs/architecture/00-current-state.md`](../../architecture/00-current-state.md) remains the canonical short-form source of truth for release readiness, supported install path, active blockers, and what is and is not part of the present release promise.

This scaffold is planning structure only. It does not override `00-current-state.md`, ADRs, or live runtime evidence.

## Architecture-Impact Classification

This scaffold is classified as **architecture-impacting**. It does not alter runtime behavior, but it creates a governance surface for future architecture-impacting Guardian maturity work. It defines campaign boundaries, proof gates, release-boundary controls, and execution discipline for subsequent campaigns.

## Governing Documents

- [ADR-020: Guardian Mediated Coding Agent Execution Contract](../../architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md)
- [ADR-022: Guardian Intent Spine and Cross-Surface Control Plane](../../architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md)
- [Chat Runtime Contract](../../architecture/chat-runtime-contract.md)
- [Agent Tool Loop Contract](../../architecture/agent-tool-loop-contract.md)
- [Pi Invocation Boundary Contract](../../architecture/pi-invocation-boundary-contract.md)
- [Config and Ops](../../architecture/config-and-ops.md)
- [Agent Protocol Operations Index](../../architecture/agent-protocol-operations.md)
- [00-current-state.md](../../architecture/00-current-state.md)

## Campaign Folders

Each campaign has a folder under `campaigns/` containing:

- `charter.md` — campaign purpose, scope, dependencies, done-when
- `backlog.md` — task queue
- `proof-pack.md` — evidence collected and gate decisions
- `decision-log.md` — architectural and operational decisions

## Templates

Reusable templates live in [`templates/`](./templates/):

- [`campaign-charter-template.md`](./templates/campaign-charter-template.md)
- [`execution-slice-template.md`](./templates/execution-slice-template.md)
- [`proof-pack-template.md`](./templates/proof-pack-template.md)
- [`decision-log-template.md`](./templates/decision-log-template.md)
- [`task-index-template.md`](./templates/task-index-template.md)

## Wave Status

| Wave | Campaign | Status |
|------|----------|--------|
| 0 | C00 Truth Gate | closed |
| 0 | C11 API Route Audit | closed |
| 1 | C01 Command Center Verdict | closed |
| 1 | C02 Chat Runtime State | closed |
| 2 | C03 Coding Delegation Spine | closed |
| 2 | C05 Command Bus and Tool Turn Observability | closed |
| 2 | C06 Guardian Operator Workspace | closed |
| 3 | C04 Pi/Coder Invocation Boundary | closed |
| 3 | C07 Persona Studio | planned |
| 4 | C09 Pi/Coder Execution Authority | **selected** — see `wave-4-selection-after-c07.md` |
| 4 | C10 Recovery and Operator Repair | planned |
| 5 | C12 Operator Auth | planned |
| 5 | C13 SSE/Task-Event Reliability | planned |
| 5 | C14 Frontend State Management Audit | planned |

Waves 2 and 3 are complete. Wave 4 begins with C08, now closed. Next: C09 Pi/Coder Execution Authority.
| 4 | C07 Persona Studio | closed |

| Campaign | Status |
|----------|--------|
| 3 | C08 Whoosh'd Runtime Integration & Context Fidelity | closed |
