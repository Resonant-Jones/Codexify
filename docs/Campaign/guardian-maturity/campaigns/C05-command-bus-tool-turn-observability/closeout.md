# C05 Closeout: Command Bus and Tool Turn Observability

## Gate Decision

**`go`** — C05 is closed. C05-T001 through C05-T005 are accepted.

## Campaign Scope

C05 created a **read-only observability path** for bounded tool-turn evidence:

1. **Seam audit** — confirmed all six canonical observability fields are durably persisted in `chat_messages.extra_meta`.
2. **Read model contract** — defined 15-field safe read model, source priority, and redaction rules.
3. **Backend helper** (`guardian/command_bus/tool_turn_observability.py`) — pure/read-only normalization of raw metadata into a safe read model.
4. **Backend readback route** (`GET /api/guardian/commands/tool-turns/{message_id}/observability`) — exposes the safe read model via Guardian API.
5. **Command Center UI surface** — read-only `ToolTurnObservability` component in `CodingWorkOrdersPanel` with redaction enforcement and truth-labeling.

This is an **observability campaign**, not an execution expansion campaign. No command invocation, artifact creation, receipt creation, or autonomous delegation semantics were added.

## Task Ledger

| Task | Gate | Commit | Summary |
|------|------|--------|---------|
| C05-T001 Seam Audit | `go` | `a0dda5ca7` | Confirmed 6 canonical fields in `chat_messages.extra_meta` |
| C05-T002 Read Model Contract | `go` | `ae3ac129a` | Defined 15-field safe read model |
| C05-T003 Read Model Helper | `go` | `2e07bb462` / `6baec95ee` | Pure helper + 24 focused tests |
| C05-T004 Readback Route | `go` | `542d82bfb` / `01be9fc33` / `9e3643879` | `GET` route w/ 50 backend tests |
| C05-T005 Command Center UI | `go` | `ed594ebfa` / `0189061d2` / `3d40fcf55` / `d34b3cf6a` | Read-only UI surface w/ 22 focused + 120 broader frontend tests |

## Final Architecture Truth

After C05:

- **Six canonical observability fields** (`toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason`, `messageId`, `requestId`) are generated and durably persisted in `chat_messages.extra_meta`.
- **Read model contract** defines the safe subset (15 fields, source priority, redaction rules).
- **Pure helper** (`ToolTurnObservabilityReadModel` + `build_tool_turn_observability_read_model()`) normalizes raw evidence into a safe read model.
- **Backend readback route** (`GET /api/guardian/commands/tool-turns/{message_id}/observability`) exposes the safe read model. No writes, no command invocation.
- **Command Center UI** displays read-only bounded tool-turn observability gated on `assistant_message_id`.
- **Redaction boundaries** are enforced and tested (no raw args, secrets, credentials, hidden prompts, system prompts, raw `extra_meta`, raw `result_json`, stack traces, unredacted payloads, local surrogate IDs).
- **Operator UI has no mutation controls** (no dispatch, execute, retry, replay, approve, complete, create artifact, create receipt).

## Release Boundary

- **No runtime behavior changed** beyond read-only observability implementation.
- **No command invocation semantics changed.**
- **No chat completion semantics changed.**
- **No persistence schema changed.**
- **No protocol tokens were added or renamed.**
- **No release claim widened.**
- **No autonomous delegation claim added.**
- **No Pi/Coder execution claim added.**
- **No recursive tool-loop claim added.**
- **No artifact creation claim added.**
- **No receipt creation claim added.**
- **No work-order completion claim added.**

## Operator Truth Surface

The operator can now see:

- Whether tool-turn evidence exists
- Tool-turn id
- Tool-turn state
- Loop stop reason
- Command run id
- Command id
- Command status
- Safe command result summary
- Safe command error summary
- Evidence durability
- Receipt count or empty receipt fields (receipt linkage deferred)

## Redaction and Safety

Enforced by C05-T002 contract, C05-T003 helper, C05-T004 route, and C05-T005 UI:

| Boundary | Enforced |
|----------|----------|
| Raw args not surfaced | ✅ |
| Secrets not surfaced | ✅ |
| Credentials not surfaced | ✅ |
| Hidden prompts not surfaced | ✅ |
| System prompts not surfaced | ✅ |
| Raw `extra_meta` not surfaced | ✅ |
| Raw `result_json` not surfaced | ✅ |
| Stack traces not surfaced | ✅ |
| Unredacted payloads not surfaced | ✅ |
| Local surrogate IDs not surfaced when stable IDs exist | ✅ |

Frontend tests include redaction proof. Backend tests include redaction proof.

## Known Limitations and Deferred Work

- **Receipt linkage remains deferred** — C03 receipt store is not wired in command bus routes. The readback route returns empty receipt fields.
- **Dynamic import mock limitation** — Loaded-state UI fetch/render proof includes source-verified evidence over dynamic `import("@/lib/api")`. The ToolTurnObservability component uses dynamic import patterns incompatible with the existing `configureSuccessResponses` mock chain for simultaneous work-order list + tool-turn fetch.
- **Playwright** — 6 pre-existing e2e failures due to no running server in the broader `-t "Coding|Health|CommandCenter"` vitest suite.
- **C06 unified operator workspace** remains deferred.
- **C05 does not prove autonomous delegation or coding-agent execution.**

## Validation Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Helper focused (`test_tool_turn_observability.py`) | 24 | passed |
| Command-bus validation (`test_command_bus_run_readback.py` etc.) | 34 | passed |
| Route + related backend (`test_command_bus_tool_turn_observability.py`) | 50 | passed |
| Focused Command Center (`CodingWorkOrdersPanel.test.tsx`) | 22 | passed |
| Broader CommandCenter+Health (`-t "Coding|Health|CommandCenter"`) | 120 (9 vitest suites) | passed |
| Playwright (broader suite) | 6 | pre-existing failures (no server) |
| `git diff --check` | — | clean |
| `python3 scripts/validate_docs.py` | — | passed |

## Documentation Follow-Through

- `00-current-state.md` unchanged
- ADRs unchanged
- C03 files unchanged
- No C06 files created
- C05 proof-pack updated
- C05 decision log updated
- C05 backlog updated
- C05 closeout created

## Final Gate

- **C05 final gate**: `go`
- **Campaign closed**

### Next Step

**Wave 2 next-campaign selection after C05 closeout**
