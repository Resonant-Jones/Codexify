# ToolSpec + Policy Wall

This document defines Phase 2 behavior for tool discovery and execution policy.

## Source of truth

`/api/tools/manifest` is derived from `/api/guardian/commands/manifest`.

No hand-maintained tool list is treated as authoritative. Tool metadata is generated
from command-bus manifest fields (`command_id`, `method`, `path_template`,
`input_schema`, `risk`, `effect`, `idempotency`, `approval_mode`).

## `/api/tools/manifest` shape

The endpoint returns:

- `tool_manifest_version`
- `manifest_version` (from command manifest)
- `generated_at` (from command manifest)
- `command_manifest_hash` (sha256 over canonical command manifest JSON)
- `tools` (derived `ToolSpec[]`)
- `openai_tools` (OpenAI function-calling payload array)

Each `ToolSpec` contains stable IDs and model-facing call schema:

- `tool_id` (stable; default `command_id`)
- `name` (model function name; default `command_id`)
- `input_schema` (transport-normalized invoke args schema)
- `risk`, `effect`, `idempotency`, `requires_confirmation`
- route linkage (`command_id`, `operation_id`, `method`, `path_template`, `aliases`)

## `/api/tools/execute` mapping

`/api/tools/execute` and `/tools/execute` map requests to command bus invoke and use
the same internal invoke implementation as `/api/guardian/commands/invoke`.

Accepted payload styles:

1. Preferred:
   - `command_id`
   - `arguments`
   - `actor`
2. Legacy:
   - `operation_id` or `method + path/path_template` or legacy `name`
   - mapped to `command_id` through manifest lookup

All routes normalize arguments into command-bus invoke shape:

- `path_params`
- `query`
- `headers`
- `body`

## Policy chokepoint

Policy evaluation is centralized in `guardian/tools/policy.py`:

- `evaluate_tool_policy(actor, command_or_tool, args, env) -> PolicyDecision`
- `apply_policy_mode(decision, mode) -> PolicyOutcome`

Policy is applied in two places (defense in depth):

1. Invoke-time: `guardian/command_bus/invoke.py` before run execution.
2. Execution-time: `guardian/command_bus/loopback_http_adapter.py` before HTTP dispatch.

Modes via `CODEXIFY_POLICY_MODE`:

- `enforce`: deny/require-confirmation blocks execution.
- `warn`: execution continues, warnings are emitted in response/events.
- `off`: bypass block, log policy decision.

Reason codes include:

- `write_effect`
- `risk_high`
- `external_network`
- `loopback_base_missing`

## Loopback requirement

Command execution requires a resolvable execution base:

- Docker/default mode: `GUARDIAN_COMMAND_BUS_LOOPBACK_BASE` is required.
- Declared non-docker mode (`LOCAL_DEV=true` or `DEBUG=true`): `GUARDIAN_API_BASE`
  may be used as fallback.

If neither is available when execution requires loopback, policy and adapter fail
closed.
