TASK-2026-02-06-014 — Initial Adapters (Slack, Discord, Telegram)

**Goal:** Ship 3 “real world” adapters.

**Deliverables:**

* `guardian/channels/adapters/slack.py`
* `guardian/channels/adapters/discord.py`
* `guardian/channels/adapters/telegram.py`

**Constraints:**

* credentials stored encrypted-at-rest (whatever your repo supports; if not present, add app-level encryption wrapper now)

**Tests:**

* adapter stubs mocked in tests (don’t hit real APIs)
* router sends outbound response via adapter

---
