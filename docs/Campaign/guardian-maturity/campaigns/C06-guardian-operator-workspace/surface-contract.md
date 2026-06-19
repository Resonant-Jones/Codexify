# C06 Surface Contract: Guardian Operator Workspace

## Gate Decision

**`go`** — C06-T003 may proceed by name only.

## Scope

This contract defines the future Guardian Operator Workspace surface. It does **not** implement the workspace. The workspace is a read-only composition surface unless a later architecture-impact task explicitly changes that. This contract translates the C06-T001 seam audit into a bounded, read-only workspace composition plan that is safe to implement later.

## Inputs Read

All 34 required pre-reads available. No missing inputs.

## Current Truth After C06-T001

- **C03 Coding Delegation Spine** — closed. Work-order CRUD, command bus manifest/invoke/run-readback, work-order-to-command-run linkage, receipt persistence/readback/linkage, operator receipt evidence UI.
- **C05 Command Bus and Tool Turn Observability** — closed. Seam audit, read model contract, backend helper, backend readback route, Command Center tool-turn UI.
- **C06 seam audit** — accepted. 8 operator surfaces, 5 backend truth surfaces, 10 composition candidates, 8 gaps.
- **Current Command Center surfaces** exist across 4+ separate lenses (agent-command, runtime-health, observability, heartbeat).
- **Backend truth surfaces** exist for command runs, tool-turn observability, receipts, health status.
- **Receipt linkage** remains deferred — C03 receipt store not wired in command bus routes.
- **C06 workspace** not yet implemented.
- **Release boundary** intact.

## Workspace Purpose

The Guardian Operator Workspace answers these questions for the operator:

| Question | Answer Source |
|----------|--------------|
| What is Guardian doing? | Work-order status, health verdict |
| What work exists? | Work-order list from C03 |
| What bounded tool-turn evidence exists? | C05 tool-turn observability readback |
| What command-run evidence exists? | C03 command-run readback |
| What receipt evidence exists? | C03 receipt readback |
| What runtime/health status exists? | C02 provider state + C01 HealthOverview |
| What is unavailable or deferred? | Gaps card (receipt linkage, assistant_message_id) |
| What must not be inferred? | Truth-labeling copy on every evidence card |

## Surface Model

### Top-Level Zones

| Zone | Purpose | Operator Question | Source of Truth | Required Fields |
|------|---------|-------------------|-----------------|-----------------|
| Workspace Header | Identify workspace, show refresh, show last-updated | "Is this the workspace?" | Shell + health timestamp | Title, lastCheckedAt, refresh button |
| Work-Order Status Card | Display current work orders | "What work exists?" | `GET /api/coding/work-orders` | Work order ID, status, created_at, latest receipt summary |
| Command-Run Evidence Card | Display command run results linked to selected work order | "What command ran?" | `GET /api/coding/work-orders/{id}/latest-run` → `GET /api/guardian/commands/runs/{run_id}` | Run ID, command ID, status, result summary, error summary, created_at |
| Tool-Turn Observability Card | Display bounded tool-turn evidence | "What tool-turn evidence exists?" | `GET /api/guardian/commands/tool-turns/{message_id}/observability` | Tool-turn ID, state, loop stop reason, command run ID, evidence durability, truth-labeling |
| Receipt Evidence Card | Display receipt evidence for selected work order | "What receipt evidence backs this?" | `GET /api/coding/work-orders/{id}/receipts/{receipt_id}` | Receipt ID, kind, command ID, status, summary, hash, schema version, truth-labeling |
| Runtime/Health Card | Display provider/runtime health status | "Can I run?" | C02 provider state + C01 health verdict | Provider state, runtime availability, health items summary, last checked |
| Gaps and Unavailable Card | Surface known gaps and deferred evidence | "What can't I see yet?" | C06 seam audit gaps | Receipt linkage deferred, assistant_message_id unavailable (when absent), EventConsole not composed |
| Safety Boundary Note | Remind operator of read-only posture | "Is this safe to look at?" | C05 contract | Read-only, no mutation controls, bounded evidence |

### Zone Readiness

