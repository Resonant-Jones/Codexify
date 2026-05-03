# TASK-2026-05-03-001: Live Compose Proof - Coding Result Return Path

## Purpose

Prove the full coding delegation pipeline end-to-end in the supported Docker Compose topology. This is not a unit test—it is a live runtime verification that validates ADR-020 compliance in the actual deployment environment.

**Completion criteria:** Every verification step below passes in a running `docker compose` stack before any feature is marked release-ready.

---

## Verification Targets

### Preconditions (must exist before testing)

1. [ ] `backend` service healthy at `http://localhost:8888`
2. [ ] `db` service PostgreSQL accepts connections
3. [ ] `redis` service healthy (PONG on `redis-cli ping`)
4. [ ] `worker-coding` service running and polling
5. [ ] A real source thread exists in Postgres with at least one user message

### Core Pipeline Verification

#### 1. Backend, DB, Redis, Worker Network

```bash
# Verify all services in same docker network
docker network inspect codexify_default | jq '.Containers[].Name'

# Verify backend can reach redis
docker compose exec backend python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print('Redis reachable:', r.ping())
"

# Verify backend can reach postgres
docker compose exec backend python -c "
from guardian.core.db import load_guardian_db_from_env
db = load_guardian_db_from_env()
print('DB reachable:', db is not None)
"
```

#### 2. Real Source Thread in Postgres

```bash
# Query for existing threads
docker compose exec db psql -U codexify -d Codexify -c "
SELECT id, user_id, created_at FROM chat_threads LIMIT 5;
"

# Query for messages in thread
docker compose exec db psql -U codexify -d Codexify -c "
SELECT id, thread_id, role, LEFT(content, 50), kind 
FROM chat_messages 
WHERE thread_id = <THREAD_ID>
ORDER BY created_at DESC 
LIMIT 5;
"
```

Record `thread_id` and `source_message_id` for use in step 3.

#### 3. POST /api/agents/coding/execute Enqueues

```bash
set -a; source .env; set +a

RESPONSE="$(
  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    http://localhost:8888/api/agents/coding/execute \
    -d "{
      \"coding_task_id\": \"live-test-$(date +%s)\",
      \"thread_id\": \"<THREAD_ID>\",
      \"source_message_id\": \"<SOURCE_MSG_ID>\",
      \"attempt_id\": \"attempt-$(date +%s)\",
      \"user_id\": \"local\",
      \"project_id\": null,
      \"adapter_kind\": \"pi_sdk\",
      \"instructions\": \"echo 'live-test-success' > /tmp/live_verification.txt\",
      \"repo_root\": \"/tmp\",
      \"context_summary\": null,
      \"permission_policy\": {
        \"allow_shell\": true,
        \"allow_network\": false,
        \"allow_write\": true,
        \"allowed_paths\": [\"/tmp\"],
        \"max_runtime_seconds\": 60
      }
    }"
)"

echo "$RESPONSE" | jq
RUN_ID="$(echo "$RESPONSE" | jq -r '.run_id')"
```

**Pass criteria:** HTTP 200, `ok: true`, `run_id` present, no errors.

#### 4. coding_worker Dequeues

```bash
# Check queue before worker processes
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution

# Wait up to 10 seconds
sleep 10

# Check queue after worker processes  
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution

# Check worker logs for processing
docker compose logs worker-coding --tail=50 | grep -E "task|running|completed|failed"
```

**Pass criteria:** 
- Queue depth drops (worker picked up task)
- Worker logs show task processing

#### 5. Run Status Reaches Terminal State

```bash
# Poll run events
curl -N -sS \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/agents/runs/$RUN_ID/events" | head -20

# Check DB for run status
docker compose exec db psql -U codexify -d Codexify -c "
SELECT run_id, status, ended_at, error 
FROM agent_runs 
WHERE run_id = '$RUN_ID';
"
```

**Pass criteria:** `status` is `succeeded` or `failed` (not `queued` or `running`).

#### 6. Task Events Show Lifecycle Evidence

**Expected event sequence:**
1. `created` (from route)
2. `task.running` (from worker)
3. `task.completed` or `task.failed` (from worker)

```bash
# Stream and capture all events
curl -N -sS \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/agents/runs/$RUN_ID/events" 2>/dev/null &
sleep 15
kill %1 2>/dev/null
```

**Pass criteria:** All three event types observed.

#### 7. Exactly One coding_result Message in Source Thread

```bash
docker compose exec db psql -U codexify -d Codexify -c "
SELECT id, thread_id, role, kind, LEFT(content, 100), extra_meta
FROM chat_messages 
WHERE thread_id = <THREAD_ID> 
  AND kind = 'coding_result'
ORDER BY created_at;
"
```

**Pass criteria:** Exactly 1 row with `kind = 'coding_result'`.

#### 8. Idempotency Prevents Duplicate

```bash
# Record current count
BEFORE="$(docker compose exec db psql -U codexify -d Codexify -t -c "
  SELECT COUNT(*) FROM chat_messages 
  WHERE thread_id = <THREAD_ID> AND kind = 'coding_result';
")"

# Trigger same run_id again (simulate retry)
# Note: This tests the guard in _inject_coding_result_into_thread
# In practice, retries use new attempt_id but same run_id

AFTER="$(docker compose exec db psql -U codexify -d Codexify -t -c "
  SELECT COUNT(*) FROM chat_messages 
  WHERE thread_id = <THREAD_ID> AND kind = 'coding_result';
")"

echo "Before: $BEFORE, After: $AFTER"
```

**Pass criteria:** Count unchanged (no duplicate created).

#### 9. Failures Are Bounded and Visible

```bash
# Submit task with invalid instructions (will fail)
RESPONSE="$(
  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    http://localhost:8888/api/agents/coding/execute \
    -d "{
      \"coding_task_id\": \"fail-test-$(date +%s)\",
      \"thread_id\": \"<THREAD_ID>\",
      \"source_message_id\": \"<SOURCE_MSG_ID>\",
      \"attempt_id\": \"fail-attempt-$(date +%s)\",
      \"user_id\": \"local\",
      \"project_id\": null,
      \"adapter_kind\": \"pi_sdk\",
      \"instructions\": \"/bin/false\",
      \"repo_root\": \"/nonexistent\",
      \"context_summary\": null,
      \"permission_policy\": {
        \"allow_shell\": true,
        \"allow_network\": false,
        \"allow_write\": false,
        \"allowed_paths\": [],
        \"max_runtime_seconds\": 10
      }
    }"
)"

echo "$RESPONSE" | jq
FAIL_RUN_ID="$(echo "$RESPONSE" | jq -r '.run_id')"

# Wait for processing
sleep 15

# Check failure state
docker compose exec db psql -U codexify -d Codexify -c "
SELECT run_id, status, error 
FROM agent_runs 
WHERE run_id = '$FAIL_RUN_ID';
"

# Check events
curl -N -sS \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/agents/runs/$FAIL_RUN_ID/events" 2>/dev/null | head -10
```

**Pass criteria:**
- Run status is `failed`
- `error` field contains failure reason
- `task.failed` event published
- Failure is visible in thread as `coding_result` with error content

---

## Success Criteria

All 9 verification targets must pass before this task is marked complete.

**Output:** Updated execution log with live verification results.

---

## Notes

- Use unique `coding_task_id` per run to avoid collisions
- The worker may take 5-15 seconds to process a task
- If worker is not running, start it: `docker compose up -d worker-coding`
- If queue is empty but task not processed, check worker logs for errors