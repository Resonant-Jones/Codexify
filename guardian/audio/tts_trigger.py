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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

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
    output_keys: list[str] = field(default_factory=list)
    artifact_path: str | None = None
    artifact_bytes: int | None = None
    containerized: bool | None = None
    containerization_reason: str | None = None
    host_audible_playback_plausible: bool | None = None
    playback_attempted: bool = False
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
            "output_keys": self.output_keys,
            "artifact_path": self.artifact_path,
            "artifact_bytes": self.artifact_bytes,
            "containerized": self.containerized,
            "containerization_reason": self.containerization_reason,
            "host_audible_playback_plausible": self.host_audible_playback_plausible,
            "playback_attempted": self.playback_attempted,
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
    size_bytes: int | None = None
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


def _failure_kind_for_plugin_error(
    code: str, details: Any | None = None
) -> str:
    remote_error = None
    if isinstance(details, dict):
        candidate = details.get("error")
        if isinstance(candidate, dict):
            remote_error = candidate.get("code")
    return {
        "not_found": "plugin_manifest_not_found",
        "ambiguous": "plugin_selection_ambiguous",
        "timeout": "plugin_timeout",
        "transport_failure": "plugin_unreachable",
        "service_not_ready": "plugin_not_ready",
        "service_startup_failed": "plugin_startup_failed",
        "invalid_response": "invalid_payload",
        "remote_error": "plugin_remote_error",
    }.get(remote_error or code, "plugin_invocation_failed")


def _effective_plugin_error_code(code: str, details: Any | None = None) -> str:
    if isinstance(details, dict):
        candidate = details.get("error")
        if isinstance(candidate, dict):
            remote_code = candidate.get("code")
            if isinstance(remote_code, str) and remote_code.strip():
                return remote_code
    return code


def _effective_plugin_error_message(
    default_message: str, details: Any | None = None
) -> str:
    if isinstance(details, dict):
        candidate = details.get("error")
        if isinstance(candidate, dict):
            remote_message = candidate.get("message")
            if isinstance(remote_message, str) and remote_message.strip():
                return remote_message
    return default_message


def _summarize_text(value: str | None, limit: int = 200) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _tts_invoke_timeout_seconds() -> float:
    raw = (os.getenv("CODEXIFY_TTS_INVOKE_TIMEOUT_SECONDS") or "").strip()
    if not raw:
        return 120.0
    try:
        return max(float(raw), 1.0)
    except ValueError:
        return 120.0


def _detect_containerized_runtime() -> tuple[bool, str | None]:
    if os.path.exists("/.dockerenv"):
        return True, "/.dockerenv"

    cgroup_path = Path("/proc/1/cgroup")
    try:
        contents = cgroup_path.read_text(encoding="utf-8")
    except OSError:
        contents = ""

    if any(
        token in contents
        for token in ("docker", "containerd", "kubepods", "podman")
    ):
        return True, str(cgroup_path)
    return False, None


def _host_inspectable_artifact_dir(containerized: bool) -> Path | None:
    if not containerized:
        return None

    for candidate in (
        Path("/app/guardian/tts_output/runtime"),
        Path("/app/codexify/tts_output/runtime"),
    ):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return candidate
    return None


def _artifact_filename(request_id: str | None, suffix: str) -> str:
    label = (request_id or "adhoc").strip().replace("/", "_").replace(" ", "_")
    label = "".join(ch for ch in label if ch.isalnum() or ch in {"-", "_"})
    label = label or "adhoc"
    return f"tts-{label}-{int(time.time())}{suffix}"


def _preserve_artifact_for_inspection(
    materialized: MaterializedAudio, request_id: str | None, containerized: bool
) -> str | None:
    if not materialized.path:
        return None

    target_dir = _host_inspectable_artifact_dir(containerized)
    if target_dir is None:
        return materialized.path

    source = Path(materialized.path)
    try:
        if target_dir in source.parents:
            return str(source)
    except ValueError:
        pass

    suffix = source.suffix or ".wav"
    target = target_dir / _artifact_filename(request_id, suffix)
    try:
        shutil.copyfile(source, target)
    except OSError:
        return materialized.path
    return str(target)


