# 🔧 UI-Backend Wiring Roadmap & Polish Tasks

## ✅ Completed Foundations

### Chat System
- ✅ Thread creation (`/api/chat/threads`)
- ✅ Message posting (`/api/chat/{thread_id}/messages`)
- ✅ Thread listing (`/api/chat/threads`)
- ✅ Thread updates (rename, assign to project, delete)
- ✅ Message listing and deletion
- ✅ Cross-browser sidebar layout fixes
- ✅ "Loose Threads" project auto-assignment
- ✅ Thread/project toggle positioning fixes

### Connectors System
- ✅ Connector listing (`/api/connectors`)
- ✅ Connector configuration (`/api/connectors/{id}/config`)
- ✅ OAuth authorization flow (`/api/connectors/{id}/authorize`)
- ✅ Connection testing (`/api/connectors/{id}/test`)
- ✅ Manual sync (`/api/connectors/{id}/sync`)
- ✅ GitHub OAuth callback handling

### Memory System
- ✅ Memory entry CRUD operations (`/api/memory/{silo}`)
- ✅ Search functionality (`/search`)
- ✅ History retrieval (`/history`)
- ✅ Chat log history v2 (`/history/v2`)

### Projects
- ✅ Project creation (`/projects`)
- ✅ Project listing (`/projects`)
- ✅ Project deletion (`/projects/{id}`)
- ✅ Thread-to-project assignment

## 🔧 In Progress / Partial

### Thread Management
- Thread lineage/parent-child relationships exist in backend but limited UI integration
- Thread summaries are stored but not prominently displayed in UI

### Connector Features
- Connector sync intervals configured but no background sync jobs
- Connector health monitoring exists but no real-time status updates

## 🚨 High Priority (Phase 1)

### 1. Real-time Data Sync
- [ ] Implement WebSocket/SSE connections for live updates
- [ ] Add connector status change notifications
- [ ] Enable real-time thread updates for multiple users
- [ ] Add typing indicators and presence detection

### 2. Background Connector Processing
- [ ] Wire up background sync job scheduling
- [ ] Implement connector data ingestion pipelines
- [ ] Add connector error handling and recovery systems
- [ ] Create connector health monitoring dashboard

### 3. Advanced Thread Features
- [ ] Complete thread branching/merging UI integration
- [ ] Wire thread templates/presets to backend
- [ ] Implement thread archiving/hiding functionality
- [ ] Add thread sharing and collaboration features

### 4. Memory System Integration
- [ ] Connect memory entries to chat context
- [ ] Add memory-based suggestions in composer
- [ ] Integrate memory search into main UI
- [ ] Implement memory-driven conversation insights

## 🎯 Medium Priority (Phase 2)

### 5. Project Management Completion
- [ ] Complete project details editing UI
- [ ] Implement project-based thread filtering
- [ ] Add project collaboration features
- [ ] Create project analytics and insights

### 6. User Management
- [ ] Complete user profile integration
- [ ] Implement multi-user thread sharing
- [ ] Add user preferences/settings sync
- [ ] Create user activity tracking

### 7. File/Document Integration
- [ ] Wire document upload to backend
- [ ] Connect file processing pipelines
- [ ] Integrate document search into UI
- [ ] Add file attachment handling in chat

## 📝 Low Priority (Phase 3 / Polish)

### 8. Analytics & Monitoring
- [ ] Implement usage analytics collection
- [ ] Add performance monitoring integration
- [ ] Create error tracking/reporting system
- [ ] Add conversation analytics dashboard

### 9. Advanced Features
- [ ] Add advanced connector features (webhooks, etc.)
- [ ] Implement multi-user real-time collaboration
- [ ] Create advanced search capabilities
- [ ] Add AI-powered conversation insights

### 10. Performance & Polish
- [ ] Optimize database queries for large datasets
- [ ] Implement caching strategies
- [ ] Add loading states and error boundaries
- [ ] Create comprehensive error handling

