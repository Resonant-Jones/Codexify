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
    AI_BACKEND: str = Field("gemini", description="Active AI backend (gemini, openai, nebius, groq)")

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