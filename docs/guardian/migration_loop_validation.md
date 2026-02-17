# Deterministic Migration Loop Validation

This runbook validates the authenticated migration loop end to end:
`POST /api/upload-chatgpt-export` -> persistent thread/message writes -> retrievable content through chat APIs.

## Preconditions
- Clean git tree (`git status --porcelain -uall` is empty).
- Docker daemon is available to the shell user.
- `GUARDIAN_API_KEY` is exported.
- Backend stack can run at `http://localhost:8888` (or override `API_BASE`).

## Deterministic Validation Criteria
A run is valid only when all conditions pass:
1. Upload returns HTTP 200 with `threads_imported=1` and `messages_imported=2`.
2. Imported thread is discoverable via `GET /api/chat/threads`.
3. Imported sentinel message content is retrievable via `GET /api/chat/{thread_id}/messages`.
4. Script exits `0` and prints a final `PASS:` line.

If any condition fails, treat the loop as non-deterministic and stop further campaign tasks.

## Canonical Command
Run from repository root:

```bash
bash scripts/verification/validate_migration_loop.sh
```

## What The Script Enforces
- Fail-closed preflight (`git status --porcelain -uall` must be empty).
- Runtime prerequisites (`docker`, `curl`, `jq`, `python3`, `git`).
- Authenticated migration upload using `X-API-Key`.
- Persistence verification against `/api/chat/threads` and `/api/chat/{thread_id}/messages`.
- Explicit PASS/FAIL output with non-zero exit on any mismatch.

## Troubleshooting
- `permission denied ... docker.sock`: start Docker Desktop and ensure current user has daemon access.
- `FAIL: GUARDIAN_API_KEY is required`: export a valid key before running.
- `Imported thread not found`: inspect backend logs and confirm upload response contained expected import counts.
- `sentinel not found`: investigate migration persistence path (`backend/rag/chatgpt_migration.py`) and message listing route.
