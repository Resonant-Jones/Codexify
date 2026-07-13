# Guardian Codex Runner Command-Bus Live Validate Proof

> Classification: live operator proof
> Status: BLOCKED
> Scope: validate-only live operator evidence for the internal command-bus bridge

Last updated: 2026-07-08

## 1. Purpose

This note records the first live operator proof attempt for the Guardian Codex Runner command-bus bridge validate path.

The goal of this slice is narrow: prove that Codexify can invoke `internal::guardian.codex_runner.validate_plan_pack` through the existing command-bus route against the real Codex Runner sample Plan Pack.

## 2. Status

Status: BLOCKED

Live proof attempt timestamp: `2026-07-08T20:42:31.123677+00:00`

Reason: the local Codexify backend was not reachable on `http://localhost:8888`, so the existing command-bus route could not be reached for a real live invoke.

A retry proof packet exists at [`guardian-codex-runner-command-bus-live-validate-retry-proof.md`](./guardian-codex-runner-command-bus-live-validate-retry-proof.md). The retry proof is separate operator evidence.

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

Proof class: live validate-only operator proof.

This proof is separate from the controlled automated proof packet.

## 5. Prerequisites Checked

Branch at proof time:

- branch: `codex/guardian-bridge-live-validate-proof`
- HEAD commit: `ed6b0afc66456f91f0b01b601e7102947cb4109b`

Prerequisite results:

- local Codexify backend reachable on `http://localhost:8888`: no
- command-bus route `/api/guardian/commands/invoke` reachable through the local backend: not reachable because backend was down or unavailable
- `GUARDIAN_API_KEY` exported in the current shell: no
- `GUARDIAN_API_KEY` available through documented local secret-loading ritual: yes, via `scripts/dev/dev-key.sh`
- Codex Runner path exists at `/Volumes/Dev_SSD/Codex-Runner`: yes
- sample Plan Pack exists at `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack`: yes

## 6. Current Truth

Current truth preserved during this attempt:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify has a typed bridge contract module, a JSON-only adapter, internal command-bus exposure for two preflight bridge commands, and controlled proof tests for the command-bus lifecycle.
- This slice adds live validate-only evidence only.
- This slice does not prove live orchestration.
- This slice does not prove Guardian UI integration.

## 7. Live Command Invoked

Live command ID intended and attempted:

- `internal::guardian.codex_runner.validate_plan_pack`

Host-side invoke shape used:

```bash
BASE=http://localhost:8888
GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)"
curl -sS \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  -X POST "$BASE/api/guardian/commands/invoke" \
  --data "$PAYLOAD"
```

Observed result of the live invoke attempt:

- curl exit code: `7`
- stderr summary: `Failed to connect to localhost port 8888`

## 8. Payload Used

Plan Pack path used:

- `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack`

Payload used:

```json
{
  "invoke_version": "1.0",
  "command_id": "internal::guardian.codex_runner.validate_plan_pack",
  "actor": {
    "kind": "human",
    "id": "operator"
  },
  "arguments": {
    "body": {
      "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
      "requested_by": "operator-live-proof",
      "correlation_id": "guardian-bridge-live-validate"
    }
  },
  "idempotency_key": "guardian-bridge-live-validate-proof-v1",
  "provenance_json": {
    "proof_class": "live_validate_only",
    "source": "docs/architecture/guardian-codex-runner-command-bus-live-validate-proof.md"
  }
}
```

## 9. Observed Response

Observed response summary:

- no HTTP response body was returned
- captured response file size: `0` bytes
- no JSON response could be inspected
- no command-bus completion status was observed

Final host-side transport observation:

- `curl: (7) Failed to connect to localhost port 8888 after 0 ms: Couldn't connect to server`

## 10. Observed Run Record

Observed run record:

- run_id: none
- command-bus run record lookup: not possible because no response payload and no run_id were produced

## 11. Boundary Fields Observed

No bridge boundary fields were observed from a live command response because the route was not reachable.

Required bridge boundary label for future successful live proof:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 12. Authority Locks Observed

No live authority block was observed because the route was not reachable.

Expected authority block for a future successful live validate proof:

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

## 13. What This Proof Establishes

This blocked proof establishes that:

- the real Codex Runner path existed at proof time
- the real sample Plan Pack path existed at proof time
- the documented local key-loading ritual was available
- the local host-side Codexify backend was not reachable on `http://localhost:8888` at proof time
- no honest live validate pass can be claimed from this attempt

## 14. What This Proof Does Not Establish

This proof does not establish:

- a successful live validate response
- a successful live command-bus run
- any live boundary fields from the adapter response
- live orchestration proof
- write-flag support
- UI support
- Codexify ingestion
- durable truth beyond ordinary command-bus run/event records

## 15. Failure or Blocked Interpretation

Interpretation: BLOCKED.

Blocking prerequisite:

- the local Codexify backend was not reachable on the supported local base URL, so the command-bus route could not be reached

This is a route-availability block, not proof of:

- Codex Runner CLI failure
- Plan Pack invalidity
- adapter contract failure
- live command-bus response failure

## 16. Future Orchestration Live-Proof Slice

Live orchestration proof remains deferred.

A future orchestration slice would require, at minimum:

- a successful live validate proof
- a real validation receipt path
- an explicit separate proof attempt for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- continued prohibition on write flags in this bridge slice unless separately approved

## 17. Forbidden Interpretations

Do not interpret this blocked proof as:

- a live validate pass
- a live orchestration pass
- shipped Guardian UI support
- permission to enable write flags
- permission to write receipts
- permission to invoke Pi Loop
- permission to mutate source
- permission to ingest evidence into Codexify
- permission to create durable truth beyond command-bus run/event records

## 18. Bottom Line

This branch adds the first live validate-only proof packet for the Guardian Codex Runner command-bus bridge.

The proof result is BLOCKED because the local Codexify backend was not reachable on `http://localhost:8888` during the proof attempt.

A retry proof packet exists at [`guardian-codex-runner-command-bus-live-validate-retry-proof.md`](./guardian-codex-runner-command-bus-live-validate-retry-proof.md). That retry proof is separate operator evidence.

Live orchestration proof remains deferred.

No live validate pass is claimed.
