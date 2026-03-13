Codexify Task: Remove SQLite CLI surfaces + route CLI to Postgres-backed Guardian API

TASK ID: TASK-2026-01-27-CLI-POSTGRES-001
Title: Switch guardian_main.py CLI from SQLite modules to Guardian API (Postgres) + neutralize legacy commands
Priority: High
Owner: Codex
Area: guardian/guardian_main.py
Goal: You (Codex) will modify the CLI so it no longer initializes/depends on SQLite tables for projects/threads, and instead uses the already-existing Guardian HTTP API (/api/chat/* and /api/projects if available). Keep command names stable to avoid breaking scripts.

⸻

Context / Problem
 • The CLI currently has multiple commands that call SQLite-backed modules:
 • create_project, list_projects → projects_module.*
 • init_db → uses sqlite3 + GuardianDB(DB_PATH) + creates chat_threads/chat_messages
 • thread commands → threads_module.*
 • conversation commands → conversations_module.*
 • I don’t use SQLite and want to ship a Postgres-first CLI.
 • There is already a working CLI surface at the bottom of the file (chat, chat:create-thread) that uses the Guardian API and requires an API key.
 • I want to:
 1. Stop creating/using SQLite tables from CLI.
 2. Make project + thread CLI commands call the Guardian API instead.
 3. Mark conversation CLI commands as legacy (no-op message), but don’t delete them.

⸻

Allowed Files
 • guardian/guardian_main.py

(Do not edit other files in this task.)

⸻

Requirements

1) Update create_project to use Guardian API (Postgres-backed)

Replace the current SQLite/module implementation:

projects_module.create_project(name, description)

with an API-backed implementation:
 • Add Typer options to the command signature:
 • --api-url (optional) default: GUARDIAN_API_URL or http://localhost:8888
 • --api-key (optional) default: GUARDIAN_API_KEY
 • POST to: POST {base}/api/projects with JSON:
 • { "name": name, "description": description } (omit description if None)
 • Print created project id/name best-effort.
 • If endpoint 404s, print a helpful message that /api/projects may not exist yet.

1) Update list_projects to use Guardian API (Postgres-backed)

Replace:

projects_module.list_projects()

with:
 • Add --api-url, --api-key
 • GET: GET {base}/api/projects
 • Support response shapes:
 • either a list of dicts
 • or { "projects": [...] }
 • Print “No projects found” if empty.
 • If 404, print helpful message.

1) Replace init_db (SQLite initializer) with a Postgres/API reachability check

Keep the command name init_db so scripts don’t break, but:
 • Remove SQLite table creation behavior (do not create guardian.db tables here).
 • Add --api-url, --api-key
 • Make a lightweight check:
 • GET {base}/api/chat/threads
 • If success: print that DB init is handled by Guardian service startup/migrations.
 • If error: print failure and exit non-zero.

1) Threads CLI commands must be API-backed

There are existing commands:
 • init_threads_table_cmd
 • create_thread_cmd
 • list_threads_by_project
 • list_child_threads
 • show_thread_lineage

4a) init_threads_table_cmd
Change to a no-op message explaining it’s legacy (SQLite) and Postgres is handled by the service. No DB writes.

4b) create_thread_cmd
Change to API-backed:
 • Add --api-url, --api-key
 • POST: POST {base}/api/chat/threads
 • Include payload:
 • title
 • user_id (if provided)
 • project (project name)
 • best-effort also include project_id if you can resolve it via GET /api/projects
 • Print created thread id best-effort.
 • If 404 on endpoint, print helpful error.

4c) list_threads_by_project
Change to API-backed:
 • Add --api-url, --api-key
 • GET: GET {base}/api/chat/threads
 • Filter client-side by project name using:
 • direct thread["project"] if present
 • or map thread["project_id"] -> project name via GET /api/projects
 • Print a list with id/title/user_id/created_at (best-effort fields).

4d) list_child_threads + show_thread_lineage
Change to API-backed:
 • Add --api-url, --api-key
 • Fetch all threads via GET /api/chat/threads
 • Use parent_thread_id OR fallback parent_id to build relationships.
 • list_child_threads prints children of a given parent thread.
 • show_thread_lineage walks parent pointers upward and prints lineage.

1) Conversations commands remain but become explicit legacy no-ops

Keep these commands registered but do not use SQLite:
 • create_conversation
 • list_conversations_by_thread
 • show_conversation_lineage

Replace each function body with a single print(...) warning that it’s legacy and has no Postgres/API equivalent wired yet.

⸻

Implementation Notes (use what already exists)
 • Reuse existing helpers already in the file:
 • _guardian_api_base_url(api_url)
 • _guardian_headers(api_key)
 • Do not delete imports/functions—minimal diff. (But it’s okay if some imports become unused; we’ll clean later.)
 • Keep Typer command names stable.

⸻

Acceptance Criteria
 • Running these commands does not create or require SQLite tables:
 • init-db, create-project, list-projects, threads commands
 • These commands successfully hit the Guardian API when it’s running:
 • create-project, list-projects, create-thread-cmd, list-threads-by-project
 • Conversations commands print a legacy warning and do nothing else.
 • Existing chat commands remain unchanged.

⸻

Suggested Local Test Commands

Assuming Guardian API is running and env vars set:

export GUARDIAN_API_URL="http://localhost:8888"
export GUARDIAN_API_KEY="..."
python -m guardian.guardian_main init-db
python -m guardian.guardian_main list-projects
python -m guardian.guardian_main create-project "Test Project" --description "hello"
python -m guardian.guardian_main create-thread-cmd "Test Project" "My Thread"
python -m guardian.guardian_main list-threads-by-project "Test Project"

⸻

Deliverable
 • A single PR/commit updating guardian/guardian_main.py to meet the above requirements.