## 🧪 Testing Requirements

- Cross-browser compatibility (Safari, Chrome, Firefox, Edge)
- Tauri desktop app compatibility
- Mobile responsive testing
- Performance testing with large datasets
- Real-time connection stability testing

## 📊 Success Metrics

- Zero UI-backend connection failures
- Sub-100ms response times for chat operations
- Real-time updates within 500ms
- 99.9% uptime for background processing
- Cross-browser layout consistency

This roadmap prioritizes user-facing functionality while ensuring robust backend integration and real-time capabilities.

---

## 📜 PRD — Final MVP Cut for **Guardian Backend v2** + Codexify (v2)

**Doc owner:** Axis (with Resonant Jones)  
**Date:** 2025‑09‑17  
**Status:** Implementable spec  
**Objective:** Provide an execution‑ready specification for the final phase before MVP. This PRD supersedes ad‑hoc notes and binds backend, frontend, and ops to a single source of truth.

### ✅ MVP Exit Criteria (single‑screen view)
- Real‑time updates delivered via **SSE** with resume (Last‑Event‑ID) across UI surfaces (threads, connectors, jobs, file processing, composer hints).
- **GitHub connector** ingests Issues, PRs, and Commits for selected repos on a schedule and on demand; health states visible in UI.
- **Thread lineage** (branch, merge, archive) implemented; summaries presented in list and detail views and are refreshable.
- **Memory integration**: pin to context, show top‑3 composer suggestions, and render a lightweight insights panel.
- **Files**: upload → async process → searchable; attachments render in chat.
- **Observability + SLOs**: metrics, logs, traces in place; runbooks written; SLOs met for a 72‑hour canary.

---

## 1) Scope & Personas

### In Scope
- SSE realtime channel with outbox + replay.
- GitHub OAuth connector (account selection → repo selection → scheduled sync → health → job list → manual Sync Now).
- Thread lineage (branch/merge/archive) + summary surfacing.
- Memory attach + composer suggestions + insights.
- Project filter, basic share (unlisted link; simple ACL: Owner/Editor/Viewer).
- File upload/processing integration with search.
- Observability: metrics, dashboards, error tracking.

### Out of Scope (post‑MVP)
- GitHub Webhooks; migration to GitHub App; fine‑grained org RBAC; enterprise SSO; multi‑cursor editing; heavy analytics.

### Personas
- **Builder (RJ)**: primary; needs fresh GitHub context and memory suggestions inline.
- **Collaborator**: can view, comment (message), and follow updates; may trigger sync.

---

## 2) Architecture & Data Model

### 2.1 Realtime (SSE)
- **Endpoint:** `GET /api/events` → `text/event-stream` with `retry: 3000` on open.
- **Auth:** same auth as existing API (cookie/bearer). Read‑only.
- **Outbox table:** `events_outbox(id BIGSERIAL, topic TEXT, payload JSONB, created_at TIMESTAMPTZ DEFAULT now(), sent_at TIMESTAMPTZ NULL)`.
- **Resume:** clients send `Last-Event-ID`; server replays where `id > last`.
- **Coalescing:** for high‑freq topics, publish `*.summary` events at most once per 2s.

### 2.2 Background Jobs
- **Queue types:** `github.list`, `github.sync.issues`, `github.sync.prs`, `github.sync.commits`, `connector.health`, `file.process`, `memory.index`.
- **State:** `PENDING → RUNNING → SUCCESS|ERROR|DEGRADED`, with `attempt`, `next_run_at` for backoff.
- **Idempotency:** job key on `(connector_id, type, repo, cursor_hash)`; drop duplicates during window.

