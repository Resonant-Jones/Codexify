"""Focused proof for the backend startup-failure diagnostic receipt."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import io
import json
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from guardian.diagnostics.startup_failure_receipt import (
    EVENT,
    FALLBACK_LINE,
    MAX_CHAIN_ENTRIES,
    MAX_FRAMES,
    MAX_MESSAGE_BYTES,
    MAX_RECEIPT_BYTES,
    RECEIPT_PREFIX,
    SCHEMA_VERSION,
    STARTUP_PHASE_APPLICATION_LIFESPAN,
    build_startup_failure_receipt,
    redact_exception_message,
    serialize_startup_failure_receipt,
    startup_failure_receipt_boundary,
)


class SyntheticStartupError(RuntimeError):
    """A deterministic startup failure used only by this test module."""


def _exception_with_message(message: str) -> BaseException:
    try:
        raise SyntheticStartupError(message)
    except SyntheticStartupError as exception:
        return exception


@pytest.mark.parametrize(
    ("message", "secret", "safe_fragment"),
    [
        (
            "Authorization: Bearer bearer-secret-value-123",
            "bearer-secret-value-123",
            "Authorization: Bearer <redacted>",
        ),
        (
            "upstream returned eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.c2lnbmF0dXJl",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.c2lnbmF0dXJl",
            "upstream returned <redacted>",
        ),
        (
            "provider rejected sk-test-secret-1234567890",
            "sk-test-secret-1234567890",
            "provider rejected <redacted>",
        ),
        (
            "api_key=api-key-secret-value",
            "api-key-secret-value",
            "api_key=<redacted>",
        ),
        (
            "password=database-password-value",
            "database-password-value",
            "password=<redacted>",
        ),
        (
            "postgresql://startup_user:database-password@db.example.test:5432/codexify",
            "startup_user:database-password",
            "postgresql://<redacted>@db.example.test:5432/codexify",
        ),
        (
            "https://operator:browser-password@service.example.test/v1/health",
            "operator:browser-password",
            "https://<redacted>@service.example.test/v1/health",
        ),
        (
            "DEEPSEEK_API_KEY=deepseek-test-secret-value",
            "deepseek-test-secret-value",
            "DEEPSEEK_API_KEY=<redacted>",
        ),
        (
            "OPENAI_API_KEY=openai-test-secret-value",
            "openai-test-secret-value",
            "OPENAI_API_KEY=<redacted>",
        ),
    ],
)
def test_receipt_redacts_secret_bearing_messages(
    message: str, secret: str, safe_fragment: str
) -> None:
    redacted, truncated = redact_exception_message(message)
    receipt = build_startup_failure_receipt(_exception_with_message(message))
    serialized = serialize_startup_failure_receipt(receipt)

    assert secret not in redacted
    assert secret not in serialized
    assert safe_fragment in redacted
    assert receipt["message_sha256"] == hashlib.sha256(
        message.encode("utf-8")
    ).hexdigest()
    assert truncated is False


def test_receipt_shape_chain_frames_and_bounds() -> None:
    try:
        try:
            raise ValueError("token=inner-secret-value")
        except ValueError as inner:
            raise SyntheticStartupError("Bearer outer-secret-value") from inner
    except SyntheticStartupError as exception:
        receipt = build_startup_failure_receipt(exception)

    assert receipt["schema_version"] == SCHEMA_VERSION
    assert receipt["event"] == EVENT
    assert receipt["startup_phase"] == STARTUP_PHASE_APPLICATION_LIFESPAN
    assert receipt["exception_type"].endswith(".SyntheticStartupError")
    assert receipt["exception_module"] == __name__
    assert receipt["message_redacted"] == "Bearer <redacted>"
    assert receipt["message_sha256"] == hashlib.sha256(
        b"Bearer outer-secret-value"
    ).hexdigest()
    datetime.fromisoformat(receipt["timestamp_utc"].replace("Z", "+00:00"))

    assert len(receipt["exception_chain"]) == 1
    chain = receipt["exception_chain"][0]
    assert chain["exception_type"] == "builtins.ValueError"
    assert chain["message_redacted"] == "token=<redacted>"
    assert "inner-secret-value" not in json.dumps(receipt)

    assert receipt["frames"]
    assert len(receipt["frames"]) <= MAX_FRAMES
    for frame in receipt["frames"]:
        assert set(frame) == {"path", "function", "line"}
        assert isinstance(frame["line"], int)
        assert "line_text" not in frame
        assert "locals" not in frame

    huge_message = "x" * (MAX_MESSAGE_BYTES * 4)
    huge_receipt = build_startup_failure_receipt(
        _exception_with_message(huge_message)
    )
    huge_serialized = serialize_startup_failure_receipt(huge_receipt)
    assert len(huge_receipt["message_redacted"].encode("utf-8")) <= MAX_MESSAGE_BYTES
    assert huge_receipt["truncated"] is True
    assert len(huge_serialized.encode("utf-8")) <= MAX_RECEIPT_BYTES
    assert len(huge_receipt["exception_chain"]) <= MAX_CHAIN_ENTRIES


@asynccontextmanager
async def _failing_lifespan():
    try:
        raise SyntheticStartupError("password=lifespan-secret-value")
    except SyntheticStartupError as exception:
        raise exception
    yield


@asynccontextmanager
async def _successful_lifespan(events: list[str]):
    events.append("startup")
    yield
    events.append("shutdown")


def test_boundary_emits_once_and_reraises_original_exception() -> None:
    stream = io.StringIO()

    async def exercise() -> None:
        with pytest.raises(SyntheticStartupError, match="lifespan-secret-value"):
            async with startup_failure_receipt_boundary(
                _failing_lifespan(), stream=stream
            ):
                pytest.fail("failed startup must not enter the application body")

    asyncio.run(exercise())

    lines = stream.getvalue().splitlines()
    receipts = [line for line in lines if line.startswith(RECEIPT_PREFIX)]
    assert len(receipts) == 1
    assert "lifespan-secret-value" not in receipts[0]
    payload = json.loads(receipts[0][len(RECEIPT_PREFIX) :])
    assert payload["event"] == EVENT
    assert payload["exception_type"].endswith(".SyntheticStartupError")


def test_boundary_success_emits_no_failure_receipt() -> None:
    stream = io.StringIO()
    events: list[str] = []

    async def exercise() -> None:
        async with startup_failure_receipt_boundary(
            _successful_lifespan(events), stream=stream
        ):
            events.append("running")

    asyncio.run(exercise())

    assert events == ["startup", "running", "shutdown"]
    assert stream.getvalue() == ""


def test_boundary_emitter_failure_preserves_original_exception() -> None:
    stream = io.StringIO()

    def failing_emitter(*_args, **_kwargs):
        raise RuntimeError("diagnostic emitter failed")

    async def exercise() -> None:
        with pytest.raises(SyntheticStartupError, match="lifespan-secret-value"):
            async with startup_failure_receipt_boundary(
                _failing_lifespan(), stream=stream, emitter=failing_emitter
            ):
                pytest.fail("failed startup must not enter the application body")

    asyncio.run(exercise())

    assert stream.getvalue().splitlines() == [FALLBACK_LINE]


def _load_guardian_api_for_boundary_test(monkeypatch) -> object:
    """Import the application with its eager database dependency replaced."""
    fake_db = MagicMock()
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")

    import guardian.core.dependencies as dependencies

    monkeypatch.setattr(dependencies, "init_database", lambda: fake_db)

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    return guardian_api


def test_guardian_app_lifespan_uses_the_receipt_boundary(
    monkeypatch, capsys
) -> None:
    guardian_api = _load_guardian_api_for_boundary_test(monkeypatch)

    @asynccontextmanager
    async def failing_body(_app):
        raise SyntheticStartupError("token=guardian-boundary-secret")
        yield

    monkeypatch.setattr(guardian_api, "_app_lifespan_body", failing_body)

    async def exercise() -> None:
        with pytest.raises(
            SyntheticStartupError, match="guardian-boundary-secret"
        ):
            async with guardian_api.app_lifespan(FastAPI()):
                pytest.fail("failed startup must not enter the application body")

    asyncio.run(exercise())

    stderr = capsys.readouterr().err
    receipts = [
        line for line in stderr.splitlines() if line.startswith(RECEIPT_PREFIX)
    ]
    assert len(receipts) == 1
    assert "guardian-boundary-secret" not in receipts[0]
