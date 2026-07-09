# Guardian Evidence Packet Static Validator Contract

> Classification: architecture contract
> Status: docs-only static validation doctrine — no runtime implementation
> Scope: future static validation of GuardianEvidencePacket fixtures and outputs

Last updated: 2026-07-09

Source anchors:
- docs/architecture/guardian-evidence-packet-reducer-contract.md
- docs/architecture/fixtures/guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json
- docs/architecture/guardian-codex-runner-bridge-proof-chain-index.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/canonical-token-philosophy.md

## 1. Purpose

This contract defines the first docs-only static validation doctrine for GuardianEvidencePacket fixtures and future GuardianEvidencePacket outputs.

A future static validator should inspect a GuardianEvidencePacket for shape completeness, guardrail presence, and boundary preservation — without executing code, approving truth, writing receipts, ingesting evidence, or widening authority.

This contract defines what a static validator must check, what issue vocabulary it should use, and what failure semantics apply. It does not implement the validator.

## 2. Status

Status: docs-only static validation doctrine.

This contract does not:

- implement a runtime validator
- add runtime reducer code
- add persistence, ingestion, UI, or dev-build test buttons
- authorize execution, source mutation, Pi Loop, or Codexify ingestion

## 3. Scope

This contract governs future static validation of GuardianEvidencePacket instances — both static fixtures and future runtime-produced packets. It defines:

- Validator input classes and output shape
- Validation phases and required checks
- Candidate issue code vocabulary
- Severity levels and pass/fail/warning semantics
- Release claim guardrails

It does not implement any of these as runtime code.

## 4. Why This Exists

The GuardianEvidencePacket schema and fixture already exist. Before a future runtime reducer produces packets, and before a future operator UI consumes them, there must be a documented static validation contract so:

- Fixture authors can check their packets before committing.
- Future reducer implementations can validate output before surfacing.
- Operators and Guardians can distinguish shape/gate correctness from claim truth.

The GuardianEvidencePacket bridge fixture's recommended next gate is already `guardian_evidence_packet_static_validator_contract`. This contract defines that gate.

## 5. Current Truth

What is true now:

- The Guardian Evidence Packet and Reducer Profile contract defines the schema family.
- The GuardianEvidencePacket bridge fixture exists as a static example.
- No runtime reducer, UI, or validator exists.
- This contract defines static validation only — no runtime implementation.

## 6. Validation Is Not Authority

Static validation must not be confused with truth approval or execution authority:

- A `pass` result means the packet shape and guardrails are correct — it does not mean claims are true.
- A `pass` result means boundary language is present — it does not mean evidence is sufficient.
- A `pass` result is not Codexify ingestion.
- A `pass` result is not Execution Ledger truth.
- A `pass` result is not WorkOrder mutation.
- A `pass` result is not execution authorization.

The validator is a shape and gate checker, not a truth oracle.

## 7. Validator Input Classes

A future static validator should accept at minimum:

- **Static fixture file** — a JSON file conforming to the GuardianEvidencePacket schema.
- **Future runtime-produced packet** — a GuardianEvidencePacket instance from a future reducer service.

This contract defines checks applicable to both input classes.

## 8. Validator Output Shape

A future static validator should produce a `GuardianEvidencePacketStaticValidationResult`:

```
GuardianEvidencePacketStaticValidationResult:
  schema_version: string         # e.g. "guardian_evidence_packet_static_validator.v1"
  validated_packet_ref: string   # ref_id or uri of the validated packet
  validator_contract_version: string  # e.g. "v0"
  result: string                 # "pass" | "pass_with_warnings" | "fail"
  issue_count: integer
  issues: [ValidationIssue]
  checked_at: string             # ISO 8601 timestamp
  checked_by: string             # "static_validator_contract" or tool name
  limits:
    max_issues: integer
    severity_filter: string
```

Allowed result values: `pass`, `pass_with_warnings`, `fail`.

## 9. Validation Phases

A future static validator should proceed through ordered phases:

