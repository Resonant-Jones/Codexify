# Database Migrations for Guardian Media Management

This directory contains database migrations for the Guardian media management system.

## Migration Files

### 001_create_media_tables.sql
Creates the core media management tables:
- **generated_images** - AI-generated images with prompt and model info
- **uploaded_images** - User-uploaded images with file metadata
- **generated_documents** - AI-generated documents with content and format
- **uploaded_documents** - User-uploaded documents with parsed text for search

## Features

✅ **UUID Primary Keys** - Using gen_random_uuid() for distributed systems
✅ **Foreign Key Constraints** - Proper references to Projects, Threads, Users
✅ **Soft Delete Support** - deleted_at timestamp for recoverable deletions
✅ **Automatic Timestamps** - created_at, updated_at with automatic updates
✅ **Comprehensive Indexing** - Fast lookups on project_id, thread_id, user_id
✅ **Full-Text Search** - GIN indices on parsed_text for document search
✅ **File Type Validation** - CHECK constraints on format and mime_type

## Running Migrations

### Option 1: Direct SQL Execution
```bash
psql -d your_database_name -f db/migrations/001_create_media_tables.sql
```

### Option 2: Python Migration Runner
```python
import psycopg2
from pathlib import Path

def run_migration(conn, migration_file):
    with conn.cursor() as cur:
        with open(migration_file, 'r') as f:
            cur.execute(f.read())
    conn.commit()

# Usage
conn = psycopg2.connect("dbname=guardian user=postgres password=your_password")
run_migration(conn, "db/migrations/001_create_media_tables.sql")
conn.close()
```

## Database Schema Overview

### generated_images
Stores AI-generated images with metadata about the generation process.
- **id**: UUID primary key
- **project_id, thread_id, user_id**: Foreign keys for organization
- **src_url**: Storage location of the generated image
- **prompt**: The text prompt used for generation
- **model**: The AI model used (e.g., "dall-e-3", "stable-diffusion")

### uploaded_images
Stores user-uploaded images with file metadata.
- **id**: UUID primary key
- **src_url**: Storage location of the uploaded file
- **filename**: Original filename
- **filesize**: File size in bytes
- **mime_type**: MIME type for proper handling

### generated_documents
Stores AI-generated documents with content and format info.
- **id**: UUID primary key
- **title**: Document title
- **content**: Full document content
- **format**: Document format (txt, md, docx, pdf, html, json)
- **model**: The AI model used for generation

### uploaded_documents
Stores user-uploaded documents with optional parsed text for search.
- **id**: UUID primary key
- **filename**: Original filename
- **filesize**: File size in bytes
- **mime_type**: MIME type
- **src_url**: Storage location
- **parsed_text**: Extracted text content for search/RAG functionality

## Index Strategy

Each table includes indices on:
- **Primary lookup fields**: project_id, thread_id, user_id (for fast filtering)
- **Temporal queries**: created_at (for chronological ordering)
- **Soft delete handling**: deleted_at (for excluding deleted records)
- **Content-specific**: mime_type, format, model (for filtering by type)

## Foreign Key Relationships

```
Projects 1:N GeneratedImages
Projects 1:N UploadedImages
Projects 1:N GeneratedDocuments
Projects 1:N UploadedDocuments

Threads 1:N GeneratedImages
Threads 1:N UploadedImages
Threads 1:N GeneratedDocuments
Threads 1:N UploadedDocuments

Users 1:N GeneratedImages
Users 1:N UploadedImages
Users 1:N GeneratedDocuments
Users 1:N UploadedDocuments
```

All relationships use ON DELETE CASCADE for automatic cleanup when parent records are deleted.
