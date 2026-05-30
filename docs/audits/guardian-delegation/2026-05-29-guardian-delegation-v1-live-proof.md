# Guardian Delegation v1 Live Proof

## Scope

This is a live internal proof for the Guardian Delegation v1 loop on the local
Docker Compose runtime. It exercises the internal Guardian delegation API with
the route intentionally enabled, then restores the default route posture.

This proof does not promote Guardian delegation to the default release surface.
The source thread remains user truth, and the transcript projection remains
inspection truth only.

Result completion was proven through the in-container Guardian result-storage
seam used by the Phase 3 contract tests:

- Actual source-thread result delivery was live against Postgres and the chat
  message API.
- External coding-worker task execution was not exercised.

## Repository and Runtime

| Field | Value |
| --- | --- |
| Working directory | `/Volumes/Dev_SSD/Codexify-main` |
| Git root | `/Volumes/Dev_SSD/Codexify-main` |
| Branch | `codex/create-guardian-delegation-contract` |
| Remote | `origin https://github.com/Resonant-Jones/Codexify.git` |
| HEAD before proof artifact | `35b8ee5ce426dcbb805bead07bb2337b7eeadfbb` |
| Docker Compose project/context | default `codexify` project from `/Volumes/Dev_SSD/Codexify-main` |
| Temporary override used | `/private/tmp/codexify-guardian-delegation-proof.override.yml` |
| Proof window | 2026-05-29T09:31Z through 2026-05-29T09:48Z |

Dirty or untracked files observed before proof:

- `docs/Arcanum/`
- `pi-session-2026-05-27T09-26-58-798Z_019e68c2-35ed-772b-bd9f-a4cbdfad9fd7.html`

These files were pre-existing and unrelated to this proof.

## Route Flag Posture

Flag name:

```text
CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES
```

The first temporary override set only that flag:

```yaml
services:
  backend:
    environment:
      CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES: "true"
```

Startup still reported `guardian_delegations` as quarantined by
`v1-local-core-web-mcp`. For this internal proof only, the override was narrowed
to disable the supported-profile quarantine while enabling the route:

```yaml
services:
  backend:
    environment:
      CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES: "true"
      CODEXIFY_SUPPORTED_PROFILE: ""
```

Observed route-enabled startup line:

```text
[routers] enabled guardian_delegations
```

Cleanup restored normal route posture. The final backend boot used
`CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp` and no Guardian delegation
route flag. Observed restored startup line:

```text
[routers] quarantined guardian_delegations (supported_profile=v1-local-core-web-mcp)
```

The restored route probe returned generic unmounted-route behavior:

```json
{"detail":"Not Found"}
```

The temporary override file was deleted after the proof. No normal development
volumes were destroyed.

## Exact Commands

Repository safety check:

```sh
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
```

Pre-read and seam inspection used `sed` and `rg` against the required
architecture docs, Guardian delegation contracts, route files, service files,
store files, and focused test files listed in the task prompt.

Compose setup:

```sh
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose -f docker-compose.yml -f /private/tmp/codexify-guardian-delegation-proof.override.yml up -d backend
```

Health and route probes:

```sh
KEY="$(bash scripts/dev/dev-key.sh)"
curl -fsS -H "X-API-Key: $KEY" http://127.0.0.1:8888/health
curl -fsS -H "X-API-Key: $KEY" http://127.0.0.1:8888/health/chat
curl -sS -o /tmp/gd_missing_transcript.json -w "%{http_code}\n" \
  -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_missing_live/transcript
```

Source-thread setup:

```sh
curl -sS -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"thread_id":null,"role":"user","content":"GUARDIAN_DELEGATION_LIVE_PROOF_2026_05_29: Patch guardian delegation live proof sentinel path and preserve source-thread lineage.","title":"Guardian Delegation Live Proof 2026-05-29","metadata":{"proof":"guardian_delegation_v1_live_proof"}}' \
  http://127.0.0.1:8888/api/chat/messages
```

Manual intent, transcript, and approval:

