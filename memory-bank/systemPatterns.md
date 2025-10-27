# System Patterns

## Architectural Patterns

- Pattern 1: Description

## Design Patterns

- Pattern 1: Description

## Common Idioms

- Idiom 1: Description

---

---
version: 1.0
author: Codex (Resonant Constructs)
created: 2025-10-26
category: database
type: enforcement
status: active
---

## PCX_SCHEMA_001 – Schema Sanity & Alembic Contract Enforcement
**Purpose:** Keep the Postgres schema wholly Alembic-managed — no dual DDL paths, no drift, no missing indexes.  
**Rules:**  
1. Inspect `guardian/core/db.py`, `guardian/core/pgdb.py`, and `guardian/core/media_db.py` for raw CREATE TABLE/INDEX or ALTER TABLE.  
2. Eliminate or comment out any runtime DDL, referencing the Alembic revision that now owns the schema.  
3. `_ensure_*` helpers must only verify table/index existence — never mutate schema.  
4. Guard all legacy drops using `IF EXISTS`, noting the fresh database context.  
5. Add integration tests validating ORM↔Alembic alignment via `sqlalchemy.inspect`.  
6. Validation prints: `✅ Alembic/ORM schema contract validated.`  

**Verification:**  
Run:  
```bash
docker compose up --build  
pytest tests/test_migrations.py
```
Expected output includes contract validation confirmation.

---

---
version: 1.0
author: Codex (Resonant Constructs)
created: 2025-10-26
category: database
type: validation
status: active
---

## PCX_SCHEMA_002 – Postgres/Alembic Contract Validation
**Purpose:** Guarantee Codexify’s runtime schema matches Alembic’s declared contract — no drift, no missing tables, no stray DDL.  
**Origin:** Commit `9373693cc12e_add_media_and_tts_tables.py` (Authored by Codex, Oct 26, 2025)  
**Core Enforcement Rules:**  
1. `_ensure_*` helpers must never create or alter tables.  
2. Alembic owns every table/index; runtime only verifies and warns.  
3. On startup, `guardian/core/db.py` uses `inspect()` to enforce schema integrity.  
4. Integration tests assert schema alignment and print ✅ confirmation.  

**Verification:**  
```bash
docker compose down -v && docker compose up --build  
pytest tests/test_migrations.py
```
Expect:  
✅ Alembic/ORM schema contract validated.