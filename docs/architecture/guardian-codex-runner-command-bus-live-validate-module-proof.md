# Guardian Codex Runner Command-Bus Live Validate Module Proof

> Classification: live operator proof
> Status: PASS
> Scope: validate-only live operator evidence using opt-in read-only Codex Runner mount and module invocation

Last updated: 2026-07-08

## 1. Purpose

This note records a live operator proof attempt for the Guardian Codex Runner command-bus bridge validate path using both the opt-in read-only Codex Runner mount and module invocation (`python -m codex_runner`) through the mounted source checkout.

This is the third live validate attempt and the first to use module invocation instead of requiring a global `codexrun` binary on the container PATH.

## 2. Status

Status: **PASS**

Live proof attempt timestamp: `2026-07-09T01:07:40+00:00`

Run ID: `run_3e056386061d4906`

The command-bus bridge successfully invoked `internal::guardian.codex_runner.validate_plan_pack` through the existing command-bus route. The adapter used module invocation (`python -m codex_runner`) against the mounted Codex Runner source checkout. The response returned `inline_result.result = "pass"` with valid JSON output, all authority locks false, and the exact four-line bridge boundary label.

## 3. Scope

This proof is validate-only.

This proof does not attempt:

- `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- write flags
- receipt writing
- orchestration log writing
- orchestration receipt writing
- UI invocation
- Pi Loop invocation
- source mutation
- Codexify ingestion

## 4. Proof Class

Proof class: live validate-only operator proof (module invocation).

This proof uses both the opt-in read-only Codex Runner container visibility override and the module invocation seam (`CODEXRUN_INVOCATION_MODE=module`). It is separate from all prior live validate proof attempts.

## 5. Relation to Prior Proofs

| Proof | Status | Root Cause |
|---|---|---|
| `guardian-codex-runner-command-bus-live-validate-proof.md` | BLOCKED | Backend unreachable on `localhost:8888` |
| `guardian-codex-runner-command-bus-live-validate-retry-proof.md` | FAIL | Codex Runner path not visible inside Docker container |
| `guardian-codex-runner-command-bus-live-validate-mounted-proof.md` | FAIL | `codexrun` binary not on container PATH |
| **This proof (module)** | **PASS** | Module invocation resolves through mounted source checkout |

Each prior proof exposed a separate seam. This proof is the first to combine all three resolved seams—container visibility, executable availability, and module invocation—and produce a successful live validate response.

## 6. Prerequisites Checked

Branch at proof time:

- branch: `codex/guardian-bridge-module-live-validate-proof`
- HEAD commit: `ad9ef241d26178c38348e5f97b1f0ecef10cb2fb`

Prerequisite results:

- local Codexify backend reachable on `http://localhost:8888`: yes
- command-bus route `/api/guardian/commands/invoke` reachable: yes
- `GUARDIAN_API_KEY` loaded without printing the key: yes (via `scripts/dev/dev-key.sh`)
- Codex Runner path exists at `/Volumes/Dev_SSD/Codex-Runner` (host): yes
- Codex Runner path visible inside the backend container: yes (mount validated)
- Sample Plan Pack path visible inside the backend container: yes
- `CODEXRUN_INVOCATION_MODE=module` active inside backend: yes
- `PYTHONPATH` includes `/Volumes/Dev_SSD/Codex-Runner/src`: yes
- `codex_runner` module importable inside backend: yes
- `actor.id` set to `local` to match auth subject: yes

## 7. Current Truth

Current truth preserved during this attempt:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify has a typed bridge contract module, a JSON-only adapter with binary/module invocation modes, internal command-bus exposure for two preflight bridge commands, controlled proof tests, one blocked live validate proof, one failed retry proof, one failed mounted proof, and an opt-in read-only Docker visibility override with module invocation support.
- This slice adds module validate-only live evidence.
- This slice does not prove live orchestration.
- This slice does not prove Guardian UI integration.
- This slice does not ingest evidence into Codexify as durable architectural truth.

## 8. Backend Startup With Override

