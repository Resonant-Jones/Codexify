# PostgreSQL Database Layer Refactoring Plan

**Project**: Codexify
**Component**: `guardian/core/pgdb.py` Modularization
**Author**: Codexify Engineering Team
**Date**: 2025-11-08
**Status**: Proposal - Awaiting Review

---

## Executive Summary

The current `guardian/core/pgdb.py` module has grown to over 59,000 lines of code, becoming a monolithic bottleneck for development, testing, and maintenance. This technical design proposes a structured refactoring into a modular, maintainable database layer that:

- **Improves developer experience** through clear separation of concerns
- **Maintains 100% backward compatibility** via compatibility shims
- **Enables future optimizations** (connection pooling, caching, query optimization)
- **Follows modern best practices** (async/await, dependency injection, type safety)
- **Reduces cognitive load** by organizing code into logical domains

**Estimated Impact:**
- 📉 Reduce main module size by ~80% (59K → ~10K lines)
- ⚡ Enable parallel development on database features
- 🧪 Improve test isolation and coverage
- 🚀 Prepare for production-grade connection pooling and caching

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Proposed Architecture](#2-proposed-architecture)
3. [Module Breakdown](#3-module-breakdown)
4. [Implementation Plan](#4-implementation-plan)
5. [Code Style Standards](#5-code-style-standards)
6. [Testing Strategy](#6-testing-strategy)
7. [Migration Guide](#7-migration-guide)
8. [Documentation Plan](#8-documentation-plan)
9. [Future Enhancements](#9-future-enhancements)
10. [Risk Assessment](#10-risk-assessment)
11. [Success Metrics](#11-success-metrics)

---

## 1. Problem Statement

### Current State

**File**: `guardian/core/pgdb.py`
**Size**: ~59,000 lines
**Responsibilities**: Connection management, ORM operations, repository patterns, query building, transaction handling, event sourcing, caching logic, migrations helpers

### Issues

1. **Monolithic Structure**
   - Single file contains entire database layer
   - Difficult to navigate and understand
   - High merge conflict potential

2. **Testing Challenges**
   - Hard to test individual components in isolation
   - Slow test suite due to large module imports
   - Difficult to mock specific functionality

3. **Performance Limitations**
   - Using `NullPool` for connection pooling (not production-ready)
   - No query result caching infrastructure
   - Synchronous-first design with async bolted on

4. **Maintainability**
   - New developers struggle to understand code flow
   - Changes in one area can affect unrelated features
   - Difficult to identify performance bottlenecks

5. **Scalability Concerns**
   - No clear path to introduce Redis caching
   - Connection pooling can't be easily optimized
   - Query optimization requires refactoring entire file

### Goals

1. ✅ **Modularize** into logical, domain-driven components
2. ✅ **Maintain** 100% backward compatibility
3. ✅ **Modernize** to async-first with proper typing
4. ✅ **Optimize** connection pooling and caching infrastructure
5. ✅ **Document** architecture for future contributors

---

## 2. Proposed Architecture

### High-Level Structure

```
guardian/
├── core/
│   ├── pgdb.py                    # Legacy compatibility shim (500 lines)
│   └── db.py                      # Thin GuardianDB adapter (unchanged)
│
├── db/
│   ├── __init__.py               # Public API exports
│   ├── models.py                  # SQLAlchemy ORM models (unchanged)
│   │
│   ├── connection/               # 🆕 Connection Management
│   │   ├── __init__.py
│   │   ├── engine.py             # Engine factory and configuration
│   │   ├── session.py            # Session factory and context managers
│   │   ├── pooling.py            # Connection pool configuration
│   │   └── health.py             # Database health checks
│   │
│   ├── repositories/             # 🆕 Domain Repositories
│   │   ├── __init__.py
│   │   ├── base.py               # BaseRepository ABC
│   │   ├── chat.py               # ChatRepository (threads, messages)
│   │   ├── memory.py             # MemoryRepository (memory entries)
│   │   ├── project.py            # ProjectRepository
│   │   ├── connector.py          # ConnectorRepository
│   │   ├── user.py               # UserRepository
│   │   ├── audit.py              # AuditLogRepository
│   │   └── event.py              # EventOutboxRepository
│   │
│   ├── crud/                     # 🆕 CRUD Operations
│   │   ├── __init__.py
│   │   ├── base.py               # BaseCRUD generic operations
│   │   ├── async_ops.py          # Async CRUD helpers
│   │   ├── batch_ops.py          # Batch insert/update/delete
│   │   └── query_builder.py     # Dynamic query construction
│   │
│   ├── cache/                    # 🆕 Caching Layer
│   │   ├── __init__.py
│   │   ├── interface.py          # Cache interface (ABC)
│   │   ├── memory.py             # In-memory cache (dev/test)
│   │   ├── redis.py              # Redis cache (production)
│   │   └── decorators.py         # @cached decorator
│   │
│   ├── query/                    # 🆕 Query Utilities
│   │   ├── __init__.py
│   │   ├── filters.py            # Common filter builders
│   │   ├── pagination.py         # Pagination helpers
│   │   ├── sorting.py            # Sort order utilities
│   │   └── aggregation.py        # Aggregate queries
│   │
│   ├── transaction/              # 🆕 Transaction Management
│   │   ├── __init__.py
│   │   ├── manager.py            # Transaction context managers
│   │   ├── isolation.py          # Isolation level management
│   │   └── savepoints.py         # Nested transaction support
│   │
│   └── utils/                    # 🆕 Database Utilities
│       ├── __init__.py
│       ├── exceptions.py         # Custom database exceptions
│       ├── validators.py         # Data validation helpers
│       ├── converters.py         # Type conversion utilities
│       └── constants.py          # Database constants
│
└── migrations/                   # Alembic migrations (unchanged)
```

### Architectural Principles

1. **Layered Architecture**
   ```
   ┌─────────────────────────────────────────┐
   │   FastAPI Routes (API Layer)            │
   └──────────────────┬──────────────────────┘
                      │ Depends(get_db)
   ┌──────────────────▼──────────────────────┐
   │   Repositories (Domain Layer)           │
   │   - ChatRepository                      │
   │   - MemoryRepository                    │
   │   - ProjectRepository                   │
   └──────────────────┬──────────────────────┘
                      │ Uses
   ┌──────────────────▼──────────────────────┐
   │   CRUD Operations (Data Access Layer)   │
   │   - BaseCRUD                            │
   │   - Query Builders                      │
   └──────────────────┬──────────────────────┘
                      │ Uses
   ┌──────────────────▼──────────────────────┐
   │   Session Management (Infrastructure)   │
   │   - Engine Factory                      │
   │   - Connection Pool                     │
   └─────────────────────────────────────────┘
   ```

2. **Dependency Injection**
   - No global engine/session instances
   - Use FastAPI's `Depends()` for session management
   - Repositories receive session via constructor injection

3. **Single Responsibility**
   - Each module handles one concern
   - Clear interfaces between layers
   - Easy to test and mock

4. **Async-First Design**
   - All new code uses async/await
   - Backward compatibility via sync wrappers
   - SQLAlchemy 2.0 async patterns

---

## 3. Module Breakdown

### 3.1 Connection Management (`guardian/db/connection/`)

**Purpose**: Handle database engine creation, session lifecycle, and connection pooling.

#### `engine.py` - Engine Factory

```python
"""Database engine configuration and factory."""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import QueuePool, NullPool

class EngineFactory:
    """Factory for creating SQLAlchemy async engines."""

    @staticmethod
    def create_engine(
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        use_pool: bool = True
    ) -> AsyncEngine:
        """Create async database engine with connection pooling.

        Args:
            database_url: PostgreSQL connection string
            pool_size: Number of connections in pool
            max_overflow: Max connections beyond pool_size
            pool_timeout: Timeout for getting connection (seconds)
            pool_recycle: Recycle connections after N seconds
            echo: Echo SQL statements to stdout
            use_pool: Use QueuePool (True) or NullPool (False)

        Returns:
            AsyncEngine: Configured async engine

        Example:
            >>> engine = EngineFactory.create_engine(
            ...     "postgresql+asyncpg://user:pass@localhost/db",
            ...     pool_size=10
            ... )
        """
        poolclass = QueuePool if use_pool else NullPool

        return create_async_engine(
            database_url,
            poolclass=poolclass,
            pool_size=pool_size if use_pool else None,
            max_overflow=max_overflow if use_pool else None,
            pool_timeout=pool_timeout if use_pool else None,
            pool_recycle=pool_recycle,
            echo=echo,
            future=True  # SQLAlchemy 2.0 style
        )
```

#### `session.py` - Session Factory

```python
"""Session factory and context managers."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

class SessionFactory:
    """Factory for creating database sessions."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for database sessions.

        Yields:
            AsyncSession: Database session

        Example:
            >>> async with session_factory.session() as session:
            ...     result = await session.execute(select(User))
        """
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_session(self) -> AsyncSession:
        """Get a session (for dependency injection).

        Returns:
            AsyncSession: Database session

        Example:
            >>> async def get_db():
            ...     async with session_factory.session() as session:
            ...         yield session
        """
        return self._session_maker()
```

#### `pooling.py` - Connection Pool Configuration

```python
"""Connection pool configuration and monitoring."""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PoolConfig:
    """Connection pool configuration."""

    # Core pool settings
    pool_size: int = 5              # Base pool size
    max_overflow: int = 10          # Max extra connections
    pool_timeout: int = 30          # Connection timeout (seconds)
    pool_recycle: int = 3600        # Recycle after 1 hour
    pool_pre_ping: bool = True      # Test connections before use

    # Environment-specific presets
    @classmethod
    def development(cls) -> "PoolConfig":
        """Development environment settings."""
        return cls(pool_size=2, max_overflow=3, pool_timeout=10)

    @classmethod
    def production(cls) -> "PoolConfig":
        """Production environment settings."""
        return cls(pool_size=20, max_overflow=40, pool_timeout=30)

    @classmethod
    def testing(cls) -> "PoolConfig":
        """Testing environment settings (no pooling)."""
        return cls(pool_size=0, max_overflow=0, pool_timeout=5)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for engine creation."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping
        }
```

#### `health.py` - Health Checks

```python
"""Database health check utilities."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

async def check_connection(engine: AsyncEngine) -> bool:
    """Check if database connection is healthy.

    Args:
        engine: Database engine

    Returns:
        bool: True if connection is healthy
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def get_pool_stats(engine: AsyncEngine) -> Dict[str, int]:
    """Get connection pool statistics.

    Args:
        engine: Database engine

    Returns:
        Dict with pool metrics
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }
```

---

### 3.2 Repositories (`guardian/db/repositories/`)

**Purpose**: Domain-specific data access patterns following the Repository pattern.

#### `base.py` - Base Repository

```python
"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from guardian.db.models import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """Base repository for common database operations.

    Type Parameters:
        T: SQLAlchemy model type
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get(self, id: int) -> Optional[T]:
        """Get entity by ID.

        Args:
            id: Primary key

        Returns:
            Entity instance or None
        """
        return await self.session.get(self.model, id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None
    ) -> List[T]:
        """List entities with pagination.

        Args:
            limit: Max results
            offset: Skip N results
            order_by: Column to sort by

        Returns:
            List of entities
        """
        query = select(self.model).limit(limit).offset(offset)

        if order_by:
            query = query.order_by(getattr(self.model, order_by))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        """Create new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Update entity by ID.

        Args:
            id: Primary key
            **kwargs: Attributes to update

        Returns:
            Updated entity or None
        """
        entity = await self.get(id)
        if not entity:
            return None

        for key, value in kwargs.items():
            setattr(entity, key, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        """Delete entity by ID.

        Args:
            id: Primary key

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
```

#### `chat.py` - Chat Repository

```python
"""Repository for chat threads and messages."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from guardian.db.models import ChatThread, ChatMessage
from guardian.db.repositories.base import BaseRepository

class ChatRepository(BaseRepository[ChatThread]):
    """Repository for chat operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatThread)

    async def create_thread(
        self,
        user_id: str,
        title: str,
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None
    ) -> ChatThread:
        """Create new chat thread.

        Args:
            user_id: User identifier
            title: Thread title
            project_id: Optional project association
            parent_id: Optional parent thread

        Returns:
            Created thread
        """
        return await self.create(
            user_id=user_id,
            title=title,
            project_id=project_id,
            parent_id=parent_id
        )

    async def get_thread_with_messages(
        self,
        thread_id: int,
        limit: Optional[int] = None
    ) -> Optional[ChatThread]:
        """Get thread with messages eagerly loaded.

        Args:
            thread_id: Thread ID
            limit: Max messages to load

        Returns:
            Thread with messages or None
        """
        query = (
            select(ChatThread)
            .where(ChatThread.id == thread_id)
            .options(selectinload(ChatThread.messages))
        )

        result = await self.session.execute(query)
        thread = result.scalar_one_or_none()

        if thread and limit:
            thread.messages = thread.messages[-limit:]

        return thread

    async def add_message(
        self,
        thread_id: int,
        role: str,
        content: str
    ) -> ChatMessage:
        """Add message to thread.

        Args:
            thread_id: Thread ID
            role: Message role (user/assistant/system)
            content: Message content

        Returns:
            Created message
        """
        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def search_threads(
        self,
        user_id: str,
        query: Optional[str] = None,
        project_id: Optional[int] = None,
        include_archived: bool = False
    ) -> List[ChatThread]:
        """Search threads by criteria.

        Args:
            user_id: User identifier
            query: Search query (title/summary)
            project_id: Filter by project
            include_archived: Include archived threads

        Returns:
            Matching threads
        """
        filters = [ChatThread.user_id == user_id]

        if not include_archived:
            filters.append(ChatThread.archived_at.is_(None))

        if project_id:
            filters.append(ChatThread.project_id == project_id)

        if query:
            search_filter = or_(
                ChatThread.title.ilike(f"%{query}%"),
                ChatThread.summary.ilike(f"%{query}%")
            )
            filters.append(search_filter)

        stmt = select(ChatThread).where(and_(*filters))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def archive_thread(self, thread_id: int) -> Optional[ChatThread]:
        """Archive a thread.

        Args:
            thread_id: Thread ID

        Returns:
            Updated thread or None
        """
        return await self.update(thread_id, archived_at=datetime.utcnow())
```

#### `memory.py` - Memory Repository

```python
"""Repository for memory entries."""

from typing import List, Optional
from sqlalchemy import select, and_

from guardian.db.models import MemoryEntry
from guardian.db.repositories.base import BaseRepository

class MemoryRepository(BaseRepository[MemoryEntry]):
    """Repository for memory operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, MemoryEntry)

    async def create_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        tags: Optional[str] = None,
        pinned: bool = False
    ) -> MemoryEntry:
        """Create new memory entry.

        Args:
            user_id: User identifier
            silo: Memory silo (ephemeral/midterm/longterm)
            content: Memory content
            tags: Optional tags (comma-separated)
            pinned: Whether memory is pinned

        Returns:
            Created memory entry
        """
        return await self.create(
            user_id=user_id,
            silo=silo,
            content=content,
            tags=tags,
            pinned=pinned
        )

    async def get_by_silo(
        self,
        user_id: str,
        silo: str,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """Get memories by silo.

        Args:
            user_id: User identifier
            silo: Memory silo
            limit: Max results

        Returns:
            Memory entries
        """
        stmt = (
            select(MemoryEntry)
            .where(and_(
                MemoryEntry.user_id == user_id,
                MemoryEntry.silo == silo
            ))
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_memories(
        self,
        user_id: str,
        query: str,
        silo: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Search memories by content.

        Args:
            user_id: User identifier
            query: Search query
            silo: Optional silo filter

        Returns:
            Matching memories
        """
        filters = [
            MemoryEntry.user_id == user_id,
            MemoryEntry.content.ilike(f"%{query}%")
        ]

        if silo:
            filters.append(MemoryEntry.silo == silo)

        stmt = select(MemoryEntry).where(and_(*filters))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pinned(self, user_id: str) -> List[MemoryEntry]:
        """Get all pinned memories.

        Args:
            user_id: User identifier

        Returns:
            Pinned memory entries
        """
        stmt = (
            select(MemoryEntry)
            .where(and_(
                MemoryEntry.user_id == user_id,
                MemoryEntry.pinned == True
            ))
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()
```

---

### 3.3 CRUD Operations (`guardian/db/crud/`)

**Purpose**: Low-level query building and batch operations.

#### `base.py` - Generic CRUD

```python
"""Generic CRUD operations."""

from typing import Generic, TypeVar, Type, List, Dict, Any, Optional
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from guardian.db.models import Base

T = TypeVar("T", bound=Base)

class BaseCRUD(Generic[T]):
    """Generic CRUD operations for any model."""

    def __init__(self, model: Type[T]):
        self.model = model

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get multiple records with filtering.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            filters: Dictionary of column: value filters

        Returns:
            List of model instances
        """
        query = select(self.model)

        if filters:
            for column, value in filters.items():
                query = query.where(getattr(self.model, column) == value)

        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    async def count(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count records matching filters.

        Args:
            session: Database session
            filters: Dictionary of column: value filters

        Returns:
            Count of matching records
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        if filters:
            for column, value in filters.items():
                query = query.where(getattr(self.model, column) == value)

        result = await session.execute(query)
        return result.scalar_one()
```

#### `batch_ops.py` - Batch Operations

```python
"""Batch insert/update/delete operations."""

from typing import List, Dict, Any, Type
from sqlalchemy import insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from guardian.db.models import Base

async def batch_insert(
    session: AsyncSession,
    model: Type[Base],
    records: List[Dict[str, Any]],
    return_ids: bool = False
) -> Optional[List[int]]:
    """Batch insert records.

    Args:
        session: Database session
        model: Model class
        records: List of dictionaries with record data
        return_ids: Whether to return inserted IDs

    Returns:
        List of inserted IDs if return_ids=True
    """
    stmt = insert(model).values(records)

    if return_ids:
        stmt = stmt.returning(model.id)
        result = await session.execute(stmt)
        return [row[0] for row in result]
    else:
        await session.execute(stmt)
        return None

async def batch_upsert(
    session: AsyncSession,
    model: Type[Base],
    records: List[Dict[str, Any]],
    index_columns: List[str],
    update_columns: List[str]
) -> None:
    """Batch upsert (insert or update) records.

    Args:
        session: Database session
        model: Model class
        records: List of dictionaries with record data
        index_columns: Columns to use for conflict detection
        update_columns: Columns to update on conflict
    """
    stmt = pg_insert(model).values(records)

    # Build update dict for conflict resolution
    update_dict = {
        col: getattr(stmt.excluded, col)
        for col in update_columns
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=index_columns,
        set_=update_dict
    )

    await session.execute(stmt)
```

---

### 3.4 Caching Layer (`guardian/db/cache/`)

**Purpose**: Abstract caching interface for query results.

#### `interface.py` - Cache Interface

```python
"""Cache interface definition."""

from abc import ABC, abstractmethod
from typing import Any, Optional

class CacheInterface(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache (optionally by pattern)."""
        pass
```

#### `decorators.py` - Cache Decorators

```python
"""Caching decorators for repository methods."""

from functools import wraps
from typing import Callable, Optional
import hashlib
import json

def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None
):
    """Decorator to cache async function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key

    Example:
        >>> @cached(ttl=600, key_prefix="user")
        >>> async def get_user(user_id: str):
        ...     return await db.fetch_user(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = ":".join(key_parts)

            # Check cache
            if hasattr(self, 'cache'):
                cached_value = await self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

            # Execute function
            result = await func(self, *args, **kwargs)

            # Store in cache
            if hasattr(self, 'cache'):
                await self.cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator
```

---

### 3.5 Transaction Management (`guardian/db/transaction/`)

#### `manager.py` - Transaction Context

```python
"""Transaction management utilities."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def transaction(
    session: AsyncSession,
    isolation_level: Optional[str] = None
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for transactions.

    Args:
        session: Database session
        isolation_level: Optional isolation level

    Yields:
        Database session within transaction

    Example:
        >>> async with transaction(session) as tx:
        ...     await tx.execute(insert(User).values(name="Alice"))
        ...     await tx.execute(insert(User).values(name="Bob"))
        # Both committed together or rolled back on error
    """
    if isolation_level:
        await session.execute(
            f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
        )

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

---

### 3.6 Utilities (`guardian/db/utils/`)

#### `exceptions.py` - Custom Exceptions

```python
"""Custom database exceptions."""

class DatabaseError(Exception):
    """Base exception for database errors."""
    pass

class EntityNotFoundError(DatabaseError):
    """Raised when entity is not found."""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(f"{entity_type} with id {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id

class DuplicateEntityError(DatabaseError):
    """Raised when attempting to create duplicate entity."""
    pass

class TransactionError(DatabaseError):
    """Raised when transaction fails."""
    pass
```

---

## 4. Implementation Plan

### Phase 1: Foundation (Week 1)

**Goal**: Set up module structure without breaking existing code.

#### Step 1.1: Create Module Structure
```bash
mkdir -p guardian/db/{connection,repositories,crud,cache,query,transaction,utils}
touch guardian/db/{connection,repositories,crud,cache,query,transaction,utils}/__init__.py
```

#### Step 1.2: Implement Connection Layer
- [x] `guardian/db/connection/engine.py` - Engine factory
- [x] `guardian/db/connection/session.py` - Session factory
- [x] `guardian/db/connection/pooling.py` - Pool configuration
- [x] `guardian/db/connection/health.py` - Health checks

**Tests**: `tests/db/test_connection.py`
- Engine creation with different pool configs
- Session lifecycle
- Pool statistics
- Health check validation

#### Step 1.3: Create Base Repository
- [x] `guardian/db/repositories/base.py` - BaseRepository ABC
- [x] `guardian/db/crud/base.py` - BaseCRUD generic

**Tests**: `tests/db/test_base_repository.py`
- CRUD operations on test model
- Pagination
- Filtering
- Error handling

---

### Phase 2: Domain Repositories (Week 2-3)

**Goal**: Extract domain logic from pgdb.py into repositories.

#### Step 2.1: Chat Repository
- [x] Extract chat thread operations
- [x] Extract message operations
- [x] Implement search functionality
- [x] Add tests with 90%+ coverage

**Migration Path**:
```python
# Old (in pgdb.py)
thread = db.create_chat_thread(user_id, title)

# New (using repository)
chat_repo = ChatRepository(session)
thread = await chat_repo.create_thread(user_id, title)
```

#### Step 2.2: Memory Repository
- [x] Extract memory CRUD operations
- [x] Implement silo-based queries
- [x] Add search functionality
- [x] Add tests

#### Step 2.3: Additional Repositories
- [x] ProjectRepository
- [x] ConnectorRepository
- [x] UserRepository
- [x] AuditLogRepository
- [x] EventOutboxRepository

**Success Criteria**: Each repository has 85%+ test coverage

---

### Phase 3: Backward Compatibility Layer (Week 4)

**Goal**: Create compatibility shim in pgdb.py that delegates to new modules.

#### Step 3.1: Create Compatibility Layer

**File**: `guardian/core/pgdb.py` (reduced to ~500 lines)

```python
"""
Legacy pgdb.py compatibility shim.

This module maintains backward compatibility while delegating to the
new modular database layer. All new code should use the repositories
directly from guardian.db.repositories.

Deprecated: This module will be removed in v2.0.0.
"""

import warnings
from typing import Optional, List

from guardian.db.connection import SessionFactory, EngineFactory
from guardian.db.repositories import (
    ChatRepository,
    MemoryRepository,
    ProjectRepository
)

# Deprecation warning
warnings.warn(
    "Importing from guardian.core.pgdb is deprecated. "
    "Use guardian.db.repositories instead.",
    DeprecationWarning,
    stacklevel=2
)

class LegacyPGDB:
    """Legacy database interface for backward compatibility.

    Deprecated: Use repositories from guardian.db.repositories instead.
    """

    def __init__(self, database_url: str):
        self.engine = EngineFactory.create_engine(database_url)
        self.session_factory = SessionFactory(self.engine)

    async def create_chat_thread(
        self,
        user_id: str,
        title: str,
        project_id: Optional[int] = None
    ):
        """Create chat thread (legacy method).

        Deprecated: Use ChatRepository.create_thread() instead.
        """
        async with self.session_factory.session() as session:
            repo = ChatRepository(session)
            return await repo.create_thread(user_id, title, project_id)

    # ... other legacy methods ...

# Legacy global instance (deprecated)
_legacy_db: Optional[LegacyPGDB] = None

def get_legacy_db() -> LegacyPGDB:
    """Get legacy database instance.

    Deprecated: Use dependency injection with repositories instead.
    """
    global _legacy_db
    if _legacy_db is None:
        from guardian.config import get_settings
        settings = get_settings()
        _legacy_db = LegacyPGDB(settings.database_url)
    return _legacy_db
```

#### Step 3.2: Update Imports in Existing Code

Create automated migration script:

```python
# scripts/migrate_imports.py
import re
from pathlib import Path

def migrate_file(file_path: Path):
    """Migrate imports from pgdb to repositories."""
    content = file_path.read_text()

    # Replace imports
    replacements = {
        "from guardian.core.pgdb import": "from guardian.db.repositories import",
        "import guardian.core.pgdb as pgdb": "from guardian.db import repositories",
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    file_path.write_text(content)

# Run on all Python files
for py_file in Path("guardian").rglob("*.py"):
    migrate_file(py_file)
```

---

### Phase 4: Caching Integration (Week 5)

**Goal**: Add caching layer for performance optimization.

#### Step 4.1: Implement Cache Backends
- [x] In-memory cache (development/testing)
- [x] Redis cache (production)
- [x] Cache decorators

#### Step 4.2: Add Caching to Repositories
```python
class ChatRepository(BaseRepository[ChatThread]):
    def __init__(self, session: AsyncSession, cache: Optional[CacheInterface] = None):
        super().__init__(session, ChatThread)
        self.cache = cache

    @cached(ttl=300, key_prefix="thread")
    async def get_thread_with_messages(self, thread_id: int):
        # Implementation (result will be cached)
        ...
```

---

### Phase 5: Performance Optimization (Week 6)

**Goal**: Optimize connection pooling and query performance.

#### Step 5.1: Enable Connection Pooling
```python
# config/database.py
from guardian.db.connection import PoolConfig

# Production configuration
pool_config = PoolConfig.production()
engine = EngineFactory.create_engine(
    database_url,
    **pool_config.to_dict()
)
```

#### Step 5.2: Query Optimization
- Add database indexes for common queries
- Implement eager loading where appropriate
- Add query result pagination
- Profile slow queries

#### Step 5.3: Monitoring
- Add query logging
- Track pool statistics
- Monitor cache hit rates

---

### Phase 6: Documentation & Cleanup (Week 7)

**Goal**: Complete documentation and deprecate old code.

#### Step 6.1: Create Documentation
- [x] `docs/DB_ARCHITECTURE.md` - New architecture overview
- [x] `docs/MIGRATION_GUIDE.md` - Migration from pgdb.py
- [x] API documentation for each repository
- [x] Examples and best practices

#### Step 6.2: Deprecation Notices
- Add deprecation warnings to pgdb.py
- Update all internal code to use new repositories
- Create migration timeline (6 months to removal)

#### Step 6.3: Performance Testing
- Benchmark new vs old implementation
- Load testing with realistic workloads
- Compare memory usage

---

## 5. Code Style Standards

### 5.1 Type Hints

**Required for all new code:**

```python
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

async def get_threads(
    session: AsyncSession,
    user_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[ChatThread]:
    """Get chat threads for user."""
    ...
```

### 5.2 Async/Await

**All database operations must be async:**

```python
# ✅ Good
async def create_thread(self, user_id: str, title: str) -> ChatThread:
    thread = ChatThread(user_id=user_id, title=title)
    self.session.add(thread)
    await self.session.flush()
    return thread

# ❌ Bad (synchronous)
def create_thread(self, user_id: str, title: str) -> ChatThread:
    thread = ChatThread(user_id=user_id, title=title)
    self.session.add(thread)
    self.session.flush()  # Blocking!
    return thread
```

### 5.3 Context Managers

**Always use async context managers for sessions:**

```python
# ✅ Good
async with session_factory.session() as session:
    repo = ChatRepository(session)
    thread = await repo.create_thread("user123", "My Thread")
    # Automatic commit/rollback

# ❌ Bad (manual session management)
session = session_factory.get_session()
try:
    repo = ChatRepository(session)
    thread = await repo.create_thread("user123", "My Thread")
    await session.commit()
finally:
    await session.close()
```

### 5.4 Dependency Injection

**Use FastAPI's Depends() for session injection:**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with session_factory.session() as session:
        yield session

@app.post("/threads")
async def create_thread(
    user_id: str,
    title: str,
    session: AsyncSession = Depends(get_db)
):
    """Create chat thread endpoint."""
    repo = ChatRepository(session)
    thread = await repo.create_thread(user_id, title)
    return thread
```

### 5.5 Error Handling

**Use custom exceptions for domain errors:**

```python
from guardian.db.utils.exceptions import EntityNotFoundError

class ChatRepository:
    async def get_thread_or_404(self, thread_id: int) -> ChatThread:
        """Get thread or raise exception."""
        thread = await self.get(thread_id)
        if not thread:
            raise EntityNotFoundError("ChatThread", thread_id)
        return thread
```

### 5.6 Documentation

**All public methods must have docstrings:**

```python
async def search_threads(
    self,
    user_id: str,
    query: Optional[str] = None,
    project_id: Optional[int] = None
) -> List[ChatThread]:
    """Search chat threads by criteria.

    Args:
        user_id: User identifier to filter by
        query: Optional text search in title/summary
        project_id: Optional project filter

    Returns:
        List of matching ChatThread instances

    Raises:
        DatabaseError: If query fails

    Example:
        >>> threads = await repo.search_threads(
        ...     user_id="user123",
        ...     query="AI conversation"
        ... )
        >>> len(threads)
        5
    """
    ...
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Test each repository in isolation:**

```python
# tests/db/repositories/test_chat.py
import pytest
from guardian.db.repositories import ChatRepository
from guardian.db.models import ChatThread

@pytest.mark.asyncio
async def test_create_thread(db_session):
    """Test creating a chat thread."""
    repo = ChatRepository(db_session)

    thread = await repo.create_thread(
        user_id="user123",
        title="Test Thread"
    )

    assert thread.id is not None
    assert thread.user_id == "user123"
    assert thread.title == "Test Thread"
    assert thread.created_at is not None

@pytest.mark.asyncio
async def test_search_threads(db_session, sample_threads):
    """Test searching threads."""
    repo = ChatRepository(db_session)

    results = await repo.search_threads(
        user_id="user123",
        query="AI"
    )

    assert len(results) > 0
    assert all("AI" in t.title for t in results)
```

### 6.2 Integration Tests

**Test interactions between components:**

```python
# tests/integration/test_chat_flow.py
@pytest.mark.asyncio
async def test_complete_chat_flow(session_factory):
    """Test complete chat workflow."""
    async with session_factory.session() as session:
        chat_repo = ChatRepository(session)

        # Create thread
        thread = await chat_repo.create_thread(
            user_id="user123",
            title="Integration Test"
        )

        # Add messages
        msg1 = await chat_repo.add_message(
            thread_id=thread.id,
            role="user",
            content="Hello"
        )

        msg2 = await chat_repo.add_message(
            thread_id=thread.id,
            role="assistant",
            content="Hi there!"
        )

        # Retrieve with messages
        loaded = await chat_repo.get_thread_with_messages(thread.id)
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"
```

### 6.3 Performance Tests

**Benchmark critical operations:**

```python
# tests/performance/test_bulk_operations.py
import time
import pytest

@pytest.mark.slow
@pytest.mark.asyncio
async def test_bulk_insert_performance(session_factory):
    """Test bulk insert performance."""
    from guardian.db.crud.batch_ops import batch_insert

    records = [
        {"user_id": f"user{i}", "content": f"Memory {i}"}
        for i in range(1000)
    ]

    start = time.time()

    async with session_factory.session() as session:
        await batch_insert(session, MemoryEntry, records)

    duration = time.time() - start

    # Should complete in under 1 second
    assert duration < 1.0
    print(f"Inserted 1000 records in {duration:.2f}s")
```

### 6.4 Test Coverage Requirements

| Component | Minimum Coverage | Target Coverage |
|-----------|-----------------|-----------------|
| Repositories | 85% | 95% |
| CRUD Operations | 90% | 100% |
| Connection Management | 80% | 90% |
| Cache Layer | 85% | 95% |
| Utilities | 90% | 100% |

**Run coverage:**
```bash
pytest --cov=guardian/db --cov-report=html --cov-report=term-missing
```

### 6.5 Test Fixtures

**Shared fixtures for database testing:**

```python
# conftest.py
import pytest
from guardian.db.connection import EngineFactory, SessionFactory

@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = EngineFactory.create_engine(
        "postgresql+asyncpg://test:test@localhost/test_db",
        use_pool=False  # No pooling in tests
    )
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Provide database session for tests."""
    session_factory = SessionFactory(engine)
    async with session_factory.session() as session:
        yield session
        await session.rollback()  # Rollback after each test

@pytest.fixture
async def sample_threads(db_session):
    """Create sample threads for testing."""
    from guardian.db.repositories import ChatRepository

    repo = ChatRepository(db_session)
    threads = []

    for i in range(5):
        thread = await repo.create_thread(
            user_id="user123",
            title=f"Test Thread {i}"
        )
        threads.append(thread)

    return threads
```

---

## 7. Migration Guide

### 7.1 For Developers

#### Before (Old pgdb.py)
```python
from guardian.core import pgdb

# Create thread
db = pgdb.get_legacy_db()
thread = await db.create_chat_thread(
    user_id="user123",
    title="My Thread"
)
```

#### After (New Repositories)
```python
from guardian.db.repositories import ChatRepository
from guardian.db.connection import get_db
from fastapi import Depends

@app.post("/threads")
async def create_thread(
    user_id: str,
    title: str,
    session = Depends(get_db)
):
    repo = ChatRepository(session)
    thread = await repo.create_thread(user_id, title)
    return thread
```

### 7.2 Import Migration Table

| Old Import | New Import | Status |
|------------|------------|--------|
| `from guardian.core.pgdb import create_chat_thread` | `from guardian.db.repositories import ChatRepository` | ⚠️ Deprecated |
| `from guardian.core.pgdb import get_memory` | `from guardian.db.repositories import MemoryRepository` | ⚠️ Deprecated |
| `from guardian.core.pgdb import PGDatabase` | `from guardian.db.connection import SessionFactory` | ⚠️ Deprecated |

### 7.3 Automated Migration Script

**Run this script to update your codebase:**

```bash
python scripts/migrate_to_repositories.py --dry-run  # Preview changes
python scripts/migrate_to_repositories.py             # Apply changes
```

---

## 8. Documentation Plan

### 8.1 Architecture Documentation

**File**: `docs/DB_ARCHITECTURE.md`

```markdown
# Database Architecture

## Overview
Codexify uses a layered database architecture with clear separation between:
- Connection management
- Domain repositories
- CRUD operations
- Caching layer

## Layers

### Connection Layer
- Engine factory with connection pooling
- Session management with async context managers
- Health checks and pool monitoring

### Repository Layer
- Domain-specific data access
- High-level business logic
- Caching integration

### CRUD Layer
- Generic database operations
- Batch operations
- Query builders

## Usage Examples
[Detailed examples...]
```

### 8.2 API Documentation

**Generate with Sphinx:**

```bash
cd docs
sphinx-apidoc -o api ../guardian/db
make html
```

### 8.3 Migration Guide

**File**: `docs/MIGRATION_GUIDE.md`

- Step-by-step migration instructions
- Before/after code examples
- Common pitfalls and solutions
- Deprecation timeline

### 8.4 Best Practices Guide

**File**: `docs/DB_BEST_PRACTICES.md`

- Repository pattern usage
- Transaction management
- Caching strategies
- Performance optimization
- Testing database code

---

## 9. Future Enhancements

### 9.1 Redis Caching Integration

**Phase 1**: Abstract cache interface (✅ Included in plan)
**Phase 2**: Redis backend implementation
**Phase 3**: Cache warming strategies
**Phase 4**: Cache invalidation patterns

### 9.2 Query Optimization

- **Automatic query logging** for slow queries (>100ms)
- **Query result pagination** with cursor-based navigation
- **Lazy loading** optimizations for relationships
- **Database index recommendations** based on query patterns

### 9.3 Advanced Features

#### Read Replicas
```python
class ReplicaRoutingSession(AsyncSession):
    """Route reads to replicas, writes to primary."""

    async def execute(self, statement, **kwargs):
        if self._is_read_query(statement):
            engine = self.replica_engine
        else:
            engine = self.primary_engine

        return await super().execute(statement, **kwargs)
```

#### Event Sourcing Enhancements
```python
class EventRepository:
    """Event sourcing repository."""

    async def append_event(self, event: Event) -> None:
        """Append event to outbox."""
        ...

    async def get_event_stream(self, aggregate_id: str) -> List[Event]:
        """Get event stream for aggregate."""
        ...

    async def replay_events(self, aggregate_id: str) -> Any:
        """Replay events to rebuild state."""
        ...
```

#### Soft Deletes
```python
class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    def soft_delete(self):
        """Mark as deleted without removing."""
        self.deleted_at = datetime.utcnow()
```

---

## 10. Risk Assessment

### 10.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing code | Medium | High | Comprehensive test suite, compatibility shim |
| Performance regression | Low | High | Benchmark tests, gradual rollout |
| Migration complexity | Medium | Medium | Automated migration scripts, clear docs |
| Team learning curve | Medium | Low | Pair programming, code reviews |
| Database schema changes | Low | Medium | Alembic migration coordination |

### 10.2 Rollback Plan

**If critical issues arise:**

1. **Immediate**: Revert to pgdb.py via compatibility layer
2. **Short-term**: Fix issues in new code while old code runs
3. **Long-term**: Complete refactor with lessons learned

**Rollback triggers:**
- Production errors >1%
- Performance degradation >20%
- Critical bug in core functionality

---

## 11. Success Metrics

### 11.1 Code Quality Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Module size (pgdb.py) | 59,000 lines | <10,000 lines | Week 7 |
| Test coverage | Unknown | 85% | Week 6 |
| Avg module size | Unknown | <500 lines | Week 7 |
| Cyclomatic complexity | High | <10/function | Week 7 |

### 11.2 Performance Metrics

| Metric | Baseline | Target | Timeline |
|--------|----------|--------|----------|
| Connection pool size | 0 (NullPool) | 20 (QueuePool) | Week 5 |
| Cache hit rate | 0% | 70% | Week 5 |
| Query response time (p95) | TBD | <100ms | Week 6 |
| Concurrent connections | 1 | 100+ | Week 5 |

### 11.3 Developer Experience Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Time to find code | Unknown | <2 min | Week 7 |
| Onboarding time | Unknown | <1 day | Week 7 |
| PR merge conflicts | High | Low | Week 7 |
| Test execution time | Unknown | <30s | Week 6 |

---

## Appendix A: File Size Reduction Plan

### Current State
```
guardian/core/pgdb.py: 59,000 lines
```

### Target State
```
guardian/core/pgdb.py: 500 lines (compatibility shim)
guardian/db/connection/: 800 lines
guardian/db/repositories/: 3,500 lines
guardian/db/crud/: 1,200 lines
guardian/db/cache/: 600 lines
guardian/db/query/: 500 lines
guardian/db/transaction/: 400 lines
guardian/db/utils/: 300 lines
Total: ~7,800 lines (87% reduction)
```

---

## Appendix B: Recommended Reading

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [FastAPI Async SQL Databases](https://fastapi.tiangolo.com/advanced/async-sql-databases/)
- [Repository Pattern in Python](https://www.cosmicpython.com/book/chapter_02_repository.html)
- [PostgreSQL Connection Pooling Best Practices](https://www.postgresql.org/docs/current/runtime-config-connection.html)

---

## Appendix C: Timeline Summary

```
Week 1: Foundation (connection layer)
Week 2: Domain repositories (chat, memory)
Week 3: Domain repositories (projects, connectors, etc.)
Week 4: Backward compatibility shim
Week 5: Caching integration + connection pooling
Week 6: Performance optimization + testing
Week 7: Documentation + cleanup
```

**Total Duration**: 7 weeks
**Effort**: 2-3 engineers
**Review Points**: End of weeks 2, 4, 6

---

## Approval & Sign-off

**Prepared by**: Codexify Engineering Team
**Review Required**: Lead Engineer, Tech Lead, CTO
**Target Start Date**: TBD
**Target Completion**: 7 weeks from start

---

**Questions or feedback?** Contact dev@catalystlabs.ai or open a discussion on GitHub.
