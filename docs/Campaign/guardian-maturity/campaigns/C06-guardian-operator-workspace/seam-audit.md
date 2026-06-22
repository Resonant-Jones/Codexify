# C06 Seam Audit: Guardian Operator Workspace

## Gate Decision

**`go`** — C06-T002 may proceed by name only.

## Scope

This is an audit of the current Guardian Operator Workspace seams. It does **not** implement the workspace. It inspects what operator truth surfaces exist after C03 and C05, classifies their readiness for composition, records gaps, and names the next task.

## Inputs Read

All 34 required pre-reads available. No missing inputs.

| # | File | Status |
|---|------|--------|
| 1–15 | `docs/architecture/*.md` | ✅ |
| 16–17 | `docs/Campaign/guardian-maturity/wave-2-*.md` | ✅ |
| 18–23 | `docs/Campaign/guardian-maturity/campaigns/C0[35]/*.md` | ✅ |
| 24–31 | `frontend/src/features/commandCenter/components/*.tsx` (8 files) | ✅ |
| 32–33 | `guardian/routes/command_bus.py`, `guardian/command_bus/tool_turn_observability.py` | ✅ |
| 34 | `guardian/db/models.py` | ✅ |

## Current Truth After C03 and C05

- **C03 Coding Delegation Spine** — closed. Work-order CRUD, command bus manifest/invoke/run-readback, work-order-to-command-run linkage, receipt persistence/readback/linkage, operator receipt evidence UI.
- **C05 Command Bus and Tool Turn Observability** — closed. Seam audit, read model contract, backend helper, backend readback route, Command Center tool-turn UI.
- **Command Center** has read-only work-order and tool-turn observability pieces in `CodingWorkOrdersPanel`.
- **Backend readback route** (`GET /api/guardian/commands/tool-turns/{message_id}/observability`) exists and is read-only.
- **Frontend surface** `CodingWorkOrdersPanel` is read-only.
- **Receipt linkage** remains deferred — C03 receipt store not wired in command bus routes.
- **No release claim widened.**

## Existing Operator Surfaces

### 1. CommandCenterShell (`frontend/src/features/commandCenter/components/CommandCenterShell.tsx`)

- **Current purpose**: Host shell with utility rail, lens switching, and bottom drawer.
- **Data sources**: Props from parent (healthItems, runs, consoleRows, connection state, etc.).
- **Operator question answered**: "Where do I inspect Guardian state?"
- **Read-only**: Yes. Lens switching is navigation, not mutation.
- **Mutation controls**: None.
- **Redaction/safety**: Imports no secret surfaces. Shell is a layout container.
- **Gaps for C06**: Shell has 8 lenses. No unified workspace lens exists. Operator must switch between `agent-command`, `runtime-health`, `observability`, and `event-console` to assemble a unified picture.

### 2. CodingWorkOrdersPanel (`frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx`)

- **Current purpose**: Display work orders, receipt evidence, and tool-turn observability.
- **Data sources**: `GET /api/coding/work-orders`, `GET /api/coding/work-orders/{id}/receipts/{receipt_id}`, `GET /api/guardian/commands/tool-turns/{message_id}/observability`.
- **Operator questions answered**:
  - What work orders exist?
  - What receipt evidence backs a given work order?
  - What bounded tool-turn evidence exists for an assistant message?
- **Read-only**: Yes.
- **Mutation controls**: None (verified in C05-T005).
- **Redaction/safety**: Enforced — no raw args, secrets, prompts, extra_meta, result_json, stack traces.
- **Truth-labeling**: Present — bounded tool-turn evidence does not prove autonomous delegation, Pi/Coder execution, artifact creation, or work-order completion.
- **Gaps for C06**: Tool-turn fetch gated on `assistant_message_id` (not always available). Receipt linkage deferred. Work-order filter/search is basic. Panel is a single scrollable region — not composable into a workspace layout.

### 3. HealthOverview (`frontend/src/features/commandCenter/components/HealthOverview.tsx`)

- **Current purpose**: Display health verdict summary and individual health item status.
- **Data sources**: `healthItems` prop from parent.
- **Operator question answered**: "Can I run?"
- **Read-only**: Yes.
- **Mutation controls**: Refresh button only.
- **Redaction/safety**: No sensitive fields surfaced.
- **Gaps for C06**: Health items are displayed as a flat list. No drill-down to individual item evidence. No workspace integration — health lives in a separate lens.

### 4. HeartbeatStatusPanel (`frontend/src/features/commandCenter/HeartbeatStatusPanel.tsx`)

- **Current purpose**: Display worker heartbeat pipeline status.
- **Data sources**: Heartbeat status prop.
- **Operator question answered**: "Are workers alive?"
- **Read-only**: Yes.
- **Mutation controls**: None observed.
- **Redaction/safety**: No sensitive fields surfaced.
- **Gaps for C06**: Separate lens. Not integrated into a unified workspace.

