# Paul Collaborator Study Lane

**For:** Paul Dukes and Paul's agent
**Last updated:** 2026-06-29
**Status:** Active - a compact study lane, not a task backlog

## Purpose

This folder is a compact, agent-readable study lane for Paul. It is tuned to the June 28 Codexify thread: study the repository, ask why modules exist, and build a grounded first path without having to absorb the whole architecture corpus or a pile of philosophy emails.

Paul's starting point should be one area, one report, one clear next question. When memory, identity, provenance, or long-lived context are in view, use the BIOME/CORAL lens: what persists, what is derived, what is intentionally forgotten, and what can be reconstructed later from evidence.

## How Paul Should Use It

- Start with `agent-startup-prompt.md`.
- Use `source-map.md` to choose the first study path.
- Use `report-request-prompts.md` to ask for a single grounded study report.
- If a report shows a change that is still worth pursuing, convert it into a proposal with `proposal-template.md`.

## What This Folder Is

- A first path for architecture study.
- A compact prompt set for one area at a time.
- A memory-aware orientation layer for long-lived context surfaces.
- A proposal bridge when a report uncovers a real change.

## What This Folder Is Not

- Not a task backlog.
- Not a release promise.
- Not permission to skip `docs/architecture/00-current-state.md`.
- Not permission to change runtime behavior without a proposal.
- Not a substitute for the architecture docs.

## Directory Contents

| File | Purpose |
|---|---|
| `agent-rag-brief.md` | Operating brief for the agent Paul points at this lane. |
| `agent-startup-prompt.md` | Copy-paste prompt for the first agent instruction. |
| `exploration-proposal-protocol.md` | Study-to-proposal workflow and risk classes. |
| `proposal-template.md` | Proposal shape for a later change request. |
| `report-output-templates.md` | Standard report shapes for Paul's study prompts. |
| `report-request-prompts.md` | Copy-paste prompts for the first study report and memory study. |
| `safe-and-sensitive-zones.md` | Where a report can stay local and where it must stop. |
| `source-map.md` | First-path map into architecture docs and code entrypoints. |

## Quick Start

Paul can copy the prompt from `agent-startup-prompt.md` into an AI agent and point the agent at this directory. The agent should start with the source map, pick one area, and produce one grounded study report before anything else.

## Suggested Orientation Order

1. `README.md`
2. `agent-rag-brief.md`
3. `agent-startup-prompt.md`
4. `source-map.md`
5. `report-request-prompts.md`
6. `report-output-templates.md`
7. `exploration-proposal-protocol.md`
8. `safe-and-sensitive-zones.md`
9. `proposal-template.md`

## Bottom Line

This lane is for architecture study first. It keeps the first move small, specific, and repeatable so Paul can enter the repo with a clear path instead of a cloud of background material.
