# guardian/core/config.py
import logging
import os
from dataclasses import dataclass

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Module-level logger for config coherence reporting
logger = logging.getLogger(__name__)

_DEFAULT_ALIBABA_API_BASE = (
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
)
SUPPORTED_ROUTED_LLM_PROVIDERS: tuple[str, ...] = (
    "local",
    "openai",
    "groq",
    "alibaba",
    "minimax",
)
SUPPORTED_ROUTED_CLOUD_LLM_PROVIDERS: tuple[str, ...] = tuple(
    provider
    for provider in SUPPORTED_ROUTED_LLM_PROVIDERS
    if provider != "local"
)
ROUTER_SUPPORTED_LLM_PROVIDERS: tuple[str, ...] = (
    "local",
    "groq",
    "openai",
    "alibaba",
    "minimax",
)
_ROUTER_SUPPORTED_LLM_PROVIDER_TEXT = ", ".join(ROUTER_SUPPORTED_LLM_PROVIDERS)
CLOUD_LLM_PROVIDERS = frozenset(
    provider
    for provider in ROUTER_SUPPORTED_LLM_PROVIDERS
    if provider != "local"
)


def _normalize_model_setting(value: str | None) -> str:
    normalized = str(value or "").strip()
    if normalized.lower() in {"", "auto"}:
        return ""
    return normalized


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
        description=(
            "The LLM provider to use. Runtime-supported values: "
            f"{_ROUTER_SUPPORTED_LLM_PROVIDER_TEXT}."
        ),
    )
    CODEXIFY_CONFIG_SOURCE: str = Field(
        default="strict",
        description=(
            "Select which settings system coherence checks should trust: "
            "'strict' (default, fail closed on mismatch), 'core' (trust guardian.core.config), "
            "or 'legacy' (trust guardian.config.core)."
        ),
    )
    ALLOW_CLOUD_PROVIDERS: bool = Field(
        default=False,
        description=(
            "Safety switch: when false, cloud providers (openai/groq/alibaba/minimax) are disallowed and local must be used. "
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
            "Supported entries include: openai, groq, alibaba, minimax, elevenlabs, federation, webhook."
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
    OPENAI_MODEL: str | None = Field(
        default=None,
        description="Optional explicit chat model for OpenAI completions.",
    )
    DEFAULT_GROQ_MODEL: str = Field(
        default="moonshotai/kimi-k2-instruct-0905",
        description="Default chat model for Groq completions.",
    )
    GROQ_MODEL: str | None = Field(
        default=None,
        description="Optional explicit chat model for Groq completions.",
    )
    EMBEDDER_PROVIDER: str = Field(
        default="local_api",
        description=(
            "Embedding provider for MemoryOS and vector flows. "
            "Supported values include local aliases ('local', 'local_api') and cloud providers (for example 'openai')."
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
        default="http://127.0.0.1:11434/v1",
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
    LOCAL_CHAT_MODEL: str = Field(
        default="library2/ministral-3:8b",
        description="Local chat model identifier used by supported profile validation.",
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
    ALIBABA_API_KEY: str | None = Field(
        default=None,
        description="API key for Alibaba Cloud DashScope / Model Studio.",
    )
    ALIBABA_API_BASE: str | None = Field(
        default=_DEFAULT_ALIBABA_API_BASE,
        description=(
            "Base URL for Alibaba Cloud DashScope's OpenAI-compatible API endpoint."
        ),
    )
    ALIBABA_MODEL: str | None = Field(
        default=None,
        description="Optional default chat model for Alibaba Cloud DashScope.",
    )
    ALIBABA_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        description=(
            "Timeout for Alibaba Cloud DashScope chat completion requests (seconds)."
        ),
    )
    ALIBABA_MODEL_DISCOVERY_URL: str | None = Field(
        default=None,
        description=(
            "Optional override for Alibaba's live model index endpoint. "
            "Defaults to deriving /models from ALIBABA_API_BASE."
        ),
    )
    ALIBABA_MODEL_DISCOVERY_TIMEOUT_SECONDS: float = Field(
        default=3.0,
        description=(
            "Timeout for Alibaba live model index discovery requests (seconds)."
        ),
    )
    MINIMAX_API_KEY: str | None = Field(
        default=None, description="API key for MiniMax."
    )
    MINIMAX_API_BASE: str | None = Field(
        default=None,
        description="Base URL for MiniMax's OpenAI-compatible API endpoint.",
    )
    MINIMAX_API_FLAVOR: str = Field(
        default="openai",
        description=(
            "MiniMax API surface to use: 'openai' for /chat/completions or "
            "'anthropic' for /v1/messages."
        ),
    )
    MINIMAX_ANTHROPIC_VERSION: str = Field(
        default="2023-06-01",
        description=(
            "Anthropic API version header used when MINIMAX_API_FLAVOR=anthropic."
        ),
    )
    MINIMAX_MODEL: str | None = Field(
        default=None,
        description="Optional default chat model for MiniMax.",
    )
    MINIMAX_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        description="Timeout for MiniMax chat completion requests (seconds).",
    )
    MINIMAX_MODEL_DISCOVERY_URL: str | None = Field(
        default=None,
        description=(
            "Optional override for MiniMax's live model index endpoint. "
            "Defaults to deriving /models from MINIMAX_API_BASE."
        ),
    )
    MINIMAX_MODEL_DISCOVERY_TIMEOUT_SECONDS: float = Field(
        default=3.0,
        description=(
            "Timeout for MiniMax live model index discovery requests (seconds)."
        ),
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
    AGENT_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum retry attempts for mutating delegated steps.",
    )
    AGENT_MIN_ATTEMPTS_BEFORE_ABORT: int = Field(
        default=2,
        description=(
            "Minimum attempts before early-abort retry heuristics may escalate."
        ),
    )
    AGENT_NO_PROGRESS_WINDOW: int = Field(
        default=2,
        description=(
            "Consecutive no-progress attempts required before early escalation."
        ),
    )
    AGENT_MAX_SAME_SIGNATURE_REPEATS: int = Field(
        default=2,
        description=(
            "Maximum repeated identical failure signatures before escalation."
        ),
    )
    AGENT_REGRESSION_LIMIT: int = Field(
        default=2,
        description=(
            "Maximum allowed regression in failing tests versus best-so-far attempt."
        ),
    )
    AGENT_AUTO_ROLLBACK_ON_FAIL: bool = Field(
        default=True,
        description=(
            "When true, failed runs auto-clean their worktree/branch unless escalated."
        ),
    )
    AGENT_VALIDATOR_MODEL_ENABLED: bool = Field(
        default=False,
        description=(
            "Enable optional validator pre-step for writing/improving tests."
        ),
    )
    AGENT_REQUIRE_TWO_COMMITS: bool = Field(
        default=True,
        description=(
            "Require exactly two commits for each successful mutating step."
        ),
    )
    AGENT_VALIDATION_COMMIT_ALLOW_EMPTY: bool = Field(
        default=True,
        description=(
            "Allow empty validation-boundary commit to avoid repository metadata churn."
        ),
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
    LOCAL_REQUEST_CONNECT_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description=(
            "Connect timeout for local model requests in seconds. Kept short so "
            "unreachable local runtimes fail quickly even when read timeouts are extended."
        ),
    )
    LOCAL_EXTENDED_THINKING_TIMEOUT_SECONDS: float = Field(
        default=300.0,
        description=(
            "Read timeout for local long-thinking models such as Qwen 3.x/QwQ, in seconds."
        ),
    )
    LOCAL_EXTENDED_THINKING_MODEL_PATTERNS: str = Field(
        default="qwen3.5,qwen-3.5,qwen 3.5,qwen3,qwen-3,qwen 3,qwq",
        description=(
            "Comma-separated substrings used to classify local models that may spend "
            "multiple minutes reasoning before emitting tokens."
        ),
    )
    LOCAL_DEFAULT_NO_THINK_ENABLED: bool = Field(
        default=True,
        description=(
            "When true, eligible local reasoning-capable Qwen 3 models receive a "
            "runtime '/no_think' instruction so they respond in fast mode by default."
        ),
    )
    LOCAL_NO_THINK_MODEL_PATTERNS: str = Field(
        default="qwen3.5,qwen-3.5,qwen 3.5,qwen3,qwen-3,qwen 3",
        description=(
            "Comma-separated substrings used to identify local models that should "
            "default to Qwen's non-thinking mode via prompt instruction."
        ),
    )
    LOCAL_NO_THINK_SKIP_MODEL_PATTERNS: str = Field(
        default="thinking-2507,qwen3.5-thinking,qwen-3.5-thinking,qwen 3.5 thinking,qwen3-thinking,qwen-3-thinking,qwen 3 thinking,instruct-2507",
        description=(
            "Comma-separated substrings that opt local models out of automatic "
            "'/no_think' injection, such as fixed-mode Qwen releases."
        ),
    )
    LOCAL_NO_THINK_INSTRUCTION: str = Field(
        default="/no_think",
        description=(
            "Prompt instruction appended for local Qwen-style models when "
            "LOCAL_DEFAULT_NO_THINK_ENABLED is true."
        ),
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
    GUARDIAN_FEDERATION_ENABLED: bool = Field(
        default=False,
        description="Master gate for all federation endpoints.",
    )
    GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY: bool = Field(
        default=True,
        description="Require a valid signed trust policy before federation requests are accepted.",
    )
    GUARDIAN_FEDERATION_TRUST_POLICY_JSON: str | None = Field(
        default=None,
        description="JSON trust policy controlling allowed federation peers/origins.",
    )
    GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE: str | None = Field(
        default=None,
        description="Base64url HMAC signature for GUARDIAN_FEDERATION_TRUST_POLICY_JSON.",
    )
    GUARDIAN_FEDERATION_POLICY_SIGNING_KEY: str | None = Field(
        default=None,
        description="Optional signing key used to verify federation trust policy signatures.",
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

    def model_post_init(self, __context) -> None:
        legacy_openai_model = _normalize_model_setting(
            os.getenv("OPENAI_MODEL_CHAT")
        )
        if legacy_openai_model and not _normalize_model_setting(
            self.OPENAI_MODEL
        ):
            self.OPENAI_MODEL = legacy_openai_model
            logger.warning(
                "[config] OPENAI_MODEL_CHAT is deprecated; use OPENAI_MODEL."
            )

        legacy_cloud_model = _normalize_model_setting(
            os.getenv("DEFAULT_CLOUD_MODEL")
        )
        if (
            legacy_cloud_model
            and not _normalize_model_setting(self.GROQ_MODEL)
            and str(self.LLM_PROVIDER or "").strip().lower() == "groq"
        ):
            self.GROQ_MODEL = legacy_cloud_model
            logger.warning(
                "[config] DEFAULT_CLOUD_MODEL is deprecated for Groq; use GROQ_MODEL."
            )


# Create a singleton instance that can be imported across the application
settings = Settings()

CLOUD_LLM_PROVIDERS = frozenset(
    provider
    for provider in ROUTER_SUPPORTED_LLM_PROVIDERS
    if provider != "local"
)
_VALID_CONFIG_SOURCES = {"strict", "core", "legacy"}
_SENSITIVE_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_LOGGED_COHERENCE_SOURCES: set[str] = set()


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


@dataclass(frozen=True)
class _CoherenceMismatch:
    label: str
    core_value: object
    legacy_value: object
    core_env_keys: tuple[str, ...]
    legacy_env_keys: tuple[str, ...]


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


def _normalize_config_source(value: object) -> str:
    raw = (_normalize_optional(value) or "strict").lower()
    if raw not in _VALID_CONFIG_SOURCES:
        raise ConfigCoherenceError(
            "Invalid CODEXIFY_CONFIG_SOURCE="
            f"{raw!r}. Expected one of: strict, core, legacy."
        )
    return raw


def _mask_env_value(env_key: str, value: str) -> str:
    upper = env_key.upper()
    if any(marker in upper for marker in _SENSITIVE_ENV_MARKERS):
        return "<redacted>"
    return value


def _format_source(keys: tuple[str, ...], effective_value: object) -> str:
    declared: list[str] = []
    for env_key in keys:
        raw = os.getenv(env_key)
        if raw is None:
            continue
        declared.append(f"{env_key}={_mask_env_value(env_key, raw)}")
    if declared:
        return ", ".join(declared)

    if not keys:
        return f"<unknown> (effective={effective_value!r})"

    if len(keys) == 1:
        return f"{keys[0]}=<unset> (effective={effective_value!r})"
    return f"{'|'.join(keys)}=<unset> (effective={effective_value!r})"


def _format_coherence_error(mismatches: list[_CoherenceMismatch]) -> str:
    lines = ["Configuration coherence check failed:"]
    for mismatch in mismatches:
        lines.append(
            f"- {mismatch.label}: core={mismatch.core_value!r} "
            f"legacy={mismatch.legacy_value!r}"
        )
        lines.append(
            "  Core source: "
            + _format_source(mismatch.core_env_keys, mismatch.core_value)
        )
        lines.append(
            "  Legacy source: "
            + _format_source(mismatch.legacy_env_keys, mismatch.legacy_value)
        )
        lines.append(
            "  Fix: remove one set OR set CODEXIFY_CONFIG_SOURCE=core|legacy"
        )
    return "\n".join(lines)


def _validate_legacy_llm_config(legacy: object) -> None:
    provider = _normalize_provider(getattr(legacy, "AI_BACKEND", None))
    if not provider:
        raise ConfigCoherenceError(
            "Legacy settings invalid: AI_BACKEND is empty."
        )
    if provider == "local":
        return

    if provider == "openai":
        if not _normalize_optional(getattr(legacy, "OPENAI_API_KEY", None)):
            raise ConfigCoherenceError(
                "Legacy settings invalid: OPENAI_API_KEY is required when AI_BACKEND=openai."
            )
        return

    if provider == "groq":
        if not _normalize_optional(getattr(legacy, "GROQ_API_KEY", None)):
            raise ConfigCoherenceError(
                "Legacy settings invalid: GROQ_API_KEY is required when AI_BACKEND=groq."
            )
        return

    if provider == "gemini":
        if not (
            _normalize_optional(getattr(legacy, "GENAI_API_KEY", None))
            or _normalize_optional(getattr(legacy, "GOOGLE_API_KEY", None))
        ):
            raise ConfigCoherenceError(
                "Legacy settings invalid: GENAI_API_KEY or GOOGLE_API_KEY is required when AI_BACKEND=gemini."
            )
        return

    if provider == "anthropic":
        if not _normalize_optional(getattr(legacy, "ANTHROPIC_API_KEY", None)):
            raise ConfigCoherenceError(
                "Legacy settings invalid: ANTHROPIC_API_KEY is required when AI_BACKEND=anthropic."
            )
        return

    raise ConfigCoherenceError(
        f"Legacy settings invalid: unsupported AI_BACKEND={provider!r}."
    )


def _log_coherence_source_once(source: str) -> None:
    if source in _LOGGED_COHERENCE_SOURCES:
        return
    _LOGGED_COHERENCE_SOURCES.add(source)
    logger.info(
        "[config] Coherence mode selected: CODEXIFY_CONFIG_SOURCE=%s",
        source,
    )


def _coherence_mismatches(
    core: Settings, legacy: object
) -> list[_CoherenceMismatch]:
    mismatches: list[_CoherenceMismatch] = []

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
                _CoherenceMismatch(
                    label=field,
                    core_value=core_norm,
                    legacy_value=legacy_norm,
                    core_env_keys=(field,),
                    legacy_env_keys=(field,),
                )
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
                _CoherenceMismatch(
                    label="LLM_PROVIDER/AI_BACKEND",
                    core_value=core_provider,
                    legacy_value=legacy_provider,
                    core_env_keys=("LLM_PROVIDER",),
                    legacy_env_keys=("AI_BACKEND",),
                )
            )

    if os.getenv("CLOUD_ONLY") is not None:
        legacy_cloud_only = (
            _normalize_optional(getattr(legacy, "CLOUD_ONLY", None)) or ""
        ).lower() in _TRUTHY
        if legacy_cloud_only and not bool(core.ALLOW_CLOUD_PROVIDERS):
            mismatches.append(
                _CoherenceMismatch(
                    label=("CLOUD_ONLY requires ALLOW_CLOUD_PROVIDERS=true"),
                    core_value=bool(core.ALLOW_CLOUD_PROVIDERS),
                    legacy_value=legacy_cloud_only,
                    core_env_keys=("ALLOW_CLOUD_PROVIDERS",),
                    legacy_env_keys=("CLOUD_ONLY",),
                )
            )

    return mismatches


def is_cloud_provider(provider: str | None) -> bool:
    if not provider:
        return False
    return provider.strip().lower() in CLOUD_LLM_PROVIDERS


def _normalize_embedding_provider(provider: str | None) -> str:
    normalized = (provider or "").strip().lower()
    if normalized in {"local_api", "local"}:
        return "local"
    return normalized


def _validate_supported_profile_contract(settings: Settings) -> None:
    from guardian.core.supported_profile import (
        get_active_supported_profile,
        validate_supported_profile_runtime,
    )

    manifest = get_active_supported_profile()
    if manifest is None:
        return

    mismatches = validate_supported_profile_runtime(manifest, settings=settings)
    if mismatches:
        detail = "; ".join(mismatches)
        raise LLMConfigError(
            "supported profile requires blessed local gateway contract: "
            f"{detail}"
        )


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
        _validate_supported_profile_contract(settings)
        return

    if provider == "openai":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        if not settings.OPENAI_API_KEY:
            raise LLMConfigError("OPENAI_API_KEY is not configured")
        _validate_supported_profile_contract(settings)
        return

    if provider == "groq":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        if not settings.GROQ_API_KEY:
            raise LLMConfigError("GROQ_API_KEY is not configured")
        _validate_supported_profile_contract(settings)
        return

    if provider == "alibaba":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        missing: list[str] = []
        if not (settings.ALIBABA_API_KEY or "").strip():
            missing.append("ALIBABA_API_KEY")
        if not (settings.ALIBABA_API_BASE or "").strip():
            missing.append("ALIBABA_API_BASE")
        if missing:
            missing_text = ", ".join(missing)
            raise LLMConfigError(
                "LLM_PROVIDER is 'alibaba' but required environment variable(s) are missing: "
                f"{missing_text}. Set {missing_text} in your backend environment."
            )
        _validate_supported_profile_contract(settings)
        return

    if provider == "minimax":
        if not settings.ALLOW_CLOUD_PROVIDERS:
            raise LLMConfigError(
                "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
            )
        missing: list[str] = []
        if not (settings.MINIMAX_API_KEY or "").strip():
            missing.append("MINIMAX_API_KEY")
        if not (settings.MINIMAX_API_BASE or "").strip():
            missing.append("MINIMAX_API_BASE")
        if missing:
            missing_text = ", ".join(missing)
            raise LLMConfigError(
                "LLM_PROVIDER is 'minimax' but required environment variable(s) are missing: "
                f"{missing_text}. Set {missing_text} in your backend environment."
            )
        api_flavor = str(
            getattr(settings, "MINIMAX_API_FLAVOR", "openai") or ""
        )
        api_flavor = api_flavor.strip().lower() or "openai"
        if api_flavor not in {"openai", "anthropic"}:
            raise LLMConfigError(
                "MINIMAX_API_FLAVOR must be one of: openai, anthropic."
            )
        _validate_supported_profile_contract(settings)
        return

    raise LLMConfigError(
        "Unsupported LLM_PROVIDER: "
        f"{provider or '<empty>'} (expected one of: "
        f"{_ROUTER_SUPPORTED_LLM_PROVIDER_TEXT})"
    )


def validate_embedding_provider_config(
    settings: Settings, provider_override: str | None = None
) -> None:
    """
    Validate embedding provider policy and credentials with fail-closed semantics.

    Args:
        settings: Settings instance to validate.
        provider_override: Optional provider name to validate instead of settings.EMBEDDER_PROVIDER.

    Raises:
        LLMConfigError: if provider is unsupported or violates policy/credentials.
    """
    provider = _normalize_embedding_provider(
        provider_override or settings.EMBEDDER_PROVIDER
    )
    if not provider:
        raise LLMConfigError("EMBEDDER_PROVIDER is not configured")

    if provider == "local":
        # Local provider intentionally has no cloud policy requirements.
        return

    # Import lazily to avoid circular module import during config bootstrap.
    from guardian.core.egress import EgressDeniedError, assert_egress_allowed

    try:
        assert_egress_allowed(provider, settings=settings)
    except EgressDeniedError as exc:
        raise LLMConfigError(str(exc)) from exc

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise LLMConfigError("OPENAI_API_KEY is not configured")
        return

    # Other providers are validated by runtime provider registry construction.
    return


def get_settings() -> Settings:
    """Return the shared Settings instance for dependency injection."""
    return settings


def assert_config_coherence(core_settings: Settings | None = None) -> None:
    """
    Ensure security-relevant settings are coherent across config systems.

    Raises ConfigCoherenceError when guardian.core.config and guardian.config.core
    disagree on overlapping critical settings.
    """
    core = core_settings or get_settings()
    config_source = _normalize_config_source(
        getattr(core, "CODEXIFY_CONFIG_SOURCE", None)
    )
    _log_coherence_source_once(config_source)

    legacy_settings = _load_legacy_settings_for_coherence()
    if config_source == "core":
        validate_llm_config(core)
        return

    if legacy_settings is None:
        if config_source == "legacy":
            raise ConfigCoherenceError(
                "CODEXIFY_CONFIG_SOURCE=legacy was requested, but legacy settings are unavailable."
            )
        return

    if config_source == "legacy":
        _validate_legacy_llm_config(legacy_settings)
        return

    mismatches = _coherence_mismatches(core, legacy_settings)
    if mismatches:
        raise ConfigCoherenceError(_format_coherence_error(mismatches))
