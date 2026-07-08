# Guardian Codex Runner Preflight Bridge Contract

> Classification: architecture contract
> Status: docs-only, normative for future Codexify-side bridge planning
> Scope: docs/contract only

Last updated: 2026-07-08

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/system-overview.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/config-and-ops.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- /Volumes/Dev_SSD/Codex-Runner/docs/guardian/GUARDIAN_UI_COMMAND_SURFACE_CONTRACT_V0.md

## 1. Purpose

This contract defines the Codexify-side architecture boundary for a future bridge from Codexify Guardian UI through a Codexify backend-owned command surface into the existing Codex Runner Guardian preflight CLI.

The purpose is to mirror the upstream Codex Runner bridge contract inside Codexify's architecture corpus so future backend or UI work has a local governing note before any adapter, route, command-bus command, or subprocess invocation exists.

This task is docs-only. It does not implement runtime behavior.

## 2. Status

Current status:

- Codex Runner already implements local CLI Guardian preflight tools.
- Codexify now exposes those tools through an internal backend command-bus layer, but not through UI or a new API route.
- This contract is architecture-impacting because it defines a future control-plane seam across the Codexify backend boundary.
- This contract does not add shipped runtime behavior, release support, or operator authority.

Implementation status note:

- a backend contract module now exists at `guardian/codex_runner_bridge/contracts.py`
- typed request/response/authority/path validation helpers now exist
- a backend JSON-only adapter now exists for `validate-plan-pack` and `orchestrate-dry-run` preflight
- internal command-bus command specs now exist for `internal::guardian.codex_runner.validate_plan_pack` and `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- the bridge remains backend-owned, JSON-only, read-only, and preflight-only
- the adapter forces JSON mode
- the adapter does not support write flags yet
- command-bus run/event persistence may record invocation metadata
- no API route exists
- no UI exists
- no write flags exist
- no Pi Loop invocation exists
- no Codexify ingestion exists
- no source mutation exists
- no durable mutation exists beyond ordinary command-bus run/event records

Controlled proof note:

- the operator proof packet lives at `docs/architecture/guardian-codex-runner-command-bus-proof.md`
- the proof packet is controlled and does not prove live Codex Runner execution
- live proof remains a future separate slice

Implementation/proof-status note:

- a live validate-only command-bus proof document now exists at `docs/architecture/guardian-codex-runner-command-bus-live-validate-proof.md`
- it does not prove live orchestration
- it does not enable write flags
- it does not add UI support
- it does not add Codexify ingestion

Required boundary label for any future bridge surface:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 3. Scope

This contract governs only the future Codexify-side bridge shape for exposing Codex Runner Guardian preflight evidence to a future Codexify Guardian UI.

It covers:

- backend-owned invocation posture
- typed operation names
- request and response field expectations
- path and capability rules
- authority locks
- evidence semantics
- UI interpretation rules
- backend responsibilities

It does not implement or approve:

- backend command adapter
- API route
- command-bus command
- frontend panel
- subprocess invocation
- Codex Runner daemon
- Pi Loop invocation
- execution mode
- source mutation
- Codexify ingestion
- durable mutation
- receipt ingestion
- Execution Ledger writes
- WorkOrder mutation
- trust promotion
- reviewer auto-fill

## 4. Current Truth

What is true now:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains the local Docker Compose stack with local-only provider posture.
- Docs-only contracts do not mean shipped runtime behavior.
- Codex Runner already implements local CLI Guardian preflight tools.
- Codexify now exposes those tools through an internal backend command-bus layer, but still not through UI or a new API route.
- Codexify already has a backend command/tooling layer, and this task adds typed internal command-bus exposure for the JSON-only bridge.
- Guardian evidence artifacts remain evidence, not approval or durable truth.

What is not yet true:

- No Codexify Guardian UI button exists for Codex Runner preflight.
- No Codex Runner daemon/service is integrated with Codexify.
- No Codexify HTTP route invokes `codexrun guardian` commands.
- No public or UI surface exposes the internal command-bus bridge commands.
- No Codexify durable record ingests Guardian receipts.
- No Guardian path invokes Pi Loop from Codexify.

## 5. Non-Goals

This contract does not:

- widen the supported beta surface
- claim that UI integration is shipped
- add runtime semantics
- create new canonical runtime tokens
- redefine command-bus semantics
- redefine Pi invocation governance
- promote evidence artifacts into durable truth
- authorize Codexify ingestion
- authorize execution authority

## 6. Relationship to Codex Runner

The upstream boundary source is:

- `/Volumes/Dev_SSD/Codex-Runner/docs/guardian/GUARDIAN_UI_COMMAND_SURFACE_CONTRACT_V0.md`

Codex Runner owns the implemented local CLI preflight surface:

- `validate-plan-pack`
- validation receipt writing
- `orchestrate-dry-run`
- orchestration log and orchestration receipt writing

Codexify does not redefine those semantics. This contract mirrors them for the Codexify-side boundary only.

Upstream bridge truths that must be preserved:

- the bridge is preflight-only
- frontend must not shell out
- typed operations only, not arbitrary command strings
- evidence artifacts remain local evidence, not approval
- a validation receipt is not execution authority
- an orchestration receipt is not dispatch
- a hash match proves file continuity, not correctness

## 7. Relationship to Codexify

Within Codexify, this contract sits beside the current backend control-plane seams:

- FastAPI backend boundary
- command bus/tooling layer
- runtime/auth/config posture
- current Guardian UI/browser shell

This note does not claim those seams already invoke Codex Runner.

It only defines how a future Codexify backend-owned bridge should look if implemented later:

```txt
Guardian UI
  -> Codexify backend command surface
  -> Codex Runner Guardian preflight CLI
  -> local evidence artifacts
