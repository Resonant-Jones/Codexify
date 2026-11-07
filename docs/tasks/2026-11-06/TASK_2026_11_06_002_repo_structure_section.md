# Task Receipt

- Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
- Task ID: 002
- Title: Make the README's Repo Structure section reflect the repository, without volatile counts
- Finding: D-02 (no AD number; this is the structure-section correction from the audit)
- Risk: LOW
- Base commit: `origin/main` at authoring time — see step 0
- Depends on: **TS-001 must be merged first.** TS-002 edits the same `README.md` that TS-001 edits, and TS-002's validator asserts facts TS-001 establishes.
- Blocks: TS-003 (D-03)

## Allowed Files

- `README.md`
- `tests/architecture/test_repo_structure_claims.py` (new)

Any other modified path is a scope violation — the checklist step enforces this.

Note: TS-002 does **not** modify `tests/architecture/test_readme_claims.py`. TS-001's validator is already reconciled and merged; TS-002's rules are a different concern (structure coverage, not command/path truth) and live in their own file so each task's diff stays independently reviewable.

## Why this task exists

The `## Repo Structure` section of `README.md` describes the repository to a new engineer. At the base commit it is wrong in two independent ways, both confirmed against the repository:

1. **It names a directory that does not exist.** The entry
   `- **models/** - Local embedding model files mounted into containers.`
   refers to a top-level `models/` directory with **zero tracked files**; the directory is not present in the tree at all.
2. **It omits most of the repository.** It names 9 paths. The repository has **33 top-level directories containing first-party source files**. The omissions include `tests/` (785 source files), `codex_runner/` (38 first-party source files plus the vendored Pi runtime — the single largest tree in the repository), `browser_host/` (44), `mobile/` (61), `config/` (7), `flows/` (3), `edge/` (2 — a declared pnpm workspace package), and `docs/` (which holds `docs/architecture/00-current-state.md`, the canonical release-truth document).

The root cause of both is the same: the section is maintained by hand and nothing checks it. A reader cannot learn the repository's shape from it, and it names a phantom.

Per the campaign's D-02 correction, the fix describes structure by directory and responsibility **only**. It adds **no file counts** — a hand-maintained count is itself a drift source, and the point of this task is to remove claims that rot rather than to add more.

## Required edits

### E-1 — remove the phantom entry

Delete the `models/` bullet. Do not replace it with another directory; `models/` has no content to describe.

### E-2 — name the real surfaces

Replace the section's bullet list with entries for the top-level directories below. Use exactly these directory names, each with a one-line responsibility description in the style of the existing entries. Keep the existing entries for `guardian/db/migrations/` and `guardian/plugins/`.

| Directory | Responsibility to state |
|---|---|
| `guardian/` | Main backend package: FastAPI app, routes, DB logic, workers, plugins, providers |
| `backend/` | Dockerfile, Alembic config, RAG embedder, and separate TTS microservice |
| `frontend/` | React + Vite app; source lives in `frontend/src` |
| `src-tauri/` | Tauri desktop shell, macOS-first local parity flow, manual packaging gate |
| `tests/` | Backend test suite |
| `codex_runner/` | Campaign engine and CLI, plus the vendored Pi runtime under `codex_runner/vendor/` |
| `browser_host/` | Browser host runtime, attachment grants, and negotiation surfaces |
| `mobile/` | Mobile app source |
| `edge/` | Cloudflare worker; a declared pnpm workspace package |
| `flows/` | Flow definitions for the flow-builder lane |
| `config/` | Supported profile definitions, launchd templates, and operator config examples |
| `docs/` | Documentation corpus; `docs/architecture/00-current-state.md` is the canonical release-truth document |
| `schemas/` | JSON schemas for audit evidence, live proof receipts, and the knowledge graph |
| `services/` | External service adapters |
| `tools/` | Auxiliary CLI tools |
| `skills/` | Agent skill definitions |
| `sql/` | Raw SQL inputs applied outside the Alembic graph |
| `docker/` | Container build contexts |
| `plugins/` | Plugin scaffolding and example plugins |
| `.github/` | CI workflows |

