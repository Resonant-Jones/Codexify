# Zac Execution Handoff — 2026-09-28

## Why this packet exists

The June collaborator kit was deliberately optimized for exploration. That was useful for learning Codexify, but it did not create a strong completion loop.

This packet is different. It contains current lanes where a second human adds information that the existing Codex/operator loop cannot cheaply manufacture: independent product friction and genuinely separate physical-node evidence.

This is **not a backlog buffet**. Choose one primary lane.

## You Do Not Need To Write Formal Reports While Working

Use Codexify normally. Complain normally. Talk to Luna normally.

The structure is for the agent, not for you.

Give Luna your raw reactions, screenshots, partial thoughts, annoyed commentary, or voice notes. Luna should translate them into the evidence format in `feedback-translator-template.md` without cleaning away what you actually meant.

Unknown stays unknown. Luna must not invent a reproduction step, root cause, severity, or architectural conclusion just to make the report look complete.

## Current Recommendation

### Lane 1 — Preview Human Loop

**Best default if you want to help Codexify become usable by people who are not Chris.**

Use the current Preview as a normal user, without rescuing the experience from the repository or terminal, and return evidence about where the product succeeds, confuses, leaks operator assumptions, or blocks a real task.

See `01-preview-human-loop.md`.

### Lane 2 — Cross-Node Field Lab

**Best fit if the node-meshing problem is the thing you are already thinking about.**

Use the real two-machine environment as a field laboratory for the read-only Git Bridge problem. Produce grounded evidence about the questions a peer-discovery layer must answer and how stale/offline state should be represented before anyone designs synchronization.

See `02-cross-node-field-lab.md`.

## Parked — Scout

Scout exists as an iOS application shell, but the current product does not yet provide a usable connection path for a normal tester to point Scout at a Codexify/Guardian runtime.

That makes the previous Scout live-continuity lane premature. It is not an active Zac lane right now.

The connection/reachability path should be restored or defined through the governed Codex `/goal` development workflow first. After that exists as an actual user-operable surface, Scout live-continuity proof can return as a bounded human lane.

See `03-scout-live-continuity-proof.md` for the parked status and the condition that would reactivate it.

## Selection Contract

Before doing work, send back five things. Luna may produce this from ordinary conversation:

1. **Lane** — 1 or 2.
2. **Outcome in your own words** — one or two sentences.
3. **First bounded slice** — what you will do before expanding.
4. **Environment / assets** — the machines, account, or Preview surface you expect to use.
5. **Evidence** — what artifact will prove that first slice happened.

Once selected, stay in that lane until the proof gate is met or a real stop condition appears. Do not silently switch to a more interesting adjacent problem.

## Accountability Contract

Saved checkpoints use:

- **Current truth**
- **What changed**
- **Evidence**
- **Blocker / ambiguity**
- **Next move**

Again: Zac does not need to remember this syntax. Luna may translate his informal status update into it.

For implementation work, GitHub remains the implementation authority. For product/field testing, the report itself is the evidence artifact. Linear tracks the coordination outcome; it should not become a duplicate engineering history.

## What Is Deliberately Not in This Handoff

These are important but are poor uses of an independent collaborator right now because they sit inside active authority-heavy engineering campaigns:

- supported-Compose release qualification and release-claim changes;
- Unified Memory Store / Memory Vault authority decisions;
- Campaign Engine orchestration authority;
- provider/authentication semantics;
- branch convergence or automatic Git synchronization;
- direct pushes to `main` or deployments;
- repairing Scout's missing connection surface as an ad hoc side quest.

If one of the active lanes uncovers a problem in those areas, report it. Do not absorb it.

## Context

Read `context-map.md` before starting a lane. It records what changed since the September 17 roadmap and which sources are authoritative.

## Stop Conditions

Stop and surface the exact boundary if:

- the lane requires a secret or account not already approved for that task;
- you would need to weaken auth or bypass an access boundary to make the proof pass;
- a peer/node operation would mutate remote Git state or a remote worktree;
- a product test can only continue by using founder-only repository/terminal knowledge;
- the current repository truth contradicts this packet;
- the next step is an architecture decision rather than evidence gathering.

A clean stop with evidence is a valid result.
