# Guardian Codex Runner Orchestration Receipt Prerequisite Contract

> Classification: architecture contract
> Status: prerequisite contract only — no orchestration proof, no receipt creation, no ingestion
> Scope: docs/contract only

Last updated: 2026-07-08

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/guardian-codex-runner-preflight-bridge-contract.md
- docs/architecture/guardian-codex-runner-command-bus-proof.md
- docs/architecture/guardian-codex-runner-command-bus-live-validate-module-proof.md
- guardian/codex_runner_bridge/contracts.py
- guardian/codex_runner_bridge/adapter.py
- guardian/codex_runner_bridge/command_bus.py

## 1. Purpose

This contract defines the explicit prerequisite for any future live orchestration proof of:

`internal::guardian.codex_runner.orchestrate_dry_run_preflight`

The validate-only live proof now passes through the command-bus bridge using module invocation. The next orchestration proof must not proceed until a validation receipt path is explicitly available, visible inside the backend container, and treated as evidence only.

This contract is prerequisite documentation — it does not execute orchestration, create receipts, or ingest evidence.

## 2. Status

Status: prerequisite contract only.

This contract does not:

- prove live orchestration
- create or write a validation receipt
- select or trust a specific receipt
- ingest any receipt into Codexify
- authorize write flags
- authorize Pi Loop invocation
- authorize plan execution
- authorize source mutation

## 3. Scope

This contract governs only the prerequisite conditions that must be met before any future live orchestration proof may proceed.

It covers:

- why orchestration requires a validation receipt
- the allowed receipt source
- receipt visibility inside the backend container
- receipt authority rules
- acceptable vs forbidden receipt states
- required preflight checks
- an example future orchestration payload (marked NOT RUN IN THIS TASK)

It does not implement or approve:

- new API route
- frontend panel
- UI trigger
- write flags
- receipt writing
- orchestration command invocation
- orchestration log writing
- orchestration receipt writing
- Codex Runner daemon/service integration
- adapter changes
- compose changes
- native backend path mode
- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- Codexify ingestion
- receipt ingestion
- Execution Ledger writes
- WorkOrder mutation
- trust promotion
- reviewer auto-fill

## 4. Triggering Evidence

The validate-only live proof (`guardian-codex-runner-command-bus-live-validate-module-proof.md`) produced a **PASS** result through the command-bus bridge for `internal::guardian.codex_runner.validate_plan_pack`:

- Run ID: `run_3e056386061d4906`
- Status: `completed`
- Result: `pass`
- All authority locks: false
- Boundary label: exact four-line label returned

With validate proven, the next bridge command is orchestrate. However, `internal::guardian.codex_runner.orchestrate_dry_run_preflight` requires a `validation_receipt_path` argument. The adapter enforces this at the command construction layer:

```python
if validated.validation_receipt_path is None:
    raise GuardianBridgeCommandError(
        "validation_receipt_path is required for orchestrate_dry_run_preflight."
    )
```

No live orchestration proof may proceed without a real, visible, operator-verified validation receipt.

## 5. Current Truth

What is true now:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- The validate-only live proof passed through the command-bus bridge using module invocation.
- The bridge adapter enforces `validation_receipt_path` as a required argument for orchestration.
- This contract documents the prerequisite, not the proof.
- This task does not create, write, select, trust, ingest, or mutate receipts.

What is not yet true:

- No live orchestration proof has been attempted.
- No validation receipt has been created or selected for orchestration use.
- No orchestration dry-run has been executed through the command-bus bridge.
- No orchestration log or receipt has been produced.

## 6. Why Orchestration Requires a Receipt

The `orchestrate_dry_run_preflight` command in Codex Runner validates a Plan Pack by reference to a previously issued validation receipt. The receipt serves as evidence that:

1. A validate-plan-pack check was previously run against the same Plan Pack.
2. The Plan Pack passed structural checks at that point in time.
3. The receipt is a local artifact — it does not itself prove the Plan Pack content is correct.