### E-3 — state no counts

The section must not contain a file count, a directory count, or a percentage. The validator enforces this (rule 3 below).

## New validator

Create `tests/architecture/test_repo_structure_claims.py`. It must implement three rules.

### Rule 1 — no phantom entries

Every path named in the `## Repo Structure` section must exist in the repository. A named directory that does not exist is a failure. This is the rule that catches the `models/` defect.

### Rule 2 — every first-party surface is accounted for

Derive the set of top-level directories containing first-party source files, then require that each one is either:

- named in the `## Repo Structure` section, **or**
- listed in an `EXCLUDED_SURFACES` mapping in the test file, whose value is a **non-empty reason string** explaining why it is deliberately not part of the structure section.

Derivation rules, to be implemented exactly:

- Source extensions: `.py .ts .tsx .js .mjs .sh .rs .swift .sql .yaml .yml`
- Excluded path segments anywhere in the path: `node_modules/`, `vendor/`, `dist/`, `build/`, and any path containing `egg-info`
- A directory qualifies when it contains at least one qualifying file

`EXCLUDED_SURFACES` must cover, at minimum, these directories with a reason for each. Add any further directory the derivation surfaces, with its own reason — an exclusion without a reason is itself a failure.

| Directory | Reason to record |
|---|---|
| `browser_host_candidates/` | candidate implementations, not the selected surface |
| `.playwright-cli/` | Playwright CLI tool residue |
| `.playwright-tmp/` | Playwright scratch output |
| `.playwright-mcp/` | Playwright MCP tool residue |
| `GitHub/` | duplicate of `.github/workflows/` |
| `Codexify-Beta/` | beta snapshot copy |
| `archive/` | retired legacy module |
| `codex_memory/` | single-file helper |
| `codex_ralph_loop/` | single-file loop helper |
| `codex_tasks/` | task-definition corpus, not runtime code |
| `cypress/` | frontend end-to-end config only |
| `data/` | data fixtures only |
| `notion_codex_templates/` | template files only |
| `requirements/` | dependency inputs only |

Rule 2 must also assert that **every entry in `EXCLUDED_SURFACES` has a non-empty reason**, and that **every excluded directory still exists** — an exclusion for a directory that has since been removed is stale and must be deleted, not left behind.

### Rule 3 — no volatile counts

The section must not contain a file count, directory count, or percentage. Match on a numeric quantity immediately followed by a count noun — for example `\b\d[\d,]*\s+(files?|directories|dirs|percent|%)\b` — and fail if it matches. Ignore prose that merely contains a bare number.

Follow the precedent at `tests/architecture/test_published_migration_head_claim.py`: resolve the repository root from `Path(__file__).resolve().parents[2]`, derive truth from the repository rather than hardcoding it, and let every assertion failure name the specific offending text.

## Non-goals

- **Do not** add file counts, directory counts, or percentages anywhere in the section (E-3 / rule 3).
- **Do not** state CI status, test counts, or qualification status anywhere in this section. Those change without a commit to `README.md` and would immediately become false claims. In particular, do **not** describe whether `guardian/tests/` runs in CI — that is TS-014's subject, and TS-002 must not pre-empt it.
- **Do not** change the Documentation Map. TS-001 owns it.
- **Do not** change the install command, the hardcoded path, or the `/upload-chat` claims. TS-001 owns those, and TS-001's validator enforces them.
- **Do not** modify `tests/architecture/test_readme_claims.py`.
- **Do not** re-curate which documents the Documentation Map recommends. The two adjacent findings — `docs/infra/system_architecture.md` classified `misleading_identity_drift`, and `docs/infra/context-report.md` classified `historical_archive` in `docs/architecture/kb-validity-matrix.md` — are inputs to **C-01 (TS-006)**, which owns the onboarding-vs-historical classification. Do **not** silently promote or demote either document here, and do not add a blanket rule rejecting links to historical documents — the KB validity matrix is a diagram-source map, not a universal document-approval registry.
- **Do not** add a section, rename a heading, or restructure the README beyond this section.
- **Do not** touch any other file.

