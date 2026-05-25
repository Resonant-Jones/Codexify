Purpose: define the canonical Build Proposal artifact for Codexify so Unity Audit findings, user requests, failed validation runs, and operator notes can become bounded review artifacts between diagnosis and execution without implying approval, runtime proof, or autonomous execution.
Last updated: 2026-05-25
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/guardian-build-loop-doctrine.md
- docs/architecture/unity-audit-doctrine.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md
- docs/audits/unity/latest.md
- docs/audits/unity/latest.json

# Build Proposal Artifact Contract

## Classification

- Classification: aligned with existing ADRs and contracts
- Governing ADRs/contracts:
  - Guardian Build Loop Doctrine
  - Unity Audit doctrine
  - Agent Protocol Operations Index
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Self-Extending Agent Plugin System / ADR-010
  - Runtime Protocol Token Contract
  - Account Export + Restore Contract
  - current-state release truth doctrine
- Brief reason:
  - This creates the canonical review artifact between diagnosis and execution without changing runtime behavior, execution authority, or release support.

## Why This Exists

Guardian Build Loop is now the umbrella doctrine for buildable work, but the repo still needs one canonical object that sits between:

- diagnosis,
- review,
- execution eligibility,
- and later proof.

That object is the `Build Proposal`.

It turns a coherence gap, user request, failed validation, or operator note into a bounded artifact that can be reviewed, approved, rejected, deferred, or later consumed by a governed execution harness.

## Canonical Definitions

### Build Proposal

A `Build Proposal` is the canonical review artifact between diagnosis and execution in the Guardian Build Loop.

A Build Proposal is:

- bounded,
- reviewable,
- lineage-aware,
- scope-aware,
- and execution-eligible only after later approval conditions are satisfied.

A Build Proposal is not execution.

A Build Proposal is not approval.

A Build Proposal is not runtime proof.

### Proposal Source

The `Proposal Source` is the governed origin of the proposal signal.

Supported source kinds:

- `unity_audit`
- `user_request`
- `validation_failure`
- `operator_note`
- `manual`

### Evidence Anchor

An `Evidence Anchor` is a repo-local reference that explains why the proposal exists.

Examples:

- a Unity Audit artifact
- a current-state note
- a validation failure summary
- a docs contract reference
- a source thread or operator note reference

Evidence anchors justify the proposal. They do not approve it.

### Scope Boundary

The `Scope Boundary` defines what files, runtime claims, and release claims the proposal may touch.

It must make it explicit whether:

- file writes are bounded,
- runtime behavior change is in scope,
- release-scope change is in scope,
- or certain files or surfaces are forbidden.

### Architecture Impact Classification

The `Architecture Impact Classification` states whether the proposal appears to affect:

- no architecture contract,
- possibly affects architecture contracts,
- or clearly affects architecture contracts.

This classification does not replace ADR review. It routes the proposal into the correct review rigor.

### Human Review Gate

The `Human Review Gate` records whether explicit approval is required before execution or promotion.

For this contract, review is required by default.

### Execution Eligibility

`Execution Eligibility` is the explicit statement of whether the proposal is currently executable by any governed harness.

Default posture:

- `eligible: false`
- `harness: "none"`

Proposal generation must not make a proposal execution-eligible by itself.

### Validation Plan

The `Validation Plan` is the bounded set of commands or checks that would later help prove the proposed change if executed.

Validation planning is not the same thing as validation success.

### Proof Receipt

A `Proof Receipt` is the later evidence bundle that shows what happened after an approved proposal was executed and validated.

This contract only defines where such receipts would be attached. It does not create them.

### Rejection / Deferral State

A proposal may be:

- `rejected`
- `deferred`
- `superseded`

without ever being executed.

This matters because the proposal layer is governance and review, not a promise that work will run.

### Build Proposal Lineage

`Build Proposal Lineage` keeps the origin of the proposal explicit.

It may point back to:

- an origin thread,
- an origin message,
- an audit artifact,
- or a parent proposal.

Lineage makes later approval, execution, proof, and export-safe recordkeeping traceable.

## Contract Rules

- A Build Proposal may be generated from Unity Audit output, a user request, a failed validation run, an operator note, or another governed source.
- A Build Proposal must remain repo-local and reviewable.
- Human approval remains required before execution.
- Architecture-impacting proposals must preserve ADR review rules.
- A coding worker, Codex Runner, Pi-like harness, or manual operator workflow may consume an approved proposal later.
- This task does not wire that execution path.
- Proposal creation must not be narrated as live support, approval, or proof.

## Canonical Artifact Shape

