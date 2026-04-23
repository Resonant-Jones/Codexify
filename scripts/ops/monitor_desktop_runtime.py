from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

STATUS_READY = "ready"
STATUS_DEGRADED = "degraded"
STATUS_UNREACHABLE = "unreachable"
STATUS_MISSING_ARTIFACT = "missing_artifact"
STATUS_NOT_READY = "not_ready"

STATUS_ORDER = {
    STATUS_READY: 0,
    STATUS_DEGRADED: 1,
    STATUS_NOT_READY: 2,
    STATUS_MISSING_ARTIFACT: 3,
    STATUS_UNREACHABLE: 4,
}

HTTP_READY_TOKENS = {
    "ok",
    "healthy",
    "online",
    "ready",
    "running",
    "available",
}
HTTP_DEGRADED_TOKENS = {
    "degraded",
    "warning",
    "warn",
    "stale",
    "warming",
}
HTTP_NOT_READY_TOKENS = {
    "down",
    "offline",
    "unhealthy",
    "error",
    "fail",
    "failed",
    "misconfigured",
    "dependency_unavailable",
    "unknown",
    "not_ready",
}
HTTP_RETRIEVAL_READY_TOKENS = {
    "ready",
}
HTTP_RETRIEVAL_DEGRADED_TOKENS = {
    "degraded",
}
HTTP_RETRIEVAL_NOT_READY_TOKENS = {
    "unproven",
    "unready",
    "missing",
    "not_ready",
    "offline",
    "down",
    "error",
}


@dataclass
class FetchResult:
    reachable: bool
    http_status: int | None
    payload: Any | None
    error: str | None


def default_base_url() -> str:
    return "http://127.0.0.1:8888"


def default_app_support_root() -> Path:
    return Path.home() / "Library" / "Application Support" / "Codexify"


def default_runtime_root() -> Path:
    return Path.home() / "Codexify"


