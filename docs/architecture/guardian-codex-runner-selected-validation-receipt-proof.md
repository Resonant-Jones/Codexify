# Guardian Codex Runner Selected Validation Receipt Proof

> Classification: operator evidence
> Status: SELECTED_AVAILABLE
> Scope: explicitly operator-selected receipt path availability check for future dry-run orchestration proof

Last updated: 2026-07-08

## 1. Purpose

This note records whether an explicitly operator-selected validation receipt path is available and visible for a future dry-run orchestration proof.

This is the follow-up to the validation receipt availability proof (`guardian-codex-runner-validation-receipt-availability-proof.md`) which was BLOCKED because no operator-selected source was configured. This proof uses the explicitly selected receipt path from `/tmp/guardian-bridge-validation-receipt-path.txt`.

## 2. Status

Status: **SELECTED_AVAILABLE**

Proof attempt timestamp: `2026-07-09T01:XX:XX+00:00`

The operator-selected receipt path is available, visible on the host and inside the backend container, readable, valid JSON, references the correct Plan Pack, and declares itself as evidence-not-authority with all nine authority locks false.

## 3. Scope

This proof is selected receipt path availability only.

This proof does not run orchestration. It does not create receipts, does not write receipts, does not trust receipts, and does not ingest receipts. It does not select receipts by model judgment or automated scanning. It does not parse receipt contents for authority. It does not execute any Codex Runner command.

Required boundary label:

```
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

Required authority block:

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

## 4. Proof Class

Proof class: operator evidence — selected receipt path availability check.

This is not a live orchestration proof.

## 5. Relation to Prior Proofs

| Artifact | Status | Relationship |
|---|---|---|
| `guardian-codex-runner-command-bus-live-validate-module-proof.md` | PASS | Validation proven |
| `guardian-codex-runner-orchestration-receipt-prerequisite-contract.md` | Contract | Defines the receipt rules |
| `guardian-codex-runner-validation-receipt-availability-proof.md` | BLOCKED | No operator source configured |
| **This proof** | **SELECTED_AVAILABLE** | Operator-selected path verified |

## 6. Current Truth

Current truth preserved during this check:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- The validate-only live proof passed through the command-bus bridge using module invocation.
- The availability proof was BLOCKED because no operator-selected source was configured.
- This proof records selected receipt path availability.
- This proof does not trust, ingest, or authorize receipt contents.
- This proof does not prove live orchestration.

## 7. Operator-Selected Receipt Path Source

The receipt path source is the local file `/tmp/guardian-bridge-validation-receipt-path.txt`, which contains exactly the operator-selected path.

Selection rule: the path was written explicitly to this file. No scanning, no automated selection, no model judgment.

## 8. Selected Receipt Path

Explicitly selected receipt path:

```
/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json
```

Path properties:

| Property | Value |
|---|---|
| Source file line count | Exactly 1 line |
| Absolute path | Yes |
| Ends in `.json` | Yes |
| Under Codex Runner receipts directory | Yes |

## 9. Host Visibility Check

All checks performed from the host (not via Docker):

| Check | Result |
|---|---|
| File exists on host | PASS |
| File readable on host | PASS |

## 10. Backend Container Visibility Check

Verified inside the backend container via the opt-in compose override:

| Check | Result |
|---|---|
| File visible inside backend container | PASS |
| File readable inside backend container | PASS |

Command used:

```bash
docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f docker-compose.codex-runner-bridge.yml exec backend test -r "$RECEIPT_PATH"
```

## 11. Optional Safe Metadata Observation

A read-only JSON metadata check was performed from the host. This is observation only — it does not constitute trust, approval, ingestion, dispatch, execution, or orchestration permission.

| Metadata field | Observed value |
|---|---|
| JSON parses | Yes |
| `receipt_type` | `guardian_plan_pack_validation` |
| `validation.valid` | `true` |
| `validation.result` | `pass` |
| `plan_pack_path` matches sample | Yes |
| All 9 authority locks false | Yes |
| `evidence.evidence_not_authority` | `true` |

## 12. Receipt Authority Interpretation

The receipt is evidence only:

- `evidence.evidence_not_authority: true` — receipt declares itself as non-authority
- `evidence.approval_granted: false`
- `evidence.execution_performed: false`
- `evidence.codexify_ingestion_performed: false`
- `evidence.durable_mutation_performed: false`
- All nine authority locks remain `false`

Selected receipt availability does not:

- grant execution authority
- grant dispatch authority
- grant merge authority
- authorize Pi Loop invocation
- authorize plan execution
- authorize source mutation
- authorize Codexify ingestion
- authorize write flags

## 13. What This Proof Establishes

This proof establishes that:

- an operator-selected receipt path source is configured via `/tmp/guardian-bridge-validation-receipt-path.txt`
- the selected path is exactly one line, absolute, ends in `.json`
- the receipt exists on the host and is readable
- the receipt is under `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/` (satisfies bridge path rules)
- the receipt is visible and readable inside the backend container through the read-only mount
- the receipt is valid JSON of type `guardian_plan_pack_validation`
- the receipt shows `validation.result: "pass"` and references the correct Plan Pack
- the receipt declares itself as evidence-not-authority
- all nine authority locks are `false` in the receipt

## 14. What This Proof Does Not Establish

This proof does not establish:

- that the receipt has been ingested or trusted by Codexify
- that the receipt authorizes orchestration
- that live orchestration can proceed (it is still deferred)
- that receipt contents are semantically correct (only structural observations were made)
- that any Codexify durable record references this receipt

## 15. Failure or Blocked Interpretation

Interpretation: **SELECTED_AVAILABLE**.

No failure or blocked conditions were encountered. All required checks passed:

- Operator-selected source configured: yes (`/tmp/guardian-bridge-validation-receipt-path.txt`)
- Selected path absolute and valid: yes
- Receipt exists on host: yes
- Receipt readable on host: yes
- Receipt under Codex Runner root: yes
- Receipt visible inside backend container: yes
- Receipt readable inside backend container: yes
- Receipt is valid JSON: yes
- Receipt references correct Plan Pack: yes
- Receipt declares itself as evidence-not-authority: yes
- All authority locks false: yes

## 16. Future Live Orchestration Proof Slice

A future live orchestration proof would require:

1. This selected receipt path verified (this proof — **SELECTED_AVAILABLE**).
2. Backend running with compose override and module invocation active.
3. An explicit payload for `internal::guardian.codex_runner.orchestrate_dry_run_preflight` with the selected receipt path as `validation_receipt_path`.
4. A separate proof document recording the observed outcome.
5. All authority locks remaining false.
6. The four-line boundary label present in the response.

Live orchestration proof remains deferred.

## 17. Forbidden Interpretations

Do not interpret this proof as meaning:

- live orchestration is proven
- a validation receipt is execution authority
- the receipt has been ingested or trusted by Codexify
- selected receipt availability authorizes Pi Loop invocation
- selected receipt availability authorizes plan execution
- selected receipt availability authorizes source mutation
- selected receipt availability authorizes Codexify ingestion
- selected receipt availability authorizes write flags
- this task created, wrote, or ingested any receipt
- the metadata observation constitutes trust or approval

## 18. Bottom Line

This proof records whether an explicitly operator-selected validation receipt path is available and visible for a future dry-run orchestration proof.

Status: **SELECTED_AVAILABLE**.

The receipt at `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json` is available, visible on host and inside the backend container, valid JSON, and declares itself as evidence-not-authority with all nine authority locks false.

Live orchestration proof remains deferred.
