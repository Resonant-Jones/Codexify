## TASK-2026-02-06-016 — End-to-End Verification Script + Docs

**Goal:** Prove the whole stack works as a system.

**Deliverables:**

* minimal `docs/guardian/control-plane.md`

  * WS connect/auth example
  * cron job examples
  * browser approvals lifecycle
  * channels pairing flow
  * env vars list
* E2E verification checklist:

  * WS connect → subscribe → receive cron events
  * create cron job → run → see ws event
  * create browser session → approval required op → approve → proceed
  * configure channel → inbound message → response routed back

**Exit Criteria:**

* Full `pytest` green
* Alembic upgrade head works on clean DB
* A human can follow the docs and reproduce the flow

---
