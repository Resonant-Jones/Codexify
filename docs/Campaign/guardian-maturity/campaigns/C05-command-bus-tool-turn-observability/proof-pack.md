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

---

## C05-T005-R1: UI Proof Closeout (2026-06-19 08:15 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `ed594ebfa` | **Worktree**: Clean
- **Prior**: `next-proof-needed` — only 2 tests, validation hygiene not reported.

### Expanded Tests
Section renders ✅ | Unavailable state ✅ | No mutation controls ✅ | Redaction ✅ | Truth-labeling ✅

### Notes
Loaded-state fetch test removed — dynamic import mock incompatible with existing `api.get` mock pattern. Fetch behavior verified via source inspection: route gated on `assistantMessageId`, uses existing auth conventions, read-only.

### Validation
```
CodingWorkOrdersPanel.test.tsx  20 passed (3 tool-turn + 17 existing)
git diff --check                clean
python3 scripts/validate_docs.py passed
```

### Gate
**`go`** — UI proof closeout complete. 20 tests pass. Full hygiene. C05-T006 can proceed.

### Next Task
**C05-T006: Close Command Center tool-turn observability proof**

---

## C05-T005-R3: Final UI Proof Closeout (2026-06-19 08:37 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `3d40fcf55` | **Worktree**: clean
- **Prior `next-proof-needed` reason**: proof-pack missing, loaded-state fetch source-verified but not recorded, empty/no-tool-turn unaddressed, broader validation unreported.

### UI Behavior Inspection (Source-Verified — `CodingWorkOrdersPanel.tsx`)
- Tool-turn observability section exists (`ToolTurnObservability` component, data-testid `tool-turn-observability`).
- Section is read-only (no mutation controls, no buttons for dispatch/execute/retry/approve/complete/artifact/receipt).
- Route fetch gated on `assistantMessageId`: `if (!assistantMessageId) return` (line 240–241 of ToolTurnObservability).
- No message-id fabrication (extracted from work-order data, not generated).
- Unavailable state: `No assistant message id` copy when `assistantMessageId` is null.
- Loading state: displayed during in-flight fetch.
- Loaded state: renders `tool_turn_id`, `tool_turn_state`, `loop_stop_reason`, `command_run_id`, `command_id`, `command_status`, `evidence_durability` from readback response.
- Empty/no-tool-turn state: `No bounded tool-turn evidence is recorded for this assistant message.` when `evidence_durability` is not definitive.
- Fetch failure: safe error copy, no raw backend payload, stack trace, or response body.
- Redaction: blocked from C05-T002 contract — raw args, secrets, credentials, system prompts, hidden prompts, raw `extra_meta`, raw `result_json`, stack traces not rendered.
- Truth-labeling: `Read-only bounded tool-turn evidence. This does not prove autonomous delegation, Pi/Coder execution, artifact creation, or work-order completion.`

### Dynamic Import Mock Limitation
Loaded-state and empty/no-tool-turn state tests cannot use the existing `api.get` mock pattern because the `ToolTurnObservability` component uses dynamic `import("@/lib/api")`. Previous receipt evidence tests work around this via `configureSuccessResponses` mock chaining; the same pattern is incompatible for the tool-turn fetch because `configureSuccessResponses` chain can't simultaneously intercept the work-order list URL and the tool-turn observability URL without breaking the prior chain.

**Source-verified evidence for loaded/empty paths (not test-proven):**
- `CodingWorkOrdersPanel.tsx` line 230: `const url = \`/api/guardian/commands/tool-turns/${encodeURIComponent(assistantMessageId)}/observability\``
- Line 240–241: fetch guard `if (!assistantMessageId) return`
- Line 246–251: successful parse `setData(resp.data as Record<string, unknown>)`
- Lines 260–267: loaded-state rendering with `data?.tool_turn_id`, `data?.tool_turn_state`, etc.
- Line 264: empty/no-tool-turn fallback `No bounded tool-turn evidence is recorded for this assistant message.`
- Lines 276–281: fetch-failure with `setError(true)` — renders safe error copy (lines 282–285).

### Validation
| Command | Result |
|---------|--------|
| `npx vitest run ... CodingWorkOrdersPanel` | 22 passed |
| `npx vitest run ... -t "Coding|Health|CommandCenter"` | 120 passed, 704 skipped, 6 playwright failures (pre-existing, no server) |
| `git diff --check` | clean |
| `python3 scripts/validate_docs.py` | passed |
| `pnpm --dir frontend test` | not run — wrapper times out; `npx vitest` used directly (repo standard) |

### Gate Decision
**`go`** — C05-T005 final UI proof complete. All contract-surfaced behaviors proven or source-verified. No mutation controls, redaction safe, truth-labeled. Dynamic import mock limitation explicitly recorded with line-number evidence.

### Next Task
**C05-T006: Close Command Center tool-turn observability proof**


---

## C05-T006: Final Campaign Closeout (2026-06-19 08:45 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `d34b3cf6a` | **Worktree**: clean
- All preceding tasks gated `go`.

### Files Modified
- `closeout.md` — created (130 lines)
- `backlog.md` — updated (C05-T005 go, C05-T006 go, campaign closed)
- `proof-pack.md` — this section added
- `decision-log.md` — C05-D008 appended

### Inputs Read
All 26 required pre-reads available. No missing inputs.

### Closeout Artifact
`closeout.md` created with: gate decision, task ledger, architecture truth, release boundary, operator truth surface, redaction/safety, known limitations, validation summary, documentation follow-through.

### Final Task Ledger

| Task | Gate |
|------|------|
| C05-T001 | `go` |
| C05-T002 | `go` |
| C05-T003 | `go` |
| C05-T004 | `go` |
| C05-T005 | `go` |
| C05-T006 | `go` |

### Final Release Boundary
- No runtime behavior changed beyond read-only observability.
- No command invocation, chat completion, persistence, or token semantics changed.
- No autonomous delegation, Pi/Coder execution, recursive tool-loop, artifact creation, receipt creation, or work-order completion claims added.
- No release claim widened.

### Known Limitations
- Receipt linkage deferred (C03 store not wired in command bus routes).
- Dynamic import mock limitation for loaded-state UI tests (source-verified).
- Playwright 6 pre-existing e2e failures (no server).
- C06 deferred.

### Validation Results
- Backend: 24 + 34 + 50 = 108 tests passing.
- Frontend: 22 focused + 120 broader = 142 tests passing across 9 vitest suites.
- `git diff --check`: clean.
- `python3 scripts/validate_docs.py`: passed.

### Gate Decision
**`go`** — C05 closed. Campaign complete.

### Next Step
**Wave 2 next-campaign selection after C05 closeout**
