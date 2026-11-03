# Saved Widget Main Rebase Compatibility Check - 2026-10-28

**Result: PASS (rebase execution and compatibility verification only).**

- **Original branch tip (pre-rebase):** `606d748c3707e1e9ce6eafbccd5b7499bbd928e3`
- **Original qualified source (evaluated SHA):** `3571556894c3707069b3e0c348e8eb5049efb243`
- **Verified upstream tip:** `bceac5b57f112a74bb7c8a4aa2dd73b05c917db1`
- **Rebased branch tip:** `4560339184b685f00f42ea31bd5fbbe07068fbe8`
- **Branch:** `integrate/saved-widget-consent-aware-20261027`
- **Worktree:** `/Volumes/Dev_SSD/Codexify-main/.worktrees/integrate-saved-widget-consent-aware-20261027`
- **Execution date:** 2026-10-28
- **Conflicts during rebase:** none
- **Application code intervention required:** none
- **Merge commits introduced:** none

**Evidence layers — these are distinct and must not be collapsed:**

| Layer | Executed at | Scope | Result |
| --- | --- | --- | --- |
| PostgreSQL qualification | `357155689` (original qualified source) | Disposable native PostgreSQL 16.15, 5 suites | 141 passed, 0 failed, 0 skipped — **not re-executed at the rebased tip** |
| Content preservation + database-independent compatibility | `456033918` (rebased tip) | 26-path byte identity, Alembic head, 4 Saved Widget suites | 26/26 byte-identical, one head, 80 passed / 0 failed / 54 skipped |
| Frontend compatibility | `456033918` (rebased tip) | vitest main + chrome-extension configs | 2293 passed / 0 failed / 1 skipped, and 84 chrome-extension passed, against a genuine upstream baseline |
| Browser qualification | — | Playwright containment spec | **Not established** — Chromium cannot launch in this environment |

**Release interpretation: no change.** This receipt records that the qualified Saved Widget integration branch was rebased onto the verified upstream `main` tip without content loss, conflict, or application-code intervention, and that bounded compatibility checks pass at the rebased tip. It does **not** qualify the rebased tip as PostgreSQL-qualified; that qualification was executed at `357155689` and was not re-executed here.

## Upstream reassessment

`origin/main` was expected at `494a60260eede59dcce35506e70e39bfbcdb3a4f`. At rebase time it had advanced:

```text
bceac5b57 Merge pull request #942 from Resonant-Jones/test/scout-sse-bounded-reader-20261028
69a6747a7 test(scout): correct bounded task event stream fixture
```

The delta was therefore reassessed against the full upstream range `28e445c0c93a227f380bfdd26db7d875184bf6d0..bceac5b57f112a74bb7c8a4aa2dd73b05c917db1`, which is **19 commits across 14 files**:

```text
guardian/tests/routes/test_hosted_room_guest.py
tests/core/test_completion_terminal_integrity.py
tests/core/test_whooshd_context_bundle_system_identity_delivery.py
tests/evidence_packets/release_truth_contract.py
tests/evidence_packets/test_guardian_evidence_bounded_read.py
tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py
tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py
tests/evidence_packets/test_guardian_evidence_packet_generator.py
tests/evidence_packets/test_guardian_evidence_packet_generator_contract.py
tests/evidence_packets/test_guardian_evidence_reducer_input_bundle_dry_run_loader_contract.py
tests/evidence_packets/test_guardian_evidence_reducer_input_bundle_template.py
tests/identity/test_operator_route_auth_migration.py
tests/identity/test_scout_app_mount.py
tests/routes/test_agent_orchestration_request_user.py
```

Every upstream path is a test or test-support file. The upstream delta contains **no production source, no frontend source, and no migration**, and has **zero path overlap** with the branch's 26 paths. `tests/routes/test_agent_orchestration_request_user.py` is the file that the separate agent-route merge-splice guard (`cecdfa115`) edits; that guard is not part of this branch and was not integrated here.

A read-only merge preview was taken before rebasing:

```sh
git merge-tree --write-tree --name-only origin/main HEAD
# bebf7edab715ea0bc24bed10d00977bf1d5826b4   (exit 0, no conflict records)
```