1. **Parse phase** — validate JSON parseability.
2. **Top-level phase** — check schema_version, required fields.
3. **Reducer profile phase** — check reducer_profile_ref presence and review_depth range.
4. **Evidence refs phase** — check ref completeness and required fields.
5. **Claim ledger phase** — check claim structure, evidence binding, and status vocabulary.
6. **Authority phase** — check authority_state presence and lock posture.
7. **Invariant phase** — check invariant presence and required fields.
8. **Uncertainty phase** — check uncertainty presence for depth-appropriate packets.
9. **Forbidden interpretations phase** — check presence of interpretation guardrails.
10. **Next gate phase** — check next_gate_options and recommended_next_gate.
11. **Loop policy phase** — check loop_policy bounds.
12. **Boundary label phase** — check boundary_label presence and content.
13. **Release guardrail phase** — check for release-claim expansion risk.

Phases may be skipped if earlier phases emit `error`-severity issues, but warnings should accumulate across phases.

## 10. Required Top-Level Packet Checks

The validator must check:

- `schema_version` equals `guardian_evidence_packet.v1` or a recognized version.
- `packet_id` is present and non-empty.
- `created_at` is present and ISO 8601 parseable.
- `source_domain` is present and non-empty.
- `evidence_class` is present and non-empty.
- `review_depth` is present and one of: `light`, `medium`, `high`, `xhigh`.
- `subject` is a non-empty object.
- `reducer_profile_ref` is present and non-empty.
- `raw_evidence_refs` is a non-empty array.
- `reduced_summary` is a non-empty string.
- `claim_ledger` is an array.
- `authority_state` is present.
- `invariant_checks` is an array.
- `uncertainty` is an array.
- `forbidden_interpretations` is an array.
- `next_gate_options` is an array.
- `recommended_next_gate` is present.
- `loop_policy` is present.
- `provenance` is present.
- `limits` is present.

## 11. Reducer Profile Checks

- `reducer_profile_ref` must be present and non-empty.
- `review_depth` must be one of: `light`, `medium`, `high`, `xhigh`.

## 12. Evidence Reference Checks

For each evidence ref in `raw_evidence_refs`:

- `ref_id` must be present and non-empty.
- `ref_type` must be present and non-empty.
- `uri_or_path` must be present and non-empty.
- `source_system` must be present and non-empty.
- `status` must be present and non-empty.
- `trust_posture` must be present and non-empty.

Warn if `content_hash` is `null` or a placeholder value.

## 13. Claim Ledger Checks

For each claim in `claim_ledger`:

- `claim_id` must be present and non-empty.
- `claim` must be present and non-empty.
- `status` must be one of: `supported`, `unsupported`, `blocked`, `inferred`, `not_evaluated`.
- `evidence_refs` must be an array.
- `confidence` must be present and non-empty.
- `limits` must be present.
- `counterclaims` must be an array.
- `missing_evidence` must be an array.
- `forbidden_interpretations` must be an array.

Each `evidence_refs` entry must reference a `ref_id` that exists in `raw_evidence_refs`. Missing evidence refs must emit an error.

## 14. Authority State Checks

- `authority_state` must be present.
- Each of the nine authority locks must be present: `guardian_operational`, `plan_execution_allowed`, `pi_loop_invocation_allowed`, `codexify_ingestion_allowed`, `durable_mutation_allowed`, `provider_execution_allowed`, `patch_application_allowed`, `dispatch_allowed`, `merge_allowed`.
- Missing locks must emit an error.
- A lock value of `true` in a packet with `evidence_class: preflight_proof_chain` or where the boundary label includes `PREFLIGHT ONLY` must emit an error.

## 15. Invariant Check Rules

Each invariant entry must have:

- `invariant_id` present and non-empty.
- `description` present and non-empty.
- `status` present and non-empty.
- `evidence_refs` as an array.

## 16. Uncertainty and Missing-Proof Rules

- `uncertainty` must be an array.
- For `review_depth: high` or `review_depth: xhigh`, an empty `uncertainty` array must emit a warning.
- Each uncertainty entry must have: `uncertainty_id`, `description`, `severity`, `missing_evidence`, `resolution_options`.

## 17. Forbidden Interpretation Rules

