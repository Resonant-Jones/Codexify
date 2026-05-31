Purpose: define the canonical Build Proposal artifact between diagnosis and execution in the Guardian Build Loop without granting approval, execution authority, or runtime proof.
Last updated: 2026-05-29
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/guardian-build-loop-doctrine.md
- docs/architecture/unity-audit-doctrine.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md

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
  - This creates the canonical review artifact between diagnosis and execution without changing runtime behavior, execution authority, release scope, identity semantics, protocol tokens, provider routing, queue semantics, or ADR review rules.

## Canonical Definition

A `Build Proposal` is the repo-local, reviewable artifact that turns an observed coherence gap, user request, validation failure, operator note, or other governed source into a bounded task candidate for the Guardian Build Loop.

A Build Proposal sits between diagnosis and execution. It captures source evidence, scope boundaries, architecture impact, human review requirements, validation expectations, proof-receipt requirements, and lineage before any execution substrate may consume it.

A Build Proposal is:

- a draft or review artifact,
- a bounded task candidate,
- a source-linked governance object,
- and a handoff surface for future approved execution.

A Build Proposal is not:

- execution,
- approval,
- runtime proof,
- release support,
- autonomous self-modification,
- ADR bypass,
- or a command to a coding worker, Codex Runner, Pi-style harness, command bus, route, worker, UI, or database.

Human approval remains required before execution. Architecture-impacting proposals must preserve ADR review rules. The coding worker or Codex Runner may consume an approved proposal later, but this contract does not wire that execution path.

## Canonical Terms

| Term | Definition |
|---|---|
| `Build Proposal` | The canonical review artifact between diagnosis and execution in the Guardian Build Loop. |
| `Proposal Source` | The governed origin of the proposal, such as Unity Audit output, a user request, a failed validation run, an operator note, or a manual source. |
| `Evidence Anchor` | A concrete source reference that explains why the proposal exists, such as a doc path, audit artifact, validation output, thread/message identifier, run id, or operator note. |
| `Scope Boundary` | The explicit allowed and forbidden file/runtime/release area for the proposed task. |
| `Architecture Impact Classification` | The proposal's declared architecture impact, ADR impact, and risk level. |
| `Human Review Gate` | The required decision boundary before approval, execution, promotion, merge, or release interpretation. |
| `Execution Eligibility` | The explicit statement of whether the proposal may be consumed by a harness after review. Draft proposals default to ineligible. |
| `Validation Plan` | The commands, checks, or proof actions expected after implementation. Validation is scoped evidence, not global runtime proof. |
| `Proof Receipt` | The required evidence bundle after execution, such as validation summaries, result commits, run ids, or linked artifacts. |
| `Rejection / Deferral State` | A terminal or waiting state that records why a proposal is not moving toward execution. |
| `Build Proposal Lineage` | Source-thread, source-message, audit-artifact, and parent-proposal references that preserve provenance. |

## Artifact Shape

Build Proposal artifacts are JSON objects with the following schema-like shape:

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

## Field Rules

- `schema_version` must start at `1`.
- `proposal_id` should be stable enough for repo-local artifact naming and should include a UTC timestamp plus a title slug.
- `created_at` must be an explicit UTC timestamp.
- `status` must default to `draft`.
- `source.kind` must use one of the declared source kinds.
- `source.references` should contain evidence anchors when known.
- `classification.architecture_impact` must distinguish no impact, possible impact, and architecture-impacting work.
- `classification.adr_impact` must preserve ADR review rules.
- `classification.risk` must reflect review and proof needs, not implementation optimism.
- `scope.files_allowed` and `scope.files_forbidden` are review boundaries, not filesystem enforcement by themselves.
- `scope.runtime_behavior_change` and `scope.release_scope_change` must default to `false`.
- `task.validation` is the proposed validation plan, not proof that validation has run.
- `review.required` must default to `true`.
- `execution.eligible` must default to `false`.
- `execution.harness` must default to `none`.
- `proof.result_commit` must remain `null` until execution produces a commit.
- `proof.validation_summary` must remain `null` until validation evidence exists.
- `lineage` fields should preserve origin and parentage whenever available.

## Status Semantics

| Status | Meaning |
|---|---|
| `draft` | Proposal exists for shaping only. No approval or execution eligibility is implied. |
| `needs_review` | Proposal is ready for human review, but not approved. |
| `approved` | Human review approved the proposal for a bounded execution path. This still is not runtime proof. |
| `rejected` | Human review rejected the proposal. The reason should be captured in review notes or adjacent evidence. |
| `deferred` | Proposal is intentionally postponed, often because evidence, scope, or prerequisite work is missing. |
| `executed` | An approved proposal has been consumed by a harness and has result evidence. |
| `superseded` | A later proposal replaces this one. `lineage.parent_proposal_id` should preserve the chain when applicable. |

## Source and Evidence Rules

A Build Proposal may be generated from:

- Unity Audit output,
- a user request,
- a failed validation run,
- an operator note,
- or another governed manual source.

Unity Audit can surface coherence gaps, but it cannot authorize execution. A user request can motivate a proposal, but it does not by itself approve execution. A failed validation run can justify follow-up work, but it does not grant permission to mutate unrelated surfaces.

Evidence anchors should be concrete and reviewable. Prefer repo paths, artifact paths, run ids, thread ids, message ids, and validation summaries over prose-only rationale.

## Execution Boundary

Draft proposal generation must not:

- execute the proposal,
- call the coding worker,
- call Codex Runner,
- call a Pi-style harness,
- enqueue work,
- add routes,
- add workers,
- add database tables,
- add command-bus commands,
- add UI,
- mutate identity,
- mutate protocol tokens,
- change provider routing,
- change queue semantics,
- widen release scope,
- or imply autonomous self-modification.

Future execution paths may consume approved proposals only through a separately reviewed and explicitly wired contract.

## Review and Proof Discipline

Human review remains the authority gate before execution. Review must check:

- whether the proposal preserves current-state release truth,
- whether architecture impact is classified correctly,
- whether ADR review is required,
- whether scope boundaries are sufficient,
- whether validation is proportional to risk,
- whether proof receipts will distinguish code-path evidence, tests, and live runtime proof.

Proof receipts must not collapse validation success into release readiness. Validation commands prove only the surfaces they exercise. Live runtime proof remains separate and must be anchored to supported-path evidence when release readiness is implicated.

## Current-Truth Anchors

What is true now:

- Guardian Build Loop doctrine is the umbrella consolidation layer.
- Unity Audit can surface coherence gaps but cannot authorize execution.
- Coding Worker / Codex Runner exists as a bounded execution substrate, but execution remains separate from proposal generation.
- Human review remains required.
- Current release truth remains local-first and proof-bound.

What remains not true:

- Build Proposal creation is not approval.
- Build Proposal creation is not execution.
- Build Proposal creation is not runtime proof.
- Build Proposal creation does not widen release support.
- Build Proposal creation does not implement autonomous self-modification.

## Minimal Viable Network

For this contract, the minimal viable network is repo-local:

- Node: operator checkout.
- Trust boundary: human operator review boundary.
- Consistency target: append-only artifact records with human-managed updates.
- Conflict policy: human-in-the-loop supersession through proposal lineage.
- Identity binding: reviewer identity is explicit only when approval metadata is filled.

This contract intentionally avoids federation, sync, and autonomous execution. Those concerns require a later protocol and authority review.
