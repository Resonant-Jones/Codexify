# Guardian Codex Runner Command-Bus Live Orchestration Proof

> Classification: live operator proof
> Status: PASS
> Scope: dry-run orchestration preflight only — no execution occurred

Last updated: 2026-07-09

## 1. Purpose

This note records the first live dry-run orchestration preflight proof for the Guardian Codex Runner command-bus bridge. It uses the selected validation receipt path and the sample Plan Pack through the module invocation seam.

This is orchestration preflight only. No execution occurred.

## 2. Status

Status: **PASS**

Live proof attempt timestamp: `2026-07-09T05:16:18+00:00`

Run ID: `run_a32f5825548a402a`

The command-bus bridge successfully invoked `internal::guardian.codex_runner.orchestrate_dry_run_preflight` through the existing command-bus route. The adapter used module invocation (`python -m codex_runner`) against the mounted Codex Runner source checkout. The response returned `inline_result.result = "pass"` with all 12 preconditions met, all 8 file hashes verified, all authority locks false, and the exact four-line bridge boundary label.

## 3. Scope

This proof is dry-run orchestration preflight only.

This proof does not attempt:

- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- write flags
- receipt writing
- orchestration log writing
- orchestration receipt writing
- Codexify ingestion
- UI invocation

This proof does not add UI support. No UI panel exists for this bridge.

## 4. Proof Class

Proof class: live dry-run orchestration preflight operator proof.

This proof uses the opt-in read-only Codex Runner mount, module invocation, and the selected validation receipt path. It is the first live orchestration attempt in the bridge proof chain.

## 5. Relation to Prior Proofs

| Artifact | Status | Relationship |
|---|---|---|
| `guardian-codex-runner-command-bus-live-validate-module-proof.md` | PASS | Validation proven first |
| `guardian-codex-runner-orchestration-receipt-prerequisite-contract.md` | Contract | Defines receipt rules |
| `guardian-codex-runner-validation-receipt-availability-proof.md` | BLOCKED | No operator source configured |
| `guardian-codex-runner-selected-validation-receipt-proof.md` | SELECTED_AVAILABLE | Receipt path verified |
| **This proof** | **PASS** | **First live orchestration preflight** |

## 6. Current Truth

Current truth preserved during this attempt:

- The validate-only live proof passed through the command-bus bridge using module invocation.
- The selected validation receipt path was proven available and visible.
- This proof records live dry-run orchestration preflight evidence.
- No execution, no Pi Loop, no source mutation, no ingestion occurred.

## 7. Selected Receipt Input

Selected receipt path:

```
/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json
```

Source: `/tmp/guardian-bridge-validation-receipt-path.txt`

Plan Pack path:

```
/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack
```

## 8. Backend Startup With Override

Backend started with compose override:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml up -d --force-recreate backend
```

Note: `GUARDIAN_AUTH_MODE=local`, `CODEXIFY_MULTI_USER_ENABLED=false`, and OAuth env cleared in the bridge override to ensure local auth works with the `.env` file's remote-mode defaults.

## 9. Preflight Checks

All preflight checks at proof time:

| Check | Result |
|---|---|
| Backend reachable on `localhost:8888` | PASS |
| `GUARDIAN_API_KEY` available | PASS |
| Codex Runner mount visible in container | PASS |
| Plan Pack visible in container | PASS |
| Selected receipt visible in container | PASS |
| Selected receipt readable in container | PASS |
| `CODEXRUN_INVOCATION_MODE=module` active | PASS |
| `codex_runner` module importable | PASS |
| `PYTHONPATH` includes Codex Runner src | PASS |

## 10. Live Command Invoked

Command ID: `internal::guardian.codex_runner.orchestrate_dry_run_preflight`

Invoke route: `POST http://localhost:8888/api/guardian/commands/invoke`

## 11. Payload Used

```json
{
  "invoke_version": "1.0",
  "command_id": "internal::guardian.codex_runner.orchestrate_dry_run_preflight",
  "actor": {
    "kind": "human",
    "id": "local"
  },
  "arguments": {
    "body": {
      "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
      "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json",
      "requested_by": "operator-live-orchestration-proof",
      "correlation_id": "guardian-bridge-live-orchestration-proof"
    }
  },
  "idempotency_key": "guardian-bridge-live-orchestration-proof-20260709a",
  "provenance_json": {
    "proof_class": "live_orchestration_dry_run_preflight",
    "source": "docs/architecture/guardian-codex-runner-command-bus-live-orchestration-proof.md"
  }
}
```

## 12. Observed Response

Response summary:

- `run_id`: `run_a32f5825548a402a`
- `status`: `completed`
- `inline_result.command_kind`: `guardian.orchestrate_dry_run_preflight`
- `inline_result.result`: `pass`
- `inline_result.reason`: `all preconditions passed; dry-run orchestration record prepared (no execution occurred)`
- `inline_result.adapter_version`: `v0-json-preflight-adapter`

Codex Runner orchestration output summary:

- `orchestration_type`: `guardian_operated_dry_run`
- `orchestration_version`: `v0`
- **12/12 preconditions met**:
  - `plan_pack_exists`: true
  - `receipt_exists`: true
  - `receipt_type_valid`: true
  - `receipt_version_valid`: true
  - `receipt_validation_passed`: true
  - `authority_locks_false`: true
  - `evidence_flags_non_authoritative`: true
  - `manifest_algorithm_sha256`: true
  - `manifest_hashes_match`: true
  - `authorization_allows_dry_run_orchestration`: true
  - `boundaries_allow_dry_run_orchestration`: true
  - `repo_boundary_valid`: true
