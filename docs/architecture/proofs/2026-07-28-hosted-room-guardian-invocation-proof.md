# Hosted Room Guardian Invocation Live Proof — 2026-07-28

> Classification: `NEXT-PROOF-NEEDED`
> Reason: Hosted Room routes quarantined by the tester-supported profile; live invocation cannot be exercised.

## Final Outcome

`NEXT-PROOF-NEEDED`

The implementation chain is present and all focused tests pass. However, the live tester Docker Compose stack runs the `v1-friends-family-web` supported profile, which does not list `hosted_rooms` or `hosted_room_guest` in its `route_posture.enabled` set. The profile's `route_status()` method defaults any unlisted label to `"quarantined"`, and the `_include_router()` gate quarantines the routes before they are registered. No hosted-room HTTP routes are exposed, so no live invocation proof can be produced.

## Tested Commit

```
df1e55ab8170827c8f2c6c9c46fc03b84bae9f00
```

Branch/detached-HEAD state: detached at `df1e55ab8` (Task 9F: "Add explicit Hosted Room Guardian invocation endpoints").

## Environment

| Component | Value |
|---|---|
| Backend URL | `http://127.0.0.1:8889` |
| Frontend URL | `http://127.0.0.1:5174` (Tailscale proxy) |
| Supported profile | `v1-friends-family-web` |
| Docker project | `codexify_tester` |
| Provider | `deepseek` |
| Model | `deepseek-v4-flash` |
| Database port | `127.0.0.1:5434` |

## Service Health

| Service | Status | Detail |
|---|---|---|
| Backend | healthy | `release_hold=true`, profile valid |
| Redis | healthy | reachable |
| DB (Postgres) | healthy | reachable |
| Worker chat | fresh | heartbeat age ~1.4s |
| Queue | progressing | depth 0 |
| Provider (deepseek) | available | authorized, enabled |
| Model (deepseek-v4-flash) | confirmed | chat capability |

All services required for the proof are healthy. The blocking condition is not a service-health issue.

## Provider and Model

- **Provider identifier**: `deepseek`
- **Model identifier**: `deepseek-v4-flash`
- **Authorization**: authorized, enabled
- **Chat capability**: confirmed
- **Provider truth**: configured, authorized, discovered, selectable, executable, egress allowed

## Proof Identities

**NOT CREATED** — blocked by route unavailability.

The proof requires:

- One disposable owner account
- One disposable guest identity/session
- One active Hosted Room owned by the proof owner
- One canonical room backing thread
- One active owner participant
- One accepted guest invitation
- One active guest participant
- One active resident Guardian participant

None were created because no Hosted Room creation endpoint is available.

## Guardian Configuration

**NOT VERIFIED** — blocked by route unavailability.

Required pre-invocation checks:

- Room is active
- Guardian is explicitly enabled
- Exactly one active Guardian participant exists
- Actor source is `resident`
- Actor reference is `guardian`
- Display snapshot is `Guardian`
- Guardian has no human account binding
- Guardian has no invitation binding

## Owner Ordinary-Message Negative Control

**NOT PERFORMED** — blocked.

## Owner Explicit Invocation

**NOT PERFORMED** — blocked.

Owner invocation endpoint:

```
POST /api/hosted-rooms/{room_id}/actors/{participant_id}/invoke
```

Not registered in the tester router.

## Guest Ordinary-Message Negative Control

**NOT PERFORMED** — blocked.

## Guest Explicit Invocation

**NOT PERFORMED** — blocked.

Guest invocation endpoint:

```
POST /api/hosted-room-session/actors/{participant_id}/invoke
```

Not registered in the tester router.

## Duplicate Invocation Proof

**NOT PERFORMED** — blocked.

## Lifecycle Rejection Proof

**NOT PERFORMED** — blocked.

## Queue-Failure Evidence Posture

`live queue-failure injection not performed; canonical focused test evidence retained`

## Identity-Separation Proof

**NOT PERFORMED** — blocked.

ADR-003 identity-separation invariants (request, task, source-message, participant, assistant-message IDs remain distinct) could not be verified live but are covered by focused tests.

## Content-Integrity Proof

**NOT PERFORMED** — blocked.

## Source-Message Preservation Proof

**NOT PERFORMED** — blocked.

## Secret and Privacy Review

Not applicable — no proof data was created and no credentials were handled beyond the read-only discovery commands below.

## Cleanup

Not applicable — no proof data was created.

## Limitations

1. The `v1-friends-family-web` supported profile does not include `hosted_rooms` or `hosted_room_guest` in its `route_posture.enabled` list. The profile's `route_status()` defaults unlisted labels to `"quarantined"`, and `_include_router()` skips quarantined routes.
2. No `.env.tester` file exists in the working tree (the file is git-ignored and was not needed for read-only discovery).
3. The `make tester-status` command requires `.env.tester` and fails; service health was verified directly via Docker and health endpoints.
4. This proof does not qualify arbitrary Persona invocation, Luna invocation, remote Personas, WebSockets, streaming, voice, files, or frontend controls.
5. This proof does not establish production-scale load behavior.

## Qualification Decision

### `NEXT-PROOF-NEEDED`

The implementation chain is present (routes exist in code, all focused tests pass, worker integration tests pass, metadata and persistence tests pass). The blocking condition is a profile-configuration gap, not a code defect.

### Minimal next atomic repair task

Add `hosted_rooms` and `hosted_room_guest` to the `route_posture.enabled` list in:

```
config/supported_profiles/v1-friends-family-web.yaml
```

