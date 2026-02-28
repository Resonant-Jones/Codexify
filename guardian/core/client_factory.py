# guardian/core/client_factory.py
from functools import lru_cache

from memoryos.embedders.factory import build_memoryos_embedder
from memoryos.memoryos import Memoryos
from memoryos.utils import DEFAULT_GROQ_BASE_URL, build_llm_client

from .config import settings, validate_embedding_provider_config


@lru_cache(maxsize=1)
def get_memoryos_instance() -> Memoryos:
    """
    Factory to create and return a singleton Memoryos instance.
    It uses the Pydantic settings object for all configuration,
    including the LLM provider and the embedder.
    """
    # --- LLM Client Configuration ---
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "groq":
        api_key = settings.GROQ_API_KEY
        base_url = settings.GROQ_BASE_URL or DEFAULT_GROQ_BASE_URL
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set."
            )
    elif provider == "openai":
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set."
            )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    llm_client = build_llm_client(provider, api_key=api_key, base_url=base_url)

    # --- Embedder Configuration ---
    validate_embedding_provider_config(settings)
    embedder = build_memoryos_embedder(settings.EMBEDDER_PROVIDER)

    # --- Instantiate MemoryOS ---
    return Memoryos(
        user_id="default_user",
        data_storage_path=settings.DATA_STORAGE_PATH,
        embedder=embedder,
        llm_client=llm_client,
        llm_model=settings.LLM_MODEL,
    )