Without a receipt, the orchestration dry-run has no evidence to reference. The bridge adapter rejects `None` for `validation_receipt_path` with a command error.

## 7. Receipt Source Rule

The receipt must come from a prior Codex Runner `validate-plan-pack` run. It is a local JSON artifact.

Allowed sources:

- A receipt file present on the host filesystem under `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/`
- A receipt file generated by a prior successful validate invocation
- A receipt file visible inside the backend container through the read-only mount

This task does not select, create, or write any receipt.

## 8. Receipt Visibility Rule

The receipt path must satisfy the same visibility rules as the Plan Pack:

- Must be visible inside the backend container at its exact host path.
- Must resolve inside `/Volumes/Dev_SSD/Codex-Runner` (enforced by `validate_codex_runner_path`).
- Must not resolve inside `/Volumes/Dev_SSD/Codexify-main` or `/Volumes/Dev_SSD/ResonantConstructs/Codexify-Core`.

The read-only Codex Runner mount makes the `.guardian/receipts/` directory visible inside the backend container when it exists on the host.

## 9. Receipt Authority Rule

A validation receipt is evidence only. It does not:

- grant execution authority
- grant dispatch authority
- grant merge authority
- authorize Pi Loop invocation
- authorize plan execution
- authorize source mutation
- authorize Codexify ingestion
- authorize write flags
- promote to durable truth

Receipt existence alone is not proof that the Plan Pack is correct, only that it passed structural validation at the time the receipt was created.

## 10. Acceptable Receipt States

An acceptable operator-selected receipt for a future dry-run orchestration proof must:

1. Exist at the claimed path and be visible inside the backend container.
2. Reference the correct Plan Pack path.
3. Be generated by Codex Runner's `validate-plan-pack`.
4. Show `result: "pass"`.
5. Be structurally valid JSON.

## 11. Forbidden Receipt States

A receipt is NOT acceptable if any of the following are true:

1. The receipt file does not exist at the claimed path.
2. The receipt path is not visible inside the backend container.
3. The receipt was manually fabricated outside Codex Runner's validate-plan-pack.
4. The receipt result field is not `"pass"`.
5. The receipt JSON is malformed or truncated.
6. The receipt references a different Plan Pack than the one being orchestrated.
7. The receipt was ingested into Codexify and treated as durable truth (ingestion requires a separate adoption contract).

## 12. Required Preflight Checks

Before attempting a future live orchestration proof, the operator must verify:

1. Validate-only live proof: PASS (achieved — `guardian-codex-runner-command-bus-live-validate-module-proof.md`)
2. Backend reachable with compose override and module invocation active.
3. Codex Runner mount visible inside backend container.
4. Sample Plan Pack visible inside backend container.
5. A validation receipt exists at a known path inside `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/`.
6. The receipt is visible inside the backend container.
7. The receipt is valid JSON with `result: "pass"` and correct Plan Pack path.
8. All bridge authority locks remain false.
9. No write flags are configured.
10. The operator understands the receipt is evidence, not execution authority.

## 13. Future Live Orchestration Proof Payload