### 2.3 Proposed Tables (DDL‑ish)
```sql
-- Threads
ALTER TABLE threads ADD COLUMN parent_id UUID NULL;
ALTER TABLE threads ADD COLUMN lineage_path TEXT; -- e.g., '/root/<uuid>/<uuid>'
ALTER TABLE threads ADD COLUMN is_archived BOOLEAN DEFAULT false;
ALTER TABLE threads ADD COLUMN visibility TEXT DEFAULT 'private'; -- 'private'|'unlisted'
ALTER TABLE threads ADD COLUMN summary TEXT;

CREATE TABLE thread_merges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_thread_id UUID NOT NULL,
  target_thread_id UUID NOT NULL,
  merged_by UUID NOT NULL,
  merged_at TIMESTAMPTZ DEFAULT now(),
  note TEXT
);

-- Connectors + Jobs + Health
CREATE TABLE connector_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL, -- 'github'
  display_name TEXT,
  avatar_url TEXT
);

CREATE TABLE connector_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE,
  scopes TEXT[],
  settings JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE connector_status_history (
  id BIGSERIAL PRIMARY KEY,
  connector_id UUID NOT NULL,
  status TEXT NOT NULL, -- OK|DEGRADED|ERROR|SYNCING
  message TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connector_id UUID NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error TEXT,
  attempt INT DEFAULT 0,
  cursor JSONB
);

CREATE TABLE events_outbox (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  sent_at TIMESTAMPTZ
);

-- GitHub entities for search/use in composer
CREATE TABLE github_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL, -- issue|pull|commit
  external_id TEXT NOT NULL, -- issue id / pr id / sha
  repo TEXT NOT NULL,
  title TEXT,
  body TEXT,
  state TEXT,
  author TEXT,
  labels JSONB,
  created_at_ts TIMESTAMPTZ,
  updated_at_ts TIMESTAMPTZ,
  synced_at TIMESTAMPTZ
);
CREATE INDEX ON github_entities (repo, entity_type);
CREATE INDEX ON github_entities USING GIN (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,'')));
```

---

## 3) Functional Requirements & AC

### 3.1 Realtime
- **FR‑RT‑01** `GET /api/events` streams events within 1s of connect; heartbeat every 15s.
- **FR‑RT‑02** Resume with `Last-Event-ID` after brief network loss without losing domain events.
- **FR‑RT‑03** Event Catalog:
  - `connector.status` {connector_id, status, message, at}
  - `connector.job` {job_id, type, status, at}
  - `thread.updated` {thread_id, fields_changed[]}
  - `message.created` {thread_id, message_id}
  - `memory.suggestion` {thread_id, suggestions:[id,...]}
  - `file.processed` {file_id, status}
- **FR‑RT‑04** Typing indicators (soft‑MVP): POST `/api/presence/typing` → broadcast `thread.typing`.

### 3.2 GitHub Connector
- **FR‑GH‑01** Connect account, show scopes; select repos; persist config.
- **FR‑GH‑02** Background sync every 5m ± jitter; manual `Sync Now` path.
- **FR‑GH‑03** Ingest resources:
  - Issues: `GET /repos/{owner}/{repo}/issues?state=all&since=<ts>` (exclude PRs via `pull_request` key), paginate `Link`.
  - PRs: `GET /repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=100&page=n` + `GET /repos/{owner}/{repo}/pulls/{number}` for body if needed.
  - Commits: `GET /repos/{owner}/{repo}/commits?since=<ts>&per_page=100&page=n`.
- **FR‑GH‑04** Cursors & idempotency: store `since` timestamps per resource; use ETags where available; dedupe on `external_id`.
- **FR‑GH‑05** Rate limits: detect remaining; backoff; surface `DEGRADED`.
- **FR‑GH‑06** Health UI: status pill; last sync; items changed; error messages.
- **FR‑GH‑07** Composer surfacing: for active project/thread, show top‑3 relevant artifacts (issue/pr/commit) ranked by recency + keyword match + author/project match.

