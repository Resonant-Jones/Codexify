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
feature-branch live PASS proof. The worktree is currently **clean**. However,
the branch is **not** a clean Remote Recall merge candidate as-is:

- **Branch contamination**: 20 commits on the branch are not on `main`, but
  only ~7 are Remote Recall owned. The rest are unrelated work (Persona Studio
  UI, federation jwt fix, Scout navigation, docker whooshd, appearance
  settings). Merging the branch wholesale would carry unreviewed, out-of-scope
  work into `main`, violating the "do not mix unrelated edits" protocol rule.
- **Whole-branch merge now conflicts**: `git merge-tree --write-tree main
  feature/remote-retrieval` exits non-zero with 8 content conflicts — **all in
  Persona Studio frontend files** (`PersonaPreviewPanel.tsx`,
  `PersonaStudioPage.tsx`, and 6 Persona Studio tests). **None of the conflicts
  are in Remote Recall owned files.** This means the conflicts belong to the
  unrelated contamination, not to Remote Recall.
- **Remote Recall itself is conflict-free**: the Remote Recall owned file set
  (`guardian/web/`, `guardian/core/chat_completion_service.py`,
  `guardian/core/config.py`, `guardian/context/retrieval_router_policy.py`,
  `guardian/protocol_tokens.py`, `tests/web/`, `tests/contracts/`, and the RR
  docs) does not overlap the conflict surface. Isolating only the Remote Recall
  commits onto a clean branch off `main` would avoid all current conflicts.
- **Remote divergence**: the local branch is ahead 7 / behind 15 of
  `origin/feature/remote-retrieval`; it must be reconciled with its remote
  before any merge.
- **No mainline proof**: Remote Recall is not proven on `main`; a post-merge
  rerun proof is required regardless.

Recommended resolution (separate task, not this one): isolate the Remote Recall
commits onto a clean branch off current `main` (the RR owned files are
conflict-free, so this is expected to apply cleanly), reconcile the remote
divergence, then run the required post-merge mainline proof. Do not merge the
whole feature branch wholesale — it carries unrelated Persona Studio work that
now conflicts with `main`.

## 4. Branch and commit context

- Current branch: `feature/remote-retrieval` (confirmed via
  `git rev-parse --abbrev-ref HEAD`, not assumed from docs).
- HEAD: `6af223efe05c6a3cdcc54f8d0368e8eb858d0eaa`.
- Remote tracking: `## feature/remote-retrieval...origin/feature/remote-retrieval
  [ahead 7, behind 15]`.
- Divergence vs `main`: `main..feature` = 20 commits (on feature, not main);
  `feature..main` = 20 commits (on main, not feature).
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
| `6af223efe` | Document Remote Recall mainline merge readiness | No |

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

`git status --short --branch --untracked-files=all` shows the worktree is
**clean** at this classification: no modified, staged, or untracked files.

(Prior classification note: an earlier pass recorded 5 unrelated dirty files —
`frontend/.../AppShell.tsx`, `frontend/.../ttsConsole/*` (×3), and
`pnpm-workspace.yaml`. Those have since been resolved outside this task and are
no longer present. They were never Remote-Recall-owned and were never staged.)

- **Remote Recall owned**: none dirty.
- **Documentation/proof owned**: none dirty (all RR docs are committed).
- **Secret/env-sensitive**: none dirty; no `.env`, `.env.local`, or
  `.env.template` modified or untracked.
- **Unknown**: none.

Worktree cleanliness removes one earlier blocker, but the `hold` stands on
branch contamination, whole-branch merge conflicts, remote divergence, and the
missing mainline proof.

## 8. Required pre-merge checks

Before any Remote Recall promotion to `main`:

1. **Decontaminate the branch**: isolate the Remote Recall commits (or the
   Remote Recall owned file set) from the ~13 unrelated commits, onto a clean
   branch off current `main`. The RR owned files are conflict-free against
   `main` today, so isolation is expected to apply cleanly.
2. **Do not merge the whole feature branch wholesale**: it carries unrelated
   Persona Studio work that now conflicts with `main` (8 content conflicts in
   Persona Studio frontend files; none in RR owned files).
3. **Reconcile remote divergence**: the local branch is ahead 7 / behind 15 of
   `origin/feature/remote-retrieval`; reconcile before merge.
4. **Confirm no secret/env files** are staged (`.env*`, credentials).
5. **Re-run unit/contract validation** on the clean branch:
   `tests/web/*`, `tests/contracts/test_protocol_tokens.py`.
6. **Re-confirm merge feasibility** against current `main` with a non-mutating
   `git merge-tree` (main advances over time; the whole-branch merge is
   currently conflicting in Persona Studio files).
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

- **Blocker (process)**: branch contamination — ~13 unrelated commits mixed
  with the ~7 Remote Recall commits. Must be isolated before merge.
- **Blocker (process)**: whole-branch merge now conflicts — 8 content conflicts
  in Persona Studio frontend files; none in Remote Recall owned files. A
  wholesale merge is not viable without resolving the unrelated conflicts.
- **Blocker (process)**: local branch diverged from its remote (ahead 7 /
  behind 15).
- **Risk**: main advances during preparation; re-confirm merge feasibility with
  a non-mutating `git merge-tree` before merge.
- **Risk**: proof-run posture relaxes egress; must be proof-run-only and
  restored. The committed default-off posture must remain.
- **Mitigating signal**: Remote Recall owned files are conflict-free against
  `main`; isolating the RR commits is expected to apply cleanly.

## 12. Recommended next task

Create a clean Remote Recall promotion branch off current `main` that contains
**only** the Remote Recall owned file set (isolate the RR commits or re-apply
the files; these are conflict-free against `main` today), with the remote
divergence resolved separately. Do not merge in that task either — produce the
clean branch, re-run unit/contract validation, then open the post-merge
mainline proof as the final gate. This readiness packet is the input to that
task.

## 13. Raw command appendix

```
# Branch / worktree (non-mutating)
git status --short --branch --untracked-files=all   # clean (ahead 7 / behind 15)
git rev-parse --abbrev-ref HEAD          # feature/remote-retrieval
git rev-parse HEAD                       # 6af223efe05...
git log --oneline --decorate -n 30
git diff --name-only                     # (empty) worktree is clean
git diff --cached --name-only            # (empty)
git ls-files --others --exclude-standard # (empty)

# Lineage (non-mutating)
for c in 7f3f5158e ba1dec8b4 0735f7ad9 81ba5d50c 867722fee 6d3e1053c 6af223efe; do
  git merge-base --is-ancestor $c HEAD && echo "$c on branch"
done
# -> all RR commits present on branch; none on main

# Divergence vs main (non-mutating)
git rev-list --count main..HEAD          # 20 (~7 RR + ~13 unrelated)
git rev-list --count HEAD..main          # 20
git merge-base main HEAD                 # c4527119f...

# Merge feasibility (non-mutating; does not touch HEAD/index/worktree)
git merge-tree --write-tree --name-only main feature/remote-retrieval
# -> exit non-zero; 8 CONFLICT (content) lines, all in Persona Studio frontend:
#    PersonaPreviewPanel.tsx, PersonaStudioPage.tsx, and 6 Persona Studio tests.
#    No Remote Recall owned file appears in the conflict set.
```
