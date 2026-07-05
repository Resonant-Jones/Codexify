# Pi Loop Receipt Compatibility Audit

## Status

Docs-only compatibility audit for proposed ADR-041 and the Pi Loop Manager adoption contract.

## Source set and audit limits

Audited in this repository revision:

- `docs/specs/campaign-runner/PI_LOOP_MANAGER_ADOPTION_CONTRACT.md`
- `docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`

Expected Campaign Runner source inputs named by the task were searched for but are not present at the requested paths in this checkout:

- `src/codex_runner/loop_manager/contracts.py`
- `src/codex_runner/schemas/loop_receipt.schema.json`
- `src/codex_runner/schemas/gate_receipt.schema.json`
- `examples/example-loop-task.yaml`
- representative `.pi/runs/<run_id>/receipt.json`

Because the concrete v0 schema files and representative receipt artifact are absent from this checkout, this audit classifies the v0 receipt shape described by the adoption contract and proposed ADR-041. Any future ingestion task must re-run this matrix against the concrete Campaign Runner schema before accepting durable evidence.

## 1. Executive summary

The Pi Loop Manager v0 receipt is **compatible with caveats** as a preserved artifact and operator-reviewed attempt-evidence candidate, but it should not be durably ingested as Codexify attempt evidence without a schema revision or an explicit operator mapping decision.

The adoption contract expects the v0 posture to be:

```yaml
receipt_mode: dry_run
receipt_trust_level: validation_captured
receipt_actionability: review_required
```

That posture is compatible with Codexify only if the receipt remains evidence, not truth. The receipt may support review of a bounded local attempt, validation capture, artifact lineage, and follow-up recommendations. It must not mutate WorkOrder lifecycle state, mark work complete, prove release readiness, dispatch downstream work, or bypass Guardian/operator review.

Recommendation: **schema_revision_required_before_codexify_ingestion**.

A minor v1 schema should be proposed before Codexify durable ingestion. Provider execution and patch-applying mode should also wait for v1 lineage and trust fields, but the stricter blocker for Codexify is durable ingestion: without exact attempt identity, artifact root, provider receipt reference, validation output references, ingestion actor, ingestion timestamp, and mode/trust/actionability fields, v0 receipts remain review artifacts only.

## 2. Receipt field mapping matrix

Classification vocabulary used here:

- `admissible_evidence` — usable as bounded evidence after review, without granting direct lifecycle authority.
- `advisory_metadata` — useful context but not sufficient proof.
- `operator_confirmation_required` — requires a human/operator decision before any durable or mutating action.
- `missing_from_v0` — required by Codexify adoption expectations but not confirmed as emitted by v0.
- `requires_schema_revision` — should be added or clarified in a v1 schema before durable ingestion.
- `out_of_scope` — not evidence for Codexify attempt ingestion.

