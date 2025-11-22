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
        default="groq", description="The LLM provider to use ('groq', 'openai')."
    )
    LLM_MODEL: str = Field(
        default="moonshotai-kimi-k2-instruct-9050",
        description="Model identifier to pass to the selected LLM provider.",
    )
    DEFAULT_OPENAI_MODEL: str = Field(
        default="gpt-4o", description="Default chat model for OpenAI completions."
    )
    DEFAULT_GROQ_MODEL: str = Field(
        default="moonshotai-kimi-k2-instruct-9050",
        description="Default chat model for Groq completions.",
    )
    EMBEDDER_PROVIDER: str = Field(
        default="local",
        description="The embedding provider to use ('local', 'openai').",
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="The embedding model to use (e.g., 'text-embedding-3-small', 'text-embedding-3-large').",
    )
    LOCAL_EMBEDDER_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="The local embedding model to use (e.g., 'all-MiniLM-L6-v2', 'all-mpnet-base-v2').",
    )
    GROQ_API_KEY: str | None = Field(default=None, description="API key for Groq.")
    GROQ_BASE_URL: str | None = Field(
        default=None,
        description="Optional override for the Groq-compatible OpenAI base URL.",
    )
    OPENAI_API_KEY: str | None = Field(default=None, description="API key for OpenAI.")
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
    PROMPT_DIR_PATH: str | None = Field(
        default=None, description="Optional absolute path to the prompts directory."
    )
    GUARDIAN_ENABLE_GRAPH_LOGGING: bool = Field(
        default=False, description="Enable graph logging of messages (Neo4j integration)."
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


def validate_llm_config(settings: Settings, provider_override: str | None = None) -> None:
    """
    Validate that the configured LLM provider has its required credentials.

    Args:
        settings: Settings instance to validate.
        provider_override: Optional provider name to validate instead of settings.LLM_PROVIDER.

    Raises:
        LLMConfigError: if the provider is unsupported or missing a required API key.
    """
    provider = (provider_override or settings.LLM_PROVIDER or "").strip().lower()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise LLMConfigError("OPENAI_API_KEY is not configured")
        return

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise LLMConfigError("GROQ_API_KEY is not configured")
        return

    raise LLMConfigError(f"Unsupported LLM_PROVIDER: {provider or '<empty>'}")


def get_settings() -> Settings:
    """Return the shared Settings instance for dependency injection."""
    return settings
