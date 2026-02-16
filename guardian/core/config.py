# guardian/core/config.py
import os

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
    CODEXIFY_LOCAL_ONLY_MODE: bool = Field(
        default=True,
        description=(
            "Fail-closed egress guard. When true, all outbound non-local egress is blocked."
        ),
    )
    CODEXIFY_EGRESS_ALLOWLIST: str = Field(
        default="",
        description=(
            "Comma-separated outbound capability allowlist used when CODEXIFY_LOCAL_ONLY_MODE=false. "
            "Supported entries include: openai, groq, elevenlabs, federation, webhook."
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
    GUARDIAN_API_KEY: str | None = Field(
        default=None,
        description="Primary API key for Guardian HTTP auth.",
    )
    GUARDIAN_API_KEYS: str | None = Field(
        default=None,
        description="Comma-separated additional API keys for Guardian HTTP auth.",
    )
    GUARDIAN_DATABASE_URL: str | None = Field(
        default=None,
        description="Primary Postgres connection URL for Guardian chatlog DB.",
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
    GUARDIAN_DEV_MODE: bool = Field(
        default=False,
        description="Enable dev-only routes such as /dev/*.",
    )
    WS_RPC_RATE_LIMIT_CAPACITY: int = Field(
        default=30,
        description="Max websocket RPC requests available per token bucket window.",
    )
    WS_RPC_RATE_LIMIT_REFILL_PER_SECOND: float = Field(
        default=10.0,
        description="Tokens replenished per second for websocket RPC rate limiting.",
    )
    WS_RPC_RATE_LIMIT_NAMESPACE: str = Field(
        default="guardian:ws:rate_limit",
        description="Redis/in-memory namespace prefix for websocket rate limit keys.",
    )
    WS_RPC_IDLE_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        description="Max idle seconds for websocket RPC connections before disconnect.",
    )
    WS_RPC_MAX_CONNECTIONS: int = Field(
        default=200,
        description="Maximum concurrent websocket RPC connections allowed.",
    )


# Create a singleton instance that can be imported across the application
settings = Settings()

CLOUD_LLM_PROVIDERS = {"openai", "groq"}


class LLMConfigError(Exception):
    """Raised when LLM provider configuration is invalid."""


class ConfigCoherenceError(RuntimeError):
    """Raised when config sources disagree on security-relevant values."""


_COHERENCE_FIELDS = (
    "GUARDIAN_API_KEY",
    "GUARDIAN_API_KEYS",
    "GUARDIAN_DATABASE_URL",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
)

_TRUTHY = ("1", "true", "yes", "on")
_PROVIDER_BY_BACKEND = {
    "ollama": "local",
    "local": "local",
    "openai": "openai",
    "groq": "groq",
}


def _normalize_optional(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_provider(value: object) -> str | None:
    raw = _normalize_optional(value)
    if raw is None:
        return None
    lowered = raw.lower()
    return _PROVIDER_BY_BACKEND.get(lowered, lowered)


def _normalize_db_url(value: object) -> str | None:
    url = _normalize_optional(value)
    if url and url.startswith("postgresql+"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


def _load_legacy_settings_for_coherence() -> object | None:
    """
    Load legacy guardian.config settings for cross-system coherence checks.

    Returns None when the legacy module is unavailable or fails to load.
    """
    try:
        from guardian.config.core import get_settings as get_legacy_settings

        return get_legacy_settings()
    except Exception:
        return None


def _coherence_mismatches(core: Settings, legacy: object) -> list[str]:
    mismatches: list[str] = []

    for field in _COHERENCE_FIELDS:
        core_val = getattr(core, field, None)
        legacy_val = getattr(legacy, field, None)
        if field == "GUARDIAN_DATABASE_URL":
            core_norm = _normalize_db_url(core_val)
            legacy_norm = _normalize_db_url(legacy_val)
        else:
            core_norm = _normalize_optional(core_val)
            legacy_norm = _normalize_optional(legacy_val)
        if core_norm != legacy_norm:
            mismatches.append(
                f"{field}: core={core_norm!r} legacy={legacy_norm!r}"
            )

    if (
        os.getenv("LLM_PROVIDER") is not None
        or os.getenv("AI_BACKEND") is not None
    ):
        core_provider = _normalize_provider(core.LLM_PROVIDER)
        legacy_provider = _normalize_provider(
            getattr(legacy, "AI_BACKEND", None)
        )
        if core_provider != legacy_provider:
            mismatches.append(
                "LLM_PROVIDER/AI_BACKEND: "
                f"core={core_provider!r} legacy={legacy_provider!r}"
            )

    if os.getenv("CLOUD_ONLY") is not None:
        legacy_cloud_only = (
            _normalize_optional(getattr(legacy, "CLOUD_ONLY", None)) or ""
        ).lower() in _TRUTHY
        if legacy_cloud_only and not bool(core.ALLOW_CLOUD_PROVIDERS):
            mismatches.append(
                "CLOUD_ONLY requires ALLOW_CLOUD_PROVIDERS=true "
                f"(core={core.ALLOW_CLOUD_PROVIDERS!r}, legacy={legacy_cloud_only!r})"
            )

    return mismatches


def is_cloud_provider(provider: str | None) -> bool:
    if not provider:
        return False
    return provider.strip().lower() in CLOUD_LLM_PROVIDERS


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


def assert_config_coherence(core_settings: Settings | None = None) -> None:
    """
    Ensure security-relevant settings are coherent across config systems.

    Raises ConfigCoherenceError when guardian.core.config and guardian.config.core
    disagree on overlapping critical settings.
    """
    legacy_settings = _load_legacy_settings_for_coherence()
    if legacy_settings is None:
        return

    core = core_settings or get_settings()
    mismatches = _coherence_mismatches(core, legacy_settings)
    if mismatches:
        detail = "; ".join(mismatches)
        raise ConfigCoherenceError(
            "Configuration coherence check failed: "
            f"{detail}. Resolve mismatches or use a single settings source."
        )