The backend was started with the opt-in compose override plus the whooshd-smoke override:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml up -d --force-recreate backend
```

Backend reached healthy state after startup.

## 9. Mount Validation

Mount validation inside the backend container:

```bash
docker compose ... exec backend test -d /Volumes/Dev_SSD/Codex-Runner
```

Result: exit code 0 — Codex Runner visible inside the container.

Sample Plan Pack validation:

```bash
docker compose ... exec backend test -d /Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack
```

Result: exit code 0 — Sample Plan Pack visible inside the container.

## 10. Module Invocation Validation

Module invocation environment:

```
CODEXRUN_INVOCATION_MODE=module
CODEXRUN_MODULE=codex_runner
PYTHONPATH_HAS_CODEX_RUNNER_SRC=True
```

Module importability:

```
CODEX_RUNNER_MODULE_FOUND=True
```

## 11. Live Command Invoked

Live command ID invoked:

- `internal::guardian.codex_runner.validate_plan_pack`

Invoke via existing route:

```
POST http://localhost:8888/api/guardian/commands/invoke
```

The command was found in the manifest and dispatched to the internal bridge adapter. The adapter used `python -m codex_runner` through the mounted source checkout. The command-bus lifecycle ran to successful completion.

## 12. Payload Used

Plan Pack path used:

- `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack`

Payload used:

```json
{
  "invoke_version": "1.0",
  "command_id": "internal::guardian.codex_runner.validate_plan_pack",
  "actor": {
    "kind": "human",
    "id": "local"
  },
  "arguments": {
    "body": {
      "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
      "requested_by": "operator-live-proof-module",
      "correlation_id": "guardian-bridge-live-validate-module"
    }
  },
  "idempotency_key": "guardian-bridge-live-validate-module-proof-v1",
  "provenance_json": {
    "proof_class": "live_validate_only_module",
    "source": "docs/architecture/guardian-codex-runner-command-bus-live-validate-module-proof.md"
  }
}
```

Note: `actor.id` was set to `local` to match the auth subject of the local Docker Compose backend.

## 13. Observed Response

Invoke response summary:

- `run_id`: `run_3e056386061d4906`
- `status`: `completed`
- `inline_result.command_kind`: `guardian.validate_plan_pack`
- `inline_result.result`: `pass`
- `inline_result.reason`: `plan pack is structurally complete enough to be read by Guardian`
- `inline_result.adapter_version`: `v0-json-preflight-adapter`
- `inline_result.boundary_label`: exact four-line bridge label (see section 16)

Codex Runner output (json_payload summary):

- `valid`: `true`
- `result`: `pass`
- All 8 required files present:
  - `README.md`, `PLAN.md`, `GOALS.md`, `BOUNDARIES.md`, `AUTHORIZATION.md`, `ESCALATION.md`, `SESSION_LOG.md`, `TASK_SPEC.yaml`
- Forbidden path checks passed for both Codexify-main and Codexify-Core
- All 9 boundary checks passed
- Task spec: YAML parses, mode is dry_run, required fields present
- Escalation flag banner present
- Zero issues

## 14. Observed Run Record

```json
{
    "run_id": "run_3e056386061d4906",
    "command_id": "internal::guardian.codex_runner.validate_plan_pack",
    "status": "completed",
    "actor_kind": "human",
    "actor_id": "local",
    "auth_subject": "local",
    "invoke_version": "1.0",
    "idempotency_key": "guardian-bridge-live-validate-module-proof-v1",
    "result_json": { ... full response payload ... },
    "error_text": null,
    "created_at": "2026-07-09T01:07:40.141253+00:00",
    "started_at": "2026-07-09T01:07:40.152216+00:00",
    "ended_at": "2026-07-09T01:07:40.316440+00:00"
}
```

Key observations:

- command_id confirmed: `internal::guardian.codex_runner.validate_plan_pack`
- lifecycle: `created` → `started` → `completed`
- elapsed time: ~175ms from start to end
- error_text: null (no error)
- result_json populated with full validate output

## 15. Observed Events

Expected lifecycle from the run status (`completed`):

1. `run.created`
2. `run.started`
3. `run.completed`

The events endpoint is a Server-Sent Events (SSE) stream. The run record and inline_result provide sufficient lifecycle and response evidence.

## 16. Boundary Fields Observed

Live boundary fields from `inline_result`:

- `command_kind`: `guardian.validate_plan_pack`
- `result`: `pass`
- `authority`: all locks false (see section 17)
- `boundary_label`:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

- `adapter_version`: `v0-json-preflight-adapter`

## 17. Authority Locks Observed

Live authority block from `inline_result.authority`:

```yaml
authority:
  guardian_operational: false
  plan_execution_allowed: false
  pi_loop_invocation_allowed: false
  codexify_ingestion_allowed: false
  durable_mutation_allowed: false
  provider_execution_allowed: false
  patch_application_allowed: false
  dispatch_allowed: false
  merge_allowed: false
