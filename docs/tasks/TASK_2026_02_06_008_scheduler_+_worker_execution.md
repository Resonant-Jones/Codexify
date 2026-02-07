TASK-2026-02-06-008 — Scheduler + Worker Execution

**Goal:** Actual execution path: schedule → enqueue → worker → executor → events.

**Deliverables:**

* `guardian/cron/scheduler.py` (APScheduler-backed)
* `guardian/cron/executor.py` (payload types)
* `guardian/workers/cron_worker.py` (queue consumer)
* events emitted on start/success/failure → visible to WS

**Tests:**

* manual trigger creates cron_run row
* execution updates status + emits event

---
