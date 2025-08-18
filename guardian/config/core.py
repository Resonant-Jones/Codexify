import sys
import os
from typing import Optional, Literal

from pydantic import Field, ValidationError, ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEFAULT_RATE_LIMIT: float = 0.1
    MEMORY_BATCH_SIZE: int = 100
    MEMORY_FLUSH_INTERVAL: float = 5.0
    MAX_MEMORY_BUFFER: int = 1000
    LOG_DIR: str = "logs"
    SAFE_MODE: bool = False
    SAFE_MODE_RATE_LIMIT: float = 0.01
    CACHE_ENABLED: bool = True
    PLUGIN_DIR: str = "guardian/plugins"

    # Core/legacy
    GENAI_API_KEY: Optional[str] = Field(None, description="Google Gemini API Key")
    GUARDIAN_DB_PATH: str = Field("guardian.db", description="SQLite DB path")
    NOTION_API_KEY: Optional[str] = Field(None, description="Notion API Key (optional)")

    # Google Gemini & Cloud
    GOOGLE_API_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API Key")
    OPENAI_API_ENDPOINT: str = Field("https://api.openai.com/v1", description="OpenAI API Endpoint")
    OPENAI_MODEL: str = Field("gpt-4", description="OpenAI model name (e.g., gpt-4, gpt-3.5-turbo)")

    # Groq
    GROQ_API_KEY: Optional[str] = Field(None, description="Groq API Key")
    GROQ_API_ENDPOINT: str = Field("https://api.groq.com/openai/v1", description="Groq API Endpoint")
    GROQ_MODEL: str = Field("meta-llama/llama-4-scout-17B-16e-instruct", description="Groq Model")
    GROQ_VISION_MODEL: str = Field(
        "meta-llama/llama-4-scout-17b-16e-instruct",
        description="Groq Vision model for image input",
    )

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = Field(None, description="Anthropic Claude API Key")
    ANTHROPIC_API_ENDPOINT: str = Field("https://api.anthropic.com/v1", description="Anthropic API Endpoint")
    ANTHROPIC_MODEL: str = Field("claude-3-opus-20240229", description="Anthropic Claude model name")

    # Backend selector
    AI_BACKEND: Literal["ollama", "openai", "gemini", "groq", "anthropic"] = Field(
        "groq", description="Active AI backend"
    )
    ENV: str = Field("development", description="Environment: development or production")

    # Ollama (Local LLM)
    OLLAMA_MODEL: str = Field(
        "gemma3n:e2b-it-q4_K_M",
        description="Ollama model tag (e.g. 'gemma3b:e4b-it-q4_K_M', 'gemma3n:e4b-it-q8_0', 'gemma3n:e4b-it-fp16')",
    )
    OLLAMA_HOST: str = Field("http://localhost:11434", description="Ollama server URL")

    # ===== PulseOS Routing Layer =====
    CLOUD_ONLY: bool = Field(False, description="Force all LLM calls to cloud backend")
    HYBRID_ENABLED: bool = Field(True, description="Enable hybrid routing")
    LOCAL_MODEL_NAME: str = Field("gemma3n", description="Default local model name")
    LOCAL_API_HOST: str = Field("http://localhost:11434", description="Local API host")
    CLOUD_MODEL_NAME: str = Field("gemini", description="Default cloud model name")
    CLOUD_API_HOST: str = Field(
        "https://generativelanguage.googleapis.com/v1/models",
        description="Cloud API endpoint",
    )

    @model_validator(mode="after")
    def _validate_provider_keys(self):
        """In development: do not hard-fail on missing keys; in production: enforce."""
        backend = (self.AI_BACKEND or "").lower()
        required_map = {
            "openai": ("OPENAI_API_KEY",),
            "gemini": ("GENAI_API_KEY", "GOOGLE_API_KEY"),
            "groq": ("GROQ_API_KEY",),
            "anthropic": ("ANTHROPIC_API_KEY",),
            "ollama": tuple(),
        }
        required = required_map.get(backend, tuple())
        if self.ENV == "production" and required:
            if backend == "gemini":
                has_any = any(bool(getattr(self, k, None)) for k in required)
                if not has_any:
                    raise ValueError("Missing API key for 'gemini': set GENAI_API_KEY or GOOGLE_API_KEY.")
            else:
                missing = [k for k in required if not getattr(self, k, None)]
                if missing:
                    raise ValueError(f"Missing API key(s) for '{backend}': {', '.join(missing)}")
        return self

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


def get_active_model(settings: Settings) -> str:
    backend = settings.AI_BACKEND.lower()
    if backend == "ollama":
        return settings.OLLAMA_MODEL
    if backend == "openai":
        return settings.OPENAI_MODEL
    if backend == "gemini":
        return settings.CLOUD_MODEL_NAME
    if backend == "groq":
        return settings.GROQ_MODEL
    if backend == "anthropic":
        return settings.ANTHROPIC_MODEL
    return "unknown"