```sh
curl -sS -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"thread_id":2,"source_message_id":7,"project_id":1,"approval_mode":"human_required"}' \
  http://127.0.0.1:8888/api/guardian/delegations

curl -sS -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_3e6e84e5c1354441/transcript

curl -sS -X POST -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_3e6e84e5c1354441/approve

curl -sS -X POST -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_3e6e84e5c1354441/approve
```

Result storage through the in-container Guardian store seam:

```sh
docker compose -f docker-compose.yml -f /private/tmp/codexify-guardian-delegation-proof.override.yml exec -T backend python -c 'import json; from guardian.core.db import load_guardian_db_from_env; from guardian.agents.store import AgentStore; db=load_guardian_db_from_env(); result=AgentStore(db=db).store_coding_result(run_id="run_827f964fa15e4473", coding_task_id="live-proof-task-1", attempt_id="live-proof-attempt-1", thread_id=2, source_message_id=7, result_status="succeeded", result_summary="Live proof stored a safe Guardian delegation result through the delivery seam.", files_changed=["docs/audits/guardian-delegation/2026-05-29-guardian-delegation-v1-live-proof.md"], validation_results={"status":"passed","command":"live-proof synthetic store seam"}, commit_hash="liveproofabc123"); print(json.dumps(result, sort_keys=True, default=str))'
```

Duplicate delivery/idempotency check:

```sh
docker compose -f docker-compose.yml -f /private/tmp/codexify-guardian-delegation-proof.override.yml exec -T backend python -c 'import json; from guardian.core.db import load_guardian_db_from_env; from guardian.agents.store import AgentStore; db=load_guardian_db_from_env(); result=AgentStore(db=db).store_coding_result(run_id="run_827f964fa15e4473", coding_task_id="live-proof-task-1", attempt_id="live-proof-attempt-1", thread_id=2, source_message_id=7, result_status="succeeded", result_summary="Live proof stored a safe Guardian delegation result through the delivery seam.", files_changed=["docs/audits/guardian-delegation/2026-05-29-guardian-delegation-v1-live-proof.md"], validation_results={"status":"passed","command":"live-proof synthetic store seam"}, commit_hash="liveproofabc123"); print(json.dumps({"delivery_ok": result.get("delivery_ok"), "delivery_status": result.get("delivery_status"), "message_id": result.get("message_id"), "result_message_id": result.get("result_message_id"), "source_thread_delivery_suppressed": result.get("source_thread_delivery_suppressed"), "visibility_status": result.get("visibility_status")}, sort_keys=True, default=str))'
```

Source-thread and delivered-transcript reads:

```sh
curl -sS -H "X-API-Key: $KEY" \
  'http://127.0.0.1:8888/api/chat/2/messages?limit=50'

curl -sS -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_3e6e84e5c1354441/transcript

curl -sS -H "X-API-Key: $KEY" \
  http://127.0.0.1:8888/api/guardian/delegations/gdi_3e6e84e5c1354441
```

Cancellation suppression proof used the same chat/API/store pattern with:

```text
pending cancel source: thread_id=3 source_message_id=9 intent_id=gdi_2f5b1496fdf54a03
active cancel source: thread_id=4 source_message_id=10 intent_id=gdi_671193a3a82a48a0 run_id=run_9ad32b5a8d3044e9
```

Cleanup/restoration:

```sh
docker compose up -d backend
docker compose -f docker-compose.yml up -d --no-deps --force-recreate backend
docker stop codexify-backend-1
docker rm codexify-backend-1
docker compose up -d --no-deps backend
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' codexify-backend-1
docker start codexify-backend-1
```

The Compose recreate commands left the backend container in `created` state.
Starting that recreated container directly restored the normal route posture.

Validation:

```sh
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase2a_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase3_delivery_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_approval_cancel_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_command_center_transcript_contract.py
cd frontend && pnpm test -- GuardianDelegationTranscriptViewer CommandCenterShell
python3 scripts/validate_docs.py
git diff --check
```

## Health Evidence

`GET /health` during the route-enabled proof returned:

```text
status=ok
service=core
supported_profile.name=null
supported_profile.valid=false
supported_profile.mismatches=["supported profile manifest is not configured"]
```

