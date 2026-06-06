# Docs-to-Issue Compiler Protocol

## Purpose

This protocol governs how Axis, Codex, and other Codexify agents may turn repository documentation into GitHub issue candidates. It is a documentation-only operating contract: it does not implement scripts, GitHub Actions, API calls, project-board mutation, autonomous issue execution, auto-merge, or runtime behavior.

The goal is to let agents compile focused, validated work packets from the documentation corpus without flooding the board, widening release claims, or treating docs as proof of implementation.

## Operating Boundaries

- Issue creation, task execution, proof collection, and release claim changes are separate acts.
- A GitHub issue is a work proxy. It is not evidence that implementation exists, that validation passed, or that the release promise has changed.
- One issue maps to one focused task or one explicit tracking epic.
- No issue may silently combine unrelated edits.
- Architecture-impacting work must be identified before task generation.
- Codex tasks must remain atomic and explicitly validated.
- Generated issues must include validation and closeout expectations.
- Release claims must stay bounded by `docs/architecture/00-current-state.md`.

## Governing Contracts

The compiler is aligned with existing architecture guidance and does not require a new ADR because it defines an agent work-derivation protocol rather than runtime behavior, queue behavior, routing behavior, or autonomous execution.

Governing sources:

- `docs/architecture/00-current-state.md` for release readiness, supported install path, active blockers, current priorities, and present release promise.
- `docs/architecture/README.md` for the architecture KB entry points and current runtime framing.
- `docs/architecture/agent-protocol-operations.md` for agent protocol operations and delegation guidance.
- `docs/architecture/kb-validity-matrix.md` for documentation validity classes, runtime source sets, and quarantined or historical source handling.
- `docs/architecture/adr/adr-index.md` and referenced ADRs for architectural decisions, including Guardian-mediated coding-agent execution when a candidate touches coding-agent execution boundaries.

## Source Hierarchy for Issue Derivation

When sources disagree, prefer the highest applicable source in this hierarchy. Lower-ranked sources may provide context, but they must not override higher-ranked current truth.

1. **Current-state truth** — `00-current-state.md` wins for release readiness, supported install path, active blockers, current priorities, and present release promise.
2. **Active audits and work briefs** — use only when they are current, scoped, and not contradicted by current-state truth.
3. **Architecture KB and validity matrix** — use validity classification to distinguish authoritative current docs from supplementary, design-canon, historical, or misleading sources.
4. **Governing ADRs and contracts** — use for decision boundaries, especially when a candidate changes queue semantics, Guardian ownership, provider/request state, persistence, graph writes, coding-agent execution, or release gates.
5. **Proof artifacts** — use live evidence, test logs, receipts, or explicit proof surfaces as evidence; do not treat generated summaries as proof unless they point to verifiable artifacts.
6. **Implementation code references** — use actual mounted routes, workers, services, schemas, imports, and tests to confirm whether a documented path is wired.
7. **Marketing or campaign docs** — use only as draft claim inputs or future-lane prompts; they cannot establish release support or current runtime truth.

## Issue Candidate Categories

Each candidate must choose one primary category. A secondary category may be recorded only if it clarifies routing without broadening scope.

| Category | Use when | Default handling |
| --- | --- | --- |
| `release-blocker` | A current-state blocker or supported-path defect prevents the stated beta promise from holding. | Highest priority; requires proof surface and owner-visible validation. |
| `proof-needed` | Documentation or code suggests a capability, but current proof is stale, missing, or code-path only. | Validate before widening any claim. |
| `architecture-contract` | A decision boundary, ADR, or operating contract needs clarification or a narrow follow-through doc change. | Mark architecture impact explicitly. |
| `implementation-slice` | A focused code change is needed and can be validated atomically. | Must name target files, tests, and runtime layer. |
| `docs-follow-through` | Documentation needs synchronization with already-proven behavior or already-merged changes. | Must cite the proof that justifies the doc update. |
| `marketing-claim-review` | Campaign, launch, or product language may overstate current truth. | Review against `00-current-state.md`; do not create implementation scope by implication. |
| `board-hygiene` | Existing issues, labels, status, duplicates, or project-board placement need cleanup. | Avoid creating new product work unless separately justified. |
| `deferred-future-lane` | A concept is valid future work but outside the present release promise or lacks current proof. | Keep out of release lanes; prefer an epic only when coordination is useful. |

