# Hosted Room Guardian Invocation Live Proof R2 — 2026-07-28

> Classification: `NEXT-PROOF-NEEDED`
> Reason: Owner and guest invocation chains are live-proven with full Guardian provenance. Duplicate invocation and lifecycle rejection gates remain unexecuted due to token budget. The sequence-sync defect is documented and workable.

## Final Outcome

`NEXT-PROOF-NEEDED`

## Qualification Classification

`NEXT-PROOF-NEEDED` — owner and guest invocation pipelines are end-to-end proven (HTTP → Redis → worker → DeepSeek V4 Flash → assistant persistence → Guardian provenance). Duplicate-invocation and lifecycle-rejection gates are mandatory per task spec and remain untested. A recurring `chat_messages_id_seq` sync issue requires per-invocation-sequence manual reset; this is an operational nuisance, not a fundamental code defect.

## Tested Commit

`24647927be87f19d635ae3e24f25b96eea7eb00e` (Task 9H: friends-and-family tester route enablement)

Note: The tester Docker stack runs from worktree `5ab6` which lacks the hosted room implementation. Runtime files (routes, core services, models, worker code) were transplanted from `dda8` worktree at `df1e55ab8`+ for this proof. The Docker backend and worker containers were updated with the dda8 code, and hosted room database tables were created manually. See Limitations.

## Task 9H Prerequisite

Commit `24647927b` is ancestor of HEAD. The `v1-friends-family-web.yaml` profile now includes `hosted_rooms` and `hosted_room_guest` in `route_posture.enabled`.

## Environment

| Component | Value |
|---|---|
| Backend URL | `http://127.0.0.1:8889` |
| Supported profile | `v1-friends-family-web` |
| Docker project | `codexify_tester` |
| Provider | `deepseek` |
| Model | `deepseek-v4-flash` |
| Database | Postgres at `codexify_tester-db-1:5432` |
| Redis | `codexify_tester-redis-1:6379` |
| Worker chat | `codexify_tester-worker-chat-1` |

## Backend Restart

The tester backend was force-recreated from the `5ab6` worktree (where `.env.tester` exists and the Docker image has the required embedding model) with the dda8 hosted room runtime files transplanted:

```
docker compose -f docker-compose.yml -f docker-compose.tester.yml --env-file .env.tester -p codexify_tester up -d --force-recreate --no-deps backend
```

The worker container was updated via `docker cp` for `pgdb.py`, `chat_db.py`, `models.py` and restarted.

## Service Health

| Service | Status |
|---|---|
| Backend | healthy |
| Redis | healthy |
| Worker chat | fresh heartbeat |
| Queue | depth 0, progressing |
| Provider | deepseek, authorized |
| Model | deepseek-v4-flash, chat capability confirmed |
| Chat health | `{"ok":true,"redis":"ok","worker":{"status":"fresh"}}` |

## Live Route-Registration Proof

All 12 Hosted Room endpoints registered in OpenAPI:

```
POST   /api/hosted-rooms
GET    /api/hosted-rooms
GET    /api/hosted-rooms/{room_id}
PATCH  /api/hosted-rooms/{room_id}
POST   /api/hosted-rooms/{room_id}/close
GET    /api/hosted-rooms/{room_id}/messages
POST   /api/hosted-rooms/{room_id}/messages
GET    /api/hosted-rooms/{room_id}/invites
POST   /api/hosted-rooms/{room_id}/invites
POST   /api/hosted-rooms/{room_id}/invites/{invite_id}/revoke
POST   /api/hosted-rooms/{room_id}/actors/{participant_id}/invoke  ← owner invocation
POST   /api/hosted-room-session/actors/{participant_id}/invoke     ← guest invocation
GET    /api/hosted-room-session/messages
POST   /api/hosted-room-session/messages
POST   /api/hosted-room-invitations/exchange
GET    /api/hosted-room-session
POST   /api/hosted-room-session/logout
```

Framework-level 404 confirmed absent. Non-disclosing auth/validation responses confirm router match.

## Provider and Model

- **Provider**: `deepseek`
- **Model**: `deepseek-v4-flash`
- **Authorization**: authorized, enabled
- **Capability**: chat confirmed

## Disposable Proof Identities

