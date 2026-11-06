# Task Receipt

- Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
- Task ID: 001
- Title: Correct the README's broken and false claims, and bind them to a static validator
- Finding: AD-06, AD-07, AD-08, AD-09 (campaign item D-01)
- Risk: LOW
- Base commit: `5b12b46f9ffe1c113afb55757abb5632fc97607c` (`origin/main` at authoring time; reviewer-reachable)
- Depends on: this Task Spec must be **tracked in the execution worktree's base** before the task starts — see step 0
- Blocks: TS-002 (D-02, shares `README.md`)

> **Base re-pin.** The spec was first authored against `806d293e9`, which is 11
> commits behind `origin/main`. `README.md` is byte-identical between the two, and
> all four findings below were re-verified at `5b12b46f9`. The base is pinned to the
> current tip. If the executor's `HEAD` is newer than the pin, step 3's
> re-verification governs — it is the authority on whether the findings still hold.

## Allowed Files

- `README.md`
- `tests/architecture/test_readme_claims.py` (new)

Any other modified path is a scope violation — the checklist step enforces this.

## Why this task exists

The README is the first document a new engineer reads, and it currently contains four
classes of false or broken claim. Every one of them was confirmed against the
repository at the base commit:

1. `pip install -r requirements.txt` appears three times (`:320`, `:506`, `:522`).
   There is no root `requirements.txt`. The root has a `requirements/` **directory**
   containing `all.txt` (786 lines, pip-compile output), `base.in`, `dev.in`, `ai.in`,
   `websearch.in`. Each of the three commands fails on its first executed line.
2. `README.md:487` hardcodes `cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify`
   — an absolute path on one maintainer's machine, inside the "Development Workflow →
   Verify" block.
3. Three sites (`:83`, `:165`, `:608`) assert that `/upload-chat` returns `503`
   because `codexify.rag.enhanced_rag` is missing. **The endpoint was removed.**
   `guardian/guardian_api.py:1862` reads
   `# (Removed redundant /upload-chat endpoint; use guardian/routes/migration.py instead)`.
   No `enhanced_rag` module exists. The only surviving `upload-chat` match is the
   unrelated `/upload-chatgpt-export` in `guardian/routes/migration.py:827-828`.
   The endpoint cannot return `503`; it does not exist.
4. The Documentation Map (`:614-658`) lists **13 bullets** as bare filenames with no
   paths. One does not exist anywhere; two are stated at paths that do not exist.

## Required edits

### E-1 — install command (AD-06)

Replace `pip install -r requirements.txt` with `pip install -r requirements/all.txt` at
all three sites (`:320`, `:506`, `:522`). Do not alter any other line of those code
blocks.

### E-2 — hardcoded path (AD-07)

Replace `cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify` with a
placeholder that is obviously a placeholder, e.g. `cd /path/to/Codexify`.

### E-3 — removed endpoint (AD-08)

Remove the `/upload-chat` status-table row at `:83`, and remove the
`/upload-chat` bullet at `:165` and at `:608`. Do **not** substitute a different
endpoint description — the surrounding bullets make their own claims and stay as they
are. If removing a row leaves the table malformed, fix the table's shape only.

### E-4 — Documentation Map paths (AD-09)

Replace each bare filename with its real repository path, resolved as follows. Use
these exact paths — do not re-derive them, and do not substitute a different document.

