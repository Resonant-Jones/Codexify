# Runner Protocol — Sequential Atomic Tasks

## Purpose
This protocol is a strict execution harness for Codexify campaigns.

It enforces:
- **one task = one change set** (atomic scope)
- **commit mode is explicit per task**: one-commit or two-phase
- **strict file scope** per task
- **tests before commit**
- **prompt + summary artifacts** recorded in `docs/tasks/`

## Inputs
A campaign file containing an ordered task list. For each TASK, the campaign should provide enough information to execute safely.

Minimum required fields per task (preferred):
- TASK-ID + title
- Goal / objective (1–3 sentences)
- Allowed (primary) file list (the only files the runner may modify for this task)
- Test loop command(s) (must be copy/paste runnable)
- Commit mode (one-commit | two-phase)
- Commit message template(s) (must include TASK-ID)

Task artifact path rules:
- The runner MUST use an underscore-named task artifact under `docs/tasks/`:
  - `docs/tasks/TASK_YYYY_MM_DD_NNN_<lowercase_slug>.md`
- The campaign MAY include the task artifact path explicitly.
- If the campaign does NOT include the task artifact path, the runner MUST derive it from the TASK-ID + a lowercase slug.

## Global Invariants
0. **Campaign → Task prompt generation is mandatory**
   - The runner MUST NOT block simply because a task prompt file does not exist yet.
   - If the task artifact file is missing, the runner MUST create it during the task (see Per-Task Execution Loop).
   - The task artifact must include a “Task Prompt” section that is sourced from the campaign entry.
   - If the campaign entry is missing required constraints (e.g., Allowed Files, Checks to Run, or Commit Mode), the runner MUST STOP and emit a **Blocker Prompt** (see “Blocker Prompt Template”) that reports exactly what is missing.
   - The runner MUST NOT ask the user to “create the task prompt file” as a prerequisite. The runner either (a) derives the task prompt from the campaign entry, or (b) stops with a Blocker Prompt when the campaign entry is insufficient.

1. **No scope creep**
   - Only edit files explicitly allowed by the current task.
   - If a change requires an additional file, stop and report.

2. **No batching**
   - Do not carry changes across tasks.
   - Do not “improve” nearby code unless the task explicitly requires it.

3. **Tests are mandatory**
   - Run the task’s test loop before committing.
   - If tests fail, fix within allowed files only.

4. **Artifacts are mandatory**
   - Every task produces/updates its `docs/tasks/...` file with:
     - Task Prompt
     - Summary (what changed, tests, git status, commit hash)

5. **Commit mode is explicit**
   - Each task must declare its commit mode:
     - **one-commit**: implementation + artifact summary are committed together.
     - **two-phase**: commit #1 is the implementation; commit #2 is a docs-only commit that finalizes the task artifact.
   - In **two-phase** mode:
     - The task artifact **must** record the **implementation commit hash**.
     - The task artifact **may** omit the finalize-artifact hash (because a commit cannot embed its own hash without becoming self-referential).
     - The runner **must** report both hashes in the campaign completion mapping as: `TASK-ID -> [impl_hash, finalize_hash]`.

6. **Commit messages include TASK-ID**
   - Every commit created by the runner must include the current task’s TASK-ID.
   - Recommended formats:
     - `<TASK-ID>: <short message>`
     - `docs(task): finalize <TASK-ID> summary`

7. **Clean tree between tasks**
   - `git status --porcelain` must be empty before moving to the next task.

