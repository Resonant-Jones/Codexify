# TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout

## Metadata
- Task-ID: TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Branch: campaign/2026-02-06/guardian-parity-control-plane
- Task artifact: docs/work/tasks/2026/02/TASK_2026_02_06_005_ws_rate_limiting_idle_timeout.md
- Owner: resonant_jones
- Risk: MED
- Commit mode: two-phase

## Objective
Introduce websocket rate limiting and an idle timeout so a single client can’t exhaust Guardian resources, with safe defaults and clear configurability via env.

## Scope
### In-scope
- Add a small, testable WS rate limiter (token-bucket style).
- Add idle timeout enforcement and configurable max connections.
- Prefer Redis-backed state when available; fall back to in-memory for dev.
- Add/adjust tests that prove:
  - Exceeding the rate limit blocks further calls.
  - Idle timeout disconnects.

### Out-of-scope
- Refactors unrelated to WS admission/rate limiting/timeout.
- New product features beyond limiting/timeout.
- Changes to unrelated authentication or routing.

## Allowed files (STRICT)
> Do not modify files outside this list.

- guardian/ws/rate_limiter.py
- guardian/ws/router.py
- guardian/ws/__init__.py
- guardian/core/config.py
- tests/realtime/test_ws_rate_limit.py
- tests/realtime/test_ws_idle_timeout.py
- docs/work/tasks/2026/02/TASK_2026_02_06_005_ws_rate_limiting_idle_timeout.md
- docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

## Dependencies / Prereqs (NO GUESSING)
Run these to confirm environment and locate the WS entrypoint(s):

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# required: clean tree before starting
git status --porcelain -uall

# locate WS server/handlers
rg -n "websocket|WebSocket|/ws" guardian/ws guardian/routes guardian/core -S

# confirm test runner
python -V
python -m pytest --version || true
```

## Command checklist (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) locate WS code paths + current limits (if any)
rg -n "rate|limit|token bucket|idle|timeout|max_connections" guardian/ws guardian/core -S

# 2) implement within allowed files only
#    - add token bucket limiter
#    - add idle timeout
#    - add env wiring and defaults

# 3) run focused tests (add files if they don’t exist yet; keep within allowed list)
python -m pytest -q tests/realtime/test_ws_rate_limit.py -q || true
python -m pytest -q tests/realtime/test_ws_idle_timeout.py -q || true

# 4) run broader suite if fast enough
python -m pytest -q tests/realtime -q || true

# 5) confirm only allowed files changed
git status --porcelain -uall
```

## Expected results (success signals)
- WS layer enforces a configurable rate limit per client (or per connection) with clear rejection behavior.
- WS layer disconnects idle connections after a configurable timeout.
- Defaults are safe for local dev and do not require Redis.
- If Redis is configured/available, limiter state uses Redis; otherwise uses in-memory without crashing.
- Tests demonstrate rate limit + idle timeout behavior (or are explicitly skipped with a documented, deterministic reason).

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard local changes to this task’s allowed files only (use carefully)
git restore -- guardian/ws/rate_limiter.py guardian/ws/router.py guardian/ws/__init__.py guardian/core/config.py tests/realtime/test_ws_rate_limit.py tests/realtime/test_ws_idle_timeout.py docs/work/tasks/2026/02/TASK_2026_02_06_005_ws_rate_limiting_idle_timeout.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git status --porcelain -uall
```

## Commit plan (MANUAL; index.lock workaround)
### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout: ws rate limit + idle timeout`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage ONLY implementation + tests (no campaign/task doc mapping updates yet)
git add \
  guardian/ws/rate_limiter.py \
  guardian/ws/router.py \
  guardian/ws/__init__.py \
  guardian/core/config.py \
  tests/realtime/test_ws_rate_limit.py \
  tests/realtime/test_ws_idle_timeout.py

git commit --no-verify -m "TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout: ws rate limit + idle timeout"

git log -1 --oneline

git status --porcelain -uall
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout: docs finalize + mapping`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage ONLY task artifact + campaign mapping
git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_005_ws_rate_limiting_idle_timeout.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
- TASK mapping (fill after commits):
  - TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout -> [f22b1165, d42bf74d]

## Notes
- WS entrypoint for this campaign is `guardian/ws/router.py`.

## Summary (fill after completion)
- What changed:
  - Added `guardian/ws/rate_limiter.py` implementing a token-bucket limiter with Redis-first state and automatic in-memory fallback.
  - Updated `guardian/ws/router.py` to enforce:
    - max concurrent connection gate,
    - per-identity request rate limiting with structured `rate_limited` errors,
    - idle timeout disconnect using `asyncio.wait_for`.
  - Added WS runtime settings in `guardian/core/config.py`:
    - `WS_RPC_RATE_LIMIT_CAPACITY`
    - `WS_RPC_RATE_LIMIT_REFILL_PER_SECOND`
    - `WS_RPC_RATE_LIMIT_NAMESPACE`
    - `WS_RPC_IDLE_TIMEOUT_SECONDS`
    - `WS_RPC_MAX_CONNECTIONS`
  - Updated WS exports in `guardian/ws/__init__.py`.
  - Added focused tests:
    - `tests/realtime/test_ws_rate_limit.py`
    - `tests/realtime/test_ws_idle_timeout.py`
- Commands run + outputs:
  - `python -m pytest -q tests/realtime/test_ws_rate_limit.py -q || true` -> `/opt/homebrew/opt/python@3.13/bin/python3.13: No module named pytest`
  - `python -m pytest -q tests/realtime/test_ws_idle_timeout.py -q || true` -> `/opt/homebrew/opt/python@3.13/bin/python3.13: No module named pytest`
  - `pytest -q tests/realtime/test_ws_rate_limit.py` -> pass
  - `pytest -q tests/realtime/test_ws_idle_timeout.py` -> pass
  - `pytest -q tests/realtime` -> pass with expected skips
  - `pytest -q tests/realtime/test_websocket_auth_handshake.py tests/realtime/test_websocket_protocol_validation.py tests/realtime/test_websocket_rpc_methods.py tests/realtime/test_ws_manager.py tests/realtime/test_ws_rate_limit.py tests/realtime/test_ws_idle_timeout.py` -> pass (13 tests)
- Final mapping:
  - TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout -> [f22b1165, d42bf74d]
