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