- `forbidden_interpretations` must be an array.
- An empty `forbidden_interpretations` array must emit a warning.
- Each interpretation must have: `interpretation_id`, `statement`.

## 18. Next Gate Rules

- `next_gate_options` must be an array.
- An empty `next_gate_options` array must emit a warning.
- `recommended_next_gate` must be present.
- A missing `recommended_next_gate` must emit a warning.

## 19. Loop Policy Rules

- `loop_policy` must be present.
- If `loop_policy.recursive_autonomous_loop_allowed` is `true`, emit an error.
- `loop_policy.bounded` should be `true`.

## 20. Boundary Label Rules

- `boundary_label` must be present and non-empty.
- The boundary label must contain all four lines: `PREFLIGHT ONLY`, `NO PI LOOP INVOCATION`, `NO SOURCE MUTATION`, `NO CODEXIFY INGESTION`.
- Missing boundary label must emit an error.
- Boundary label with missing lines must emit an error.

## 21. Release Claim Guardrails

The validator should check for release-claim expansion risk:

- If the reduced summary or claim ledger contains language implying shipped UI, production auth policy, execution support, Pi Loop authorization, plan execution authorization, or Codexify ingestion when the authority state has those locks `false`, emit a warning with code `release_claim_expansion_risk`.
- This is a warning, not an error, because static validation cannot determine semantic intent.

## 22. Candidate Issue Code Vocabulary

Candidate validator issue codes (not runtime protocol tokens until future promotion):

| Code | Description |
|---|---|
| `packet_json_invalid` | Packet is not valid JSON. |
| `packet_schema_version_missing` | `schema_version` is missing. |
| `packet_schema_version_unsupported` | `schema_version` is unrecognized. |
| `packet_required_field_missing` | A required top-level field is missing. |
| `review_depth_invalid` | `review_depth` is not in the allowed set. |
| `reducer_profile_missing` | `reducer_profile_ref` is missing or empty. |
| `evidence_ref_required_field_missing` | An evidence ref is missing a required field. |
| `claim_required_field_missing` | A claim entry is missing a required field. |
| `claim_status_invalid` | A claim `status` is not in the allowed vocabulary. |
| `claim_evidence_ref_missing` | A claim references an evidence ref_id not in `raw_evidence_refs`. |
| `authority_state_missing` | `authority_state` is missing from the packet. |
| `authority_lock_missing` | An authority lock is missing from `authority_state`. |
| `authority_lock_true_for_preflight` | An authority lock is `true` in a preflight-only packet. |
| `invariant_required_field_missing` | An invariant check is missing a required field. |
| `uncertainty_missing_for_depth` | `uncertainty` is empty for high or xhigh depth. |
| `forbidden_interpretations_missing` | `forbidden_interpretations` is empty. |
| `next_gate_options_missing` | `next_gate_options` is empty. |
| `recommended_next_gate_missing` | `recommended_next_gate` is missing. |
| `loop_policy_missing` | `loop_policy` is missing. |
| `recursive_loop_allowed` | `recursive_autonomous_loop_allowed` is true. |
| `boundary_label_missing` | `boundary_label` is missing or incomplete. |
| `release_claim_expansion_risk` | Packet summary/claims contain language inconsistent with false authority locks. |
| `content_hash_missing` | An evidence ref has null or placeholder `content_hash`. |
| `static_fixture_marker_missing` | A static fixture does not declare itself as static. |

These are candidate codes for a future validator implementation. They must be promoted through the runtime protocol token process before becoming canonical runtime tokens.

## 23. Severity Levels

Three severity levels for validation issues:

- `error` — Must be fixed. Packet fails validation.
- `warning` — Should be reviewed. Packet passes with warnings.
- `info` — Advisory. Does not affect pass/fail.

## 24. Pass / Fail / Warning Semantics

| Result | Condition |
|---|---|
| `pass` | Zero errors, zero warnings. |
| `pass_with_warnings` | Zero errors, one or more warnings. |
| `fail` | One or more errors. |

A `pass` is not truth approval. A `fail` does not authorize broad repair work outside the packet's task scope.

## 25. Relationship to Evidence Packet Reducer Contract

