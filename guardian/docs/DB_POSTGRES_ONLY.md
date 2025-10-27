# Codexify Database Architecture: Postgres-Only

**Effective Date:** 2025-10-26
**Status:** Active Policy
**Owner:** Resonant Constructs LLC

---

## Executive Summary

Codexify has transitioned to a **Postgres-only** database architecture. SQLite support has been removed. All schema management is handled through **SQLAlchemy ORM + Alembic migrations**.

## Rationale

### Why Postgres-Only?

1. **Production Reality**: Codexify deployments run on Postgres via Docker Compose
2. **Schema Complexity**: Advanced features (JSONB, full-text search, complex joins) require Postgres
3. **Maintenance Burden**: Dual-backend support created schema drift and testing complexity
4. **Local-First Philosophy**: Postgres can run locally via Docker - no cloud dependency required

### What About Local-First?

Codexify remains local-first:
- Postgres runs in a local Docker container (no external services)
- Data stays on your machine
- No vendor lock-in - Postgres is open source
- Simple `docker compose up` provides full stack

---

## Architecture

### Schema Management

**Single Source of Truth: `guardian/db/models.py`**

All tables are defined as SQLAlchemy ORM models:

```python
from guardian.db.models import (
    Project,
    ChatThread,
    ChatMessage,
    ConnectorConfig,
    MemoryEntry,
    # ... etc
)
```

**Migrations: Alembic Only**

```bash
# Create migration from model changes
alembic revision --autogenerate -m "add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

###  Database Adapter: `GuardianDB`

**Location:** `guardian/core/db.py`

`GuardianDB` is now a **thin service layer** over SQLAlchemy:

- ✅ **Provides**: High-level query methods, session management
- ❌ **Does NOT**: Create tables, run DDL, manage schema

```python
# Good: Service layer usage
db = GuardianDB(DATABASE_URL)
thread = db.create_chat_thread(user_id="user123", title="New Chat")

# Bad: Don't do this anymore
db.execute("CREATE TABLE ...") # Schema is managed by Alembic!
```

---

## Development Workflow

### Initial Setup

```bash
# 1. Start Postgres
docker compose up -d db

# 2. Run migrations
docker compose up migrations

# 3. Start backend
docker compose up backend
```

### Making Schema Changes

```bash
# 1. Edit guardian/db/models.py
class MyNewTable(Base):
    __tablename__ = "my_new_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ... fields

# 2. Generate migration
alembic -c backend/alembic.ini revision --autogenerate -m "add my_new_table"

# 3. Review generated migration in guardian/db/migrations/versions/

# 4. Apply migration
alembic -c backend/alembic.ini upgrade head

# 5. Test
docker compose restart backend
```

### Testing Migrations

```bash
# Test on fresh database
docker compose down -v  # Wipe data
docker compose up -d db
docker compose up migrations
# Should complete without errors

# Test idempotency
docker compose up migrations  # Run again
# Should be no-op
```

---

## Rules & Guardrails

### ✅ DO

- Define all tables in `guardian/db/models.py`
- Use Alembic for all schema changes
- Write idempotent migrations (use `CREATE TABLE IF NOT EXISTS` in raw SQL if needed)
- Test migrations on fresh databases
- Use `GuardianDB` methods for queries

### ❌ DON'T

- Create tables with raw SQL in application code
- Use `ALTER TABLE` in runtime code
- Add SQLite-specific code (`sqlite3` module, `.db` files)
- Bypass Alembic (no manual DDL)
- Use `CREATE TABLE IF NOT EXISTS` in models (Alembic handles creation)

---

## Migration from Legacy Code

### If You Have Old SQLite Code

**Old (SQLite):**
```python
import sqlite3
conn = sqlite3.connect("guardian.db")
conn.execute("CREATE TABLE IF NOT EXISTS ...")
```

**New (Postgres + ORM):**
```python
from guardian.db.models import ChatThread
from guardian.core.db import GuardianDB

db = GuardianDB(os.getenv("DATABASE_URL"))
thread = db.create_chat_thread(...)  # Uses ORM under the hood
```

### If You Have Raw DDL

Move it to a proper Alembic migration:

```bash
# 1. Create migration
alembic revision -m "migrate legacy tables"

# 2. Edit migration file
def upgrade():
    # Add your DDL here
    op.execute("""
        CREATE TABLE IF NOT EXISTS my_legacy_table (...)
    """)

def downgrade():
    op.drop_table("my_legacy_table")
```

---

## Troubleshooting

### Migration Fails: "Table already exists"

**Cause:** Table was created manually before migration
**Fix:**
```bash
# Mark migration as applied without running it
alembic stamp head
```

### Import Error: "cannot import GuardianDB"

**Cause:** Old SQLite `guardian/core/db.py` still in use
**Fix:**
```bash
# Ensure you're using the new Postgres version
cat guardian/core/db.py | head -20
# Should say "Postgres-only" in docstring
```

### Boot Crash: "SQLite database is locked"

**Cause:** Still referencing old SQLite code
**Fix:** Remove all sqlite3 imports and `.db` file references

### Schema Drift

**Symptom:** Models don't match database
**Fix:**
```bash
# Generate migration to sync
alembic revision --autogenerate -m "sync schema"
alembic upgrade head
```

---

## FAQ

**Q: Can I still develop offline?**
A: Yes! Postgres runs locally in Docker. No internet required after initial image pull.

**Q: What if I need SQLite for testing?**
A: Use Postgres for all environments. It's consistent and avoids drift. You can run lightweight Postgres in CI.

**Q: How do I backup my data?**
A:
```bash
# Dump database
docker compose exec db pg_dump -U guardian guardian > backup.sql

# Restore
docker compose exec -T db psql -U guardian guardian < backup.sql
```

**Q: Can I use other ORMs (Tortoise, Pony)?**
A: Stick with SQLAlchemy. It's the standard and Alembic integrates seamlessly.

---

## Related Documentation

- [SQLAlchemy Mapped Column Docs](https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Postgres Docker Image](https://hub.docker.com/_/postgres)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-10-26 | Initial Postgres-only policy | Claude (Resonant Constructs) |
| 2025-10-26 | Removed SQLite support | Claude (Resonant Constructs) |
| 2025-10-26 | Refactored GuardianDB to service layer | Claude (Resonant Constructs) |
| 2025-10-26 | Updated all models for JSONB/Postgres types | Claude (Resonant Constructs) |

---

**Questions?** Open an issue or contact the Codexify team at Resonant Constructs LLC.
