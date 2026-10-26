# Dependency-Authority Integration — Mobile Campaign Path

**Campaign:** `CAMPAIGN-MOB-2026-10-23` (Mobile Experience Calibration)
**Task:** `IR-004` — land PR #896 (retire `frontend/` as an independent dependency
install root) before the canonical frontend qualification.
**Tracking issue:** https://github.com/Resonant-Jones/Codexify/issues/888
**Integrated PR:** https://github.com/Resonant-Jones/Codexify/pull/896
**Merge commit:** `6e0fb06d220f7ba01e01a6b5607432ceaebcf8fe` (2026-10-26)
**Date:** 2026-10-26
**Evidence posture:** repository inspection, local automated test execution, and
CI job evidence at exact revisions. This is a read-only integration record; no
application behaviour was changed.

---

## 1. What this task did

The mobile campaign's integration-readiness audit recommended finishing the
`#896` dependency-authority integration **before** running the canonical Node
20 / pnpm 9 qualification, because `#896` changes the installation topology,
the manifests, the lockfile authority, and the self-heal recovery behavior. A
qualification run immediately before that merge would describe a dependency
arrangement that is being retired.

This task landed `#896` and repaired the inherited test failures that its CI
plumbing exposed.

## 2. Attribution: every failure was inherited, none was introduced

`#896` is the first change whose diff reaches backend- and frontend-relevant
paths, so it is the first to **actually run** those suites. `main` had not
exercised them: every recent mainline commit was documentation-only, so the
`Backend Tests` job resolved to a no-op and `Architecture Contracts` failed
before the branch point.

Every failure below was reproduced against `main`'s own source:

| Failure | Proof it is inherited |
|---|---|
| `test_stale_terminal_lock_is_recovered` → `AttributeError: ... has no attribute 'turn_lock_is_stale'` | The failing test function is byte-identical on `main` and on the branch (same MD5). `guardian/core/chat_completion_service.py` contains zero occurrences of `turn_lock_is_stale` on both. Re-running the test with `main`'s source in place reproduced the identical `AttributeError`. |
| `test_pgdb_persists_provenance_in_initial_insert_and_one_transaction` → `assert ('Jane Guest', '{}') == ('part-guest', 'Jane Guest')` | `#896` touches neither `guardian/core/pgdb.py` nor this test. The assertion read provenance from the *trailing* parameter positions; `extra_meta` was appended to the same INSERT on 2026-10-15 (`ec1681798`). |
| `GuardianMobileSidebarAppMenu > does not refetch workspace data when the local menu toggles` | Present at the identical identity in the campaign's own recorded runs, in PR #891's CI at `9d28ef00d`, and in the integration audit's baseline-source run with the campaign removed. |

## 3. Repairs landed

Four commits, all test-only. No application source, manifest, or lockfile was
modified.

| Commit | Change | Local evidence |
|---|---|---|
| `78405ab34` | `tests/core/test_chat_completion_enqueue_service.py`: removed the superseded `test_stale_terminal_lock_is_recovered` case | The case asserted the pre-2026-10-04 recovery contract — a lease-margin-stale turn lock plus a terminal task event proving recoverability, cleared with `clear_turn_lock`, emitting `chat.orphaned_turn_recovered`. That contract was **deliberately retired** by `2ab3f8d18`; its proof states that the non-atomic clear and the unbounded recovery audit write were removed, that recovery is now driven by the durable attempt outcome and its receipts, and that no orphan event is emitted for a task merely because its lock was cleaned. The current contract is covered by `tests/core/test_turn_lock_recovery.py`. | `test_chat_completion_enqueue_service.py` + `test_turn_lock_recovery.py` — 53 passed |
| `d9b3e5f72` | `tests/core/test_chat_message_provenance_persistence.py`: assert provenance by **named column** instead of trailing position | The provenance columns are still written in the initial insert, in one transaction; `extra_meta` simply moved the trailing positions. The assertions now map the parameter tuple onto the statement's named columns — the same invariant, robust to a future column. | 26 passed |
| `b8df26b7d` | `GuardianMobileSidebarAppMenu.test.tsx`: complete the `@/lib/authState` mock with `getAuthState` | `components/sidebar/useProjectsCache.ts` reads `getAuthState()` before it consults `checkAuthGate`; the mock omitted it, so the gate argument raised and the workspace fetch never happened. | 9 passed |
| `ad510b8b7` | Five more shell suites: same mock completion | `GuardianMobileComposerSingleSurface`, `GuardianMobileHeaderTools`, `GuardianMobileFrameShell`, `GuardianChatWithSidebar.terminal-projection`, `AppShell.runtimeHealth` — all mock the auth module identically and all render the sidebar shell. | 35 passed across the six suites |

## 4. CI state at merge

| Job | Conclusion | Note |
|---|---|---|
| Architecture Contracts | **pass** | The branch realigned the DLG node hashes (`4b3f9dc80`), which also clears the red that was inherited on `main`. |
| Frontend Quality | **pass** | Lint ✓, Build ✓, Test ✓. |
| Backend Tests (Python 3.11) | **fail** | Inherited mainline debt — see §5. |

## 5. The remaining backend failure — exact inventory

The backend suite runs with `--maxfail=1`, so it reports one failure per run.
The chain behind it is now fully enumerated:

