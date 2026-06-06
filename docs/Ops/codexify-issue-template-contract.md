# Codexify Issue Template Contract

This contract defines the canonical GitHub issue-body shape for Codexify work packets. It is intentionally docs-only: it describes how Axis, Codex, and the project board should exchange task context through issues, but it does not implement GitHub Actions, `.github/` templates, scripts, or board automation.

## Scope

Use this contract when creating a Codexify issue that is intended to become a self-contained Codex work packet. Each issue must be narrow enough to review, validate, and commit independently.

Issues following this contract must:

- describe the requested task shape before implementation details;
- identify the workflow lane and board metadata needed for triage;
- name the expected target files and validation commands;
- include source evidence links when the task depends on prior work, external context, or a design decision;
- keep release claims, architecture claims, and product scope aligned with proven evidence.

Issues following this contract must not:

- widen release claims beyond what the requested change can prove;
- mix unrelated edits in the same work packet;
- hide architectural drift behind wording such as "cleanup," "polish," or "small follow-up";
- ask Codex to implement automation, templates under `.github/`, or board wiring unless that is the explicit and separately scoped task.

## Required Issue Fields

### Title convention

Use a short imperative title that describes the desired outcome, not the implementation mechanism.

Recommended format:

```text
<Verb> <Codexify object or surface> <outcome>
```

Examples:

- `Define Codexify issue template contract`
- `Document chat runtime request states`
- `Clarify board hygiene closeout fields`

Avoid titles that combine unrelated outcomes, imply unproven runtime support, or make release-status claims that are not established by the acceptance criteria.

### Workflow lane

Every issue must declare exactly one workflow lane:

- `standard` — routine implementation, wiring, or maintenance with no architectural contract change.
- `architecture-impact` — changes that alter runtime contracts, subsystem boundaries, state models, persistence shape, queue/worker semantics, or public product claims.
- `proof` — validation, audit, runtime evidence gathering, or test-backed confirmation without primary product implementation.
- `docs` — documentation-only work with no code, automation, or runtime behavior changes.
- `marketing` — campaign, positioning, messaging, or audience-facing content work.
- `board-hygiene` — issue cleanup, project board metadata repair, closeout normalization, or task decomposition.

The lane must be declared near the top of the issue body so triage can route it before reading implementation details.

### Context

The issue must provide enough context for Codex to act without needing hidden conversation state. Context should distinguish proven facts from working theories.

Include:

- why the task is being requested now;
- what system, document, or product surface is affected;
- known constraints or non-goals;
- whether the evidence is proven in tests, proven in live runtime, code-path only, or a working theory.

### Target files

The issue must list every expected file or directory Codex should touch. If discovery may change the target list, say so explicitly and constrain the allowed discovery scope.

Required format:

```text
Files:
- path/to/file.md
- path/to/another-file.ts
```

### Explicit ownership line

Every issue must include an explicit line that starts with `This change belongs in` and names the primary destination for the change.

Required format:

```text
This change belongs in path/to/primary-file-or-directory
```

This line acts as the work packet's ownership anchor. If the task has multiple target files, the line should name the primary file, primary directory, or owning subsystem.

### Acceptance criteria

Acceptance criteria must describe observable completion conditions. They should be specific enough for a reviewer to decide whether the task is done without inferring intent from prior chat.

Good acceptance criteria include:

- required headings or fields in a document;
- expected user-visible behavior;
- required runtime state distinctions;
- explicit exclusions for things that must not be changed.

Acceptance criteria must not rely on vague phrases such as "make it better," "clean up," or "modernize" without measurable details.

### Validation commands

Every issue must include validation commands that can be run from the repository root. For docs-only issues, include file existence, content checks, or `git diff --check`, and explicitly state that no automated runtime tests apply.

Required format:

```text
Validation:
- command one
- command two
- No automated runtime tests apply.
```

Backend-oriented work should normally include `pytest -v` or a targeted `pytest -v tests/<path>` command. Frontend-oriented work should normally include `pnpm test` or a targeted `pnpm test -- <pattern>` command. Mixed work should include both unless the issue explains why a narrower check is sufficient.

