import logging
import os

import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def chat_with_ai(messages, model=None):
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        return call_groq(messages, model or "llama3-70b-8192")
    elif provider == "openai":
        return call_openai(messages, model or "gpt-4")
    else:
        logger.warning(f"Unsupported LLM provider: {provider}")
        raise HTTPException(
            status_code=501, detail=f"Unsupported LLM provider: {provider}"
        )


def call_groq(messages, model):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "temperature": 0.7}
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("GROQ backend error")
        raise HTTPException(status_code=502, detail=str(e))


def call_openai(messages, model):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "temperature": 0.7}
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("OpenAI backend error")
        raise HTTPException(status_code=502, detail=str(e))
