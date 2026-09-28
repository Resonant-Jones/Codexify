# Zac Execution Handoff — 2026-09-28

## Why this packet exists

The June collaborator kit was deliberately optimized for exploration. That was useful for learning Codexify, but it did not create a strong completion loop.

This packet is different. It contains three current lanes where a second human adds information that the existing Codex/operator loop cannot cheaply manufacture: independent product friction, real multi-node field reality, and independent live-client proof.

This is **not a backlog buffet**. Choose one primary lane.

## Current Recommendation

### Lane 1 — Preview Human Loop

**Best default if you want to help Codexify become usable by people who are not Chris.**

Use the current Preview as a normal user, without rescuing the experience from the repository or terminal, and return evidence about where the product succeeds, confuses, leaks operator assumptions, or blocks a real task.

See `01-preview-human-loop.md`.

### Lane 2 — Cross-Node Field Lab

**Best fit if the node-meshing problem is the thing you are already thinking about.**

Use the real two-machine environment as a field laboratory for the read-only Git Bridge problem. Produce grounded evidence about the questions a peer-discovery layer must answer and how stale/offline state should be represented before anyone designs synchronization.

See `02-cross-node-field-lab.md`.

### Lane 3 — Scout Live Continuity Proof

**Best fit if you want a concrete iOS/Xcode runtime task with a hard pass/fail gate.**

Exercise the first live authenticated Scout read described by GitHub #815 and capture a clean proof without changing Guardian authentication.

See `03-scout-live-continuity-proof.md`.

## Selection Contract

Before doing work, send back five things:

1. **Lane** — 1, 2, or 3.
2. **Outcome in your own words** — one or two sentences.
3. **First bounded slice** — what you will do before expanding.
4. **Environment / assets** — the machines, account, simulator, or Preview surface you expect to use.
5. **Evidence** — what artifact will prove that first slice happened.

Once selected, stay in that lane until the proof gate is met or a real stop condition appears. Do not silently switch to a more interesting adjacent problem.

## Accountability Contract

A checkpoint is not “worked on X.” Use:

- **Current truth**
- **What changed**
- **Evidence**
- **Blocker / ambiguity**
- **Next move**

For implementation work, GitHub remains the implementation authority. For product/field testing, the report itself is the evidence artifact. Linear tracks the coordination outcome; it should not become a duplicate engineering history.

## What Is Deliberately Not in This Handoff

These are important but are poor uses of an independent collaborator right now because they sit inside active authority-heavy engineering campaigns:

- supported-Compose release qualification and release-claim changes;
- Unified Memory Store / Memory Vault authority decisions;
- Campaign Engine orchestration authority;
- provider/authentication semantics;
- branch convergence or automatic Git synchronization;
- direct pushes to `main` or deployments.

If one of the three lanes uncovers a problem in those areas, report it. Do not absorb it.

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
