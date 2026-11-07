# Task Receipt

- Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
- Task ID: 003
- Title: Bind the KB index to release truth — its links and its surface statuses
- Finding: D-03 (KB index reconciled with release truth)
- Risk: LOW
- Base commit: `origin/main` at authoring time — see step 0
- Depends on: TS-001 and TS-002 (both merged). TS-003 touches `docs/architecture/README.md`, which no earlier task edits.
- Blocks: TS-004 (D-04, claim-binding extension)

## Scope note: this task was re-scoped against the current base

D-03 was written against the audit base, where `docs/architecture/README.md:62,64,211`
carried three `supported-compose-stock` "does not yet exist" claims that were false
against `00-current-state.md` and against existing files.

**Those claims no longer exist.** The release lane rewrote the KB index since the
audit, and the stale prose is gone — verified against the current base:

- no occurrence of "does not yet exist" anywhere in the KB index;
- the KB index now states `supported-compose` and `supported-compose-stock` as
  `PASS` with `freshness: stale`, matching the registry exactly;
- it correctly avoids repeating the registry's tip-dependent path counts, which
  is the pattern PR #1028 established for `00-current-state.md`.

The **correction** half of D-03 was therefore delivered by the release lane, not by
this campaign. The **protection** half was not delivered by anyone, and the
campaign's whole point is the prevention mechanism. This task builds that
protection, and the protection immediately finds real defects that are still live.

## Allowed Files

- `docs/architecture/README.md`
- `tests/architecture/test_kb_index_claims.py` (new)

Any other modified path is a scope violation — the checklist step enforces this.

## Why this task exists

The KB index (`docs/architecture/README.md`) is the entry point to the
architecture knowledge base. It makes two kinds of checkable claim:

1. **Link claims.** 384 relative links point at other documents. A link that
   resolves on the author's filesystem but not in CI is a false claim.
2. **Status claims.** It states in prose what the qualification registry
   projects per surface.

Neither kind is enforced. There is no validator for the KB index anywhere in
`tests/architecture/`, and no script under `scripts/` that checks document
links. Writing the validator D-03 asked for surfaces three live defects.

### D-1 — a case-broken link that CI cannot resolve

`docs/architecture/README.md` links, in the "Paul Collaborator Study Lane"
entry:

```
../collaborators/paul/README.md
```

The tracked path is `docs/Collaborators/paul/README.md` — capital C. The link
resolves on macOS (case-insensitive filesystem) and **fails on Linux CI**,
where the runner is `ubuntu-latest`.

The root cause is a repository-level **case collision**: git tracks *both*
`docs/Collaborators/` (14 files, including `paul/`) and `docs/collaborators/`
(20 files, `zac/`). On a case-insensitive filesystem they merge on disk into one
directory of 34 files; on a case-sensitive filesystem they are two distinct
directories. The same defect appears in `docs/Collaborators/README.md:16`,
which links `./zac/README.md`.

### D-2 — two `## Doc Map` sections, with conflicting content

The KB index contains **two** sections titled `## Doc Map` (lines 57 and 206).
They are not duplicates — they share only 10 link targets; the first has 44
targets the second lacks, the second has 196 the first lacks. The first
(line 57) carries the qualification-status prose D-03 was about; the second
(line 206) is the exhaustive catalogue.

The duplicate was introduced by the weekly current-state override
(`0a595ec5c`, "docs: refresh weekly current-state override"), which added a
second `## Doc Map` above the existing one. That override has rewritten this
file repeatedly, and it is the same mechanism that dropped release-truth
obligations from `00-current-state.md` three times. No `#doc-map` anchor
anywhere in the repository depends on either heading, so renaming is safe.

### D-3 — the KB index states no release-gate posture

`00-current-state.md:23` states plainly: "The release gate remains `HOLD`". The
KB index **never mentions the release gate at all**. A reader arriving at the
KB index — the entry point to the knowledge base — sees per-surface `PASS`
verdicts and no statement that the release as a whole is `HOLD`. That is the
exact reading hazard `00-current-state.md:65` warns against: "Do not read one
qualified surface as a qualified release."

### D-4 — a registry surface is absent from the KB index

The registry projects four surfaces. The KB index names three of them. The
fourth, `release-readiness-gates`, is `HOLD` with the blocker "No qualification
run receipt exists for this surface" — and it appears nowhere in the KB index.
A reader cannot tell from the index whether that surface exists.

## Required edits

### E-1 — make the KB index's links resolve exactly

Every relative link in the KB index must resolve to a tracked path **with exact
case**. This is what CI checks out, so it is the only definition that means
anything.

### E-2 — one `## Doc Map`, not two

The KB index must have exactly one section titled `## Doc Map`. The two
current sections have different content and different audiences; merge their
link targets into one section rather than discarding either. The merged section
must retain every link target from both, so nothing is lost.

The section at line 206 is the exhaustive catalogue and is the natural home for
the merged result. The section at line 57 is the qualification-status section;
its prose content (not its links) belongs with the qualification receipts in the
merged map, and the release-gate statement required by E-4 belongs near it.