def normalize_token(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token


def path_status(present: bool) -> str:
    return STATUS_READY if present else STATUS_MISSING_ARTIFACT


def worst_status(*statuses: str) -> str:
    return max(statuses, key=lambda status: STATUS_ORDER.get(status, 0))


def _is_ready_token(token: str) -> bool:
    return token in HTTP_READY_TOKENS


def _is_degraded_token(token: str) -> bool:
    return token in HTTP_DEGRADED_TOKENS


def _is_not_ready_token(token: str) -> bool:
    return token in HTTP_NOT_READY_TOKENS


def _request_json(
    url: str,
    *,
    timeout: float,
    request_get: Callable[..., Any] = requests.get,
) -> FetchResult:
    try:
        response = request_get(url, timeout=timeout)
    except requests.RequestException as exc:
        return FetchResult(
            reachable=False,
            http_status=None,
            payload=None,
            error=f"{type(exc).__name__}: {exc}",
        )

    http_status = getattr(response, "status_code", None)
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        return FetchResult(
            reachable=True,
            http_status=http_status if isinstance(http_status, int) else None,
            payload=None,
            error=f"invalid_json: {type(exc).__name__}: {exc}",
        )

    return FetchResult(
        reachable=True,
        http_status=http_status if isinstance(http_status, int) else None,
        payload=payload,
        error=None,
    )


def _json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            token = value.strip()
            if token:
                return token
    return None


def _surface_detail(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    return _first_string(
        payload.get("status"),
        payload.get("reason"),
        payload.get("error"),
        payload.get("message"),
    )


def _classify_standard_health(payload: dict[str, Any] | None) -> str:
    token = normalize_token(_surface_detail(payload))
    if not token:
        return STATUS_NOT_READY
    if _is_ready_token(token):
        return STATUS_READY
    if _is_degraded_token(token):
        return STATUS_DEGRADED
    if _is_not_ready_token(token):
        return STATUS_NOT_READY
    return STATUS_NOT_READY


def _classify_retrieval_health(payload: dict[str, Any] | None) -> str:
    token = normalize_token(_surface_detail(payload))
    if not token:
        return STATUS_NOT_READY
    if token in HTTP_RETRIEVAL_READY_TOKENS:
        if payload and payload.get("ok") is True:
            same_runtime = payload.get("same_runtime_as_worker")
            if same_runtime is False:
                return STATUS_DEGRADED
            return STATUS_READY
        return STATUS_NOT_READY
    if token in HTTP_RETRIEVAL_DEGRADED_TOKENS:
        return STATUS_DEGRADED
    if token in HTTP_RETRIEVAL_NOT_READY_TOKENS:
        return STATUS_NOT_READY
    return STATUS_NOT_READY


def _classify_catalog(
    payload: dict[str, Any] | None
) -> tuple[str, dict[str, Any]]:
    if not payload:
        return STATUS_NOT_READY, {"provider_count": 0}

    providers = payload.get("providers")
    if not isinstance(providers, list):
        return STATUS_NOT_READY, {"provider_count": 0}

    local_provider: dict[str, Any] | None = None
    for item in providers:
        if not isinstance(item, dict):
            continue
        if normalize_token(item.get("id")) == "local":
            local_provider = item
            break

    summary: dict[str, Any] = {
        "provider_count": len(providers),
        "local_provider": None,
    }
    if local_provider is None:
        return STATUS_NOT_READY, summary

    truth = _json_object(local_provider.get("truth")) or {}
    summary["local_provider"] = {
        "id": local_provider.get("id"),
        "enabled": local_provider.get("enabled"),
        "available": local_provider.get("available"),
        "truth": {
            "configured": truth.get("configured"),
            "authorized": truth.get("authorized"),
            "discoverable": truth.get("discoverable"),
            "selectable": truth.get("selectable"),
        },
    }

    enabled = bool(local_provider.get("enabled"))
    available = bool(local_provider.get("available"))
    truth_selectable = bool(truth.get("selectable"))
    truth_discoverable = bool(truth.get("discoverable"))
    if enabled and available and truth_selectable and truth_discoverable:
        return STATUS_READY, summary
    if available or enabled or truth_selectable or truth_discoverable:
        return STATUS_DEGRADED, summary
    return STATUS_NOT_READY, summary


def _endpoint_report(
    *,
    name: str,
    url: str,
    fetch_result: FetchResult,
    status: str,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "name": name,
        "url": url,
        "status": status,
        "reachable": fetch_result.reachable,
        "http_status": fetch_result.http_status,
        "detail": detail or fetch_result.error,
    }
    if extra:
        report.update(extra)
    return report


def _probe_file_artifact(path: Path) -> tuple[dict[str, Any], Any | None]:
    if not path.is_file():
        return (
            {
                "path": str(path),
                "present": False,
                "status": STATUS_MISSING_ARTIFACT,
                "detail": "missing_artifact",
            },
            None,
        )

    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except Exception as exc:
        return (
            {
                "path": str(path),
                "present": True,
                "status": STATUS_NOT_READY,
                "detail": f"invalid_json: {type(exc).__name__}: {exc}",
            },
            None,
        )

    return (
        {
            "path": str(path),
            "present": True,
            "status": STATUS_READY,
            "detail": None,
        },
        payload,
    )


def _probe_startup_state(path: Path) -> dict[str, Any]:
    report, payload = _probe_file_artifact(path)
    if not report["present"]:
        return report
    if report["status"] != STATUS_READY:
        return report

    payload = _json_object(payload)
    if payload is None:
        return {
            **report,
            "status": STATUS_NOT_READY,
            "detail": "startup_state_not_an_object",
        }

    setup_complete = bool(payload.get("setupComplete"))
    runtime_profile = _first_string(payload.get("runtimeProfile"))
    env_path = _first_string(payload.get("envPath"))
    handoff_target = _first_string(payload.get("handoffTarget"))
    detail = _first_string(payload.get("detail"))

    if not setup_complete or not handoff_target:
        return {
            "path": str(path),
            "present": True,
            "status": STATUS_NOT_READY,
            "detail": detail or "startup_state_present_but_not_ready",
            "setup_complete": setup_complete,
            "runtime_profile": runtime_profile,
            "env_path": env_path,
            "handoff_target": handoff_target,
        }

    return {
        "path": str(path),
        "present": True,
        "status": STATUS_READY,
        "detail": detail or "startup_state_ready",
        "setup_complete": setup_complete,
        "runtime_profile": runtime_profile,
        "env_path": env_path,
        "handoff_target": handoff_target,
    }


def _probe_packaged_runtime(runtime_root: Path) -> dict[str, Any]:
    manifest_path = runtime_root / ".codexify-runtime-manifest.json"
    marker_path = runtime_root / ".codexify-packaged-runtime"

    manifest_report, manifest_payload = _probe_file_artifact(manifest_path)
    marker_report = {
        "path": str(marker_path),
        "present": marker_path.is_file(),
        "status": path_status(marker_path.is_file()),
        "detail": None if marker_path.is_file() else "missing_artifact",
    }

    if not manifest_report["present"] or not marker_report["present"]:
        return {
            "status": worst_status(
                manifest_report["status"], marker_report["status"]
            ),
            "present": False,
            "manifest": manifest_report,
            "marker": marker_report,
            "detail": "packaged_runtime_missing_artifact",
        }

    if manifest_report["status"] != STATUS_READY:
        return {
            "status": STATUS_NOT_READY,
            "present": True,
            "manifest": manifest_report,
            "marker": marker_report,
            "detail": manifest_report["detail"],
        }

    payload = _json_object(manifest_payload)
    if payload is None:
        return {
            "status": STATUS_NOT_READY,
            "present": True,
            "manifest": manifest_report,
            "marker": marker_report,
            "detail": "manifest_not_an_object",
        }

    schema_version = payload.get("schema_version")
    packaged = bool(payload.get("packaged"))
    attachment_state = _first_string(payload.get("attachment_state"))

    if (
        schema_version != 1
        or not packaged
        or attachment_state
        not in {
            "first-run",
            "refresh",
        }
    ):
        return {
            "status": STATUS_NOT_READY,
            "present": True,
            "manifest": {
                **manifest_report,
                "schema_version": schema_version,
                "packaged": packaged,
                "attachment_state": attachment_state,
            },
            "marker": marker_report,
            "detail": "packaged_runtime_not_ready",
        }

    return {
        "status": STATUS_READY,
        "present": True,
        "manifest": {
            **manifest_report,
            "schema_version": schema_version,
            "packaged": packaged,
            "attachment_state": attachment_state,
            "runtime_home": _first_string(payload.get("runtime_home")),
            "compose_file": _first_string(payload.get("compose_file")),
            "env_file": _first_string(payload.get("env_file")),
            "env_template": _first_string(payload.get("env_template")),
            "env_example": _first_string(payload.get("env_example")),
            "resource_root": _first_string(payload.get("resource_root")),
        },
        "marker": marker_report,
        "detail": "packaged_runtime_ready",
    }


def _probe_runtime(
    *,
    base_url: str,
    timeout: float,
    request_get: Callable[..., Any],
) -> dict[str, Any]:
    core_url = f"{base_url.rstrip('/')}/health"
    chat_url = f"{base_url.rstrip('/')}/health/chat"
    retrieval_url = f"{base_url.rstrip('/')}/api/health/retrieval"

    core_fetch = _request_json(
        core_url, timeout=timeout, request_get=request_get
    )
    core_payload = _json_object(core_fetch.payload)
    core_status = (
        STATUS_UNREACHABLE
        if not core_fetch.reachable
        else _classify_standard_health(core_payload)
    )

    chat_fetch = _request_json(
        chat_url, timeout=timeout, request_get=request_get
    )
    chat_payload = _json_object(chat_fetch.payload)
    chat_status = (
        STATUS_UNREACHABLE
        if not chat_fetch.reachable
        else _classify_standard_health(chat_payload)
    )

    retrieval_fetch = _request_json(
        retrieval_url, timeout=timeout, request_get=request_get
    )
    retrieval_payload = _json_object(retrieval_fetch.payload)
    retrieval_status = (
        STATUS_UNREACHABLE
        if not retrieval_fetch.reachable
        else _classify_retrieval_health(retrieval_payload)
    )
    runtime_status = worst_status(core_status, chat_status, retrieval_status)
    reachability = "reachable" if core_fetch.reachable else "unreachable"

    return {
        "status": runtime_status,
        "reachability": reachability,
        "surfaces": {
            "core": _endpoint_report(
                name="core",
                url=core_url,
                fetch_result=core_fetch,
                status=core_status,
                detail=_surface_detail(core_payload),
                extra={
                    "supported_profile": _json_object(
                        core_payload.get("details")
                    ).get("supported_profile")
                    if core_payload
                    and _json_object(core_payload.get("details"))
                    else None
                },
            ),
            "chat": _endpoint_report(
                name="chat",
                url=chat_url,
                fetch_result=chat_fetch,
                status=chat_status,
                detail=_surface_detail(chat_payload),
                extra={
                    "redis": chat_payload.get("redis")
                    if chat_payload
                    else None,
                    "worker_status": _json_object(
                        chat_payload.get("worker") if chat_payload else None
                    ).get("status")
                    if chat_payload and _json_object(chat_payload.get("worker"))
                    else None,
                },
            ),
            "retrieval": _endpoint_report(
                name="retrieval",
                url=retrieval_url,
                fetch_result=retrieval_fetch,
                status=retrieval_status,
                detail=_surface_detail(retrieval_payload),
                extra={
                    "ok": retrieval_payload.get("ok")
                    if retrieval_payload
                    else None,
                    "proof_capable": retrieval_payload.get("proof_capable")
                    if retrieval_payload
                    else None,
                    "same_runtime_as_worker": retrieval_payload.get(
                        "same_runtime_as_worker"
                    )
                    if retrieval_payload
                    else None,
                },
            ),
        },
    }


def _probe_provider(
    *,
    base_url: str,
    timeout: float,
    request_get: Callable[..., Any],
) -> dict[str, Any]:
    llm_url = f"{base_url.rstrip('/')}/api/health/llm"
    catalog_url = f"{base_url.rstrip('/')}/api/llm/catalog?include=all"

    llm_fetch = _request_json(llm_url, timeout=timeout, request_get=request_get)
    llm_payload = _json_object(llm_fetch.payload)
    llm_status = (
        STATUS_UNREACHABLE
        if not llm_fetch.reachable
        else _classify_standard_health(llm_payload)
    )

    catalog_fetch = _request_json(
        catalog_url, timeout=timeout, request_get=request_get
    )
    catalog_payload = _json_object(catalog_fetch.payload)
    catalog_status, catalog_summary = (
        (STATUS_UNREACHABLE, {"provider_count": 0})
        if not catalog_fetch.reachable
        else _classify_catalog(catalog_payload)
    )

    provider_status = worst_status(llm_status, catalog_status)
    reachability = "reachable" if llm_fetch.reachable else "unreachable"

    return {
        "status": provider_status,
        "reachability": reachability,
        "surfaces": {
            "llm": _endpoint_report(
                name="llm",
                url=llm_url,
                fetch_result=llm_fetch,
                status=llm_status,
                detail=_surface_detail(llm_payload),
                extra={
                    "provider": llm_payload.get("provider")
                    if llm_payload
                    else None,
                    "model": llm_payload.get("model") if llm_payload else None,
                    "provider_runtime": llm_payload.get("provider_runtime")
                    if llm_payload
                    else None,
                },
            ),
            "catalog": _endpoint_report(
                name="catalog",
                url=catalog_url,
                fetch_result=catalog_fetch,
                status=catalog_status,
                detail="catalog_ready"
                if catalog_status == STATUS_READY
                else None,
                extra=catalog_summary,
            ),
        },
    }


def _summarize_launcher(
    *,
    app_support_root: Path,
    runtime_root: Path,
) -> dict[str, Any]:
    startup_state_path = (
        app_support_root / ".codexify-launcher-startup-state.json"
    )
    startup_state = _probe_startup_state(startup_state_path)
    packaged_runtime = _probe_packaged_runtime(runtime_root)

    launcher_status = worst_status(
        startup_state["status"], packaged_runtime["status"]
    )
    return {
        "status": launcher_status,
        "app_support_root": str(app_support_root),
        "runtime_root": str(runtime_root),
        "startup_state": startup_state,
        "packaged_runtime": packaged_runtime,
    }


def _build_next_actions(snapshot: dict[str, Any]) -> list[str]:
    next_actions: list[str] = []
    runtime = snapshot["runtime"]
    provider = snapshot["provider"]
    launcher = snapshot["launcher"]

    if runtime["status"] == STATUS_UNREACHABLE:
        next_actions.append(
            "Confirm the supported Docker Compose backend is up and the monitor base URL points at it."
        )
    elif runtime["status"] == STATUS_NOT_READY:
        next_actions.append(
            "Inspect the backend health surfaces and fix the non-ready runtime surface before trusting the proof."
        )
    elif runtime["status"] == STATUS_DEGRADED:
        next_actions.append(
            "Treat the runtime as partially healthy and inspect the degraded surface before release proof."
        )

    if provider["status"] == STATUS_UNREACHABLE:
        next_actions.append(
            "Inspect the local provider lane and verify the model runtime is reachable from the backend."
        )
    elif provider["status"] == STATUS_NOT_READY:
        next_actions.append(
            "Check /health/llm and the provider catalog for configuration or model-selection drift."
        )
    elif provider["status"] == STATUS_DEGRADED:
        next_actions.append(
            "Treat provider readiness as degraded and inspect model warmup or catalog truth before calling it ready."
        )

    if launcher["startup_state"]["status"] == STATUS_MISSING_ARTIFACT:
        next_actions.append(
            "Rerun the installed-app launch ritual and confirm the startup-state file is written into Application Support."
        )
    elif launcher["startup_state"]["status"] == STATUS_NOT_READY:
        next_actions.append(
            "Inspect the startup-state file; it exists, but the launcher has not recorded a ready handoff."
        )

    if launcher["packaged_runtime"]["status"] == STATUS_MISSING_ARTIFACT:
        next_actions.append(
            "Confirm the packaged runtime manifest and marker appear in the runtime root after launcher materialization."
        )
    elif launcher["packaged_runtime"]["status"] == STATUS_NOT_READY:
        next_actions.append(
            "Inspect the packaged runtime manifest; the runtime root is present, but materialization is not yet cleanly ready."
        )

    deduped: list[str] = []
    for action in next_actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def collect_monitor_snapshot(
    *,
    base_url: str | None = None,
    app_support_root: Path | None = None,
    runtime_root: Path | None = None,
    timeout: float = 2.0,
    request_get: Callable[..., Any] = requests.get,
) -> dict[str, Any]:
    base = base_url or default_base_url()
    app_support = app_support_root or default_app_support_root()
    runtime = runtime_root or default_runtime_root()

    runtime_summary = _probe_runtime(
        base_url=base, timeout=timeout, request_get=request_get
    )
    provider_summary = _probe_provider(
        base_url=base, timeout=timeout, request_get=request_get
    )
    launcher_summary = _summarize_launcher(
        app_support_root=app_support, runtime_root=runtime
    )

    overall_status = worst_status(
        runtime_summary["status"],
        provider_summary["status"],
        launcher_summary["status"],
    )
    snapshot = {
        "timestamp": time.time(),
        "base_url": base,
        "overall_status": overall_status,
        "runtime": runtime_summary,
        "provider": provider_summary,
        "launcher": launcher_summary,
    }
    snapshot["next_actions"] = _build_next_actions(snapshot)
    return snapshot


def render_snapshot(snapshot: dict[str, Any], *, json_output: bool) -> str:
    if json_output:
        return json.dumps(snapshot, indent=2, sort_keys=True)

    runtime = snapshot["runtime"]
    provider = snapshot["provider"]
    launcher = snapshot["launcher"]
    lines = [
        f"overall_status: {snapshot['overall_status']}",
        f"base_url: {snapshot['base_url']}",
        f"runtime_status: {runtime['status']} ({runtime['reachability']})",
        f"provider_status: {provider['status']} ({provider['reachability']})",
        f"launcher_status: {launcher['status']}",
        f"  startup_state: {launcher['startup_state']['status']}",
        f"  packaged_runtime: {launcher['packaged_runtime']['status']}",
        "runtime_surfaces:",
    ]

    for name, report in runtime["surfaces"].items():
        lines.append(
            f"  - {name}: {report['status']} (reachable={report['reachable']}, http={report['http_status']})"
        )

    lines.append("provider_surfaces:")
    for name, report in provider["surfaces"].items():
        lines.append(
            f"  - {name}: {report['status']} (reachable={report['reachable']}, http={report['http_status']})"
        )

    if snapshot["next_actions"]:
        lines.append("next_actions:")
        for action in snapshot["next_actions"]:
            lines.append(f"  - {action}")
    else:
        lines.append("next_actions: none")

    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only operator monitor for the supported local runtime and "
            "desktop launcher proof surfaces."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once", action="store_true", help="Run one snapshot and exit."
    )
    mode.add_argument(
        "--watch",
        action="store_true",
        help="Continuously poll the surfaces until interrupted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the text summary.",
    )
    parser.add_argument(
        "--base-url",
        default=default_base_url(),
        help="Backend base URL for the supported runtime surfaces.",
    )
    parser.add_argument(
        "--app-support-root",
        default=str(default_app_support_root()),
        help="Application Support root that holds launcher state.",
    )
    parser.add_argument(
        "--runtime-root",
        default=str(default_runtime_root()),
        help="Packaged runtime root that holds the manifest and marker.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds for --watch mode.",
    )
    return parser


def _run_once(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    snapshot = collect_monitor_snapshot(
        base_url=args.base_url,
        app_support_root=Path(args.app_support_root),
        runtime_root=Path(args.runtime_root),
        timeout=args.timeout,
    )
    print(render_snapshot(snapshot, json_output=args.json))
    return snapshot, 0 if snapshot["overall_status"] == STATUS_READY else 1


def _run_watch(args: argparse.Namespace) -> int:
    try:
        while True:
            snapshot = collect_monitor_snapshot(
                base_url=args.base_url,
                app_support_root=Path(args.app_support_root),
                runtime_root=Path(args.runtime_root),
                timeout=args.timeout,
            )
            print(render_snapshot(snapshot, json_output=args.json))
            sys.stdout.flush()
            time.sleep(max(0.1, args.interval))
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    watch = bool(args.watch)
    once = bool(args.once or not args.watch)
    if watch:
        return _run_watch(args)
    if once:
        _snapshot, exit_code = _run_once(args)
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