**Root cause.** `cd7be2a57` (2026-10-04, *"Require durable terminal capability
for chat worker cleanup"*) removed the owner-string release from the worker's
accepted lifecycle's `finally` block. Its proof
(`docs/architecture/proofs/supported-compose/2026-10-04-chat-worker-terminal-cleanup.md`)
records: *"removes the owner-string release… After PostgreSQL acknowledgement, a
separate bounded Redis operation invokes the existing single-Lua task/token/
thread CAS… No legacy release or separate GET/DELETE fallback."* The same
commit updated **fifteen** sibling worker test files to the new pattern and
missed two.

**Remaining stale sites — seven patches across two files:**

| File | Lines | Stale target |
|---|---|---|
| `tests/test_chat_worker_turn_integrity.py` | 54, 115, 149, 205, 256, 282 | `chat_worker.release_turn_lock` |
| `tests/core/test_completion_terminal_integrity.py` | 313 | `chat_worker.release_turn_lock` |

**The three seams the new contract reads** (a faithful migration needs all of
them):

1. `chat_worker._read_attempt_for_worker` — the worker now reads its durable
   attempt before any accepted work, and returns early if there is none
   (`guardian/workers/chat_worker.py:2737-2740`).
2. `chat_worker.observe_chat_completion_attempt_terminal` — the durable
   terminal authority (`chat_worker.py:585`).
3. `chat_worker.record_chat_completion_attempt_terminal_event` — the durable
   terminal outcome record (`chat_worker.py:530-534`).

**Why this was not completed here.** The two tests whose subject *is* the
terminal publication (`..._completes_idempotently_and_releases_lock` and
`..._marks_task_failed_and_releases_lock`) now receive their terminal event
from the durable authority rather than from the worker's in-memory path, so
each needs its own durable-authority expectation rather than a mechanical
rename. That is a contract decision — the 2026-10-04 proof lists *"UI/operator
projection and explicit new-request retry, unconfirmed-admission ambiguity"* as
the next required obligations in this area — so it is left to the contract
owner rather than guessed at here. A partial migration that fails for the
wrong reason would be worse than a clearly stale test.

**Consequence to carry forward.** `main`'s backend job will now fail on every
pull request that touches backend-relevant paths, until these two files are
migrated. The failure is inherited, deterministic, and named above.

## 6. Verification method (reusable)

The `--maxfail=1` chain was unwound in one pass rather than one CI cycle per
failure, using two static sweeps that resolve a patch target and check it
still exists on the module:

- **Backend:** an AST sweep over `tests/**` for `monkeypatch.setattr(module,
  "attr", …)` and `patch.object(module, "attr", …)`, resolving each imported
  alias and asserting `hasattr(module, attr)`. This is what found the
  `release_turn_lock` family and confirmed the `media.chatlog_db` and
  `candidate_ingest_worker.store_candidate_trace` hits are false positives —
  those two already pass `raising=False`.
- **Frontend:** a sweep for `vi.mock("@/lib/authState", …)` blocks that omit
  `getAuthState`. Eleven suites had an incomplete auth mock; the six that
  render the sidebar shell (and therefore read `getAuthState`) were repaired.

## 7. Method and environment notes

- The backend suite was executed locally against a real install of the
  branch's dependency set (`backend/requirements-ci.txt` plus
  `pip install -e ".[mcp-memory]"`, matching the branch's own CI change).
  CI remained the authority for the final verdict, because CI has the
  PostgreSQL container that a local run does not.
- `pytest` runs need `-o addopts=""` here: the repository's `pytest.ini` sets
  `addopts = -q --disable-warnings`, which overrides a command-line `-v`.
- The frontend suite was executed locally against the mainline install; three
  suites could not be *collected* locally because that install predates
  `react-markdown`, which the branch's lockfile contains. CI installs from the
  branch lockfile and collects them, which is where the green verdict came
  from.

## 8. Next atomic Task

**`IR-005` — canonical Node 20 / pnpm 9 frontend qualification on the merged
mainline revision `6e0fb06d220f`.**

The mainline now carries the retired dependency authority, so the
qualification must run against the resulting revision with the repository's own
workflow — Node 20, `pnpm install --frozen-lockfile`, `pnpm run lint`,
`pnpm run build`, `pnpm run test` — with the actual step list recorded, not a
job conclusion alone.

**Precondition to decide first:** whether the `chat_worker` migration in §5
lands before that qualification, because a red `Backend Tests` job on the
qualification revision would otherwise make the qualification's own verdict
ambiguous.

**Then `IR-006` — physical-device acceptance.** The behaviours that remain
unproven are all device behaviours: keyboard docking, multiline composition,
provider switching, backgrounding and resuming an active response, and
behaviour during a genuinely slow local-model startup.

## 9. Invariants checked

| Invariant | Status |
|---|---|
| Guardian remains the runtime authority | **Preserved** — no runtime source changed. |
| Provider and runtime identities remain distinct | **Preserved** — untouched. |
| Canonical request and attempt identity is preserved | **Preserved** — no identity code changed; the migration in §5 is deferred precisely so it is not changed blind. |
| Transcript persistence remains authoritative | **Preserved** — the provenance repair re-asserts the existing single-insert, one-transaction invariant by named column. |
| No source code modified by this task | **Preserved** — four test-only commits. |
| The local `main` branch and concurrent operator work remain untouched | **Preserved** — local `main` was never merged into, rebased, or reset. |
| Release qualification remains separately gated | **Preserved** — the release gate is unchanged; this task makes no release claim. |