| README entry | Correct path | Note |
|---|---|---|
| `Codexify-System-Specification.md` | `docs/Codexify/Codexify-System-Specification.md` | path was unstated |
| `Codexify-Master-Architecture-Report.md` | `docs/Codexify/Codexify-Master-Architecture-Report.md` | path was unstated |
| `system_architecture.md` | `docs/infra/system_architecture.md` | path was unstated |
| `Event_Graph.md` | `docs/Future-Features/Event_Graph.md` | path was unstated |
| `context-report.md` | `docs/infra/context-report.md` | path was unstated |
| `Codexify-UI-Rendering-Protocol.md` | `docs/dev/ARTIFACT3—Codexify-UI-Rendering-Protocol.md` | filename contains an em-dash |
| `CODEXIFY-PERCEPTUAL-STACK-SPEC.md` | `docs/dev/ARTIFACT7--CODEXIFY-PERCEPTUAL-STACK-SPEC.md` | filename contains a double dash |
| `docs/SECURITY.md` | `SECURITY.md` | README stated a path that does not exist; the root file is the intended one |
| `docs/CONFIGURATION.md` | `docs/Codexify/CONFIGURATION.md` | README stated a path that does not exist |
| `docs/security/auth-boundary-decision.md` | unchanged | already correct |
| `docs/dev/SECURITY_HARDENING_PLAN.md` | unchanged | already correct |
| `CONTRIBUTING.md` | unchanged | already correct |
| `Thread-Artifact-Lineage.md` | **remove the entry** | no file of this name exists anywhere in the repository |

For `Thread-Artifact-Lineage.md`: **remove the entry and record it in the closeout.**
Do not substitute `docs/exports/codexify-space-source-kb/05-retrieval-continuity-and-artifact-lineage.md`
or any other document — that is a different document in an exports tree, and choosing a
replacement is a separate decision that this task does not make.

The map contains **13 bullets today**; this edit leaves **12**. The validator in E-5
rule 2 asserts that floor, so an entry removed without being replaced fails the test
rather than passing quietly.

Render the corrected entries as markdown links so the path is unambiguous, e.g.
`- [Codexify-System-Specification.md](docs/Codexify/Codexify-System-Specification.md) — what Codexify is, what problems it solves, and what it intentionally does not do.`
Keep each entry's existing one-line description.

### E-5 — static validator (new file)

Create `tests/architecture/test_readme_claims.py`. It must assert, at minimum:

1. Every `pip install -r <path>` target in `README.md` resolves to an existing file
   relative to the repository root.
2. **The Documentation Map is present, fully parsed, and every entry is a validated
   link.** This rule has four separate requirements, and all four are load-bearing:
   - The `## Documentation Map` heading must be located. If it is absent, **FAIL**.
     "Section not found" must never be treated as "nothing to validate".
   - The section must contain **at least 12 bullet entries**. Deleting every entry
     must fail this check. An empty section is a failure, not a pass.
   - **Every bullet must parse as a markdown link**, and the number of parsed links
     must equal the number of bullets. A bullet whose format drifts and stops
     parsing is a failure, not a silently skipped entry — otherwise a format change
     could quietly delete entries from validation while leaving them in the README.
   - Every link target must resolve to an existing tracked file.

   The expected post-fix count is **12 entries**: 13 bullets today, minus the
   removed `Thread-Artifact-Lineage.md`. Adding entries later is permitted — the
   check asserts a floor and a parse-completeness ratio, not an exact set.
3. `README.md` contains no absolute path under a user home directory
   (a `/Users/<name>/` or `/home/<name>/` prefix).
4. **The removed `/upload-chat` route is not described as an endpoint** in
   `README.md`. This must be implemented with a **path-segment boundary, not a bare
   substring**: a naive `'/upload-chat' in text` check also matches
   `/upload-chatgpt-export`, which is a **different, live** endpoint
   (`guardian/routes/migration.py:827-828`) and must remain documentable. Use a
   boundary that matches only the removed path:

   ```python
   REMOVED_UPLOAD_CHAT_ROUTE = re.compile(r"/upload-chat(?![A-Za-z0-9_-])")
   ```

   This matches `/upload-chat` at a token boundary (in backticks, followed by
   whitespace or punctuation) and does **not** match `/upload-chatgpt-export`.
   The docstring must record that the endpoint was removed at
   `guardian/guardian_api.py:1862` and that re-adding it requires updating both the
   route and this assertion. **Add a self-test asserting the regex does not match
   `/upload-chatgpt-export`** — otherwise the boundary can silently regress into a
   substring check, and the failure mode is a false positive that would block a
   legitimate future documentation change.

Follow the precedent at `tests/architecture/test_published_migration_head_claim.py`:
resolve the repository root from `Path(__file__).resolve().parents[2]`, derive truth
from the repository rather than hardcoding it, and let an assertion failure name the
specific offending text. Scope rule 2 to the `## Documentation Map` section only — do
not validate links in unrelated README sections in this task.

