# Task Receipt

- Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
- Task ID: 004
- Title: Bind the consulting capability audit's countable and link claims to the repository
- Finding: D-04 (claim-binding extension, reusing the existing pattern)
- Risk: LOW
- Base commit: `origin/main` at authoring time — see step 0
- Depends on: TS-003 (merged). TS-004 touches `docs/consulting/Codexify_Codebase_Capability_Audit.md`, which no earlier task edits.
- Blocks: TS-005 (D-05, CHANGELOG currency)

## Scope note: D-04's first target is already resolved

D-04 named three claim classes. Its first — "`docs/architecture/README.md:60`
('twelve paths', actually 18)" — **no longer exists**. TS-003 replaced the KB
index's registry entry, and the current text states the stable fact and points at
the registry's blocker strings instead of repeating a tip-dependent count. The
same pattern PR #1028 established for `00-current-state.md`.

The other two classes are **live and wrong today**, and writing the validator
D-04 asked for surfaces a fourth that D-04 did not name.

## Allowed Files

- `docs/consulting/Codexify_Codebase_Capability_Audit.md`
- `tests/architecture/test_capability_audit_claims.py` (new)

Any other modified path is a scope violation — the checklist step enforces this.

## Why this task exists

`docs/consulting/Codexify_Codebase_Capability_Audit.md` is a client-facing
consulting deliverable. It describes the codebase's shape with numbers and with
links, and **nothing checks either**. It is the same claim class as the README's
(TS-001) and the KB index's (TS-003) — a checkable prose claim with no check.

### D-1 — three module/file counts are stale

| Claim | Document says | Repository has |
|---|---|---|
| Route modules | 45 | 68 |
| Worker modules | 16 | 18 |
| Architecture files | 141 | 852 |

A client reading "45 route modules" against a repository with 68 is reading a
number that was true when the audit was written and is false now. The document
carries no date marker, so a reader has no way to know that.

### D-2 — 202 links carry an absolute path from one machine

Every link in the document points at `/Volumes/Dev_SSD/Codexify-main/…` — one
developer's checkout on one volume. **144 of the document's links are of this
form**, covering 79 unique targets. They resolve for that developer and for
nobody else: not in CI, not in a clone, not in a review.

This is AD-07's defect class — the hardcoded machine path TS-01 corrected in the
README — in a document nobody has corrected.

### D-3 — two links name paths that do not exist

Of the 79 absolute-path targets:

- `requirements.txt` — **does not exist at the repository root.** The root
  requirement file is `requirements/all.txt`. This is AD-06's defect exactly:
  TS-01 corrected it in the README, and the audit still names the file that was
  never there.
- `guardian/services/document_parsers` — exists as a **directory**, not a file.
  A link to it is broken as a file link but resolvable as a directory link.

### D-4 — the document carries no date

The audit states module counts, file counts, and capability statuses, and
declares no "as of" date anywhere. A dated snapshot's numbers are historical
facts; an undated document's numbers are claims about the present. Without a
date, D-1 cannot be corrected — the reader cannot tell whether 45 was ever
right or is simply wrong now.

## Required edits

### E-1 — the counts are either correct or gone

A hand-maintained count in a client-facing document is a drift source, and
every merge that touches the surface moves it. The campaign's established
resolution is the one `00-current-state.md` and the KB index now use: **state
the stable fact, and point at the machine source for the exact number.**

For each of the three counts, replace the number with the fact it stands for,
and name where the current number lives. The route and worker module counts are
derivable from the repository — `git ls-files 'guardian/routes/*.py'` — so the
document should describe the surface by responsibility and let the reader
derive the count, exactly as TS-002's Repo Structure section does.

**If a count is retained, it must be bound** by this task's validator, and then
it must be a value that does not move on every merge. A count that changes
whenever a route is added cannot be bound and must not be retained.

### E-2 — the links are repository-relative

Every `/Volumes/Dev_SSD/Codexify-main/…` link becomes a repository-relative
link that resolves from the document's own directory. The link's **text** must
also change: a link labelled with an absolute path is unreadable even if it
resolves.

### E-3 — every link resolves

The `requirements.txt` link must name the file that exists — `requirements/all.txt`
— and the `guardian/services/document_parsers` link must name a real file inside
that directory rather than the directory itself.

### E-4 — the document states its as-of date

The audit must say when it describes. A dated consulting snapshot may state
counts; an undated one may not.

## New validator

Create `tests/architecture/test_capability_audit_claims.py`. It must implement
three rules, each deriving truth from the repository rather than hardcoding it.

### Rule 1 — no absolute machine paths