| Zone | Backing Truth Exists | Frontend Surface Exists | Implementation Readiness |
|------|---------------------|------------------------|-------------------------|
| Workspace Header | ✅ (health timestamp) | ✅ (CommandCenterShell) | ⚠️ Needs workspace lens |
| Work-Order Status | ✅ C03 | ✅ CodingWorkOrdersPanel | ✅ Safe to compose |
| Command-Run Evidence | ✅ C03 | ❌ | ✅ Backend exists, needs UI card |
| Tool-Turn Observability | ✅ C05 | ✅ CodingWorkOrdersPanel | ⚠️ Conditional on assistant_message_id |
| Receipt Evidence | ✅ C03 | ✅ CodingWorkOrdersPanel | ✅ Safe to compose |
| Runtime/Health | ✅ C02/C01 | ✅ HealthOverview | ✅ Safe to compose |
| Gaps and Unavailable | ✅ C06-T001 | ❌ | ✅ Docs-only content |
| Safety Boundary Note | ✅ C05 | ❌ | ✅ Docs-only content |

## Source-of-Truth Mapping

| Zone | Frontend Source | Backend Route/Helper | Durable Store | Proof Artifact | Known Limitation |
|------|----------------|---------------------|---------------|----------------|------------------|
| Workspace Header | CommandCenterShell | N/A | N/A | C06-T001 | No workspace lens exists |
| Work-Order Status | CodingWorkOrdersPanel | `GET /api/coding/work-orders` | `coding_work_orders` | C03-T001–T006 | Filter is basic |
| Command-Run Evidence | (new) | `GET /api/coding/work-orders/{id}/latest-run` + `GET /api/guardian/commands/runs/{run_id}` | `command_runs` | C03-T008–T009 | Not surfaced in any UI panel |
| Tool-Turn Observability | CodingWorkOrdersPanel (ToolTurnObservability) | `GET /api/guardian/commands/tool-turns/{message_id}/observability` | `chat_messages.extra_meta` | C05-T001–T005 | Gated on assistant_message_id |
| Receipt Evidence | CodingWorkOrdersPanel (ReceiptEvidence) | `GET /api/coding/work-orders/{id}/receipts/{receipt_id}` | `work_order_result_receipts` | C03-T012–T015 | Receipt linkage deferred |
| Runtime/Health | HealthOverview | HealthService | Provider state | C01, C02 | None |
| Gaps and Unavailable | (new) | N/A | C06 seam audit | C06-T001 | Static content |
| Safety Boundary Note | (new) | N/A | C05 contract | C05-T002/T005 | Static content |

## Read-Only Interaction Rules

### Allowed Interactions

- Navigate between workspace sections (scroll, tab, expand/collapse cards).
- Refresh read-only evidence (refetch from backend routes).
- Copy stable public IDs (work order ID, receipt ID, run ID) — only if already surfaced safely by existing routes.
- Select a work order to focus on it.

### Prohibited Interactions

- Dispatch
- Execute
- Retry
- Replay
- Approve
- Complete
- Create artifact
- Create receipt
- Mutate work-order state
- Mutate command-run state
- Invoke Pi/Coder
- Invoke recursive tool loops
- Modify backend state through any workspace interaction

## Evidence State Model

| State | User-Facing Label | When to Use | What Not to Imply |
|-------|-------------------|-------------|-------------------|
| Available | Field value rendered normally | Truth data returned from backend | Does not prove completion, execution, or delegation |
| Unavailable | `Unavailable` + reason | Missing data (e.g., no assistant_message_id) | Does not mean backend is broken |
| Deferred | `Not yet available` + what's deferred | Known gap (e.g., receipt linkage) | Does not mean it will never be available |
| Loading | Spinner or skeleton | In-flight fetch | Does not mean system is stuck |
| Error | `Unable to load` + safe reason | Fetch failed | Does not expose raw backend error payload or stack trace |
| Stale | `Last updated: {timestamp}` | Data refreshable but not live (only where timestamp exists) | Does not mean system is unhealthy |
| Diagnostic-Only | `Raw event stream — not workspace evidence` | EventConsole only | Does not meet durable evidence standard |

## Redaction and Safety Rules

The workspace must never expose:

