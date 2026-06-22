# Wave 2 Next Campaign Selection After C05

## Gate Decision

**`go`** — Selected: **C06: Guardian Operator Workspace**

## Inputs Read

All 24 required pre-reads available. No missing inputs.

| # | File | Status |
|---|------|--------|
| 1 | `docs/architecture/00-current-state.md` | ✅ |
| 2 | `docs/architecture/README.md` | ✅ |
| 3 | `docs/architecture/agent-protocol-operations.md` | ✅ |
| 4 | `docs/architecture/agent-tool-loop-contract.md` | ✅ |
| 5 | `docs/architecture/flows.md` | ✅ |
| 6 | `docs/architecture/runtime-protocol-token-contract.md` | ✅ |
| 7 | `docs/architecture/chat-runtime-contract.md` | ✅ |
| 8 | `docs/architecture/pi-invocation-boundary-contract.md` | ✅ |
| 9 | `docs/architecture/config-and-ops.md` | ✅ |
| 10 | `docs/architecture/modules-and-ownership.md` | ✅ |
| 11 | `docs/architecture/data-and-storage.md` | ✅ |
| 12 | `docs/architecture/tech-debt-and-risks.md` | ✅ |
| 13 | `docs/architecture/ui-diagrams-v1.md` | ✅ |
| 14 | `docs/Campaign/guardian-maturity/wave-2-selection.md` | ✅ |
| 15 | `docs/Campaign/guardian-maturity/campaigns/C03-coding-delegation-spine/closeout.md` | ✅ |
| 16 | `docs/Campaign/guardian-maturity/campaigns/C05-command-bus-tool-turn-observability/closeout.md` | ✅ |
| 17 | `docs/Campaign/guardian-maturity/campaigns/C05/.../proof-pack.md` | ✅ |
| 18 | `docs/Campaign/guardian-maturity/campaigns/C05/.../decision-log.md` | ✅ |
| 19 | `docs/Campaign/guardian-maturity/campaigns/C05/.../backlog.md` | ✅ |
| 20 | `docs/Campaign/guardian-maturity/campaigns/C05/.../seam-audit.md` | ✅ |
| 21 | `docs/Campaign/guardian-maturity/campaigns/C05/.../tool-turn-read-model-contract.md` | ✅ |
| 22 | `guardian/command_bus/tool_turn_observability.py` | ✅ |
| 23 | `guardian/routes/command_bus.py` | ✅ |
| 24 | `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx` | ✅ |

## Current Truth After C05

### C03: Coding Delegation Spine — closed

- Work-order CRUD under internal-only posture.
- Command bus: 106 auto-discovered commands, manifest, invoke, run readback.
- Work-order to command-run linkage via `latest_run_id` (fail-closed).
- Durable CommandRun readback by `run_id`.
- Work-order latest-run bridge via `GET .../latest-run`.
- Receipt persistence, creation, readback, list, and `latest_receipt_id` fail-closed linkage.
- Operator receipt evidence UI in `CodingWorkOrdersPanel` (truth-labeled, read-only).
- 52 backend + 16 frontend tests passing.

### C05: Command Bus and Tool Turn Observability — closed

- Seam audit: 6 canonical observability fields durably persisted in `chat_messages.extra_meta`.
- Read model contract: 15-field safe read model with source priority and redaction rules.
- Pure backend helper: `ToolTurnObservabilityReadModel` + `build_tool_turn_observability_read_model()`.
- Readback route: `GET /api/guardian/commands/tool-turns/{message_id}/observability`.
- Command Center UI: read-only `ToolTurnObservability` component in `CodingWorkOrdersPanel`.
- Redaction enforced and tested (no raw args, secrets, prompts, extra_meta, result_json, stack traces).
- No mutation controls in operator UI.
- Truth-labeling: bounded tool-turn evidence does not prove autonomous delegation, Pi/Coder execution, artifact creation, or work-order completion.
- 108 backend + 142 frontend tests passing.

### What Remains Deferred

- **Receipt linkage** — C03 receipt store not wired in command bus routes; readback returns empty receipt fields.
- **C06 unified operator workspace** — was deferred in prior wave-2 selection.
- **Autonomous delegation** — not release-supported.
- **Pi/Coder execution** — not implemented.

### Release Boundary Intact

- No runtime behavior changed beyond read-only observability.
- No command invocation, chat completion, persistence, or token semantics changed.
- No release claim widened.

## Candidate Campaigns Considered

### C06: Guardian Operator Workspace

- **Rationale**: C03 and C05 have delivered four operator truth components that currently live in separate panels: receipt evidence, tool-turn observability, work-order status, and HealthOverview verdict. The operator must navigate between multiple surfaces. C06 would unify them into a coherent workspace (Scratchpad, Shelf, Inspector) per the Workspace Surface Spec v1.
- **Blockers removed by C03/C05**:
  - C03 provides receipt evidence as a workspace-relevant component.
  - C05 provides tool-turn observability as a workspace-relevant component.
  - C01 provides HealthOverview verdict.
  - C02 provides provider/runtime state banners.
- **Remaining prerequisites**: None. All operator truth components exist. C06 composes them.
- **Risk**: LOW — frontend/UX only. No backend route, schema, or provider changes per the campaign map.
- **Why selected**: C06 is the final Wave 2 campaign. C03 and C05 delivered the components; C06 unifies them. Without C06, the operator has scattered truth surfaces. With C06, the operator has a single inspection lane.

