# C05 Proof Pack

## C05-T001: Tool-Turn Observability Seam Audit (2026-06-19 05:45 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `56fbe3f37` — docs: select next Guardian maturity wave campaign
- **Worktree**: Clean

### Files Modified

- `seam-audit.md` — 17-section audit artifact (new)
- `backlog.md` — C05 task queue (new)
- `proof-pack.md` — this section (new)
- `decision-log.md` — C05-D001 (new)

### Inputs Read

`00-current-state.md`, `agent-tool-loop-contract.md`, `tech-debt-and-risks.md`, `wave-2-selection.md`, C03 closeout, `protocol_tokens.py`, `chat_completion_service.py`, `chat_worker.py`, `command_bus/contracts.py`, `command_bus.py`, `db/models.py`.

### Audit Result

All six canonical observability fields (`toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason`, `messageId`, `requestId`) are **defined, generated at runtime, and durably persisted** in `chat_messages.extra_meta`. CommandRun records provide durable result/error storage with API readback via C03-T008. The gap is **frontend surfacing** — the data exists, it's just not visible to the operator.

### Gate Decision

**`go`** — Backend seams are proven. C05 can proceed to C05-T002 (define tool-turn observability read model contract).

### Next Task

**C05-T002: Define tool-turn observability read model contract**

---

## C05-T002: Read Model Contract (2026-06-19 06:00 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `a0dda5ca7` — docs: audit Guardian tool-turn observability seam
- **Worktree**: Clean

### Files Modified

- `tool-turn-read-model-contract.md` — 18-section contract (new)
- `backlog.md` — C05-T002 marked complete

### Contract Result

Defined 15 canonical read model fields with source, durability, and redaction rules. Source priority: `chat_messages.extra_meta` → `command_runs` → `command_run_events` → receipts → task events → logs. All redaction boundaries documented. Relationship to CommandRun readback and receipt evidence defined.

### Gate Decision

**`go`** — Read model contract complete. C05-T003 can proceed.

### Next Task

**C05-T003: Add backend read-model helper for tool-turn observability**

---

## C05-T003: Backend Read-Model Helper (2026-06-19 06:15 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `ae3ac129a` — docs: define Guardian tool-turn observability read model
- **Worktree**: Clean

### Files Modified

- `guardian/command_bus/tool_turn_observability.py` — read-model helper with `ToolTurnObservabilityReadModel` dataclass + `build_tool_turn_observability_read_model()` (new)
- `tests/command_bus/test_tool_turn_observability.py` — 24 tests (new)

### Test Results

```
test_tool_turn_observability.py  24 passed
```

### C05-T003 Gate Decision

- **Decision**: `go`
- **Reason**: Read-model helper implemented. Pure/read-only. Extracts from extra_meta (camelCase wins over snake_case), enriches from CommandRun (mapping + ORM), supports receipt enrichment. Redaction proven: no raw args, secrets, prompts, or surrogate IDs surfaced. 24 tests pass.

### Next Task

**C05-T004: Add backend readback route for tool-turn observability**

---

## C05-T003-R1: Helper Validation Closeout (2026-06-19 06:30 UTC)

### Context

- **Branch**: `codex/campaignOS`
- **Latest Commit**: `2e07bb462` — feat: add Guardian tool-turn observability read model helper
- **Worktree**: Clean
- **Prior `next-proof-needed` Reason**: Broader command-bus suite, git diff check, docs validator, and complete decision log entry not reported.

### Files Modified

- `proof-pack.md` — this section
- `decision-log.md` — C05-D003 expanded + C05-D004 added

### Helper Inspection

- Pure/read-only ✅
- No DB access ✅
- No HTTP calls ✅
- No command invocation ✅
- No shell/subprocess ✅
- No artifact creation ✅
- No input mutation ✅
- CamelCase over snake_case ✅
- Mapping + ORM CommandRun ✅
- Safe missing-evidence output ✅

### Validation

