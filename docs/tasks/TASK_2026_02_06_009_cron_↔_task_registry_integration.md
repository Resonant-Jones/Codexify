TASK-2026-02-06-009 — Cron ↔ Task Registry Integration

**Goal:** Cron execution becomes a first-class task type.

**Deliverables:**

* register `CronExecutionTask` in `guardian/tasks/types.py` (or your actual registry file)
* ensure existing queue conventions are used (no parallel queue abstraction)

**Tests:**

* task registry resolves cron task correctly

---