### 5. TraceWorkbench (`frontend/src/features/commandCenter/components/TraceWorkbench.tsx`)

- **Current purpose**: Display retrieval posture traces and run traces with filtering.
- **Data sources**: `runs` prop, `traceFilters` prop.
- **Operator question answered**: "What happened during retrieval and trace execution?"
- **Read-only**: Yes.
- **Mutation controls**: Filter controls only.
- **Redaction/safety**: No sensitive fields surfaced in public trace view.
- **Gaps for C06**: Separate lens. Trace data is not linked to work orders or tool-turn evidence.

### 6. EventConsole (`frontend/src/features/commandCenter/components/EventConsole.tsx`)

- **Current purpose**: Display raw event stream.
- **Data sources**: `consoleRows` prop.
- **Operator question answered**: "What events are flowing?"
- **Read-only**: Yes.
- **Mutation controls**: None.
- **Redaction/safety**: Raw events may contain sensitive data — no explicit redaction layer observed.
- **Gaps for C06**: Raw event surface. Not suitable for default workspace composition without redaction review.

### 7. CommandCenterUtilityRail (`frontend/src/features/commandCenter/components/CommandCenterUtilityRail.tsx`)

- **Current purpose**: Lens navigation sidebar.
- **Data sources**: Local `activeLens` state.
- **Operator question answered**: "Which lens am I viewing?"
- **Read-only**: Yes — navigation only.
- **Mutation controls**: None.
- **Gaps for C06**: No workspace lens entry. Adding one is trivial (add to `CommandCenterLensId` union).

### 8. CommandCenterBottomDrawer (`frontend/src/features/commandCenter/components/CommandCenterBottomDrawer.tsx`)

- **Current purpose**: Drawer with 4 tabs: Terminal, Logs, Receipts, Problems.
- **Data sources**: Props for drawer content.
- **Operator question answered**: "Where are terminal/logs/receipts/problems?"
- **Read-only**: Yes.
- **Mutation controls**: None in drawer shell.
- **Redaction/safety**: Tab labels are safe. Content is rendered by tab-specific components.
- **Gaps for C06**: Receipts tab is a placeholder — no C03 receipt list wired. Terminal/Logs/Problems are also placeholders. Drawer could host workspace-adjacent content.

## Existing Backend Truth Surfaces

### 1. Command Bus Run Readback (`GET /api/guardian/commands/runs/{run_id}`)

- **File**: `guardian/routes/command_bus.py` (line 252)
- **Source of durable truth**: `command_runs` table (`CommandRun` model).
- **Operator question answered**: "What happened in this command run?"
- **Redaction boundaries**: Run-level fields only — no raw args, no secrets, no prompts.
- **Gaps for C06**: Readback does not include receipt linkage. No cross-reference to work orders in route response.

### 2. Command Bus Manifest (`GET /api/guardian/commands/manifest`)

- **File**: `guardian/routes/command_bus.py` (line 73)
- **Source of durable truth**: Auto-discovered command registry (106 commands at C03-T005).
- **Operator question answered**: "What commands can I inspect?"
- **Redaction boundaries**: Command metadata only — no invocation paths, no args.
- **Gaps for C06**: Manifest is discoverable but not surfaced in any operator UI panel.

### 3. Tool-Turn Observability Readback (`GET /api/guardian/commands/tool-turns/{message_id}/observability`)

- **File**: `guardian/routes/command_bus.py` (line 270)
- **Source of durable truth**: `chat_messages.extra_meta` + `command_runs` table.
- **Operator question answered**: "What bounded tool-turn evidence exists for this assistant message?"
- **Redaction boundaries**: Full — no raw args, secrets, prompts, extra_meta, result_json, stack traces, unredacted payloads, local surrogate IDs (C05-T002/T003/T004/T005 proven).
- **Gaps for C06**: Receipt linkage deferred (returns empty receipt fields). Gated on `assistant_message_id` availability.

### 4. Work-Order Latest-Run Bridge (`GET /api/coding/work-orders/{id}/latest-run`)

- **File**: `guardian/routes/coding_work_orders.py`
- **Source of durable truth**: `coding_work_orders.latest_run_id` → `command_runs` table.
- **Operator question answered**: "What is the latest command run for this work order?"
- **Redaction boundaries**: Same as command run readback.
- **Gaps for C06**: Bridge not surfaced in any operator UI panel. Work-order list in CodingWorkOrdersPanel does not show linked runs.

### 5. Receipt Readback (`GET /api/coding/work-orders/{id}/receipts/{receipt_id}`, `GET /api/coding/work-orders/{id}/receipts`)

- **File**: `guardian/routes/coding_work_orders.py`
- **Source of durable truth**: `work_order_result_receipts` table.
- **Operator question answered**: "What receipt evidence exists for this work order?"
- **Redaction boundaries**: Receipt-level fields — receipt_kind, receipt_hash, command_id, command_status, result_summary, error_summary, schema_version.
- **Gaps for C06**: Receipt readback surfaced in CodingWorkOrdersPanel receipt evidence section, but not in bottom drawer Receipts tab.

