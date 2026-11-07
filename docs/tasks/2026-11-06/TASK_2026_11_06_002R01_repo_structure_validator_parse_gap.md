# Task Receipt

- Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
- Task ID: 002-R01
- Title: Close the parser bypass in the Repo Structure validator
- Finding: R-01 (independent reconciliation of TS-02, PARTIALLY_ALIGNED)
- Risk: LOW
- Base commit: `origin/main` at authoring time — see step 0
- Depends on: **TS-002 must be merged.** This task corrects the validator TS-002 introduced.
- Blocks: TS-003 (D-03)

This is a **bounded correction to an already-merged task**, not a new work item. It
closes one named gap and changes nothing else.

## Allowed Files

- `tests/architecture/test_repo_structure_claims.py`

Any other modified path is a scope violation — the checklist step enforces this.

`README.md` is **not** in scope. The README's Repo Structure section is correct as
merged; the defect is in the validator's parsing, not in the document.

## Why this task exists

The TS-02 validator extracts the paths a section names with `_path_claims()`, which
reads **backtick-quoted spans only**. A bullet that names a directory without
backticks is therefore invisible to the validator:

```
- models/ - Local model storage
```

The bullet is present in the section, but no path claim is extracted from it, so
Rule 1 never asks whether `models/` exists. A contributor can add a phantom
directory entry — the exact defect class TS-002 exists to prevent — and the
validator stays green.

This was found in independent reconciliation of TS-02 (R-01, P2, verified
validator bypass) and reproduced against the merged validator at
`90d1023162f9cf9e77f12db5ca64112b16d7f634`.

The gap is real and it is narrow: it is a **parsing** defect, not a coverage
defect. Rule 2's derivation is unaffected — it reads the repository, not the
section. Rule 3's count scan is unaffected. Only Rule 1's claim extraction has a
blind spot.

There is a second, narrower variant of the same bypass, also reproduced:

```
- models/ - Local model storage, see `backend/`
```

Here the first backtick span is `backend/`, so the validator treats `backend/` as
the bullet's subject and never examines `models/` at all.

## Required edits

### E-1 — a bullet's leading path declaration is required, and its absence is an explicit failure

Every bullet in the section must begin with a path declaration. A bullet whose
leading text is not a recognised path declaration must cause an explicit
assertion failure naming the offending bullet — not be skipped.

"Recognised path declaration" means the bullet's leading text is a path-like
token: one or more path segments, optionally ending in `/`. This is the form the
merged section already uses for every one of its 22 bullets, so the rule accepts
the current document unchanged.

### E-2 — the leading declaration is the bullet's subject, not its first backtick

A bullet's subject is its **leading path declaration**. Additional paths named
later in the bullet (for example `backend/` in the variant above, or
`codex_runner/vendor/` in the merged section) are still claims and are still
checked — but they are claims *in addition to* the subject, never instead of it.

This closes the variant where a later backtick span was silently promoted to
subject.

### E-3 — the fix must not accept prose as a path

The path-declaration rule must not be so permissive that ordinary words are read
as directory names. A bullet whose leading text is a plain word or phrase
(`Local model storage`) is still a malformed bullet and still fails.

## Required test

The validator gains a committed test that exercises **both** a valid input and a
malformed input — the reviewer's template improvement, applied to this task:

- **Valid input**: a bullet whose leading text is a path declaration is parsed
  as a subject, and its later backticked paths are parsed as additional claims.
- **Malformed input**: a bullet whose leading text is *not* a path declaration
  is rejected — the extraction must not silently drop it.

This test is committed to the repository, so the bypass cannot be reintroduced
without the test failing. The mutation gate below remains the end-to-end proof
against the real document.

## Command Checklist

0. **Precondition — TS-002 is merged and its validator is present in the base.**
   ```bash
   git ls-files --error-unmatch tests/architecture/test_repo_structure_claims.py
   ```
   If it fails, **STOP** — the execution base is wrong.

   Do not add that path to this task's commit. It belongs to the base.
1. Preflight — tree must be clean:
   ```bash
   git status --porcelain -uall
   ```
   If non-empty: `echo 'STOP: dirty tree'; exit 1`
2. Confirm the bypass reproduces against the base validator, before the fix:
   ```bash
   python3 - <<'PY'
   import importlib.util, sys
   spec = importlib.util.spec_from_file_location(
       "v", "tests/architecture/test_repo_structure_claims.py")
   mod = importlib.util.module_from_spec(spec)
   sys.modules["v"] = mod
   spec.loader.exec_module(mod)
   good = "- `guardian/` - Main backend package.\n"
   bad = good + "- models/ - Local model storage\n"
   before, after = mod._path_claims(good), mod._path_claims(bad)
   assert before == after, "bypass no longer reproduces — re-check the base"
   print("bypass reproduces: claims unchanged:", before)
   PY
   ```
   The assertion must hold. If it does not, STOP and report: the base has moved.
3. Apply E-1 … E-3 and the required test to
   `tests/architecture/test_repo_structure_claims.py`.
4. Scope guard — only the one allowed path may be modified:
   ```bash
   for f in $(git diff --name-only; git ls-files --others --exclude-standard); do
     case "$f" in
       tests/architecture/test_repo_structure_claims.py) ;;
       *) echo "STOP: out-of-scope file $f"; exit 1 ;;
     esac
   done
   ```
5. Validate the validator passes against the merged README:
   ```bash
   python -m pytest -q tests/architecture/test_repo_structure_claims.py
   ```