## Rebase execution

Preflight confirmed the active branch, a clean worktree, and no stale `index.lock`:

```sh
git status --porcelain     # empty
git branch --show-current  # integrate/saved-widget-consent-aware-20261027
git rev-parse HEAD         # 606d748c3707e1e9ce6eafbccd5b7499bbd928e3
git fetch origin main
git rev-parse origin/main  # bceac5b57f112a74bb7c8a4aa2dd73b05c917db1
```

The upstream SHA was re-verified immediately before the rebase, and the rebase was pinned to that explicit SHA rather than a moving ref:

```sh
git rebase bceac5b57f112a74bb7c8a4aa2dd73b05c917db1
# Rebasing (1/12) ... Rebasing (12/12)
# Successfully rebased and updated refs/heads/integrate/saved-widget-consent-aware-20261027.
```

All twelve commits were replayed. **No conflict occurred**, so no semantic conflict was resolved and no application code was changed to make the rebase succeed. The rebased branch contains **zero merge commits** (`git rev-list --count --merges bceac5b57..HEAD` → `0`).

The rebased chain, oldest first:

```text
456033918 docs(proof): qualify saved widget storage on PostgreSQL 16.15
ebcd282cb test(db): prove saved widget migration ancestry without a database
f6ab32f13 fix(db): chain saved widget migration after consent
9a4fecadb feat(guardian): persist canonical saved widget revisions
dd6aec0b8 fix(guardian): reject unavailable saved widget dependencies
bc8ea7550 fix(generative-ui): preserve network containment across navigation
1652638d9 test(generative-ui): repair navigation escape reproduction
4f9ef6590 test(generative-ui): prove sandbox navigation containment
f3837e18f feat(guardian): validate saved widget artifact eligibility
ae3dd5d8d docs(architecture): accept saved widget identity and revision contract
f085c59d5 docs(architecture): resolve saved widget contract review findings
95eded165 docs(architecture): propose saved widget identity and revision contract
```

## Preserved path set

The original 26-path delta was recorded against the branch's merge-base before rebasing:

```sh
git diff --name-only "$(git merge-base origin/main HEAD)" HEAD   # 26 paths
```

After the rebase, the same command against the new base yields the identical 26 paths, and `diff` of the two path lists is empty. Beyond path identity, each of the 26 paths was compared blob-for-blob between the original tip `606d748c` and the rebased tip `456033918`:

```sh
git rev-parse "606d748c:$path"   # vs
git rev-parse "HEAD:$path"
```

**All 26 paths are byte-identical.** The preserved set:

```text
docs/architecture/00-current-state.md
docs/architecture/README.md
docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
docs/architecture/adr/adr-index.md
docs/architecture/data-and-storage.md
docs/architecture/generative-ui-contract.md
docs/architecture/generative-ui-marker-corpus.json
docs/architecture/library-projects-spaces-product-surface-contract.md
docs/architecture/proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md
docs/architecture/proofs/runtime/2026-10-28-saved-widget-postgresql-qualification.md
docs/architecture/saved-widget-contract.md
docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json
docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json
docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json
frontend/src/features/chat/components/__tests__/GenerativeUI.test.tsx
frontend/src/features/chat/components/generativeUi/SandboxFrame.tsx
frontend/src/tests/playwright/generative-ui-navigation-containment.spec.ts
guardian/core/db.py
guardian/core/saved_widget_store.py
guardian/core/saved_widget_validation.py
guardian/db/migrations/versions/a6b9d2e4f701_add_saved_widget_identity_and_revisions.py
guardian/db/models.py
tests/core/test_saved_widget_validation.py
tests/db/test_saved_widget_revision_store.py
tests/db/test_saved_widget_storage_migration.py
tests/db/test_saved_widget_validation_provenance.py
```

The three knowledge-graph node JSON files retain the recomputed DLG node hashes from the prior reconciliation; they were not regenerated during this rebase and their blobs are unchanged.

This 26-path set is the branch delta as it stood immediately after the rebase and before this receipt was added. The one authorized addition — this receipt — makes the branch's path count relative to `origin/main` **27** at the rebased tip. No other path was introduced, removed, or modified.