## Workspace Composition Candidates

| Component | Backing Truth Exists | Frontend Surface Exists | Safe to Compose Now | Risk | Deferrals |
|-----------|---------------------|------------------------|---------------------|------|-----------|
| Work-order status | ✅ C03 | ✅ CodingWorkOrdersPanel | ✅ Yes | LOW | None |
| Command-run evidence | ✅ C03 | ❌ Not in UI | ✅ Yes | LOW | Needs UI card |
| Tool-turn observability | ✅ C05 | ✅ CodingWorkOrdersPanel | ⚠️ Conditional | MED | Gated on `assistant_message_id` |
| Receipt evidence | ✅ C03 | ✅ CodingWorkOrdersPanel | ✅ Yes | LOW | Receipt linkage deferred |
| Runtime/provider status | ✅ C02 | ✅ HealthOverview | ✅ Yes | LOW | None |
| Worker heartbeat | ✅ HeartbeatStatusPanel | ✅ | ✅ Yes | LOW | None |
| Event console | ✅ Event stream | ✅ EventConsole | ❌ No | HIGH | Raw events — redaction review needed |
| Command manifest | ✅ C03 | ❌ Not in UI | ✅ Yes | LOW | Needs UI card |
| Retrieval posture | ✅ TraceWorkbench | ✅ | ✅ Yes | MED | Posture data may be large |
| Bottom drawer receipts | ✅ C03 | ⚠️ Placeholder | ⚠️ Partial | LOW | Wired in CodingWorkOrdersPanel, not in drawer |

### Key Finding

Four operator truth surfaces are **scattered across separate lenses**: work-order/receipt/tool-turn (agent-command lens), health (runtime-health lens), heartbeat (heartbeat lens), and trace/retrieval (observability lens). No unified workspace lens exists. The operator must manually switch between lenses to assemble a complete picture.

### Composition Readiness

C06 can safely compose the following into a unified workspace **now**:
- Work-order status (C03)
- Receipt evidence (C03, already in CodingWorkOrdersPanel)
- Tool-turn observability (C05, conditional on assistant_message_id)
- Runtime/provider health (C02, already in HealthOverview)
- Heartbeat status (heartbeat lens)

C06 should **defer**:
- Event console integration (needs redaction review)
- Command manifest UI (nice-to-have, not blocking)
- Receipt linkage wiring (deferred C05 follow-through)
- Bottom drawer receipt tab (placeholder wiring only)

## Safety and Redaction Boundaries

The workspace must never expose:

| Boundary | Source of Enforcement |
|----------|----------------------|
| Raw args | C05-T002 contract, C05-T003 helper |
| Secrets | C05-T002 contract, C05-T003 helper |
| Credentials | C05-T002 contract, C05-T003 helper |
| Hidden prompts | C05-T002 contract |
| System prompts | C05-T002 contract |
| Raw `extra_meta` | C05-T002 contract, C05-T003 helper |
| Raw `result_json` | C05-T002 contract, C05-T003 helper |
| Stack traces | C05-T002/C05-T005 |
| Unredacted payloads | C05-T002 |
| Local surrogate IDs when stable IDs exist | C05-T002 |

All existing C05 redaction boundaries must be preserved in any workspace composition.

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

## Gaps

1. **Receipt linkage deferred** — C03 receipt store not wired in command bus routes. Tool-turn readback returns empty receipt fields.
2. **No unified workspace lens** — Operator must switch between 4+ lenses to assemble a complete picture.
3. **No workspace surface contract** — C06 needs a contract defining what panels/cards compose the workspace, their data dependencies, and layout constraints.
4. **Tool-turn observability conditional** — Gated on `assistant_message_id` availability (not always present in work-order data).
5. **Event console not redaction-reviewed** — Raw event surface is not safe for default workspace composition.
6. **Command manifest not surfaced** — 106 discoverable commands exist but are not visible to the operator.
7. **Bottom drawer receipts tab is a placeholder** — Receipt evidence exists in CodingWorkOrdersPanel but not in the drawer.
8. **Work-order latest-run bridge not surfaced** — Backend route exists, no UI panel.

## Recommended C06 Backlog

1. `C06-T001: Guardian Operator Workspace seam audit` ← THIS TASK
2. `C06-T002: Define Guardian Operator Workspace surface contract`
3. `C06-T003: Scaffold workspace lens and layout`
4. `C06-T004: Compose work-order status panel`
5. `C06-T005: Compose receipt evidence panel`
6. `C06-T006: Compose tool-turn observability panel`
7. `C06-T007: Compose health and heartbeat panels`
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

No automated runtime tests apply — docs-only seam audit.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C06-T002: Define Guardian Operator Workspace surface contract`