6. **Mutation check — Defect C, the malformed-bullet class.** The unquoted
   phantom bullet must be detected, and the failure must name it. Preserve the
   corrected bytes with an `EXIT` trap.
   ```bash
   corrected="$(mktemp -t ts002r01_readme.XXXXXX)"
   cp README.md "$corrected"
   restore_corrected() { cp "$corrected" README.md; }
   trap restore_corrected EXIT

   # Insert the unquoted phantom bullet INTO the Repo Structure section, where
   # the rule under test reads it.
   python - "$corrected" <<'PY'
   import re, sys
   path = "README.md"
   text = open(path, encoding="utf-8").read()
   head = "## Repo Structure"
   i = text.index(head) + len(head)
   j = text.find("\n## ", i)
   section = text[i:] if j == -1 else text[i:j]
   bullet = "- models/ - Local model storage\n"
   k = section.index("\n") + 1
   section = section[:k] + bullet + section[k:]
   text = text[:i] + section + (text[j:] if j != -1 else "")
   open(path, "w", encoding="utf-8").write(text)
   PY

   mut_output="$(python -m pytest -q tests/architecture/test_repo_structure_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: malformed-bullet mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -q 'models/'; then
     echo "STOP: the malformed-bullet failure did not name the offending bullet"
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
   The `trap restore_corrected EXIT` is required. Note that `rm` of a temp file
   may be refused by the host's deletion policy — that is expected, report the
   residue, and do not bypass the policy.
7. **The two previously-passing defect classes must still fail.** The fix must
   not have weakened Rules 1 or 2. Re-run TS-002's original two-class gate
   unchanged: a quoted phantom entry inserted into the section must fail naming
   `models/`, and removing the `codex_runner/` bullet must fail naming
   `codex_runner`.
8. Validate TS-001's validator still passes:
   ```bash
   python -m pytest -q tests/architecture/test_readme_claims.py
   ```
9. Validate the surrounding architecture suite:
   ```bash
   python -m pytest -q tests/architecture tests/evidence_packets
   ```
   `tests/architecture/test_guardian_evidence_packet_make_target.py::test_make_target_passes_current_fixture_set_without_writing_files`
   is a **known pre-existing environmental failure** (the Make target writes a
   `__pycache__` `.pyc` into `scripts/guardian/`, violating the test's filesystem
   snapshot). It is documented and unresolved, and is **not** a defect of this
   task. If it fails, report it as the known exception and deselect it:
   ```bash
   python -m pytest -q tests/architecture tests/evidence_packets \
     --deselect tests/architecture/test_guardian_evidence_packet_make_target.py::test_make_target_passes_current_fixture_set_without_writing_files
   ```
   State the result exactly as: *N tests passing across M files, one known test
   deselected, with a reported baseline reproduction.*
10. Stage and commit:
    ```bash
    git add tests/architecture/test_repo_structure_claims.py
    git commit -m "fix(readme): close the parser bypass in the Repo Structure validator

    A bullet that named a directory without backticks was invisible to the
    path extractor, so a phantom directory entry could be added to the
    README's Repo Structure section without the validator failing.

    A bullet's leading path declaration is now required and its absence is an
    explicit failure rather than a skip. The leading declaration is the
    bullet's subject; later backticked paths remain additional claims.

    Adds a committed test covering a valid input and a malformed input, so the
    bypass cannot be reintroduced silently.

    Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
    Task: 002-R01 (R-01)"
    ```

## Expected Outputs

- A bullet whose leading text is not a path declaration causes an explicit
  assertion failure naming the offending bullet.
- A bullet's subject is its leading path declaration, not the first backtick
  span in the line.
- A committed test exercises a valid input and a malformed input.
- The quoted-phantom defect class still fails, naming `models/`.
- The omitted-surface defect class still fails, naming `codex_runner`.
- `tests/architecture/test_readme_claims.py` still passes.
- One commit containing exactly the one allowed file.

## Qualification-Surface Impact

**None.** The qualification surface for `supported-compose-stock` is
`.dockerignore`, `docker-compose*.yml`, `config/**`, `backend/**`, `guardian/**`,
`frontend/**`, `plugins/**`, `codex_runner/**`, `package.json`, `pnpm-lock.yaml`,
`pnpm-workspace.yaml`. The allowed file appears in none of them.

## Rollback / Cleanup

```bash
git restore --staged tests/architecture/test_repo_structure_claims.py 2>/dev/null || true
git restore tests/architecture/test_repo_structure_claims.py 2>/dev/null || true
rm -f /tmp/ts002r01_readme.* 2>/dev/null || true
```

`git restore` restores the **committed** file, not the corrected one — use it
only to abandon the task, not to undo the mutation probe. If the host's deletion
policy refuses the temp file, report the residue rather than bypassing it.

## Dependencies / Prereqs

- `command -v git >/dev/null`
- `command -v python3 >/dev/null`
- `python3 -m pytest --version` succeeds (the repository's virtualenv is at
  `/Volumes/Dev_SSD/Codexify-main/.venv`; use its `bin/python` if the system
  interpreter lacks `pytest`)
- Network access is **not** required
- **TS-002 is merged** and its validator is present in the base

## Closeout Summary

Report, in this order:

1. The commit SHA produced.
2. The bypass reproduction from step 2 — the before/after claim lists.
3. Step 6's observed mutation output for the malformed-bullet class, with the
   captured exit code.
4. Step 7's result for the two previously-passing defect classes.
5. Step 8's TS-001 validator result and step 9's suite result, stated in the
   exact form given in step 9.
6. Confirmation that the scope guard listed only the one allowed file.
7. Explicit statement that no runtime or CI behaviour was changed and no startup
   was proven.
