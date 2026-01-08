# guardian/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Manages application settings using Pydantic.
    Settings are loaded from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    LLM_PROVIDER: str = Field(
        default="local",
        description="The LLM provider to use ('local', 'groq', 'openai').",
    )
    ALLOW_CLOUD_PROVIDERS: bool = Field(
        default=False,
        description=(
            "Safety switch: when false, cloud providers (openai/groq) are disallowed and local must be used. "
            "Set to true only if you intentionally want cloud fallback."
        ),
    )
    LLM_MODEL: str = Field(
        default="library2/ministral-3:8b",
        description="Model identifier to pass to the selected LLM provider.",
    )
    DEFAULT_LOCAL_MODEL: str = Field(
        default="library2/ministral-3:8b",
        description="Default chat model for local (Ollama) completions.",
    )
    DEFAULT_OPENAI_MODEL: str = Field(
        default="gpt-4o",
        description="Default chat model for OpenAI completions.",
    )
    DEFAULT_GROQ_MODEL: str = Field(
        default="moonshotai-kimi-k2-instruct-9050",
        description="Default chat model for Groq completions.",
    )
    EMBEDDER_PROVIDER: str = Field(
        default="local_api",
        description=(
            "Embedding provider (currently fixed for users): 'local_api' (Ollama via LOCAL_BASE_URL). "
            "Advanced override only: set to 'openai' via env for emergency fallback."
        ),
    )
    EMBEDDING_MODEL: str | None = Field(
        default=None,
        description=(
            "Embedding model identifier passed to the selected EMBEDDER_PROVIDER. "
            "Set via environment variables; no default model is assumed."
        ),
    )
    LLM_FALLBACK_ORDER: list[str] = Field(
        default_factory=lambda: ["local", "openai", "groq"],
        description=(
            "Provider failover order for chat completions. Used by retry/fallback logic to attempt local first, then cloud providers."
        ),
    )
    # NOTE: We keep only *defaults* here. A UI model selector should usually query the
    # local provider (e.g., Ollama) for installed models rather than hard-coding a full
    # catalog in config.
    # --- Local (Ollama OpenAI-compatible) routing ---
    LOCAL_BASE_URL: str = Field(
        default="http://192.168.4.225:11434/v1",
        description="Base URL for the local OpenAI-compatible API (e.g., Ollama ).",
    )
    LOCAL_API_KEY: str = Field(
        default="local",
        description="API key placeholder for the local OpenAI-compatible API (often ignored by Ollama).",
    )
    LOCAL_LLM_MODEL: str = Field(
        default="library2/ministral-3:8b",
        description="Local chat model identifier for Ollama.",
    )
    LOCAL_EMBEDDING_MODEL: str | None = Field(
        default=None,
        description=(
            "Deprecated in favor of LOCAL_EMBED_MODEL. Set LOCAL_EMBED_MODEL in the environment."
        ),
    )
    GROQ_API_KEY: str | None = Field(
        default=None, description="API key for Groq."
    )
    GROQ_BASE_URL: str | None = Field(
        default=None,
        description="Optional override for the Groq-compatible OpenAI base URL.",
    )
    OPENAI_API_KEY: str | None = Field(
        default=None, description="API key for OpenAI."
    )
    OPENAI_BASE_URL: str | None = Field(
        default=None,
        description="Optional override for the OpenAI API base URL.",
    )
    DATA_STORAGE_PATH: str = Field(
        default="./data", description="Path for MemoryOS data storage."
    )
    AGENT_TIMEOUT_SECONDS: int = Field(
        default=30, description="Timeout in seconds for agent execution."
    )
    PROVIDER_MAX_RETRIES: int = Field(
        default=3,
        description="Max retry attempts for provider requests (applies to local/openai/groq).",
    )
    PROVIDER_RETRY_BASE_SECONDS: float = Field(
        default=0.5,
        description="Base delay for exponential backoff retries (seconds).",
    )
    PROVIDER_RETRY_MAX_SECONDS: float = Field(
        default=8.0,
        description="Maximum delay between retries (seconds).",
    )
    PROVIDER_RETRY_JITTER_SECONDS: float = Field(
        default=0.2,
        description="Random jitter added to retry sleep to avoid thundering herd (seconds).",
    )
    LLM_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Timeout for individual LLM completion requests (seconds).",
    )
    EMBEDDING_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout for individual embedding requests (seconds).",
    )
    PROMPT_DIR_PATH: str | None = Field(
        default=None,
        description="Optional absolute path to the prompts directory.",
    )
    GUARDIAN_ENABLE_GRAPH_LOGGING: bool = Field(
        default=False,
        description="Enable graph logging of messages (Neo4j integration).",
    )
    GUARDIAN_GRAPH_LOGGING_MODE: str = Field(
        default="noop",
        description="Graph logging mode (e.g., 'noop', 'neo4j', 'stub').",
    )
    GUARDIAN_ENABLE_GRAPH_CONTEXT: bool = Field(
        default=False,
        description="Enable using graph-derived context during completions.",
    )


# Create a singleton instance that can be imported across the application
settings = Settings()


class LLMConfigError(Exception):
    """Raised when LLM provider configuration is invalid."""


def validate_llm_config(
    settings: Settings, provider_override: str | None = None
) -> None:
    """
    Validate that the configured LLM provider has its required credentials.

    Args:
        settings: Settings instance to validate.
        provider_override: Optional provider name to validate instead of settings.LLM_PROVIDER.

    Raises:
        LLMConfigError: if the provider is unsupported or missing a required API key.
    """
    provider = (
        (provider_override or settings.LLM_PROVIDER or "").strip().lower()
    )

    if provider == "local":
        if not settings.LOCAL_BASE_URL:
            raise LLMConfigError("LOCAL_BASE_URL is not configured")
        return

    if provider == "openai":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        if not settings.OPENAI_API_KEY:
            raise LLMConfigError("OPENAI_API_KEY is not configured")
        return

    if provider == "groq":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        if not settings.GROQ_API_KEY:
            raise LLMConfigError("GROQ_API_KEY is not configured")
        return

    raise LLMConfigError(
        f"Unsupported LLM_PROVIDER: {provider or '<empty>'} (expected one of: local, groq, openai)"
    )


def get_settings() -> Settings:
    """Return the shared Settings instance for dependency injection."""
    return settings
