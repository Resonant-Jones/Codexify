# Guardian Codex Runner Command-Bus Live Validate Retry Proof

> Classification: live operator proof
> Status: FAIL
> Scope: retry validate-only live operator evidence for the internal command-bus bridge

Last updated: 2026-07-08

## 1. Purpose

This note records the second live operator proof attempt (retry) for the Guardian Codex Runner command-bus bridge validate path.

The goal of this slice remains narrow: prove that Codexify can invoke `internal::guardian.codex_runner.validate_plan_pack` through the existing command-bus route against the real Codex Runner sample Plan Pack.

This is a retry of the first blocked live validate proof.

## 2. Status

Status: FAIL

Live proof attempt timestamp: `2026-07-08T21:43:51+00:00`

Reason: the Codex Runner bridge adapter failed because `/Volumes/Dev_SSD/Codex-Runner` does not exist inside the Docker container running the Codexify backend. The command-bus lifecycle completed a `run.failed` event with the adapter exception. This is a host-path accessibility gap, not a bridge contract or command-bus lifecycle failure.

## 3. Container Visibility Contract

A separate opt-in local Docker container visibility contract exists to address the host-path accessibility gap that caused this proof to fail:

- [`guardian-codex-runner-container-visibility-contract.md`](./guardian-codex-runner-container-visibility-contract.md)

Key points:

- the retry proof failed because the backend container could not see the host Codex Runner checkout at `/Volumes/Dev_SSD/Codex-Runner`
- the container visibility contract defines the next opt-in mount seam via `docker-compose.codex-runner-bridge.yml`
- a mounted live validate proof attempt was run using that override: [`guardian-codex-runner-command-bus-live-validate-mounted-proof.md`](./guardian-codex-runner-command-bus-live-validate-mounted-proof.md) — **FAIL** because `codexrun` binary was not found on the container PATH
- a live validate pass remains future proof, not implied by the mount contract

## 4. Scope

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

## 5. Proof Class

Proof class: live validate-only operator proof (retry).

This proof is separate from the controlled automated proof packet and the first blocked live validate proof.

## 6. Relation to Prior Blocked Proof

The first live validate proof (`guardian-codex-runner-command-bus-live-validate-proof.md`) was BLOCKED because the local Codexify backend was unreachable on `http://localhost:8888`.

This retry proof advances past that block: the backend is reachable, the command-bus route is available, and the internal command is found in the manifest. The new failure is a host-path accessibility gap inside Docker, not a route-availability block.

## 7. Prerequisites Checked

Branch at proof time:

- branch: `codex/guardian-bridge-live-validate-retry-proof`
- HEAD commit: `a3fa670c52f4790da111f0e5ed0a5db96b39ab7d`

Prerequisite results:

- local Codexify backend reachable on `http://localhost:8888`: yes
- command-bus route `/api/guardian/commands/invoke` reachable: yes
- internal command `internal::guardian.codex_runner.validate_plan_pack` in manifest: yes (after backend restart)
- `GUARDIAN_API_KEY` loaded without printing the key: yes
- Codex Runner path exists at `/Volumes/Dev_SSD/Codex-Runner` (host): yes
- Codex Runner path exists at `/Volumes/Dev_SSD/Codex-Runner` (inside Docker): no
- sample Plan Pack exists at `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack` (host): yes

## 8. Current Truth

Current truth preserved during this attempt:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify has a typed bridge contract module, a JSON-only adapter, internal command-bus exposure for two preflight bridge commands, controlled proof tests for the command-bus lifecycle, and one prior blocked live validate proof.
- This slice adds a retry live validate-only evidence packet.
- This slice does not prove live orchestration.
- This slice does not prove Guardian UI integration.
- This slice does not ingest evidence into Codexify as durable architectural truth.

## 9. Backend Startup / Reachability

The local Codexify backend was initially reachable but the internal bridge commands were not visible in the manifest (137 commands, 0 internal). A `docker compose restart backend` resolved this; after restart the manifest returned 139 commands with 2 internal bridge commands present.

Backend reachability at proof time: `http://localhost:8888/health` returned `200`.

## 10. Live Command Invoked

Live command ID invoked:

- `internal::guardian.codex_runner.validate_plan_pack`

Invoke via existing route:

```
POST http://localhost:8888/api/guardian/commands/invoke
```

