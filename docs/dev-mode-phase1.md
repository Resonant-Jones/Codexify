# Codexify – Dev Mode Phase 1

## Overview

We are adding a **Dev Mode** to Codexify threads so that some threads become "Dev Threads".

In a Dev Thread:

- The thread is bound to a local project path on disk.
- Guardian (the dev persona) can use tools to:
  - Run terminal commands in that project directory.
  - Inspect git status and diff.
  - Show a simple project file tree.
- We also introduce **sessions** with **end-of-session summaries** that are stored in Postgres and appended to the thread.

This should all appear as a **normal Codexify view**. The coding bits are just extra panels and tools that show up when Dev Mode is ON.

---

## Goals (Phase 1)

- Add a `mode` field to threads: `'normal' | 'dev'`.
- Add an optional `project_path` on threads when `mode = 'dev'`.
- Implement **sessions** and **session summaries**:
  - Track sessions per thread.
  - On "End Session", summarize the session via LLM.
  - Store summaries in Postgres and append them to the thread as a message.
- Implement backend tools:
  - `terminal_run(projectPath, command)` – run shell commands in the project directory.
  - `git_status_and_diff(projectPath)` – return branch, changed files, and unified diff.
- Add a **Dev Thread view**:
  - Center: existing chat UI (unchanged).
  - Left: read-only project file tree (based on `project_path`).
  - Bottom tray: buttons for "Run Command" and "Show Diff".
- (Optional for Phase 1) Read-only file view + basic Monaco editor drawer.

Non-goals for Phase 1:

- No prompt library UI yet.
- No advanced git history viewer (just status + diff).
- No full-blown Guardian ethics/IDDB graph integration; just use existing persona system.

---

## Data Model Changes (High Level)

### threads

Add:

- `mode` – `'normal' | 'dev'` (default `'normal'`)
- `project_path` – `text | null`

### sessions

New table:

- `id`
- `thread_id` (FK to threads)
- `started_at`
- `ended_at` (nullable until closed)

### session_summaries

New table:

- `id`
- `session_id` (FK to sessions)
- `summary_text` – narrative summary for humans
- `decisions_text` – key decisions taken in this session
- `todos_text` – next steps
- `created_at`

We will also insert a summary message into `messages` at the end of each session.

---

## Backend Tools (High Level)

### 1. `terminal_run`

- Input:
  - `projectPath: string`
  - `command: string`
- Behavior:
  - Run the command in `projectPath`.
  - Capture stdout, stderr, and exit code.
- Output:
  - `{ stdout: string, stderr: string, exitCode: number }`

### 2. `git_status_and_diff`

- Input:
  - `projectPath: string`
- Behavior:
  - Call:
    - `git status --short --branch`
    - `git diff`
  - Parse branch name and list of changed files (if feasible).
- Output:
  - `{ branch: string, changedFiles: string[], diff: string }`

These tools will be wired as callable tools for Guardian in Dev Mode threads only.

---

## UI/UX: Dev Thread View (Phase 1)

### Thread Header

- Show a toggle:
  - `Code Mode: [ OFF | ON ]`
- When switching ON from OFF:
  - Prompt the user to select or enter a `project_path`.
  - Save `mode = 'dev'` and `project_path`.

### Layout

- Center: existing Codexify chat UI (unchanged).
- Left panel: **Project File Tree**
  - Read-only.
  - Source: recursive directory listing under `project_path` with ignore rules (`.git`, `node_modules`, etc.).
- Bottom tray (visible only in Dev Mode):
  - Button: **Run Command**
    - Opens input for a shell command.
    - Calls `terminal_run`.
    - Displays result in the thread as a message (or dedicated output panel).
  - Button: **Show Diff**
    - Calls `git_status_and_diff`.
    - Displays branch, changed files, and diff in a panel (and/or as a thread message).

### Sessions

- When user sends the first message after a gap or on thread open:
  - If there is no active session: create a new session for this thread.
- Add "End Session" button in Dev Mode.
- On "End Session":
  - Collect messages for that session.
  - Call LLM to summarize the session:
    - `summary_text`
    - `decisions_text`
    - `todos_text`
  - Store in `session_summaries`.
  - Append a summary message to the thread.

Right sidebar (Phase 1):

- Show the latest session summary for this thread in Dev Mode.

---

## Implementation Order (Suggested)

1. Add `mode` and `project_path` to threads (backend + UI toggle).
2. Add `sessions` and `session_summaries` and "End Session" behavior.
3. Implement `terminal_run` and wire it as a tool for Guardian in Dev Mode.
4. Implement `git_status_and_diff` and basic diff display.
5. Add read-only project file tree panel.
6. (Optional) Add file viewer + Monaco drawer.

This is Phase 1 only; prompt library and richer git tools will come later.
