TASK-2026-02-06-010 — Browser Session Manager (Playwright)

**Goal:** Controlled browser contexts with persisted profiles.

**Deliverables:**

* `guardian/browser/session_manager.py`

  * create/get/list/close sessions
  * profile dirs under `STORAGE_BASE_PATH/browser_profiles/`
* minimal `guardian/browser/cdp_bridge.py` abstraction:

  * navigate, screenshot, click, type, content

**Security:**

* URL allowlist config
* max concurrent sessions
* per-session TTL

**Tests:**

* session lifecycle
* allowlist blocks forbidden domains

---
