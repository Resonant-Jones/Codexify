# WBC Backend Git-LFS Isolation Proof — 2026-08-22

## Scope and authority

- **Workflow lane:** architecture-impact
- **Task kind:** qualification-environment isolation + proof
- **Source WBC branch:** `codex/wbc-c1-canonical-dlg-refresh-rebaseline`
- **Source WBC tip:** `9720202dd1fc614b6362082eacefaaa29b4fb4e2`
- **Canonical main:** `c90d3ca3ac3e5d4e70563fbc96e31a06e8cabb36`

This proof qualifies one test-environment boundary only. It does not change
runtime, queue, Guardian Evidence, release-support, DLG, or acceptance
semantics.

## Original failure classification

The original linked-worktree Backend Tests run stopped in
`tests/browser_host_harness/test_electron_candidate.py::test_electron_candidate_does_not_change_root_dependency_paths`.
That test executes:

```text
git diff --quiet HEAD -- package.json pnpm-lock.yaml pnpm-workspace.yaml
```

`git check-attr filter -- package.json` reported `package.json: filter: lfs`.
The repository-wide `.gitattributes` rule is:

```text
*.json filter=lfs diff=lfs merge=lfs -text
```

The source linked worktree's Git directory was
`/Volumes/Dev_SSD/Codexify-main/.git/worktrees/worktree3`, with common Git
directory `/Volumes/Dev_SSD/Codexify-main/.git`. The original test's `git diff`
therefore invoked the LFS clean filter for root `package.json` through shared
metadata and stopped with `Error cleaning Git LFS object` under
`/Volumes/Dev_SSD/Codexify-main/.git/lfs/tmp/3155903044` and `Operation not
permitted`.

**Original Browser Host failure classified as shared-worktree Git-LFS
infrastructure: yes.** It was not an assertion that root dependency paths had
changed, and it was not a Codexify runtime failure.

## Standalone checkout and LFS ownership

The isolated clone was created without a linked worktree at:

```text
/private/tmp/codexify-wbc-backend-lfs-isolated/repo
```

It contains detached commit `9720202dd1fc614b6362082eacefaaa29b4fb4e2` and a
real private Git directory:

```text
/private/tmp/codexify-wbc-backend-lfs-isolated/repo/.git
```

`git lfs install --local` was used only inside that clone. After a
`GIT_LFS_SKIP_SMUDGE=1` checkout, `git lfs pull` hydrated LFS content normally.
`python3 -m json.tool package.json >/dev/null` passed, proving the root package
file was materialized rather than left as an LFS pointer. The tracked checkout
was clean before the task-local virtual environment was created.

`git lfs env` recorded these private local paths:

```text
LocalWorkingDir=/private/tmp/codexify-wbc-backend-lfs-isolated/repo
LocalGitDir=/private/tmp/codexify-wbc-backend-lfs-isolated/repo/.git
LocalGitStorageDir=/private/tmp/codexify-wbc-backend-lfs-isolated/repo/.git
LocalMediaDir=/private/tmp/codexify-wbc-backend-lfs-isolated/repo/.git/lfs/objects
TempDir=/private/tmp/codexify-wbc-backend-lfs-isolated/repo/.git/lfs/tmp
```

No source-checkout Git/LFS configuration or permissions were changed. The LFS
endpoint remained a read-only local file endpoint for the source repository,
but all isolated checkout Git/LFS storage and temporary paths above were private
to the task directory.

## Electron boundary proof

In the standalone clone:

- `git diff --quiet HEAD -- package.json pnpm-lock.yaml pnpm-workspace.yaml`
  exited `0`.
- `pytest -v tests/browser_host_harness/test_electron_candidate.py::test_electron_candidate_does_not_change_root_dependency_paths`
  passed: `1 passed`.
- `pytest -v tests/browser_host_harness/test_electron_candidate.py` passed:
  `4 passed`.

The earlier shared Git-LFS permission failure did not recur.

## Backend Tests evidence

A fresh task-local virtual environment in the isolated clone used Python
`3.11.14`. It installed `backend/requirements-ci.txt` and the repository as an
editable package. The exact Backend Tests command ran with the required dummy
settings:

```text
GUARDIAN_ALLOW_DUMMY_SETTINGS=1 GENAI_API_KEY=dummy NOTION_API_KEY=dummy ANTHROPIC_API_KEY=dummy OPENAI_API_KEY=dummy GEMINI_API_KEY=dummy GOOGLE_API_KEY=dummy GROQ_API_KEY=dummy LLM_PROVIDER=groq PYTHONUNBUFFERED=1 .venv/bin/python -m pytest -q --maxfail=1 --disable-warnings tests -m "not integration" -k "not cli"
```

The suite advanced past the former Electron/LFS stop and reached approximately
48%. Its first deterministic failure was:

```text
tests/evidence_packets/test_guardian_evidence_packet_generator_contract.py::test_cross_links_and_existing_tools_remain_green
```

Expected behavior: `docs/architecture/00-current-state.md` contains the literal
`Guardian Evidence Packet generator contract` phrase required by the existing
cross-link assertion.

Observed behavior: the assertion failed because that literal is absent from the
current-state document. No LFS permission failure recurred. This is a static
documentation/test-contract mismatch, not evidence of changed runtime behavior.

**Classification:** `LFS_ISOLATED_BACKEND_BLOCKED`.

The suite stopped before the known Make-target parser test, so this proof does
not claim that the full isolated Backend Tests gate reached it. The focused
parser diagnosis remains unchanged and was not repaired here.

## Non-promotion statement

- Release posture changed: no.
- Runtime semantics changed: no.
- Makefile behavior defect proven: no.
- Make-target extraction defect proven: yes, from the prior focused proof; no
  change was made in this task.

This artifact records test-environment and static-regression evidence only. It
does not establish live-service proof, supported-runtime expansion, or a green
Backend Tests gate.
