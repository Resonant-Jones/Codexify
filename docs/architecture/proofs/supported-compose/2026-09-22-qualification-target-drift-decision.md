# Supported-Compose qualification target drift decision

## Scope and authority

This is an architecture-impact, inspection-only decision about the next frozen
qualification revision. It performs no Compose, browser, provider, or runtime
qualification and changes no implementation, tests, configuration, ADR, or
release-status source. ADR-069 governs the supported Beta boundary; ADR-074
governs local model-selection authority. The canonical live-proof receipt
contract and the two preceding 2026-09-22 supported-Compose receipts remain
the proof context. `docs/architecture/00-current-state.md` remains the
short-horizon release authority and is not updated here.

The object to select is an immutable Git commit. Git trees and commit patches
are evidence of code identity, not evidence that either revision passes a live
qualification. The earlier repair receipt proves only its bounded static and
live exercises; the earlier full qualification ended `HOLD` before the repair.

## Repository identity at inspection

| Field | Observed value |
| --- | --- |
| Branch | `main` |
| `HEAD` / `main` at initial inspection | `7006ecf740e8056a66bc06ae5be312a7bc52fa42` |
| Upstream | `origin/main` at `7006ecf740e8056a66bc06ae5be312a7bc52fa42` |
| Ahead / behind at initial inspection | `+0 / -0` |
| Old frozen repair | `d3d0c8d6f60f39b28f10f19ef001650045dc53bb` |
| Staged / unstaged / untracked | None at inspection (`git status --porcelain=v2 --branch` reported only branch headers) |
| Local object availability | Both full SHAs passed `git cat-file -e <sha>^{commit}` |

The inspected `main` and upstream initially matched. While this receipt was
being drafted, another actor committed
`a2dcef6d3f8f8f4579c10155a094bd8b47d96cca` (`Enable direct messages in
private preview`) on `main`; the worktree then showed `+1 / -0` against
`origin/main`, with this receipt as its only untracked path. That commit
changes eleven paths, including the private-preview supported profile,
Guardian route/mount, and frontend sharing code. It is **outside** the exact
`d3d0c8d6...` to `7006ecf...` delta authorized for classification here and
does not become a qualification target by implication. The current checkout
at closeout is recorded again below. This task did not make that commit or
mutate any of its files.

## Commit graph and patch relationship

`git merge-base --is-ancestor d3d0c8d6f60f39b28f10f19ef001650045dc53bb
7006ecf740e8056a66bc06ae5be312a7bc52fa42` exited 1:
**NON-LINEAR TARGET DRIFT**. Their merge base is
`6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`. The symmetric difference is
11 commits unique to the old side and 17 unique to the current side.

The current side first adds five Persona Studio commits and merges them with
`9dcf00438fde201d35f604651b9c34d9dd295697`. It then replays eleven
patch-equivalent campaign commits on that tree. `git range-diff` marks each of
the eleven old/current campaign pairs `=`. This establishes patch equivalence
for those commits, not ancestry or a runtime result. The original repair is
therefore a distinct historical commit even though current `main` carries the
same repair patch.

### Intervening commits unique to current `main`

Path IDs `P1`–`P16` resolve to full paths in the net-delta inventory below.
For the merge commit, the path set is its first-parent tree difference;
ordinary `git log --name-status` omits merge path output.