## Required Issue Metadata

Every generated issue must include these fields in the body or structured task packet:

- **Lane**: one of the candidate categories above.
- **Priority**: `P0`, `P1`, `P2`, or `P3`, with a one-sentence reason tied to current-state impact.
- **Source docs**: exact source paths and, when helpful, sections or line anchors.
- **Source rank**: the highest-ranked source used from the source hierarchy.
- **Target files**: expected files or directories to inspect or edit; use `TBD after inspection` only for investigation issues.
- **Runtime layer**: route, queue, worker, provider, persistence, eventing, frontend, docs, or `not runtime`.
- **Proof surface**: tests, live health endpoints, receipts, logs, screenshots, diff checks, or explicit statement that the issue is proof-seeking.
- **Validation**: copy/paste runnable checks expected before closeout.
- **Board status suggestion**: `triage`, `ready`, `blocked`, `in progress`, `review`, or `deferred`.
- **Closeout expectations**: what must be true before the issue can close.
- **Architecture impact**: `none`, `aligned with existing ADRs`, or `ADR review needed`, with a brief reason.
- **Release claim note**: whether the issue may affect release language; default is `no release claim change until proof is attached and current-state truth is updated`.

## Dedupe Rules

Use these dedupe rules before recommending a new issue:

1. Normalize the candidate around the actual problem, not the document that mentioned it.
2. Search existing open and recently closed issues, active work briefs, task packets, and relevant docs for the same target files, runtime layer, proof surface, and closeout condition.
3. Treat repeated docs, mirrored exports, campaign drafts, and generated artifacts as duplicate evidence unless they introduce a distinct current-state conflict or validation gap.
4. Prefer updating or commenting on an existing issue when the same work can close under the same validation criteria.
5. Create a new issue only when it has a distinct closeout condition, distinct target surface, or distinct architecture decision boundary.
6. If several related items are too broad for one issue, create one explicit tracking epic and link atomic implementation or proof-needed issues beneath it.
7. Do not split work by source document when the required code or proof change is the same.
8. Do not merge unrelated runtime layers into one issue merely because one document mentions them together.

## Hold Rules: When No Issue Should Be Created

Hold issue creation when any of these conditions apply:

- The source is contradicted by `00-current-state.md` and the candidate only widens a release claim.
- The source is classified as historical, misleading, draft-only, or design-canon-not-runtime-truth and no current proof or current-state conflict is present.
- The candidate asks for autonomous issue execution, auto-merge, board-field automation, or runtime mutation without an explicit scoped task authorizing that work.
- The candidate depends on unverified live behavior but is phrased as an implementation defect rather than `proof-needed`.
- The proposed issue silently combines unrelated edits, layers, or validation surfaces.
- Existing issues already cover the same closeout expectation.
- The action is purely speculative, aspirational, or marketing-driven and cannot name a source-ranked evidence path.
- The work would require a new subsystem, table, route, queue, or domain type without clear architecture justification.
- The only available validation is a statement in docs, with no runnable check, live proof target, or reviewable artifact.

When a hold rule applies, record a rejected candidate note instead of opening an issue. The note should state the source, hold reason, and what evidence would be needed to reconsider.

## Safe First-Pass Backlog Compilation Algorithm

