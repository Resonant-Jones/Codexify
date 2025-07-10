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
    EMBEDDER_PROVIDER: str = Field(
        default="local",
        description="The embedding provider to use ('local', 'openai', 'groq').",
    )
    GROQ_API_KEY: str | None = Field(default=None, description="API key for Groq.")
    OPENAI_API_KEY: str | None = Field(default=None, description="API key for OpenAI.")
    DATA_STORAGE_PATH: str = Field(
        default="./data", description="Path for MemoryOS data storage."
    )
    AGENT_TIMEOUT_SECONDS: int = Field(
        default=30, description="Timeout in seconds for agent execution."
    )
    PROMPT_DIR_PATH: str | None = Field(
        default=None, description="Optional absolute path to the prompts directory."
    )


# Create a singleton instance that can be imported across the application
settings = Settings()
