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
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from guardian.core import plugins as core_plugins
from guardian.plugins.plugin_manifest import PluginManifest


@dataclass
class TTSDiagnosticEvent:
    stage: str
    status: str
    detail: str | None = None


@dataclass
class TTSAttemptResult:
    ok: bool = False
    plugin_id: str | None = None
    base_url: str | None = None
    audio_source: str | None = None
    playback_command: str = "none"
    playback_command_path: str | None = None
    playback_return_code: int | None = None
    stdout_summary: str | None = None
    stderr_summary: str | None = None
    failure_kind: str | None = None
    failure_stage: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    trail: list[TTSDiagnosticEvent] = field(default_factory=list)

    def record(
        self, stage: str, status: str, detail: str | None = None
    ) -> None:
        self.trail.append(
            TTSDiagnosticEvent(stage=stage, status=status, detail=detail)
        )

    def fail(
        self,
        *,
        failure_kind: str,
        failure_stage: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.ok = False
        self.failure_kind = failure_kind
        self.failure_stage = failure_stage
        self.error_code = error_code
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plugin_id": self.plugin_id,
            "base_url": self.base_url,
            "audio_source": self.audio_source,
            "playback_command": self.playback_command,
            "playback_command_path": self.playback_command_path,
            "playback_return_code": self.playback_return_code,
            "stdout_summary": self.stdout_summary,
            "stderr_summary": self.stderr_summary,
            "failure_kind": self.failure_kind,
            "failure_stage": self.failure_stage,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "trail": [
                {
                    "stage": event.stage,
                    "status": event.status,
                    "detail": event.detail,
                }
                for event in self.trail
            ],
        }


@dataclass
class MaterializedAudio:
    path: str | None
    source: str | None
    temporary: bool
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class PlaybackCommandSelection:
    command_id: str
    argv: list[str] | None
    binary_path: str | None = None


