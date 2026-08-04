#!/usr/bin/env python3
"""Reduced local Guardian process for Browser Host negotiation and attachment proof."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class _Clock:
    expired: bool = False

    def __call__(self) -> datetime:
        now = datetime.now(timezone.utc)
        return now + timedelta(seconds=360 if self.expired else 0)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--summary-file", type=Path, required=True)
    parser.add_argument("--negotiation-enabled", action="store_true")
    parser.add_argument("--attachment-enabled", action="store_true")
    parser.add_argument(
        "--negotiation-outcome",
        choices=("compatible", "incompatible", "malformed"),
        default="compatible",
    )
    parser.add_argument("--expire-after-issuance", action="store_true")
    parser.add_argument("--shutdown-after-issuance", action="store_true")
    return parser.parse_args()


def create_app(args: argparse.Namespace, server_ref: dict[str, Any]):
    os.environ["CODEXIFY_DISABLE_DOTENV"] = "1"
    os.environ["GUARDIAN_DEV_MODE"] = "true"
    os.environ["GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED"] = (
        "true" if args.negotiation_enabled else "false"
    )
    os.environ["GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED"] = (
        "true" if args.attachment_enabled else "false"
    )
    os.environ["GUARDIAN_EXPOSURE_MODE"] = "local_safe"
    os.environ["GUARDIAN_AUTH_MODE"] = "local"
    os.environ.setdefault("CODEXIFY_SINGLE_USER_ID", "browser-host-negotiation-proof")

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from guardian.browser_host import http_adapter
    from guardian.browser_host.attachment_grants import AttachmentGrantStore
    from guardian.browser_host.negotiation import BrowserHostNegotiationPolicy
    from guardian.routes import browser_host

    app = FastAPI(title="Browser Host Guardian development support")
    counts: dict[str, int] = {"negotiation": 0, "grantIssuance": 0, "attachment": 0}
    statuses: dict[str, list[int]] = {
        "negotiation": [], "grantIssuance": [], "attachment": []
    }
    clock = _Clock()
    negotiation_mounted = http_adapter.install_browser_host_negotiation_adapter(
        app, browser_host.negotiation_router
    )
    attachment_mounted = http_adapter.install_browser_host_attachment_adapter(
        app, browser_host.router
    )
    if args.negotiation_enabled and not negotiation_mounted:
        raise RuntimeError("guardian_negotiation_adapter_not_mounted")
    if args.attachment_enabled and not attachment_mounted:
        raise RuntimeError("guardian_attachment_adapter_not_mounted")
    if attachment_mounted:
        app.state.browser_host_attachment_grant_store = AttachmentGrantStore(clock=clock)

    if args.negotiation_outcome == "incompatible" and negotiation_mounted:
        app.state.browser_host_negotiation_policy = BrowserHostNegotiationPolicy(
            supported_protocol_versions=("9.0.0",),
            supported_envelope_versions=("9.0.0",),
            supported_attachment_versions=("9.0.0",),
            allowed_feature_tokens=("capture:selected", "capture:visible", "capture:attach"),
        )

    @app.middleware("http")
    async def record_bounded_route_state(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method == "POST" and path.endswith("/negotiate"):
            counts["negotiation"] += 1
            statuses["negotiation"].append(response.status_code)
            if args.negotiation_outcome == "malformed":
                return JSONResponse(status_code=200, content={"malformed": True})
        elif request.method == "POST" and path.endswith("/attachment-grants"):
            counts["grantIssuance"] += 1
            statuses["grantIssuance"].append(response.status_code)
            if response.status_code == 201 and args.expire_after_issuance:
                clock.expired = True
            if response.status_code == 201 and args.shutdown_after_issuance:
                loop = asyncio.get_running_loop()
                loop.call_later(0.05, setattr, server_ref["server"], "should_exit", True)
        elif request.method == "POST" and path.endswith("/attachments"):
            counts["attachment"] += 1
            statuses["attachment"].append(response.status_code)
        return response

    @app.on_event("startup")
    async def announce_ready() -> None:
        print(f"READY {args.port}", flush=True)

    @app.on_event("shutdown")
    async def write_sanitized_summary() -> None:
        http_adapter.shutdown_browser_host_negotiation_adapter(app)
        http_adapter.shutdown_browser_host_attachment_adapter(app)
        args.summary_file.write_text(
            json.dumps(
                {
                    "negotiationEnabled": bool(args.negotiation_enabled),
                    "negotiationMounted": bool(negotiation_mounted),
                    "negotiationOutcome": args.negotiation_outcome,
                    "negotiationCount": counts["negotiation"],
                    "negotiationStatuses": statuses["negotiation"],
                    "grantIssuanceCount": counts["grantIssuance"],
                    "grantIssuanceStatuses": statuses["grantIssuance"],
                    "attachmentEnabled": bool(args.attachment_enabled),
                    "attachmentMounted": bool(attachment_mounted),
                    "attachmentCount": counts["attachment"],
                    "attachmentStatuses": statuses["attachment"],
                    "routes": sorted(
                        route.path
                        for route in app.routes
                        if route.path.startswith("/dev/browser-host/v1")
                    ),
                    "rawSecretsIncluded": False,
                    "rawProtocolBodiesIncluded": False,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    return app


def main() -> int:
    args = _parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("invalid_port")
    server_ref: dict[str, Any] = {}
    app = create_app(args, server_ref)
    import uvicorn

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
        access_log=False,
        lifespan="on",
    )
    server = uvicorn.Server(config)
    server_ref["server"] = server
    signal.signal(signal.SIGTERM, lambda *_: setattr(server, "should_exit", True))
    signal.signal(signal.SIGINT, lambda *_: setattr(server, "should_exit", True))
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
