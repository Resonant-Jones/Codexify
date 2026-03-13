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

# TASK-2026-02-06-014 — Initial Adapters (Slack, Discord, Telegram)

- Task-ID: TASK-2026-02-06-014_initial_adapters_slack_discord_telegram
- Title: Initial adapters (Slack, Discord, Telegram)
- Campaign: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Commit mode: two-phase (Commit A = implementation, Commit B = docs finalize + mapping)

## Objective
Ship 3 “real world” outbound adapters (Slack, Discord, Telegram) using the channel adapter framework introduced in TASK 013.

## Background
We want a practical proof that the channel adapter registry can drive outbound messaging through multiple providers without embedding credentials in plaintext and without hitting real vendor APIs during tests.

## Definition of Done
- `SlackAdapter`, `DiscordAdapter`, `TelegramAdapter` exist and implement the common adapter interface from TASK 013.
- Adapters support a minimal outbound send primitive (e.g. `send_message(...)`), returning a normalized result (success/failed + provider message id if available).
- Credentials are treated as secrets:
  - Read from env or persisted config layer (whatever exists in-repo).
  - Stored encrypted-at-rest if persistence is used.
- Tests:
  - Do not hit real external APIs.
  - Mock the HTTP client layer and assert request construction + response handling.
  - At least one router/service-level test proves “router triggers adapter send” (can be via dependency injection / registry lookup).

## Allowed files (STRICT)
Only edit/create within this list:
- `guardian/channels/adapters/slack.py`
- `guardian/channels/adapters/discord.py`
- `guardian/channels/adapters/telegram.py`
- `guardian/channels/adapters/__init__.py` (if needed for exports)
- `guardian/tests/channels/test_slack_adapter.py`
- `guardian/tests/channels/test_discord_adapter.py`
- `guardian/tests/channels/test_telegram_adapter.py`
- `guardian/tests/channels/test_channel_router_outbound.py` (only if a router/service integration test is needed)

If encryption-at-rest support is missing and must be added, STOP and create a follow-up task (do not expand scope here).

## Dependencies / prereqs
Run these before editing:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall
python -V
pytest --version || true
```

## Command checklist
### 1) Locate the adapter interface + registry (read-only)
```bash
rg -n "class .*Adapter|Protocol\[|ChannelAdapter|adapter" guardian/channels || true
rg -n "register|registry|ADAPTER" guardian/channels || true
```
Expected: you can point to the base interface/type and how adapters are registered/selected.

### 2) Implement adapters (allowed files only)
Implement provider-specific outbound sends:
- Slack: send to channel via Bot token (typical API: `chat.postMessage`).
- Discord: send to channel webhook URL OR bot token message endpoint (choose one; prefer webhook because it’s simplest).
- Telegram: send to chat via bot token (typical API: `sendMessage`).

Constraints:
- Keep each adapter tiny.
- Centralize HTTP calls behind a small internal helper so tests can patch/mimic it.
- Validate required config keys and return a clean error (do not throw raw exceptions to callers).

After edits:
```bash
git status --porcelain -uall
```

### 3) Add focused unit tests per adapter
Create/update tests to cover:
- Missing config → deterministic failure result
- Success response → normalized success
- Non-200 / vendor error body → deterministic failure

Suggested discovery commands:
```bash
rg -n "httpx|requests|aiohttp" guardian/channels guardian/tests || true
rg -n "pytest.*monkeypatch|respx" guardian/tests || true
```

Run adapter tests:
```bash
pytest -q guardian/tests/channels/test_slack_adapter.py -q
pytest -q guardian/tests/channels/test_discord_adapter.py -q
pytest -q guardian/tests/channels/test_telegram_adapter.py -q
```
Expected: all pass locally.

### 4) Router/service-level “outbound send” test (only if needed)
If the repo already has a channel route/service that triggers outbound sends, add ONE integration-style test (still mocked HTTP) to prove the adapter is invoked.

Run:
```bash
pytest -q guardian/tests/channels/test_channel_router_outbound.py -q
```

### 5) Full relevant test sweep
```bash
pytest -q guardian/tests/channels -q
```

## Expected outputs (success signals)
- `git status --porcelain -uall` shows only allowed files changed.
- `pytest -q guardian/tests/channels -q` passes.
- No real network calls were made (tests use mocks).

## Rollback / cleanup
If you need to abort this task:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git restore --staged --worktree -- \
  guardian/channels/adapters/slack.py \
  guardian/channels/adapters/discord.py \
  guardian/channels/adapters/telegram.py \
  guardian/channels/adapters/__init__.py \
  guardian/tests/channels/test_slack_adapter.py \
  guardian/tests/channels/test_discord_adapter.py \
  guardian/tests/channels/test_telegram_adapter.py \
  guardian/tests/channels/test_channel_router_outbound.py

git clean -fd -- guardian/tests/channels || true

git status --porcelain -uall
```