```
test_tool_turn_observability.py              24 passed
test_command_bus_phase1_invoke.py             9 passed
test_command_bus_phase1_manifest.py           1 passed
Total                                        34 passed
git diff --check                              clean
python3 scripts/validate_docs.py               passed
```

### C05-T003-R1 Gate Decision

- **Decision**: `go`
- **Reason**: Helper validation closeout complete. All 34 tests pass. `git diff --check` clean. Docs validator passed. Decision log complete. C05-T004 can proceed.

### Next Task

**C05-T004: Add backend readback route for tool-turn observability**

---

## C05-T004: Tool-Turn Readback Route (2026-06-19 06:45 UTC)

### Context
- **Branch**: `codex/campaignOS`
- **Latest Commit**: `6baec95ee`
- **Worktree**: Clean

### Files
- `guardian/routes/command_bus.py` — route added (+65 lines)
- `tests/routes/test_command_bus_tool_turn_observability.py` — 8 tests (new)

### Route
`GET /api/guardian/commands/tool-turns/{message_id}/observability`

### Tests
50 passed (8 new + 42 existing)

### Gate
**`go`** — Readback route added. Uses C05-T003 helper. All edge cases handled. No raw data.

### Next Task
**C05-T005: Surface tool-turn observability in Command Center**

---

## C05-T004-R1: Route Validation Closeout (2026-06-19 07:00 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `542d82bfb` | **Worktree**: Clean
- **Prior**: `next-proof-needed` — git diff check, docs validator, complete decision log, receipt linkage, auth posture, and no-side-effects proof not reported.

### Route Inspection
- Read-only ✅ | Uses C05-T003 helper ✅ | extra_meta → CommandRun enrichment ✅
- Missing message 404 ✅ | Non-assistant 400 ✅ | No metadata → safe null ✅
- Missing CommandRun → metadata preserved ✅ | No raw data ✅
- No writes, commands, artifacts, receipts, or job enqueue ✅
- Auth: follows command bus internal-only posture ✅

### Receipt Linkage
**Deferred** — route returns empty `receipt_ids` and `latest_receipt_id: null`. Receipt linkage requires C03 store access not yet wired in command_bus routes.

### Validation
```
test_command_bus_tool_turn_observability  8 passed
test_command_bus_run_readback             5 passed
test_command_bus_work_order_linkage      13 passed
test_tool_turn_observability             24 passed
Total                                    50 passed
git diff --check                         clean
python3 scripts/validate_docs.py          passed
```

### Gate
**`go`** — Route validation closeout complete. 50 tests pass. Full hygiene. C05-T005 can proceed.

### Next Task
**C05-T005: Surface tool-turn observability in Command Center**

---

## C05-T004-R2: Decision Log Closeout (2026-06-19 07:10 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `01be9fc33` | **Worktree**: Clean
- **Prior**: `next-proof-needed` — C05-D006 was a one-line entry.

### Repair
C05-D006 expanded to complete entry with reason, evidence, consequence, revisit trigger.

### Validation
```
git diff --check                    clean
python3 scripts/validate_docs.py     passed
```

### Gate
**`go`** — Decision log complete. C05-T004 fully closed.

### Next Task
**C05-T005: Surface tool-turn observability in Command Center**

---

## C05-T005: Command Center Tool-Turn Observability UI (2026-06-19 08:00 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `9e3643879` | **Worktree**: Clean

### Files
- `CodingWorkOrdersPanel.tsx` — `ToolTurnObservability` component (+80 lines)
- `types.ts` — added `assistant_message_id` field
- `CodingWorkOrdersPanel.test.tsx` — 2 new tests

### UI Behavior
- Unavailable state when no `assistant_message_id` ✅
- Route wired for future message ID availability ✅
- Truth-labeling present ✅
- Loading/error states ✅
- No mutation controls ✅

### Tests
18 passed (2 new + 16 existing)

### Gate
**`go`** — Tool-turn observability UI added. 18 tests pass.

### Next Task
**C05-T006: Close Command Center tool-turn observability proof**
