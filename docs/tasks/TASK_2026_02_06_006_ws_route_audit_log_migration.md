TASK-2026-02-06-006 — WS Route + Audit Log Migration

**Goal:** Productionize WS endpoint with audit trail.

**Deliverables:**

* `guardian/routes/websocket.py` (FastAPI websocket route)
* DB migration + model:

  * `ws_audit_log`: connection_id, identity, method, params_hash, status, duration_ms, created_at
* ensure router + lifespan hook registration

**Tests:**

* successful call writes audit row
* failed call writes audit row (status=error)

---
