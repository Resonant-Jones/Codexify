# Guardian Codex Runner Command-Bus Live Validate Mounted Proof

> Classification: live operator proof
> Status: FAIL
> Scope: validate-only live operator evidence using the opt-in read-only Codex Runner mount

Last updated: 2026-07-08

## 1. Purpose

This note records a live operator proof attempt for the Guardian Codex Runner command-bus bridge validate path, this time using the opt-in Docker Compose override (`docker-compose.codex-runner-bridge.yml`) that mounts Codex Runner read-only into the backend container.

The goal remains narrow: prove that Codexify can invoke `internal::guardian.codex_runner.validate_plan_pack` through the existing command-bus route against the real Codex Runner sample Plan Pack, with the host checkout visible inside the backend container.

## 2. Status

Status: **FAIL**

Live proof attempt timestamp: `2026-07-09T00:22:19+00:00`

Reason: the Codex Runner bridge adapter failed because the `codexrun` binary was not found on PATH inside the Docker container (`[Errno 2] No such file or directory: 'codexrun'`). The filesystem visibility gap is resolved—the mount is working and Codex Runner is visible at `/Volumes/Dev_SSD/Codex-Runner`—but the `codexrun` CLI binary itself is not installed inside the container runtime.

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

Proof class: live validate-only operator proof (mounted).

This proof uses the opt-in read-only Codex Runner container visibility override and is separate from the controlled automated proof packet, the first blocked live validate proof, and the failed retry proof.

## 5. Relation to Prior Proofs

| Proof | Status | Root Cause |
|---|---|---|
| `guardian-codex-runner-command-bus-live-validate-proof.md` | BLOCKED | Backend unreachable on `localhost:8888` |
| `guardian-codex-runner-command-bus-live-validate-retry-proof.md` | FAIL | Codex Runner path `/Volumes/Dev_SSD/Codex-Runner` not visible inside Docker container |
| This proof (mounted) | FAIL | `codexrun` binary not found on PATH inside Docker container |

The container visibility contract (`guardian-codex-runner-container-visibility-contract.md`) addressed the filesystem visibility gap that caused the retry proof to fail. This proof confirms the mount works—Codex Runner is visible at the expected path—but exposes the next requirement: the `codexrun` CLI binary must be available inside the backend container.

## 6. Prerequisites Checked

Branch at proof time:

- branch: `codex/guardian-bridge-mounted-live-validate-proof`
- HEAD commit: `9db72b06a516c469100251f176a522cadc0d9d14`

Prerequisite results:

- local Codexify backend reachable on `http://localhost:8888`: yes
- command-bus route `/api/guardian/commands/invoke` reachable: yes
- `GUARDIAN_API_KEY` loaded without printing the key: yes (via `scripts/dev/dev-key.sh`)
- Codex Runner path exists at `/Volumes/Dev_SSD/Codex-Runner` (host): yes
- Codex Runner path visible inside the backend container: yes (mount validated via `docker compose exec backend test -d ...`)
- Sample Plan Pack path visible inside the backend container: yes
- sample Plan Pack exists at `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack` (host): yes
- `codexrun` binary available inside the backend container: **no**

## 7. Current Truth

Current truth preserved during this attempt:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify has a typed bridge contract module, a JSON-only adapter, internal command-bus exposure for two preflight bridge commands, controlled proof tests, one blocked live validate proof, one failed retry proof, and an opt-in local Docker read-only Codex Runner visibility override.
- This slice adds mounted validate-only live evidence using that opt-in override.
- This slice does not prove live orchestration.
- This slice does not prove Guardian UI integration.
- This slice does not ingest evidence into Codexify as durable architectural truth.

## 8. Backend Startup With Override

The backend was started with the opt-in compose override plus the existing whooshd-smoke override to satisfy the supported profile contract:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml up -d --force-recreate backend
```

Backend reached healthy state after startup.

## 9. Mount Validation

Mount validation inside the backend container:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml exec backend test -d /Volumes/Dev_SSD/Codex-Runner
```

