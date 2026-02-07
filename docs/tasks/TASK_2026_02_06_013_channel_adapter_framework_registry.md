## TASK-2026-02-06-013 — Channel Adapter Framework + Registry

**Goal:** Build the *foundation* for multi-channel messaging without committing to 40 integrations.

**Deliverables:**

* `guardian/channels/base.py` (ABC + shared types)
* `guardian/channels/registry.py`
* `guardian/channels/router.py` (incoming→thread→completion→outgoing)
* `guardian/channels/allowlist.py` (pairing codes, TTL)

**Security:**

* unknown senders rejected or forced into pairing workflow
* pairing codes expire

**Tests:**

* allowlist enforcement works
* pairing flow works end-to-end

---