## Commit plan
### Commit A (implementation)
- Message:
  - `TASK-2026-02-06-014_initial_adapters_slack_discord_telegram: add slack/discord/telegram outbound adapters + tests`

Commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  guardian/channels/adapters/slack.py \
  guardian/channels/adapters/discord.py \
  guardian/channels/adapters/telegram.py \
  guardian/channels/adapters/__init__.py \
  guardian/tests/channels/test_slack_adapter.py \
  guardian/tests/channels/test_discord_adapter.py \
  guardian/tests/channels/test_telegram_adapter.py \
  guardian/tests/channels/test_channel_router_outbound.py

git commit --no-verify -m "TASK-2026-02-06-014_initial_adapters_slack_discord_telegram: add slack/discord/telegram outbound adapters + tests"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
- Message:
  - `TASK-2026-02-06-014_initial_adapters_slack_discord_telegram: docs finalize + mapping`

Commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_014_initial_adapters_slack_discord_telegram.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-014_initial_adapters_slack_discord_telegram: docs finalize + mapping"

git log -1 --oneline
```

## Campaign mapping line
Add/update in the campaign file when hashes are known:
- `TASK-2026-02-06-014_initial_adapters_slack_discord_telegram -> [966879e0, 049461bc]`

## Notes / results
### Commands run
- `git status --porcelain -uall`
- `python -V`
- `pytest --version || true`
- `rg -n "class .*Adapter|Protocol\\[|ChannelAdapter|adapter" guardian/channels || true`
- `rg -n "register|registry|ADAPTER" guardian/channels || true`
- `rg -n "httpx|requests|aiohttp" guardian/channels guardian/tests || true`
- `rg -n "pytest.*monkeypatch|respx" guardian/tests || true`
- `pytest -q guardian/tests/channels/test_slack_adapter.py -q`
- `pytest -q guardian/tests/channels/test_discord_adapter.py -q`
- `pytest -q guardian/tests/channels/test_telegram_adapter.py -q`
- `pytest -q guardian/tests/channels/test_channel_router_outbound.py -q`
- `pytest -q guardian/tests/channels -q`

### Key outputs
- Added adapters:
  - `guardian/channels/adapters/slack.py`
  - `guardian/channels/adapters/discord.py`
  - `guardian/channels/adapters/telegram.py`
  - `guardian/channels/adapters/__init__.py`
- Added tests:
  - `guardian/tests/channels/test_slack_adapter.py`
  - `guardian/tests/channels/test_discord_adapter.py`
  - `guardian/tests/channels/test_telegram_adapter.py`
  - `guardian/tests/channels/test_channel_router_outbound.py`
- Test results:
  - adapter tests: pass
  - router outbound test: pass
  - `pytest -q guardian/tests/channels -q`: `10 passed`
- Commit A created: `966879e0`
- Commit B created: `049461bc`

### Deviations
- None.

### Final mapping
- `TASK-2026-02-06-014_initial_adapters_slack_discord_telegram -> [966879e0, 049461bc]`
