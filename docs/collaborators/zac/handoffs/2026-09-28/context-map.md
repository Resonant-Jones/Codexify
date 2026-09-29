# Context Map — 2026-09-28

## What changed since the September 17 roadmap

The earlier Zac roadmap was structurally sound but several lanes changed underneath it.

### Scout

The old roadmap said Scout still needed to become a real iOS application. That is stale.

- GitHub #814 completed the app-target/simulator/root-shell proof.
- GitHub #822 completed the explicit authentication-mode prerequisite.
- GitHub #815 is now the active live-continuity proof lane.

### Product surface

A September 26 product decision clarified that Codexify should expose multiple surfaces over one underlying system:

- **Use Codexify** — client-facing continuity without infrastructure burden.
- **Operate Codexify** — Full Stack/operator authority, observability, routing, and infrastructure.

That makes independent user-path testing more valuable than another round of internal UI opinion.

### Memory / authority

Unified Memory Store work progressed through the internal Memory Vault read/mutation surface and direct user-authored creation. Those are authority-sensitive campaigns with explicit sequencing. They are not a good casual collaborator lane.

### Development orchestration

Codexify now contains a bounded Development Operator goal and Campaign Engine bootstrap goal. The project is increasingly able to select and execute already-authorized engineering work through agent/operator machinery.

That changes the leverage calculation: a second human is most valuable where the machine cannot cheaply supply an independent human perspective or a genuinely separate physical environment.

## Current Human-Leverage Priorities

1. **Independent product friction** — can a person use Preview without founder rescue?
2. **Real multi-node evidence** — what breaks or becomes ambiguous when repository state truly lives on separate machines?
3. **Independent live-client proof** — can Scout cross an actual auth/runtime boundary as specified?

These are the three lanes in this handoff.

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
- #815 — Scout iOS Phase 1: prove live Vault continuity loop
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
- any need for automatic cross-node mutation.

Those are real findings, but they are not scope expansions.
