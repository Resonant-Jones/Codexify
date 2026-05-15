# Execution Ledger Token Domain Proposal

## Purpose
This document proposes canonical token domains for future Execution Ledger implementation.

This is proposal-only and does not add runtime tokens.

## Status
- status: proposal / architecture planning
- governing ADR: ADR-028 Execution Ledger Campaign Runner Contract
- implementation status: docs-only; no runtime tokens added
- next step before implementation: accept exact token values through a separate implementation task or ADR amendment if needed

## Implementation Note: Backend Bounded Registry
- `guardian/agents/execution_ledger_tokens.py` now provides a backend-only bounded registry for the proposed token domains.
- These tokens are not yet wired into runtime behavior.
- Cross-surface or API-visible adoption still requires explicit implementation tasks and tests.
- Frontend mirroring is deferred until a UI/API surface consumes these tokens.
- `guardian/protocol_tokens.py` remains unchanged in this task.

## Source Set
### Governing docs read
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/execution-ledger-phase-1-repo-aware-recon.md`
- `docs/architecture/execution-ledger-gate-artifacts-contract.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`

### Governing ADRs read
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`

### Governing ADRs applied
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md`
- `docs/architecture/adr/002-dual-state-machine-model.md`

## Scope
### In scope
- proposed token domains
- candidate token names
- semantic definitions
- placement recommendations
- migration risks
- test expectations for future implementation

### Out of scope
- editing `guardian/protocol_tokens.py`
- editing frontend contract token files
- adding migrations
- adding routes
- adding UI
- changing Campaign Runner behavior
- changing work-order behavior
- changing Guardian execution behavior
- changing command bus behavior

## Current-Truth Anchors
- ADR-028 governs Execution Ledger as a Campaign Runner extension.
- The gate/artifact contract defines the docs-level shape of future gate artifacts and proof evidence.
- `coding_work_orders` remain the canonical atomic execution units.
- `campaign_execution_attempts` and Guardian run/attempt records remain durable execution evidence surfaces.
- File artifacts are not canonical runtime truth.
- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- No new runtime states, UI behavior, autonomous dispatch, merge automation, or release widening are introduced by this proposal.

## Token Governance Principles
In Codexify terms, this proposal follows these rules:
- repeated contract-bearing literals must be canonicalized
- runtime-visible lifecycle values must not be invented inline
- backend and frontend values must not diverge
- bounded registries are preferred over one giant enum swamp
- docs-only conceptual terms must not be mistaken for runtime literals
- candidate values require contract tests before runtime use

## Proposed Token Domains Overview
| Domain | Purpose | Runtime-visible? | Suggested registry location | Future test surface |
|---|---|---|---|---|
| Gate decisions | Review gate outcomes | yes, if persisted/exposed | `guardian/protocol_tokens.py` or bounded ledger registry | protocol token tests |
| Gate phases | Intent, plan, proof phases | yes, if persisted/exposed | bounded ledger registry, promoted if cross-surface | protocol token tests |
| Plan states | Lifecycle of implementation plans | yes, if persisted/exposed | bounded ledger registry | backend store/route tests |
| Acceptance validation modes | How criteria are verified | maybe | bounded ledger registry | contract tests |
| Acceptance criterion results | Result of each criterion | yes, if persisted/exposed | bounded ledger registry | backend proof tests |
| Proof decisions | Completion/proof review outcome | yes | `guardian/protocol_tokens.py` or bounded ledger registry | protocol token tests |
| Escalation reasons | Why work could not progress cleanly | yes, if exposed to operator surfaces | `guardian/protocol_tokens.py` or bounded ledger registry | backend/UI tests |

## Candidate Gate Phase Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `intent_scope`
- meaning: the gate phase that bounds task intent, scope, and anti-scope-creep constraints.
- when it appears: intent/scope review before implementation-plan approval.
- what it must not imply: execution has started or completion is proven.
- related gate artifact: intent/scope gate artifact.

### `implementation_plan`
- meaning: the gate phase where an explicit implementation plan is reviewed.
- when it appears: after intent/scope approval and before execution attempts.
- what it must not imply: validation already passed.
- related gate artifact: implementation-plan gate artifact.

### `completion_proof`
- meaning: the gate phase where durable proof evidence is reviewed.
- when it appears: after at least one implementation attempt has produced evidence.
- what it must not imply: UI receipt or release expansion.
- related gate artifact: completion/proof gate artifact.

## Candidate Gate Decision Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `pending`
- meaning: review decision not yet finalized.
- allowed use: pre-decision state for any gate artifact.
- what evidence must exist: gate artifact exists with required fields and identified reviewer.
- what it must not imply: implicit approval or rejection.

### `approved`
- meaning: reviewer accepted the gate artifact under current scope.
- allowed use: explicit gate decision only with reviewer attribution.
- what evidence must exist: decision rationale, reviewer, and timestamp.
- what it must not imply: runtime completion. For intent/scope or plan gates, it does not imply execution success.

### `rejected`
- meaning: reviewer denied gate progression.
- allowed use: explicit halt state requiring revision or closure.
- what evidence must exist: decision rationale and rejected artifact reference.
- what it must not imply: permanent cancellation of the entire campaign.

### `changes_requested`
- meaning: reviewer requests revision before approval.
- allowed use: non-terminal review outcome for iterative correction.
- what evidence must exist: required change notes mapped to artifact sections.
- what it must not imply: rejection of overall intent.

### `deferred`
- meaning: gate decision postponed pending prerequisite conditions.
- allowed use: controlled delay where next review trigger is known.
- what evidence must exist: defer reason and next trigger condition.
- what it must not imply: approval by timeout.

### `superseded`
- meaning: artifact replaced by a newer artifact/version.
- allowed use: lineage-preserving replacement state.
- what evidence must exist: superseding artifact reference.
- what it must not imply: previous artifact was correct or complete.

## Candidate Plan State Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `not_started`
- meaning: no plan draft exists yet for the work order.
- allowed transition notes: may transition to `draft`.
- relationship to work-order execution: execution should not begin from this state.
- what it must not imply: idle campaign or blocked attempt by itself.

### `draft`
- meaning: plan is being authored.
- allowed transition notes: may transition to `ready_for_review`, `abandoned`, or `superseded`.
- relationship to work-order execution: execution remains gated.
- what it must not imply: approved scope for code changes.

### `ready_for_review`
- meaning: draft is complete enough for formal gate review.
- allowed transition notes: may transition to `approved`, `changes_requested`, or `deferred`.
- relationship to work-order execution: execution remains gated until approved.
- what it must not imply: technical correctness verified.

### `approved`
- meaning: reviewed plan accepted for bounded execution attempts.
- allowed transition notes: may transition to `superseded` if replaced.
- relationship to work-order execution: execution may be attempted under approved boundary.
- what it must not imply: completion proven.

### `changes_requested`
- meaning: plan requires revisions before approval.
- allowed transition notes: should return to `draft` or `ready_for_review`.
- relationship to work-order execution: execution should pause or remain blocked.
- what it must not imply: rejection of campaign intent.

### `superseded`
- meaning: plan replaced by a newer approved or reviewable version.
- allowed transition notes: terminal for the superseded plan version.
- relationship to work-order execution: execution should reference active non-superseded plan.
- what it must not imply: prior plan was invalid in all contexts.

### `abandoned`
- meaning: plan intentionally retired without execution.
- allowed transition notes: terminal for that plan instance.
- relationship to work-order execution: work order requires a new plan to proceed.
- what it must not imply: work order automatically cancelled.

## Candidate Acceptance Validation Mode Tokens
All values in this section are candidate conceptual values only and must not be used as runtime literals until canonicalized.

### `manual_review`
- meaning: reviewer-driven qualitative or checklist validation.
- evidence expected: reviewer notes and explicit pass/fail rationale.
- automation posture: manual.
- future proof surface: gate artifact review records.

### `unit_test`
- meaning: scoped automated unit-level tests.
- evidence expected: command and test output summary.
- automation posture: automated.
- future proof surface: backend test execution evidence.

### `integration_test`
- meaning: cross-component automated tests.
- evidence expected: command and integration result summary.
- automation posture: automated.
- future proof surface: integration test output captured in proof artifact.

### `typecheck`
- meaning: static type validation command.
- evidence expected: typecheck command output.
- automation posture: automated.
- future proof surface: typecheck logs attached to completion/proof artifact.

### `lint`
- meaning: lint/static analysis command.
- evidence expected: lint command output.
- automation posture: automated.
- future proof surface: lint report attached to completion/proof artifact.

### `runtime_probe`
- meaning: controlled runtime behavioral check.
- evidence expected: probe command output and observed runtime status.
- automation posture: mixed.
- future proof surface: supported-path proof artifacts where applicable.

### `docs_validation`
- meaning: docs integrity and link validation checks.
- evidence expected: docs validation command results.
- automation posture: automated.
- future proof surface: docs validator outputs.

### `diff_inspection`
- meaning: reviewer inspection of changed files/diff constraints.
- evidence expected: changed-files summary with review conclusion.
- automation posture: manual or mixed.
- future proof surface: gate rationale and diff audit notes.

## Candidate Acceptance Criterion Result Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `not_checked`
- meaning: criterion exists but has not been evaluated yet.
- required evidence: criterion definition only.
- relationship to completion/proof review: blocks proof acceptance when criterion is required.
- what it must not imply: criterion passed implicitly.

### `passed`
- meaning: criterion validated against expected evidence.
- required evidence: observed evidence linked to validation mode and attempt/run context.
- relationship to completion/proof review: supports proof acceptance when required criteria pass.
- what it must not imply: all criteria passed.

### `failed`
- meaning: criterion validation did not satisfy expected evidence.
- required evidence: failure evidence with validation output and rationale.
- relationship to completion/proof review: supports proof rejection or follow-up requirement.
- what it must not imply: entire work order must always be abandoned.

### `blocked`
- meaning: criterion could not be evaluated due to prerequisite or environment constraints.
- required evidence: blocking reason and missing prerequisite.
- relationship to completion/proof review: often drives `evidence_incomplete` or follow-up decisions.
- what it must not imply: silent pass or fail.

### `not_applicable`
- meaning: criterion is intentionally inapplicable under approved scope.
- required evidence: reviewer rationale for exclusion.
- relationship to completion/proof review: can be acceptable if exclusion rationale is explicit.
- what it must not imply: criteria can be skipped without review.

## Candidate Proof Decision Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `proof_pending`
- meaning: proof review not complete.
- required durable evidence: attempt references exist but review decision not finalized.
- relationship to completion receipt: receipt may exist but is not accepted yet.
- relationship to follow-up work orders: none required yet.
- what it must not imply: implicit acceptance.

### `proof_accepted`
- meaning: reviewer accepted completion claim based on durable evidence.
- required durable evidence: attempt/run records, validation outputs, and completion receipt linkage.
- relationship to completion receipt: must reference accepted receipt evidence.
- relationship to follow-up work orders: optional.
- what it must not imply: UI receipt guarantees or release widening.

### `proof_rejected`
- meaning: reviewer rejected completion claim.
- required durable evidence: rejection rationale and failing/incomplete proof references.
- relationship to completion receipt: receipt exists but insufficient for acceptance.
- relationship to follow-up work orders: likely required.
- what it must not imply: route acceptance or event publication failed.

### `follow_up_required`
- meaning: work is partially complete but requires additional bounded tasks.
- required durable evidence: accepted evidence subset and explicit unresolved items.
- relationship to completion receipt: may accept current receipt while requiring additional receipts later.
- relationship to follow-up work orders: one or more follow-up IDs expected.
- what it must not imply: autonomous dispatch of follow-up work.

### `evidence_incomplete`
- meaning: available evidence is insufficient to make a final proof decision.
- required durable evidence: explicit missing evidence list.
- relationship to completion receipt: receipt linkage is incomplete or missing required fields.
- relationship to follow-up work orders: may require follow-up for evidence collection.
- what it must not imply: failure of execution by itself.

## Candidate Escalation Reason Tokens
All values in this section are candidate conceptual values only and are non-runtime until accepted.

### `scope_unclear`
- meaning: scope cannot be bounded confidently.
- likely source surface: intent/scope gate.
- expected remediation path: revise scope artifact and criteria draft.
- operator-facing UI later: yes, likely.

### `plan_rejected`
- meaning: plan gate decision rejected.
- likely source surface: implementation-plan gate.
- expected remediation path: revise plan and resubmit.
- operator-facing UI later: yes.

### `validation_failed`
- meaning: required validation produced failing results.
- likely source surface: completion/proof artifact.
- expected remediation path: address failures and rerun validation.
- operator-facing UI later: yes.

### `delivery_failed`
- meaning: source-thread/result delivery evidence failed or is inconsistent.
- likely source surface: completion/proof artifact with result-link checks.
- expected remediation path: investigate delivery path and attempt evidence.
- operator-facing UI later: yes.

### `lineage_missing`
- meaning: required source lineage references are missing.
- likely source surface: any gate artifact referencing thread/message/codex origin.
- expected remediation path: restore lineage references before approval.
- operator-facing UI later: yes.

### `attempt_failed`
- meaning: execution attempt reached failed terminal state.
- likely source surface: attempt records and Guardian run evidence.
- expected remediation path: analyze failure and decide retry or follow-up.
- operator-facing UI later: yes.

### `evidence_incomplete`
- meaning: decision blocked by insufficient proof data.
- likely source surface: completion/proof review.
- expected remediation path: gather missing evidence and re-review.
- operator-facing UI later: yes.

### `out_of_scope_change`
- meaning: change set exceeded approved scope boundaries.
- likely source surface: diff inspection and completion/proof review.
- expected remediation path: rollback/split changes and issue follow-up work order.
- operator-facing UI later: yes.

### `requires_human_decision`
- meaning: automated/semi-automated progression cannot proceed safely.
- likely source surface: any gate where policy ambiguity or risk is high.
- expected remediation path: explicit reviewer decision.
- operator-facing UI later: yes.

## Placement Recommendation
Recommended strategy: **2. Add a bounded backend ledger token registry and promote only cross-surface values to `guardian/protocol_tokens.py`.**

Rationale:
- aligns with Codexify's bounded-registry doctrine and avoids one giant enum surface.
- keeps Execution Ledger-specific vocab local until values become truly cross-surface.
- supports conservative promotion to global protocol tokens only when values are API/event/UI visible.

Conservative constraints for later implementation:
- keep validation-mode tokens in the bounded ledger registry unless they become API-visible.
- mirror accepted backend canonical tokens in frontend contract types only after backend canon exists.

This recommendation is not implemented in this task.

## Transition and Compatibility Notes
- Future runtime work should avoid conflicting with existing `coding_work_orders` and Campaign Runner statuses.
- Future token adoption should avoid casual renaming of existing Campaign Runner values.
- Docs-only terms should be migrated into runtime tokens only with canonical tests.
- Frontend should avoid independent literal invention and mirror backend canonical values.
- If older metadata values appear later, adapters/mapping layers should normalize them explicitly instead of silently reinterpreting them.

## Future Test Expectations
If any proposed values become runtime-visible, future implementation must add:
- protocol token contract tests
- backend store/route tests for accepted values
- frontend contract/type tests if mirrored
- docs validation
- migration/backfill tests only if existing persisted values are changed

## Invariants
- no runtime token changes in this task
- no duplicate canonical truth surface
- no prompt-only control plane
- no acceptance/completion collapse
- no event-publication/UI-receipt collapse
- no private identity/persona leakage into public task artifacts
- no durable trait inference through task artifacts
- no bypass of command bus or Guardian-mediated orchestration policy seams
- no release-promise widening

## Follow-Up Task Recommendation
Next task recommendation:
- Add a backend-only bounded Execution Ledger token registry and contract tests, if maintainers accept the proposed domains.
