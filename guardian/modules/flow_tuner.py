"""LLM Flow Tuner
================

Configuration helper for controlling how much narrative context is
injected into LLM prompts and the maximum token window sizes for
local vs. cloud inference.

Usage example::

    from guardian.modules.flow_tuner import FlowConfig
    config = FlowConfig()
    print(config.context_window)
"""

from __future__ import annotations

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class FlowConfig(BaseSettings):
    """Flow tuning parameters."""

    context_window: int = Field(4096, description="Max narrative tokens")
    injection_ratio: float = Field(0.5, description="Context injection ratio")
    local_max_tokens: int = Field(2048, description="Local model token cap")
    cloud_max_tokens: int = Field(4096, description="Cloud model token cap")

    # Add these to match .env keys
    genai_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    nebius_api_key: Optional[str] = None
    nebius_api_endpoint: Optional[str] = None
    nebius_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_api_endpoint: Optional[str] = None
    groq_model: Optional[str] = None
    ai_backend: Optional[str] = None
    github_bot_token: Optional[str] = None
    guardian_llm_backend: Optional[str] = None
    guardian_model_name: Optional[str] = None
    guardian_ollama_endpoint: Optional[str] = None
    guardian_db_path: Optional[str] = None

    model_config = {
        "env_prefix": "FLOW_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