## Non-goals

- **Do not** prove that the Quick Start works end to end. Static path and command
  validity is what this task establishes. Runtime startup proof belongs to the release
  lane's supported-startup qualification; a green validator is **not** startup proof.
- **Do not** modify the "Repo Structure" section. That is TS-002 (D-02), which owns
  `README.md` after this task completes.
- **Do not** add or remove any endpoint, route, module, or dependency.
- **Do not** touch `docs/**`. The `docs/architecture/README.md` reconciliation is a
  separate task (TS-003, D-03).
- **Do not** introduce file counts, version numbers, or other volatile values into
  `README.md`.
- **Do not** broaden rule 2 to all README links; scope it to the Documentation Map.

## Command Checklist

0. **Precondition — the Task Spec must be tracked in this worktree.** This Task Spec
   is part of the base, not a working-tree artifact:
   ```bash
   git ls-files --error-unmatch docs/tasks/2026-11-06/TASK_2026_11_06_001_readme_claim_correction.md
   ```
   If this reports "did not match any file(s) known to git", **STOP**. The execution
   worktree was created before the Task Spec landed. Do not `git add` it into this
   task, and do not relax steps 1 or 7 to accommodate it — start the execution from a
   base that already contains the tracked spec.
1. Preflight — tree must be clean:
   ```bash
   git status --porcelain -uall
   ```
   If non-empty: `echo 'STOP: dirty tree'; exit 1`
2. Record the base commit and confirm reviewer reachability:
   ```bash
   git rev-parse HEAD
   git branch -r --contains HEAD
   ```
   The pinned base `5b12b46f9` must be reachable from a remote ref. `HEAD` may be
   newer than the pin — step 3's re-verification is the authority on whether the
   findings still hold at that commit.
3. Capture the pre-change defect evidence:
   ```bash
   grep -n 'pip install -r requirements.txt' README.md
   grep -n '/Users/' README.md
   grep -n 'upload-chat' README.md
   grep -n 'Thread-Artifact-Lineage' README.md
   ```
   All four must return matches before the edit. If any returns nothing, STOP and
   report — the base has moved and the finding set must be re-verified.
4. Confirm the `/upload-chat` removal claim against source before deleting the
   README claims:
   ```bash
   grep -rn 'upload-chat' --include=*.py guardian/
   sed -n '1858,1866p' guardian/guardian_api.py
   ```
   The only `upload-chat` matches must be `/upload-chatgpt-export` in
   `guardian/routes/migration.py`, plus the removal comment.
5. Apply E-1 … E-4 to `README.md`.
6. Apply E-5: create `tests/architecture/test_readme_claims.py`.
7. Scope guard — only the two allowed paths may be modified:
   ```bash
   for f in $(git diff --name-only; git ls-files --others --exclude-standard); do
     case "$f" in
       README.md|tests/architecture/test_readme_claims.py) ;;
       *) echo "STOP: out-of-scope file $f"; exit 1 ;;
     esac
   done
   ```
8. Validate the new test passes:
   ```bash
   python -m pytest -q tests/architecture/test_readme_claims.py
   ```
9. **Validate the new test actually fails when the claim is wrong** (mutation check —
   the test must not pass vacuously).

   The corrected README bytes must survive this step. `git checkout -- README.md`
   would restore the file from `HEAD` and **discard every correction made in steps
   5 and 6**, leaving the final validation to run against the uncorrected README.
   Preserve the corrected bytes explicitly, and restore those bytes — not the
   committed ones:

   ```bash
   corrected="$(mktemp -t ts001_readme.XXXXXX)"
   cp README.md "$corrected"
   restore_corrected() { cp "$corrected" README.md; }
   trap restore_corrected EXIT

   printf '\n<!-- mutation probe -->\npip install -r requirements/nonexistent.txt\n' >> README.md
   python -m pytest -q tests/architecture/test_readme_claims.py   # must FAIL

   restore_corrected
   python -m pytest -q tests/architecture/test_readme_claims.py   # must PASS

   trap - EXIT
   rm -f "$corrected"
   ```

   The `trap restore_corrected EXIT` is required: if the first pytest run fails for
   an unexpected reason, or the shell aborts mid-step, the corrected README is still
   restored. Cleanup must not depend on the mutation check passing.

   **Verify the restore actually happened** before continuing:
   ```bash
   grep -n 'requirements/nonexistent.txt' README.md   # must return nothing
   grep -n 'mutation probe' README.md                  # must return nothing
   grep -n 'pip install -r requirements/all.txt' README.md   # must match (3)
   ```
   Report the observed failure output. If the mutated file still passes, the
   validator is broken — fix it before continuing. If the corrected README was not
   restored, the restore step is broken — fix that first and re-run the whole step.