### Receipt Linkage Follow-Through

- **Rationale**: C05 deferred receipt linkage because the C03 receipt store is not wired in command bus routes. Wiring it would enrich the tool-turn readback with receipt data.
- **Blockers removed by C03/C05**: C03 has the receipt store; C05 has the readback route. Both exist.
- **Remaining prerequisites**: Backend wiring between `guardian/routes/command_bus.py` and the C03 receipt store.
- **Risk**: MED — involves backend route changes.
- **Why deferred**: Receipt linkage is a follow-through on a deferred C05 limitation, not a full campaign. It is a natural seam to address within C06 (Inspector enrichment) or within a future C09 execution ledger campaign. It does not block C06 workspace unification.

### Command Center Observability Hardening

- **Rationale**: C05 added tool-turn observability, but the health surfaces (provider state, queue depth, worker heartbeat) have partial coverage. Hardening would deepen command-center truth.
- **Blockers removed by C03/C05**: Command Center shell, HealthOverview, and CodingWorkOrdersPanel exist.
- **Remaining prerequisites**: Backend health route extensions, queue depth metrics.
- **Risk**: MED — involves backend route and metric changes.
- **Why deferred**: Observability hardening is a natural candidate for a later campaign (C10 recovery/repair or a standalone observability campaign). C06 workspace unification is the sharper Wave 2 priority.

### Graph/Chronicle Optimization

- **Rationale**: Not present in the current Guardian Maturity campaign map or backlog. The map lists C01–C14; no graph or chronicle campaign exists.
- **Why deferred**: Not a defined campaign. If surface becomes needed, it would require charter creation.

## Selection Criteria

| Criterion | Weight | C06 | Receipt Linkage | Cmd Center Harden |
|-----------|--------|-----|-----------------|-------------------|
| Operator value | High | **Unifies 4 surfaces** | Enriches 1 field | Deepens 1 surface |
| Dependency readiness | High | **All components exist** | Store + route exist | Partial backend needed |
| Architecture risk | High | **LOW** (frontend only) | MED (backend) | MED (backend) |
| Release-boundary safety | Critical | **Safe** (UI only) | Safe | Safe |
| Completes Wave 2 | High | **Yes** (final campaign) | No (not a campaign) | No |
| Proof surface availability | Medium | **WorkspacePane exists** | C03 store exists | Health routes exist |
| Dangerous to forget | Medium | Operator surfaces fragment | Minor | Minor |
| Unlocked by C03/C05 | Critical | **Yes** (all components) | Yes | Partially |

## Selected Campaign

**C06: Guardian Operator Workspace**

C06 is selected because:

1. **It completes Wave 2.** C03 and C05 are closed. C06 is the final Wave 2 campaign. After C06, the Guardian Maturity program transitions to Wave 3 (Pi/Coder invocation boundary, Persona Studio, Whoosh'd runtime).

2. **All operator truth components exist.** C03 provided receipt evidence. C05 provided tool-turn observability. C01 provided HealthOverview. C02 provided runtime state banners. C06 unifies them.

3. **C03 and C05 make it safe to proceed.** The operator truth components are proven — not speculative. C06 composes proven surfaces rather than inventing new backend capability.

4. **Low risk, high value.** Frontend/UX only per the campaign map. No backend route, schema, provider, or queue changes. The WorkspacePane component already exists and the Workspace Surface Spec v1 defines the target.

5. **C06 was correctly deferred from the prior wave-2 selection.** The prior selection deferred C06 because tool-turn state was invisible. C05 made tool-turn state visible. C06 is now the correct next step.

### Out of Scope for C06

- Receipt linkage wiring (deferred C05 follow-through, belongs in a later campaign or C06 extension).
- Autonomous delegation.
- Pi/Coder execution.
- Command invocation controls.
- Artifact creation.
- New backend routes or persistence schema.
- Release claim widening.

## Deferred Campaigns

| Campaign | Reason Deferred |
|----------|-----------------|
| Receipt linkage follow-through | Deferred C05 limitation; belongs in C09 execution ledger or C06 extension. Does not block workspace unification. |
| Command Center observability hardening | Partial backend prerequisites; natural candidate for C10 recovery/repair or standalone observability campaign. |
| Graph/Chronicle optimization | Not a defined campaign in the Guardian Maturity map. |

## Release Boundary

- **No runtime behavior changed** — this is a docs-only campaign selection.
- **No command invocation semantics changed.**
- **No chat completion semantics changed.**
- **No persistence schema changed.**
- **No protocol tokens added or renamed.**
- **No release claim widened.**
- **No autonomous delegation claim added.**
- **No Pi/Coder execution claim added.**
- **No recursive tool-loop claim added.**
- **No artifact creation claim added.**
- **No receipt creation claim added.**
- **No work-order completion claim added.**
- `docs/architecture/00-current-state.md` remains authoritative.

## Recommended First Task

**C06-T001: Guardian Operator Workspace seam audit**

## Validation

```
git diff --check                    clean
python3 scripts/validate_docs.py     passed
```

No automated runtime tests apply — docs-only campaign selection task.

## Final Gate

- **Decision**: `go`
- **Selected campaign**: C06: Guardian Operator Workspace
- **Next task by name only**: `C06-T001: Guardian Operator Workspace seam audit`