### Git add command

Every issue must include the exact staging command Codex should run after validation passes.

Required format:

```text
git add path/to/file-or-directory
```

Use the narrowest truthful path list. Do not use `git add .` unless the issue intentionally owns every changed file in the worktree.

### Git commit command

Every issue must include the exact commit command Codex should run after staging.

Required format:

```text
git commit -m "Short imperative commit subject"
```

The commit subject should match the task title unless there is a clear reason to make it more specific.

### Expected closeout fields

Every issue must tell Codex what to report at closeout.

Required closeout fields:

- Summary of changes
- Files changed
- Validation results or explicit `No automated runtime tests apply`
- Git commit hash
- What Axis should add to his KB

Closeout should mention warnings separately from failures. Environment limitations should not be presented as successful validation.

### Board metadata

Every issue must include board metadata so Axis and the project board can route the work packet consistently.

Required board metadata:

- workflow lane;
- priority or sequencing note;
- owner or responsible role;
- status target after Codex completes the task;
- dependencies or blockers, if any;
- review expectation, such as docs review, architecture review, proof review, or standard PR review.

Recommended format:

```text
Board metadata:
- Lane: docs
- Priority: normal
- Owner: Codex
- Target status after completion: Ready for review
- Dependencies/blockers: none
- Review expectation: docs review
```

### Source evidence links

Issues must include source evidence links when they depend on existing docs, prior PRs, runtime behavior, architectural decisions, product claims, or external references.

Recommended format:

```text
Source evidence links:
- docs/path/to/source.md
- https://github.com/org/repo/pull/123
```

If no external or prior evidence is required, say:

```text
Source evidence links:
- None; task is self-contained.
```

## Architecture-Impact Rules

An issue must use the `architecture-impact` lane when it changes, redefines, or makes claims about any of the following:

- provider/runtime state, request/attempt state, or chat transcript integrity;
- queue, worker, broker, retry, timeout, orphan, or replay behavior;
- persistence schema, migration strategy, storage ownership, or data retention;
- API contracts, route semantics, event contracts, or health surfaces;
- subsystem boundaries between frontend, guardian, backend, workers, services, plugins, or codex runner components;
- product claims that imply runtime support, release readiness, reliability, compliance, or production availability;
- board process rules that alter who owns triage, review, closeout, or evidence capture.

An issue may stay out of `architecture-impact` only when it is limited to local wording, narrow implementation, or proof gathering that does not alter a runtime contract, subsystem boundary, public claim, or board governance rule.

If the issue author is unsure whether a task is architecture-impacting, the issue should default to `architecture-impact` and include an explicit review expectation for architecture review.

## Reusable Issue-Body Skeleton

```markdown
# <Imperative issue title>

Workflow lane: <standard | architecture-impact | proof | docs | marketing | board-hygiene>

Context:
<Why this task exists, what is proven, what is a working theory, and what is out of scope.>

Goal:
<The narrow outcome Codex should produce.>

Files:
- <path/to/file-or-directory>

This change belongs in <path/to/primary-file-or-directory>

Acceptance criteria:
- <Observable completion condition>
- <Observable completion condition>
- <Explicit non-goal or boundary, if needed>

Validation:
- <command run from repo root>
- <command run from repo root>
- <No automated runtime tests apply, if docs-only>

If checks pass:
- `git add <path/to/file-or-directory>`
- `git commit -m "<Short imperative commit subject>"`

Expected closeout fields:
- Summary of changes
- Files changed
- Validation results or explicit `No automated runtime tests apply`
- Git commit hash
- What Axis should add to his KB

Board metadata:
- Lane: <lane>
- Priority: <urgent | high | normal | low | sequencing note>
- Owner: <Axis | Codex | reviewer role>
- Target status after completion: <Ready for review | Done | Needs architecture review | Needs proof review>
- Dependencies/blockers: <none or list>
- Review expectation: <standard PR review | docs review | architecture review | proof review>

Source evidence links:
- <path, URL, PR, issue, or `None; task is self-contained.`>
```