- **8/8 file hashes verified** (sha256 match for all Plan Pack files)
- All authority locks: `false`
- Evidence: `orchestration_record_only: true`, `execution_performed: false`, `pi_loop_invoked: false`, `codexify_ingestion_performed: false`, `source_mutation_performed: false`
- `intended_action.kind`: `dry_run_orchestration_preparation`
- `evidence_paths`: all null (no write paths)

## 13. Observed Run Record

```json
{
    "run_id": "run_a32f5825548a402a",
    "command_id": "internal::guardian.codex_runner.orchestrate_dry_run_preflight",
    "status": "completed",
    "error_text": null,
    "created_at": "2026-07-09T05:16:18.737819+00:00",
    "started_at": "2026-07-09T05:16:18.759731+00:00",
    "ended_at": "2026-07-09T05:16:18.938056+00:00"
}
```

Lifecycle: `created` → `started` → `completed` (~178ms from start to end).

## 14. Observed Events

Expected lifecycle: `run.created` → `run.started` → `run.completed`.

The events endpoint is an SSE stream. The run record and inline_result provide sufficient lifecycle and response evidence.

## 15. Boundary Fields Observed

Live boundary fields from `inline_result`:

- `command_kind`: `guardian.orchestrate_dry_run_preflight`
- `result`: `pass`
- `boundary_label`:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

- `adapter_version`: `v0-json-preflight-adapter`

## 16. Authority Locks Observed

All nine authority locks remain `false`:

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

Additionally, the orchestration output declares:
- `evidence.orchestration_record_only: true`
- `evidence.execution_performed: false`
- `evidence.pi_loop_invoked: false`
- `evidence.codexify_ingestion_performed: false`
- `evidence.durable_mutation_performed: false`
- `evidence.source_mutation_performed: false`
- `evidence.approval_granted: false`

## 17. Write-Flag Absence

No write flags were used:

- `inline_result.evidence_paths.validation_receipt_path`: null
- `inline_result.evidence_paths.orchestration_log_path`: null
- `inline_result.evidence_paths.orchestration_receipt_path`: null
- No `--write-receipt`, `--write-orchestration-log`, or `--write-orchestration-receipt` in the command
- Adapter rejected write flags at the command construction layer (as proven in adapter tests)

## 18. What This Proof Establishes

This proof establishes that:

- the command-bus bridge successfully invoked `orchestrate_dry_run_preflight` through module invocation
- the selected validation receipt path was accepted and verified
- all 12 preconditions were met (Plan Pack exists, receipt valid, authority locks false, manifest hashes match, etc.)
- all 8 Plan Pack file hashes matched between the receipt's manifest and live files
- the orchestration declared itself as dry-run only: `orchestration_record_only: true`
- no execution occurred: `execution_performed: false`
- no Pi Loop was invoked: `pi_loop_invoked: false`
- no source mutation occurred
- no Codexify ingestion occurred
- all nine authority locks remained false
- the four-line boundary label was returned exactly
- no write evidence paths were produced

## 19. What This Proof Does Not Establish

This proof does not establish:

- Pi Loop invocation capability
- plan execution capability
- source mutation authorization
- patch application authorization
- provider execution authorization
- Codexify ingestion authorization
- write-flag support (write flags remain rejected by the adapter)
- UI support
- release support expansion
- that orchestration preflight success = plan execution authority

This proof does not add UI support. No Guardian UI panel exists for this bridge.

## 20. Failure or Blocked Interpretation

Interpretation: **PASS**.

No failure or blocked conditions encountered. All preflight checks passed. The orchestration dry-run ran to completion with all preconditions met.

This is dry-run preparation only — no execution occurred.

## 21. Future Post-Orchestration Slices

Future slices beyond this proof remain deferred. Any post-orchestration work would require separate contracts for:

- Codexify ingestion
- Execution Ledger writes
- WorkOrder mutation
- Plan execution (requires Chris-approved Pi Loop contract)
- Source mutation
- UI integration

None of these are authorized by this proof.

## 22. Forbidden Interpretations

Do not interpret this proof as meaning:

- Pi Loop invocation is authorized
- plan execution is authorized
- source mutation is authorized
- the orchestration result is execution authority
- the orchestration result is dispatch authority
- the selected receipt was ingested or trusted
- any Codexify durable record was created beyond command-bus run/event records
- Guardian UI integration is shipped
- write flags are supported

## 23. Bottom Line

This branch adds the first live dry-run orchestration preflight proof for the Guardian Codex Runner command-bus bridge.

The proof result is **PASS**.

The Codex Runner orchestrate-dry-run confirmed all 12 preconditions were met: the Plan Pack exists, the receipt is valid, authority locks remain false, manifest hashes match, and both authorization and boundaries allow dry-run orchestration. No execution, no Pi Loop invocation, no source mutation, and no Codexify ingestion occurred.

The validate and orchestrate preflight bridge commands are now both live-proven through the command-bus bridge using module invocation and the read-only Codex Runner mount.
