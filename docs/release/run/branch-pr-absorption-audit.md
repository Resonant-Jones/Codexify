# Branch and PR Absorption Audit

**Date:** 2026-03-12
**Base Branch:** `main` (commit `c76b1333d`)
**Audit Focus:** Post-Beta Stabilization merge branch classification

---

## Summary

This audit classifies local and remote branches based on whether their substantive commits have been absorbed into `main` via the Beta Stabilization merge.

**Classification Summary:**

| Category | Count | Disposition |
|----------|-------|-------------|
| Safe to close/delete | 100+ | Branches fully merged into main |
| Keep alive (unique work) | 3+ | Branches with commits not in main |
| Unclear/needs review | 2 | Worktree branches with ambiguous state |

---

## Command Evidence Used

Primary classification commands:

```bash
# Find branches fully merged into main
git branch --merged main

# Find branches NOT merged into main
git branch --no-merged main

# Check if specific commit is in main
git branch -a --contains <commit>

# Check commits unique to a branch
git log --oneline main..<branch>

# Check if branch is contained by main
git branch -a --contains origin/<branch> | grep main
```

---

## Category 1: Safe to Close/Delete (Absorbed into Main)

These branches are fully merged into `main` via the Beta Stabilization merge cycle.

### Beta Stabilization Integration Branches

| Branch | Evidence | Status |
|--------|----------|--------|
| `codex/apply-campaign-task-execution-rules` | Merged via PR #81, commit `c76b1333d` | **Fully absorbed** |
| `codex/stabilize-codexify-for-beta-testers` | Contained in main (via merge) | **Fully absorbed** |

**Command Evidence:**
```bash
$ git branch -a --contains 564b4a886
* codex/apply-campaign-task-execution-rules
+ main
  remotes/origin/main
```

### Feature Branches Absorbed

| Branch | Evidence | Notes |
|--------|----------|-------|
| `codex/add-tts-diagnostics-trail` | Contained in main | TTS diagnostics work merged |
| `codex/add-personalized-signal-digest-agent` | Contained in main | Signal digest work merged |
| `codex/bootstrap-cli-tauri` | Contained in main | Tauri bootstrap work merged |
| `codex/update-docs-architecture-kb` | Contained in main | Architecture KB updates merged |
| `codex/add-audit-readiness-cli` | Contained in main | Platform readiness CLI merged |
| `codex/add-tts-diagnostics-trail` | Contained in main | Diagnostics trail merged |
| `codex/control_plane_polish` | Contained in main | Control plane polish merged |
| `codex/add-import-progress-ui-feedback` | Contained in main | Import progress UI merged |
| `codex/fix-minimax-catalog-visibility` | Contained in main | Minimax fixes merged |
| `codex/local-first-voice-mvp-v3` | Contained in main | Voice MVP work merged |
| `codex/memoryos-embedder-provider-agnostic` | Contained in main | Embedder work merged |
| `codex/phase2-toolspec-policy` | Contained in main | Toolspec policy merged |
| `codex/frontend_fixes` | Contained in main | Frontend fixes merged |
| `codex/image_gallery_refactor` | Contained in main | Gallery refactor merged |
| `codex/redesign-chatui-session-rail` | Contained in main | Session rail redesign merged |
| `codex/reformat_chat_header_nav` | Contained in main | Header nav reformat merged |
| `codex/session_rail_edits` | Contained in main | Session rail edits merged |
| `codex/unifying_plugin_sdk` | Contained in main | Plugin SDK unification merged |
| `codex/update-composer-add-menu-behavior` | Contained in main | Composer updates merged |

### Historical Campaign/Backup Branches

These branches represent older work that has been superseded or absorbed:

- `2026-02-03_codex_runner_audit` - Old audit branches (merged)
- `CAMPAIGN_2026_02_16_SECURITY_HARDENING` - Security campaign (merged)
- `campaign/*` - Various campaign branches (merged/absorbed)
- `chore/*` - Cleanup branches (merged)
- `claude/*` - Claude-assisted work (merged)
- `recovery/*` - Recovery snapshots (no longer needed)
- `safety/*` - Safety backups (no longer needed)
- `pr-72`, `pr-73` - PR branches (merged)

**Safe to Delete Locally:** All branches listed in `git branch --merged main` output (100+ branches).

---

## Category 2: Keep Alive (Contains Unique Work Not in Main)

These branches have commits that are NOT present in `main` and represent ongoing or pending work.

### Active Development Branches

| Branch | Unique Commits | Evidence | Recommendation |
|--------|----------------|----------|----------------|
| `codex/add-operator-console-route` | 3 commits | `git log main..codex/add-operator-console-route` shows unique work | **Keep alive** |
| `origin/codex/voice-turn-interaction-pipeline` | 2+ commits | `git log main..origin/codex/voice-turn-interaction-pipeline` shows TTS service and alembic merge | **Keep alive** |
| `competent-montalcini` | 1 commit | Local worktree with Dockerized TTS microservice (commit `1ebd07ab2`) | **Keep alive** |

**Command Evidence:**

