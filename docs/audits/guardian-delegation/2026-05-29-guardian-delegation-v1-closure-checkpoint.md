# Guardian Delegation v1 Closure Checkpoint

## Scope

This is a docs-only checkpoint for the internal Guardian Delegation v1 arc.
It consolidates what has landed, what remains internal or flag-gated, what is
explicitly not yet true, and which future branches are safest.

This checkpoint does not change runtime behavior, frontend behavior, backend
routes, tests, database schema, migrations, protocol tokens, UI surfaces,
Command Center behavior, approval/cancel behavior, GitHub context,
intent-spine behavior, or release posture.

## Repository and Branch

| Field | Value |
| --- | --- |
| Working directory | `/Volumes/Dev_SSD/Codexify-main` |
| Git root | `/Volumes/Dev_SSD/Codexify-main` |
| Branch | `codex/create-guardian-delegation-contract` |
| Remote | `origin https://github.com/Resonant-Jones/Codexify.git` |
| Current HEAD at checkpoint authoring | `f59d92b64e825670e4acc5c3ef509ece37e79c05` |

Notable dirty or untracked files observed before this checkpoint:

- `docs/Arcanum/`
- `pi-session-2026-05-27T09-26-58-798Z_019e68c2-35ed-772b-bd9f-a4cbdfad9fd7.html`

These files were pre-existing and are unrelated to this checkpoint.

## Current Arc Summary

```text
Phase 1        Contract
Phase 2A       Intent -> AgentRun seam
Phase 2A+      Selected-turn privacy hardening
DB proof       Clean migration proof
Phase 2B       Local Project KB context
Phase 3        Source-thread result delivery
Phase 3.1      Delivery hardening
Control        Approval/cancel lifecycle
Control+       Approval containment hardening
Observability  Read-only transcript projection API
Observability+ Transcript projection containment hardening
UI             Read-only Command Center transcript viewer
UI+            Viewer containment hardening
```

The arc is coherent as an internal Guardian-owned loop. It should still be read
under `docs/architecture/00-current-state.md`: internal proof does not promote
Guardian delegation into the default supported release surface.

## Commit Ledger

| Phase / slice | Commit hash | Summary | Proof status | Notes / caveats |
| --- | --- | --- | --- | --- |
| Phase 1 | `07d7c7a00635e5b485317e7cf907e0057e3fb0da` | Added the Guardian Delegation Loop Contract. | Docs validation passed for the slice. | Contract only; no runtime implementation claim. |
| Phase 2A | `8d9ae3aef9c2e0388571747f444d523c65dd3e7e` | Added GuardianDelegationIntent intake, selected-turn context basis, scoped auto-approval, and AgentRun linkage. | Focused backend contract proof passed. | Route remained flag-gated; no source-thread result delivery yet. |
| Phase 2A+ | `7587adcac3130e135ac32bcfc9193db52be66123` | Hardened selected-turn privacy so raw personal/conversational text cannot persist into plan/run artifacts. | Focused privacy and protocol-token proof passed. | Fails closed on obvious excluded selected-turn personal context. |
| DB proof | `e11b75a646a8e4c18ba4432492400de84703814e` | Repaired Compose DB health proof and captured clean fresh-DB migration evidence. | Audit artifact reports PASS. | Proves schema/ops path only, not runtime completion. |
| Phase 2B | `ae8d45842598d5394eb5e24abc1968d5d085f2ad` | Added local Project KB context expansion. | Focused backend contract proof passed. | Local/project-bound and policy-filtered only; no GitHub context. |
| Phase 3 | `7ca2099f480bd578ea497349ef533be7638d5d19` | Added Guardian-owned source-thread result delivery. | Focused delivery and migration proof passed. | Source-thread delivery requires explicit lineage and ownership metadata. |
| Phase 3.1 | `d473eae0568d80a9f305667fbf0c83028f39b60e` | Hardened result delivery idempotency, late-cancel handling, and posted-result hygiene. | Focused delivery hardening proof passed. | No schema change; message-level DB uniqueness remains deferred. |
| Control | `b484d141858dcc347ef19a70a1e04bb0ad9fbcfa` | Added backend approval/cancel lifecycle. | Focused approval/cancel contract proof passed. | Backend only; no UI controls. |
| Control+ | `399adbbf3d632b80e1df1b7d193c03d0e29a552b` | Added approval lifecycle containment tests and transaction-safety note. | Focused approval containment proof passed. | PostgreSQL row-lock concurrency not end-to-end proven in SQLite harness. |
| Observability | `20e82332a4d88c24834be410e4013ea5bb5ed2c2` | Added read-only Guardian delegation transcript projection API. | Focused transcript projection contracts passed. | Inspection truth only; no Command Center UI yet. |
| Observability+ | `a47ad377d225128fe50f53170243c581a99cdb83` | Hardened transcript projection tests. | Focused containment proof passed. | Keeps projection read-only and operator-safe. |
| UI | `f536ae58d31e1d55857f7e3677cfc276519913b2` | Added read-only Command Center transcript viewer. | Focused viewer tests passed. | Internal lens only; no mutation controls. |
| UI+ | `f59d92b64e825670e4acc5c3ef509ece37e79c05` | Added viewer containment hardening tests. | Focused viewer and shell tests passed. | Existing neighboring React `act(...)` and key warnings remain outside this slice. |