def _materialize_audio_output(output: dict[str, Any]) -> MaterializedAudio:
    audio_path = output.get("audio_path")
    if isinstance(audio_path, str) and audio_path.strip():
        if os.path.exists(audio_path):
            try:
                size_bytes = os.path.getsize(audio_path)
            except OSError:
                size_bytes = None
            if size_bytes is not None and size_bytes <= 0:
                return MaterializedAudio(
                    path=None,
                    source="audio_path",
                    temporary=False,
                    error_code="empty_audio_file",
                    error_message="audio_path exists but the file is empty",
                )
            return MaterializedAudio(
                path=audio_path,
                source="audio_path",
                temporary=False,
                size_bytes=size_bytes,
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
            size_bytes=0,
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
            size_bytes=len(audio_bytes),
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
    envelope = core_plugins._build_invoke_envelope(
        plugin_id=manifest.id,
        capability="tts",
        action="speak",
        input=input_payload,
        context=context,
    )
    url = f"{manifest.base_url}/invoke"

    try:
        response = requests.post(
            url,
            json=envelope,
            headers=core_plugins._INVOKE_HEADERS,
            timeout=_tts_invoke_timeout_seconds(),
        )
    except requests.RequestException as exc:
        core_plugins._handle_transport_error(
            exc,
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
        )

    payload = core_plugins._parse_response_payload(
        response,
        plugin_id=manifest.id,
        capability="tts",
        action="speak",
    )

    if response.status_code >= 400:
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_REMOTE_ERROR,
            message="Plugin returned an error response",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details={
                "status_code": response.status_code,
                "error": payload.get("error"),
            },
        )
    if payload.get("error") not in (None, ""):
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_REMOTE_ERROR,
            message="Plugin returned an application error",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details=payload.get("error"),
        )
    if "ok" in payload and not isinstance(payload["ok"], bool):
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_INVALID_RESPONSE,
            message="Plugin response field 'ok' must be boolean when present",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details={"status_code": response.status_code},
        )
    if payload.get("ok") is False and payload.get("error") in (None, ""):
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_INVALID_RESPONSE,
            message="Plugin response marked failure without canonical error payload",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details={"status_code": response.status_code},
        )
    if "output" not in payload:
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_INVALID_RESPONSE,
            message="Plugin response missing required 'output' field",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details={"status_code": response.status_code},
        )
    if not isinstance(payload["output"], dict):
        raise core_plugins.PluginFacadeError(
            code=core_plugins.ERROR_INVALID_RESPONSE,
            message="Plugin response field 'output' must be an object",
            plugin_id=manifest.id,
            capability="tts",
            action="speak",
            details={"status_code": response.status_code},
        )
    return payload


