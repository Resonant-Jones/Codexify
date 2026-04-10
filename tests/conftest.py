import os

import pytest

# Hermetic test defaults: do not let local developer .env leak into pytest.
os.environ.setdefault("CODEXIFY_CONFIG_SOURCE", "core")
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("CODEXIFY_DISABLE_DOTENV", "1")


@pytest.fixture(autouse=True)
def _drain_chat_import_queue():
    from guardian.queue import redis_queue

    redis_queue._CLIENT = redis_queue._InMemoryRedis()
    redis_queue._QUEUE_CLIENT = redis_queue._InMemoryRedis()
    from guardian.queue.redis_queue import dequeue_chat_import_embed

    while dequeue_chat_import_embed(block=False):
        pass
    yield
    redis_queue._CLIENT = redis_queue._InMemoryRedis()
    redis_queue._QUEUE_CLIENT = redis_queue._InMemoryRedis()
    while dequeue_chat_import_embed(block=False):
        pass