### 3.3 Threads & Summaries
- **FR‑TL‑01** Branch from message; **AC:** new thread created with linkback, lineage updated.
- **FR‑TL‑02** Merge source→target; **AC:** `thread_merges` row + system note in both.
- **FR‑TL‑03** Archive/unarchive; **AC:** default list hides archived.
- **FR‑TL‑04** Summaries shown in list and header; refresh regenerates and updates timestamp.

### 3.4 Memory
- **FR‑MM‑01** Pin/unpin memories to thread context.
- **FR‑MM‑02** Composer shows top‑3 suggestions (based on last 20 messages + project tags + simple TF‑IDF over memory titles/bodies; tie‑break by recency).
- **FR‑MM‑03** Insights panel with 1–2 auto‑extracted bullets; “Add to memory” one‑click.

### 3.5 Files
- **FR‑FD‑01** Upload PDF/MD/TXT ≤ 25MB; background parse; on complete emit `file.processed`.
- **FR‑FD‑02** Search returns snippet and link; attach chip displayed in message bubble.

---

## 4) API Contracts (additions only)

### 4.1 Realtime
`GET /api/events` → SSE with lines of `id`, optional `event`, and `data` (JSON string).

### 4.2 Connectors
- `POST /api/connectors/{id}/sync` → `202 Accepted` enqueues job.
- `GET /api/connectors/{id}/status` → current + last 10 transitions.
- `GET /api/connectors/{id}/jobs?page&limit` → list jobs (sorted desc by started_at).
- `GET /api/connectors/{id}/repos` → list repos accessible to token.
- `PUT /api/connectors/{id}/config` → `{ repos: string[], settings?: {} }`.

### 4.3 Threads
- `POST /api/chat/threads/{id}/branch` → `{ from_message_id?: string }`.
- `POST /api/chat/threads/merge` → `{ target_thread_id, source_thread_ids: string[], note?: string }`.
- `POST /api/chat/threads/{id}/archive` / `/unarchive`.
- `PUT /api/chat/threads/{id}/summary` → `{ summary: string }`.

---

## 5) Observability, SLOs, and Error Taxonomy

### Metrics (Prometheus names)
- `guardian_sse_active_connections` gauge
- `guardian_sse_delivery_lag_ms` histogram
- `guardian_jobs_inflight` gauge; `guardian_jobs_success_total`; `guardian_jobs_failed_total`
- `guardian_github_rate_remaining` gauge
- `guardian_sync_items_total{type}` counter
- `guardian_composer_suggestion_latency_ms` histogram

### Logs
- JSON with `trace_id`, `span_id`, `job_id`, `connector_id`. Redact tokens and emails.

### Traces
- Wrap external API calls and DB writes; propagate `trace_id` to UI via response header for debugging.

### Error taxonomy
- `AUTH_*`, `RATE_LIMIT_*`, `REMOTE_5XX`, `PARSE_*`, `DB_*`, `TIMEOUT_*` with human hints.

### SLOs
- Chat ops p50 ≤ 120ms; realtime delivery ≤ 500ms; background sync completes ≤ 90s per repo per cycle.

---

## 6) Configuration & Flags

