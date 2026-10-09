# Accepted-chat outbox lock deadline proof — 2026-10-04

## Scope and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF mode. This atomic Task
checks the production `PgDB.append_event` path under a native PostgreSQL table
lock in the retained supported-Compose worker. It changes no production code,
runtime configuration, migration, queue, deadline policy or release claim.

Governing sources: ADR-087 (child deadlines, PostgreSQL inside the envelope and
terminal reserve), ADR-001/002/003/038/069, the Chat Runtime Contract and
Completion Pipeline. This proof is aligned with those accepted contracts; no
new ADR is required. Full supported-path qualification remains **HOLD**.

The clean repair branch began at `9c1bff5257d9f00ca3fcd3e91c667ce892d9b517`.
Main was independently observed at `0163521312ef767c0884654e70094ae7b44a5eec`
with an unrelated staged Dev Log deletion. Both main and its deletion remained
untouched. No fetch, merge, push or deployment occurred in this Task.

## Runtime and evidence custody

Evidence root:
`/private/tmp/codexify-chat-outbox-lock-9c1bff525-20261004/`.

The Task Spec was saved before probe execution. Artifacts include `probe.py`,
`driver.py`, `validate.py`, stdout/stderr, process exit, result, pre/post health
and queue observations, the source matrix and independent validation.
The native probe ran through `docker exec -i` and created no container files.

Retained Compose project: `codexify_chat_branch_proof_896387ad2`.
The worker uses Python 3.11 and psycopg 3.3.6. Before execution and after cleanup,
all **1,136** tracked Guardian/backend Python files matched the repair checkout,
retained source snapshot, backend container and worker container. There was no
source refresh or restart.

## Native operation and result

The production adapter creates its normal SQLAlchemy engine/session and uses
`append_event`, including its native commit/rollback path. A private psycopg
connection holds `ACCESS EXCLUSIVE` on the existing `events_outbox` table. Its
acquisition has a three-second PostgreSQL statement/lock ceiling. The probe
keeps that lock held while checking the operation's deadline result, then
rolls back and closes the locker before proceeding.

Each valid immutable 720-second work / 60-second terminal envelope was aged to
approximately 0.30 seconds remaining in the tested phase. This changes neither
policy nor the envelope interval. It is a controlled native adapter proof,
not a new application acceptance or a complete chat-turn proof.

| Phase | Elapsed seconds | Canonical result | Lock still held | Owned active waiters |
| --- | --- | --- | --- | --- |
| Work | 0.305316 | `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` | true | 0 |
| Terminal | 0.304085 | `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` | true | 0 |

The exception messages distinguish work and terminal expiry. Both attempts
returned before the locker was released. The unique inert proof tenant
`outbox_bound_be00d8351d524d49b15ad8ecfa5246e0` had zero outbox rows afterward.
No event was published through the application's event bus or subscriber hub.
The private engine was disposed; its labelled connections and locker
connections were absent. A subsequent unscoped production outbox read succeeded.

The first probe exited 1 before creating its adapter or acquiring a lock:
`make_conninfo` produced a libpq string where the adapter requires a SQLAlchemy
URL. The fixture was corrected to preserve URL form. Its source, stderr,
stdout and process result remain under `initial-*`. Preflight state/health and
source matrix were refreshed for the corrected execution; those files describe
the successful execution, not a timestamped record of the initial fixture run.

## Independent validation and retained state

The corrected probe/driver exited **0**. The independent validator exited **0**
and checked result thresholds, canonical failure code, absent owned rows and
connections, source equivalence and retained application state.

Chat queue remained zero, turn locks empty and heartbeat fresh idle with positive
TTL. Evaluation/system queues remained **31/11**; neither was dequeued or cleared.
General health remained `ok`. Thread 34 still contained exact user/assistant
messages **64/65**, including `CHAT_INDEPENDENT_HEARTBEAT_SUCCESS_20261004`.
No assistant, completion attempt or application request was created by this probe.

Commands executed:

- `python3 /private/tmp/codexify-chat-outbox-lock-9c1bff525-20261004/driver.py` — corrected run passed; initial fixture failure retained.
- `python3 /private/tmp/codexify-chat-outbox-lock-9c1bff525-20261004/validate.py` — passed.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No automated application runtime regression suite applies to this docs-only
receipt. The live native adapter proof above is the tested surface.

## Limits and next obligation

This closes the held native outbox-table-lock observation for the tested work
and terminal paths. It does not prove remote commit acknowledgement under a
lost network response, all terminal-reserve exhaustion cases, subscriber/UI
receipt, embedding/vector context bounds, worker loss recovery or current-main
restart/shutdown qualification. Context work remains the next bounded census
and proof obligation; the Goal stays active.
