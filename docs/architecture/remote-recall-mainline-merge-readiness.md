# Remote Recall Mainline Merge Readiness

## 1. Title

Remote Recall Search-as-RAG — `feature/remote-retrieval` → `main` Merge
Readiness Classification (docs-only; no merge performed).

## 2. Scope

Classify whether the `feature/remote-retrieval` branch is ready to be merged
toward `main` for the Remote Recall Search-as-RAG seam, **without performing
the merge**. This packet records branch/worktree state, commit lineage, the
feature-branch proof boundary, dirty-file classification, and the post-merge
proof requirement. It does not merge, cherry-pick, rebase, or modify runtime
code.

Governing docs: ADR-021, Web Agent Spec v1, Search-as-RAG Provider Adapter
Contract, Web Evidence Intake Gate Contract, Retrieval Router Decision Table,
Runtime Protocol Token Contract, Chat Runtime Contract, Config and Ops, Agent
Protocol Operations Index.

## 3. Readiness status

**`hold`**

The Remote Recall seam itself is implemented, unit-tested, and has a
feature-branch live PASS proof, and a textual merge of the branch into `main`
is **clean (no file-level conflicts)**. However, the branch is **not** a clean
Remote Recall merge candidate as-is:

- **Branch contamination**: 19 commits on the branch are not on `main`, but
  only 6 are Remote Recall owned. The other 13 are unrelated work (Persona
  Studio UI, federation jwt fix, Scout navigation, docker whooshd, appearance
  settings). Merging the branch wholesale would carry unreviewed, out-of-scope
  work into `main`, violating the "do not mix unrelated edits" protocol rule.
- **Worktree contamination**: 5 unrelated dirty files (frontend TTS console,
  AppShell, `pnpm-workspace.yaml`) are present and must not be staged or
  merged.
- **Remote divergence**: the local branch is ahead 6 / behind 15 of
  `origin/feature/remote-retrieval`; it must be reconciled with its remote
  before any merge.
- **No mainline proof**: Remote Recall is not proven on `main`; a post-merge
  rerun proof is required regardless.

Recommended resolution (separate task, not this one): isolate the 6 Remote
Recall commits onto a clean branch off current `main` (or re-apply only the
Remote Recall owned file set), resolve the worktree and remote divergence
separately, then run the required post-merge mainline proof.

## 4. Branch and commit context

- Current branch: `feature/remote-retrieval` (confirmed via
  `git rev-parse --abbrev-ref HEAD`, not assumed from docs).
- HEAD: `6d3e1053cc27a156b740050aeafbb586c722d744`.
- Remote tracking: `## feature/remote-retrieval...origin/feature/remote-retrieval
  [ahead 6, behind 15]`.
- Local `main` HEAD: `6561de759f3568c1f734e4b577bf4d49c20a64cb`.
- Merge-base(`main`, HEAD): `c4527119ffd5d223a11ee036f3e8cbffbe74277d`.

Remote Recall commit lineage on this branch (all confirmed present via
`git merge-base --is-ancestor`):

| Commit | Subject | On `main`? |
|---|---|---|
| `7f3f5158e` | Add gated Remote Recall search-as-RAG seam | No |
| `ba1dec8b4` | Document Remote Recall live proof status (BLOCKED) | No |
| `0735f7ad9` | Keep Remote Recall evidence out of system authority | No |
| `81ba5d50c` | Record Remote Recall live proof PASS result | No |
| `867722fee` | Record Remote Recall live proof result (rerun verification) | No |
| `6d3e1053c` | Clarify Remote Recall proof branch scope | No |

No Remote Recall commit is on `main`.

## 5. Feature-branch proof evidence

From `remote-recall-live-proof.md` (feature-branch scoped PASS):

- One explicit `global_search` completion executed on the supported local
  Docker Compose path with a real Groq credential and intentionally relaxed
  posture.
- Provider result status `ok`; 5 candidate evidence items; 5 eligible; 0
  blocked; all 5 passed prompt-injection screening.
- Assistant message persisted; `trace["remote_recall"]` present with
  `trace_event: remote_recall.completed`, gate decisions, content hashes, and
  provenance URLs.
- Internal consistency re-verified: all 5 recorded `content_hash → evidence_id`
  pairs reproduce exactly via the gate's deterministic
  `uuid.uuid5(NAMESPACE_URL, content_hash)` computation.

This evidence is valid for `feature/remote-retrieval` only. It is not `main`
proof.

## 6. Mainline boundary

- Remote Recall is **not on `main`**.
- Remote Recall is **not part of `v1-local-core-web-mcp`**.
- Remote Recall is **not beta-supported**.
- Local-only default posture on `main` is unchanged: `CODEXIFY_LOCAL_ONLY_MODE=true`,
  `ALLOW_CLOUD_PROVIDERS=false`, Remote Recall flags default-off.
- A mainline proof requires the seam to be merged to `main` and rerun there
  under the same intentionally relaxed proof-run posture.

## 7. Dirty worktree classification

`git status --short --branch --untracked-files=all` shows 5 modified files,
nothing staged, nothing untracked:

