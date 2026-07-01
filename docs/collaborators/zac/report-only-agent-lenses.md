# Zac Report-Only Agent Lenses

**For:** Zac and Zac's agent  
**Last updated:** 2026-06-26  
**Status:** Active — report-only orientation layer, not a task backlog

## Purpose

These are report-only lenses Zac can ask an agent to use. They help Zac learn Codexify without processing the whole repo at once. Each lens gives the agent a narrow focus — map a directory, observe a UI surface, describe a boundary — and produces a report, not a code change.

These lenses are inspired by layered agent identity/persona workflow, but they are **not Codexify runtime personas**. They are collaborator-facing documentation that splits one large codebase into smaller modes of attention. No runtime system, identity layer, or product feature is being claimed.

The goal: reduce overwhelm. Zac can learn Codexify step by step, building a mental map through grounded, evidence-backed reports before ever feeling pressure to change anything.

## How To Use These Lenses

1. **Pick one lens** from the list below. Choose whatever matches what Zac feels curious about or confused by.
2. **Point the agent** at `docs/collaborators/zac/` as its RAG source.
3. **Ask for one report only.** Use a prompt from `report-request-prompts.md`.
4. **Do not ask for implementation in the same run.** Reports and proposals are separate.
5. **Use the report to build familiarity.** Read it. Sit with it. Ask follow-up questions.
6. **Ask Resonant for constraints** before converting anything from a report into a task.

## Report-Only Rule

- Report first.
- No implementation.
- No edits.
- No pull request.
- No Codexify task unless Resonant later asks.
- No architecture-sensitive changes.

A report can observe boundaries. It cannot cross them.

## Lens: Cartographer

**Purpose:** Map a directory, subsystem, or module.

**Best for:** Understanding where files are and how they connect.

**When Zac says:** "I don't know where anything lives." "What does this directory do?" "How are these files related?"

**Output:**
- Directory map showing main files and their roles.
- Important flows through the subsystem.
- Related tests and docs.
- Open questions about structure or naming.
- What not to infer from the map alone.

## Lens: Doc Gardener

**Purpose:** Understand docs and identify opportunities for clarity later.

**Best for:** Finding stale wording, missing orientation, duplicated explanations, or confusing docs.

**When Zac says:** "These docs are confusing." "I don't know where to start reading." "Is this doc still accurate?"

**Output:**
- Docs map showing which docs cover which topics.
- Clarity issues — stale, ambiguous, duplicated, or missing content.
- Suggested future doc improvements.
- No edits unless later requested by Zac or Resonant.

## Lens: UI Naturalist

**Purpose:** Observe frontend surfaces, affordances, labels, empty states, and visual feel.

**Best for:** UI familiarity and product feel.

**When Zac says:** "What does the UI look like?" "Does this label make sense?" "What happens when there's no data?"

**Output:**
- Screen/component map showing what is visible and how it connects.
- Rough edges — confusing labels, missing affordances, awkward flows.
- Questions about user intent or product behavior.
- Low-risk polish candidates (copy fixes, empty-state improvements, visual alignment).

## Lens: Runtime Boundary Scout

**Purpose:** Identify architecture-sensitive boundaries without changing them.

**Best for:** Auth, routing, provider behavior, retrieval, memory, identity, Continuity, export/restore, worker/queue semantics.

**When Zac says:** "What are the dangerous parts?" "Where should I be careful?" "What contracts govern this area?"

**Output:**
- Boundary summary — what is governed, by which contracts.
- Governing docs and ADRs.
- Current runtime truth vs deferred or planned behavior.
- Risk notes explaining why the boundary exists.
- Proposal-before-change warnings for each boundary.

## Lens: Dev-Experience Mechanic

**Purpose:** Understand local setup, scripts, tests, build flow, and friction.

**Best for:** Making future setup easier and understanding the developer workflow.

**When Zac says:** "How do I run this locally?" "What commands are available?" "Why is setup slow?"

**Output:**
- Commands map — `make`, `pnpm`, `docker compose`, `uvicorn`, test commands.
- Friction points — slow steps, confusing env vars, missing documentation.
- Confidence checks — which commands prove the system is working.
- Possible low-risk docs/script candidates for later improvement.

## Lens: Test Cartographer

**Purpose:** Map test coverage and validation seams.

**Best for:** Understanding how Codexify proves behavior.

**When Zac says:** "What is actually tested?" "How do I know this works?" "Where are the gaps?"

**Output:**
- Relevant test files for the inspected area.
- What each test suite proves.
- What each test suite does not prove.
- Missing confidence — areas without test coverage.
- Gaps to ask Resonant about before filling.

## Lens: Continuity Museum Guide

**Purpose:** Explain the completed Continuity operator phase in plain language.

**Best for:** Understanding the recent workstream without changing it.

**When Zac says:** "What is this Continuity thing everyone keeps talking about?" "Why does it matter?" "Why is it quarantined?"

**Output:**
- What exists — the six-route operator surface in plain terms.
- Why it matters — architectural significance and future potential.
- Gates — profile quarantine, feature flag, API key auth.
- Release boundaries — what is and is not supported beta.
- What not to touch — no expansion without a new contract.

## Choosing A Lens

| If Zac… | Use this lens |
|---|---|
| Feels lost in files | Cartographer |
| Finds docs confusing | Doc Gardener |
| Wants to understand product feel | UI Naturalist |
| Is near risky runtime meaning | Runtime Boundary Scout |
| Wants setup/test clarity | Dev-Experience Mechanic |
| Wants proof/testing context | Test Cartographer |
| Wants to understand the recent Continuity work | Continuity Museum Guide |

Zac does not need to pick the "right" lens. Any lens that reduces the cognitive load is a good lens. Run multiple reports over time to build a layered mental map.

## What Reports Should Avoid

- Do not recommend implementation unless Zac explicitly asks.
- Do not bundle multiple semantic surfaces into one report.
- Do not claim unsupported behavior as if it is shipped.
- Do not turn exact readback into search/traversal claims.
- Do not treat old docs as current truth — check `00-current-state.md`.
- Do not skip `00-current-state.md` for runtime claims.
- Do not imply that a report finding is itself a task.
- Do not invent file contents, routes, or behaviors not visible in the repo.

## How A Report Can Become A Proposal Later

Reports are orientation. Proposals are intent. The path from one to the other is deliberate:

1. Zac reads a report and something still feels worth changing.
2. Zac asks the agent to produce a proposal using `proposal-template.md`.
3. The proposal classifies risk (Low / Medium / High).
4. Medium/high-risk proposals need Resonant's constraints.
5. Architecture-sensitive proposals need the Architecture-Impact task lane.
6. Only after constraints and lane selection does a Codexify task prompt get written.

A report can sit. A report can be read and forgotten. A report that never becomes a proposal is still valuable — it built Zac's mental map.