def get_model_and_host(settings: Settings) -> tuple[str, str]:
    backend = settings.AI_BACKEND.lower()
    if backend == "ollama":
        return settings.OLLAMA_MODEL, settings.OLLAMA_HOST
    if backend == "openai":
        return settings.OPENAI_MODEL, settings.OPENAI_API_ENDPOINT
    if backend == "gemini":
        return settings.CLOUD_MODEL_NAME, settings.CLOUD_API_HOST
    if backend == "groq":
        return settings.GROQ_MODEL, settings.GROQ_API_ENDPOINT
    if backend == "anthropic":
        return settings.ANTHROPIC_MODEL, settings.ANTHROPIC_API_ENDPOINT
    return "unknown", "unknown"


def is_backend_capable(settings: Settings, capability: str) -> bool:
    capabilities = get_backend_capabilities(settings)
    return capabilities.get(capability, False)


def is_cloud_backend(settings: Settings) -> bool:
    if os.getenv("CLOUD_BACKEND", "false").lower() in ("1", "true", "yes"):
        return True
    return settings.AI_BACKEND.lower() in {"openai", "gemini", "groq", "anthropic"}


def get_backend_capabilities(settings: Settings) -> dict:
    capabilities = {
        "ollama": {"local": True, "can_stream": True, "sovereign": True},
        "openai": {"can_search": True, "can_stream": True},
        "gemini": {"can_search": True},
        "groq": {"can_stream": True, "can_vision": True},
        "anthropic": {"can_stream": True},
    }
    return capabilities.get(settings.AI_BACKEND.lower(), {})


def warn_if_missing_keys(settings: Settings):
    if settings.ENV == "production":
        return
    backend = (settings.AI_BACKEND or "").lower()
    if backend == "gemini":
        if not (getattr(settings, "GENAI_API_KEY", None) or getattr(settings, "GOOGLE_API_KEY", None)):
            print("⚠️  Warning: Missing Gemini API key (set GENAI_API_KEY or GOOGLE_API_KEY).")
        return
    key_attr = {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(backend)
    if key_attr and not getattr(settings, key_attr, None):
        print(f"⚠️  Warning: Missing {backend.capitalize()} API key.")


def print_config_errors(e: ValidationError):
    print("❌ Configuration error: Missing or invalid settings.\n")
    for err in e.errors():
        field = err["loc"][0]
        print(f" - {field}: {err['msg']}")
    print("\nTo fix, set these as environment variables or in your .env file.")


def config_summary(settings: Settings):
    print("🧩 PulseOS Backend Configuration Summary")
    print("─────────────────────────────────────────")
    print(f"🔧 AI_BACKEND         : {settings.AI_BACKEND}")
    print(f"💻 LOCAL_MODEL_NAME   : {settings.LOCAL_MODEL_NAME}")
    print(f"🌐 CLOUD_MODEL_NAME   : {settings.CLOUD_MODEL_NAME}")
    print(f"🧠 ACTIVE_MODEL       : {get_active_model(settings)}")
    print(f"☁️  CLOUD_ONLY         : {settings.CLOUD_ONLY}")
    print(f"🔀 HYBRID_ENABLED     : {settings.HYBRID_ENABLED}")
    print(f"📡 LOCAL_API_HOST     : {settings.LOCAL_API_HOST}")
    print(f"🌍 CLOUD_API_HOST     : {settings.CLOUD_API_HOST}")
    print(f"👁️  Vision Capable     : {is_backend_capable(settings, 'can_vision')}")
    print(f"🧬 GROQ_MODEL          : {settings.GROQ_MODEL}")
    print(f"🖼️  GROQ_VISION_MODEL   : {settings.GROQ_VISION_MODEL}")


def get_settings() -> Settings:
    """
    Load Settings. In production, fail fast on invalid/missing config.
    In tests/CI only, allow benign dummy fallbacks so import-time validation
    doesn’t kill pytest collection.
    """
    try:
        return Settings()
    except ValidationError as e:
        # Only soften behavior in test/CI contexts
        if (
            os.getenv("GUARDIAN_ALLOW_DUMMY_SETTINGS") == "1"
            or os.getenv("PYTEST_CURRENT_TEST")
            or os.getenv("GITHUB_ACTIONS") == "true"
        ):
            print_config_errors(e)
            overrides = {
                "GENAI_API_KEY": os.getenv("GENAI_API_KEY", "dummy"),
                "NOTION_API_KEY": os.getenv("NOTION_API_KEY", "dummy"),
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "dummy"),
            }
            return Settings(**overrides)
        # Not a test/CI context: keep strong validation
        raise


def print_config_status():
    try:
        settings = get_settings()
        config_summary(settings)
        warn_if_missing_keys(settings)
    except ValidationError as e:
        print_config_errors(e)


Config = Settings


def get_settings_no_env(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)
