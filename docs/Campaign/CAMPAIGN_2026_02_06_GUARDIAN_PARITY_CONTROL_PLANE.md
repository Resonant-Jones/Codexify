# TASK LIST

## Task artifacts

* **Source of truth:** This campaign file: `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`
* Each TASK has a corresponding artifact file named `TASK_2026_02_06_###_*.md`.
* Task artifacts must reference this campaign (CAMPAIGN-ID / campaign filename) and must not point at other campaigns.
* This campaign doc should **not** embed runnable task templates; it only describes intent/guardrails and enumerates tasks.

---

## TASK-2026-02-06-001 — Recon + Design Lock

**Goal:** Establish design parity targets and lock the architectural approach *before* implementing the WS / cron / browser / channels phases.

**Deliverables:**

* Repo recon notes (what already exists we should reuse):
  * auth patterns (`require_api_key` / dependencies)
  * event bus usage (`event_bus.emit_event`, `subscribe_in_memory`)
  * worker/queue conventions (existing workers, task registry patterns)
  * DB conventions (SQLAlchemy + Alembic patterns)
* A written **Design Lock** section that states:
  * where WebSocket modules/routes live
  * how WS auth handshake is performed
  * how audit logging is enforced for privileged actions
  * how cron scheduling/execution is wired (scheduler → queue/worker → events)
  * how browser approvals + allowlists are enforced
  * how channel adapters + pairing/allowlists are structured
* A concrete “Do / Don’t” list to prevent parallel frameworks.

**Exit Criteria:**

* Task artifacts 002..016 can be implemented without ambiguity about module layout, auth strategy, and audit/event expectations.

### Design Lock (Task 001 Recon Output)

**Auth entrypoints (reuse, do not fork):**
* API key verification lives in `guardian/core/dependencies.py` via `verify_api_key()` and `require_api_key()`.
* App startup hard-fails if `GUARDIAN_API_KEY` is missing in `guardian/guardian_api.py`.
* Route auth should continue to use `Depends(require_api_key)` and/or router-level dependencies.

**Router registration pattern:**
* Central registration is in `guardian/guardian_api.py` under the Router Inclusion block (`app.include_router(...)`).
* New control-plane routers must be registered there; do not add secondary app instances.

**Lifespan and startup wiring:**
* Startup/shutdown wiring is centralized in `guardian/guardian_api.py` via `app_lifespan()` (`@asynccontextmanager`).
* Background worker lifecycle follows the existing `_CONNECTOR_WORKER_STOP` and `_CONNECTOR_WORKER_TASK` pattern in that lifespan function.
* Scheduler baseline exists at `guardian/runtime/tools/scheduler.py` (`scheduler = _GuardianScheduler()` facade).

**Queue/outbox/worker conventions to preserve:**
* Durable/in-memory event fanout is `guardian/core/event_bus.py` (`emit_event()`, `subscribe_in_memory()`, `configure_event_store()`).
* Redis queue primitives are in `guardian/queue/redis_queue.py` (`enqueue()`, `dequeue()`, `enqueue_chat_embed()`).
* Worker entrypoints are module-based under `guardian/workers/` and executed as `python -m guardian.workers.<worker_name>`, mirrored in `docker-compose.yml` services (`worker-chat`, `worker-document-embed`, `worker-chat-embed`, etc.).
* Existing typed task registry is `guardian/tasks/types.py` (`TASK_TYPE_REGISTRY`, `task_from_dict`); extend this instead of creating a second registry.

**Audit expectations for privileged paths:**
* Existing audit trail writers are used directly in routes and workers (`chatlog_db.write_audit_log(...)`) and modeled in `guardian/db/models.py` (`AuditLog`, `CollaborationAuditLog`).
* Existing websocket/audit behavior exists in `guardian/realtime/collaboration.py`; new control-plane websocket flows should follow the same "authorize -> audit -> emit" ordering.

**WebSocket/Cron/Browser/Channels module layout lock:**
* Keep planned control-plane modules in dedicated namespaces:
  * WS: `guardian/ws/*` plus route at `guardian/routes/websocket.py`.
  * Cron: `guardian/cron/*` plus route at `guardian/routes/cron.py`.
  * Browser: `guardian/browser/*` plus route at `guardian/routes/browser.py`.
  * Channels: `guardian/channels/*` plus route at `guardian/routes/channels.py`.
* No conflicting files currently exist under `guardian/ws`, `guardian/cron`, `guardian/browser`, or `guardian/channels`; this avoids collisions with legacy modules.

**Do / Don't guardrails:**
* Do reuse: `require_api_key`, `app_lifespan`, `event_bus.emit_event/subscribe_in_memory`, `redis_queue.enqueue/dequeue`, and `TASK_TYPE_REGISTRY`.
* Do place all new router registration in `guardian/guardian_api.py`.
* Don't add a parallel auth dependency implementation for websocket/cron/browser/channels.
* Don't introduce a second scheduler abstraction when `guardian/runtime/tools/scheduler.py` can be wrapped.
* Don't bypass queue/event contracts with ad hoc background threads outside lifespan ownership.

**Mapping placeholder:**
* `TASK-2026-02-06-001_recon_+_design_lock -> [<commit>, n/a]`

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

**Mapping:**

* `TASK-2026-02-06-002_websocket_protocol_types_and_auth_handshake -> [bef02d9c, 3dd76be1]`

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

**Mapping:**

* `TASK-2026-02-06-003_wsconnectionmanager_subscriptions -> [6f7f2404, f2452481]`

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

**Mapping:**

* `TASK-2026-02-06-004_rpc_method_registry_+_initial_methods -> [39f6140e, f70968ea]`

---

## TASK-2026-02-06-005 — WS Rate Limiting + Idle Timeout

**Goal:** Prevent a single client from turning Guardian into soup.

**Deliverables:**

* `guardian/ws/rate_limiter.py` token bucket (Redis-backed if present; fallback in-memory for dev)
* idle timeout + max connections configurable via env

**Tests:**

* exceeding rate limit blocks calls
* idle timeout disconnects

**Mapping:**

* `TASK-2026-02-06-005_ws_rate_limiting_+_idle_timeout -> [f22b1165, d42bf74d]`

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

**Mapping:**

* `TASK-2026-02-06-006_ws_route_audit_log_migration -> [55cf078d, d55fc7c9]`

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

**Mapping:**

* `TASK-2026-02-06-007_cron_data_model_crud_routes -> [46aed0cf, 0b163be1]`

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

**Mapping:**

* `TASK-2026-02-06-008_scheduler_worker_execution -> [dacffa97, 663ba791]`

---

## TASK-2026-02-06-009 — Cron ↔ Task Registry Integration

**Goal:** Cron execution becomes a first-class task type.

**Deliverables:**

* register `CronExecutionTask` in `guardian/tasks/types.py` (or your actual registry file)
* ensure existing queue conventions are used (no parallel queue abstraction)

**Tests:**

* task registry resolves cron task correctly

**Mapping:**

* `TASK-2026-02-06-009_cron_to_task_registry_integration -> [dea42fdc, d3418591]`

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

**Mapping:**

* `TASK-2026-02-06-010_browser_session_manager_playwright -> [78b83ad1, d2814e97]`

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

**Mapping:**

* `TASK-2026-02-06-011_browser_approval_workflow_audit -> [5e486996, 04fa84ca]`

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

**Mapping:**

* `TASK-2026-02-06-012_browser_routes_ws_hooks -> [4b32590b, 42e546d6]`

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