```json
{
  "schema_version": 1,
  "proposal_id": "...",
  "created_at": "...",
  "title": "...",
  "status": "draft|needs_review|approved|rejected|deferred|executed|superseded",
  "source": {
    "kind": "unity_audit|user_request|validation_failure|operator_note|manual",
    "references": []
  },
  "classification": {
    "architecture_impact": "none|possible|yes",
    "adr_impact": "none|aligned|requires_new|supersedes_existing",
    "risk": "low|medium|high"
  },
  "scope": {
    "files_allowed": [],
    "files_forbidden": [],
    "runtime_behavior_change": false,
    "release_scope_change": false
  },
  "task": {
    "summary": "...",
    "instructions": [],
    "validation": [],
    "commit_message": "..."
  },
  "review": {
    "required": true,
    "review_questions": [],
    "approved_by": null,
    "approved_at": null
  },
  "execution": {
    "eligible": false,
    "eligible_after": [],
    "harness": "none|coding_worker|codex_runner|pi_codex_runner|manual",
    "run_id": null
  },
  "proof": {
    "required_receipts": [],
    "result_commit": null,
    "validation_summary": null
  },
  "lineage": {
    "origin_thread_id": null,
    "origin_message_id": null,
    "audit_artifact": null,
    "parent_proposal_id": null
  }
}
```

## Field Interpretation

### `status`

`status` is a governance state, not an execution state.

- `draft`: created but not yet reviewed
- `needs_review`: ready for explicit review
- `approved`: review accepted the proposal for later execution
- `rejected`: explicitly refused
- `deferred`: intentionally delayed
- `executed`: later execution happened through a governed path
- `superseded`: replaced by another proposal

### `source.references`

`references` should contain repo-local evidence anchors when available.

Examples:

- `docs/audits/unity/latest.md`
- `docs/audits/unity/latest.json`
- `docs/architecture/00-current-state.md`
- a validation failure report path
- an operator note path

### `classification`

- `architecture_impact` governs review depth
- `adr_impact` states expected ADR relationship
- `risk` states bounded operator risk, not release truth

### `scope`

`scope.runtime_behavior_change` and `scope.release_scope_change` default to `false`.

If either becomes `true`, the proposal must be treated as higher-rigor review work.

### `review`

`review.required` must default to `true`.

Proposal generation must not populate `approved_by` or `approved_at`.

### `execution`

The proposal layer may describe a future harness, but it must default to:

- `eligible: false`
- `harness: "none"`

That default prevents proposal creation from being interpreted as a command to run work.

### `proof`

`proof.required_receipts` defines the kinds of evidence a later approved execution would need.

Examples:

- validation command receipts
- commit hash
- review note
- supported-path proof reference

### `lineage`

Lineage fields are nullable because the first scaffold may be created manually, but the contract preserves explicit places for source thread, message, audit artifact, and proposal ancestry.

## Relationship To Existing Build Loop Surfaces

| Surface | Relationship to Build Proposal |
|---|---|
| `Unity Audit` | Can generate proposal signals but cannot approve or execute them |
| `Guardian Build Loop` | Proposal is the canonical artifact between Diagnose and Execute |
| `Guardian Delegation` | May later supervise proposal execution after review |
| `coding-worker / Codex Runner` | May later consume an approved proposal, but proposal creation does not call them |
| `Pi Invocation Boundary` | May later constrain a future Pi-like harness, but proposal creation does not invoke that path |
| `Command Bus` | Remains the bounded internal authority lane; proposal generation does not create command authority |

## Current-Truth Anchors

What is true now:

- Guardian Build Loop doctrine is already the umbrella consolidation layer.
- Unity Audit can surface coherence gaps but cannot authorize execution.
- Coding Worker / Codex Runner exists as a bounded execution substrate, but execution remains separate from proposal generation.
- Human review remains required.
- Current release truth remains local-first and proof-bound.

What this contract adds:

- one canonical review artifact between diagnosis and execution
- a stable JSON shape for repo-local proposal scaffolding
- explicit separation between draft proposal, approval, execution, and proof

What this contract does not add:

- autonomous execution
- runtime dispatch
- approval automation
- release approval
- new queue, worker, route, or UI behavior

## Explicit Non-Goals

This contract does not:

- implement autonomous execution
- call coding-worker or Codex Runner
- add routes, workers, DB tables, command-bus commands, or UI
- widen release scope
- bypass ADR review
- treat proposal creation as approval
- treat proposal creation as runtime proof
- mutate identity, protocol tokens, provider routing, queue semantics, or release promises

## Maintenance Rule

If future work changes:

- proposal status semantics,
- review gate semantics,
- execution eligibility rules,
- lineage requirements,
- or proof receipt attachment rules,

update this contract in the same change set and keep it aligned with `guardian-build-loop-doctrine.md` rather than creating a second proposal vocabulary.