1. `867acb86636da58302dbe0fd1cea37a380340ed0` — Prototype Persona Studio V2 workspace. Changed `P16`. Its added HTML is a standalone Persona Studio V2 prototype.
2. `702c6e27db98187bd35db3c9bcfbfc53a06ca586` — Align Persona Studio V2 prototype with native Codexify styling. Changed `P16`. The HTML/CSS patch restyles that prototype.
3. `89772731d8b60ca01d146b5b95c713d9b6ae837d` — Project Codexify shell into Persona Studio prototype. Changed `P16`. The prototype patch adds native shell composition.
4. `71ea619057afecd6a1943ef60a5c4eff55e305cd` — Replace Persona Studio with V2 workspace. Changed `P1`–`P15`. The diff replaces the page layout, removes its outer `FrameCard` in the Persona Studio branch of `AppShell`, adds a local draft configurator, revises its preview and tests, and rewrites three Persona Studio docs.
5. `44e24e364d2e6705b99fb8df2fd42b7d220d9360` — Fix Persona Studio desktop columns. Changed `P7`, `P10`, `P13`. The page diff adds a container-query grid and column sizing; tests follow that layout.
6. `9dcf00438fde201d35f604651b9c34d9dd295697` — Merge pull request #821 from `design/interface-adjustments`. Its first-parent diff integrates `P1`–`P16`; it introduces no additional net path beyond the five Persona commits.
7. `383baa4d7cb34336f08ad3491a74c4c79366612c` — Record repaired current-tip end-to-end evaluation. Added `docs/architecture/proofs/supported-compose/2026-09-21-current-tip-end-to-end-rerun.md`; proof text only.
8. `6d58153aad068d13023b03c870847e5ec225d42a` — Record repaired current-tip end-to-end evaluation. Modified `docs/architecture/proofs/supported-compose/2026-09-21-current-tip-end-to-end-rerun.md`; proof text only.
9. `4e886f241f1358e0992a4c4710588eafe1f5397f` — Publish 2026-09-22 daily dev log. Added `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; administrative log only.
10. `794b54036016e7c704ee46608567809c54108224` — Refresh weekly current-state override. Modified `docs/architecture/00-current-state.md` and `docs/architecture/README.md`; release/KB text only, not executable proof.
11. `dbeaa5f26a51fa54b4e70a2f71e6cb9798313daa` — Reconcile Guardian terminal task state. Added `docs/architecture/proofs/supported-compose/2026-09-21-guardian-terminal-state-projection-repair.md`; proof text only.
12. `422aeacba2da143bc5b1e8701e5f58dc7b3cdcf2` — Fix Guardian shell terminal projection. Added `docs/architecture/proofs/supported-compose/2026-09-22-guardian-shell-terminal-projection-repair.md`, modified `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, and added `frontend/src/components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx`. The code patch separates provider status presentation from request lifecycle and narrows chat blocking.
13. `c05f649fc5a8b2e8f43eec640fdcca5dbf1937db` — Persist retrieval document provenance. Added `docs/architecture/proofs/supported-compose/2026-09-22-durable-retrieval-provenance-repair.md` and `tests/core/test_retrieval_document_chunk_provenance.py`; modified `guardian/context/broker.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `tests/context/test_retrieval_trace_provenance.py`, and `tests/workers/test_chat_worker_lifecycle_events.py`. The patch carries document/chunk identity through retained retrieval evidence, assistant persistence, and terminal outbox evidence.
14. `177dbc49f56a71b85c12c214941b620f4ad3c5ff` — Reconcile Beta boundary static assertions. Added `docs/architecture/proofs/supported-compose/2026-09-22-backend-static-boundary-reconciliation.md`; modified `tests/architecture/test_beta_release_boundary.py` and `tests/core/test_supported_profile_startup.py`. The diff updates governing assertions without changing runtime source.
15. `98cf17e4a851d2731969b4446276da35dd40b78e` — Stabilize Guardian lifecycle tests. Added `docs/architecture/proofs/supported-compose/2026-09-22-guardian-lifecycle-test-reliability-repair.md`; modified `frontend/src/features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx` and `frontend/src/features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx`. The patch changes lifecycle test setup/expectations, not production source.
16. `9f08cbe3c2fac19e02413817b896d658179fb5d5` — Record final supported Compose qualification. Added `docs/architecture/proofs/supported-compose/2026-09-22-current-tip-final-supported-compose-qualification.md`. That receipt records a `HOLD` on the unavailable exact-model request; it is not a `GO` or proof of this later tree.
17. `7006ecf740e8056a66bc06ae5be312a7bc52fa42` — Enforce explicit local model authority. Added `docs/architecture/proofs/supported-compose/2026-09-22-explicit-local-model-authority-repair.md` and `tests/workers/test_chat_worker_explicit_model_authority.py`; modified `guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `tests/core/test_ai_router.py`, and `tests/test_local_model_default_authority.py`. The patch gates explicit local models against inventory before dispatch and preserves explicit selection metadata.

Rows 7–17 have patch-equivalent old-side counterparts in the same order:
`1fbf2f043117a252bfafe52720725cfc29281e92`,
`3590076c54739b5fd18be11e49ae0f1275d1e3c1`,
`0e434a0cc5d885bef61d0706eef2cb7e356bc64f`,
`0ff840aee769c09621922b0313d0dde88702ac58`,
`75707cb9a5b72e284262829cecac53aa88d344e0`,
`ae6cc6b308e5fc7a4a28956d5a780e26eeef290b`,
`9c6b14fca047203c14daf3fe4032baf630d5b4dc`,
`487b9e076f1e957cb01fd798f95a4e5a464c5607`,
`5da79431fa059b7da80688380550cf29d4854b18`,
`1cbf7a56c6e404d48ec9da46ab8df018ca5a3668`, and
`d3d0c8d6f60f39b28f10f19ef001650045dc53bb`.

