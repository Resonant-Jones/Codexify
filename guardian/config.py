# guardian/config.py

import sys

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core/legacy
    GENAI_API_KEY: str = Field(None, description="Google Gemini API Key")
    GUARDIAN_DB_PATH: str = Field("guardian.db", description="SQLite DB path")
    NOTION_API_KEY: str = Field(None, description="Notion API Key (optional)")

    # Google Gemini & Cloud
    GOOGLE_API_KEY: str = Field(None, description="Google API Key (Gemini/other)")

    # OpenAI
    OPENAI_API_KEY: str = Field(None, description="OpenAI API Key")

    # Nebius
    NEBIUS_API_KEY: str = Field(None, description="Nebius API Key")
    NEBIUS_API_ENDPOINT: str = Field(
        "https://api.studio.nebius.com/v1/chat/completions",
        description="Nebius API Endpoint",
    )
    NEBIUS_MODEL: str = Field(
        "deepseek-ai/DeepSeek-V3-0324-fast", description="Nebius Model"
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

    # Backend selector
    AI_BACKEND: str = Field("groq", description="Active AI backend")
    ENV: str = Field(
        "development", description="Environment: development or production"
    )

    # Ollama (Local LLM)
    OLLAMA_MODEL: str = Field(
        "gemma3:4b", description="Ollama model tag (e.g. 'gemma3b:4b', 'gemma3:12b')"
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }


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
    elif backend == "nebius":
        return settings.NEBIUS_MODEL
    elif backend == "groq":
        return settings.GROQ_MODEL
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
    elif backend == "nebius":
        return settings.NEBIUS_MODEL, settings.NEBIUS_API_ENDPOINT
    elif backend == "groq":
        return settings.GROQ_MODEL, settings.GROQ_API_ENDPOINT
    return "unknown", "unknown"


# ===== Backend capability helper =====
def is_backend_capable(settings: Settings, capability: str) -> bool:
    """Check if the current backend supports a specific capability (e.g., can_search, can_stream)."""
    capabilities = get_backend_capabilities(settings)
    return capabilities.get(capability, False)


# ===== Backend helper functions =====
def is_cloud_backend(settings: Settings) -> bool:
    return settings.AI_BACKEND.lower() in {"openai", "gemini", "nebius", "groq"}


def get_backend_capabilities(settings: Settings) -> dict:
    capabilities = {
        "ollama": {"local": True, "can_stream": True, "sovereign": True},
        "openai": {"can_search": True, "can_stream": True},
        "gemini": {"can_search": True},
        "nebius": {"can_stream": True},
        "groq": {"can_stream": True, "can_vision": True},
    }
    return capabilities.get(settings.AI_BACKEND.lower(), {})


def warn_if_missing_keys(settings: Settings):
    """Warn if required API keys are missing based on active backend."""
    backend = settings.AI_BACKEND.lower()
    if backend == "openai" and not settings.OPENAI_API_KEY:
        print("⚠️  Warning: Missing OpenAI API key.")
    elif backend == "gemini" and not settings.GENAI_API_KEY:
        print("⚠️  Warning: Missing Gemini API key.")
    elif backend == "nebius" and not settings.NEBIUS_API_KEY:
        print("⚠️  Warning: Missing Nebius API key.")
    elif backend == "groq" and not settings.GROQ_API_KEY:
        print("⚠️  Warning: Missing Groq API key.")


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
    settings = Settings()

    # Enforce Groq-only backend in production
    if settings.ENV == "production" and settings.AI_BACKEND.lower() != "groq":
        raise RuntimeError("❌ In production, only the Groq backend is supported.")

    if settings.ENV == "production":
        settings.GROQ_MODEL = "groq-1"

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
