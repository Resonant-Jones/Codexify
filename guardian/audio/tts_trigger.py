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


def _diagnostic_layer_for_error(code: str) -> str:
    return {
        "not_found": "manifest_or_capability_resolution",
        "ambiguous": "capability_resolution",
        "timeout": "timeout",
        "transport_failure": "transport_connectivity",
        "invalid_response": "plugin_response_validation",
        "remote_error": "remote_plugin_error",
    }.get(code, "plugin_invocation")


def trigger_tts_if_available(
    text: str, metadata: dict[str, Any] | None = None
) -> bool:
    metadata = metadata or {}
    input_payload = {"text": text, "metadata": metadata}
    context = _build_tts_context(metadata)

    try:
        response = invoke_capability(
            "tts",
            "speak",
            input_payload,
            context=context,
        )
        output = response.get("output") if isinstance(response, dict) else None
        if not isinstance(output, dict):
            logger.warning(
                "[TTS] failed layer=downstream_output_handling reason=missing_output_object"
            )
            return False
        return True
    except PluginFacadeError as e:
        layer = _diagnostic_layer_for_error(e.code)
        logger.warning(
            "[TTS] failed layer=%s code=%s message=%s",
            layer,
            e.code,
            e.message,
        )
        return False
    except Exception as e:
        logger.error("[TTS] Error calling TTS plugin: %s", e)
        return False
