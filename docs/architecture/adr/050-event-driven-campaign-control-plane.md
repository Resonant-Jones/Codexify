# ADR-050: Event-Driven Campaign Control Plane

## Status

Proposed — dry-run foundation implemented; no merge or agent behavior is enabled.

## Context

Campaign issue `#625` and its child packets need an inspectable, deterministic path from approved task packet to pull-request evidence. GitHub is already the repository substrate, while `docs/architecture/00-current-state.md` does not claim an autonomous campaign runtime.

## Decision

Use GitHub-native issue, pull-request, and pull-request-review events as the initial control-plane substrate. Issues hold planning, authorization, and dependency records; pull requests hold implementation and proof records. Deterministic checks, protection, and human authority outrank advisory model review. The initial implementation evaluates supplied evidence and emits a dry-run workflow receipt only.

Agent dispatch, automated model-review invocation, merge enablement, dependency promotion, and closeout each require separate implementation tasks. A hosted webhook service is deferred until GitHub-native constraints are demonstrated. Human override and an emergency stop remain mandatory.

## Authority and security consequences

No model has unilateral merge authority. The workflow uses read-only permissions, checks out the trusted default branch, avoids `pull_request_target`, treats issue/PR bodies as data, and has no write or repository-administration path. Missing required-check or branch-protection evidence blocks rather than infers authority.

## Operational consequences

Receipts are workflow summaries, concurrency is repository-plus-subject scoped, and stale evidence is rejected. This gives operators an observable foundation but not a complete campaign automation service.

## Alternatives considered

- Hosted webhook receiver now: rejected; it adds service, credential, and deployment authority before GitHub-native limits are proven.
- Model-led approval: rejected; it cannot replace deterministic proof or protected repository rules.
- Immediate auto-merge: rejected; separate proof and human authorization are required first.

## Follow-up work

Authorize and prove, separately: deterministic scope/privacy integrations, durable check/comment receipts if summaries become insufficient, bounded dispatch, advisory review, supervised merge, dependency promotion, and autonomous-merge proof.