1. **Anchor current truth**: read `docs/architecture/00-current-state.md` first and write down the supported install path, active blockers, not-yet-true claims, and release definition.
2. **Select source set**: choose a bounded source set from active audits, work briefs, the architecture KB, validity matrix, governing ADRs, and proof artifacts. Do not sweep the whole repository unless explicitly requested.
3. **Classify source validity**: mark each source as current truth, active work, authoritative KB, supplementary-verify-against-code, design canon, historical, misleading, proof artifact, code reference, or marketing draft.
4. **Extract candidates**: write one candidate per focused problem, validation gap, contract gap, implementation slice, documentation follow-through, claim review, board-hygiene item, or deferred future-lane idea.
5. **Assign category and layer**: choose a primary category and runtime layer for each candidate. Use `not runtime` for docs-only or board-only tasks.
6. **Check architecture impact**: mark whether the candidate is aligned with existing ADRs, requires ADR review, or has no architecture impact.
7. **Run dedupe**: compare candidates against existing issues, active tasks, source docs, and duplicate generated artifacts using the dedupe rules above.
8. **Apply hold rules**: reject candidates that would widen release claims, duplicate work, rely on stale docs, or lack validation.
9. **Draft issue packets**: for surviving candidates, fill all required metadata and include explicit validation and closeout expectations.
10. **Cap first pass volume**: emit a small ranked batch first, preferring release blockers and proof-needed items over speculative future work.
11. **Separate proof from execution**: if implementation depends on unproven runtime behavior, create or recommend a `proof-needed` issue before an `implementation-slice` issue.
12. **Review release language**: ensure every issue says whether it changes the release claim; default to no release claim change until proof is attached and current-state truth is updated.

## Example Issue Candidate

```markdown
Title: Validate supported-path chat completion proof on current main

Lane: proof-needed
Priority: P1 — current-state truth says chat completion works on the supported local Compose path, and that proof should remain fresh during beta hardening.
Source docs:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
Source rank: current-state truth
Target files: tests and proof logs TBD after inspection
Runtime layer: route → queue → worker → persistence → events
Proof surface: supported local Docker Compose run, health checks, chat completion response persisted to source thread, and relevant logs or receipts
Validation:
- docker compose up -d db redis backend worker frontend
- curl health surfaces required by the current supported path
- run or document the nearest supported-path chat proof command
Board status suggestion: ready
Closeout expectations: attach fresh proof showing request acceptance, worker execution, persistence, and event/result visibility are not being collapsed into one success signal.
Architecture impact: aligned with existing ADRs; this verifies the queued completion contract rather than changing it.
Release claim note: no release claim change unless proof is attached and current-state truth is updated if needed.
```

This is a valid candidate because it is focused, proof-seeking, tied to current-state truth, and does not infer a wider release claim from documentation alone.

## Example Rejected Candidate

```markdown
Rejected title: Ship autonomous issue execution from generated architecture docs

Source docs:
- marketing or generated campaign material claiming future autonomous agent behavior
Hold reason:
- `00-current-state.md` says not to assume autonomous issue execution, auto-merge, UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- The proposal combines issue generation, execution, proof, board mutation, and release support into one broad task.
- No current proof surface or scoped implementation contract is named.
Evidence needed to reconsider:
- A governing ADR or scoped work brief authorizing the execution boundary.
- A separate proof-needed issue proving the existing runtime seam.
- Atomic implementation slices with validation and closeout expectations.
```

No issue should be created for this candidate in first-pass compilation. At most, it belongs in a deferred future lane or a claim-review note until current proof and governing contracts exist.

## Closeout Checklist for Compiler Runs

Before publishing issue recommendations, confirm:

- `00-current-state.md` was consulted and release claims remain bounded.
- Each candidate has one primary category, one runtime layer, and one closeout expectation.
- Dedupe checks were performed against active work and repeated docs.
- Hold rules were applied and rejected candidates were recorded instead of silently dropped.
- Source evidence was recorded with exact paths.
- Validation is runnable or explicitly proof-seeking.
- Issue creation, task execution, proof, and release claim changes remain distinct.
- No scripts, GitHub Actions, API calls, or board mutation were introduced by this protocol.
