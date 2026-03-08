"""
TTS Trigger
~~~~~~~~~~~

Discovery-aware trigger for local TTS plugins (if available).
"""

import logging
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from guardian.core.plugins import PluginFacadeError, invoke_capability


def _build_tts_context(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Provide canonical plugin context fields when available.
    """
    return {
        "request_id": metadata.get("request_id"),
        "thread_id": metadata.get("thread_id"),
        "user_id": metadata.get("user_id"),
    }


def trigger_tts_if_available(
    text: str, metadata: dict[str, Any] | None = None
) -> bool:
    metadata = metadata or {}
    input_payload = {"text": text, "metadata": metadata}
    context = _build_tts_context(metadata)

    try:
        invoke_capability(
            "tts",
            "speak",
            input_payload,
            context=context,
        )
        return True
    except PluginFacadeError as e:
        logger.warning(
            "[TTS] canonical plugin invocation failed code=%s message=%s",
            e.code,
            e.message,
        )
        return False
    except Exception as e:
        logger.error("[TTS] Error calling TTS plugin: %s", e)
        return False