## Original PostgreSQL receipt identity

The original qualification receipt was verified byte-identical across the rebase and was **not** amended:

```text
path:   docs/architecture/proofs/runtime/2026-10-28-saved-widget-postgresql-qualification.md
blob:   dc2fa35541a281d27e77af123a418b0f6f6ca5e7   (identical pre- and post-rebase)
size:   5902 bytes
sha256: 46346f303a577d3f1198faa7842a4bce6cddeb6bea05b5ddb7b83312a0823737
```

The receipt still names `3571556894c3707069b3e0c348e8eb5049efb243` as its evaluated source commit and still records `141 passed, 0 failed, 0 skipped`. That claim remains attributable to that SHA and was not re-executed at the rebased tip.

The shared marker corpus referenced by that receipt remains hydrated at 11,456 bytes, matching the size stated in the original receipt.

## Alembic head

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m alembic -c backend/alembic.ini heads
# a6b9d2e4f701 (head)
```

**Exactly one head.** The asserted canonical ancestry is unchanged:

```text
f0d7c4b2a198 -> c59e4d1a28f0 -> a6b9d2e4f701
```

No second head and no merge revision was produced. The migration file `a6b9d2e4f701_add_saved_widget_identity_and_revision_boundary` remains a byte-identical path of the rebased tree.

## Focused database-independent compatibility checks

Run from the rebased worktree with all ambient database URLs explicitly unset:

```sh
env -u TEST_DATABASE_URL -u DATABASE_URL -u GUARDIAN_DATABASE_URL PYTHONPATH=. \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v -ra -o addopts='' \
  tests/db/test_saved_widget_storage_migration.py \
  tests/core/test_saved_widget_validation.py
# 79 passed, 9 skipped, 2 warnings in 11.18s
```

```sh
env -u TEST_DATABASE_URL -u DATABASE_URL -u GUARDIAN_DATABASE_URL PYTHONPATH=. \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v -ra -o addopts='' \
  tests/db/test_saved_widget_revision_store.py \
  tests/db/test_saved_widget_validation_provenance.py
