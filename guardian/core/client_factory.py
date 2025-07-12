# guardian/core/client_factory.py
from functools import lru_cache

from .config import settings
from memoryos.memoryos import Memoryos

# Import embedders
from memoryos.embedders.local_embedder import LocalEmbedder

# from MemoryOS_main.embedders.openai_embedder import OpenAIEmbedder # Example
# from MemoryOS_main.embedders.groq_embedder import GroqEmbedder # Example


@lru_cache(maxsize=1)
def get_memoryos_instance() -> Memoryos:
    """
    Factory to create and return a singleton Memoryos instance.
    It uses the Pydantic settings object for all configuration,
    including the LLM provider and the embedder.
    """
    # --- LLM Client Configuration ---
    llm_api_key = None
    llm_base_url = None
    if settings.LLM_PROVIDER == "groq":
        llm_api_key = settings.GROQ_API_KEY
        llm_base_url = "https://api.groq.com/openai/v1"
        if not llm_api_key:
            raise ValueError("LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set.")
    elif settings.LLM_PROVIDER == "openai":
        llm_api_key = settings.OPENAI_API_KEY
        if not llm_api_key:
            raise ValueError("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set.")
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    # --- Embedder Configuration ---
    embedder = None
    if settings.EMBEDDER_PROVIDER == "local":
        embedder = LocalEmbedder()
    # Add other embedders here
    # elif settings.EMBEDDER_PROVIDER == "openai":
    #     ...
    else:
        raise ValueError(f"Unsupported EMBEDDER_PROVIDER: {settings.EMBEDDER_PROVIDER}")

    # --- Instantiate MemoryOS ---
    return Memoryos(
        user_id="default_user",
        data_storage_path=settings.DATA_STORAGE_PATH,
        embedder=embedder,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
    )
