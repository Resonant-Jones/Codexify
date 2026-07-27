# Campaign Control Plane Contract

## Status
Accepted first implementation slice: GitHub-native, deterministic, and dry-run only.

## Authority model
Human repository authority, branch protection, deterministic checks, and explicit merge-authority evidence outrank model review. Issues are planning and approval records. Pull requests are implementation and proof records. LLM review is advisory and cannot authorize merge.

## Event substrate
The first substrate is GitHub Actions. It reacts to bounded issue, pull-request, review, Guardian CI `workflow_run`, and manual diagnostic events. `workflow_run` is used instead of `check_suite` because a workflow that reacts to every completed check suite can trigger itself recursively.

## States
`ineligible`, `eligible_dry_run`, `blocked`, `invalid_packet`, and `missing_lineage`.

## Issue packets
Child issues must satisfy the Codexify Issue Template Contract and carry `ready-for-agent`. The evaluator parses structured headings, the parent campaign, lane, task kind, files, ownership line, validation, narrow staging and commit commands, closeout fields, board metadata, and source evidence.

## PR lineage
A PR must link exactly one approved child issue using a supported closing keyword or `Codexify-Child-Issue: #<number>` / `Implements-Issue: #<number>`. Title references do not establish lineage. A parent campaign is not an implementation issue.

## Merge eligibility
`eligible_dry_run` requires a valid approved child issue, a non-draft open PR, configured successful checks, no active requested-changes review, a branch not known to be behind, in-scope files, a passing privacy sentinel when requested, and the human-applied `merge-authorized` label.

The evaluator never merges, enables auto-merge, updates branches, dismisses reviews, dispatches agents, deploys, or changes repository settings.

## Permissions
The workflow is read-only: `contents`, `issues`, `pull-requests`, `checks`, and `statuses` are read-only. Same-repository pull requests may check out their candidate head under that read-only token with credentials disabled; fork and non-PR events use trusted default-branch code. No untrusted pull-request code executes with elevated permissions.

## Durable receipt
Each run writes a JSON receipt to the workflow summary and uploads the same receipt as a native Actions artifact. A deterministic `receipt_key` identifies the logical target and a deterministic `decision_id` makes duplicate evaluations recognizable. Concurrency cancels obsolete in-progress runs. No issue or PR comments are created, so repeated events cannot create a comment storm.

## Scope and privacy
Scope validation compares changed paths with the child issue's explicit Files list. Privacy scanning is enabled only by the exact issue marker `Privacy sentinel: required`; when enabled, missing patches fail closed and bounded secret-like patterns block eligibility.

## Threat model
- Issue and PR bodies are untrusted data and never reach shell interpolation.
- No `pull_request_target` is used.
- Fork PRs receive no elevated execution path.
- The workflow token is read-only.
- Guardian CI completion is observed through `workflow_run` to avoid check-suite recursion.
- Stale evaluations are bounded by target-scoped concurrency and deterministic decision IDs.
- Model output is never merge authority.

## Dry-run limitation
This slice reports eligibility only. It does not dispatch agents, create branches, commit, push, open PRs, invoke external reviewers, mutate labels, merge, enable auto-merge, update branch protection, host a webhook receiver, or implement observability Slice 3.

## Follow-on work
Agent dispatch, external review invocation, repository mutation, merge enablement, and any hosted receiver require separate issues and architecture review.