**NOT RUN IN THIS TASK. Example only.**

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
      "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/<operator-selected-validation-receipt>.json",
      "requested_by": "operator-live-orchestration-proof",
      "correlation_id": "guardian-bridge-live-orchestration-proof"
    }
  },
  "idempotency_key": "guardian-bridge-live-orchestration-proof-v1",
  "provenance_json": {
    "proof_class": "live_orchestration_dry_run",
    "source": "<future-orchestration-proof-doc>.md"
  }
}
```

The placeholder receipt path `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/<operator-selected-validation-receipt>.json` is not a valid proof path. An operator must supply and verify a real file before any orchestration proof attempt.

Required bridge boundary label (must appear in the response for any successful future orchestration):

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

Required authority block (must remain all-false):

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

## 14. What This Contract Enables

When the prerequisites in this contract are satisfied, an operator may:

- select or generate a validation receipt
- verify the receipt is visible inside the backend container
- construct an orchestrate_dry_run_preflight payload with a real receipt path
- attempt a future live orchestration proof

This contract defines the prerequisite shape. It does not perform any of those steps.

## 15. What This Contract Does Not Enable

This contract does NOT enable:

- live orchestration proof (requires a separate future proof attempt)
- receipt creation or writing
- receipt ingestion into Codexify
- write flags
- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- dispatch
- merge
- durable truth promotion
- UI support
- release support expansion

## 16. Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Orchestration proof fails before invocation | No receipt exists at the claimed path | Generate a receipt via validate-plan-pack or select an existing one |
| Orchestration proof fails at adapter level | Receipt path not visible inside container | Verify the read-only mount includes `.guardian/receipts/` |
| Orchestration proof fails with invalid receipt | Receipt JSON malformed or references wrong Plan Pack | Verify receipt structure and Plan Pack path |
| Orchestration proof passes but is misinterpreted | Receipt treated as execution authority | Enforce boundary label and authority locks; this contract defines interpretation rules |
| Orchestration proof passes but receipt is ingested | Receipt ingested into Codexify as durable truth | Ingestion requires a separate adoption contract; do not ingest without one |

## 17. Operator Review Checklist

Before proceeding to a future live orchestration proof:

- [ ] Validate-only live proof: PASS (confirmed)
- [ ] Backend reachable with compose override and module invocation active
- [ ] Codex Runner mount visible inside backend container
- [ ] Sample Plan Pack visible inside backend container
- [ ] Validation receipt exists at a known host path
- [ ] Validation receipt visible inside backend container
- [ ] Validation receipt is valid JSON with `result: "pass"`
- [ ] Validation receipt references the correct Plan Pack
- [ ] All authority locks remain false
- [ ] No write flags configured
- [ ] Operator acknowledges receipt is evidence, not execution authority

## 18. Future Live Orchestration Proof Slice

A future live orchestration proof slice would require, at minimum:

1. All prerequisites in this contract satisfied.
2. A real validation receipt path supplied and verified.
3. Backend running with compose override and module invocation active.
4. An explicit payload for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`.
5. A separate proof document recording the observed outcome (PASS, FAIL, or BLOCKED).
6. Continued prohibition on write flags.
7. All authority locks remaining false.
8. The four-line boundary label present in the response.

An operator receipt path availability check has been performed. See [`guardian-codex-runner-validation-receipt-availability-proof.md`](./guardian-codex-runner-validation-receipt-availability-proof.md).

An operator-selected receipt path check was performed. See [`guardian-codex-runner-selected-validation-receipt-proof.md`](./guardian-codex-runner-selected-validation-receipt-proof.md) — the selected receipt was verified as `SELECTED_AVAILABLE`. Selected availability does not imply trust, ingestion, orchestration, dispatch, or execution authority.

Live orchestration proof remains deferred.

## 19. Forbidden Interpretations

Do not interpret this contract as meaning:

- live orchestration is proven
- a validation receipt is execution authority
- a validation receipt is dispatch authority
- receipt existence authorizes Pi Loop invocation
- receipt existence authorizes plan execution
- receipt existence authorizes source mutation
- receipt existence authorizes Codexify ingestion
- receipt existence authorizes write flags
- the orchestration dry-run is a full orchestration run
- Guardian UI integration is shipped
- this task created, wrote, or ingested any receipt

## 20. Bottom Line

This contract defines the prerequisite shape for any future live orchestration proof of the Guardian Codex Runner command-bus bridge.

The validate-only live proof passed. Orchestration is the next bridge command. It requires a real, visible, operator-verified validation receipt.

This contract is prerequisite documentation only. It does not execute orchestration, create receipts, or ingest evidence.

Live orchestration proof remains a separate future slice.
