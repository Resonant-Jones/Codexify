# Paul Proposal Template

Copy this template, fill it in, and bring it to Resonant if the risk is Medium or High.

---

## Proposal Title

A short, descriptive title for the proposed change.

## Area Explored

Which part of Codexify did this study focus on?

## What Caught My Attention

Describe the specific observation, friction, or opportunity. Be concrete.

## Why It Matters

Explain the impact. Who benefits? What gets better?

## Evidence Observed

What did you inspect? List specific files, docs, tests, or live behaviors that support the observation.

## Files/Modules Likely Involved

List the files or modules the change would likely touch. Include paths.

## Risk Classification

- [ ] Low - copy, docs, small UI polish, local component styling, no runtime meaning.
- [ ] Medium - behavior changes, settings, API touchpoints, local state, test harnesses.
- [ ] High - runtime semantics, identity, memory, retrieval, provider routing, auth, export/restore, profiles, Continuity, Project Pulse, worker/queue semantics.

## Proposed First Move

What is the smallest, most atomic first task? This should be testable, commit-ready, and scoped to one focused change.

## What I Will Not Touch

Be explicit about boundaries. What is this proposal not changing?

## Questions for Resonant

List anything you need clarity on before proceeding: constraints, deferred features, cross-module concerns, ADR alignment questions.

## Suggested Validation

How would you prove this change is correct? What test commands, manual checks, or live proof would verify the change?

## Suggested Codexify Task Lane

- [ ] Standard - low risk, no architecture implications.
- [ ] Architecture-Impact - medium or high risk, touches architecture-sensitive zones.
- [ ] Docs-only - documentation changes with no runtime implementation.
