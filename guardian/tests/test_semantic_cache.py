import pytest

pytestmark = pytest.mark.asyncio

from guardian.cache import semantic_cache, semantic_cache_store


def test_semantic_cache_hit():
    semantic_cache_store("hello world", {"result": 1})
    assert semantic_cache("hello world again") == {"result": 1}


def test_semantic_cache_miss():
    assert semantic_cache("completely different") is None
