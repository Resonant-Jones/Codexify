# Zac Collaborator RAG Source

**For:** Zac and Zac's agent  
**Last updated:** 2026-06-26  
**Status:** Active — a compact RAG source directory, not a task backlog

## Purpose

This folder is a compact RAG source for Zac's agent. Zac does not need to manually read the whole Codexify architecture corpus before exploring. This folder helps an agent understand how to explore Codexify and return grounded proposals.

Resonant Jones wants Zac to work from curiosity and inspiration, not assigned ticket grinding. Zac is not expected to hammer through Codexify the same way Resonant does. Zac should be able to point an agent at this one directory and get enough context for exploration, proposal-making, and safe contribution.

## How Zac Should Use It

- Point an agent at this directory.
- Ask the agent to explore an area that feels interesting.
- Ask the agent to produce a proposal before implementation.
- Bring proposals to Resonant when architecture-sensitive boundaries are involved.
- Ask Resonant for constraints when a proposal touches sensitive zones.

## What This Folder Is

- Collaborator orientation.
- Proposal protocol.
- Safe/sensitive zone map.
- Source map into deeper docs.

## What This Folder Is Not

- Not a task backlog.
- Not a complete architecture replacement.
- Not permission to bypass `00-current-state.md`.
- Not permission to change runtime semantics without a contract.
- Not a release promise.

## Directory Contents

| File | Purpose |
|---|---|
| `agent-rag-brief.md` | Main file Zac hands to an agent. Gives the agent its role, rules, and workflow. |
| `exploration-proposal-protocol.md` | Lightweight proposal-before-change workflow. Defines the exploration loop and risk classes. |
| `safe-and-sensitive-zones.md` | Map of where Zac can explore freely and where proposals are required. |
| `proposal-template.md` | Copy-paste template for proposals. |
| `source-map.md` | Deeper pointers into architecture docs, code entrypoints, and sensitive domains. |
| `agent-startup-prompt.md` | Copy-paste prompt Zac can give to an AI agent as the initial instruction. |
| `report-only-agent-lenses.md` | Seven report-only lenses Zac can ask an agent to use for learning the codebase. |
| `report-request-prompts.md` | Copy-paste prompts for each report-only lens plus a general prompt and follow-up proposal prompt. |
| `report-output-templates.md` | Standardized report shapes for directory maps, UI observations, runtime boundaries, test coverage, and Continuity phases. |

## Quick Start: Copy-Paste Prompt

Zac can copy the prompt from `agent-startup-prompt.md` into an AI agent and point the agent at this directory. The agent will orient from the RAG source, explore one area, and produce a scout report/proposal — not implementation. This removes the need to manually summarize the directory each time.

## Suggested Agent Orientation Order

These files are designed for Zac's agent. Zac does not need to read them all manually.

If Zac wants an agent to explore, tell the agent:

1. Read `agent-rag-brief.md` first — this is the agent's operating brief.
2. Read `safe-and-sensitive-zones.md` to know which areas require proposals before changes.
3. Follow `exploration-proposal-protocol.md` to shape any proposals.
4. Use `source-map.md` as a doc/code pointer index.
5. Use `proposal-template.md` to produce a clean proposal.

## Reports Before Proposals

Zac can use report-only lenses while learning the repo. These lenses produce grounded reports — directory maps, UI observations, boundary summaries, test coverage maps — without any implementation or proposal pressure.

Reports are useful even when they do not lead to code changes. They help Zac build a mental map of Codexify step by step. Proposals come later if something still feels worth changing after the report.

## Bottom Line

Zac should follow inspiration and explore what feels alive, awkward, undercooked, or worth improving. Curiosity is welcome. But architecture-sensitive changes require proposal-before-change. This directory helps Zac's agent do that safely.