After this change and a tester stack restart, the routes will be registered and the live proof can proceed.

## Focused Test Results

All tests pass (301 total).

| Test suite | Tests | Result |
|---|---|---|
| `guardian/tests/core/test_hosted_room_invocation.py` | 5 | PASS |
| `guardian/tests/routes/test_hosted_rooms.py` | 131 | PASS |
| `guardian/tests/routes/test_hosted_room_guest.py` | 52 | PASS |
| `guardian/tests/workers/test_chat_worker_hosted_room_invocation.py` | 21 | PASS |
| `tests/core/test_chat_completion_enqueue_service.py` | 7 | PASS |
| `tests/tasks/test_hosted_room_invocation_metadata.py` | 35 | PASS |
| `tests/core/test_chat_message_provenance_persistence.py` | 26 | PASS |
| `tests/test_hosted_room_models.py` | 7 | PASS |
| `tests/test_hosted_room_message_provenance.py` | 17 | PASS |

Command:

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

## Documentation Validation

```
make docs PYTHON=venv/bin/python
```

Result: PASS. "Docs validation passed: required architecture docs, README links, and source headings verified." "Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid."

## Alembic Result

```
venv/bin/python -m alembic -c backend/alembic.ini heads
```

Result: `8b02d5f3a7c9 (head)` — no warnings, no duplicate revisions.

## Tester Service-Health Result

Direct discovery (bypassing `make tester-status` which requires `.env.tester`):

```
curl http://127.0.0.1:8889/health           → {"status":"ok"}
curl http://127.0.0.1:8889/health/chat      → {"ok":true,"redis":"ok","worker":{"status":"fresh"},"queue":{"depth":0},"provider":"deepseek","model":"deepseek-v4-flash"}
docker ps --filter name=codexify_tester     → all 10 services Up and healthy
```

Blocker discovery:

```
curl http://127.0.0.1:8889/openapi.json | grep -i hosted → NO_HOSTED_ROUTES_FOUND
```

## Task 9A–9F Ancestry Results

All commits in the implementation chain verified present:

| Task | Commit | Description |
|---|---|---|
| 9A | `891a9bc92` | Alembic revision reconciliation |
| 9B | `7014f8f6e` | Canonical completion-enqueue extraction |
| 9C | `c0b0145dd` | Bounded Hosted Room invocation task metadata |
| 9D | `f5a0065b0` | Canonical message-provenance persistence |
| 9E | `91a82ec2e` | Worker Hosted Room validation and provenance |
| 9F | `df1e55ab8` | Explicit owner and guest invocation endpoints |

## Starting Gates

| Check | Result |
|---|---|
| `git status --short` | Clean |
| `git rev-parse --abbrev-ref HEAD` | `HEAD` (detached) |
| `git rev-parse HEAD` | `df1e55ab8170827c8f2c6c9c46fc03b84bae9f00` |
| `git merge-base --is-ancestor df1e55ab8 HEAD` | yes |
| Alembic heads | `8b02d5f3a7c9` |
| Owner invocation endpoint | exists in code, not registered at runtime |
| Guest invocation endpoint | exists in code, not registered at runtime |
| Tester backend | available |
| Redis | available |
| Worker-chat | available |
| Configured model/provider | available (`deepseek` / `deepseek-v4-flash`) |
| Disposable proof account | not created (blocked) |

## Exact Commands Executed

```bash
# Starting gates
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git log --all --oneline --decorate --grep="Add explicit Hosted Room Guardian invocation endpoints"
git merge-base --is-ancestor df1e55ab8170827c8f2c6c9c46fc03b84bae9f00 HEAD

# Alembic
venv/bin/python -m alembic -c backend/alembic.ini heads

# Service health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl -s http://127.0.0.1:8889/health
curl -s http://127.0.0.1:8889/health/chat

# Route discovery
curl -s http://127.0.0.1:8889/openapi.json | python3 -c "import json,sys; d=json.load(sys.stdin); paths=[p for p in d.get('paths',{}) if 'hosted' in p.lower()]; print('\n'.join(paths) if paths else 'NO_HOSTED_ROUTES_FOUND')"

# Backend env verification
docker exec codexify_tester-backend-1 env | grep -E "CODEXIFY_SUPPORTED|LLM_PROVIDER"

# Backend log inspection
docker logs codexify_tester-backend-1 2>&1 | grep "routers"

# Profile inspection
cat config/supported_profiles/v1-friends-family-web.yaml | grep -A100 "route_posture:"

# Focused tests
venv/bin/python -m pytest -v guardian/tests/core/test_hosted_room_invocation.py guardian/tests/routes/test_hosted_rooms.py guardian/tests/routes/test_hosted_room_guest.py
venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_hosted_room_invocation.py
venv/bin/python -m pytest -v tests/core/test_chat_completion_enqueue_service.py tests/tasks/test_hosted_room_invocation_metadata.py tests/core/test_chat_message_provenance_persistence.py
venv/bin/python -m pytest -v tests/test_hosted_room_models.py tests/test_hosted_room_message_provenance.py

# Docs validation
make docs PYTHON=venv/bin/python
```

## Current-State Update Decision

**NOT UPDATED** — outcome is `NEXT-PROOF-NEEDED`. Per task protocol, `docs/architecture/00-current-state.md` is only updated when the outcome is `QUALIFIED`.

## Truth-Ledger Update Decision

**NOT UPDATED** — no `docs/architecture/truth-ledger.md` exists in this repository. No new ledger is created.

## Git Commit Hash

To be assigned after committing this proof document.