### E-3 — state the release gate

The KB index must state the release-gate posture explicitly, and that statement
must agree with `00-current-state.md`. The KB index's own
`How to answer "What is currently in Codexify Beta?"` section already designates
`00-current-state.md` as the first authority to read; the gate statement belongs
where a reader meets that pointer.

### E-4 — name every surface the registry projects

Every surface the registry projects must be named in the KB index, with a status
that agrees with the registry. A surface the index omits is a surface a reader
cannot see.

## New validator

Create `tests/architecture/test_kb_index_claims.py`. It must implement three
rules, each deriving truth from the repository rather than hardcoding it:

### Rule 1 — every link in the KB index resolves, with exact case

For each relative markdown link in the KB index, resolve it relative to the
KB index's directory and assert the resolved path is a tracked path, or a
directory containing tracked paths. **Case must match exactly** — this is the
rule that catches D-1, and a case-insensitive comparison would pass it.

External links (`http://`, `https://`, `mailto:`) and pure anchors (`#...`) are
out of scope. A link target may be a file or a directory.

### Rule 2 — the KB index states the release gate, and it agrees

The KB index must contain a release-gate statement, and it must agree with
`00-current-state.md`. Both documents are release-truth prose; derive the gate
posture from `00-current-state.md` and assert the KB index states the same one.

### Rule 3 — every registry surface is named, with an agreeing status

Read `docs/qualification/registry.json`. For each surface it projects, assert
the KB index names that surface, and assert the status the index states for it
agrees with the registry's `status` field.

The registry is generated and drift-gated; it is the machine-readable authority
for a surface's status. The KB index states the same thing in prose. When they
disagree, one of them is wrong, and this rule says which.