10. Validate the surrounding architecture suite still passes:
    ```bash
    python -m pytest -q tests/architecture tests/evidence_packets
    ```
11. Confirm no stale references remain:
    ```bash
    grep -n 'pip install -r requirements.txt' README.md   # must return nothing
    grep -n '/Users/' README.md                            # must return nothing
    grep -n 'upload-chat' README.md                        # must return nothing
    ```
12. Stage and commit:
    ```bash
    git add README.md tests/architecture/test_readme_claims.py
    git commit -m "docs(readme): correct broken install command, hardcoded path, removed endpoint, and doc-map paths

Also adds tests/architecture/test_readme_claims.py to bind these claims to a
static validator so the same drift class cannot return silently.

Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
Task: 001 (D-01)
Findings: AD-06, AD-07, AD-08, AD-09"
    ```

## Expected Outputs

- `README.md` contains no `pip install -r requirements.txt`, no `/Users/` absolute
  path, and no `/upload-chat` claim.
- Every Documentation Map entry points at an existing tracked file, or has been
  removed with the removal recorded in the closeout.
- `tests/architecture/test_readme_claims.py` exists, passes, and has been shown to
  fail against a mutated README (step 9).
- `tests/architecture` and `tests/evidence_packets` still pass.
- One commit containing exactly the two allowed files.

## Qualification-Surface Impact

**None.** The qualification surface for `supported-compose-stock` is
`.dockerignore`, `docker-compose*.yml`, `config/**`, `backend/**`, `guardian/**`,
`frontend/**`, `plugins/**`, `codex_runner/**`, `package.json`, `pnpm-lock.yaml`,
`pnpm-workspace.yaml`. Neither allowed file appears in it, so this task does not
invalidate qualification freshness and needs no release-lane coordination.

## Rollback / Cleanup

```bash
git restore --staged README.md tests/architecture/test_readme_claims.py 2>/dev/null || true
git restore README.md 2>/dev/null || true
rm -f tests/architecture/test_readme_claims.py
rm -f /tmp/ts001_readme.* 2>/dev/null || true
```

The `ts001_readme.*` cleanup covers the mutation-probe copy from step 9. Note that
`git restore README.md` restores the **committed** README, not the corrected one —
use it only when abandoning the task entirely, not to undo the mutation probe.

## Dependencies / Prereqs

- `command -v git >/dev/null`
- `command -v python3 >/dev/null`
- `python3 -m pytest --version` succeeds (the repository's virtualenv is at
  `/Volumes/Dev_SSD/Codexify-main/.venv`; use its `bin/python` if the system
  interpreter lacks `pytest`)
- Network access is **not** required
- The base commit is reviewer-reachable: `5b12b46f9` is `origin/main`
- **This Task Spec is tracked in the execution worktree's base** (step 0)

## Closeout Summary

Report, in this order:

1. The commit SHA produced.
2. Step 9's observed mutation-failure output (the proof that the validator bites).
3. Step 10's suite result.
4. Confirmation that the scope guard in step 7 listed only the two allowed files.
5. The removed `Thread-Artifact-Lineage.md` entry, flagged as a follow-up question:
   a document of that intent may need to be written or an existing one designated.
   **Do not** designate one in this task.
6. Explicit statement that no startup/runtime behaviour was proven by this task, and
   that runtime proof remains the release lane's.
