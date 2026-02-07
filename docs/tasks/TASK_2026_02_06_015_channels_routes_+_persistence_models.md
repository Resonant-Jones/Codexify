## TASK-2026-02-06-015 — Channels Routes + Persistence Models

**Goal:** Manage configs + store channel message audit trail.

**Deliverables:**

* `guardian/routes/channels.py`
* migrations/models:

  * `channel_configs`
  * `channel_allowlists`
  * `channel_pairings`
  * `channel_messages`

**Tests:**

* config CRUD
* message persistence on inbound/outbound

---
