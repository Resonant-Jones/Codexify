# ADR-049: Event-Driven Campaign Control Plane

## Status
Accepted

## Context
Codexify needs a repository-native control-plane substrate that can validate approved issue packets, PR lineage, and merge eligibility without granting an LLM or webhook handler authority to mutate branches or merge code.

## Decision
1. GitHub-native events are the first control-plane substrate.
2. Issues are planning and approval records; PRs are implementation and proof records.
3. Deterministic checks and branch protection outrank model review.
4. LLM review is advisory only.
5. The initial control plane is dry-run only.
6. `workflow_run` scoped to Guardian CI replaces broad `check_suite` handling to avoid recursive control-plane runs.
7. Agent dispatch, external review invocation, merge enablement, and repository-setting mutation require separate tasks.
8. A hosted webhook receiver remains deferred until GitHub-native limits are proven insufficient.

## Consequences
The repository gains an inspectable eligibility receipt and a bounded vocabulary without gaining autonomous execution or merge behavior. Human labels remain explicit authority evidence. Same-repository pull requests may validate candidate evaluator code under an explicitly read-only token with credentials disabled; fork and non-PR events use trusted default-branch code.

## Rejected alternatives
- `pull_request_target` with checkout of PR code: rejected because it can expose elevated tokens to untrusted code.
- Automatic merge or auto-merge: rejected for this slice.
- Comment-based receipts: rejected initially to avoid comment storms and write permissions.
- Hosted webhook service: deferred as unnecessary infrastructure for the first slice.
