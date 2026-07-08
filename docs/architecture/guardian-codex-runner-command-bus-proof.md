# Guardian Codex Runner Command-Bus Proof

> Classification: proof packet
> Status: controlled, repeatable, backend-only operator proof
> Scope: command-bus lifecycle wiring and bridge boundary preservation only

Last updated: 2026-07-08

## 1. Purpose

This note is the first operator-proof packet for the Guardian Codex Runner command-bus bridge.

It exists to prove, in a controlled and repeatable way, that Codexify's two internal Guardian bridge commands can run through the command-bus lifecycle while preserving the bridge boundaries.

## 2. Status

This is a controlled operator proof, not live Codex Runner proof.

Automated tests must not execute real `codexrun`.

Live validate proof is separate operator evidence at `docs/architecture/guardian-codex-runner-command-bus-live-validate-proof.md`.

A retry live validate proof packet exists at [`guardian-codex-runner-command-bus-live-validate-retry-proof.md`](./guardian-codex-runner-command-bus-live-validate-retry-proof.md). The retry proof is separate operator evidence.

Controlled proof remains the automated proof packet.

Live orchestration proof remains deferred.

## 3. Scope

This proof covers only:

- internal command-bus invocation for the two Guardian bridge commands
- command-bus run creation, lifecycle events, completion, and failure handling
- backend-owned adapter dispatch through controlled mocked responses
- preservation of bridge authority locks and boundary posture

This proof does not add:

- a new API route
- a frontend panel
- a UI trigger
- write flags
- receipt writing
- orchestration log writing
- orchestration receipt writing
- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- Codexify ingestion
- durable truth beyond ordinary command-bus run/event records

## 4. Proof Class

Proof class: controlled operator proof.

The proof validates command-bus lifecycle wiring and bridge boundary preservation only.

The proof is intentionally adapter-mocked and must remain controlled.

## 5. Current Truth

Current truth for this slice:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify now has a typed bridge contract module, a JSON-only adapter, and internal command-bus exposure for two preflight bridge commands.
- This proof adds documentation and controlled tests only.
- This proof must not be read as shipped Guardian UI integration.

## 6. What This Proof Establishes

This proof establishes that:

- the internal command IDs are present and documented
- the two bridge commands are invokable through the existing command-bus invoke path
- internal bridge commands complete through normal command-bus run/event persistence
- adapter-returned `pass` and `fail` responses complete runs with `inline_result`
- adapter exceptions produce failed runs
- internal bridge commands do not use loopback HTTP
- raw route-backed commands still use loopback HTTP
- the bridge remains typed, backend-owned, JSON-only, read-only, and preflight-only
- authority locks remain false

## 7. What This Proof Does Not Establish

This proof does not establish any of the following:

- that a real Plan Pack exists
- that the Codex Runner CLI is installed or available
- that live validation succeeded
- that live orchestration succeeded
- that a validation receipt is execution authority
- that an orchestration receipt is dispatch authority
- that a hash match proves correctness
- that any UI exists
- that any new API route exists
- that write flags are enabled
- that Pi Loop invocation exists
- that source mutation exists
- that Codexify ingestion exists
- that durable truth exists beyond ordinary command-bus run/event records

## 8. Internal Command IDs

- `internal::guardian.codex_runner.validate_plan_pack`
- `internal::guardian.codex_runner.orchestrate_dry_run_preflight`

Required bridge boundary label:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 9. Controlled Proof Path

Controlled proof path:

1. Build an invoke payload for one of the internal command IDs.
2. Send it through the existing command-bus invoke route.
3. Monkeypatch the backend bridge adapter entrypoint to return a controlled `GuardianBridgeResponse`.
4. Confirm the run lifecycle reaches `completed` for adapter `pass` or adapter `fail`.
5. Confirm the run lifecycle reaches `failed` for adapter exceptions.
6. Confirm loopback HTTP is skipped for internal bridge commands.
7. Confirm raw route-backed commands still use loopback HTTP.

No automated test in this packet may execute real `codexrun`.

## 10. Example Command-Bus Invoke Payloads

Validate example payload:

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
      "requested_by": "operator-proof",
      "correlation_id": "guardian-bridge-proof-validate"
    }
  }
}
```

Orchestrate example payload:

```json
{
  "invoke_version": "1.0",
  "command_id": "internal::guardian.codex_runner.orchestrate_dry_run_preflight",
  "actor": {
    "kind": "human",
    "id": "operator"
  },
  "arguments": {
    "body": {
      "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
      "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example-validation-receipt.json",
      "requested_by": "operator-proof",
      "correlation_id": "guardian-bridge-proof-orchestrate"
    }
  }
}
```

## 11. Expected Command-Bus Lifecycle

Expected response fields:

- `run_id`
- `status`
- `invoke_version`
- `manifest_version`
- `events_url`
- `inline_result`

Expected lifecycle for controlled adapter `pass` or controlled adapter `fail`:

1. `run.created`
2. `run.started`
3. `run.completed`

Expected lifecycle for adapter exception:

1. `run.created`
2. `run.started`
3. `run.failed`

## 12. Expected Boundary Fields

Expected `inline_result` fields:

- `command_kind`
- `result`
- `reason`
- `stdout_text`
- `json_payload`
- `evidence_paths`
- `authority`
- `boundary_label`
- `correlation_id`
- `adapter_version`

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

Expected boundary interpretation:

- response mode is forced to JSON
- write flags remain false
- evidence artifacts remain evidence only

## 13. Failure Interpretation

Interpret failures narrowly:

- `completed` plus `inline_result.result = "fail"` means the bridge returned a valid controlled failure payload
- `failed` means the adapter raised an exception or the command-bus lifecycle failed before completion
- neither case proves live Codex Runner behavior
- neither case authorizes execution, dispatch, merge, ingestion, or mutation

## 14. Operator Review Checklist

- confirm both internal command IDs are present
- confirm the four-line boundary label appears exactly
- confirm the proof is labeled controlled and not live Codex Runner proof
- confirm the proof says automated tests must not execute real `codexrun`
- confirm the example payloads use the documented internal command IDs
- confirm all authority locks are false
- confirm internal bridge commands bypass loopback HTTP
- confirm raw route-backed commands still use loopback HTTP
- confirm no UI, no new API route, and no write flags were added

## 15. Future Live-Proof Slice

A future live-proof slice may exist later, but it must be separate from this packet.

That future slice would need human-run evidence for:

- real `codexrun` availability
- real Plan Pack inputs
- live validation output
- live orchestration preflight output
- explicit evidence capture attached outside this controlled automated proof

## 16. Forbidden Interpretations

Do not interpret this proof as any of the following:

- live Codex Runner execution proof
- shipped Guardian UI support
- release support expansion
- API-route expansion
- permission to enable write flags
- permission to invoke Pi Loop
- permission to mutate source
- permission to ingest evidence into Codexify
- permission to create durable truth beyond command-bus run/event records

## 17. Bottom Line

This packet proves the Guardian Codex Runner command-bus bridge wiring in a controlled way.

It proves backend command-bus lifecycle integration and boundary preservation only.

It does not prove live Codex Runner execution.
