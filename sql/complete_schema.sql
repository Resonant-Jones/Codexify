-- Complete database schema for Guardian

-- Projects
CREATE TABLE IF NOT EXISTS projects (
  id         SERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL DEFAULT 'default',
  name       TEXT NOT NULL UNIQUE,
  description TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Threads
CREATE TABLE IF NOT EXISTS chat_threads (
  id         SERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL DEFAULT 'default',
  title      TEXT NOT NULL,
  summary    TEXT NOT NULL DEFAULT '',
  project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_threads_project_id ON chat_threads(project_id);
CREATE INDEX IF NOT EXISTS ix_chat_threads_updated_at ON chat_threads(updated_at DESC);

-- Messages
CREATE TABLE IF NOT EXISTS chat_messages (
  id         SERIAL PRIMARY KEY,
  thread_id  INTEGER NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  role       TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content    TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_thread_created
  ON chat_messages(thread_id, created_at);

-- Chat log (for history)
CREATE TABLE IF NOT EXISTS chat_log (
  id         SERIAL PRIMARY KEY,
  timestamp  TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id TEXT,
  user_id    TEXT NOT NULL DEFAULT 'default',
  role       TEXT,
  message    TEXT,
  response   TEXT,
  backend    TEXT,
  model      TEXT,
  agent      TEXT,
  tag        TEXT,
  extra      TEXT
);

-- Memory entries
CREATE TABLE IF NOT EXISTS memory_entries (
  id         SERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL DEFAULT 'default',
  silo       TEXT NOT NULL CHECK (silo IN ('ephemeral','midterm','longterm')),
  content    TEXT NOT NULL,
  tags       TEXT DEFAULT '',
  pinned     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_memory_entries_silo ON memory_entries(silo);

-- Sync jobs
CREATE TABLE IF NOT EXISTS sync_jobs (
  id           SERIAL PRIMARY KEY,
  connector_id TEXT NOT NULL,
  status       TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ,
  attempts     INTEGER DEFAULT 0,
  last_error   TEXT,
  metadata     JSONB
);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_connector_created ON sync_jobs(connector_id, created_at);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
  id         SERIAL PRIMARY KEY,
  event      TEXT NOT NULL,
  entity     TEXT NOT NULL,
  entity_id  TEXT NOT NULL,
  user_id    TEXT NOT NULL,
  timestamp  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent profiles
CREATE TABLE IF NOT EXISTS agent_profiles (
  agent_id                  TEXT PRIMARY KEY,
  profile_json              JSONB,
  summarization_frequency   INTEGER DEFAULT 0,
  last_summarized_at        TIMESTAMPTZ
);

-- Threads (legacy)
CREATE TABLE IF NOT EXISTS threads (
  thread_id          SERIAL PRIMARY KEY,
  parent_thread_id   INTEGER REFERENCES threads(thread_id) ON DELETE CASCADE,
  session_id         TEXT,
  summary            TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id            TEXT NOT NULL DEFAULT 'default',
  project_id         TEXT
);

-- Seed "Loose Threads" as project id=1
INSERT INTO projects (id, user_id, name, description)
VALUES (1, 'default', 'Loose Threads', 'Default bucket for unassigned threads')
ON CONFLICT (id) DO NOTHING;

-- Keep the sequence in sync if we forced id=1
SELECT setval(pg_get_serial_sequence('projects','id'), (SELECT GREATEST(COALESCE(MAX(id),1),1) FROM projects), true);