```

## 8. Proposed Bridge Shape

The smallest acceptable future bridge shape is:

```txt
Codexify Guardian UI
  -> backend-owned typed operation
  -> validated Codex Runner path inputs
  -> bounded Codex Runner Guardian preflight command
  -> returned text/json plus artifact paths
```

The smallest future UI slice is trigger-plus-read only.

The future bridge must remain:

- backend-owned
- preflight-only
- typed
- bounded by allowlisted operations
- explicit about authority locks

## 9. Recommended Adapter Posture

Recommended order:

1. command-bus adapter
2. local service boundary
3. thin backend route delegating to one of the two shapes above

Preferred posture:

- The backend should prefer a command-bus adapter or local service boundary over ad hoc route shelling.
- The backend must own command invocation.
- The backend must not expose arbitrary shell command execution.
- The frontend must not shell out.

## 10. Typed Operation Model

The future bridge must expose typed operations only:

- `guardian.validate_plan_pack`
- `guardian.write_validation_receipt`
- `guardian.orchestrate_dry_run_preflight`
- `guardian.write_orchestration_evidence`
- `guardian.list_evidence_for_plan_pack`

Interpretation rules:

- These are operation identifiers, not proof that a command exists in Codexify today.
- They define the future adapter vocabulary for the bridge.
- They must not be replaced by freeform shell command strings from the frontend.

## 11. Request Fields

Required request fields:

```yaml
operation:
plan_pack_path:
validation_receipt_path:
write_receipt:
write_orchestration_log:
write_orchestration_receipt:
response_mode:
requested_by:
correlation_id:
```

Field intent:

- `operation`: one allowlisted typed operation name
- `plan_pack_path`: candidate Codex Runner plan-pack path
- `validation_receipt_path`: candidate Codex Runner validation receipt path when required
- `write_receipt`: request that validation evidence be written
- `write_orchestration_log`: request that orchestration log evidence be written
- `write_orchestration_receipt`: request that orchestration receipt evidence be written
- `response_mode`: `text` or `json`
- `requested_by`: caller identity or operator/session label for auditability
- `correlation_id`: stable request correlation handle for UI/backend tracing

## 12. Response Fields

Required response fields:

```yaml
command_kind:
result:
reason:
stdout_text:
json_payload:
evidence_paths:
authority:
boundary_label:
correlation_id:
adapter_version:
```

Response intent:

- `command_kind`: normalized command family such as `validate_plan_pack` or `orchestrate_dry_run`
- `result`: `pass` or `fail`
- `reason`: bounded reason string
- `stdout_text`: rendered CLI output when the caller requests or benefits from text
- `json_payload`: machine-readable payload when `response_mode=json`
- `evidence_paths`: returned local artifact paths only
- `authority`: explicit hard-false authority block
- `boundary_label`: exact preflight-only boundary label
- `correlation_id`: echo of the request correlation handle
- `adapter_version`: bridge-adapter version string once an adapter exists

## 13. Path and Capability Rules

The future backend bridge must enforce all of the following:

- `plan_pack_path` must resolve inside `/Volumes/Dev_SSD/Codex-Runner`
- `validation_receipt_path` must resolve inside `/Volumes/Dev_SSD/Codex-Runner`
- no path may resolve inside `/Volumes/Dev_SSD/Codexify-main` for Codex Runner evidence execution
- no path may resolve inside `/Volumes/Dev_SSD/ResonantConstructs/Codexify-Core`
- all paths must be normalized before evaluation
- symlink escapes must be rejected
- frontend-provided paths must be treated as hostile until checked

Capability rules:

- the backend must allow only the typed Guardian preflight operations in this contract
- the backend must enforce path allowlists, timeouts, output limits, and exit-code interpretation
- the backend must reject freeform shell input

## 14. Authority Locks

The future bridge must surface this exact hard-false authority block:

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

All authority locks must remain false.

No future UI or backend interpretation may promote these values implicitly.

## 15. Evidence Semantics

The evidence rules are fixed:

- Guardian validation receipts are evidence, not approval.
- Guardian orchestration receipts are evidence, not dispatch.
- Codex Runner evidence paths are local artifacts, not Codexify durable records.
- Returning an evidence path to Codexify does not ingest that evidence.
- Showing an artifact in the UI does not promote it to durable truth.
- A future ingestion path requires a separate Codexify-side adoption contract.

Additional evidence interpretation:

- a validation receipt is not execution authority
- an orchestration receipt is not dispatch
- a hash match proves file continuity, not correctness

## 16. UI Interpretation Rules

The future UI rules are:

- The smallest future UI slice is trigger-plus-read only.
- The UI may render returned JSON and artifact paths.
- The UI must display authority locks as false.
- The UI must not imply execution.
- The UI must not edit Plan Pack files in V1.
- The UI must not create Codexify records from Guardian evidence in V1.

The UI must display this exact boundary label:

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 17. Backend Responsibility

The backend responsibilities are:

- The backend must own command invocation.
- The backend must not expose arbitrary shell command execution.
- The backend must use typed operations and validated arguments.
- The backend must enforce path allowlists, timeouts, output limits, and exit-code interpretation.
- The backend should prefer a command-bus adapter or local service boundary over ad hoc route shelling.

Additional backend obligations:

- preserve the current auth/exposure boundary
- keep auditability tied to `requested_by` and `correlation_id`
- fail closed when path or authority checks do not pass

## 18. Failure Modes

Key failure modes and required posture:

1. Stale or mismatched validation receipt.
   - Fail closed; do not imply preflight readiness.
2. Path escape, symlink escape, or wrong repo root.
   - Reject before invocation.
3. Frontend sends unsupported typed operation.
   - Reject with bounded error; do not downgrade to shell passthrough.
4. UI interprets a successful preflight as execution.
   - Prevent through boundary label, explicit hard-false authority block, and non-goal wording.
5. Backend timeout or oversized output from subprocess/service boundary.
   - Bound timeout and output capture; return structured failure.
6. Evidence path is shown in UI and mistaken for ingestion.
   - Keep evidence semantics explicit: path return is not durable record creation.

## 19. Security and Trust Boundaries

Nodes:

- frontend Guardian UI
- Codexify backend
- Codex Runner local process or future local service
- local filesystem under `/Volumes/Dev_SSD/Codex-Runner`

Trust boundaries:

- browser boundary is untrusted for command invocation
- backend boundary is trusted to validate and constrain operations
- Codex Runner boundary is trusted only for bounded preflight semantics
- filesystem paths are untrusted inputs until normalized and checked

Threat model:

- honest-but-buggy UI
- honest-but-buggy backend adapter
- malicious local caller attempting path or authority escalation
- stale evidence accidentally represented as fresh truth

## 20. Future Implementation Slices

Recommended future slices:

1. this Codexify-side mirror contract
2. one backend-owned typed adapter for `guardian.validate_plan_pack`
3. one backend-owned typed adapter for `guardian.orchestrate_dry_run_preflight`
4. read-only artifact listing surface
5. trigger-plus-read Guardian UI panel

Deferred beyond this contract:

- execution mode
- Pi Loop invocation
- source mutation
- Codexify ingestion
- durable mutation
- receipt adoption into Codexify records
- Execution Ledger writes
- WorkOrder mutation

## 21. Forbidden Interpretations

Do not interpret this contract as meaning:

- the bridge is already implemented
- the UI integration is shipped
- a returned evidence path creates a Codexify record
- a displayed receipt becomes durable truth
- a validation receipt grants execution authority
- an orchestration receipt is dispatch
- Codexify may ingest Guardian evidence automatically
- Pi Loop may be invoked from Codexify
- command bus or backend route work is approved without a separate implementation task

## 22. Review Checklist

- [ ] The document stays docs-only.
- [ ] `00-current-state.md` remains the release-truth override.
- [ ] No new runtime behavior is claimed.
- [ ] No backend adapter is implied as already present.
- [ ] No UI panel is implied as already present.
- [ ] The bridge is explicitly backend-owned.
- [ ] Typed operations are listed and freeform shell input is rejected.
- [ ] Path rules preserve Codex Runner-only evidence execution.
- [ ] Authority locks remain hard-false.
- [ ] Evidence semantics stay non-authoritative.
- [ ] Pi Loop invocation remains forbidden.
- [ ] Codexify ingestion remains forbidden without a separate adoption contract.

## 23. Bottom Line

Codex Runner already has the altar.

Codexify does not yet have the door.

This contract defines the Codexify-side door frame only:

- backend-owned
- typed
- preflight-only
- evidence-returning
- non-ingesting
- non-executing

No runtime behavior is added by this task. No backend adapter is added. No UI panel is added. No Pi Loop invocation is added. No Codexify ingestion is added. No durable mutation is added.
