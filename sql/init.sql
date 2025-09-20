-- sql/init.sql

-- Projects
CREATE TABLE IF NOT EXISTS projects (
  id         SERIAL PRIMARY KEY,
  user_id    TEXT NOT NULL DEFAULT 'default',
  name       TEXT NOT NULL UNIQUE,
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

-- Seed "Loose Threads" as project id=1
INSERT INTO projects (id, user_id, name)
VALUES (1, 'default', 'Loose Threads')
ON CONFLICT (id) DO NOTHING;

-- Keep the sequence in sync if we forced id=1
SELECT setval(pg_get_serial_sequence('projects','id'), (SELECT GREATEST(COALESCE(MAX(id),1),1) FROM projects), true);