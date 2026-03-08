"""
TTS Trigger
~~~~~~~~~~~

Discovery-aware trigger for local TTS plugins (if available).
"""

import base64
import binascii
import logging
import os
import shutil
import subprocess
import tempfile
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


def _materialize_audio_output(output: dict[str, Any]) -> str | None:
    audio_path = output.get("audio_path")
    if isinstance(audio_path, str) and audio_path.strip():
        if os.path.exists(audio_path):
            return audio_path
        logger.warning(
            "[TTS] failed layer=output_materialization reason=audio_path_not_found"
        )
        return None

    audio_base64 = output.get("audio_base64")
    if not isinstance(audio_base64, str) or not audio_base64.strip():
        logger.warning(
            "[TTS] failed layer=output_materialization reason=missing_audio_payload"
        )
        return None

    fmt = str(output.get("format") or "wav").lower()
    suffix = ".wav" if fmt == "wav" else f".{fmt}"
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except (ValueError, binascii.Error):
        logger.warning(
            "[TTS] failed layer=output_materialization reason=invalid_audio_base64"
        )
        return None
    if not audio_bytes:
        logger.warning(
            "[TTS] failed layer=output_materialization reason=empty_audio_payload"
        )
        return None

    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=suffix,
        prefix="codexify-tts-",
        delete=False,
    ) as handle:
        handle.write(audio_bytes)
        return handle.name


def _playback_command_for(audio_path: str) -> list[str] | None:
    if shutil.which("afplay"):
        return ["afplay", audio_path]
    if shutil.which("aplay"):
        return ["aplay", audio_path]
    if shutil.which("ffplay"):
        return [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            audio_path,
        ]
    return None


def _dispatch_playback(audio_path: str) -> bool:
    command = _playback_command_for(audio_path)
    if command is None:
        logger.warning(
            "[TTS] failed layer=playback_dispatch reason=no_local_audio_player"
        )
        return False

    try:
        result = subprocess.run(
            command,
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "[TTS] failed layer=local_audio_device_output reason=timeout"
        )
        return False
    except Exception as exc:
        logger.warning(
            "[TTS] failed layer=local_audio_device_output reason=launch_error detail=%s",
            str(exc),
        )
        return False

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.warning(
            "[TTS] failed layer=local_audio_device_output reason=nonzero_exit code=%s detail=%s",
            result.returncode,
            stderr[:200],
        )
        return False
    return True


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
                "[TTS] failed layer=synthesis_response_parsing reason=missing_output_object"
            )
            return False

        audio_path = _materialize_audio_output(output)
        if not audio_path:
            return False

        is_temp_audio = not (
            isinstance(output.get("audio_path"), str)
            and output.get("audio_path")
        )
        try:
            played = _dispatch_playback(audio_path)
            if not played:
                logger.warning(
                    "[TTS] failed layer=playback_dispatch reason=playback_failed"
                )
                return False
            return True
        finally:
            if is_temp_audio:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
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