This mismatch was expected because the route-enabled proof boot explicitly
disabled the supported-profile manifest to bypass the route quarantine. It is
evidence that this proof is internal-only, not release posture.

`GET /health/chat` during the proof returned:

```text
ok=true
status=healthy
redis=ok
worker.status=fresh
queue.depth=0
completion_service.ok=true
provider=local
```

Service status after cleanup:

```text
backend healthy
db healthy
neo4j healthy
redis healthy
worker-chat running
worker-coding running
worker-document-embed running
```

## Source Thread and Message

Primary proof source:

| Field | Value |
| --- | --- |
| `thread_id` | `2` |
| `source_message_id` | `7` |
| `project_id` | `1` |
| Sentinel | `GUARDIAN_DELEGATION_LIVE_PROOF_2026_05_29` |

The source thread remains user truth. The selected source message was used for
lineage, and the durable delegation plan referenced it by hash/length rather
than copying broad chat history or personal facts.

## Manual Approval Intent Proof

Manual intent creation returned:

```text
intent_id=gdi_3e6e84e5c1354441
approval_mode=human_required
approval_state=pending
approval_source=none
intent_status=awaiting_approval
run_id=null
run_status=not_enqueued
visibility_status=not_posted
context_basis[0].source_type=selected_turn
```

Pending transcript projection returned:

```text
inspection_only=true
run_id=null
run_status=not_enqueued
transcript_items=intent_created, plan_prepared, approval_state
```

No AgentRun was created before approval.

## Approval and Run Linkage Proof

First approval returned:

```text
approval_state=approved
approval_source=human
intent_status=accepted
run_id=run_827f964fa15e4473
run_status=queued
```

Repeated approval returned the same stable run:

```text
run_id=run_827f964fa15e4473
```

GET detail after delivery returned:

```text
run_status=completed
visibility_status=result_posted
result_message_id=8
result_delivered_at=2026-05-29T09:34:31.112260+00:00
```

## Result Delivery Proof

Result delivery was proven through the in-container Guardian result-storage
seam, not external coding-worker execution.

First storage returned:

```text
ok=true
delivery_ok=true
delivery_status=delivered
message_id=8
result_message_id=8
visibility_status=result_posted
terminal_run_status=succeeded
```

Repeated storage returned:

```text
delivery_ok=true
delivery_status=delivered
message_id=8
result_message_id=8
source_thread_delivery_suppressed=false
visibility_status=result_posted
```

The source thread contained exactly two messages after delivery:

```text
message 7: user source turn
message 8: assistant coding_result
```

Result message metadata included:

```text
guardian_delegation_intent_id=gdi_3e6e84e5c1354441
run_id=run_827f964fa15e4473
thread_id=2
source_message_id=7
delivery_key=guardian_delegation:gdi_3e6e84e5c1354441:run_827f964fa15e4473:thread_result
delivery_kind=guardian_delegation_result
visibility_status=result_posted
```

The posted content was bounded and safe. It included status, intent ID, run ID,
a safe result summary, one safe repo path, validation status/command, and a
synthetic proof commit marker. It did not dump `context_basis`, hidden prompts,
Project KB excerpts, broad chat history, secrets, or personal/conversational
content.

## Transcript Projection Proof

Pending projection evidence:

```text
inspection_only=true
items=intent_created, plan_prepared, approval_state
run_id=null
no delivery_result item
```

Delivered projection evidence:

```text
inspection_only=true
run_id=run_827f964fa15e4473
run_status=completed
visibility_status=result_posted
result_message_id=8
items included run_linked, run_status, delivery_result
```

Delivered transcript lineage included:

```text
intent_id=gdi_3e6e84e5c1354441
thread_id=2
source_message_id=7
run_id=run_827f964fa15e4473
delivery_key=guardian_delegation:gdi_3e6e84e5c1354441:run_827f964fa15e4473:thread_result
```

## Cancellation Suppression Proof

Pending cancel proof:

```text
thread_id=3
source_message_id=9
intent_id=gdi_2f5b1496fdf54a03
cancel result intent_status=cancelled
run_id=null
run_status=not_enqueued
```