## What Is Implemented Internally

- `GuardianDelegationIntent` persistence exists for the internal v1 route.
- Selected-turn lineage is preserved by reference.
- Selected-turn privacy hardening prevents raw selected-turn personal or conversational text from being copied into durable plan artifacts.
- Local Project KB context expansion exists for project-bound, policy-filtered sources.
- AgentRun linkage exists through the existing execution backbone.
- Source-thread result delivery exists for Guardian-owned coding runs with explicit lineage.
- Idempotency and delivery hardening exist for result posting and stale/superseded/cancelled suppression.
- Manual approval/cancel lifecycle exists behind the Guardian delegation route boundary.
- Read-only transcript projection API exists for one Guardian delegation intent.
- Read-only Command Center transcript viewer exists as an internal inspection lens.

## What Remains Explicitly Not Implemented

- GitHub context is not implemented for Guardian delegation.
- Command Center mutation controls are not implemented.
- UI approve/cancel controls are not implemented.
- Intent-spine unification is not implemented.
- Broad autonomous execution is not implemented.
- Broad "answer as me" authority is not implemented.
- Release-surface promotion is not implemented.
- Multi-worker/concurrent PostgreSQL proof for approval idempotency is not complete.
- Full frontend suite/typecheck remediation is not complete.
- A broader Command Center product surface is not complete.

## Current Safety Rails

- Guardian delegation routes remain internal and flag-gated.
- The source thread remains user truth.
- Transcript projection is inspection truth only.
- Project KB context is local, project-bound, and policy-filtered.
- Raw selected-turn text is not persisted into plan artifacts.
- Result delivery requires explicit Guardian ownership and source-thread/source-message/run lineage.
- Approval/cancel state, execution state, visibility state, and transcript projection remain separate truths.
- The Command Center viewer is read-only and does not call mutation endpoints.

## Known Caveats

- Approval idempotency relies on PostgreSQL `SELECT ... FOR UPDATE` row-lock semantics, but the local contract harness proves sequential behavior through SQLite rather than true concurrent PostgreSQL behavior.
- Broader frontend test/typecheck issues were treated as repo-wide or environmental and were not fixed in this arc.
- React `act(...)` warnings and a neighboring key warning remain in Command Center-adjacent tests.
- The current UI viewer is an internal read-only lens, not Command Center product completion.
- Route flag-off and default release posture still govern interpretation.

## Recommended Next Branches

### A. `Command Center UI Phase 2: read-only refinement`

- Improve viewer ergonomics.
- Add zero-event, equal-timestamp, and malformed-event tests.
- Keep mutation controls out of scope.

### B. `Approval UI controls`

- Start only after an explicit decision.
- Add approve/cancel buttons against the existing backend lifecycle.
- Preserve backend authority and the Guardian delegation route flag posture.

### C. `GitHub context Phase 2C`

- Add configured GitHub context only after the local KB path remains stable.
- Keep context provenance explicit.
- Do not include personal chat history.

### D. `Live supported-path proof`

- Run an end-to-end local Compose proof for the internal Guardian delegation route when intentionally enabled.
- Record route-flag posture, thread lineage, AgentRun linkage, result delivery, and transcript projection.
- Do not treat live internal proof as release promotion by itself.

### E. `Frontend test/typecheck remediation`

- Use a separate cleanup branch for repo-wide frontend warnings and typecheck issues.
- Keep that branch separate from Guardian delegation feature work.

## Recommended Immediate Next Step

If the operator intends to use this loop locally, the safest next step is a live
supported-path internal proof with the Guardian delegation route intentionally
enabled and the release boundary explicitly recorded.

If not, pause feature work and review the current branch state before choosing
the next branch. Do not promote Guardian delegation to the default release
surface from this internal arc alone.

## Validation

Validation commands for this docs-only checkpoint:

```sh
python3 scripts/validate_docs.py
git diff --check
```

No automated runtime tests apply because this checkpoint changes only an audit
document.

## Final Status

- Guardian Delegation v1 internal loop: coherent and proof-backed.
- Release surface: not promoted.
- Command Center UI: read-only Phase 1 only.
- Next work: requires explicit branch/task decision.