8. **Canonical file naming (prevents scope + path ambiguity)**
   - **Task artifacts** MUST use underscores and a lowercase slug:
     - Directory: `docs/tasks/`
     - Filename pattern: `TASK_YYYY_MM_DD_NNN_<lowercase_slug>.md`
     - Example: `docs/tasks/TASK_2026_01_20_001_chat_endpoint_canonicalization.md`
   - **Campaign files** SHOULD be visually distinct and consistent:
     - Directory: `docs/Campaign/` (note case: capital C in `Campaign`)
     - Filename pattern: `CAMPAIGN_YYYY_MM_DD.md` (uppercase prefix)
     - Example: `docs/Campaign/CAMPAIGN_2026_01_20.md`
     - All campaign/task paths and filenames are **case-sensitive** on Linux containers; treat them as case-sensitive everywhere.
   - **Disallowed / non-canonical**: dash-separated task filenames like `TASK-2026-01-20-001_...md`.
   - **Preflight enforcement**:
     - If the campaign references a non-canonical task filename/path, the runner MUST prefer the canonical underscore-named path.
       - If a safe canonical mapping is possible (same TASK-ID, slug can be derived), the runner should proceed using the canonical path and note the mapping in the task artifact.
       - If a safe mapping is NOT possible, STOP and report the mismatch.
     - Do **not** auto-rename during an in-progress task (it can violate that task’s allowed-file list).
     - The correct fix is a **docs-only** rename using `git mv` performed **before** starting the campaign (or as a separate docs task), e.g. renaming to the underscore pattern.

9. Shell command hygiene (prevents copy/paste breakage)
   - In all command snippets, use plain ASCII hyphens `-` for flags (e.g., `git status --porcelain`).
   - Do not use typographic/en-dash characters like `–` in flags; they will break in shells.

## Blocker Prompt Template (Source of Truth)

When any STOP condition triggers, the runner MUST output a single structured Blocker Prompt and then stop without editing files.

Copy/paste template:

```text
<BLOCKER_PROMPT>
RUN-ID: <run-id-or-unknown>
CAMPAIGN-ID: <campaign-id>
TASK-ID: <task-id>
TASK-ARTIFACT: <docs/tasks/TASK_YYYY_MM_DD_NNN_slug.md>
BRANCH: <git-branch>
REPO-ROOT: <git-rev-parse--show-toplevel>
SEVERITY: <stop|warning>

STOP-REASON:
- <one sentence>

MISSING / CONFLICTING INPUTS:
- <bullet list of the exact fields/files/commands that are missing or conflicting>

EVIDENCE:
- Command(s) run:
  - <command>
- Key output excerpt(s):
  - <trimmed excerpt>

ALLOWED OPTIONS:
A) <option A phrased as an explicit instruction the user can choose>
B) <option B>

RECOMMENDED:
- <one recommended option and why>

WHAT I WILL DO NEXT (once resolved):
- <1–3 bullet steps>
</BLOCKER_PROMPT>
```

Notes:
- The Blocker Prompt must be actionable: list *exactly* what the user must supply or change.
- If the blocker is a file-scope mismatch, include the exact path(s) that must be added to Allowed Files.
- If the blocker is a dirty tree, include `git status --porcelain` output.

## Per-Task Execution Loop
For each task in the campaign (in order):

### 0) Announce + lock scope
Print:
- Task ID + title
- Allowed file list
- Task artifact path
- Test command(s)
- Commit message (must include TASK-ID)
- Commit mode (one-commit | two-phase)
- If stopping, emit a Blocker Prompt (see “Blocker Prompt Template”).

### 1) Preflight check
Run:
```bash
git status --porcelain
```
If anything is dirty, stop and report.
Note: Use ASCII hyphens in commands; `git status –porcelain` (en-dash) is invalid.

### 1.5) Ensure task artifact exists (create if missing)

After confirming a clean tree, ensure the task artifact file exists.

- If the task artifact file does not exist, create it as a new file at the canonical underscore path.
- Creating the task artifact file is considered in-scope for the current task.
- Do not run tests or make implementation changes until the task artifact file exists.
- The file must contain (at minimum) the following headings:

  - `# <TASK-ID>: <title>`
  - `## Task Prompt`
  - `## Allowed Files`
  - `## Checks to Run`
  - `## Commit Mode`
  - `## Commit Messages`
  - `## Summary` (may be left as “TBD” until finalize)

If the campaign does not specify Allowed Files, Checks to Run, or Commit Mode, STOP and emit a Blocker Prompt (see “Blocker Prompt Template”) reporting exactly what is missing.

### 2) Implement minimal change
Edit only the allowed files.

### 3) Scope enforcement check
Run:
```bash
git status --porcelain
```
If any modified/untracked file is **not** in the allowed file list **or** the task artifact path:
- Revert/remove it immediately, or
- Stop and report if reverting would lose required work.