Active cancel proof:

```text
thread_id=4
source_message_id=10
intent_id=gdi_671193a3a82a48a0
run_id=run_9ad32b5a8d3044e9
cancel result intent_status=cancelled
```

Later result storage for the cancelled active intent returned:

```text
delivery_ok=false
delivery_status=stale_suppressed
delivery_reason_code=guardian_delegation_cancelled
message_id=null
source_thread_delivery_suppressed=true
visibility_status=stale_suppressed
```

The active-cancel source thread still contained only the user source message.
No stale assistant result message was posted.

The cancelled transcript projection showed:

```text
intent_status=cancelled
visibility_status=stale_suppressed
items included intent_cancelled and visibility_state
delivery_error=guardian_delegation_cancelled
```

## Frontend Viewer Probe

The local frontend viewer was not probed in-browser during this backend live
proof. It was not required for the backend supported-path evidence and remains
covered by focused frontend tests:

```sh
cd frontend && pnpm test -- GuardianDelegationTranscriptViewer CommandCenterShell
```

## What This Proof Does Not Prove

- This is not release promotion.
- This does not prove GitHub context.
- This does not prove intent-spine unification.
- This does not prove broad autonomous execution.
- This does not prove broad "answer as me" authority.
- This does not prove a complete Command Center product surface.
- This does not prove multi-worker PostgreSQL concurrency for approval idempotency.
- This does not prove external coding-worker execution, because the result leg
  used the in-container Guardian result-storage seam.
- This does not prove the Guardian delegation route can be enabled under the
  current supported profile without an explicit route-posture change; the
  supported profile currently quarantines the route.

## Caveats

- The route-enabled proof boot required `CODEXIFY_SUPPORTED_PROFILE=""` because
  `v1-local-core-web-mcp` quarantines `guardian_delegations` before the route
  flag can mount it.
- `/health` therefore reported the supported-profile manifest as not configured
  during the enabled-route proof. This is intentionally recorded as internal
  proof posture, not release posture.
- Result completion was store-seam proof, not actual coding-worker execution.
- Cleanup hit Docker Compose CLI hangs while recreating backend. No volumes were
  removed. The backend container was stopped and removed, Compose recreated it
  in `created` state with normal environment, and `docker start
  codexify-backend-1` restored the healthy default-off backend.
- The temporary override file was deleted.
- Existing unrelated untracked files remained untouched.

## Validation

Validation commands for this task are recorded below.

```sh
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase2a_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase3_delivery_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_approval_cancel_contract.py
./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_command_center_transcript_contract.py
cd frontend && pnpm test -- GuardianDelegationTranscriptViewer CommandCenterShell
python3 scripts/validate_docs.py
git diff --check
```

Observed results:

- `./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase2a_contract.py`
  passed: 22 tests passed, 4 warnings.
- `./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_phase3_delivery_contract.py`
  passed: 15 tests passed.
- `./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_approval_cancel_contract.py`
  passed: 13 tests passed.
- `./.venv/bin/pytest -v tests/contracts/test_guardian_delegation_command_center_transcript_contract.py`
  passed: 12 tests passed, 4 warnings.
- `cd frontend && pnpm test -- GuardianDelegationTranscriptViewer CommandCenterShell`
  passed: 30 tests passed across 2 files. The run emitted existing neighboring
  React `act(...)` and list-key warnings in Command Center shell tests.
- `python3 scripts/validate_docs.py` passed.
- `git diff --check` passed.

## Final Result

`PASS`

The live proof established:

- route enabled internally for the proof window
- manual intent created pending without dispatch
- transcript projection showed pending inspection state
- approval linked exactly one stable AgentRun
- source-thread result delivery was proven through the explicitly caveated
  in-container Guardian result-storage seam
- duplicate result storage did not create duplicate messages
- delivered transcript projection showed lifecycle and delivery lineage
- pending cancel prevented dispatch
- active cancel suppressed future source-thread delivery
- route posture was restored to default quarantined/off state
- no release posture was widened
