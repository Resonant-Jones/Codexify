-- Migration: 001_create_media_tables.sql
-- Purpose: Create tables for GeneratedImages, UploadedImages, GeneratedDocuments, and UploadedDocuments
-- with proper foreign key constraints and indices for fast lookups
-- NOTE: Aligns FKs with existing core tables used by the app:
--       - projects(id)           -> INTEGER (SERIAL)
--       - chat_threads(id)       -> INTEGER
--       - users(id)              -> TEXT (e.g., 'default')

-- 0) prerequisites
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid()

-- 1) ensure base 'projects' table exists (INTEGER ids)
CREATE TABLE IF NOT EXISTS projects (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 1a) if the projects table already existed (created by core init.sql) it
--     may be missing the `description` column. Add it idempotently so the
--     INSERT below doesn't fail when we include that column.
ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS description TEXT;

-- seed default project used by the app
INSERT INTO projects (id, name, description)
VALUES (1, 'General', 'Default project for content without a specified project')
ON CONFLICT (id) DO NOTHING;

-- 2) ensure minimal 'users' table exists (TEXT ids) to satisfy FKs
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- seed default user
INSERT INTO users (id) VALUES ('default')
ON CONFLICT (id) DO NOTHING;

-- 3) media tables (UUID PKs; FKs to projects/chat_threads/users)
--    NOTE: thread_id references chat_threads(id) (INTEGER) which must already exist in your schema.

-- GeneratedImages table - for AI-generated images
CREATE TABLE IF NOT EXISTS generated_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    src_url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT fk_generated_images_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_generated_images_thread
        FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
    CONSTRAINT fk_generated_images_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for fast lookups on GeneratedImages
CREATE INDEX IF NOT EXISTS idx_generated_images_project_id ON generated_images(project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_images_thread_id ON generated_images(thread_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_images_user_id ON generated_images(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_images_created_at ON generated_images(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_images_deleted_at ON generated_images(deleted_at) WHERE deleted_at IS NOT NULL;

-- UploadedImages table - for user-uploaded images
CREATE TABLE IF NOT EXISTS uploaded_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    src_url TEXT NOT NULL,
    filename TEXT NOT NULL,
    filesize BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT fk_uploaded_images_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_uploaded_images_thread
        FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
    CONSTRAINT fk_uploaded_images_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for fast lookups on UploadedImages
CREATE INDEX IF NOT EXISTS idx_uploaded_images_project_id ON uploaded_images(project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_images_thread_id ON uploaded_images(thread_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_images_user_id ON uploaded_images(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_images_created_at ON uploaded_images(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_images_deleted_at ON uploaded_images(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_images_mime_type ON uploaded_images(mime_type) WHERE deleted_at IS NULL;

-- GeneratedDocuments table - for AI-generated documents
CREATE TABLE IF NOT EXISTS generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('txt', 'md', 'docx', 'pdf', 'html', 'json')),
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT fk_generated_documents_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_generated_documents_thread
        FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
    CONSTRAINT fk_generated_documents_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for fast lookups on GeneratedDocuments
CREATE INDEX IF NOT EXISTS idx_generated_documents_project_id ON generated_documents(project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_thread_id ON generated_documents(thread_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_user_id ON generated_documents(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_created_at ON generated_documents(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_deleted_at ON generated_documents(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_format ON generated_documents(format) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_generated_documents_model ON generated_documents(model) WHERE deleted_at IS NULL;

-- UploadedDocuments table - for user-uploaded documents
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    filesize BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    src_url TEXT NOT NULL,
    parsed_text TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT fk_uploaded_documents_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_uploaded_documents_thread
        FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
    CONSTRAINT fk_uploaded_documents_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for fast lookups on UploadedDocuments
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_project_id ON uploaded_documents(project_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_thread_id ON uploaded_documents(thread_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_user_id ON uploaded_documents(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_created_at ON uploaded_documents(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_deleted_at ON uploaded_documents(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_mime_type ON uploaded_documents(mime_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_parsed_text ON uploaded_documents USING GIN (to_tsvector('english', parsed_text)) WHERE parsed_text IS NOT NULL;

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to keep generated_images.updated_at in sync
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_generated_images_updated_at'
    ) THEN
        CREATE TRIGGER update_generated_images_updated_at
            BEFORE UPDATE ON generated_images
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Trigger to keep uploaded_images.updated_at in sync
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_uploaded_images_updated_at'
    ) THEN
        CREATE TRIGGER update_uploaded_images_updated_at
            BEFORE UPDATE ON uploaded_images
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Trigger to keep generated_documents.updated_at in sync
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_generated_documents_updated_at'
    ) THEN
        CREATE TRIGGER update_generated_documents_updated_at
            BEFORE UPDATE ON generated_documents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Trigger to keep uploaded_documents.updated_at in sync
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_uploaded_documents_updated_at'
    ) THEN
        CREATE TRIGGER update_uploaded_documents_updated_at
            BEFORE UPDATE ON uploaded_documents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;
