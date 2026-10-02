# Context Map — 2026-09-29

## What changed since the September 17 roadmap

The earlier Zac roadmap was structurally sound but several lanes changed underneath it.

### Scout

The old roadmap said Scout still needed to become a real iOS application. That is stale, but the September 28 handoff then moved too quickly in the other direction.

- GitHub #814 completed the app-target/simulator/root-shell proof.
- GitHub #822 completed an authentication-mode prerequisite in code.
- GitHub #815 describes the intended live-continuity proof.
- Current product observation on 2026-09-29: Scout still does not expose a usable connection path that lets an ordinary tester point the app at a Codexify/Guardian runtime and proceed with the #815 proof.

Therefore Scout is **parked as a Zac lane** until the connection path is restored or defined through the governed Codex `/goal` development workflow.

This is a useful distinction:

- the app shell exists;
- some underlying auth/runtime work exists;
- the human-usable connection workflow does not yet exist.

Do not collapse those into "Scout is ready for live testing."

### Product surface

A September 26 product decision clarified that Codexify should expose multiple surfaces over one underlying system:

- **Use Codexify** — client-facing continuity without infrastructure burden.
- **Operate Codexify** — Full Stack/operator authority, observability, routing, and infrastructure.

That makes independent user-path testing more valuable than another round of internal UI opinion.

### Memory / authority

Unified Memory Store work progressed through the internal Memory Vault read/mutation surface and direct user-authored creation. Those are authority-sensitive campaigns with explicit sequencing. They are not a good casual collaborator lane.

### Development orchestration

Codexify now contains a bounded Development Operator goal and Campaign Engine bootstrap goal, including a governed Codex `/goal` operator contract.

That changes the leverage calculation: a second human is most valuable where the machine cannot cheaply supply an independent human perspective or a genuinely separate physical environment. Internal implementation recovery, such as Scout's missing connection path, should stay inside the governed development-operator lane unless explicitly handed off.

### Zac feedback intake

Formal reporting syntax is no longer a human requirement.

Zac may provide raw comments, screenshots, voice notes, or informal complaints. Luna can translate them using `feedback-translator-template.md` while preserving facts, uncertainty, and Zac's actual meaning.

## Current Human-Leverage Priorities

1. **Independent product friction** — can a person use Preview without founder rescue?
2. **Real multi-node evidence** — what breaks or becomes ambiguous when repository state truly lives on separate machines?

These are the two active lanes in this handoff.

Scout live proof is parked pending an actual connection path.

## Current Repository Truth

Read first:

- `docs/architecture/00-current-state.md`

As of its 2026-09-24 update:

- `main` remains in local-first Beta hardening with a gated private-preview lane;
- the latest complete supported-Compose qualification remains `HOLD`;
- account import has bounded materialization/vector evidence but not a complete natural import-to-recall proof;
- current release blockers remain owner/operator qualification work;
- branch-local UMS progress does not automatically widen `main`, Preview, or Beta claims.

## Authoritative GitHub Issues

- #796 — Define read-only cross-node Git Bridge discovery
- #815 — Scout iOS Phase 1: intended live Vault continuity loop; currently blocked as a Zac lane by the missing user-operable connection path
- #644 — OpenAI artifact import (still open, but not selected for this handoff)
- #555 — golden runtime doctor (still open, but not selected for this handoff)

## Notion Context

- Zac Collaboration Roadmap — Codexify, September 2026
- Codexify Hosted Service Launch Plan
- Codexify Product Surface Split — Client, Full Stack, and Domain Workspaces
- Codexify: Scout — iOS Continuity & App Intents Framework
- Codexify Vertical Surfaces — Industry Product Matrix

Notion supplies product intent and the larger map. It does not override current runtime truth or GitHub implementation contracts.

## Coordination

Linear RES-6 tracks lane selection and handoff. GitHub owns implementation contracts and evidence. The report archive in this directory owns non-code field/product evidence.

## Things to report, not absorb

If any lane discovers one of these, stop at the evidence boundary and hand it back:

- release-qualification failures;
- Memory Vault / identity / persona authority questions;
- provider or authentication semantics;
- Campaign Engine authority gaps;
- branch/publication convergence;
- any need for automatic cross-node mutation;
- Scout connection-path implementation work not explicitly handed off.

Those are real findings, but they are not scope expansions.