## Command Checklist

0. **Precondition — TS-001 is merged and TS-002's own spec is tracked in this worktree.**
   ```bash
   git ls-files --error-unmatch docs/tasks/2026-11-06/TASK_2026_11_06_002_repo_structure_section.md
   git ls-files --error-unmatch tests/architecture/test_readme_claims.py
   ```
   The second command must succeed: TS-001's validator must be present in the base. If either fails, **STOP** — the execution base is wrong.

   Do not add either path to this task's commit. They belong to the base.
1. Preflight — tree must be clean:
   ```bash
   git status --porcelain -uall
   ```
   If non-empty: `echo 'STOP: dirty tree'; exit 1`
2. Capture the pre-change evidence:
   ```bash
   grep -n 'models/' README.md
   git ls-files models/ | wc -l
   ```
   The first must match; the second must print `0` — confirming the phantom. If `models/` is non-empty, STOP and report: the base has moved.
3. Capture the derived surface set before the edit, for the closeout:
   ```bash
   python3 -m pytest -q tests/architecture/test_repo_structure_claims.py --collect-only
   ```
   (The file does not exist yet at this point — run it after step 5.) Instead, record:
   ```bash
   git ls-files | grep -vE 'node_modules|/vendor/|/dist/|/build/|egg-info' \
     | awk -F/ 'NF>1{print $1}' | sort -u | wc -l
   ```
4. Apply E-1 … E-3 to `README.md`.
5. Apply the validator: create `tests/architecture/test_repo_structure_claims.py`.
6. Scope guard — only the two allowed paths may be modified:
   ```bash
   for f in $(git diff --name-only; git ls-files --others --exclude-standard); do
     case "$f" in
       README.md|tests/architecture/test_repo_structure_claims.py) ;;
       *) echo "STOP: out-of-scope file $f"; exit 1 ;;
     esac
   done
   ```
7. Validate the new test passes:
   ```bash
   python -m pytest -q tests/architecture/test_repo_structure_claims.py
   ```
8. **Mutation check** — the new rules must detect their own target failures. Preserve the corrected README bytes with an `EXIT` trap, introduce each defect in turn, and require exit code **1** with the failure naming the offending surface.
   ```bash
   corrected="$(mktemp -t ts002_readme.XXXXXX)"
   cp README.md "$corrected"
   restore_corrected() { cp "$corrected" README.md; }
   trap restore_corrected EXIT

   # Defect A: a named directory that does not exist (the models/ class).
   printf '\n- `models/` - Local embedding model files mounted into containers.\n' >> README.md
   mut_output="$(python -m pytest -q tests/architecture/test_repo_structure_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: phantom-entry mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -q 'models/'; then
     echo "STOP: the phantom-entry failure did not name the offending path"
     exit 1
   fi
   restore_corrected

   # Defect B: a required surface removed from the section (the omission class).
   grep -v 'codex_runner/' "$corrected" > README.md
   mut_output="$(python -m pytest -q tests/architecture/test_repo_structure_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: omission mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -q 'codex_runner'; then
     echo "STOP: the omission failure did not name the missing surface"
     exit 1
   fi
   restore_corrected

   python -m pytest -q tests/architecture/test_repo_structure_claims.py || {
     echo "STOP: validator did not pass after restoring the corrected README"
     exit 1
   }

   trap - EXIT
   rm -f "$corrected" || true
   ```
   The `trap restore_corrected EXIT` is required: the corrected bytes are restored even if a mutation check aborts. Note that `rm` of a temp file may be refused by the host's deletion policy — that is expected, report the residue, and do not bypass the policy. The restoration must be verified independently:
   ```bash
   grep -n 'models/' README.md      # must return nothing
   grep -c 'codex_runner/' README.md # must be at least 1
   grep -n 'files' README.md | sed -n '/Repo Structure/,+14p'   # no count phrases
   ```
