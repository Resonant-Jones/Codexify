# guardian/config.py

import sys
import os
from typing import Optional, Literal

from pydantic import Field, ValidationError, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEFAULT_RATE_LIMIT: float = 0.1  # seconds between plugin calls
    MEMORY_BATCH_SIZE: int = 100  # Default batch size for the SafeLogger
    MEMORY_FLUSH_INTERVAL: float = 5.0  # Or your default interval in seconds
    MAX_MEMORY_BUFFER: int = 1000  # Or whatever cap you want
    LOG_DIR: str = "logs"  # Default log directory for SafeLogger
    SAFE_MODE: bool = False
    SAFE_MODE_RATE_LIMIT: float = 0.01
    CACHE_ENABLED: bool = (
        True  # Toggle for enabling/disabling caching in plugin execution
    )
    PLUGIN_DIR: str = "guardian/plugins"  # Default plugin directory path
    # Core/legacy
    GENAI_API_KEY: str = Field(None, description="Google Gemini API Key")
    GUARDIAN_DB_PATH: str = Field("guardian.db", description="SQLite DB path")
    NOTION_API_KEY: str = Field(None, description="Notion API Key (optional)")

    # Google Gemini & Cloud
    GOOGLE_API_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: str = Field(None, description="OpenAI API Key")
    OPENAI_API_ENDPOINT: str = Field(
        "https://api.openai.com/v1", description="OpenAI API Endpoint"
    )
    OPENAI_MODEL: str = Field(
        "gpt-4", description="OpenAI model name (e.g., gpt-4, gpt-3.5-turbo)"
    )
    # Groq
    GROQ_API_KEY: str = Field(None, description="Groq API Key")
    GROQ_API_ENDPOINT: str = Field(
        "https://api.groq.com/openai/v1", description="Groq API Endpoint"
    )
    GROQ_MODEL: str = Field(
        "meta-llama/llama-4-scout-17B-16e-instruct", description="Groq Model"
    )
    GROQ_VISION_MODEL: str = Field(
        "meta-llama/llama-4-scout-17b-16e-instruct",
        description="Groq Vision model for image input",
    )

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(None, description="Anthropic Claude API Key")
    ANTHROPIC_API_ENDPOINT: str = Field(
        "https://api.anthropic.com/v1", description="Anthropic API Endpoint"
    )
    ANTHROPIC_MODEL: str = Field(
        "claude-3-opus-20240229", description="Anthropic Claude model name"
    )

    # Backend selector
    AI_BACKEND: Literal["ollama", "openai", "gemini", "groq", "anthropic"] = Field(
        "groq", description="Active AI backend"
    )
    ENV: str = Field(
        "development", description="Environment: development or production"
    )

    # Ollama (Local LLM)
    OLLAMA_MODEL: str = Field(
        "gemma3n:e2b-it-q4_K_M",
        description="Ollama model tag (e.g. 'gemma3b:e4b-it-q4_K_M', 'gemma3n:e4b-it-q8_0', 'gemma3n:e4b-it-fp16')",
    )
    OLLAMA_HOST: str = Field("http://localhost:11434", description="Ollama server URL")

    # ===== PulseOS Routing Layer =====
    # These settings control AI routing behavior (local/cloud/hybrid)
    # AI Routing Toggles
    CLOUD_ONLY: bool = Field(
        False,
        description="Force all LLM calls to cloud backend (overrides hybrid/local)",
    )
    HYBRID_ENABLED: bool = Field(
        True,
        description="Enable hybrid routing: cloud for research/search, local for chat/general)",
    )
    LOCAL_MODEL_NAME: str = Field(
        "gemma3n", description="Default local model name (e.g., gemma3n for mobile)"
    )
    LOCAL_API_HOST: str = Field(
        "http://localhost:11434", description="Local API host (or mobile endpoint)"
    )
    CLOUD_MODEL_NAME: str = Field(
        "gemini", description="Default cloud model name (e.g., gpt-4, gemini-pro)"
    )
    CLOUD_API_HOST: str = Field(
        "https://generativelanguage.googleapis.com/v1/models",
        description="Cloud API endpoint",
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


# ===== Helper functions for backend/model/key selection =====


def get_active_model(settings: Settings) -> str:
    """Resolve the currently active model based on backend setting."""
    backend = settings.AI_BACKEND.lower()
    if backend == "ollama":
        return settings.OLLAMA_MODEL
    elif backend == "openai":
        return "gpt-4"
    elif backend == "gemini":
        return settings.CLOUD_MODEL_NAME
    elif backend == "groq":
        return settings.GROQ_MODEL
    elif backend == "anthropic":
        return settings.ANTHROPIC_MODEL
    return "unknown"


# ===== New helper function: get_model_and_host =====


def get_model_and_host(settings: Settings) -> tuple[str, str]:
    """Resolve both the model name and its corresponding endpoint based on the backend."""
    backend = settings.AI_BACKEND.lower()
    if backend == "ollama":
        return settings.OLLAMA_MODEL, settings.OLLAMA_HOST
    elif backend == "openai":
        return "gpt-4", "https://api.openai.com/v1"
    elif backend == "gemini":
        return settings.CLOUD_MODEL_NAME, settings.CLOUD_API_HOST
    elif backend == "groq":
        return settings.GROQ_MODEL, settings.GROQ_API_ENDPOINT
    elif backend == "anthropic":
        return settings.ANTHROPIC_MODEL, settings.ANTHROPIC_API_ENDPOINT
    return "unknown", "unknown"


# ===== Backend capability helper =====
def is_backend_capable(settings: Settings, capability: str) -> bool:
    """Check if the current backend supports a specific capability (e.g., can_search, can_stream)."""
    capabilities = get_backend_capabilities(settings)
    return capabilities.get(capability, False)


# ===== Backend helper functions =====
def is_cloud_backend(settings: Settings) -> bool:
    """
    Return True if CLOUD_BACKEND environment variable is truthy
    or if the AI_BACKEND setting indicates a cloud provider.
    """
    # Environment override
    if os.getenv("CLOUD_BACKEND", "false").lower() in ("1", "true", "yes"):
        return True
    # Fallback to settings.AI_BACKEND
    return settings.AI_BACKEND.lower() in {"openai", "gemini", "groq"}


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
    """Warn if required API keys are missing based on active backend."""
    BACKEND_KEYS = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    backend = settings.AI_BACKEND.lower()
    key_attr = BACKEND_KEYS.get(backend)
    if key_attr and not getattr(settings, key_attr, None):
        print(f"⚠️  Warning: Missing {backend.capitalize()} API key.")


def print_config_errors(e: ValidationError):
    print("❌ Configuration error: Missing or invalid settings.\n")
    for err in e.errors():
        field = err["loc"][0]
        print(f" - {field}: {err['msg']}")
    print("\nTo fix, set these as environment variables or in your .env file.")


# ===== PulseOS Configuration Summary =====
def config_summary(settings: Settings):
    """Print a summary of the current configuration state."""
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
    try:
        settings = Settings()
    except ValidationError as e:
        print_config_errors(e)
        raise

    # Enforce Groq-only backend in production
    if settings.ENV == "production" and settings.AI_BACKEND.lower() != "groq":
        raise RuntimeError("❌ In production, only the Groq backend is supported.")

    if settings.ENV == "production":
        settings.GROQ_MODEL = "meta-llama/llama-4-scout-17B-16e-instruct"

    return settings


# ===== CLI Utility Wrapper =====
def print_config_status():
    """Convenience function to print config summary + key warnings."""
    try:
        settings = get_settings()
        config_summary(settings)
        warn_if_missing_keys(settings)
    except ValidationError as e:
        print_config_errors(e)


# Alias for legacy compatibility
Config = Settings