| Pi Loop field | Codexify adoption field | Classification | Required for ingestion? | Trust limit | Operator review trigger? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `task_id` | `task_id` | `admissible_evidence` | Yes | Identifies the task spec used by the loop; does not identify a Codexify WorkOrder by itself. | Yes, if not mapped to a known WorkOrder. | Preserve exactly as receipt lineage. |
| `work_order_id` | `work_order_id` / `coding_work_orders.id` | `operator_confirmation_required` | Yes when available; otherwise explicit mapping required. | Provider or loop declaration is not proof that the WorkOrder exists or should transition. | Yes, when absent, malformed, stale, or unmapped. | Must already exist or require operator mapping before durable ingestion. |
| `run_id` | run / attempt lineage | `admissible_evidence` | Yes | Local run lineage only; must not replace WorkOrder identity. | Yes, if duplicate or not tied to an artifact root. | Should be unique within the Campaign Runner run namespace. |
| `attempt` | `attempt_id` or attempt ordinal | `requires_schema_revision` | Yes | Integer attempt ordinal is insufficient if Codexify needs durable attempt identity. | Yes, if null or ambiguous. | v1 should distinguish local attempt number from Codexify `attempt_id`. |
| `attempt_id` | `attempt_id` / mapped Codexify attempt identity | `missing_from_v0` | Yes | Required for durable Codexify attempt evidence; cannot be inferred safely from `attempt`. | Yes. | Add explicit nullable `attempt_id` or `codexify_attempt_id` mapping field. |
| `loop_status` | attempt evidence status | `admissible_evidence` | Yes | Status is a loop observation, not WorkOrder completion. | Yes, for pass/success/completion-like statuses. | Must not directly mutate WorkOrder lifecycle. |
| `stop_reason` | attempt evidence reason | `admissible_evidence` | Yes | Explains why the loop stopped; token vocabulary is not necessarily canonical. | Yes, for ambiguous, error, policy, or success-as-completion language. | v1 should define closed tokens or a canonical mapping. |
| `provider_kind` | `provider_kind` | `admissible_evidence` | Yes | Identifies the adapter kind selected; does not prove provider output truth. | Yes, for unknown provider, cloud provider, or boundary change. | Needed to preserve provider lineage. |
| `provider_receipt_ref` | `provider_receipt_ref` | `requires_schema_revision` | Yes when provider output exists. | A pointer to adapter output, not proof that output is valid. | Yes, when absent for provider execution. | For dry-run, null can be acceptable if explicitly mode-scoped. |
| `gate_receipts` | `gate_receipts` | `admissible_evidence` | Yes | Evidence that gates reported statuses; does not prove policies were sufficient. | Yes, on any failed, skipped, unknown, or ambiguous gate. | See gate mapping below. |
| `validation_commands` | `validation_commands` | `admissible_evidence` | Yes | Captured commands are scoped proof intentions, not global release proof. | Yes, if missing for claimed validation. | Preserve exact command, working directory if available, and environment limitations. |
| `validation_outputs` | `validation_outputs` or artifact refs | `requires_schema_revision` | Yes | Without stable artifact refs, output may be unverifiable or lossy. | Yes, when output is summarized only, missing, or not linked. | v1 should require exact log/artifact references with exit status. |
| `changed_paths` | `changed_paths` | `advisory_metadata` | Yes for patch-producing modes; useful in dry-run. | Provider-declared or loop-detected paths are not proof of persisted changes. | Yes, for architecture, runtime, schema, provider, queue, worker, UI, design-token, identity, privacy, or ADR paths. | Use as review triage, not as durable mutation evidence. |
| `evidence_refs` | `evidence_refs` | `admissible_evidence` | Yes | References require resolver checks and artifact integrity review. | Yes, if refs are external, missing, mutable, or unresolved. | Should include stable file paths or object refs. |
| `adr_impact` | `adr_impact` | `operator_confirmation_required` | Yes | Loop classification is advisory until architecture review. | Yes, for anything other than explicit none/no-impact. | Accepted ADRs remain read-only unless separately authorized. |
| `documentation_impact` | `documentation_impact` | `operator_confirmation_required` | Yes | Documentation claims are not runtime proof. | Yes, for canonical docs, release docs, current-state docs, or accepted contracts. | Proposed docs remain proposals. |
| `operator_review_required` | `operator_review_required` | `operator_confirmation_required` | Yes | Boolean signal cannot self-resolve review. | Yes, always when true; also when absent. | Missing value must fail closed to review-required. |
| `follow_up_recommendations` | `follow_up_recommendations` | `advisory_metadata` | No for minimal ingestion; yes for review workflow preservation. | Recommendations are candidates, not accepted work packets. | Yes, before issue/work-order creation. | Must not dispatch or create work automatically. |
| `artifact_root` | source artifact path / object reference | `requires_schema_revision` | Yes | Required to preserve source lineage and locate logs/receipts. | Yes, if absent or not immutable enough. | v1 should require the run artifact root. |
| `receipt_mode` | `receipt_mode` | `missing_from_v0` | Yes | Cannot safely infer dry-run vs patch-producing vs durable-ingested from status alone. | Yes, if absent. | Add explicit token: `dry_run`, `patch_producing`, `local_execution`, `durable_ingested`. |
| `receipt_trust_level` | `receipt_trust_level` | `missing_from_v0` | Yes | Trust level must not be inferred from validation text. | Yes, if absent. | Add explicit token: `artifact_only`, `validation_captured`, `validation_passed`, `operator_reviewed`, `durable_evidence_ingested`. |
| `receipt_actionability` | `receipt_actionability` | `missing_from_v0` | Yes | Actionability controls whether ingestion/review is safe. | Yes, if absent. | v0 expected value should be `review_required`. |
| `ingestion_timestamp` | `ingestion_timestamp` | `missing_from_v0` | Yes for durable ingestion; no for pre-ingestion artifact. | Should only be set by Codexify ingestion, not local loop output. | Yes, if receipt claims durable ingestion without Codexify path. | Keep null before ingestion; set by future governed ingestion path. |
| `ingestion_actor` | `ingestion_actor` | `missing_from_v0` | Yes for durable ingestion; no for pre-ingestion artifact. | Should identify the Codexify actor/service that performed ingestion. | Yes, if receipt self-declares ingestion. | Keep null before ingestion; set by future governed ingestion path. |
| `completion_claim` / success wording | no direct durable lifecycle field | `operator_confirmation_required` | No as lifecycle truth. | Completion claims are review inputs only. | Yes. | Receipt success must not become WorkOrder complete, merge-ready, or release-ready. |
| `dispatch` / downstream action hints | no direct adoption field | `out_of_scope` | No | Dispatch is deferred and forbidden for this audit. | Yes. | Must remain outside receipt ingestion. |