| File | Classification | RR-owned? | Secret? |
|---|---|---|---|
| `frontend/src/components/persona/layout/AppShell.tsx` | unrelated frontend / other-agent | No | No |
| `frontend/src/features/ttsConsole/TtsConsole.css` | unrelated frontend / other-agent | No | No |
| `frontend/src/features/ttsConsole/TtsConsoleWindow.test.tsx` | unrelated frontend / other-agent | No | No |
| `frontend/src/features/ttsConsole/TtsConsoleWindow.tsx` | unrelated frontend / other-agent | No | No |
| `pnpm-workspace.yaml` | unrelated workspace / other-agent | No | No |

- **Remote Recall owned**: none dirty.
- **Documentation/proof owned**: none dirty (all RR docs are committed).
- **Secret/env-sensitive**: none dirty; no `.env`, `.env.local`, or
  `.env.template` modified or untracked.
- **Unknown**: none.

These 5 files are preserved untouched. They are not staged and must not enter
any Remote Recall merge commit.

## 8. Required pre-merge checks

Before any Remote Recall promotion to `main`:

1. **Decontaminate the branch**: isolate the 6 Remote Recall commits (or the
   Remote Recall owned file set) from the 13 unrelated commits, onto a clean
   branch off current `main`.
2. **Resolve worktree contamination**: commit, stash, or discard the 5
   unrelated frontend/pnpm dirty files outside the Remote Recall change.
3. **Reconcile remote divergence**: the local branch is ahead 6 / behind 15 of
   `origin/feature/remote-retrieval`; reconcile before merge.
4. **Confirm no secret/env files** are staged (`.env*`, credentials).
5. **Re-run unit/contract validation** on the clean branch:
   `tests/web/*`, `tests/contracts/test_protocol_tokens.py`.
6. **Confirm textual merge is still clean** against current `main` (this check
   showed `git merge-tree --write-tree main HEAD` exits 0 / no conflicts, but
   main advances over time).
7. **Preserve defaults**: `REMOTE_RECALL_ENABLED=false`,
   `GROQ_WEB_SEARCH_ENABLED=false`, `CODEXIFY_LOCAL_ONLY_MODE=true`,
   `ALLOW_CLOUD_PROVIDERS=false`.

## 9. Required post-merge proof

After the seam is on `main`:

1. Rebuild `backend` and `worker-chat` from `main`.
2. Apply proof-run-only posture (real `GROQ_API_KEY`, Remote Recall flags on,
   cloud egress on, local-only off, proof profile) — never committed.
3. Submit one explicit `global_search` completion; capture task lifecycle to a
   terminal event.
4. Confirm persisted assistant message and `trace["remote_recall"]` (provider,
   source kinds, candidate/eligible/blocked counts, gate decisions).
5. Restore local-only defaults; record the mainline PASS in
  `remote-recall-live-proof.md`.
6. Only then may `00-current-state.md` state a mainline PASS.

## 10. Release-claim boundary

- This packet does not widen any release claim.
- Remote Recall remains default-off and not beta-supported.
- Feature-branch PASS is not a `main` claim.
- No new provider, broker, Composer picker, URL fetch, or browser automation is
  implied.

## 11. Risks and blockers

- **Blocker (process)**: branch contamination — 13 unrelated commits mixed with
  the 6 Remote Recall commits. Must be isolated before merge.
- **Blocker (process)**: worktree contamination — 5 unrelated dirty files.
- **Blocker (process)**: local branch diverged from its remote (ahead 6 /
  behind 15).
- **Risk**: main advances during preparation; re-confirm a clean merge-tree
  before merge.
- **Risk**: proof-run posture relaxes egress; must be proof-run-only and
  restored. The committed default-off posture must remain.
- **Not a blocker**: textual merge is clean today (no conflicts).

## 12. Recommended next task

Create a clean Remote Recall promotion branch off current `main` that contains
**only** the Remote Recall owned file set (isolate the 6 commits or re-apply
the files), with the worktree contamination and remote divergence resolved
separately. Do not merge in that task either — produce the clean branch, re-run
unit/contract validation, then open the post-merge mainline proof as the final
gate. This readiness packet is the input to that task.

## 13. Raw command appendix

```
# Branch / worktree (non-mutating)
git status --short --branch --untracked-files=all
git rev-parse --abbrev-ref HEAD          # feature/remote-retrieval
git rev-parse HEAD                       # 6d3e1053cc...
git log --oneline --decorate -n 30
git diff --name-only                     # 5 unrelated frontend/pnpm files
git diff --cached --name-only            # (empty)
git ls-files --others --exclude-standard # (empty)

# Lineage (non-mutating)
for c in 7f3f5158e ba1dec8b4 0735f7ad9 81ba5d50c 867722fee 6d3e1053c; do
  git merge-base --is-ancestor $c HEAD && echo "$c on branch"
done
# -> all six present on branch; none on main

# Divergence vs main (non-mutating)
git rev-list --count main..HEAD          # 19 (6 RR + 13 unrelated)
git rev-list --count HEAD..main          # 16
git merge-base main HEAD                 # c4527119f...

# Merge feasibility (non-mutating; does not touch HEAD/index/worktree)
git merge-tree --write-tree --name-only main HEAD   # exit 0 -> no conflicts
```