The static validator contract is a companion to the Guardian Evidence Packet and Reducer Profile contract. The reducer contract defines the schema; this contract defines how to statically validate instances of that schema. Static validation does not implement runtime reducer behavior.

Future reducer implementations should produce packets that pass static validation before operator surfacing.

## 26. Relationship to Static Bridge Fixture

The GuardianEvidencePacket bridge proof-chain fixture is a candidate for static validation. A future validator implementation should be able to validate the fixture and produce a `GuardianEvidencePacketStaticValidationResult`. The fixture's recommended next gate is `guardian_evidence_packet_static_validator_contract`.

A local static validator script now exists at `scripts/guardian/validate_evidence_packet.py`. Invocation:

```bash
python3 scripts/guardian/validate_evidence_packet.py docs/architecture/fixtures/guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json --json
```

A local batch validator script exists at `scripts/guardian/validate_evidence_packets.py`. It scans GuardianEvidencePacket fixtures under `docs/architecture/fixtures` by default and emits a `GuardianEvidencePacketBatchValidationResult`. It preserves individual packet warnings, does not convert warnings into failures, and does not prove claim truth.

```bash
python3 scripts/guardian/validate_evidence_packets.py --json
make guardian-evidence-packets-validate
```

The local Makefile target is operator tooling only: it runs the batch validator over the fixture set. It is not runtime code, ingestion, UI, CI by default, or a release gate by default. It does not write receipts or invoke live validation or orchestration. The script validates shape and guardrail presence only. It does not prove claim truth or promote evidence to authority.

## 27. Relationship to Runtime Reducer Implementation

A runtime reducer implementation is a separate future slice. The static validator does not:

- Replace the reducer.
- Execute the reducer.
- Validate the reducer's internal behavior.
- Generate GuardianEvidencePacket instances.

The validator checks packets after they are produced, whether from a static fixture or a runtime reducer.

## 28. Relationship to Future UI

A future read-only operator UI for consuming packets and validation results is a separate future surface. This contract does not define UI components, layouts, or dev-build test buttons.

## 29. Relationship to Execution Ledger and WorkOrder

Execution Ledger adoption and WorkOrder mutation are separate future contracts. This contract does not connect static validation to Execution Ledger or WorkOrder semantics.

## 30. Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Packet fails JSON parse | Malformed fixture or reducer output | Fix JSON; re-run validator |
| Authority lock true in preflight packet | Reducer or fixture author elevated a lock | Lock must be false; check source evidence |
| Claim references missing evidence ref | Typo in ref_id or ref removed | Fix ref_id or add evidence ref |
| Recursive loop allowed | loop_policy misconfigured | Set recursive_autonomous_loop_allowed to false |
| Boundary label missing | Fixture or reducer omitted boundary_label | Add the exact four-line bridge boundary label |
| Validator treats pass as truth | Consumer misinterprets validation result | This contract explicitly states pass is not truth approval |

## 31. Future Allowed Slices

Future slices beyond this contract remain deferred:

- Runtime validator implementation
- Reducer integration
- Validator as a pre-commit hook
- Validator as a CI gate
- Validator output surfacing in operator UI

## 32. Forbidden Interpretations

Do not interpret this contract as meaning:

- a runtime validator is implemented
- static validation proves claim truth
- static validation proves evidence sufficiency
- a pass result is Codexify ingestion
- a pass result is Execution Ledger truth
- a pass result is WorkOrder mutation
- a pass result is execution authorization
- static validation authorizes Pi Loop invocation
- static validation authorizes plan execution
- static validation authorizes source mutation
- static validation authorizes provider execution
- static validation adds UI support
- static validation is a dev-build test button
- candidate issue codes are canonical runtime tokens (they are not, until promoted)

## 33. Bottom Line

This contract defines the first docs-only static validation doctrine for GuardianEvidencePacket fixtures and future outputs. It specifies validation phases, required checks, candidate issue codes, severity levels, and pass/fail semantics — all without implementing runtime code.

Static validation proves shape, completeness, and guardrail presence. It does not prove claims are true, evidence is sufficient, or execution is authorized.

The bridge fixture's recommended next gate is this contract. This contract defines that gate.

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

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