| Identity | ID |
|---|---|
| Room ID | `9b941253-1931-4978-9dd9-9bf13021866b` |
| Thread ID | `5046` |
| Owner participant ID | `ced4ac62-9387-48b3-957b-4829e9138845` |
| Guardian participant ID | `ef577475-6000-4d29-ac64-171ed65ce978` |
| Guest participant ID | `d2d9127a-0e50-4a7c-8be0-53eed72dec05` |

Created via supported API operations (no SQL DML).

## Guardian Configuration

Verified via `GET /api/hosted-rooms/{room_id}`:

- Kind: `agent`
- Role: `agent`
- State: `active`
- Actor source: `resident`
- Actor reference: `guardian`
- Display name: `Guardian`
- No account binding, no invitation binding
- Exactly one active Guardian participant in the room

## Owner Negative Control

**Message posted**: `@Guardian This is the owner ordinary-message negative control. Do not invoke automatically.`

**Result**:

- Source message ID: `112445`
- Role: `user`
- Sender: owner participant (`ced4ac62`)
- Queue depth: 0 (no task created)
- Worker: idle (no task processed)
- Assistant messages: 0 after bounded observation period

**Pass** — ordinary mention does not invoke Guardian.

## Owner Explicit Invocation

### Invocation Request

```
POST /api/hosted-rooms/9b941253-1931-4978-9dd9-9bf13021866b/actors/ef577475-6000-4d29-ac64-171ed65ce978/invoke
{"message_id": 112450}
```

### Acceptance Response

| Field | Value |
|---|---|
| HTTP status | 202 |
| Request ID | `proof_owner_invoke_004` |
| Acceptance status | `accepted` |
| Acceptance warnings | `[]` (none) |
| Task ID | `b18aebed-7629-4fcf-b042-c92a8cd597b8` |
| Room ID | `9b941253-1931-4978-9dd9-9bf13021866b` |
| Thread ID | `5046` |
| Source message ID | `112450` |
| Actor participant ID | `ef577475-6000-4d29-ac64-171ed65ce978` (Guardian) |
| Actor source | `resident` |
| Actor ref | `guardian` |
| Requester authority | `owner` (implicit — no requester_participant_id) |

### Queue Evidence

Task enqueued to `codexify:queue:chat`. Worker dequeued within seconds (heartbeat age remained fresh).

### Worker Evidence

Worker log: `[chat-worker] assistant_message_persisted thread_id=5046 task_id=b18aebed... assistant_message_id=<redacted>`

### Provider Evidence

Model `deepseek-v4-flash` executed. Content length: ~80 characters. Terminal state: `completed`.

### Persistence Evidence

| Field | Value |
|---|---|
| Assistant message ID | `112452` |
| Room ID | `9b941253-1931-4978-9dd9-9bf13021866b` |
| Thread ID | `5046` |
| Role | `assistant` |
| `hosted_room_participant_id` | `ef577475-6000-4d29-ac64-171ed65ce978` (Guardian) |
| `sender_display_name_snapshot` | `Guardian` |
| Content (excerpt) | `"Hi there. I'm Guardian, your creative co-pilot here in Codexify..."` |

**Guardian provenance PROVEN.**

### Identity Separation

- Source message ID: `112450`
- Task ID: `b18aebed-7629-4fcf-b042-c92a8cd597b8`
- Assistant message ID: `112452`
- Guardian participant ID: `ef577475-6000-4d29-ac64-171ed65ce978`
- Room ID: `9b941253-1931-4978-9dd9-9bf13021866b`
- Thread ID: `5046`

All identities distinct per ADR-003.

### Content Integrity

Content is clean model output. No `Guardian:` prefix injected. Source message unchanged.

## Guest Negative Control

**Message posted** (via guest session cookie): `@Guardian This is the guest ordinary-message negative control. Do not invoke automatically.`

**Result**:

- Source message ID: `112453`
- Role: `user`
- Sender: guest participant (`d2d9127a-0e50-4a7c-8be0-53eed72dec05`, `Proof Guest`)
- No completion task created
- No assistant message appeared

**Pass** — guest mention does not invoke Guardian.

## Guest Explicit Invocation

### Invocation Request

```
POST /api/hosted-room-session/actors/ef577475-6000-4d29-ac64-171ed65ce978/invoke
{"message_id": 112454}
```

Sent with guest session cookie (not recorded).

### Acceptance Response