### Env
- `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
- `ENCRYPTION_KEY` (AES‑GCM 256)
- `JOB_SCHEDULER_CONCURRENCY` (default 4)
- `SSE_MAX_QUEUE` (per user; default 100 events)

### Feature Flags
- `ff_sse_enabled`, `ff_connector_github_enabled`, `ff_composer_suggestions`, `ff_lineage_enabled`.

---

## 7) Security & Privacy
- Minimal GitHub scopes (`repo` if private repos, `read:org` as needed). Display scopes in UI and document rationale.
- Encrypt tokens at rest; rotate on demand; redact in logs.
- Respect `X‑RateLimit‑Remaining`; adaptive backoff; surface `DEGRADED`.
- Data retention: status history 30d, jobs 90d, outbox 24h.

---

## 8) Test Plan

### Unit
- Cursor math; job idempotency; lineage path invariants; summary refresh hooks.

### Integration
- SSE reconnect and replay via `Last-Event-ID` across server restarts.
- GitHub sync on a seeded test repo with simulated rate‑limit.
- File upload → process → search snippet returns.

### UX/Manual
- Branch/merge/archive flows; summaries visible and editable.
- Composer shows top‑3 memories and top‑3 GitHub artifacts.
- Connectors dashboard shows job progress and surfaces errors.

---

## 9) Rollout & Migrations

### Migration Order
1) Extend `threads` (parent, lineage_path, is_archived, visibility, summary).
2) Create `thread_merges`.
3) Create `connector_*`, `sync_jobs`, `events_outbox`, `github_entities`.
4) Backfill lineage paths for existing threads `('/root/' || id)`.

### Deployment Steps
- Apply migrations → deploy backend with flags off → warm queue → enable SSE → enable connector sync → turn on composer suggestions.

---

## 10) Work Plan
- **Sprint 1**: SSE + outbox + client plumbing.
- **Sprint 2**: GitHub ingest + jobs + health + UI dashboard.
- **Sprint 3**: Lineage + summaries.
- **Sprint 4**: Memory + composer.
- **Sprint 5**: Files + ops hardening.

---

## 11) Runbooks (abridged)
- **Connector Error `AUTH_401`**: prompt re‑auth; retain repo list; backoff 15m; downgrade to `ERROR`.
- **Rate Limit**: write `DEGRADED`; set `next_run_at` to reset time; notify via SSE banner.
- **Stuck Jobs**: watchdog marks `RUNNING` > 10m as `ERROR` with hint; emit `connector.status`.
- **Outbox Bloat**: daily compaction for events older than 24h; confirm no `Last-Event-ID` references.

---

## 12) Definition of Done (one list)
- [ ] SSE online with resume + catalog; UI handlers wired.
- [ ] GitHub connector syncing issues/prs/commits; health visible; manual sync works.
- [ ] Branch/Merge/Archive usable; lineage view renders; summaries visible in list & header.
- [ ] Composer suggestions + memory pinning + insights toggle.
- [ ] File upload→process→search integrates with chat.
- [ ] Metrics dashboards + error tracking + runbooks checked in.
- [ ] Test plan green; SLOs met for 72h canary.

---

## Appendix A: Example SSE Frame
```text
id: 102938
event: connector.status
data: {"connector_id":"gh_123","status":"SYNCING","message":"Fetching prs","at":"2025-09-17T12:00:00Z"}
```

## Appendix B: Example Job JSON
```json
{"type":"github.sync.issues","connector_id":"gh_123","repo":"resonant/guardian-backend","cursor":{"since":"2025-09-16T00:00:00Z","etag":"\"abc123\""}}
```

## Appendix C: UI States (empty/error)
- **Connectors dashboard**: when no repos selected → prompt to select. On `ERROR` state → show re‑auth button and last error message.
- **Threads list**: empty → friendly CTA to start a thread.
- **Composer**: if no suggestions, show “No suggestions yet—pin memories or connect GitHub.”


---

## 🔩 Implementation Patchpack — Migrations & Handler Stubs (ready to paste)

This section contains **drop‑in SQL migrations** and **TypeScript route stubs** for the endpoints/spec above. Since I can’t create files directly from here, the content is bundled below so you can paste it into your codebase. If you open the relevant files in VS Code, I can patch them in‑place next.

### A) SQL Migrations (PostgreSQL)
Create these under your migrations folder (e.g., `db/migrations/`).

#### `001_add_threads_lineage.sql`
```sql
-- 001_add_threads_lineage.sql
ALTER TABLE threads ADD COLUMN IF NOT EXISTS parent_id UUID NULL;
ALTER TABLE threads ADD COLUMN IF NOT EXISTS lineage_path TEXT;
ALTER TABLE threads ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT false;
ALTER TABLE threads ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private'; -- 'private'|'unlisted'
ALTER TABLE threads ADD COLUMN IF NOT EXISTS summary TEXT;

