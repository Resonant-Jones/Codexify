TASK-2026-02-06-007 — Cron Data Model + CRUD Routes

**Goal:** DB-backed cron job definitions + run history.

**Deliverables:**

* `guardian/cron/models.py` (Pydantic)
* `guardian/routes/cron.py`

  * POST/GET/PATCH/DELETE jobs
  * trigger endpoint
  * runs listing endpoint
* DB migration:

  * `cron_jobs`
  * `cron_runs`

**Security:**

* enforce URL allowlist for webhook payload type (no localhost/internal by default)

**Tests:**

* CRUD works + auth enforced
* invalid schedule rejected
* allowlist blocks forbidden webhook target

---
