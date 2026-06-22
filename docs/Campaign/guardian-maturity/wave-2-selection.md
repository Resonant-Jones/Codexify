# Guardian Maturity Wave 2 Selection

## Decision

**C05: Command Bus and Tool Turn Observability** — `go`

## Selection Date

2026-06-19

## Inputs Read

- `docs/architecture/00-current-state.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/flows.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/Campaign/guardian-maturity/03-proof-gates.md`
- `docs/Campaign/guardian-maturity/04-release-boundary.md`
- `docs/Campaign/guardian-maturity/campaigns/C03-coding-delegation-spine/closeout.md`
- `docs/Campaign/guardian-maturity/campaigns/C03-coding-delegation-spine/proof-pack.md`

## Current Truth Boundary

Per `00-current-state.md` (2026-06-16): Codexify is in local-first beta hardening on `main`. Local Docker Compose remains the supported install path. The supported posture is local-only. Guardian delegation and Pi/Coder execution are not release-supported. This selection does not widen release claims.

## C03 Carry-Forward

### What C03 Made Newly True

- Work-order CRUD is runtime-available under internal-only posture.
- Command bus has 106 auto-discovered commands with manifest, invoke, and run readback.
- Work orders can link to command runs via `latest_run_id`.
- CommandRun results are durably stored and API-readable.
- Work orders can resolve their latest run via `GET .../latest-run`.
- Receipt persistence, creation, readback, list, and `latest_receipt_id` linkage are all proven.
- Operator receipt evidence is displayed read-only in the CodingWorkOrdersPanel.
- 52 backend + 16 frontend tests pass.

### What C03 Did Not Make True

- End-to-end Guardian delegation is not release-supported.
- Pi/Coder execution is not implemented.
- Autonomous coding-agent execution is not implemented.
- Artifact creation is not implemented.
- Tool-turn observability (toolTurnId, commandRunId, toolTurnState, loopStopReason) is not surfaced.

## Candidate: C05 Command Bus and Tool Turn Observability

### Purpose

Make bounded tool execution visible and auditable. Surface toolTurnId, commandRunId, toolTurnState, loopStopReason, and failure reasons in the operator UI. Prove that one-turn tool execution does not imply autonomous agent recursion.

### Why Now

C03 proved command bus manifest, invocation, run readback, and work-order linkage. The command bus infrastructure is proven but the operator cannot see tool-turn state. The Agent Tool Loop Contract defines canonical observability fields that are not surfaced. The tech-debt-and-risks doc lists `observability/operator-surface` as `operator burden` — this campaign directly addresses that.

### Dependency on C03

- CommandRun readback (C03-T008) provides the data source.
- Work-order latest-run bridge (C03-T009) provides the linkage path.
- Receipt evidence UI (C03-T015) provides the operator display pattern.

### Risks Reduced

- Operator cannot distinguish tool-turn completion from plain assistant response.
- Tool decision failure is invisible.
- Loop-stop reason is not inspectable.
- Command run history is not browsable.

### Risks Not Reduced

- Workspace unification remains fragmented.
- Pi/Coder execution is not addressed.
- Autonomous agent recursion is not addressed beyond the bounded one-turn contract.

### First Proof Surface Needed

Audit the current tool-turn state embedded in chat message `extra_meta` and command run records. Determine what is observable today, what is stored but not surfaced, and what requires backend event emission.

### First Recommended Task Name Only

**C05-T001: Tool-turn observability seam audit**

## Candidate: C06 Guardian Operator Workspace

### Purpose

Give the operator a unified working surface with scratchpad, shelf, inspector, and active task materials. Consolidate operator truth into one coherent view.

### Why Now

C03 receipt evidence display, C02 provider runtime state, and C01 HealthOverview verdict all provide operator truth fragments. A unified workspace would reduce the need to navigate between surfaces. The Workspace Surface Spec v1 already defines Shelf + Scratchpad + Inspector.

### Dependency on C03

- Receipt evidence display provides a workspace-relevant operator truth component.
- Work-order detail provides task materials for the workspace.

### Risks Reduced

- Operator must navigate multiple surfaces to understand system state.
- No persistent operator scratchpad for planning tasks.

### Risks Not Reduced

- Command/tool execution remains opaque.
- Tool-turn state is not visible.
- Autonomous execution ambiguity is not addressed.
- The system has more truth surfaces but no unified inspection lane.

### First Proof Surface Needed

Audit the existing WorkspacePane component against the Workspace Surface Spec v1. Determine what exists, what needs to be extended for operator use, and what backend API gaps exist.

### First Recommended Task Name Only

**C06-T001: Operator workspace gap audit**

## Comparison Matrix

| Criterion | C05 | C06 | Winner |
|-----------|-----|-----|--------|
| Reduces active release blocker or operator burden | Directly — tool-turn invisibility is operator burden | Indirectly — consolidates existing surfaces | **C05** |
| Depends directly on C03 receipt/result truth | Yes — CommandRun readback + work-order linkage | Partially — receipt display is a component | **C05** |
| Improves command/tool truth | Yes — primary focus | No — workspace consolidation | **C05** |
| Improves operator workspace truth | Partially — adds tool-turn visibility | Yes — primary focus | C06 |
| Lowers risk before autonomous delegation | Yes — proves tool-turn is bounded, observable, not autonomous | No — workspace is about UI, not execution boundaries | **C05** |
| Smallest next atomic task | Tool-turn seam audit (read-only) | Workspace gap audit (read-only) | Tie |
| Safest proof-first campaign start | Read-only audit of already-stored tool-turn data | Read-only audit of existing workspace component | Tie |
| Avoids release-claim expansion | Yes | Yes | Tie |
| Supports later Pi/Coder boundary work | Yes — tool-turn observability is prerequisite for understanding bounded execution | Indirectly — workspace could display Pi/Coder results later | **C05** |
| Supports Command Center maturity | Yes — tool-turn state is missing observability | Yes — workspace is a separate surface | **C05** |

## Selected Next Campaign

**C05: Command Bus and Tool Turn Observability**

C05 wins because it directly addresses the `observability/operator-surface` operator burden identified in the tech-debt-and-risks register. C03 invested heavily in command bus infrastructure (manifest, invoke, run readback, linkage) and the natural next step is making that infrastructure operator-visible. Tool-turn state is stored but not surfaced — the data exists, the observability gap is the blocker.

C06 (Guardian Operator Workspace) is deferred. It remains a valid campaign but is less dependent on C03 proof and less critical for safety before autonomous delegation planning. After C05 makes tool execution auditable, C06 can compose workspace surfaces from proven observability components rather than building a unified view on top of invisible execution state.

## First Next Task Name Only

**C05-T001: Tool-turn observability seam audit**

## Release Boundary

- No runtime behavior changed by this selection.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- `docs/architecture/00-current-state.md` remains authoritative.
- This is a planning-only selection artifact.

## Validation

```
git diff --check                    clean
python3 scripts/validate_docs.py     passed
```

No automated runtime tests apply — docs-only selection task.