## 3. Gate receipt mapping

The adoption contract expects each gate receipt to preserve:

```yaml
gate_id: string
gate_status: string
summary: string
evidence_refs: list
changed_paths: list
adr_impact: string
documentation_impact: string
next_gate: string | null
stop_reason: string | null
```

| Gate receipt field | Codexify evidence expectation | Classification | Required for ingestion? | Trust limit | Fail-closed behavior |
| --- | --- | --- | --- | --- | --- |
| `gate_id` | Stable gate identity in attempt evidence | `admissible_evidence` | Yes | Identifies the policy step, not policy sufficiency. | Missing/unknown gate id => `review_required`. |
| `gate_status` | Gate outcome observation | `admissible_evidence` | Yes | Status is local gate output only. | Failed, skipped, unknown, null, or ambiguous status => `review_required` or `blocked`. |
| `summary` | Human-readable review context | `advisory_metadata` | Yes | Summary cannot replace evidence refs. | Missing summary with failed/ambiguous status => `review_required`. |
| `evidence_refs` | Gate-level artifacts/log refs | `admissible_evidence` | Yes | References must resolve before durable trust. | Missing refs for validation/policy gates => `review_required`. |
| `changed_paths` | Gate-specific path impact | `advisory_metadata` | Yes for execution/inspection/doc gates. | Paths are declared observations, not durable changes. | Sensitive paths => operator review. |
| `adr_impact` | Architecture impact signal | `operator_confirmation_required` | Yes | Gate classification is not ADR approval. | Any possible ADR impact => `review_required`; accepted ADR mutation => `blocked` unless explicitly authorized. |
| `documentation_impact` | Documentation impact signal | `operator_confirmation_required` | Yes | Does not prove docs are canonical or current. | Canonical/current-state/release docs => `review_required`. |
| `next_gate` | Gate graph continuation lineage | `advisory_metadata` | No for minimal evidence; useful for replay. | Sequencing hint, not proof that next gate ran. | Missing or impossible transition => `review_required`. |
| `stop_reason` | Gate-local stop reason | `admissible_evidence` | Yes when a gate halts or blocks. | Local reason only; vocabulary may need canonical mapping. | Missing reason on halted/failed gate => `review_required`. |

Gate failures or ambiguous gate states must fail closed. The future Codexify boundary should map them to `review_required` when human evaluation can decide whether the artifact remains useful, and to `blocked` when the receipt implies forbidden mutation, accepted ADR modification, unsupported provider execution, merge automation, dispatch, or release-readiness claims.

## 4. Trust boundary analysis

### Artifact evidence

Artifact evidence includes the receipt file, artifact root, validation logs, provider receipt refs, gate evidence refs, and emitted handoff artifacts. These are admissible only as source-lineage evidence. They do not prove the artifact is complete, immutable, safe, or durably ingested.

### Validation evidence

Validation commands and outputs can support a scoped claim that a command was captured or run under the loop. They do not prove global release readiness, live runtime support, UI receipt, merged state, or compatibility outside the command's scope. Missing exact output refs should keep the receipt in review-required status.

### Provider-declared paths

Provider-declared or loop-inspected `changed_paths` are advisory until verified against the repository diff or artifact bundle. They are useful for review routing and operator triggers, especially for architecture, runtime, schema, queue, worker, provider, UI, identity, privacy, or docs-current-state surfaces.

### Operator review signals

