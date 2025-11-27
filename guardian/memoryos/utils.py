from __future__ import annotations

import logging
from typing import List, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

import json
import os
import time
import uuid
from typing import Optional

import memoryos.prompts as prompts
import numpy as np
from sentence_transformers import SentenceTransformer


# ---- Common LLM Client Protocol ----
@runtime_checkable
class LLMClient(Protocol):
    def chat_completion(
        self,
        *,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        ...

    def tokenize(self, text: str) -> list[int]:
        ...


# ---- OpenAI Client ----
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def build_llm_client(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
):
    """Return an LLM client matching ``provider`` with helpful validation.

    Args:
        provider: Identifier such as ``"openai"`` or ``"groq"``.
        api_key: Secret to authenticate with the provider.
        base_url: Optional override for self-hosted or proxy deployments.

    Raises:
        ValueError: If the provider is unknown or required credentials are missing.
    """

    normalized = (provider or "").strip().lower()
    if normalized == "groq":
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER 'groq' requires GROQ_API_KEY to be configured."
            )
        return GroqClient(
            api_key=api_key, base_url=base_url or DEFAULT_GROQ_BASE_URL
        )

    if normalized == "openai":
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER 'openai' requires OPENAI_API_KEY to be configured."
            )
        return OpenAIClient(api_key=api_key, base_url=base_url)

    raise ValueError(f"Unsupported LLM provider '{provider}' for MemoryOS.")


