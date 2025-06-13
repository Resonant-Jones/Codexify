# guardian/config.py

from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError
import sys

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
    NEBIUS_API_ENDPOINT: str = Field("https://api.studio.nebius.com/v1/chat/completions", description="Nebius API Endpoint")
    NEBIUS_MODEL: str = Field("deepseek-ai/DeepSeek-V3-0324-fast", description="Nebius Model")

    # Groq
    GROQ_API_KEY: str = Field(None, description="Groq API Key")
    GROQ_API_ENDPOINT: str = Field("https://api.groq.com/openai/v1", description="Groq API Endpoint")
    GROQ_MODEL: str = Field("llama3-70b-8192", description="Groq Model")

    # Backend selector
    AI_BACKEND: str = Field("ollama", description="Active AI backend (gemini, openai, nebius, groq, ollama)")

    # Ollama (Local LLM)
    OLLAMA_MODEL: str = Field("gemma3:4b", description="Ollama model tag (e.g. 'gemma3b:4b', 'gemma3:12b')")
    OLLAMA_HOST: str = Field("http://localhost:11434", description="Ollama server URL")

    # ===== PulseOS Routing Layer =====
    # These settings control AI routing behavior (local/cloud/hybrid)
    # AI Routing Toggles
    CLOUD_ONLY: bool = Field(False, description="Force all LLM calls to cloud backend (overrides hybrid/local)")
    HYBRID_ENABLED: bool = Field(True, description="Enable hybrid routing: cloud for research/search, local for chat/general)")
    LOCAL_MODEL_NAME: str = Field("gemma3n", description="Default local model name (e.g., gemma3n for mobile)")
    LOCAL_API_HOST: str = Field("http://localhost:11434", description="Local API host (or mobile endpoint)")
    CLOUD_MODEL_NAME: str = Field("gemini", description="Default cloud model name (e.g., gpt-4, gemini-pro)")
    CLOUD_API_HOST: str = Field("https://generativelanguage.googleapis.com/v1/models", description="Cloud API endpoint")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

def print_config_errors(e: ValidationError):
    print("❌ Configuration error: Missing or invalid settings.\n")
    for err in e.errors():
        field = err['loc'][0]
        print(f" - {field}: {err['msg']}")
    print("\nTo fix, set these as environment variables or in your .env file.")
    sys.exit(1)

def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        print_config_errors(e)
        # sys.exit will halt the program, so this return won't be reached