Result: exit code 0 — Codex Runner visible inside the container.

Sample Plan Pack validation:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml exec backend test -d /Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack
```

Result: exit code 0 — Sample Plan Pack visible inside the container.

## 10. Live Command Invoked

Live command ID invoked:

- `internal::guardian.codex_runner.validate_plan_pack`

Invoke via existing route:

```
POST http://localhost:8888/api/guardian/commands/invoke
```

The command was found in the manifest and dispatched to the internal bridge adapter. The command-bus lifecycle created a run, started execution, and then failed with an adapter exception because `codexrun` was not found on PATH.

## 11. Payload Used

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
      "requested_by": "operator-live-proof-mounted",
      "correlation_id": "guardian-bridge-live-validate-mounted"
    }
  },
  "idempotency_key": "guardian-bridge-live-validate-mounted-proof-v2",
  "provenance_json": {
    "proof_class": "live_validate_only_mounted",
    "source": "docs/architecture/guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
  }
}
```

Note: `actor.id` was set to `local` to match the auth subject of the local Docker Compose backend. The first attempt with `actor.id = "operator"` returned `actor_claim_not_permitted`; the `idempotency_key` was bumped to `v2` for the corrected payload.

## 12. Observed Response

Invoke response:

```json
{
    "run_id": "run_3eeacbd5996d49f3",
    "status": "failed",
    "invoke_version": "1.0",
    "manifest_version": "1.0",
    "events_url": "/api/guardian/commands/runs/run_3eeacbd5996d49f3/events?after_seq=0",
    "error": "[Errno 2] No such file or directory: 'codexrun'",
    "policy_warnings": []
}
```

Key observations:

- run_id was produced: `run_3eeacbd5996d49f3`
- status: `failed` (not `completed`)
- no `inline_result` was returned
- error: `[Errno 2] No such file or directory: 'codexrun'` — `codexrun` not on PATH inside container

## 13. Observed Run Record

Run record:

```json
{
    "run_id": "run_3eeacbd5996d49f3",
    "command_id": "internal::guardian.codex_runner.validate_plan_pack",
    "status": "failed",
    "actor_kind": "human",
    "actor_id": "local",
    "auth_subject": "local",
    "invoke_version": "1.0",
    "idempotency_key": "guardian-bridge-live-validate-mounted-proof-v2",
    "result_json": null,
    "error_text": "[Errno 2] No such file or directory: 'codexrun'",
    "created_at": "2026-07-09T00:22:19.365401+00:00",
    "started_at": "2026-07-09T00:22:19.377172+00:00",
    "ended_at": "2026-07-09T00:22:19.388220+00:00"
}
```

Key observations:

- command_id confirmed: `internal::guardian.codex_runner.validate_plan_pack`
- result_json: null (no adapter response produced — `codexrun` not found)
- lifecycle timestamps show rapid fail (~11ms from start to end)
- the adapter raised an exception before reaching the `subprocess.run` call because `codexrun` wasn't found

## 14. Observed Events

Expected lifecycle from the run status (`failed`):

1. `run.created`
2. `run.started`
3. `run.failed`

The events endpoint is a Server-Sent Events (SSE) stream and was not inspected as a JSON body. The run record provides sufficient lifecycle evidence.

## 15. Boundary Fields Observed

No bridge boundary fields were observed in the live response because the adapter raised an exception before producing a `GuardianBridgeResponse`. The adapter failed at the `subprocess.run` call because `codexrun` was not found on PATH.

Required bridge boundary label for future successful live proof:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 16. Authority Locks Observed

No live authority block was observed because the adapter failed before producing a response.

Expected authority block:

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

## 17. What This Proof Establishes

This failed proof establishes that:

- the local Codexify backend was reachable at proof time
- the opt-in compose override was used and the backend started successfully
- the Codex Runner host path is visible inside the backend container at `/Volumes/Dev_SSD/Codex-Runner`
- the sample Plan Pack is visible inside the backend container
- the command-bus route was available and accepted the invoke request
- the internal command `internal::guardian.codex_runner.validate_plan_pack` was found in the manifest
- the command-bus lifecycle ran to completion (run.created → run.started → run.failed)
- the adapter advanced past the filesystem visibility check (the previous blocker) but failed because `codexrun` is not available on PATH inside the Docker container
- the error message is accurate and surfaced through the command-bus error field
- the container visibility contract (`docker-compose.codex-runner-bridge.yml`) works as designed

## 18. What This Proof Does Not Establish

This proof does not establish:

- a successful live validate response
- live adapter boundary fields
- live authority locks observed
- live orchestration proof
- write-flag support
- UI support
- Codexify ingestion
- durable truth beyond ordinary command-bus run/event records
- that `codexrun` is available inside the Docker container

## 19. Failure Interpretation

Interpretation: **FAIL**.

The failure is an adapter-level binary-availability gap:

- Codex Runner exists on the host and is visible inside the container: yes
- The container mount contract works: yes
- `codexrun` is not installed on PATH inside the Docker container: yes

This is NOT a:

- bridge contract failure
- command-bus lifecycle failure
- manifest registration failure
- authentication failure
- Plan Pack validity failure
- container visibility failure
- Codex Runner CLI failure (the CLI was never reached)

To fix this failure would require either:

- installing `codexrun` inside the Docker container image
- running the backend natively outside Docker (where `codexrun` is available on the host PATH)
- adding `codexrun` to the container via a Dockerfile change or volume mount of the binary

These are outside the scope of this proof task.

**Follow-up:** The executable availability gap is now addressed by an opt-in module invocation seam in the bridge adapter (`guardian/codex_runner_bridge/adapter.py`). The adapter supports `CODEXRUN_INVOCATION_MODE=module` which uses `python -m codex_runner` through the mounted source checkout instead of requiring a global `codexrun` binary.

A module live validate proof was run combining all three resolved seams. Result: [`PASS`](./guardian-codex-runner-command-bus-live-validate-module-proof.md) — `python -m codex_runner` through the mounted checkout produced a successful `validate-plan-pack` response.

This mounted proof remains FAIL and must not be retroactively reclassified. The module proof is a separate, forward evidence artifact.

See [`guardian-codex-runner-container-visibility-contract.md`](./guardian-codex-runner-container-visibility-contract.md), section 15 for the executable availability contract.

## 20. Future Orchestration Live-Proof Slice

Live orchestration proof remains deferred.

A future orchestration slice would require, at minimum:

- a successful live validate proof (i.e., `codexrun` available inside the backend container)
- a real validation receipt path
- an explicit separate proof attempt for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- continued prohibition on write flags in this bridge slice unless separately approved

## 21. Forbidden Interpretations

Do not interpret this failed proof as:

- a live validate pass
- a live orchestration pass
- proof that the bridge contract is broken
- proof that the command-bus lifecycle is broken
- proof that the container visibility contract is broken (it works)
- shipped Guardian UI support
- permission to enable write flags
- permission to write receipts
- permission to invoke Pi Loop
- permission to mutate source
- permission to ingest evidence into Codexify
- permission to create durable truth beyond command-bus run/event records

## 22. Bottom Line

This branch adds the mounted validate-only live proof packet for the Guardian Codex Runner command-bus bridge.

The proof result is **FAIL** because the `codexrun` binary was not found on PATH inside the Docker container.

The container visibility contract works: Codex Runner is visible at `/Volumes/Dev_SSD/Codex-Runner` inside the backend container. The filesystem visibility gap from the retry proof is resolved. The next gap is `codexrun` binary availability inside the container runtime.

No live validate pass is claimed. No live orchestration pass is claimed.