CREATE INDEX IF NOT EXISTS idx_threads_lineage_path ON threads (lineage_path);
CREATE INDEX IF NOT EXISTS idx_threads_is_archived ON threads (is_archived);
```

#### `002_create_thread_merges.sql`
```sql
-- 002_create_thread_merges.sql
CREATE TABLE IF NOT EXISTS thread_merges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_thread_id UUID NOT NULL,
  target_thread_id UUID NOT NULL,
  merged_by UUID NOT NULL,
  merged_at TIMESTAMPTZ DEFAULT now(),
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_thread_merges_target ON thread_merges (target_thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_merges_source ON thread_merges (source_thread_id);
```

#### `003_connectors_jobs_events.sql`
```sql
-- 003_connectors_jobs_events.sql
CREATE TABLE IF NOT EXISTS connector_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL, -- 'github'
  display_name TEXT,
  avatar_url TEXT
);

CREATE TABLE IF NOT EXISTS connector_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE,
  scopes TEXT[],
  settings JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS connector_status_history (
  id BIGSERIAL PRIMARY KEY,
  connector_id UUID NOT NULL,
  status TEXT NOT NULL, -- OK|DEGRADED|ERROR|SYNCING
  message TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_csh_connector_time ON connector_status_history (connector_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connector_id UUID NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error TEXT,
  attempt INT DEFAULT 0,
  cursor JSONB
);
CREATE INDEX IF NOT EXISTS idx_jobs_connector_time ON sync_jobs (connector_id, started_at DESC);

CREATE TABLE IF NOT EXISTS events_outbox (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_events_outbox_time ON events_outbox (created_at DESC);

CREATE TABLE IF NOT EXISTS github_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL, -- issue|pull|commit
  external_id TEXT NOT NULL, -- issue id / pr id / sha
  repo TEXT NOT NULL,
  title TEXT,
  body TEXT,
  state TEXT,
  author TEXT,
  labels JSONB,
  created_at_ts TIMESTAMPTZ,
  updated_at_ts TIMESTAMPTZ,
  synced_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_gh_entities_repo_type ON github_entities (repo, entity_type);
CREATE INDEX IF NOT EXISTS idx_gh_entities_updated ON github_entities (updated_at_ts DESC);
```

#### `004_backfill_threads_lineage.sql`
```sql
-- 004_backfill_threads_lineage.sql
UPDATE threads SET lineage_path = '/root/' || id::text WHERE lineage_path IS NULL;
UPDATE threads SET visibility = COALESCE(visibility, 'private');
```

---

### B) Backend Route Stubs (TypeScript)
Variants are provided for **Express** and **Fastify**. Pick the one that matches your server.

#### B1) Express variant

Create files such as `src/routes/events.ts`, `src/routes/connectors.ts`, and `src/routes/threads.ts`, then register them in your server bootstrap.

`src/routes/events.ts`
```ts
import type { Request, Response } from 'express';
import { Router } from 'express';

export const eventsRouter = Router();

// Simple in‑memory heartbeat; replace with DB outbox reader
const HEARTBEAT_MS = 15000;

eventsRouter.get('/api/events', async (req: Request, res: Response) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');

  // initial retry hint
  res.write(`retry: 3000\n\n`);

  const lastId = req.header('Last-Event-ID');
  // TODO: resume by reading events_outbox where id > lastId
  void lastId;

  // heartbeat ping
  const ping = setInterval(() => {
    res.write(`event: ping\ndata: {}\n\n`);
  }, HEARTBEAT_MS);

  req.on('close', () => {
    clearInterval(ping);
  });
});
```

`src/routes/connectors.ts`
```ts
import { Router } from 'express';
export const connectorsRouter = Router();

// POST /api/connectors/:id/sync → enqueue job
connectorsRouter.post('/api/connectors/:id/sync', async (req, res) => {
  const { id } = req.params;
  // TODO: enqueue sync_jobs row for the connector id
  res.status(202).json({ ok: true, connector_id: id });
});

// GET /api/connectors/:id/status → current + last 10 transitions
connectorsRouter.get('/api/connectors/:id/status', async (req, res) => {
  const { id } = req.params;
  // TODO: query connector_status_history
  res.json({ connector_id: id, status: 'OK', history: [] });
});

// GET /api/connectors/:id/jobs → list recent jobs
connectorsRouter.get('/api/connectors/:id/jobs', async (req, res) => {
  const { id } = req.params;
  // TODO: query sync_jobs by connector
  res.json({ connector_id: id, jobs: [] });
});

// GET /api/connectors/:id/repos → discover repos for the token
connectorsRouter.get('/api/connectors/:id/repos', async (req, res) => {
  const { id } = req.params;
  // TODO: call GitHub API with stored token
  res.json({ connector_id: id, repos: [] });
});
```

`src/routes/threads.ts`
```ts
import { Router } from 'express';
export const threadsRouter = Router();

threadsRouter.post('/api/chat/threads/:id/branch', async (req, res) => {
  const { id } = req.params; // parent thread id
  const { from_message_id } = req.body || {};
  // TODO: create child thread with parent_id=id; copy metadata
  res.json({ ok: true, parent_id: id, from_message_id, new_thread_id: 'TBD' });
});

threadsRouter.post('/api/chat/threads/merge', async (req, res) => {
  const { target_thread_id, source_thread_ids, note } = req.body || {};
  // TODO: insert thread_merges rows; post system notes
  res.json({ ok: true, target_thread_id, merged: source_thread_ids, note });
});

threadsRouter.post('/api/chat/threads/:id/archive', async (req, res) => {
  const { id } = req.params;
  // TODO: set is_archived=true
  res.json({ ok: true, thread_id: id, is_archived: true });
});

threadsRouter.post('/api/chat/threads/:id/unarchive', async (req, res) => {
  const { id } = req.params;
  // TODO: set is_archived=false
  res.json({ ok: true, thread_id: id, is_archived: false });
});

threadsRouter.put('/api/chat/threads/:id/summary', async (req, res) => {
  const { id } = req.params;
  const { summary } = req.body || {};
  // TODO: update threads.summary
  res.json({ ok: true, thread_id: id, summary });
});
```

Register in your server (example):
```ts
import express from 'express';
import { eventsRouter } from './routes/events';
import { connectorsRouter } from './routes/connectors';
import { threadsRouter } from './routes/threads';

const app = express();
app.use(express.json());
app.use(eventsRouter);
app.use(connectorsRouter);
app.use(threadsRouter);

app.listen(process.env.PORT || 3000);
```

#### B2) Fastify variant

As plugins under `src/plugins/`.

`src/plugins/events.ts`
```ts
import fp from 'fastify-plugin';
import type { FastifyInstance } from 'fastify';

export default fp(async function eventsPlugin (app: FastifyInstance) {
  app.get('/api/events', async (req, reply) => {
    reply.raw.setHeader('Content-Type', 'text/event-stream');
    reply.raw.setHeader('Cache-Control', 'no-cache');
    reply.raw.setHeader('Connection', 'keep-alive');
    reply.raw.setHeader('X-Accel-Buffering', 'no');
    reply.raw.write(`retry: 3000\n\n`);

    const HEARTBEAT_MS = 15000;
    const timer = setInterval(() => {
      reply.raw.write(`event: ping\ndata: {}\n\n`);
    }, HEARTBEAT_MS);

    req.raw.on('close', () => clearInterval(timer));
    return reply.hijack();
  });
});
```

`src/plugins/connectors.ts`
```ts
import fp from 'fastify-plugin';
import type { FastifyInstance } from 'fastify';

export default fp(async function connectorsPlugin (app: FastifyInstance) {
  app.post('/api/connectors/:id/sync', async (req, reply) => {
    const { id } = req.params as { id: string };
    // TODO: enqueue sync job
    return reply.code(202).send({ ok: true, connector_id: id });
  });

  app.get('/api/connectors/:id/status', async (req) => {
    const { id } = req.params as { id: string };
    // TODO: query status history
    return { connector_id: id, status: 'OK', history: [] };
  });

  app.get('/api/connectors/:id/jobs', async (req) => {
    const { id } = req.params as { id: string };
    // TODO: query jobs
    return { connector_id: id, jobs: [] };
  });

  app.get('/api/connectors/:id/repos', async (req) => {
    const { id } = req.params as { id: string };
    // TODO: call GitHub API with stored token
    return { connector_id: id, repos: [] };
  });
});
```

`src/plugins/threads.ts`
```ts
import fp from 'fastify-plugin';
import type { FastifyInstance } from 'fastify';

export default fp(async function threadsPlugin (app: FastifyInstance) {
  app.post('/api/chat/threads/:id/branch', async (req) => {
    const { id } = req.params as { id: string };
    const { from_message_id } = (req.body as any) || {};
    // TODO: insert child thread
    return { ok: true, parent_id: id, from_message_id, new_thread_id: 'TBD' };
  });

  app.post('/api/chat/threads/merge', async (req) => {
    const { target_thread_id, source_thread_ids, note } = (req.body as any) || {};
    // TODO: insert thread_merges
    return { ok: true, target_thread_id, merged: source_thread_ids, note };
  });

  app.post('/api/chat/threads/:id/archive', async (req) => {
    const { id } = req.params as { id: string };
    // TODO: set is_archived=true
    return { ok: true, thread_id: id, is_archived: true };
  });

  app.post('/api/chat/threads/:id/unarchive', async (req) => {
    const { id } = req.params as { id: string };
    // TODO: set is_archived=false
    return { ok: true, thread_id: id, is_archived: false };
  });

  app.put('/api/chat/threads/:id/summary', async (req) => {
    const { id } = req.params as { id: string };
    const { summary } = (req.body as any) || {};
    // TODO: update summary
    return { ok: true, thread_id: id, summary };
  });
});
```

Register plugins (example `src/server.ts`):
```ts
import Fastify from 'fastify';
import eventsPlugin from './plugins/events';
import connectorsPlugin from './plugins/connectors';
import threadsPlugin from './plugins/threads';

const app = Fastify();
app.register(eventsPlugin);
app.register(connectorsPlugin);
app.register(threadsPlugin);

app.listen({ port: Number(process.env.PORT) || 3000, host: '0.0.0.0' });
```

---

### C) Quick‑Start Checklist (apply in order)
1. **Drop the SQL files** into your migrations folder and run them (via your migration tool or `psql`).
2. **Pick your server variant** (Express or Fastify), paste the route files, and register them.
3. **Set env**: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `ENCRYPTION_KEY`, and reasonable defaults for `JOB_SCHEDULER_CONCURRENCY`, `SSE_MAX_QUEUE`.
4. **Smoke test**:
   - `curl -N http://localhost:3000/api/events` → should stream `ping` every 15s.
   - `curl -X POST http://localhost:3000/api/connectors/gh_123/sync -d '{}' -H 'Content-Type: application/json'` → `202 Accepted`.
   - `curl http://localhost:3000/api/connectors/gh_123/jobs` → empty list.
   - Archive/unarchive + summary endpoints should return JSON stubs.
5. **Next pass**: wire DB reads/writes, enqueue background jobs, and connect the composer suggestions.

> Once you open any of the target files in VS Code, ping me—I can patch the exact imports and glue code inline.
```