9. Validate TS-001's validator still passes against the edited README:
   ```bash
   python -m pytest -q tests/architecture/test_readme_claims.py
   ```
   TS-002 must not break TS-001's guarantees.
10. Validate the surrounding architecture suite:
    ```bash
    python -m pytest -q tests/architecture tests/evidence_packets
    ```
    `tests/architecture/test_guardian_evidence_packet_make_target.py::test_make_target_passes_current_fixture_set_without_writing_files`
    is a **known pre-existing environmental failure** (the Make target writes a `__pycache__` `.pyc` into `scripts/guardian/`, violating the test's filesystem snapshot). It is documented and unresolved, and is **not** a TS-002 defect. If it fails, report it as the known exception and deselect it:
    ```bash
    python -m pytest -q tests/architecture tests/evidence_packets \
      --deselect tests/architecture/test_guardian_evidence_packet_make_target.py::test_make_target_passes_current_fixture_set_without_writing_files
    ```
    State the result exactly as: *N tests passing across M files, one known test deselected, with a reported baseline reproduction.*
11. Stage and commit:
    ```bash
    git add README.md tests/architecture/test_repo_structure_claims.py
    git commit -m "docs(readme): make the Repo Structure section reflect the repository

Removes a phantom entry for a directory that does not exist, names the
top-level surfaces the section previously omitted, and states no file counts
so the section cannot rot into a numeric drift source.

Adds tests/architecture/test_repo_structure_claims.py, which rejects named
directories that do not exist, requires every first-party source surface to
be either named or excluded with a recorded reason, and rejects volatile
counts.

Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
Task: 002 (D-02)"
    ```

## Expected Outputs

- The `## Repo Structure` section names no directory that does not exist.
- Every top-level first-party source surface is either named in the section or excluded with a non-empty recorded reason.
- The section contains no file, directory, or percentage counts.
- `tests/architecture/test_repo_structure_claims.py` exists, passes, and has been shown to **fail with exit code 1** against both a phantom entry and an omitted surface, with the failure naming the offending path in each case.
- `tests/architecture/test_readme_claims.py` still passes — TS-002 does not weaken TS-001.
- One commit containing exactly the two allowed files.

## Qualification-Surface Impact

**None.** The qualification surface for `supported-compose-stock` is `.dockerignore`, `docker-compose*.yml`, `config/**`, `backend/**`, `guardian/**`, `frontend/**`, `plugins/**`, `codex_runner/**`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`. Neither allowed file appears in it.

## Rollback / Cleanup

```bash
git restore --staged README.md tests/architecture/test_repo_structure_claims.py 2>/dev/null || true
git restore README.md 2>/dev/null || true
rm -f tests/architecture/test_repo_structure_claims.py
rm -f /tmp/ts002_readme.* 2>/dev/null || true
```

`git restore` restores the **committed** README, not the corrected one — use it only to abandon the task, not to undo the mutation probe. If the host's deletion policy refuses the temp file, report the residue rather than bypassing it.

## Dependencies / Prereqs

- `command -v git >/dev/null`
- `command -v python3 >/dev/null`
- `python3 -m pytest --version` succeeds (the repository's virtualenv is at `/Volumes/Dev_SSD/Codexify-main/.venv`; use its `bin/python` if the system interpreter lacks `pytest`)
- Network access is **not** required
- **TS-001 is merged** and present in the base

## Closeout Summary

Report, in this order:

1. The commit SHA produced.
2. The count of top-level first-party source surfaces derived, and how many are named in the section versus excluded with a reason.
3. Step 8's observed mutation-failure output for **both** defect classes, with the captured exit codes.
4. Step 9's TS-001 validator result and step 10's suite result, stated in the exact form given in step 10.
5. Confirmation that the scope guard listed only the two allowed files.
6. Explicit statement that no runtime or CI behaviour was changed and no startup was proven.