No link in the document may target an absolute filesystem path. This is the rule
that catches D-2, and it generalises: any absolute path is specific to one
machine and resolves for no one else.

### Rule 2 — every relative link resolves

Every relative link must resolve to a tracked file, or a directory containing
tracked files, **with exact case** — the same rule TS-03 installed for the KB
index, and for the same reason: CI checks out on a case-sensitive filesystem.

### Rule 3 — no unbound countable claim

The document must not state a module, file, or endpoint count that nothing
binds. This is the rule that catches D-1.

**The design question this task must answer honestly:** a count that changes on
every merge cannot be bound by a test without making CI red on every feature
PR. So the rule is not "no numbers" — the document legitimately states "seven
checks", "three runtime modes". It is **no count of repository content that
nothing binds**. A count of repository content (routes, workers, files) is
either bound to the repository or removed. A count of a fixed property of the
document itself (sections, checks in a named rubric) is fine.

This mirrors the distinction the release truth drew this week: the published
Alembic head is bound because it is a stable, deliberately-published value; the
tip-dependent path counts are not published because they move.

### Design rules carried from the existing precedent

Follow `tests/architecture/test_published_migration_head_claim.py`:

1. **Match the claim on its meaning**, not one exact wording, because the
   document's prose is rewritten regularly.
2. **Assert exactly one claim was matched**, so a regex that silently matches
   nothing fails loudly instead of passing vacuously.
3. **Derive the truth from the repository**, never hardcode it.

## Required test

The validator gains a committed test exercising **both** a valid input and a
malformed input — the improvement the TS-002 reconciliation identified. A link
with an absolute path must be rejected; a repository-relative link must be
accepted. A validator that only ever passes is not evidence.

## Command Checklist

0. **Precondition — the audit document is present in the base.**
   ```bash
   git ls-files --error-unmatch docs/consulting/Codexify_Codebase_Capability_Audit.md
   ```
   If it fails, **STOP** — the execution base is wrong.

   Do not add that path to this task's commit. It belongs to the base.
1. Preflight — tree must be clean:
   ```bash
   git status --porcelain -uall
   ```
   If non-empty: `echo 'STOP: dirty tree'; exit 1`
2. Capture the pre-change evidence — the defects, before the fix:
   ```bash
   grep -cE '\]\(/Volumes/' docs/consulting/Codexify_Codebase_Capability_Audit.md
   grep -cE 'requirements\.txt' docs/consulting/Codexify_Codebase_Capability_Audit.md
   grep -cE '[0-9]+ (route|worker) modules' docs/consulting/Codexify_Codebase_Capability_Audit.md
   ```
   The first must print `144`, the second non-zero, the third `1` — both module
   counts appear on the same table row, so the line count is one, not two. If
   the first prints `0`, STOP and report: the base has moved.
3. Apply E-1 … E-4 to `docs/consulting/Codexify_Codebase_Capability_Audit.md`.
4. Apply the validator and the required test to
   `tests/architecture/test_capability_audit_claims.py`.
5. Scope guard — only the two allowed paths may be modified:
   ```bash
   for f in $(git diff --name-only; git ls-files --others --exclude-standard); do
     case "$f" in
       docs/consulting/Codexify_Codebase_Capability_Audit.md|tests/architecture/test_capability_audit_claims.py) ;;
       *) echo "STOP: out-of-scope file $f"; exit 1 ;;
     esac
   done
   ```
6. Validate the validator passes:
   ```bash
   python -m pytest -q tests/architecture/test_capability_audit_claims.py
   ```
