TASK-2026-02-06-011 — Browser Approval Workflow + Audit

**Goal:** Dangerous ops require explicit approval + reasons.

**Deliverables:**

* `guardian/browser/approval.py`
* routes:

  * list approvals
  * approve/deny with reason
* migrations:

  * `browser_approvals`
  * `browser_audit_log`

**Approval required for:**

* `evaluate`
* cookie set/get
* navigation to non-allowlisted domains (if you allow “ask to approve” mode)

**Tests:**

* blocked op creates approval request
* approval transitions enforced (no double-approve)
* audit log always written

---
