# Zac Collaborator RAG Source

**For:** Zac and Zac's agent  
**Last updated:** 2026-09-29
**Status:** Active — orientation resources plus bounded execution handoffs

## Purpose

This folder is Zac's compact entrypoint into Codexify. It exists so a person or agent can orient from a bounded source set instead of reconstructing the project from the full architecture corpus.

The original June 2026 resources were intentionally exploration-first: reports before proposals, curiosity before ticket grinding. That mode remains useful. It is no longer the only mode.

## Two Collaboration Modes

### 1. Exploration / report mode

Use the existing report lenses when the goal is to learn, map, critique, or investigate without committing to implementation.

- Read `agent-rag-brief.md`.
- Use `report-only-agent-lenses.md` and `report-request-prompts.md`.
- Save grounded learning artifacts under `reports/`.
- Reports are not tasks, approvals, or architecture authority.

### 2. Execution handoff mode

When Chris sends a dated handoff, the handoff defines one bounded outcome with an evidence gate.

Start from the newest dated packet under `handoffs/`. A handoff may ask for product testing, field evidence, runtime proof, a proposal, or implementation. Its scope and stop conditions override the older exploration-first posture for that lane.

Current handoff:

- `handoffs/2026-09-28/README.md`

The rule is simple: **one primary lane at a time, evidence before expansion**.

## Feedback Does Not Need To Be Formal

Zac does not need to remember the report schema while using Codexify.

He can complain, narrate, voice-dump, paste screenshots, or describe what felt wrong in ordinary language. His assistant can translate that raw feedback into the project format afterward using:

- `handoffs/2026-09-28/feedback-translator-template.md`

The translator must preserve uncertainty and must not invent reproduction steps, causes, severity, or product intent. The human experience is the source material; formatting is an agent task.

## Authority Order

For any Codexify claim or task, use this order:

1. `docs/architecture/00-current-state.md` for current operational and release truth.
2. The authoritative GitHub issue / accepted architecture contract for the chosen lane.
3. The dated handoff packet for coordination, proof shape, and stop conditions.
4. Older collaborator reports and planning docs for background only.

If these conflict, stop and surface the conflict instead of reconciling it by assumption.

## Directory Contents

| Path | Purpose |
|---|---|
| `agent-rag-brief.md` | Exploration-mode agent brief. |
| `agent-startup-prompt.md` | Copy-paste exploration startup prompt. |
| `exploration-proposal-protocol.md` | Proposal-before-change workflow. |
| `safe-and-sensitive-zones.md` | Historical risk map; verify against current state before relying on it. |
| `proposal-template.md` | Proposal template. |
| `source-map.md` | Historical orientation map; dated 2026-06-26. |
| `report-only-agent-lenses.md` | Report-only exploration lenses. |
| `report-request-prompts.md` | Report prompts. |
| `report-output-templates.md` | Standard report shapes. |
| `reports/` | Learning-artifact archive. |
| `handoffs/` | Dated execution packets with outcomes, evidence gates, and stop conditions. |
| `handoffs/2026-09-28/feedback-translator-template.md` | Agent template for turning informal Zac feedback into evidence without requiring Zac to format it. |

## Execution Checkpoint Format

For an active handoff, the saved checkpoint should be compact:

- **Current truth** — what is true now.
- **What changed** — what was actually completed.
- **Evidence** — screenshot, trace, report, commit, test output, or runtime proof.
- **Blocker / ambiguity** — only if one exists.
- **Next move** — the next bounded action.

Zac does not need to speak in this format. His assistant may translate an informal update into it.

Do not replace evidence with an activity log.

## General Stop Conditions

Stop and ask rather than improvise when:

- current truth conflicts with the handoff;
- a step requires a credential, permission, account, node, or provider access that has not been explicitly supplied;
- the work would change identity, memory, auth, provider, queue/worker, release, or architecture authority beyond the lane's contract;
- a task would require pushing to `main`, deploying, widening a release claim, or mutating another node without explicit authorization;
- the proof invalidates a premise that the next step depends on.

## Bottom Line

Exploration is still welcome. Active collaboration is now more explicit: when a dated handoff exists, choose one lane, complete the bounded proof or reach a real stop condition, and return evidence. Curiosity can determine *how* the lane is approached; it does not replace the outcome.