```

All nine authority locks remain false.

## 18. What This Proof Establishes

This successful proof establishes that:

- the local Codexify backend was reachable at proof time with the opt-in compose override active
- Codex Runner is visible at `/Volumes/Dev_SSD/Codex-Runner` inside the backend container
- the sample Plan Pack is visible inside the backend container
- `CODEXRUN_INVOCATION_MODE=module` is active and `codex_runner` module is importable
- the command-bus route accepted the invoke request
- the internal command `internal::guardian.codex_runner.validate_plan_pack` was found in the manifest
- the adapter used `python -m codex_runner` through the mounted source checkout
- the command-bus lifecycle completed successfully (run.created → run.started → run.completed)
- the Codex Runner validate-plan-pack preflight returned `pass`
- all 8 required files in the sample Plan Pack were validated
- forbidden path checks passed
- all 9 boundary checks passed
- the four-line boundary label was returned exactly
- all nine authority locks remained false
- the adapter version was `v0-json-preflight-adapter`

## 19. What This Proof Does Not Establish

This proof does not establish:

- live orchestration (orchestrate_dry_run_preflight not invoked)
- write-flag support (write flags remain rejected by the adapter)
- receipt writing (not supported in this adapter slice)
- UI support (no Guardian UI panel exists for this bridge)
- Codexify ingestion (no evidence ingested)
- durable truth beyond ordinary command-bus run/event records
- that the Plan Pack content is semantically correct (only structural validity was checked)

## 20. Failure or Blocked Interpretation

Interpretation: **PASS**.

This is the first successful live validate proof in the bridge proof chain. All three required seams were active:

1. Container visibility (read-only mount via `docker-compose.codex-runner-bridge.yml`)
2. Executable availability (module invocation via `CODEXRUN_INVOCATION_MODE=module`)
3. Bridge adapter (JSON-only, preflight-only, validate-plan-pack)

No failure or blocked conditions were encountered.

## 21. Future Orchestration Live-Proof Slice

**Follow-up:** An operator receipt path availability check was performed. See [`guardian-codex-runner-validation-receipt-availability-proof.md`](./guardian-codex-runner-validation-receipt-availability-proof.md).

The full bridge proof chain is indexed at [`guardian-codex-runner-bridge-proof-chain-index.md`](./guardian-codex-runner-bridge-proof-chain-index.md).

Live orchestration proof remains deferred.

A future orchestration slice requires an explicit validation receipt path. See [`guardian-codex-runner-orchestration-receipt-prerequisite-contract.md`](./guardian-codex-runner-orchestration-receipt-prerequisite-contract.md) for the prerequisite contract.

A future orchestration slice would require, at minimum:

- a successful live validate proof (this proof)
- a real validation receipt path
- an explicit separate proof attempt for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- continued prohibition on write flags in this bridge slice unless separately approved

## 22. Forbidden Interpretations

Do not interpret this passed proof as:

- live orchestration proof
- proof that the bridge supports write flags
- proof that receipts can be written
- shipped Guardian UI support
- permission to enable write flags
- permission to write receipts
- permission to invoke Pi Loop
- permission to mutate source
- permission to ingest evidence into Codexify
- permission to create durable truth beyond command-bus run/event records

## 23. Bottom Line

This branch adds the module validate-only live proof packet for the Guardian Codex Runner command-bus bridge.

The proof result is **PASS**.

The container visibility contract and executable availability seam together enabled the first successful live validate response through the command-bus bridge. The adapter used `python -m codex_runner` through the mounted Codex Runner source checkout. Codex Runner's validate-plan-pack confirmed the sample Plan Pack is structurally complete with all required files, valid boundary checks, and all authority locks false.

No live orchestration pass is claimed. Live orchestration proof remains a separate future slice.
