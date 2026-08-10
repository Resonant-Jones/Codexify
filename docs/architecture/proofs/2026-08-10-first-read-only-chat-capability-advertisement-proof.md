# First read-only ordinary-chat capability advertisement proof

**Date:** 2026-08-10
**Campaign stage:** 2I
**Classification:** architecture-aligned code and deterministic seam proof; no release claim.

## Scope

This receipt records the first automatic ordinary-chat capability exposure:
`op::health_health_get`, the existing `GET /health` Command Bus command. It
does not add a user selector, a second capability, a write action, a recursive
tool loop, a provider-wide `supports_tools` declaration, or a release claim.

## Manifest and least-authority evidence

The live `guardian.guardian_api` FastAPI surface was passed to
`build_manifest()`. Its current entry is:

| Field | Value |
| --- | --- |
| command ID | `op::health_health_get` |
| method / path | `GET /health` |
| effect / risk | `read` / `read_only` |
| idempotency / approval | `safe` / `none` |
| required path/query/header fields | none |
| required body | none |

The model-facing ToolSpec is exactly one command with the canonical command ID,
a health description, and `{ "type": "object", "additionalProperties":
false, "maxProperties": 0 }`. It intentionally does not mirror Command Bus
transport buckets, so a model controls no headers, query, body, or path values.
The canonical execution identity still comes from the current manifest entry.

## Exposure and authority proof

`guardian/tools/chat_exposure.py` contains a fixed one-ID allowlist and also
verifies the manifest safety facts above. Unknown commands and a modified
mutating version of the health manifest entry return no exposure. The helper
does not call `execute_invoke` and never projects the full manifest.

Automatic resolution runs only after effective provider/model resolution and
only when `task.tools is None`. The resolved list is used both for provider
advertisement and as the Stage 1 advertised subset. Explicit non-empty lists
and `task.tools=[]` remain unchanged. An unadvertised proposal still stops at
Stage 1 with `tool_command_blocked`, no Command Bus call, and no command run.

## Provider proof

- DeepSeek automatically receives the one health tool through its unchanged
  native alias transport. A deterministic native call executes once, reinjects
  the result, and returns a final assistant answer with `completed`,
  `tool_turn_completed`, and a populated `commandRunId`. A model may also
  return a plain answer without executing the advertised capability.
- Whoosh'd receives the command only for the exact Stage 2D Gemma target when
  a current configured-endpoint `/v1/models` `ModelInfo` entry parses through
  `parse_whooshd_runtime_inventory_entry` and the real Stage 2G projection is
  `eligible` under explicit exposure permission. The bounded helper retains no
  raw inventory, model path, or endpoint metadata and performs no runtime
  mutation or cache write.
- Missing inventory, missing/mismatched attestation, wrong target, or non-ready
  state result in no advertisement and preserve the ordinary local streaming
  path. Stage 2F.1b remains mandatory after a response: a simulated post-request
  serving-identity change stops before `execute_invoke` even after Stage 2G had
  exposed the command.
- Other providers and local runtimes receive no automatic tools.

The existing Stage 2H convergence tests retain the one-command limit for both
transports. A second decision reaches `limit_reached` / `tool_turn_limit_reached`
after exactly one invocation. No canonical runtime protocol token changed.

## Files and validation

Changed implementation and test surfaces:

- `guardian/tools/chat_exposure.py`
- `guardian/core/chat_completion_service.py`
- `guardian/providers/whooshd_control_plane.py`
- `tests/core/test_chat_tool_exposure.py`
- the four architecture documents updated by this receipt

Focused deterministic validation:

```text
.venv/bin/python -m pytest -q tests/core/test_chat_tool_exposure.py \
  tests/core/test_chat_completion_service_tool_loop.py \
  tests/providers/test_tool_turn_transport_convergence.py \
  tests/providers/test_deepseek_adapter.py \
  tests/providers/test_whooshd_tool_adapter.py \
  tests/providers/test_whooshd_qualification.py \
  tests/providers/test_whooshd_tool_capability.py \
  tests/command_bus/test_manifest.py tests/core/test_ai_router.py
```

Result: `158 passed`.

Full-suite, documentation validation, and final diff checks are recorded in the
task closeout. The repository Ruff baseline currently contains pre-existing
findings in `chat_completion_service.py`; the new exposure/test files are
clean, and the edited control-plane file retains its one pre-existing blind
exception finding with no new lint finding.

## Limitations and next proof

No paid DeepSeek call, provider process start/restart, model replacement, or
live ordinary-chat provider proof was performed. Deterministic runtime-seam
tests prove the code path only. The next atomic slice, if separately approved,
is Stage 2J: live proof of this same capability on already-available qualified
transports, with no new capability added.

## Commit

Commit ID is recorded in the task closeout; embedding the final commit hash in
the file it hashes is self-referential and would make the receipt inaccurate.