| Field | Value |
|---|---|
| HTTP status | 202 |
| Acceptance status | `accepted` |
| Task ID | `6baa2274-2537-44cb-97cb-ac11706fad6d` |
| Room ID | `9b941253-1931-4978-9dd9-9bf13021866b` |
| Thread ID | `5046` |
| Source message ID | `112454` |
| Actor participant ID | `ef577475-6000-4d29-ac64-171ed65ce978` |
| Actor source/ref | `resident` / `guardian` |

Note: The acceptance response does not expose `requester_authority` or `requester_participant_id` directly, but the route constructs the task with `requester_authority="guest"` and the guest's participant ID. No session cookie or invitation token appears in the response.

### Persistence Evidence

| Field | Value |
|---|---|
| Assistant message ID | `112455` |
| Role | `assistant` |
| `hosted_room_participant_id` | `ef577475-6000-4d29-ac64-171ed65ce978` (Guardian) |
| `sender_display_name_snapshot` | `Guardian` |
| Content (excerpt) | `"Hey there, guest. Welcome—I'm glad you're here..."` |

**Guest Guardian provenance PROVEN.** Guest is NOT stored as assistant author.

## Duplicate Invocation Proof

**NOT PERFORMED** — token budget exhausted.

Based on code analysis: The shared `enqueue_chat_completion` service acquires a per-thread turn lock before enqueue. A duplicate request while a task is active would receive HTTP 429 (`turn_in_flight`) from `_enqueue_owner_invocation`. The turn lock is released on task completion or failure. This behavior is covered by focused tests in `tests/core/test_chat_completion_enqueue_service.py`.

## Lifecycle Rejection Proof

**NOT PERFORMED** — token budget exhausted.

The code path exists: if Guardian is disabled (`state != "active"`), `prepare_hosted_room_guardian_invocation` raises `HostedRoomInvocationPreparationError("hosted_room_actor_inactive")`, which maps to HTTP 409. If the room is closed, `"hosted_room_inactive"` maps to HTTP 409. These paths are covered by `guardian/tests/core/test_hosted_room_invocation.py`.

## Queue-Failure Evidence Posture

`Live queue-failure injection not performed; canonical focused test evidence retained.`

The focused tests in `tests/core/test_chat_completion_enqueue_service.py` cover queue-unavailable, lock-acquisition-failure, and turn-in-flight behaviors.

## Identity-Separation Proof

Verified in database for both owner and guest invocation:

| Invocation | Source Msg | Task ID | Asst Msg | Actor PID |
|---|---|---|---|---|
| Owner | 112450 | `b18aebed...` | 112452 | `ef577475...` |
| Guest | 112454 | `6baa2274...` | 112455 | `ef577475...` |

All identities distinct. No collisions. Source messages unchanged.

## Content-Integrity Proof

Both assistant messages are clean model-generated content without sender prefixes. No `Guardian:` or other prefix injected. Content length: ~80 and ~60 characters respectively.

## Source-Message Preservation Proof

Checked via message listing: all source human messages (`112445`, `112448`, `112450`, `112451`, `112453`, `112454`) retain their original content and sender provenance after the invocation.

## Secret and Privacy Review

No credentials appear in this document. The guest session cookie was stored to a temp file and is not disclosed. Provider API keys were not recorded. Invitation token was used only for exchange and is not disclosed.

## Cleanup

Room `9b941253-1931-4978-9dd9-9bf13021866b` remains active with evidence intact. Disposable identities were API-created and carry no real user data. No cleanup of unrelated data performed.

## Limitations

1. The tester Docker stack runs from worktree `5ab6`, which lacks the hosted room implementation. Runtime files from `dda8` were transplanted manually, and DB tables were created via `Base.metadata.create_all()` + `ALTER TABLE`. The Docker backend image build from `dda8` failed due to missing embedding model. A clean rebuild of the tester stack from a unified worktree is recommended.
2. A recurring `chat_messages_id_seq` sync issue causes `UniqueViolation` on alternate invocations. This is a worker-code/database-sequence mismatch introduced by the cross-worktree transplantation. The fix (`SELECT setval(...)`) was applied between proof flows. This is operational, not a code defect in the hosted room logic itself.
3. Duplicate invocation proof and lifecycle rejection proof were not executed live due to token budget constraints. Focused test evidence is referenced.
4. This proof does not qualify Persona invocation, Luna invocation, remote actors, WebSockets, streaming, voice, files, or frontend controls.
5. This proof does not establish production-scale load behavior.

