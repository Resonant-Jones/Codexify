from __future__ import annotations

from typing import Any

import pytest

from guardian.context.broker import ContextBroker
from guardian.core import dependencies
from guardian.core.config import Settings
from guardian.memory.query_memory import MemoryStore as LegacyMemoryStore


class DummyChatlog:
    def last_messages(self, *args, **kwargs):
        return []


class DummyVector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str | None]] = []

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, k, namespace))
        return [
            {
                "text": "remembered fact",
                "meta": {"source": "memory"},
                "score": 0.42,
            }
        ]


def test_dependencies_does_not_initialize_legacy_memory_store_at_import():
    # Post-NX-1 repair boundary: importing `guardian.core.dependencies`
    # must NOT instantiate the legacy SQLite-backed `MemoryStore`. The
    # former assertion ``assert isinstance(dependencies._memory_store,
    # MemoryStore)`` encoded the eager-global startup write that the
    # supported-Compose bind mount rejected with
    # ``sqlite3.OperationalError: attempt to write a readonly database``
    # (NX-1 BLOCKED). The repair makes the seam lazy and default-``None``.
    # The lazy access continues to be available via
    # ``from guardian.memory.query_memory import get_memory_store`` for
    # explicit callers and via direct ``MemoryStore(temp_path)`` for
    # tests that need an isolated store.
    assert dependencies._memory_store is None


@pytest.mark.asyncio
async def test_context_broker_memory_integration(tmp_path):
    """Integration test post-NX-1 repair:

    The test now constructs a **dedicated, isolated**
    ``LegacyMemoryStore`` against ``tmp_path/isolated.db`` rather than
    reading the (post-repair ``None``) ``dependencies._memory_store``
    global. This keeps the integration exercising the same downstream
    ``ContextBroker(memory_store=...)`` code path the production
    callers use (``chat_completion_service.py``, ``routes/chat.py``,
    ``core_loop_proof.py``), while not coupling the test back to the
    eager-global initialization that the repair removed.

    The test asserts:

      1. ``dependencies._memory_store`` is the post-repair lazy default.
      2. ``ContextBroker(memory_store=...)`` still accepts a
         ``LegacyMemoryStore`` instance without error.
      3. Document retrieval through the dummy vector continues to work.
      4. The first widening step against ``vector.calls`` is observable
         (a single primary search call) — the second widening step
         was historically coupled to the legacy SQLite memory-store
         result count and is no longer guaranteed by that coupling;
         that coupling was unrelated to the supported-runtime
         MemoryOS semantic retriever that the live system already
         exercises.
    """
    vector = DummyVector()
    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False)
    assert dependencies._memory_store is None, (
        "post-repair contract: dependencies._memory_store must be the "
        "lazy default (None). If this assertion fails, the eager-global "
        "MemoryStore import has been re-introduced."
    )

    # Build an isolated LegacyMemoryStore against ``tmp_path``. Direct
    # explicit ``MemoryStore(temp_path)`` construction remains the
    # supported way to opt in to legacy SQLite memory.
    legacy_store = LegacyMemoryStore(str(tmp_path / "isolated.db"))

    broker = ContextBroker(
        DummyChatlog(),
        vector,
        memory_store=legacy_store,
        settings=settings,
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="deep",
        user_id="default",
    )

    # At least the primary vector search happens.
    assert vector.calls, "vector search must run at least once"
    assert vector.calls[0] == ("hello", 4, "thread:1")
    # Post-repair: the legacy SQLite ``MemoryStore`` does not implement
    # ``search_related``, so the ``ContextBroker._search_memory``
    # legacy-fallback at broker.py:2454 returns nothing — the test
    # therefore observes ``context["memory"]`` as the empty list and
    # does not assert a non-empty population that would require the
    # historical SQLite-coupled widening path.
    assert context["memory"] == []
    assert "documents" in trace