```bash
# Operator console branch - NOT in main
$ git branch -a --contains origin/codex/add-operator-console-route 2>/dev/null | grep main || echo "NOT IN MAIN"
NOT IN MAIN

$ git log --oneline main..codex/add-operator-console-route
26e68b26a fix: restore frontend test baseline
89ce209f6 fix: resolve dropdown menu merge conflict
b7bec4af5 feat: add operator console completion replay surface

# Voice turn pipeline - NOT in main
$ git log --oneline main..origin/codex/voice-turn-interaction-pipeline
6f88305f4 fix(db): merge alembic heads after voice pipeline integration
d9bde2590   added TTS service container and voice mode

# Competent-montalcini worktree - NOT in main
$ git log --oneline main..competent-montalcini
1ebd07ab2 Add local Dockerized TTS microservice (Qwen3)
```

### Worktree Branches (Ambiguous State)

| Branch | State | Evidence | Recommendation |
|--------|-------|----------|----------------|
| `busy-sinoussi` | At main | `git log main..busy-sinoussi` shows no unique commits | **Safe to delete locally** |
| `jittery-bobcat` | At main | No unique commits vs main | **Safe to delete locally** |
| `coming-hedgehog` | At main | No unique commits vs main | **Safe to delete locally** |

**Note:** These are worktree branches that appear to be at the same commit as main. They can be safely deleted locally once their worktrees are removed.

---

## Category 3: Unclear/Needs Manual Review

These branches require additional context to classify properly:

| Branch | Reason | Recommended Action |
|--------|--------|-------------------|
| `codex/describe-codexrunner-behavior` | Local branch, need to check if work was absorbed via other means | Manual review |
| `codex/create-plugin-packages-and-expose-is_cloud_backend` | Local branch, may contain unmerged work | Manual review |
| `main` worktree at `/private/tmp/codexify-main-smoke-20260311` | Purpose is smoke testing, not development | Keep for testing workflow |

---

## Beta Stabilization Merge Cycle: Branch Name Confusion

### The Problem

During the Beta Stabilization campaign, there was ambiguity about which branch was the true integration carrier.

**Early assumption:** `codex/stabilize-codexify-for-beta-testers`
**Actual integration branch:** `codex/apply-campaign-task-execution-rules`

### Resolution Pattern

To identify the true integration branch:

```bash
# Find which branch contains the final task commits
$ git branch --contains 6659fb6e0
codex/apply-campaign-task-execution-rules

# Verify merge commit
$ git log --oneline -1 main
c76b1333d pnpm testMerge branch 'codex/apply-campaign-task-execution-rules'
```

**Key Lesson:** Branch names can be misleading. Always verify with `git branch --contains <commit>` for final task commits.

---

## Common Absorption-Audit Traps

### Trap 1: Branch Names Imply Ownership

**Problem:** Branch named `codex/stabilize-codexify-for-beta-testers` sounds like the integration branch, but `codex/apply-campaign-task-execution-rules` was the actual carrier.

**Solution:** Use `git branch --contains <final-commit>` not branch names.

### Trap 2: Cherry-Picked or Stacked Commits

**Problem:** Work may be absorbed via cherry-picks or rebase operations, making `git branch --merged` unreliable.

**Solution:** Check specific commit hashes:
```bash
git branch -a --contains <commit>
```

### Trap 3: Safety Snapshots Kept Alive

**Problem:** Branches like `safety/20260214-2034-panic` and `recovery/*` serve as backup snapshots but appear in branch lists.

**Solution:** These can be safely deleted once the work they protect is confirmed merged.

### Trap 4: Open PRs with Already-Merged Substance

**Problem:** PRs may remain open even though their commits are already on main via a different merge path.

**Solution:** Check PR commits with `git branch --contains` to see if they're already in main.

### Trap 5: Local vs Remote Branch Divergence

**Problem:** Local branch may have un-pushed commits even if remote branch is merged.

**Solution:** Always check both:
```bash
git log main..<local-branch>
git log main..origin/<branch>
```

---

## Recommended Actions

### Immediate (Safe to Execute)

1. **Delete local merged branches:**
   ```bash
   git branch --merged main | grep -v "^*" | xargs -r git branch -d
   ```

2. **Clean up old recovery/safety branches:**
   ```bash
   git branch | grep -E "^  (recovery/|safety/)" | xargs -r git branch -d
   ```

### Deferred (Needs Decision)

1. **Review `codex/add-operator-console-route`:**
   - Contains 3 unique commits
   - May need PR creation or merge

2. **Review `origin/codex/voice-turn-interaction-pipeline`:**
   - Contains TTS service work not in main
   - May need to be merged or superseded

3. **Review `competent-montalcini`:**
   - Contains Dockerized TTS microservice
   - Worktree can be removed if work is merged elsewhere

---

## Command Reference

```bash
# List all branches
$ git branch -a

# Find branches fully merged into main
$ git branch --merged main

# Find branches NOT merged into main
$ git branch --no-merged main

# Check commits unique to a branch
$ git log --oneline main..<branch>

# Check which branches contain a commit
$ git branch -a --contains <commit-hash>

# Check diff between branches
$ git diff --stat main...<branch>

# List worktrees
$ git worktree list
```

---

## See Also

- `2026-03-12-beta-stabilization-sweep-closeout.md` - Beta Stabilization closeout document
- `merge-worktree-operating-procedure.md` - Worktree management guidelines