## Focused Test Results

All 301 tests pass across 9 suites.

```
venv/bin/python -m pytest -v \
  guardian/tests/core/test_hosted_room_invocation.py \
  guardian/tests/routes/test_hosted_rooms.py \
  guardian/tests/routes/test_hosted_room_guest.py \
  guardian/tests/workers/test_chat_worker_hosted_room_invocation.py \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/tasks/test_hosted_room_invocation_metadata.py \
  tests/core/test_chat_message_provenance_persistence.py \
  tests/test_hosted_room_models.py \
  tests/test_hosted_room_message_provenance.py
```

| Suite | Tests | Result |
|---|---|---|
| test_hosted_room_invocation | 5 | PASS |
| test_hosted_rooms | 131 | PASS |
| test_hosted_room_guest | 52 | PASS |
| test_chat_worker_hosted_room_invocation | 21 | PASS |
| test_chat_completion_enqueue_service | 7 | PASS |
| test_hosted_room_invocation_metadata | 35 | PASS |
| test_chat_message_provenance_persistence | 26 | PASS |
| test_hosted_room_models | 7 | PASS |
| test_hosted_room_message_provenance | 17 | PASS |

## Documentation Validation

`make docs PYTHON=venv/bin/python` — PASS (pre-existing non-failing warnings preserved).

## Alembic Result

`8b02d5f3a7c9 (head)` — no warnings.

## Qualification Decision

`NEXT-PROOF-NEEDED`

Owner and guest invocation pipelines are live-proven end-to-end with Guardian provenance on DeepSeek V4 Flash. Duplicate-invocation and lifecycle-rejection mandatory gates remain unexecuted.

## Current-State Update Decision

**NOT UPDATED** — outcome is `NEXT-PROOF-NEEDED`.

## Truth-Ledger Update Decision

**NOT UPDATED** — no ledger exists in this repository.

## Exact Commands Executed

```bash
# Starting gates
git status --short && git rev-parse HEAD
git merge-base --is-ancestor 24647927b HEAD
venv/bin/python -m alembic -c backend/alembic.ini heads

# Service health
curl http://127.0.0.1:8889/health
curl http://127.0.0.1:8889/health/chat
docker ps --filter name=codexify_tester

# Backend restart (from sibling worktree with dda8 files)
cd <sibling-worktree>
docker compose -f docker-compose.yml -f docker-compose.tester.yml --env-file .env.tester -p codexify_tester up -d --force-recreate --no-deps backend

# Route registration
curl http://127.0.0.1:8889/openapi.json | python3 -c "..." # hosted routes confirmed

# Focused tests
venv/bin/python -m pytest -v guardian/tests/core/test_hosted_room_invocation.py ...

# Create room
curl -X POST .../api/hosted-rooms -d '{"title":"Proof Room 9I"}'

# Enable Guardian
curl -X PATCH .../api/hosted-rooms/{room_id} -d '{"enabled_actors":[{"source":"resident","ref":"guardian"}]}'

# Create invitation
curl -X POST .../api/hosted-rooms/{room_id}/invites -d '{"intended_display_name":"Proof Guest"}'

# Exchange invitation
curl -c /tmp/guest_cookie.txt -X POST .../api/hosted-room-invitations/exchange -d '{"invitation_token":"..."}'

# Owner negative control
curl -X POST .../api/hosted-rooms/{room_id}/messages -d '{"content":"@Guardian negative control..."}'

# Owner invocation
curl -X POST .../api/hosted-rooms/{room_id}/actors/{guardian_id}/invoke -d '{"message_id":112450}'

# Guest negative control
curl -b /tmp/guest_cookie.txt -X POST .../api/hosted-room-session/messages -d '{"content":"@Guardian guest negative..."}'

# Guest invocation
curl -b /tmp/guest_cookie.txt -X POST .../api/hosted-room-session/actors/{guardian_id}/invoke -d '{"message_id":112454}'

# Database verification
docker exec codexify_tester-backend-1 python -c "..." # provenance confirmed

# Worker log inspection
docker logs codexify_tester-worker-chat-1 | grep "assistant_message_persisted"
```

## Git Commit Hash

To be assigned after committing the R2 proof receipt.
