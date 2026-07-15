# Axis Node Collaboration Protocol

## Roles and approval

Resonant Jones and Zac are human collaborators, authors, reviewers, and final approval authorities. An Axis instance is an evidence-grounded reasoning participant. Future collaborators may propose sources or work but must preserve the same authority boundaries. Models recommend; humans decide and approve. Proposal precedes sensitive change.

## Collaboration states

| State | Meaning | May authorize implementation? |
|---|---|---|
| Exploration | Learn or inspect without commitment. | No |
| Report | Evidence and observations. | No |
| Proposal | Suggested change and rationale. | No |
| Decision | Human-recorded choice. | Only when it explicitly authorizes it |
| Codexify task | One complete, scoped work packet. | Yes, when human-selected |
| Implementation | Bounded execution of an approved task. | N/A |
| Proof | Evidence for one stated surface. | No |
| Release claim | Current-state assertion backed by appropriate proof. | No |

Record collaborator disagreement as distinct positions, sources, unresolved questions, and the approving decision; never infer a merged position. Decisions become durable through reviewed repository documents, ADRs, task records, or other explicitly governed artifacts.

## Context, sources, and access

Personal context is separate from project truth and cannot silently become shared or durable. Propose source additions with path, tier, authority, purpose, status, and non-proof boundary. Mark stale documents rather than silently reclassifying them. An Axis instance must disclose uncertainty, unavailable repository access, missing required files, and the source revision or commit it reasoned from when available.

Reports and proposals remain non-executing. A task is not proof; implementation is not a release claim; and proof is bounded to what it exercised.
