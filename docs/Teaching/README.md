# Codexify Teaching

This directory contains lessons, presentation outlines, developer onboarding material, and system explanation artifacts for Codexify.

## Derivative status

All Teaching artifacts are **derivative**. They summarize, explain, and contextualize — they do not define. Teaching material must never override or contradict the governing sources of truth.

When in conflict, the following sources win, in order:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/README.md`
3. `docs/architecture/kb-validity-matrix.md`
4. Relevant ADRs and architecture contracts
5. Live runtime evidence on the supported path

## Audience

| Role | Use case |
|------|----------|
| Lead Engineer / Project Manager | System-level orientation, risk communication, build-vs-buy reasoning, supported-path advocacy |
| Implementation developers | Onboarding to runtime loop, retrieval, chat completion, upload pipeline, coding-result return |
| Architecture reviewers | Boundary analysis, contract awareness, trust-model walkthroughs |
| Future contributors | Guided entry into Codexify subsystems, extension seams, and operator surface |

## Teaching stance

The goal of teaching material in this directory is to help people relate to Codexify as a **system** — not a feature list. Lessons should ground every explanation in:

- The **runtime loop**: what runs, where, and when
- **Ownership boundaries**: who is source-of-truth for what state
- The **supported path**: what the current release promise actually covers
- **Operational risks**: queues, config drift, sync durability, federation sensitivity
- **Extension seams**: where developers can plug in without breaking the supported contract

## Source hierarchy

Every lesson, presentation, or onboarding artifact must cite or link back to the governing docs it summarizes. A lesson without source links is not ready for use.

Prefer relative links to files in `docs/architecture/`, `docs/audits/`, and relevant ADRs.

## Do not use this directory for

- Accepted architecture decisions
- Release promises or supported-path definitions
- Runtime contracts
- ADR replacements
- Speculative roadmap claims presented as current truth
- Operator documentation (see `docs/architecture/config-and-ops.md`)
- Health or monitoring contracts