## Net tree delta and path classification

`git diff --name-status <old> <current>` reports only these 16 paths: 13
modified and three added. `git diff --stat` reports 3,173 insertions and
3,677 deletions. Each path has exactly one task classification. The three
Persona docs are documentation-only; the remaining 13 are unrelated Persona
product work, including executable frontend code and Persona-specific tests.

| ID | Status | Exact changed path | Classification | Qualification impact |
| --- | --- | --- | --- | --- |
| P1 | M | `docs/architecture/design/persona-studio-design-contract.md` | PROOF / DOCUMENTATION ONLY | Persona design contract changed; no executable drift. |
| P2 | M | `docs/architecture/persona-studio-spec.md` | PROOF / DOCUMENTATION ONLY | Persona specification changed; no executable drift. |
| P3 | M | `docs/architecture/persona-studio.md` | PROOF / DOCUMENTATION ONLY | Persona implementation description changed; no executable drift. |
| P4 | M | `frontend/src/components/persona/layout/AppShell.tsx` | UNRELATED PRODUCT WORK | Executable shared shell file; its changed branch mounts Persona Studio only. It is still frontend bundle drift. |
| P5 | M | `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx` | UNRELATED PRODUCT WORK | Persona route assertion in shared-shell test changed; not a governing chat lifecycle test. |
| P6 | M | `frontend/src/features/personaStudio/PersonaPreviewPanel.tsx` | UNRELATED PRODUCT WORK | Persona preview rendering changed. |
| P7 | M | `frontend/src/features/personaStudio/PersonaStudioPage.tsx` | UNRELATED PRODUCT WORK | Persona page behavior and layout replaced; executable drift. |
| P8 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudio.tabs.test.tsx` | UNRELATED PRODUCT WORK | Persona tab coverage changed. |
| P9 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.persistence.test.tsx` | UNRELATED PRODUCT WORK | Persona draft/save coverage changed. |
| P10 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.render-safety.test.tsx` | UNRELATED PRODUCT WORK | Persona render coverage changed. |
| P11 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.test.tsx` | UNRELATED PRODUCT WORK | Persona page coverage changed. |
| P12 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx` | UNRELATED PRODUCT WORK | Persona shell coverage changed. |
| P13 | M | `frontend/src/features/personaStudio/__tests__/PersonaStudioTwoPaneLayout.test.tsx` | UNRELATED PRODUCT WORK | Persona layout coverage changed. |
| P14 | A | `frontend/src/features/personaStudio/__tests__/personaStudioConfigurator.test.ts` | UNRELATED PRODUCT WORK | New Persona draft configurator coverage. |
| P15 | A | `frontend/src/features/personaStudio/lib/personaStudioConfigurator.ts` | UNRELATED PRODUCT WORK | New local draft configurator; no chat/provider/storage call in the inspected module. |
| P16 | A | `projection-ui-map/persona-studio-v2-prototype.html` | UNRELATED PRODUCT WORK | Standalone design prototype, outside the supported Compose runtime bundle. |

### Qualification-critical comparison

| Surface | Changed? | Classification | Qualification impact |
| --- | --- | --- | --- |
| Backend runtime | No | — | `guardian/` trees match. |
| Chat worker | No | — | Worker implementation matches. |
| Model routing | No | — | Router and explicit-model repair match. |
| Retrieval/provenance | No | — | Broker, completion, worker, and retrieval tests match. |
| Persistence/migrations | No | — | No migration or durable-state path differs. |
| Frontend Guardian path | No direct chat-path delta; shared shell file yes | UNRELATED PRODUCT WORK | Guardian chat component and chat lifecycle tests match; `AppShell` changed only in its Persona Studio branch. The shipped frontend bundle still differs. |
| Supported Compose/config | No | — | No Compose or supported-profile path differs. |
| Governing backend tests | No | — | Backend governing tests match. |
| Guardian lifecycle tests | No | — | The two governing chat lifecycle files match. |
| Dependencies/tooling | No | — | No build, lockfile, or dependency path differs. |
| Architecture docs | Yes, three Persona docs | PROOF / DOCUMENTATION ONLY | No governing ADR or current-state net difference. |
| Proof artifacts | No net difference | PROOF / DOCUMENTATION ONLY | The two 2026-09-22 supported-Compose receipts match in both trees. |
| Dev logs/admin | No net difference | DEV LOG / NON-RUNTIME ADMIN | Patch-equivalent daily log exists in both trees. |
| Unrelated product work | Yes, 13 paths | UNRELATED PRODUCT WORK | Persona Studio executable/test/prototype delta is outside the bounded chat-repair campaign. |

The `git diff --name-only` restriction over `guardian/`, `tests/`, `config/`,
Compose files, `frontend/src/features/chat/`, and the Guardian chat component
and terminal-projection test returned no paths. Thus the campaign's backend,
chat, model, retrieval, configuration, and governing-test trees are identical
between these two revisions. The complete executable frontend trees are
**materially different**: Persona Studio V2 replaces a live route's page,
changes its shared-shell mount, and changes Persona-specific tests. ADR-069
classifies the bounded Persona Studio core as Beta Bounded / Conditional, so
these files cannot be dismissed as harmless merely because the prior chat
proof did not exercise them.

## Campaign admission and decision

The eleven patch-equivalent commits on the `7006ecf...` side include the same
supported-Compose proof, Guardian projection, retrieval provenance, static
assertion, lifecycle-test, and explicit-model repair work already present at
the old frozen repair tree, plus one matching daily administrative log. The
campaign patches are admitted as equivalent copies; the log is administrative.
This is a code/patch identity finding, not a fresh test or runtime acceptance.

The five Persona Studio commits and their merge are **unrelated product work**
relative to the bounded supported-Compose chat-repair question. They are not
admitted into this qualification merely by landing on `main`. Their executable
and Persona-test delta would require its own current-main qualification scope
before evidence could support a current-main release conclusion. The inspected
`d3d0c8d6...` to `7006ecf...` delta shows no accepted ADR contradiction or
unexplained path, but it does not establish that either `7006ecf...` or the
subsequent `a2dcef6...` has passed the Beta bounded Persona surface.

**Decision: `QUALIFY_ORIGINAL_REPAIR`**.

**Selected qualification target:**
`d3d0c8d6f60f39b28f10f19ef001650045dc53bb`.

This retains the deliberate, pre-Persona repair boundary for one complete
supported-Compose qualification. Its eventual result must be labeled
**historical relative to current `main`** and must not be presented as
qualification of `7006ecf740e8056a66bc06ae5be312a7bc52fa42`, the later
`a2dcef6d3f8f8f4579c10155a094bd8b47d96cca`, a supported-runtime `GO` for
current `main`, or a release-status change. Current `main` still needs
separate qualification if a release claim is sought.

## Next execution rule and limits

The single next prerequisite is to run the complete supported-Compose
qualification in a dedicated detached checkout/worktree frozen at
`d3d0c8d6f60f39b28f10f19ef001650045dc53bb`, explicitly labeling the
result historical relative to current `main`. The qualification checkout must
not alter the primary `main` checkout. Its preflight must verify that exact
SHA before image builds and keep proof commits, dev logs, and unrelated
mainline work out of the evaluated tree. No such checkout or qualification
was created or run in this task.

No ADR was changed or requested. No release claim, supported-profile
semantics, or exact-model authority rule was widened. Documentation
follow-through is this decision receipt alone; `00-current-state.md` remains
untouched. No automated runtime tests apply to this inspection-only decision.

## Validation record

| Check | Result |
| --- | --- |
| `git status --porcelain=v2 --branch`; `git rev-parse HEAD main '@{upstream}'` | Recorded before inspection and after the concurrent `a2dcef6...` commit; only this receipt was untracked by this task. |
| `git cat-file -e <sha>^{commit}` for both requested full SHAs | PASS; both local commit objects exist. |
| `git merge-base --is-ancestor <old> <candidate>` | Exit 1; non-linear target drift recorded. |
| `git log --format='%H %s' <old>..<candidate>` and `git log --reverse --name-status <old>..<candidate>` | PASS; 17 current-side commits enumerated with full SHAs and paths. |
| `git range-diff <merge-base>..<old> <merge-base>..<candidate>` | PASS; eleven old/current post-base patches paired `=`. |
| `git diff --name-status <old> <candidate>` and `git diff --stat <old> <candidate>` | PASS; 16 net paths and 3,173 additions / 3,677 deletions recorded. |
| Restricted qualification-surface `git diff --name-only <old> <candidate> -- guardian tests config Compose/chat paths` | Empty; exact tested backend/chat/config surfaces match. |
| `.venv/bin/python scripts/validate_docs.py` | PASS; required architecture docs, README links, and source headings verified. |
| `git diff --check`; `git diff --cached --check` | PASS; no working-tree or staged-proof whitespace errors. |
