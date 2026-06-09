# Campaign Runner Intention Packet

This packet is operator-authored planning input for Campaign Runner Stage A audit and Stage B campaign compilation. It is not runtime proof, is not an ADR, and cannot override schemas, runner-owned constraints, provider governance, Guardian ownership, Pi boundaries, or `docs/architecture/00-current-state.md`.

Unsupported or unproven claims in this packet must become discovery findings, not implementation assumptions.

## Packet Metadata

- Packet title: `<replace with a short name>`
- Author/operator: `<replace with operator name or role>`
- Date: `<YYYY-MM-DD>`
- Intended repo/root: `<replace with repo path or repo name>`
- Related contracts or ADRs: `<replace with governing docs, if any>`
- Intended runner usage: `--intention-packet-file <path-to-this-packet>`

## Objective

State the narrow planning objective Campaign Runner should audit and compile around.

Replace this with one or two concrete sentences. Avoid broad product goals that cannot be audited from repository evidence.

## Why This Matters

Explain why this objective is worth auditing now.

Replace this with the operator context, risk, dependency, or decision pressure that makes the packet useful.

## Scope

List the repository areas, contracts, flows, tests, or docs that Stage A should inspect first.

- `<repo path, subsystem, or contract>`
- `<repo path, subsystem, or contract>`
- `<repo path, subsystem, or contract>`

## Out of Scope

List anything Campaign Runner must not turn into findings, campaigns, or tasks for this packet.

- `<excluded behavior, surface, or claim>`
- `<excluded behavior, surface, or claim>`
- `<excluded behavior, surface, or claim>`

## Evidence Requirements

Define what evidence Stage A must collect before making claims.

- Use repo paths, line references, tests, schemas, contracts, or existing artifacts.
- Separate repo-grounded evidence from operator intent.
- Mark explicit unknowns when evidence is missing or contradictory.
- Treat unsupported or unproven claims as discovery findings, not implementation assumptions.

## Stage A Audit Posture

Describe how Stage A should read the repo under this objective.

- Audit against this packet, but keep `mega_audit_output.schema.json` authoritative.
- Preserve runner-owned constraints and JSON-only output requirements.
- Separate implemented behavior from future planning language.
- Prefer discovery-only findings when repository evidence does not support implementation.

## Stage B Campaign Posture

Describe how Stage B should compile campaigns from Stage-A findings.

- Use this packet only to interpret and filter Stage-A evidence.
- Synthesize only campaigns and tasks supported by Stage-A evidence.
- Keep campaign and task scope independently mergeable.
- Prefer discovery tasks over speculative implementation when evidence is insufficient.

## Task-Lane Expectations

Describe expectations for generated task classification, scope, and proof surface.

- Use architecture-impact classification when contracts, provider governance, Guardian ownership, Pi boundaries, schemas, or release-truth interpretation are touched.
- Keep each task self-contained, testable, and independently mergeable.
- Include validation expectations that match the touched files.
- Do not add git instructions to generated tasks unless the active task artifact contract safely supports them.

## Release-Truth Constraints

State the release-truth boundaries that must govern this packet.

- `docs/architecture/00-current-state.md` remains authoritative for current release truth.
- This packet cannot prove runtime support, shipped behavior, provider support, UI dispatch, lease allocation, live agent execution, merge automation, or autonomous self-modification.
- Do not widen release claims from docs, examples, route presence, prompt language, or operator intent.

## Success Criteria

List what a good Stage A and Stage B result would accomplish.

- `<replace with evidence-backed success criterion>`
- `<replace with evidence-backed success criterion>`
- `<replace with evidence-backed success criterion>`

## Failure / Stop Conditions

List conditions where Campaign Runner should stop, emit discovery findings, or avoid campaign generation.

- Evidence is missing, contradictory, or only aspirational.
- The requested objective would require runtime behavior outside current release truth.
- The objective would require changing schemas, provider behavior, Pi broker semantics, queues, workers, routes, databases, or UI outside this packet's scope.
- `<replace with packet-specific stop condition>`

## Notes for Operator Review

Add any final operator reminders before running Campaign Runner.

- Confirm this packet is plain Markdown and contains no secrets.
- Confirm base prompt templates do not need one-off edits for this target.
- Confirm the packet path passed to `--intention-packet-file` is the completed copy, not this untouched template.
