# guardian/config.py

from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError
import sys

class Settings(BaseSettings):
    GENAI_API_KEY: str = Field(..., description="Google Gemini API Key")
    GUARDIAN_DB_PATH: str = Field("guardian.db", description="SQLite DB path")
    NOTION_API_KEY: str = Field(None, description="Notion API Key (optional)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

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