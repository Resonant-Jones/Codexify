import os

# Hermetic test defaults: do not let local developer .env leak into pytest.
os.environ.setdefault("CODEXIFY_CONFIG_SOURCE", "core")
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("CODEXIFY_DISABLE_DOTENV", "1")
