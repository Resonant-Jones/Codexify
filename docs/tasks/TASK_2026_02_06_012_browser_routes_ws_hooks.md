## TASK-2026-02-06-012 — Browser Routes + WS Hooks

**Goal:** REST + WS interop (approvals & status broadcast).

**Deliverables:**

* `guardian/routes/browser.py` endpoints
* WS events:

  * `browser.approval.requested`
  * `browser.approval.decided`
  * `browser.session.updated`

**Tests:**

* event emission on approval requested/decided

---
