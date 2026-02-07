"""Cron execution primitives for worker dispatch."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable


def _dispatch_webhook(
    *,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> int:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        return int(getattr(response, "status", 200))


def execute_cron_job(
    *,
    job_type: str,
    payload: dict[str, Any] | None,
    webhook_dispatcher: Callable[..., int] | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Execute one cron job payload and return a structured result."""

    normalized_type = (job_type or "noop").strip().lower()
    data = payload or {}

    if normalized_type == "noop":
        return {"ok": True, "job_type": "noop", "result": "noop_executed"}

    if normalized_type == "webhook":
        url = str(data.get("url") or "").strip()
        if not url:
            raise ValueError("webhook payload.url is required")
        body = data.get("body")
        if body is None:
            body = {}
        if not isinstance(body, dict):
            raise ValueError("webhook payload.body must be an object")
        headers = data.get("headers")
        if headers is None:
            headers = {}
        if not isinstance(headers, dict):
            raise ValueError("webhook payload.headers must be an object")

        dispatch = webhook_dispatcher or _dispatch_webhook
        status_code = dispatch(
            url=url,
            body=body,
            headers={str(k): str(v) for k, v in headers.items()},
            timeout_seconds=timeout_seconds,
        )
        return {
            "ok": True,
            "job_type": "webhook",
            "status_code": int(status_code),
        }

    raise ValueError(f"unsupported cron job_type={normalized_type}")


__all__ = ["execute_cron_job"]