def _emit_attempt_log(result: TTSAttemptResult) -> None:
    trail = ",".join(
        f"{event.stage}:{event.status}"
        + (f"({event.detail})" if event.detail else "")
        for event in result.trail
    )
    log_fn = logger.info if result.ok else logger.warning
    log_fn(
        "[TTS] attempt status=%s plugin_id=%s base_url=%s output_keys=%s "
        "audio_source=%s artifact_path=%s artifact_bytes=%s "
        "playback_command=%s playback_binary=%s containerized=%s "
        "host_audible_playback_plausible=%s playback_attempted=%s "
        "failure_kind=%s error_code=%s playback_return_code=%s "
        "stdout_summary=%s stderr_summary=%s trail=%s",
        "ok" if result.ok else "failed",
        result.plugin_id or "none",
        result.base_url or "none",
        ",".join(result.output_keys) if result.output_keys else "none",
        result.audio_source or "none",
        result.artifact_path or "none",
        result.artifact_bytes,
        result.playback_command,
        result.playback_command_path or "none",
        result.containerized,
        result.host_audible_playback_plausible,
        result.playback_attempted,
        result.failure_kind or "none",
        result.error_code or "none",
        result.playback_return_code,
        result.stdout_summary or "none",
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
    containerized, containerization_reason = _detect_containerized_runtime()
    result.containerized = containerized
    result.containerization_reason = containerization_reason
    selection_probe = _select_playback_command("/tmp/codexify-tts-probe.wav")
    result.playback_command = selection_probe.command_id
    result.playback_command_path = selection_probe.binary_path
    result.host_audible_playback_plausible = (
        bool(selection_probe.argv) and not containerized
    )
    manifest = _resolve_tts_plugin(result)
    if manifest is None:
        _emit_attempt_log(result)
        return result

    result.record(
        "runtime_environment",
        "containerized" if containerized else "host",
        containerization_reason or "none",
    )
    result.record(
        "playback_command_selection",
        "ok" if selection_probe.argv else "failed",
        f"command={selection_probe.command_id} binary={selection_probe.binary_path or 'none'}",
    )

    result.record(
        "plugin_invoke_start",
        "started",
        f"url={manifest.base_url}/invoke",
    )
    try:
        response = _invoke_tts_plugin(manifest, input_payload, context)
        result.record("plugin_invoke_success", "ok")
    except core_plugins.PluginFacadeError as exc:
        effective_code = _effective_plugin_error_code(exc.code, exc.details)
        result.record("plugin_invoke_failure", "failed", effective_code)
        result.fail(
            failure_kind=_failure_kind_for_plugin_error(exc.code, exc.details),
            failure_stage="plugin_invoke_failure",
            error_code=effective_code,
            error_message=_effective_plugin_error_message(
                exc.message, exc.details
            ),
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

    result.output_keys = sorted(output.keys())
    materialized = _materialize_audio_output(output)
    result.audio_source = materialized.source
    if materialized.error_code:
        result.record(
            "output_parsing",
            "ok",
            f"keys={','.join(result.output_keys) or 'none'} source={materialized.source or 'none'}",
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
        f"keys={','.join(result.output_keys) or 'none'} source={materialized.source or 'none'}",
    )

    request_id = context.get("request_id")
    result.artifact_path = _preserve_artifact_for_inspection(
        materialized,
        request_id,
        containerized,
    )
    result.artifact_bytes = materialized.size_bytes
    result.record(
        "audio_materialization",
        "ok",
        "source=%s path=%s bytes=%s"
        % (
            materialized.source or "none",
            result.artifact_path or materialized.path or "none",
            materialized.size_bytes,
        ),
    )
    selection = _select_playback_command(materialized.path or "")
    result.playback_command = selection.command_id
    result.playback_command_path = selection.binary_path
    result.host_audible_playback_plausible = (
        bool(selection.argv) and not containerized
    )
    result.record(
        "playback_command_selection",
        "ok" if selection.argv else "failed",
        f"command={selection.command_id} binary={selection.binary_path or 'none'}",
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

    if containerized:
        result.record(
            "playback_host_audibility",
            "failed",
            "container_local_playback",
        )
        result.fail(
            failure_kind="container_local_playback_not_host_audible",
            failure_stage="playback_host_audibility",
            error_code="container_local_playback",
            error_message=(
                "Synthesis produced audio, but backend-local playback is running "
                "inside a container and is not host-audible"
            ),
        )
        _emit_attempt_log(result)
        _cleanup_materialized_audio(materialized)
        return result

    result.playback_attempted = True
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
    containerized, containerization_reason = _detect_containerized_runtime()
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
        "runtime": {
            "containerized": containerized,
            "containerization_reason": containerization_reason,
        },
        "plugin_health": {
            "reachable": False,
            "url": None,
            "status": None,
            "ready": None,
            "startup_phase": None,
            "error_code": None,
            "failure_kind": None,
            "default_provider": None,
        },
        "playback": {
            "command": selection.command_id,
            "binary_path": selection.binary_path,
            "host_audible_playback_plausible": bool(selection.argv)
            and not containerized,
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
    report["plugin_health"]["ready"] = payload.get("ready")
    report["plugin_health"]["startup_phase"] = payload.get("startup_phase")
    report["plugin_health"]["default_provider"] = payload.get(
        "default_provider"
    )
    report["selected_provider"] = payload.get("default_provider")
    return report


def trigger_tts_if_available(
    text: str, metadata: dict[str, Any] | None = None
) -> bool:
    return trigger_tts_with_result(text, metadata=metadata).ok