| Forbidden Content | Enforced By |
|-------------------|-------------|
| Raw args | C05-T002/C05-T003 |
| Secrets | C05-T002/C05-T003 |
| Credentials | C05-T002/C05-T003 |
| Hidden prompts | C05-T002 |
| System prompts | C05-T002 |
| Raw `extra_meta` | C05-T002/C05-T003 |
| Raw `result_json` | C05-T002/C05-T003 |
| Stack traces | C05-T002/C05-T005 |
| Unredacted payloads | C05-T002 |
| Local surrogate IDs when stable IDs exist | C05-T002 |

All existing C05 redaction proof must remain valid after workspace composition. No new data sources may bypass these boundaries.

## Truth Labeling Rules

Every evidence card must include truth-labeling copy that distinguishes bounded evidence from unsupported claims:

| Evidence Type | Required Truth Label |
|---------------|---------------------|
| Tool-turn observability | `Read-only bounded tool-turn evidence. This does not prove autonomous delegation, Pi/Coder execution, artifact creation, or work-order completion.` |
| Command-run evidence | `Read-only CommandRun evidence. This does not prove autonomous delegation, artifact creation, or work-order completion.` |
| Receipt evidence | `Receipt evidence records observed results. This does not prove completion, artifact creation, coding-agent execution, or autonomous delegation.` |
| Work-order status | `Work-order status from the coding delegation spine. No autonomous execution, deployment, or artifact delivery has occurred.` |
| Runtime/health status | `Provider and runtime health snapshot. Does not guarantee request completion, model availability, or end-to-end execution.` |

## Unavailable and Deferred States

| Deferred Item | State Label | Source |
|---------------|-------------|--------|
| Receipt linkage | `Receipt enrichment not yet available` | C05 deferred — C03 receipt store not wired in command bus routes |
| Assistant message ID | `No assistant message ID available for this work order` | Tool-turn observability gated on assistant_message_id |
| Unified workspace | `Workspace composition in progress` | C06 not yet implemented |
| EventConsole | `Raw event stream — not workspace evidence` | Redaction review not complete |
| Command manifest | `106 discoverable commands — browse not yet available` | No manifest UI panel |
| Latest-run bridge | `Latest command run for this work order — browse not yet available` | Backend route exists, no UI panel |

## Non-Goals

- No autonomous delegation.
- No Pi/Coder execution.
- No recursive tool loops.
- No artifact creation.
- No receipt creation.
- No work-order completion semantics.
- No command invocation controls.
- No runtime behavior changes.
- No backend implementation in this task.
- No frontend implementation in this task.

## C06 Implementation Readiness

The following is safe to implement next (C06-T003+):

1. **First implementation must be read-only** — compose existing safe surfaces only.
2. **First implementation must not create new backend truth** — all data sources already exist.
3. **First implementation must not alter command/work-order semantics** — no mutation controls.
4. **Missing evidence must render as unavailable or deferred** — no fabricated data.
5. **Gaps card must be visible** — operator awareness of limitations is required.
6. **Safety boundary note must be visible** — read-only posture must be explicit.
7. **Implementation sequence**:
   - Scaffold workspace lens and layout (C06-T003)
   - Compose existing safe surfaces one at a time (C06-T004–T007)
   - Add workspace integration tests (C06-T008)
   - Close with proof and validation (C06-T009)

## Recommended C06 Backlog

1. `C06-T001: Guardian Operator Workspace seam audit` ← complete
2. `C06-T002: Define Guardian Operator Workspace surface contract` ← THIS TASK
3. `C06-T003: Add Guardian Operator Workspace lens scaffold`
4. `C06-T004: Compose work-order status panel`
5. `C06-T005: Compose receipt evidence panel`
6. `C06-T006: Compose tool-turn observability panel`
7. `C06-T007: Compose runtime/health and heartbeat panels`
8. `C06-T008: Workspace integration tests`
9. `C06-T009: Operator workspace proof closeout`

## Release Boundary

- No runtime behavior changed.
- No command invocation semantics changed.
- No chat completion semantics changed.
- No persistence schema changed.
- No protocol tokens added or renamed.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- No recursive tool-loop claim added.
- No artifact creation claim added.
- No receipt creation claim added.
- No work-order completion claim added.

## Validation

```
git diff --check                    clean
python3 scripts/validate_docs.py     passed
```

No automated runtime tests apply — docs-only surface contract.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C06-T003: Add Guardian Operator Workspace lens scaffold`
