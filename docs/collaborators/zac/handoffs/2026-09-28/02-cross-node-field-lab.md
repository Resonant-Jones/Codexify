# Lane 2 — Cross-Node Field Lab

## Outcome

Use a real two-node development environment to produce field evidence for the read-only cross-node Git discovery contract in GitHub #796.

The goal is to answer: **what does an agent or operator actually need to know about repository state on another trusted node before any synchronization is allowed?**

## Authority Boundary

GitHub #796 is the governing issue.

This lane gathers evidence. It does not authorize automatic synchronization, remote worktree mutation, pull/push, merge/rebase, cherry-pick, remote command execution, or a new transport authority.

Tailscale or another private transport may be present. Transport is not Git authority.

Zac's existing execution-node and append-only event-log experiments may be useful observations here, but they are not automatically Codexify architecture or authority. Describe what exists; do not silently promote the experiment into the product contract.

## First Bounded Slice

Choose two trusted machines that already participate in the development environment. Give them neutral aliases in the report; do not publish private addresses or credentials.

Record the minimum topology:

- node alias;
- repository identity/path;
- currently visible branch/ref;
- whether the peer is reachable;
- how reachability is established at a high level.

Then answer three real read-only questions using the environment you already have:

1. **Existence:** does the peer have a specific commit, ref, or path that the local node does not?
2. **Divergence:** how can a human tell that the two nodes have different valid unpublished repository state?
3. **Provenance:** how should the answer distinguish local, peer-local, and GitHub-published state?

Finally, deliberately observe one unavailable/stale condition: disconnect a peer from the test path or use an already unavailable state without destroying work. Record what a truthful system should say instead of treating the peer as empty.

## Feedback Intake

Do not try to narrate this like an architecture document while testing it.

Tell Luna what you tried, what surprised you, what was annoying, what required a weird workaround, what you could not tell, and what you think might matter.

Luna should translate that into the field-report structure using `feedback-translator-template.md`.

The translation must distinguish:

- observed machine/repository facts;
- Zac's interpretation;
- hypotheses about what Codexify should do;
- unresolved questions.

If the JSONL/event-log experiment is relevant, record it as an observed mechanism with its role and limits. Do not call it canonical Codexify state unless repository authority establishes that.

## Evidence Artifact

Create:

`docs/collaborators/zac/reports/YYYY-MM-DD-cross-node-field-lab.md`

Include:

- sanitized topology;
- the three concrete discovery questions;
- actual observations;
- what metadata was sufficient or missing;
- stale/offline behavior;
- moments where the workflow tempted you to mutate rather than observe;
- any difference between what Tailscale/network reachability tells you and what Git repository truth tells you;
- translated feedback records for important friction or ambiguity.

If the evidence implies a useful change to #796, add a final **Contract Delta Proposal** section. Do not implement the bridge in this lane.

## Proof Gate

The first slice is complete when:

- two nodes are represented without exposing secrets;
- at least three real Git discovery questions have evidence-backed answers;
- local, peer-local, and published state are distinguishable in the report;
- stale/offline behavior is demonstrated or truthfully bounded;
- all observations were read-only with respect to remote Git/worktree state.

## Stop Conditions

Stop if the next useful step would require:

- changing remote refs or worktrees;
- automatic sync;
- arbitrary remote shell automation unrelated to Git object discovery;
- inventing a new repository authority;
- choosing a canonical ADR number from an unconverged node view.

Those are architecture decisions, not field evidence.

## Why this is a good human lane

The repository can define a clean protocol on paper. A second person with a genuinely separate machine exposes the awkward questions that only appear when state is actually distributed.