### 4) Run tests
Run the task’s test loop exactly as specified.
- If tests fail: fix within allowed files and re-run until passing.
- If passing requires touching a non-allowed file: stop and report.

### 5) Write task artifact
Update the task file under `docs/tasks/…` with two sections:

#### Task Prompt
Include the full Codexify Task Template prompt for this task:
- Context
- Instructions
- Task Description
- Expected Output

#### Summary
Include:
- Changed files + key functions/components
- Test command(s) + pass/fail summary
- `git status --porcelain` confirmation (no out-of-scope files)
- Commit mode (one-commit | two-phase)
- Implementation commit hash
- Finalize-artifact commit hash (two-phase only; may be recorded as “reported in campaign mapping” if not embedded in-file)
- Campaign mapping output requirement: in two-phase mode, output `TASK-ID -> [impl_hash, finalize_hash]`

### 6) Stage + commit
Stage **only**:
- allowed files for this task
- the task artifact file

Then commit according to the task’s declared commit mode.

#### Commit mode: one-commit
- Commit once using the campaign’s commit message template.
- The commit message must include the TASK-ID (e.g., `<TASK-ID>: <message>`).

#### Commit mode: two-phase
1) **Implementation commit**
   - Stage **only** the implementation changes (allowed code/config files). Do **not** include the task artifact yet unless the task explicitly requires it.
   - Commit using the campaign’s commit message template, including the TASK-ID (e.g., `<TASK-ID>: <message>`).
   - Capture the implementation commit hash.

2) **Finalize-artifact commit**
   - Update **only** the task artifact Summary to include:
     - commit mode = two-phase
     - implementation commit hash
     - commands, tests, and git status confirmation
     - finalize-artifact commit hash: `reported in campaign mapping` (optional to embed)
   - Stage **only** the task artifact.
   - Commit with a docs-only message that includes the TASK-ID, e.g.:
     - `docs(task): finalize <TASK-ID> summary`

### 7) Post-commit clean check
Run:
```bash
git status --porcelain
```
Must be empty before proceeding.

## Campaign Completion Output
After the final task:
- Print a list mapping `TASK-ID -> commit-hash`.
  - If a task used **two-phase** mode, record both hashes as: `TASK-ID -> [impl_hash, finalize_hash]`.
- If any task commit message is missing the TASK-ID, treat it as a protocol violation and stop in the next audit.

## Stop Conditions
Stop immediately and report if:
- A task requires editing files outside its allowed list.
- Tests cannot pass without violating scope.
- The working tree becomes unexpectedly dirty.
- A campaign references a task artifact path/name that cannot be safely mapped to the canonical underscore format.
- Any campaign/task filename/path mismatch due to dash-vs-underscore naming or directory case (e.g., `docs/campaign` vs `docs/Campaign`).
- A STOP condition is hit and the runner fails to emit a Blocker Prompt using the “Blocker Prompt Template” above.

## Defaults (only when campaign explicitly allows)
The runner may apply defaults ONLY if the active campaign explicitly authorizes defaults.

Suggested safe defaults:
- Commit mode: two-phase
- Commit message templates:
  - Implementation: `<TASK-ID>: <short message>`
  - Finalize: `docs(task): finalize <TASK-ID> summary`

Defaults must NEVER be applied to “Allowed Files” or “Checks to Run”. Those must be specified by the campaign/task.

## Notes
- This protocol is intentionally strict. It is designed to prevent "Franken-commits" and preserve auditability.
- Two-phase mode avoids self-referential hashes by recording the implementation hash in-file and reporting the finalize hash in the campaign completion mapping.


---

In `docs/Campaign/CAMPAIGN_2026_01_20.md`, in the section `## CAMPAIGN_2026_01_20_004_MVP_LOOP_CLOSURE_DOCUMENT_GENERATION` under `### TASK-2026-01-20-013_DOCUMENT_GEN_MODAL_UI`, update the `Files allowed to edit (only)` list by removing the non-existent sidebar file and adding the correct one:

- Delete the bullet line `- frontend/src/components/Sidebar.tsx` if present.
- Ensure there is a bullet line `- frontend/src/components/SidebarRoot.tsx` in the allowed files list.
- Leave the `- frontend/src/components/AppShell.tsx` line unchanged.