def _build_tts_context(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Provide canonical plugin context fields when available.
    """
    return {
        "request_id": metadata.get("request_id"),
        "thread_id": metadata.get("thread_id"),
        "user_id": metadata.get("user_id"),
    }


def _failure_kind_for_plugin_error(code: str) -> str:
    return {
        "not_found": "plugin_manifest_not_found",
        "ambiguous": "plugin_selection_ambiguous",
        "timeout": "plugin_timeout",
        "transport_failure": "plugin_unreachable",
        "invalid_response": "invalid_payload",
        "remote_error": "plugin_remote_error",
    }.get(code, "plugin_invocation_failed")


def _summarize_text(value: str | None, limit: int = 200) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _materialize_audio_output(output: dict[str, Any]) -> MaterializedAudio:
    audio_path = output.get("audio_path")
    if isinstance(audio_path, str) and audio_path.strip():
        if os.path.exists(audio_path):
            return MaterializedAudio(
                path=audio_path,
                source="audio_path",
                temporary=False,
            )
        return MaterializedAudio(
            path=None,
            source="audio_path",
            temporary=False,
            error_code="audio_path_not_found",
            error_message="audio_path does not exist on disk",
        )

    audio_base64 = output.get("audio_base64")
    if not isinstance(audio_base64, str) or not audio_base64.strip():
        return MaterializedAudio(
            path=None,
            source=None,
            temporary=False,
            error_code="missing_audio_payload",
            error_message="plugin output did not contain audio_path or audio_base64",
        )

    fmt = str(output.get("format") or "wav").lower()
    suffix = ".wav" if fmt == "wav" else f".{fmt}"
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except (ValueError, binascii.Error):
        return MaterializedAudio(
            path=None,
            source="audio_base64",
            temporary=False,
            error_code="invalid_audio_base64",
            error_message="audio_base64 was not valid base64",
        )
    if not audio_bytes:
        return MaterializedAudio(
            path=None,
            source="audio_base64",
            temporary=False,
            error_code="empty_audio_payload",
            error_message="audio_base64 decoded to zero bytes",
        )

    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=suffix,
        prefix="codexify-tts-",
        delete=False,
    ) as handle:
        handle.write(audio_bytes)
        return MaterializedAudio(
            path=handle.name,
            source="audio_base64",
            temporary=True,
        )


def _playback_command_order() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return ("afplay", "ffplay", "aplay")
    if sys.platform.startswith("linux"):
        return ("aplay", "ffplay", "afplay")
    return ("ffplay", "afplay", "aplay")


def _select_playback_command(audio_path: str) -> PlaybackCommandSelection:
    for command_id in _playback_command_order():
        binary_path = shutil.which(command_id)
        if not binary_path:
            continue
        if command_id == "ffplay":
            return PlaybackCommandSelection(
                command_id=command_id,
                argv=[
                    binary_path,
                    "-nodisp",
                    "-autoexit",
                    "-loglevel",
                    "error",
                    audio_path,
                ],
                binary_path=binary_path,
            )
        return PlaybackCommandSelection(
            command_id=command_id,
            argv=[binary_path, audio_path],
            binary_path=binary_path,
        )
    return PlaybackCommandSelection(
        command_id="none",
        argv=None,
        binary_path=None,
    )


def _classify_playback_failure(
    stderr_summary: str | None,
    stdout_summary: str | None,
) -> str:
    combined = " ".join(
        part for part in (stderr_summary, stdout_summary) if part
    ).lower()
    device_markers = (
        "audio device",
        "alsa",
        "coreaudio",
        "pulse",
        "sdl",
        "speaker",
        "no default audio",
        "device or resource busy",
        "permission denied",
    )
    if any(marker in combined for marker in device_markers):
        return "local_audio_device_output_failure"
    return "playback_subprocess_failed"


def _resolve_tts_plugin(result: TTSAttemptResult) -> PluginManifest | None:
    manifests = core_plugins.list_plugin_manifests()
    result.record(
        "manifest_discovery",
        "ok" if manifests else "failed",
        f"count={len(manifests)}",
    )

    matches = [
        manifest
        for manifest in manifests
        if manifest.supports_operation("tts", "speak")
    ]
    if not matches:
        result.record("capability_resolution", "failed", "not_found")
        result.fail(
            failure_kind="plugin_manifest_not_found",
            failure_stage="capability_resolution",
            error_code="not_found",
            error_message="No plugin advertises tts.speak",
        )
        return None
    if len(matches) > 1:
        result.record("capability_resolution", "failed", "ambiguous")
        result.fail(
            failure_kind="plugin_selection_ambiguous",
            failure_stage="capability_resolution",
            error_code="ambiguous",
            error_message="Multiple plugins advertise tts.speak",
        )
        return None

    manifest = matches[0]
    result.plugin_id = manifest.id
    result.base_url = manifest.base_url
    result.record(
        "capability_resolution",
        "ok",
        f"plugin_id={manifest.id}",
    )
    return manifest


def _invoke_tts_plugin(
    manifest: PluginManifest,
    input_payload: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    return core_plugins.invoke_plugin(
        manifest.id,
        capability="tts",
        action="speak",
        input=input_payload,
        context=context,
    )


def _emit_attempt_log(result: TTSAttemptResult) -> None:
    trail = ",".join(
        f"{event.stage}:{event.status}"
        + (f"({event.detail})" if event.detail else "")
        for event in result.trail
    )
    log_fn = logger.info if result.ok else logger.warning
    log_fn(
        "[TTS] attempt status=%s plugin_id=%s base_url=%s audio_source=%s "
        "playback_command=%s failure_kind=%s error_code=%s "
        "playback_return_code=%s stderr_summary=%s trail=%s",
        "ok" if result.ok else "failed",
        result.plugin_id or "none",
        result.base_url or "none",
        result.audio_source or "none",
        result.playback_command,
        result.failure_kind or "none",
        result.error_code or "none",
        result.playback_return_code,
        result.stderr_summary or "none",
        trail or "none",
    )


def _cleanup_materialized_audio(materialized: MaterializedAudio) -> None:
    if not materialized.temporary or not materialized.path:
        return
    try:
        os.remove(materialized.path)
    except OSError:
        pass


def trigger_tts_with_result(
    text: str, metadata: dict[str, Any] | None = None
) -> TTSAttemptResult:
    metadata = metadata or {}
    input_payload = {"text": text, "metadata": metadata}
    context = _build_tts_context(metadata)
    result = TTSAttemptResult()
    manifest = _resolve_tts_plugin(result)
    if manifest is None:
        _emit_attempt_log(result)
        return result

    result.record(
        "plugin_invoke_start",
        "started",
        f"url={manifest.base_url}/invoke",
    )
    try:
        response = _invoke_tts_plugin(manifest, input_payload, context)
        result.record("plugin_invoke_success", "ok")
    except core_plugins.PluginFacadeError as exc:
        result.record("plugin_invoke_failure", "failed", exc.code)
        result.fail(
            failure_kind=_failure_kind_for_plugin_error(exc.code),
            failure_stage="plugin_invoke_failure",
            error_code=exc.code,
            error_message=exc.message,
        )
        _emit_attempt_log(result)
        return result
    except Exception as exc:
        result.record("plugin_invoke_failure", "failed", "unexpected_exception")
        result.fail(
            failure_kind="plugin_invocation_failed",
            failure_stage="plugin_invoke_failure",
            error_code="unexpected_exception",
            error_message=str(exc),
        )
        _emit_attempt_log(result)
        return result

    output = response.get("output") if isinstance(response, dict) else None
    if not isinstance(output, dict):
        result.record("output_parsing", "failed", "missing_output_object")
        result.fail(
            failure_kind="invalid_payload",
            failure_stage="output_parsing",
            error_code="missing_output_object",
            error_message="Plugin response did not contain an output object",
        )
        _emit_attempt_log(result)
        return result

    materialized = _materialize_audio_output(output)
    result.audio_source = materialized.source
    if materialized.error_code:
        result.record(
            "output_parsing",
            "ok",
            f"source={materialized.source or 'none'}",
        )
        result.record(
            "audio_materialization",
            "failed",
            materialized.error_code,
        )
        result.fail(
            failure_kind="invalid_payload",
            failure_stage="audio_materialization",
            error_code=materialized.error_code,
            error_message=materialized.error_message,
        )
        _emit_attempt_log(result)
        return result

    result.record(
        "output_parsing",
        "ok",
        f"source={materialized.source or 'none'}",
    )
    result.record(
        "audio_materialization",
        "ok",
        f"source={materialized.source or 'none'}",
    )

    selection = _select_playback_command(materialized.path or "")
    result.playback_command = selection.command_id
    result.playback_command_path = selection.binary_path
    result.record(
        "playback_command_selection",
        "ok" if selection.argv else "failed",
        f"command={selection.command_id}",
    )

    if selection.argv is None:
        result.fail(
            failure_kind="no_playback_binary_available",
            failure_stage="playback_command_selection",
            error_code="no_playback_binary_available",
            error_message="No local playback binary was available",
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result

    result.record(
        "playback_subprocess_launch",
        "started",
        f"command={selection.command_id}",
    )
    try:
        completed = subprocess.run(
            selection.argv,
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        result.stderr_summary = _summarize_text(exc.stderr)
        result.stdout_summary = _summarize_text(exc.stdout)
        result.record("playback_subprocess_exit_status", "failed", "timeout")
        result.fail(
            failure_kind="local_audio_device_output_failure",
            failure_stage="playback_subprocess_exit_status",
            error_code="playback_timeout",
            error_message="Playback subprocess timed out",
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result
    except FileNotFoundError as exc:
        result.record(
            "playback_subprocess_exit_status",
            "failed",
            "binary_not_found",
        )
        result.fail(
            failure_kind="no_playback_binary_available",
            failure_stage="playback_subprocess_exit_status",
            error_code="binary_not_found",
            error_message=str(exc),
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result
    except OSError as exc:
        result.record(
            "playback_subprocess_exit_status",
            "failed",
            "launch_error",
        )
        result.fail(
            failure_kind="local_audio_device_output_failure",
            failure_stage="playback_subprocess_exit_status",
            error_code="playback_launch_error",
            error_message=str(exc),
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result

    result.playback_return_code = completed.returncode
    result.stdout_summary = _summarize_text(completed.stdout)
    result.stderr_summary = _summarize_text(completed.stderr)
    if completed.returncode != 0:
        result.record(
            "playback_subprocess_exit_status",
            "failed",
            f"returncode={completed.returncode}",
        )
        result.fail(
            failure_kind=_classify_playback_failure(
                result.stderr_summary,
                result.stdout_summary,
            ),
            failure_stage="playback_subprocess_exit_status",
            error_code="playback_nonzero_exit",
            error_message="Playback subprocess exited non-zero",
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result

    result.record(
        "playback_subprocess_exit_status",
        "ok",
        f"returncode={completed.returncode}",
    )
    result.ok = True
    _emit_attempt_log(result)
    _cleanup_materialized_audio(materialized)
    return result


def get_tts_runtime_self_check() -> dict[str, Any]:
    manifests = core_plugins.list_plugin_manifests()
    selection = _select_playback_command("/tmp/codexify-tts-self-check.wav")
    matches = [
        manifest
        for manifest in manifests
        if manifest.supports_operation("tts", "speak")
    ]
    report: dict[str, Any] = {
        "manifest_discoverable": bool(matches),
        "discovered_plugin_ids": [manifest.id for manifest in manifests],
        "selected_plugin_id": None,
        "selected_plugin_base_url": None,
        "selected_provider": None,
        "selection_error": None,
        "plugin_health": {
            "reachable": False,
            "url": None,
            "status": None,
            "error_code": None,
            "failure_kind": None,
            "default_provider": None,
        },
        "playback": {
            "command": selection.command_id,
            "binary_path": selection.binary_path,
        },
    }
    if not matches:
        report["selection_error"] = "not_found"
        return report
    if len(matches) > 1:
        report["selection_error"] = "ambiguous"
        return report

    manifest = matches[0]
    report["selected_plugin_id"] = manifest.id
    report["selected_plugin_base_url"] = manifest.base_url
    report["plugin_health"]["url"] = f"{manifest.base_url}/health"

    try:
        payload = core_plugins.get_plugin_health(manifest.id)
    except core_plugins.PluginFacadeError as exc:
        report["plugin_health"]["error_code"] = exc.code
        report["plugin_health"][
            "failure_kind"
        ] = _failure_kind_for_plugin_error(exc.code)
        return report

    report["plugin_health"]["reachable"] = True
    report["plugin_health"]["status"] = payload.get("status")
    report["plugin_health"]["default_provider"] = payload.get(
        "default_provider"
    )
    report["selected_provider"] = payload.get("default_provider")
    return report


def trigger_tts_if_available(
    text: str, metadata: dict[str, Any] | None = None
) -> bool:
    return trigger_tts_with_result(text, metadata=metadata).ok
