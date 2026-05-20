import os

import pytest

# Hermetic test defaults: do not let local developer .env leak into pytest.
os.environ.setdefault("CODEXIFY_CONFIG_SOURCE", "core")
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("CODEXIFY_DISABLE_DOTENV", "1")
os.environ["GUARDIAN_API_KEY"] = "test-api-key"
os.environ["GUARDIAN_AUTH_MODE"] = "local"
os.environ["GUARDIAN_EXPOSURE_MODE"] = "local_safe"
os.environ["CODEXIFY_MULTI_USER_ENABLED"] = "false"
os.environ["CODEXIFY_BETA_CORE_ONLY"] = "0"

from tests.utils import get_test_auth_headers


@pytest.fixture
def auth_headers():
    return get_test_auth_headers()


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