The command was found in the manifest and dispatched to the internal bridge adapter. The command-bus lifecycle created a run, started execution, and then failed with an adapter exception.

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
      "requested_by": "operator-live-proof-retry",
      "correlation_id": "guardian-bridge-live-validate-retry"
    }
  },
  "idempotency_key": "guardian-bridge-live-validate-proof-retry-v1",
  "provenance_json": {
    "proof_class": "live_validate_only_retry",
    "source": "docs/architecture/guardian-codex-runner-command-bus-live-validate-retry-proof.md"
  }
}
```

Note: `actor.id` was changed from `operator` to `local` to match the auth subject of the local Docker Compose backend.

## 12. Observed Response

Observed invoke response:

```json
{
    "run_id": "run_ecf4b99e55ee4b7f",
    "status": "failed",
    "invoke_version": "1.0",
    "manifest_version": "1.0",
    "events_url": "/api/guardian/commands/runs/run_ecf4b99e55ee4b7f/events?after_seq=0",
    "error": "[Errno 2] No such file or directory: PosixPath('/Volumes/Dev_SSD/Codex-Runner')",
    "policy_warnings": []
}
```

Key observations:

- run_id was produced: `run_ecf4b99e55ee4b7f`
- status: `failed` (not `completed`)
- no `inline_result` was returned
- error: `[Errno 2] No such file or directory: PosixPath('/Volumes/Dev_SSD/Codex-Runner')`

## 13. Observed Run Record

Run record:

```json
{
    "run_id": "run_ecf4b99e55ee4b7f",
    "command_id": "internal::guardian.codex_runner.validate_plan_pack",
    "status": "failed",
    "actor_kind": "human",
    "actor_id": "local",
    "auth_subject": "local",
    "invoke_version": "1.0",
    "idempotency_key": "guardian-bridge-live-validate-proof-retry-v1",
    "result_json": null,
    "error_text": "[Errno 2] No such file or directory: PosixPath('/Volumes/Dev_SSD/Codex-Runner')",
    "created_at": "2026-07-08T21:43:51.773511+00:00",
    "started_at": "2026-07-08T21:43:51.792237+00:00",
    "ended_at": "2026-07-08T21:43:51.802966+00:00"
}
```

Key observations:

- command_id confirmed: `internal::guardian.codex_runner.validate_plan_pack`
- result_json: null (no adapter response produced)
- error_text confirms the file-not-found exception from the adapter
- lifecycle timestamps show rapid fail (~30ms from start to end)

## 14. Observed Events

The events endpoint is a Server-Sent Events (SSE) stream and was not inspected as a JSON body. The run record itself provides sufficient lifecycle evidence.

Expected lifecycle from the run status (`failed`):

1. `run.created`
2. `run.started`
3. `run.failed`

## 15. Boundary Fields Observed

No bridge boundary fields were observed in the live response because the adapter raised an exception before producing a `GuardianBridgeResponse`.

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
- the command-bus route was available and accepted the invoke request
- the internal command `internal::guardian.codex_runner.validate_plan_pack` was found in the manifest
- the command-bus lifecycle ran to completion (run.created → run.started → run.failed)
- the adapter attempted to execute but failed because `/Volumes/Dev_SSD/Codex-Runner` is not accessible from inside the Docker container
- the error message is accurate and surfaced through the command-bus error field

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

## 19. Failure or Blocked Interpretation

Interpretation: FAIL.

The failure is an adapter-level host-path accessibility gap:

- Codex Runner exists on the host at `/Volumes/Dev_SSD/Codex-Runner`
- The Codexify backend runs inside Docker and cannot access that host path
- The adapter's `subprocess.run(cwd=CODEX_RUNNER_ROOT)` fails because the working directory doesn't exist inside the container

This is NOT a:

- bridge contract failure
- command-bus lifecycle failure
- manifest registration failure
- authentication failure
- Plan Pack validity failure
- Codex Runner CLI failure

To fix this failure would require either:

- mounting the Codex Runner host path into the Docker container (a Docker Compose volume mount change)
- or running the backend natively outside Docker (a deployment change)

Both are outside the scope of this proof task.

## 20. Future Orchestration Live-Proof Slice

Live orchestration proof remains deferred.

A future orchestration slice would require, at minimum:

- a successful live validate proof (i.e., the host-path gap resolved)
- a real validation receipt path
- an explicit separate proof attempt for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- continued prohibition on write flags in this bridge slice unless separately approved

## 21. Forbidden Interpretations

Do not interpret this failed proof as:

- a live validate pass
- a live orchestration pass
- proof that the bridge contract is broken
- proof that the command-bus lifecycle is broken
- shipped Guardian UI support
- permission to enable write flags
- permission to write receipts
- permission to invoke Pi Loop
- permission to mutate source
- permission to ingest evidence into Codexify
- permission to create durable truth beyond command-bus run/event records

## 22. Bottom Line

This branch adds the retry live validate-only proof packet for the Guardian Codex Runner command-bus bridge.

The proof result is FAIL because the Codex Runner path `/Volumes/Dev_SSD/Codex-Runner` is not accessible from inside the Docker container running the Codexify backend.

The command-bus lifecycle worked correctly: the internal command was found, dispatched, and produced a failed run with an accurate error message.

No live validate pass is claimed. No live orchestration pass is claimed.
