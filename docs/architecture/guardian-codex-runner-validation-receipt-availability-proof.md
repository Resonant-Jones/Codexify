# Guardian Codex Runner Validation Receipt Availability Proof

> Classification: operator evidence
> Status: BLOCKED
> Scope: receipt-path availability check for future dry-run orchestration proof

Last updated: 2026-07-08

## 1. Purpose

This note records whether an operator-selected validation receipt path is available and visible for a future dry-run orchestration proof of `internal::guardian.codex_runner.orchestrate_dry_run_preflight`.

This task does not run orchestration. It does not create receipts, does not write receipts, does not trust receipts, and does not ingest receipts. It verifies path availability only.

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

## 2. Status

Status: **BLOCKED**

Proof attempt timestamp: `2026-07-09T01:XX:XX+00:00`

Reason: No operator-selected receipt path source is configured. Neither `CODEX_RUNNER_VALIDATION_RECEIPT_PATH` nor `/tmp/guardian-bridge-validation-receipt-path.txt` is present. A valid receipt exists on disk and is visible inside the backend container, but the orchestration prerequisite contract requires an explicit operator-supplied path. Without an operator-configured source, the proof cannot proceed past the selection gate.

## 3. Scope

This proof is receipt-path availability only.

This proof does not:

- run orchestration
- run validate-plan-pack with --write-receipt
- create, write, trust, or ingest receipts
- select receipts by model judgment or automated scanning
- parse receipt contents for authority
- execute any Codex Runner command

## 4. Proof Class

Proof class: operator evidence — receipt path availability check.

This is not a live orchestration proof.

## 5. Relation to Prior Proofs

| Artifact | Status | Relationship |
|---|---|---|
| `guardian-codex-runner-command-bus-live-validate-module-proof.md` | PASS | Validation proven; receipt now needed for orchestration |
| `guardian-codex-runner-orchestration-receipt-prerequisite-contract.md` | Contract | Defines the rules this proof checks |
| **This proof** | **BLOCKED** | No operator-selected receipt path source configured |

## 6. Current Truth

Current truth preserved during this check:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- The validate-only live proof passed through the command-bus bridge using module invocation.
- The orchestration receipt prerequisite contract defines the receipt rules.
- This proof records receipt-path availability only.
- This proof does not trust, ingest, or authorize receipt contents.
- This proof does not prove live orchestration.

## 7. Receipt Path Source

Two operator-controlled sources are accepted by the prerequisite contract:

1. **Environment variable**: `CODEX_RUNNER_VALIDATION_RECEIPT_PATH`
2. **Local file**: `/tmp/guardian-bridge-validation-receipt-path.txt` (must contain exactly one absolute path to a JSON file)

Status of each at proof time:

| Source | Present? |
|---|---|
| `CODEX_RUNNER_VALIDATION_RECEIPT_PATH` | No |
| `/tmp/guardian-bridge-validation-receipt-path.txt` | No |

Neither source is configured. The proof is blocked at the selection gate.

## 8. Receipt Path Candidate

Despite no operator source being configured, a Codex Runner validation receipt exists on the host filesystem:

**Receipt:** `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json`

Receipt properties (verified from host, not ingested):

| Property | Value |
|---|---|
| Path is absolute | Yes |
| Ends in `.json` | Yes |
| Exists on host | Yes |
| Readable on host | Yes |
| Receipt type | `guardian_plan_pack_validation` |
| Receipt version | `v0` |
| `validation.valid` | `true` |
| `validation.result` | `pass` |
| `plan_pack_path` | Matches sample Plan Pack |
| `evidence.evidence_not_authority` | `true` |
| `authority` (all 9 locks) | All `false` |

This receipt exists and is structurally valid. It could be selected by an operator for a future orchestration proof. However, because no operator source is configured, it is NOT the active receipt for this proof.

## 9. Host Visibility Check

Receipt path verified on the host (not via Docker):

```
$ test -f "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json"
Host: EXISTS

$ test -r "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json"
Host: READABLE
```

## 10. Backend Container Visibility Check