**No volatile counts.** Neither this task's prose nor the validator may introduce
a tip-dependent count — a file count, a path count, a directory count, a
percentage. The registry's own blocker strings carry the exact changed-path
counts and are tip-dependent; `00-current-state.md` deliberately does not repeat
them (PR #1028), and the KB index already follows the same rule. This task must
preserve that. A count in the KB index is a claim that rots on the next merge.

## Required test

The validator gains a committed test exercising **both** a valid input and a
malformed input — the improvement the TS-02 reconciliation identified, applied
here. Specifically: a link whose case does not match a tracked path must be
rejected, while a link that matches exactly must be accepted. A validator that
only ever passes is not evidence.

## Command Checklist

0. **Precondition — the KB index and the registry are present in the base.**
   ```bash
   git ls-files --error-unmatch docs/architecture/README.md
   git ls-files --error-unmatch docs/qualification/registry.json
   ```
   If either fails, **STOP** — the execution base is wrong.

   Do not add either path to this task's commit. They belong to the base.
1. Preflight — tree must be clean:
   ```bash
   git status --porcelain -uall
   ```
   If non-empty: `echo 'STOP: dirty tree'; exit 1`
2. Capture the pre-change evidence — the three defects, before the fix:
   ```bash
   grep -n 'collaborators/paul' docs/architecture/README.md
   grep -c '^## Doc Map$' docs/architecture/README.md
   grep -c 'release gate' docs/architecture/README.md
   ```
   The first must match; the second must print `2`; the third must print `0`.
   If the second prints `1` or the third prints non-zero, STOP and report: the
   base has moved.
3. Apply E-1 … E-4 to `docs/architecture/README.md`.
4. Apply the validator and the required test to
   `tests/architecture/test_kb_index_claims.py`.
5. Scope guard — only the two allowed paths may be modified:
   ```bash
   for f in $(git diff --name-only; git ls-files --others --exclude-standard); do
     case "$f" in
       docs/architecture/README.md|tests/architecture/test_kb_index_claims.py) ;;
       *) echo "STOP: out-of-scope file $f"; exit 1 ;;
     esac
   done
   ```
6. Validate the validator passes:
   ```bash
   python -m pytest -q tests/architecture/test_kb_index_claims.py
   ```
7. **Mutation check — the defect classes must be detected.** Preserve the
   corrected bytes with an `EXIT` trap.
   ```bash
   corrected="$(mktemp -t ts003_kb.XXXXXX)"
   cp docs/architecture/README.md "$corrected"
   restore_corrected() { cp "$corrected" docs/architecture/README.md; }
   trap restore_corrected EXIT

   # Defect A: a link whose case does not match a tracked path.
   # The corrected index links `../Collaborators/paul/README.md`; flipping the
   # capital C to a lower one reproduces the case-broken form CI cannot resolve.
   python - "$corrected" <<'PY'
   import sys
   path = "docs/architecture/README.md"
   text = open(path, encoding="utf-8").read()
   text = text.replace(
       "](../Collaborators/paul/README.md)",
       "](../collaborators/paul/README.md)",
   )
   open(path, "w", encoding="utf-8").write(text)
   PY
   mut_output="$(python -m pytest -q tests/architecture/test_kb_index_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: case-broken link mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -qi 'paul'; then
     echo "STOP: the case-broken link failure did not name the offending path"
     exit 1
   fi
   restore_corrected

   # Defect B: a second '## Doc Map' heading.
   printf '\n## Doc Map\n\n- [Duplicate](./00-current-state.md)\n' >> docs/architecture/README.md
   mut_output="$(python -m pytest -q tests/architecture/test_kb_index_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: duplicate-heading mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   restore_corrected

   # Defect C: the release-gate statement removed.
   grep -v -i 'release gate' "$corrected" > docs/architecture/README.md
   mut_output="$(python -m pytest -q tests/architecture/test_kb_index_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: missing-release-gate mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   restore_corrected

   # Defect D: a registry surface dropped from the KB index.
   grep -v 'release-readiness-gates' "$corrected" > docs/architecture/README.md
   mut_output="$(python -m pytest -q tests/architecture/test_kb_index_claims.py 2>&1)" || mut_code=$?
   mut_code="${mut_code:-0}"
   printf '%s\n' "$mut_output"
   if [ "$mut_code" -ne 1 ]; then
     echo "STOP: missing-surface mutation did not fail as an assertion (exit=$mut_code)"
     exit 1
   fi
   if ! printf '%s' "$mut_output" | grep -q 'release-readiness-gates'; then
     echo "STOP: the missing-surface failure did not name the surface"
     exit 1
   fi
   restore_corrected

   python -m pytest -q tests/architecture/test_kb_index_claims.py || {
     echo "STOP: validator did not pass after restoring the corrected KB index"
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
   cmp -s docs/architecture/README.md "$corrected" && echo "byte-identical"
   grep -c '^## Doc Map$' docs/architecture/README.md   # must be 1
   ```
8. Validate TS-001's and TS-002's validators still pass:
   ```bash
   python -m pytest -q tests/architecture/test_readme_claims.py
   python -m pytest -q tests/architecture/test_repo_structure_claims.py
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
    git add docs/architecture/README.md tests/architecture/test_kb_index_claims.py
    git commit -m "docs(architecture): bind the KB index to release truth

    The KB index's links and its qualification-surface statuses are checkable
    claims that nothing enforced. This corrects the three that are wrong today
    and installs the validator that would have caught them.

    Fixes a link that resolves on macOS but not on Linux CI, merges two
    conflicting '## Doc Map' sections into one, states the release gate, and
    names the registry surface the index omitted.

    Adds tests/architecture/test_kb_index_claims.py, which resolves every
    relative link in the index with exact case, asserts the index states the
    release gate and that it agrees with 00-current-state.md, and asserts
    every registry surface is named with an agreeing status.

    Campaign: CAMPAIGN_2026_11_06_CRAFTSHIP_REMEDIATION
    Task: 003 (D-03)"
    ```

## Expected Outputs

- Every relative link in the KB index resolves to a tracked path with exact case.
- The KB index contains exactly one `## Doc Map` section, retaining every link
  target both current sections carried.
- The KB index states the release-gate posture, and it agrees with
  `00-current-state.md`.
- Every surface the registry projects is named in the KB index with a status
  that agrees with the registry.
- No volatile count appears anywhere in the edited section.
- `tests/architecture/test_kb_index_claims.py` exists, passes, and has been
  shown to **fail with exit code 1** against a case-broken link, a duplicate
  `## Doc Map` heading, a missing release-gate statement, and an omitted
  registry surface.
- A committed test exercises a valid input and a malformed input.
- TS-001's and TS-002's validators still pass.
- One commit containing exactly the two allowed files.

## Qualification-Surface Impact

**None.** The qualification surface for `supported-compose-stock` is
`.dockerignore`, `docker-compose*.yml`, `config/**`, `backend/**`, `guardian/**`,
`frontend/**`, `plugins/**`, `codex_runner/**`, `package.json`, `pnpm-lock.yaml`,
`pnpm-workspace.yaml`. Neither allowed path appears in it.

## Rollback / Cleanup

```bash
git restore --staged docs/architecture/README.md tests/architecture/test_kb_index_claims.py 2>/dev/null || true
git restore docs/architecture/README.md 2>/dev/null || true
rm -f tests/architecture/test_kb_index_claims.py
rm -f /tmp/ts003_kb.* 2>/dev/null || true
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

## Closeout Summary

Report, in this order:

1. The commit SHA produced.
2. The pre-change evidence from step 2, and the post-change counts.
3. Step 7's observed mutation output for each defect class, with the captured
   exit codes.
4. Step 8's validator results and step 9's suite result, stated in the exact
   form given in step 9.
5. Confirmation that the scope guard listed only the two allowed files.
6. Confirmation that no volatile count was introduced.
7. Explicit statement that no runtime or CI behaviour was changed and no startup
   was proven.
8. The repository-level case collision (`docs/Collaborators/` vs
   `docs/collaborators/`) — **reported, not fixed**, because it is a separate
   decision about repository layout, not a documentation correction.