# 1 passed, 45 skipped in 0.67s
```

| Suite | Collected | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| `tests/db/test_saved_widget_storage_migration.py` | 13 | 4 | 0 | 9 |
| `tests/core/test_saved_widget_validation.py` | 75 | 75 | 0 | 0 |
| `tests/db/test_saved_widget_revision_store.py` | 30 | 1 | 0 | 29 |
| `tests/db/test_saved_widget_validation_provenance.py` | 16 | 0 | 0 | 16 |
| **Total** | **134** | **80** | **0** | **54** |

The collected counts (13 + 75 + 30 + 16) match the per-suite counts recorded in the original PostgreSQL qualification receipt exactly, so the rebased tree exposes the same test surface.

**Every skip was inspected.** All 54 skips carry a single reason:

```text
TEST_DATABASE_URL required for disposable Postgres proof
```

These are the database-dependent portions of the four suites, gated behind a live disposable PostgreSQL fixture. They are recorded here as **skipped and not executed**. They are **not** counted as PostgreSQL proof, and no database-backed assertion was evaluated at the rebased tip. The two warnings reported by the first command were Alembic's `prepend_sys_path` deprecation notice, raised twice by the migration suite's own structural checks; the second command reported none. Both are pre-existing and unrelated to the rebase.

The migration suite's non-database structural assertions — including the linear-chain and single-head checks — executed and passed. These are the assertions that make the Alembic-head result above independently re-verifiable without a database.

## Frontend compatibility checks

The preserved delta contains three frontend paths, so the frontend suite was executed. The branch's frontend content is byte-identical pre- and post-rebase, and upstream changed no frontend file, so the frontend outcome is independent of the rebase itself.

### Environment preparation

The workspace frontend toolchain carried two independent dependency gaps. Neither is a property of this branch.

1. **`@openuidev/react-lang`** — declared at `frontend/src/package.json:49` as version `1.0.1`, absent from every `node_modules` tree and from the pnpm store. The importing module `frontend/src/features/chat/components/generativeUi/openuiNative.tsx` is **byte-identical between `origin/main` and the branch**, and upstream's `frontend/src/package.json:49` declares the same dependency. The gap is an upstream environment gap.
2. **Six broken package links** under `frontend/src/node_modules` pointed into pnpm store paths whose inner package directories were missing: `@eslint/js`, `@tailwindcss/postcss`, `@tailwindcss/vite`, `@vitejs/plugin-react`, `@tauri-apps/api`, and `@testing-library/react`. Every one of the six had a real copy in `frontend/node_modules`. The `@testing-library/react` link is the one that mattered: the chrome-extension vitest config loads `frontend/src/test/setup.ts`, which imports it.

Both were repaired **only in `node_modules`**, which is gitignored and untracked. No tracked file was modified by the repair.

One installation detail is load-bearing and is recorded so the result is reproducible. `@openuidev/react-lang` must be installed *inside* the project's tree. Installing it into an isolated prefix and linking that prefix in produces a second React copy, and the suite then fails with 17 spurious `Invalid hook call` errors. Placed in the project tree, its `react` import resolves to the project's single `react@19.2.0`, and the OpenUI suites pass.

### True upstream baseline

The root checkout's local `main` (`f0d2d26ea664d1e15459f5e8e2ed5522115cb45d`) is **not an ancestor of `origin/main`** — it is a divergent line that already carries the generative-ui containment work upstream lacks. It is therefore **not** a valid upstream baseline, and a reproduction there is not evidence about upstream.

A genuine upstream baseline was built by exporting `bceac5b57` with `git archive` into a separate tree, materializing the upstream marker corpus from the local Git LFS object store, and applying the same dependency repairs. Upstream's corpus is a distinct LFS object of 4,268 bytes; the branch's is 11,456 bytes.

| Suite | Upstream `bceac5b57` | Branch `456033918` |
| --- | ---: | ---: |
| Collected | 2288 | 2294 (+6) |
| Passed | 2287 | 2293 (+6) |
| Failed | 0 | 0 |
| Skipped | 1 | 1 |

The branch's `+6` are the `generative UI trusted wrapper` tests it adds to `GenerativeUI.test.tsx` — nested sandboxed frame, navigation containment, preserved CSP, wrapper sandboxing, validated action relay, and rejection of directly posted frame messages. All six pass.

### Results

```sh
cd frontend && pnpm --dir src exec vitest run --config vitest.config.ts
# Test Files  227 passed | 1 skipped (228)
# Tests       2293 passed | 1 skipped (2294)
# Duration    88.09s
```

```sh
cd frontend && pnpm test:chrome-extension
# Test Files  5 passed (5)
# Tests       84 passed (84)
```

Both stages are green. `pnpm test` chains the two stages with `&&`, so the chrome-extension stage is reached only when the vitest stage exits zero.

### One timeout-sensitive test, recorded as a review item

With the default `testTimeout` of 5000 ms, `tests/thread_documents_rehydration.spec.tsx > rehydrates linked documents on bootstrap and thread switch` fails in the branch's full suite at roughly 5,400 ms with:

```text
Error: Test timed out in 5000ms.
```

This is not an assertion failure, and it is not a rebase artifact — the branch's frontend content is byte-identical pre- and post-rebase, and the branch touches nothing related to thread documents. The test passes in isolation (2.2 s) and passes on upstream in the full suite. Re-running the branch's full suite with `--testTimeout=20000` yields **2293 passed, 1 skipped, 0 failed**.

The honest characterization is that the branch's suite schedules this test marginally past the default budget where upstream's does not. It is a pre-existing condition of the branch's own frontend state, and it is flagged here for review rather than dismissed. It was not introduced by the rebase, and no application code was changed to address it.

### Playwright containment spec: not executable in this environment

The branch adds `frontend/src/tests/playwright/generative-ui-navigation-containment.spec.ts` (707 lines). `pnpm test` excludes `tests/playwright/**`, so the spec was invoked directly:

```sh
cd frontend && pnpm --dir src exec playwright test \
  tests/playwright/generative-ui-navigation-containment.spec.ts --reporter=list
# 29 failed
```

All 29 failed at **browser launch**, not at any assertion. Chromium aborts with:

```text
FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS.
bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer: Permission denied (1100)
```

An independent minimal launch probe, independent of this spec, fails identically, confirming the cause is environmental: Chromium cannot start inside this agent sandbox. The spec is deliberately written so that this is visible — its unmarked harness-liveness test exists precisely to keep an infrastructure failure from reporting green.

This spec is therefore recorded as **not executed**, not as passed and not as failed on the merits. The real-browser containment evidence remains the pre-existing, byte-identical receipt `docs/architecture/proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md`; it was not re-established by this rebase.

## Invariants and ADR assessment

| Invariant | Assessment |
| --- | --- |
| Canonical account ownership | Preserved; `guardian/core/saved_widget_store.py` byte-identical, store suite passed |
| Immutable Saved Widget revisions | Preserved; revision-immutability trigger and store suite passed |
| Server-owned E5 provenance | Preserved; provenance suite passed, server authority untouched |
| Automatic-memory consent behavior | Preserved; consent migration `c59e4d1a28f0` unchanged, single-head ancestry intact |
| Saved Widget migration ancestry | Preserved; `f0d7c4b2a198 -> c59e4d1a28f0 -> a6b9d2e4f701`, exactly one head |
| Original PostgreSQL evidence and evaluated SHA | Preserved; receipt blob `dc2fa355`, 5902 bytes, sha256 `46346f30…`, not amended |

**ADR impact:** aligned with ADR-102 (Saved Widget identity and revision boundary), ADR-069 (Beta runtime support boundary), ADR-091 (durable completion-attempt authority), and ADR-081 (project ownership authority). No ADR was created or modified, and no ADR conflict arose during the rebase. The rebase introduced no architectural change: it relocated existing, already-reviewed commits onto a newer upstream base without altering their content.

## Evidence limits

**Proven by this receipt:** the rebase completed without conflict, without merge commits, and without application-code intervention; all 26 branch paths are byte-identical to their pre-rebase state; the original PostgreSQL receipt is byte-identical and unamended; the Alembic chain has exactly one head; 80 database-independent assertions passed with 0 failures across the four Saved Widget suites and the 75-test eligibility suite; the frontend suite is green against a genuine upstream baseline — 2293 passed, 0 failed, 1 skipped versus upstream's 2287 passed, 0 failed, 1 skipped — with the branch's 6 added wrapper tests all passing, and the chrome-extension suite green at 84 passed.

**Not proven by this receipt:** the rebased tip is **not** PostgreSQL-qualified. The 141-test PostgreSQL qualification was executed at `357155689` and was not re-executed at `456033918`; 54 database-dependent assertions were skipped for want of a live disposable PostgreSQL cluster. The Playwright navigation-containment spec was not executed because Chromium cannot launch in this environment, so no browser qualification is claimed. `tests/thread_documents_rehydration.spec.tsx` fails at the default 5000 ms test timeout in the branch's full suite and passes only when the budget is raised; it is a pre-existing branch condition, not a rebase artifact, and it remains a review item. No user-facing Saved Widget lifecycle behavior, no Beta release promotion, and no Docker Compose supported-path qualification is claimed or implied.

**Release posture: HOLD.** This receipt records integration readiness evidence only.

**Files changed:** this proof receipt only. No application source, migration, test, configuration, or prior receipt file was edited during the rebase or the checks. The dependency repairs described above were made only inside `node_modules`, which is gitignored and untracked; `git status` was clean before and after every command that touched it.

---

# Appendix — Current-upstream reconciliation (added 2026-10-28)

**This appendix does not change any result recorded above.** Every SHA, test count, blob identity, and historical claim in the body of this receipt stands exactly as written and continues to describe the rebase onto `bceac5b57f112a74bb7c8a4aa2dd73b05c917db1` and the branch tip `4560339184b685f00f42ea31bd5fbbe07068fbe8`. This section records what happened to upstream *after* those measurements were taken, and it draws the resulting evidence boundary.

## Upstream advanced again and absorbed this work independently

`origin/main` moved from `bceac5b57f112a74bb7c8a4aa2dd73b05c917db1` to `4791f219d1b872a7d55384767f5c8ba2df5f3060` (`merge(db): reconcile local main with origin/main for publication`) while this work was in progress.

Upstream has, independently, absorbed the Saved Widget storage foundation. The implementation files carried by this branch are **byte-identical** to their counterparts at `4791f219d`:

```text
guardian/core/saved_widget_store.py
guardian/core/saved_widget_validation.py
guardian/core/db.py
tests/core/test_saved_widget_validation.py
frontend/src/features/chat/components/generativeUi/SandboxFrame.tsx
frontend/src/features/chat/components/__tests__/GenerativeUI.test.tsx
```

Upstream additionally carries its own Saved Widget proofs, including `docs/architecture/proofs/runtime/2026-10-27-saved-widget-integrated-merge-candidate-proof.md`, `docs/architecture/proofs/runtime/2026-10-27-saved-widget-memory-consent-merge-head-proof.md`, and `docs/architecture/proofs/runtime/2026-10-28-saved-widget-alembic-main-promotion-proof.md`.

## The migration topology differs, and the qualification does not transfer

This is the load-bearing distinction. The chain qualified by the original PostgreSQL receipt was **linear**:

```text
f0d7c4b2a198 -> c59e4d1a28f0 -> a6b9d2e4f701
```

where the qualified `a6b9d2e4f701` declared `down_revision = "c59e4d1a28f0"`.

Upstream at `4791f219d` resolves the same saved-widget / automatic-memory-consent head collision **through a merge revision instead of a linearization**:

```text
a6b9d2e4f701   down_revision = "f0d7c4b2a198"          (blob adcd6e4529324118206cd691a52db0b9e343f1b3)
7f2c9e1a4b63   down_revision = ('a6b9d2e4f701', 'c59e4d1a28f0')
3a91d7c4e8b2   down_revision = ('7f2c9e1a4b63', 'b3c8d1e5f7a2')   -- current single head
```

The `a6b9d2e4f701` file on upstream is a **different revision from the one that was qualified**: blob `adcd6e4529324118206cd691a52db0b9e343f1b3` upstream, against blob `4ba8fb09226c1e7633d0cf8b197bd66e6f89b425` on this branch, with a different `down_revision`. The current upstream tree resolves to exactly one head, `3a91d7c4e8b2`.

**Therefore the 141-test PostgreSQL qualification at `357155689` does not establish PostgreSQL qualification of the current upstream merge-head topology.** The original receipt's claim remains true and remains scoped to the SHA it names. It is not evidence about `4791f219d`.

## The integration branch is superseded for publication

`integrate/saved-widget-consent-aware-20261027` is retained unchanged as the historical record of the rebase, at `4c7a1f693be93fa9c07eb8f329e009598d2a5269`. Its rebase compatibility evidence applies to `bceac5b57`, **not** to the current upstream tip. The branch is superseded for publication purposes: rebasing it onto `4791f219d` produces seven conflicts, including an `add/add` conflict on `a6b9d2e4f701_add_saved_widget_identity_and_revisions.py` and on `tests/db/test_saved_widget_storage_migration.py`, because both sides added the same paths with different content. Resolving that conflict would require choosing a migration lineage, which is an application-level decision, not a documentation one. It was therefore not performed.

The original qualification anchor `proof/saved-widget-postgres-357155-20261028` remains untouched at `606d748c3707e1e9ce6eafbccd5b7499bbd928e3`.

## Evidence boundary of this publication

This receipt is published as **historical evidence**, carried onto current `main` unchanged in substance. It is not a compatibility statement about `4791f219d`, and it is not a re-qualification of the current upstream migration topology.

The following remain **open proof gates**, stated separately rather than folded into the historical result:

- **PostgreSQL qualification of the current upstream merge-head topology** (`7f2c9e1a4b63` -> `3a91d7c4e8b2`). Not established. The 141/141 run was against the linear chain at `357155689`.
- **Browser qualification.** The Playwright navigation-containment spec was not executed, because Chromium cannot launch in the environment used. The pre-existing receipt `docs/architecture/proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md` remains the browser evidence for the containment boundary.
- **User-facing Saved Widget lifecycle.** Not implemented, and not claimed.

**Release posture: HOLD**, unchanged.