Receipt path verified inside the backend container using the opt-in compose override:

```
$ docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml exec backend test -r "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json"
Result: exit 0 — Receipt visible and readable inside backend container
```

The receipt path is under the mounted Codex Runner root (`/Volumes/Dev_SSD/Codex-Runner`) and resolves inside the read-only mount. The path satisfies the bridge adapter's `validate_codex_runner_path` rules.

## 11. Receipt Authority Interpretation

The receipt is evidence only:

- `evidence.evidence_not_authority: true` — the receipt itself declares it is not authority
- `evidence.approval_granted: false`
- `evidence.execution_performed: false`
- `evidence.codexify_ingestion_performed: false`
- `evidence.durable_mutation_performed: false`
- All nine authority locks remain `false`

Receipt existence does not:

- grant execution authority
- grant dispatch authority
- grant merge authority
- authorize Pi Loop invocation
- authorize plan execution
- authorize source mutation
- authorize Codexify ingestion
- authorize write flags

## 12. What This Proof Establishes

This blocked proof establishes that:

- no operator-selected receipt path source is currently configured
- `CODEX_RUNNER_VALIDATION_RECEIPT_PATH` is not set
- `/tmp/guardian-bridge-validation-receipt-path.txt` does not exist
- a valid Codex Runner validation receipt exists on the host filesystem at `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json`
- the receipt is structurally valid JSON with `validation.result: "pass"`
- the receipt references the correct sample Plan Pack
- the receipt is visible and readable inside the backend container through the read-only mount
- the receipt declares itself as evidence-not-authority
- all authority locks remain false in the receipt

## 13. What This Proof Does Not Establish

This proof does not establish:

- that an operator-selected receipt source is configured (it is not)
- that the receipt has been ingested or trusted
- that the receipt authorizes orchestration
- that live orchestration can proceed (it is still deferred)
- that receipt contents are semantically correct (only structural validity was checked)
- that any Codexify durable record references this receipt

## 14. Failure or Blocked Interpretation

Interpretation: **BLOCKED**.

Blocking prerequisite: no operator-selected receipt path source configured.

To unblock:

Option A — Environment variable:

```bash
export CODEX_RUNNER_VALIDATION_RECEIPT_PATH="/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json"
```

Option B — Local file:

```bash
echo "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json" \
  > /tmp/guardian-bridge-validation-receipt-path.txt
```

Either option must be set before a future orchestration proof attempt.

This is NOT a:

- receipt validity failure (the receipt is valid)
- container visibility failure (the receipt is visible)
- adapter or command-bus failure
- Codex Runner CLI failure

## 15. Future Live Orchestration Proof Slice

A future live orchestration proof would require:

1. An operator-selected receipt path configured (this proof's blocker).
2. The receipt verified as visible inside the backend container (confirmed here).
3. Backend running with compose override and module invocation active.
4. An explicit payload for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`.
5. A separate proof document recording the observed outcome.
6. All authority locks remaining false.

Live orchestration proof remains deferred.

## 16. Forbidden Interpretations

Do not interpret this proof as meaning:

- live orchestration is proven
- a validation receipt is execution authority
- the receipt has been ingested or trusted by Codexify
- receipt availability authorizes Pi Loop invocation
- receipt availability authorizes plan execution
- receipt availability authorizes source mutation
- receipt availability authorizes Codexify ingestion
- receipt availability authorizes write flags
- this task created, wrote, or ingested any receipt
- the BLOCKED status implies the receipt is invalid

## 17. Bottom Line

This proof records whether an operator-selected validation receipt path is available for a future dry-run orchestration proof.

Status: **BLOCKED** — no operator source configured.

A valid Codex Runner validation receipt exists at `/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json`. It is structurally valid (`validation.result: "pass"`), references the correct Plan Pack, is visible inside the backend container, and declares itself as evidence-not-authority.

Setting `CODEX_RUNNER_VALIDATION_RECEIPT_PATH` or creating `/tmp/guardian-bridge-validation-receipt-path.txt` would unblock the receipt selection gate.

Live orchestration proof remains deferred.
