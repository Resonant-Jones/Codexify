CREATE TABLE IF NOT EXISTS chat_threads (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    project_id INTEGER,
    active_profile_id TEXT,
    parent_id INTEGER,
    archived_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    -- You can add parent_id as a FK to chat_threads(id) if you want threading
);
CREATE INDEX IF NOT EXISTS idx_chat_threads_user_id ON chat_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_project_id ON chat_threads(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_archived_at ON chat_threads(archived_at) WHERE archived_at IS NOT NULL;
