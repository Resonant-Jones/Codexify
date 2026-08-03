#!/usr/bin/env python3
"""Launch the development Browser Host with one Guardian attachment grant.

The parent process owns the reusable local Guardian API key.  The child gets a
sanitized environment containing only the short-lived attachment capability
and bounded Browser Host configuration.  This helper is intentionally not a
production credential broker.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from guardian.browser_host.contract_loader import load_contract_metadata  # noqa: E402


API_KEY_ENV = "GUARDIAN_API_KEY"
ATTACHMENT_ENABLED_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED"
ATTACHMENT_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN"
ATTACHMENT_GRANT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT"
INSTANCE_ID_ENV = "CODEXIFY_BROWSER_HOST_INSTANCE_ID"
ATTACHMENT_TIMEOUT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_TIMEOUT_MS"
NEGOTIATION_ENABLED_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_DEV_ENABLED"
NEGOTIATION_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN"
NEGOTIATION_TIMEOUT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_TIMEOUT_MS"
NEGOTIATION_TRANSPORT_ENV = "CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT"
PROOF_MODE_ENV = "CODEXIFY_BROWSER_HOST_PROOF_MODE"
PROOF_TOKEN_ENV = "CODEXIFY_BROWSER_HOST_PROOF_TOKEN"

_INSTANCE_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
_SECRET_NAME_PATTERN = re.compile(
    r"(?:API_KEY|API_KEYS|SESSION|JWT|SECRET|PASSWORD|COOKIE|PRIVATE_KEY|"
    r"ACCESS_KEY|AUTHORIZATION|BEARER|SIGNING|TOKEN|CREDENTIAL)",
    re.IGNORECASE,
)
_SAFE_NON_SECRET_NAMES = {
    PROOF_TOKEN_ENV,
}


def _bounded_loopback_origin(value: str) -> str:
    parsed = urlsplit(value or "")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("origin_invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or port is None
        or not 1 <= port <= 65535
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("origin_invalid")
    return f"http://127.0.0.1:{port}"


def _bounded_instance_id(value: str) -> bool:
    return isinstance(value, str) and bool(_INSTANCE_PATTERN.fullmatch(value))


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if "--" not in argv:
        raise ValueError("child_command_required")
    separator = argv.index("--")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guardian-origin", required=True)
    parser.add_argument("--attachment-origin")
    parser.add_argument("--browser-host-instance-id")
    parser.add_argument("--grant-ttl-seconds", type=int, default=120)
    parser.add_argument("--max-attachment-bytes", type=int, default=65536)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument(
        "--negotiation-transport",
        choices=("guardian_dev_adapter", "deterministic_stub"),
        default="guardian_dev_adapter",
    )
    args = parser.parse_args(argv[:separator])
    command = argv[separator + 1 :]
    if not command:
        raise ValueError("child_command_required")
    return args, command


def _validate_contract(kind: str, value: Any) -> bool:
    metadata = load_contract_metadata()
    schema = metadata.schemas[kind]
    return Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(value)


def _grant_request(args: argparse.Namespace, instance_id: str) -> dict[str, Any]:
    metadata = load_contract_metadata()
    request = {
        "schemaVersion": "1.0.0",
        "protocolVersion": metadata.protocol_version,
        "attachmentVersion": metadata.attachment_version,
        "requestId": instance_id,
        "browserHostInstanceId": instance_id,
        "requestedRetention": metadata.retention_class,
        "requestedAttachmentCount": metadata.allowed_uses,
        "requestedMaxContentBytes": args.max_attachment_bytes,
        "requestedTtlSeconds": args.grant_ttl_seconds,
        "userConfirmationMode": "explicit_each_attachment",
        "generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if not _validate_contract("attachmentGrantRequest", request):
        raise ValueError("grant_request_invalid")
    return request


def _request_grant(origin: str, api_key: str, request: dict[str, Any]) -> dict[str, Any]:
    parsed = urlsplit(origin)
    body = json.dumps(request, separators=(",", ":")).encode("utf-8")
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    try:
        connection.request(
            "POST",
            "/dev/browser-host/v1/attachment-grants",
            body=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-API-Key": api_key,
            },
        )
        response = connection.getresponse()
        response_body = response.read(131073)
    finally:
        connection.close()
    if response.status != 201 or len(response_body) > 131072:
        raise ValueError("grant_issuance_failed")
    try:
        value = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("grant_response_invalid") from exc
    if not _validate_contract("attachmentGrant", value):
        raise ValueError("grant_response_invalid")
    if (
        value.get("authorizationScheme") != "browser_host_attachment_grant"
        or value.get("retentionClass") != "ephemeral"
        or value.get("remainingUses") != 1
        or value.get("browserHostInstanceId") != request["browserHostInstanceId"]
        or not isinstance(value.get("grantBearer"), str)
    ):
        raise ValueError("grant_response_invalid")
    return value


def _assert_route_available(origin: str, path: str, *, expected: tuple[int, ...]) -> None:
    """Probe a development route without logging or retaining its response body."""

    parsed = urlsplit(origin)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
    try:
        # GET is deliberately unsupported by the POST-only adapter.  A 405
        # proves the route is mounted without creating a negotiation attempt,
        # issuing a grant, or sending a protocol body.
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        response.read(4097)
    finally:
        connection.close()
    if response.status not in expected:
        raise ValueError("guardian_browser_host_route_unavailable")


def _is_secret_environment_name(name: str) -> bool:
    return name not in _SAFE_NON_SECRET_NAMES and bool(_SECRET_NAME_PATTERN.search(name))


def _child_environment(
    base: dict[str, str],
    grant: str,
    negotiation_origin: str,
    attachment_origin: str,
    instance_id: str,
    timeout_ms: int,
    negotiation_transport: str,
) -> dict[str, str]:
    child = {
        name: value
        for name, value in base.items()
        if not _is_secret_environment_name(name)
    }
    child.update(
        {
            PROOF_MODE_ENV: "1",
            ATTACHMENT_ENABLED_ENV: "1",
            ATTACHMENT_ORIGIN_ENV: attachment_origin,
            ATTACHMENT_GRANT_ENV: grant,
            INSTANCE_ID_ENV: instance_id,
            ATTACHMENT_TIMEOUT_ENV: str(timeout_ms),
            NEGOTIATION_TRANSPORT_ENV: negotiation_transport,
        }
    )
    if negotiation_transport == "guardian_dev_adapter":
        child.update(
            {
                NEGOTIATION_ENABLED_ENV: "1",
                NEGOTIATION_ORIGIN_ENV: negotiation_origin,
                NEGOTIATION_TIMEOUT_ENV: str(timeout_ms),
            }
        )
    return child


def _validate_operator_args(args: argparse.Namespace) -> tuple[str, str, str]:
    guardian_origin = _bounded_loopback_origin(args.guardian_origin)
    attachment_origin = _bounded_loopback_origin(args.attachment_origin or guardian_origin)
    if args.negotiation_transport == "guardian_dev_adapter" and attachment_origin != guardian_origin:
        raise ValueError("guardian_origins_must_match")
    instance_id = args.browser_host_instance_id or f"browser-host-{uuid.uuid4().hex}"
    if not _bounded_instance_id(instance_id):
        raise ValueError("browser_host_instance_id_invalid")
    metadata = load_contract_metadata()
    if not metadata.minimum_ttl_seconds <= args.grant_ttl_seconds <= metadata.maximum_ttl_seconds:
        raise ValueError("grant_ttl_invalid")
    if not 1 <= args.max_attachment_bytes <= metadata.max_capture_bytes:
        raise ValueError("grant_budget_invalid")
    if not 1000 <= args.timeout_ms <= 30000:
        raise ValueError("attachment_timeout_invalid")
    return guardian_origin, attachment_origin, instance_id


def main(argv: list[str] | None = None) -> int:
    try:
        args, command = _parse_args(argv if argv is not None else sys.argv[1:])
        guardian_origin, attachment_origin, instance_id = _validate_operator_args(args)
        api_key = (os.environ.get(API_KEY_ENV) or "").strip()
        if not api_key:
            raise ValueError("guardian_api_key_missing")
        request = _grant_request(args, instance_id)
        response = _request_grant(guardian_origin, api_key, request)
        grant = response["grantBearer"]
        if args.negotiation_transport == "guardian_dev_adapter":
            _assert_route_available(guardian_origin, "/dev/browser-host/v1/negotiate", expected=(405,))
        _assert_route_available(attachment_origin, "/dev/browser-host/v1/attachments", expected=(405,))
        child_env = _child_environment(
            dict(os.environ), grant, guardian_origin, attachment_origin, instance_id,
            args.timeout_ms, args.negotiation_transport
        )
        print("attachment grant issuance succeeded", flush=True)
        print(f"browser host instance id: {instance_id}", flush=True)
        print("child command started", flush=True)
        completed = subprocess.run(command, cwd=str(ROOT), env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        print(f"child exit code: {completed.returncode}", flush=True)
        return completed.returncode
    except (OSError, ValueError, json.JSONDecodeError):
        print("attachment grant issuance or launch failed", file=sys.stderr, flush=True)
        return 2
    finally:
        if "child_env" in locals():
            child_env.pop(ATTACHMENT_GRANT_ENV, None)
        if "grant" in locals():
            grant = None
        if "response" in locals():
            response = None


if __name__ == "__main__":
    raise SystemExit(main())