7. **Mutation check — the defect classes must be detected.** Preserve the
   corrected bytes with an `EXIT` trap.
   ```bash
   corrected="$(mktemp -t ts004_audit.XXXXXX)"
   cp docs/consulting/Codexify_Codebase_Capability_Audit.md "$corrected"
   restore_corrected() { cp "$corrected" docs/consulting/Codexify_Codebase_Capability_Audit.md; }
   trap restore_corrected EXIT

   # Defect A: an absolute machine path reintroduced.
   printf '\n- [example](/Volumes/Dev_SSD/Codexify-main/README.md)\n' >> docs/consulting/Codexify_Codebase_Capability_Audit.md
   mut_output="$(python -m pytest -q tests/architecture/test_capability_audit_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: absolute-path mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   restore_corrected

   # Defect B: a link to a path that does not exist.
   printf '\n- [missing](./does_not_exist_under_this_path.md)\n' >> docs/consulting/Codexify_Codebase_Capability_Audit.md
   mut_output="$(python -m pytest -q tests/architecture/test_capability_audit_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: broken-link mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -q 'does_not_exist_under_this_path'; then
     echo "STOP: the broken-link failure did not name the offending path"
     exit 1
   fi
   restore_corrected

   # Defect C: an unbound countable claim about repository content.
   printf '\n- 999 route modules are present in this repository.\n' >> docs/consulting/Codexify_Codebase_Capability_Audit.md
   mut_output="$(python -m pytest -q tests/architecture/test_capability_audit_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: countable-claim mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   restore_corrected

   python -m pytest -q tests/architecture/test_capability_audit_claims.py || {
     echo "STOP: the validator did not pass after restoring the corrected document"
     exit 1
   }

   trap - EXIT
   rm -f "$corrected" || true
   ```
   The `trap restore_corrected EXIT` is required. Note that `rm` of a temp file
   may be refused by the host's deletion policy — that is expected, report the
   residue, and do not bypass the policy.

   The restoration must be verified independently:
   ```bash
   cmp -s docs/consulting/Codexify_Codebase_Capability_Audit.md "$corrected" && echo "byte-identical"
   grep -cE '\]\(/Volumes/' docs/consulting/Codexify_Codebase_Capability_Audit.md   # must be 0
   ```
8. Validate the earlier validators still pass:
   ```bash
   python -m pytest -q tests/architecture/test_readme_claims.py
   python -m pytest -q tests/architecture/test_repo_structure_claims.py
   python -m pytest -q tests/architecture/test_kb_index_claims.py
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
    git add docs/consulting/Codexify_Codebase_Capability_Audit.md tests/architecture/test_capability_audit_claims.py
    git commit -m "docs(consulting): bind the capability audit's claims to the repository

    The audit is a client-facing deliverable that states module counts and
    links into the codebase. Its counts were stale, 144 of its links carried
    one developer's absolute path, one linked a file that does not exist, and
    the document carried no date.

    The counts are replaced by the facts they stand for, every link is
    repository-relative and resolves, and the document states its as-of date.

    Adds tests/architecture/test_capability_audit_claims.py, which rejects
    absolute machine paths, requires every relative link to resolve with exact
    case, and rejects unbound counts of repository content.

    Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
    Task: 004 (D-04)"
    ```

## Expected Outputs

- The audit contains no absolute filesystem path in any link.
- Every relative link in the audit resolves to a tracked file or directory, with
  exact case.
- The audit states no unbound count of repository content.
- The audit states an as-of date.
- `tests/architecture/test_capability_audit_claims.py` exists, passes, and has
  been shown to **fail with exit code 1** against an absolute path, a broken
  link, and an unbound countable claim.
- A committed test exercises a valid input and a malformed input.
- The earlier validators still pass.
- One commit containing exactly the two allowed files.

## Qualification-Surface Impact

**None.** The qualification surface for `supported-compose-stock` is
`.dockerignore`, `docker-compose*.yml`, `config/**`, `backend/**`, `guardian/**`,
`frontend/**`, `plugins/**`, `codex_runner/**`, `package.json`, `pnpm-lock.yaml`,
`pnpm-workspace.yaml`. Neither allowed path appears in it.

## Rollback / Cleanup

```bash
git restore --staged docs/consulting/Codexify_Codebase_Capability_Audit.md tests/architecture/test_capability_audit_claims.py 2>/dev/null || true
git restore docs/consulting/Codexify_Codebase_Capability_Audit.md 2>/dev/null || true
rm -f tests/architecture/test_capability_audit_claims.py
rm -f /tmp/ts004_audit.* 2>/dev/null || true
```

`git restore` restores the **committed** file, not the corrected one — use it
only to abandon the task, not to undo the mutation probe. Note that on this host
`git restore` cannot replace a file whose inode must be unlinked; write the
committed content in place instead (`git show HEAD:<path> > <path>`). If the
host's deletion policy refuses the temp file, report the residue rather than
bypassing it.

## Dependencies / Prereqs

- `command -v git >/dev/null`
- `command -v python3 >/dev/null`
- `python3 -m pytest --version` succeeds (the repository's virtualenv is at
  `/Volumes/Dev_SSD/Codexify-main/.venv`; use its `bin/python` if the system
  interpreter lacks `pytest`)
- Network access is **not** required

## Closeout Summary

Report, in this order:

1. The commit SHA produced.
2. The pre-change evidence from step 2, and the post-change counts.
3. Step 7's observed mutation output for each defect class, with the captured
   exit codes.
4. Step 8's validator results and step 9's suite result, stated in the exact
   form given in step 9.
5. Confirmation that the scope guard listed only the two allowed files.
6. Explicit statement that no runtime or CI behaviour was changed and no startup
   was proven.
