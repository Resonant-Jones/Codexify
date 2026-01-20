Codexify Task Prompt

TASK-ID
TASK-2026-01-20-001_CHAT_ENDPOINT_CANONICALIZATION

Context
You’re operating on the local Codexify repo on branch chore/post-skip-hook-fixes.

We have drift/ambiguity around “the chat endpoint” (backend route(s) and frontend client calls). This causes:

- Multiple URLs that “kind of work” depending on which UI surface calls them
- Confusing proxy/baseURL behavior (especially in Docker vs local)
- Higher chance of regressions (tests/e2e hitting the wrong route)

We want ONE canonical chat endpoint that the frontend uses consistently, while preserving backward compatibility for any legacy paths.

Objective
Canonicalize the Guardian chat/completions endpoint(s):

1) Pick a single canonical backend route for chat completion.
2) Ensure any legacy/alternate routes remain functional by delegating to the canonical handler (no breaking change).
3) Update the frontend client code to call ONLY the canonical route.
4) Add/adjust tests so the canonical path is covered and legacy aliases don’t silently break.

Requirements

- Canonical route must be clearly defined and documented in the task artifact.
- Backward compatible:
  - If old route(s) exist, keep them as aliases that call the canonical handler (no duplicate logic).
  - Do NOT break existing UI flows or imports.
- Minimal behavior change:
  - No model logic changes, no prompt changes, no RAG logic changes.
  - Only routing + client path canonicalization.
- Follow docs/Ops/Runner_Protocol.md two-phase commit pattern:
  - Commit A: implementation changes only
  - Commit B: docs task artifact only
- Include TASK-ID in BOTH commit messages.
- Commit hash paradox handling:
  - DO NOT use git commit --amend.
  - In the artifact doc, Finalize-artifact hash may be: (reported in final mapping)
  - Final output MUST include mapping with both hashes.

Files allowed to edit (only)
Backend (routing only):

- guardian/app.py (or the backend entry/router registration file if different)
- guardian/routes/chat.py (or equivalent chat route module)
- guardian/routes/__init__.py (only if needed for router inclusion)

Frontend (client path only):

- frontend/src/lib/api.ts
- frontend/src/features/chat/GuardianChat.tsx (only if it directly hardcodes endpoints)
- frontend/src/features/chat/useChat.ts (or equivalent hook calling the chat endpoint)

Docs:

- docs/tasks/TASK_2026_01_20_001_chat_endpoint_canonicalization.md

STOP CONDITION (scope integrity)
If any of the above paths do not exist or the correct files differ, STOP and report:

- the closest matching file paths you found
- what route(s) currently exist
- what the frontend currently calls
Do NOT edit “equivalent” files unless they are explicitly confirmed by the repository structure (report first).

Implementation Notes
A) Identify current routes

- Find all backend routes that serve chat completion (search for: "/chat", "/guardian", "completion", "messages", "threads", "respond", "stream").
- Find all frontend calls that send messages to the backend (search for axios.post/fetch to "/chat", "/api/chat", "/api/guardian", etc).

B) Choose canonical endpoint

- Canonical endpoint should be stable and unsurprising.
- Recommendation unless repo conventions say otherwise:
  - Canonical: POST /api/chat
- If repo already uses a different stable prefix (e.g. /api/guardian/chat), follow repo convention and make THAT canonical instead.

C) Canonical backend implementation pattern

- The canonical route should call the existing “real” handler function (or become the real handler).
- Any legacy endpoints should delegate to the canonical handler function (same request/response behavior).
- Avoid redirect responses for POST APIs (redirects break some clients). Prefer in-process delegation.

D) Frontend canonicalization

- Update the frontend to call ONLY the canonical route.
- Ensure baseURL/proxy usage remains unchanged (don’t change Vite proxy behavior in this task).

E) Tests

- Add/adjust at least one test that exercises the canonical endpoint path end-to-end at the “request layer” you already have.
- If existing tests cover chat flow but use a legacy path, update them to use canonical.
- If backend tests are sparse, add a lightweight unit/integration test for the router path mapping (canonical + alias calling same handler).

Checks to run (required)
Run these exactly and report pass/fail:

1) Backend

- pytest -v

1) Frontend

- pnpm --dir frontend/src test
- pnpm --dir frontend/src lint

1) Final repo state

- git status --porcelain  (must be empty after Commit B)

Git steps (two-phase)

Commit A (implementation)

1) git status --porcelain (must show only expected changes)
2) Run required checks above (must pass)
3) git add <only allowed files that changed>
4) git commit -m "TASK-2026-01-20-001_CHAT_ENDPOINT_CANONICALIZATION: canonicalize chat endpoint + alias legacy routes"
5) Capture hash A

Commit B (finalize task artifact)

1) Create/update docs/tasks/TASK_2026_01_20_001_chat_endpoint_canonicalization.md including:
   - Task Prompt (verbatim copy of this prompt)
   - What is the canonical endpoint (exact path + method)
   - What legacy endpoints exist and how they alias
   - Summary: files changed, commands run + results, git status confirmation
   - Commit mode: two-phase (NO amend)
   - Implementation hash: <hash A>
   - Finalize-artifact hash: (reported in final mapping)
2) git add docs/tasks/TASK_2026_01_20_001_chat_endpoint_canonicalization.md
3) git commit -m "TASK-2026-01-20-001_CHAT_ENDPOINT_CANONICALIZATION: finalize task summary"
4) Capture hash B

Output required (must print)

- Canonical endpoint (method + path)
- Legacy endpoints and alias behavior
- Commands run + pass/fail
- git status --porcelain (must be empty)
- Mapping:
  TASK-2026-01-20-001_CHAT_ENDPOINT_CANONICALIZATION -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria
✅ Frontend calls exactly one chat endpoint path (canonical)  
✅ Backend supports canonical path + legacy aliases without duplicating logic  
✅ Tests/lint pass  
✅ Working tree clean after finalize commit