class GroqClient:
    """LLM client using Groq's SDK (OpenAI-compatible).
    Exposes the minimal interface Memoryos expects.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        if not api_key:
            api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for GroqClient")
        # Import SDK lazily to avoid hard dependency when unused
        try:
            from groq import Groq  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Groq SDK not installed: {e}")
        self._client = (
            Groq(api_key=api_key, base_url=base_url)
            if base_url
            else Groq(api_key=api_key)
        )
        self._timeout = timeout

    def chat_completion(
        self,
        *,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return ""

    def tokenize(self, text: str) -> list[int]:
        # Simple, stable token estimate (enough for thresholds)
        return list(range(len(text.split())))


class OpenAIClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIClient")
        # Import SDK lazily to avoid hard dependency when unused
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"openai SDK not installed: {e}")
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_completion(
        self,
        *,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        logger.info(f"Calling OpenAI API. Model: {model}")
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {e}")
            # Fallback or error handling
            return ""

    def tokenize(self, text: str) -> list[int]:
        # Simple, stable token estimate (enough for thresholds)
        return list(range(len(text.split())))


# ---- Basic Utilities ----
def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def generate_id(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def ensure_directory_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


# ---- Embedding Utilities ----
_model_cache = {}


def get_embedding(text, model_name="all-MiniLM-L6-v2"):
    if model_name not in _model_cache:
        logger.info(f"Loading sentence transformer model: {model_name}")
        _model_cache[model_name] = SentenceTransformer(model_name)
    model = _model_cache[model_name]
    embedding = model.encode([text], convert_to_numpy=True)[0]
    return embedding


def normalize_vector(vec):
    vec = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


# ---- Time Decay Function ----
def compute_time_decay(
    event_timestamp_str, current_timestamp_str, tau_hours=24
):
    from datetime import datetime

    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        t_event = datetime.strptime(event_timestamp_str, fmt)
        t_current = datetime.strptime(current_timestamp_str, fmt)
        delta_hours = (t_current - t_event).total_seconds() / 3600.0
        return np.exp(-delta_hours / tau_hours)
    except ValueError:  # Handle cases where timestamp might be invalid
        return 0.1  # Default low recency


# ---- LLM-based Utility Functions ----


def gpt_summarize_dialogs(dialogs, client: LLMClient, model="gpt-4o-mini"):
    dialog_text = "\n".join(
        [
            f"User: {d.get('user_input','')} Assistant: {d.get('agent_response','')}"
            for d in dialogs
        ]
    )
    messages = [
        {"role": "system", "content": prompts.SUMMARIZE_DIALOGS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.SUMMARIZE_DIALOGS_USER_PROMPT.format(
                dialog_text=dialog_text
            ),
        },
    ]
    logger.info("Calling LLM to generate topic summary...")
    return client.chat_completion(model=model, messages=messages)


def gpt_generate_multi_summary(text, client: LLMClient, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": prompts.MULTI_SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.MULTI_SUMMARY_USER_PROMPT.format(text=text),
        },
    ]
    logger.info("Calling LLM to generate multi-topic summary...")
    response_text = client.chat_completion(model=model, messages=messages)
    try:
        summaries = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning(
            f"Warning: Could not parse multi-summary JSON: {response_text}"
        )
        summaries = []  # Return empty list or a default structure
    return {"input": text, "summaries": summaries}


def gpt_user_profile_analysis(
    dialogs, client: LLMClient, model="gpt-4o-mini", known_user_traits="None"
):
    """Analyze user personality profile from dialogs"""
    conversation = "\n".join(
        [
            f"User: {d.get('user_input','')} (Timestamp: {d.get('timestamp', '')})\nAssistant: {d.get('agent_response','')} (Timestamp: {d.get('timestamp', '')})"
            for d in dialogs
        ]
    )
    messages = [
        {
            "role": "system",
            "content": prompts.PERSONALITY_ANALYSIS_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": prompts.PERSONALITY_ANALYSIS_USER_PROMPT.format(
                conversation=conversation, known_user_traits=known_user_traits
            ),
        },
    ]
    logger.info("Calling LLM for user profile analysis...")
    result_text = client.chat_completion(model=model, messages=messages)
    return result_text.strip() if result_text else "None"


def gpt_knowledge_extraction(dialogs, client: LLMClient, model="gpt-4o-mini"):
    """Extract user private data and assistant knowledge from dialogs"""
    conversation = "\n".join(
        [
            f"User: {d.get('user_input','')} (Timestamp: {d.get('timestamp', '')})\nAssistant: {d.get('agent_response','')} (Timestamp: {d.get('timestamp', '')})"
            for d in dialogs
        ]
    )
    messages = [
        {
            "role": "system",
            "content": prompts.KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": prompts.KNOWLEDGE_EXTRACTION_USER_PROMPT.format(
                conversation=conversation
            ),
        },
    ]
    logger.info("Calling LLM for knowledge extraction...")
    result_text = client.chat_completion(model=model, messages=messages)

    private_data = "None"
    assistant_knowledge = "None"

    try:
        if "【User Private Data】" in result_text:
            private_data_start = result_text.find("【User Private Data】") + len(
                "【User Private Data】"
            )
            if "【Assistant Knowledge】" in result_text:
                private_data_end = result_text.find("【Assistant Knowledge】")
                private_data = result_text[
                    private_data_start:private_data_end
                ].strip()

                assistant_knowledge_start = result_text.find(
                    "【Assistant Knowledge】"
                ) + len("【Assistant Knowledge】")
                assistant_knowledge = result_text[
                    assistant_knowledge_start:
                ].strip()
            else:
                private_data = result_text[private_data_start:].strip()
        elif "【Assistant Knowledge】" in result_text:
            assistant_knowledge_start = result_text.find(
                "【Assistant Knowledge】"
            ) + len("【Assistant Knowledge】")
            assistant_knowledge = result_text[
                assistant_knowledge_start:
            ].strip()

    except Exception as e:
        logger.exception(
            f"Error parsing knowledge extraction: {e}. Raw result: {result_text}"
        )

    return {
        "private": private_data if private_data else "None",
        "assistant_knowledge": assistant_knowledge
        if assistant_knowledge
        else "None",
    }


# Keep the old function for backward compatibility, but mark as deprecated
def gpt_personality_analysis(
    dialogs, client: LLMClient, model="gpt-4o-mini", known_user_traits="None"
):
    """
    DEPRECATED: Use gpt_user_profile_analysis and gpt_knowledge_extraction instead.
    This function is kept for backward compatibility only.
    """
    # Call the new functions
    profile = gpt_user_profile_analysis(
        dialogs, client, model, known_user_traits
    )
    knowledge_data = gpt_knowledge_extraction(dialogs, client, model)

    return {
        "profile": profile,
        "private": knowledge_data["private"],
        "assistant_knowledge": knowledge_data["assistant_knowledge"],
    }


def gpt_update_profile(
    old_profile, new_analysis, client: LLMClient, model="gpt-4o-mini"
):
    messages = [
        {"role": "system", "content": prompts.UPDATE_PROFILE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.UPDATE_PROFILE_USER_PROMPT.format(
                old_profile=old_profile, new_analysis=new_analysis
            ),
        },
    ]
    logger.info("Calling LLM to update user profile...")
    return client.chat_completion(model=model, messages=messages)


def gpt_extract_theme(answer_text, client: LLMClient, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": prompts.EXTRACT_THEME_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.EXTRACT_THEME_USER_PROMPT.format(
                answer_text=answer_text
            ),
        },
    ]
    logger.info("Calling LLM to extract theme...")
    return client.chat_completion(model=model, messages=messages)


def llm_extract_keywords(text, client: LLMClient, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": prompts.EXTRACT_KEYWORDS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.EXTRACT_KEYWORDS_USER_PROMPT.format(text=text),
        },
    ]
    logger.info("Calling LLM to extract keywords...")
    response = client.chat_completion(model=model, messages=messages)
    return [kw.strip() for kw in response.split(",") if kw.strip()]


# ---- Functions from dynamic_update.py (to be used by Updater class) ----
def check_conversation_continuity(
    previous_page, current_page, client: LLMClient, model="gpt-4o-mini"
):
    prev_user = previous_page.get("user_input", "") if previous_page else ""
    prev_agent = (
        previous_page.get("agent_response", "") if previous_page else ""
    )

    user_prompt = prompts.CONTINUITY_CHECK_USER_PROMPT.format(
        prev_user=prev_user,
        prev_agent=prev_agent,
        curr_user=current_page.get("user_input", ""),
        curr_agent=current_page.get("agent_response", ""),
    )
    messages = [
        {"role": "system", "content": prompts.CONTINUITY_CHECK_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat_completion(
        model=model, messages=messages, temperature=0.0, max_tokens=10
    )
    return response.strip().lower() == "true"


def generate_page_meta_info(
    last_page_meta, current_page, client: LLMClient, model="gpt-4o-mini"
):
    current_conversation = f"User: {current_page.get('user_input', '')}\nAssistant: {current_page.get('agent_response', '')}"
    user_prompt = prompts.META_INFO_USER_PROMPT.format(
        last_meta=last_page_meta if last_page_meta else "None",
        new_dialogue=current_conversation,
    )
    messages = [
        {"role": "system", "content": prompts.META_INFO_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return client.chat_completion(
        model=model, messages=messages, temperature=0.3, max_tokens=100
    ).strip()


__all__ = ["LLMClient", "OpenAIClient", "GroqClient"]