`operator_review_required`, `adr_impact`, `documentation_impact`, sensitive changed paths, ambiguous status, absent WorkOrder mapping, absent validation refs, and completion-like language are all review signals. They cannot self-resolve. A true review signal must prevent durable or mutating adoption until a governed reviewer acts.

### Completion claims

`loop_status`, `stop_reason`, or summary text may say that a loop passed, completed, stopped cleanly, or produced candidate outputs. These claims are receipt evidence only. They must not become WorkOrder completion, merge readiness, dispatch approval, release readiness, accepted ADR status, or Command Center truth.

### Durable lifecycle state

Durable lifecycle state belongs to Codexify WorkOrders, Execution Ledger attempts, Guardian-mediated execution records, and operator-visible truth surfaces. Pi Loop receipts may become input evidence only through a future governed ingestion path that records source lineage, actor, timestamp, trust/actionability classification, and review state.

## 5. Missing or ambiguous fields

Required adoption fields that are missing or ambiguous in the available v0 description:

- `work_order_id` — required or operator-mapped before durable ingestion; v0 compatibility is ambiguous without the concrete schema.
- `attempt_id` — not satisfied by an `attempt` integer alone; needs explicit Codexify attempt identity or mapping.
- `provider_kind` — required for provider lineage; concrete v0 emission was not verifiable in this checkout.
- `provider_receipt_ref` — required when provider output exists; nullable only for explicit dry-run/no-provider modes.
- `artifact_root` — required as a stable source artifact path/object reference.
- `ingestion_actor` — should be null before ingestion and set only by Codexify during a governed ingestion event.
- `ingestion_timestamp` — should be null before ingestion and set only by Codexify during a governed ingestion event.
- exact validation output references — summaries are insufficient; v1 should preserve log refs, exit codes, and working directory where relevant.
- mode/trust classification fields — `receipt_mode`, `receipt_trust_level`, and `receipt_actionability` should be explicit fields, not inferred.
- canonical status/reason vocabulary — `loop_status`, `gate_status`, and `stop_reason` need closed-token mapping or explicit noncanonical classification before runtime visibility.
- source schema version — not listed in the adoption contract but recommended so future readers can distinguish v0/v1 receipts.
- receipt integrity/hash — not required by the current adoption contract, but recommended before durable ingestion if receipts can move across stores.

## 6. Schema revision recommendation

Decision: `schema_revision_required_before_codexify_ingestion`.

Proposed v1 additions or clarifications, without implementing them:

1. Add explicit schema metadata:
   - `schema_version`
   - `receipt_kind`
   - `generated_at`
2. Add explicit Codexify lineage fields:
   - `work_order_id`
   - `attempt_id` or `codexify_attempt_id`
   - `source_artifact_ref`
   - `artifact_root`
3. Add explicit provider lineage fields:
   - `provider_kind`
   - `provider_receipt_ref`
   - `provider_output_ref`
4. Add explicit trust/actionability fields:
   - `receipt_mode`
   - `receipt_trust_level`
   - `receipt_actionability`
   - `operator_review_required`
   - `review_triggers`
5. Tighten validation evidence:
   - command string
   - working directory
   - exit code
   - started/finished timestamps when available
   - stdout/stderr or stable artifact refs
   - environment limitation marker when applicable
6. Tighten gate evidence:
   - closed `gate_status` tokens
   - `evidence_refs` required for gates that claim validation or policy proof
   - explicit fail-closed mapping for failed/skipped/unknown states
7. Reserve Codexify-owned ingestion fields:
   - `ingestion_timestamp`
   - `ingestion_actor`
   - `ingestion_review_state`
   - `durable_attempt_evidence_id`

Provider execution and patch-applying mode should also require this v1 work or an equivalent provider-execution schema, because those modes increase the risk that provider-declared paths, validation summaries, or completion wording will be mistaken for durable truth.

## 7. Deferred surfaces

This audit does not implement or authorize:

- durable receipt ingestion.
- WorkOrder lifecycle mutation.
- provider integration.
- patch-applying execution.
- Command Center UI.
- dispatch.
- merge automation.
- accepted ADR modification.
- runtime token registry changes.
- database/schema changes.
- queue, worker, route, event, or persistence behavior changes.

## ADR impact

This audit is aligned with proposed ADR-041 and the Pi Loop Manager adoption contract. It does not promote ADR-041 to accepted status, alter accepted ADRs, or change runtime behavior. It preserves the governing invariant: **receipt is evidence, not truth**.
