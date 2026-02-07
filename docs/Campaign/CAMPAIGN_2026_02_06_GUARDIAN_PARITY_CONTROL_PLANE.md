# CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

## Campaign Intent

Implement **OpenClaw-like operational breadth** (real-time control plane, scheduling, browser automation, multi-channel messaging) as **native Codexify features** behind the Guardian surface — **no OpenClaw dependency**, only patterns.

### Phases

1. **WebSocket Control Plane (RPC + events)**
2. **Cron / Scheduled Tasks (DB-backed + worker)**
3. **Browser Automation (Playwright + approvals)**
4. **Multi-Channel Messaging (adapter framework + allowlist pairing)**

### Non-Negotiables

* **Security-first always** (auth, rate limits, allowlists, approvals, audit logs)
* **Everything emits events** (so UI/WS can stay reactive)
* **Every privileged action is auditable** (params hashed, reasons captured)
* **No “magic background execution”**: all execution is explicit via workers/queues.

---

## Global Campaign Guardrails (Codex Runner Rules)

**Runner MUST:**

* Start each TASK with **repo recon** (search for existing patterns; do not invent parallel frameworks).
* Prefer reusing:

  * existing auth (`require_api_key` / dependencies)
  * existing event bus (`event_bus.emit_event`, `subscribe_in_memory`)
  * existing db model conventions (SQLAlchemy + Alembic)
* Add tests for:

  * auth bypass attempts
  * rate limit enforcement
  * audit log completeness
* Keep changes per task **reviewable** (avoid mega-diffs; commit boundaries are part of safety).

**Definition of Done (per task):**

* ✅ Code compiles / typechecks
* ✅ Unit + integration tests added/passing
* ✅ DB migrations run on clean DB
* ✅ Minimal docs updated (route/WS usage + env vars)

---

## Implementation Map

### Shared “New Top-Level Modules” (target structure)

* `guardian/ws/*`
* `guardian/cron/*`
* `guardian/browser/*`
* `guardian/channels/*`
* corresponding `guardian/routes/*`
* models + migrations + tests

---

# TASK LIST

## TASK-2026-02-06-001 — Recon + Design Lock

**Goal:** Verify existing patterns + decide *exact integration points* before writing new subsystems.

**Steps:**

* Locate:

  * current auth dependency for API key verification
  * event bus entrypoints + outbox pattern
  * how existing routes register routers / lifespan hooks
  * test harness patterns (TestClient fixtures, db overrides)
* Produce a short “Design Lock” note in the campaign file:

  * where WS router will be registered
  * where scheduler will start
  * where workers live
  * which queue mechanism exists (Redis, etc.)

**Exit Criteria:**

* A concrete integration plan that references real code locations (paths + functions).

---

## TASK-2026-02-06-002 — WebSocket Protocol Types + Auth Handshake

**Goal:** Create WS framing + connection auth that reuses existing API-key verification logic.

**Deliverables:**

* `guardian/ws/protocol.py`:

  * `RPCRequest`, `RPCResponse`, `RPCEvent`
  * message validation + bounded payload size checks
* `guardian/ws/auth.py`:

  * handshake strategy (query param OR first message)
  * reject unauthenticated connection with appropriate close code

**Security:**

* Enforce **max payload size**
* No method dispatch before auth completes

**Tests:**

* unauthenticated connect rejected
* malformed frame rejected
* oversized payload rejected

---

## TASK-2026-02-06-003 — WSConnectionManager + Subscriptions

**Goal:** Central connection registry + pub/sub topics.

**Deliverables:**

* `guardian/ws/manager.py`

  * register/unregister connections
  * topic subscriptions
  * broadcast to subscribers
* wire in an event relay listener using `subscribe_in_memory()`

**Tests:**

* subscribe/unsubscribe correctness
* broadcast routes to correct clients only

---

## TASK-2026-02-06-004 — RPC Method Registry + Initial Methods

**Goal:** Minimal useful RPC surface.

**Deliverables:**

* `guardian/ws/methods.py`

  * `@rpc_method` decorator + registry
  * initial methods:

    * `ping`
    * `subscribe` / `unsubscribe`
    * `health.status`
    * `thread.list`
    * `chat.send` (calls existing chat pipeline rather than duplicating it)

**Security:**

* per-method authorization flags (admin_only / permissions)
* rate-limited invocations (see next task)

**Tests:**

* unknown method returns structured error
* permission-gated method rejects

---

## TASK-2026-02-06-005 — WS Rate Limiting + Idle Timeout

**Goal:** Prevent a single client from turning Guardian into soup.

**Deliverables:**

* `guardian/ws/rate_limiter.py` token bucket (Redis-backed if present; fallback in-memory for dev)
* idle timeout + max connections configurable via env

**Tests:**

* exceeding rate limit blocks calls
* idle timeout disconnects

---

## TASK-2026-02-06-006 — WS Route + Audit Log Migration

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

## TASK-2026-02-06-007 — Cron Data Model + CRUD Routes

**Goal:** DB-backed cron job definitions + run history.

**Deliverables:**

* `guardian/cron/models.py` (Pydantic)
* `guardian/routes/cron.py`

  * POST/GET/PATCH/DELETE jobs
  * trigger endpoint
  * runs listing endpoint
* DB migration:

  * `cron_jobs`
  * `cron_runs`

**Security:**

* enforce URL allowlist for webhook payload type (no localhost/internal by default)

**Tests:**

* CRUD works + auth enforced
* invalid schedule rejected
* allowlist blocks forbidden webhook target

---

## TASK-2026-02-06-008 — Scheduler + Worker Execution

**Goal:** Actual execution path: schedule → enqueue → worker → executor → events.

**Deliverables:**

* `guardian/cron/scheduler.py` (APScheduler-backed)
* `guardian/cron/executor.py` (payload types)
* `guardian/workers/cron_worker.py` (queue consumer)
* events emitted on start/success/failure → visible to WS

**Tests:**

* manual trigger creates cron_run row
* execution updates status + emits event

---

## TASK-2026-02-06-009 — Cron ↔ Task Registry Integration

**Goal:** Cron execution becomes a first-class task type.

**Deliverables:**

* register `CronExecutionTask` in `guardian/tasks/types.py` (or your actual registry file)
* ensure existing queue conventions are used (no parallel queue abstraction)

**Tests:**

* task registry resolves cron task correctly

---

## TASK-2026-02-06-010 — Browser Session Manager (Playwright)

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

## TASK-2026-02-06-011 — Browser Approval Workflow + Audit

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

## TASK-2026-02-06-014 — Initial Adapters (Slack, Discord, Telegram)

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

## Suggested Commit Message Rhythm (per phase)

* `feat(ws): add websocket rpc control plane`
* `feat(cron): add scheduler jobs + worker execution`
* `feat(browser): add playwright sessions + approval workflow`
* `feat(channels): add adapter framework + slack/discord/telegram`

