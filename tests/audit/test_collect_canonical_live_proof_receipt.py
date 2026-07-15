"""Isolated proof for the bounded supported-Compose live receipt collector."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.audit.collect_canonical_live_proof_receipt import (
    MUTATING_DOCKER_SUBCOMMANDS,
    HttpResponse,
    LiveProofError,
    _run_docker_command,
    _validate_docker_command,
    collect_live_proof_receipt,
    main,
)

NOW = dt.datetime(2026, 7, 15, 12, 0, tzinfo=dt.timezone.utc)
SHA = "a" * 40
IMAGE = "b" * 64


def identity_result(*, canonical: bool = False) -> dict[str, Any]:
    return {
        "observation_complete": True,
        "machine": {
            "machine_id": "vaultnode" if canonical else "test-machine",
            "machine_role": (
                "canonical_evidence_host"
                if canonical
                else "provisional_development_host"
            ),
            "hostname": "fixture-host",
            "authority_basis": "operator-confirmed"
            if canonical
            else "test-fixture",
        },
        "repository": {
            "repository_root_identity": "git:" + "c" * 64,
            "branch": "main",
            "commit_sha": SHA,
            "upstream_sha": SHA,
            "dirty": False,
            "worktree_identity": "worktree:" + "d" * 64,
        },
        "eligibility": {
            "canonical_machine_candidate": canonical,
            "canonical_repository_candidate": True,
            "reason_codes": []
            if canonical
            else ["canonical_machine_authority_not_asserted"],
        },
    }


def runtime_result() -> dict[str, Any]:
    return {
        "observation_complete": True,
        "runtime": {
            "supported_profile": "v1-local-core-web-mcp",
            "effective_config_hash": "e" * 64,
            "compose_project": "codexify-audit",
            "compose_files": ["docker-compose.yml"],
            "migration_head": "head-1",
            "service_identities": [
                "backend",
                "graph-init",
                "migrator",
                "redis",
            ],
            "compose_identity": {
                "required_services": ["backend", "migrator"],
                "optional_services": ["graph-init", "redis"],
            },
        },
        "eligibility": {
            "runtime_identity_complete": True,
            "reason_codes": [],
        },
    }


def ps_records() -> list[dict[str, Any]]:
    return [
        {
            "Service": "backend",
            "ID": "1" * 12,
            "Name": "codexify-audit-backend-1",
            "State": "running",
            "Health": "healthy",
            "ExitCode": 0,
        },
        {
            "Service": "migrator",
            "ID": "2" * 12,
            "Name": "codexify-audit-migrator-1",
            "State": "exited",
            "ExitCode": 0,
        },
        {
            "Service": "redis",
            "ID": "3" * 12,
            "Name": "codexify-audit-redis-1",
            "State": "running",
            "Health": "healthy",
            "ExitCode": 0,
        },
    ]


def image_records(
    records: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    return [
        {"Container": item["Name"], "ID": f"sha256:{IMAGE}"}
        for item in (records or ps_records())
    ]


def healthy_bodies() -> dict[str, bytes]:
    profile = {
        "name": "v1-local-core-web-mcp",
        "valid": True,
        "mismatches": [],
        "selected_provider_supported": True,
        "release_hold": False,
    }
    return {
        "/ping": b"pong\n",
        "/health": json.dumps(
            {
                "status": "healthy",
                "release_hold": False,
                "supported_profile": profile,
            }
        ).encode(),
        "/health/chat": json.dumps(
            {
                "status": "healthy",
                "ok": True,
                "completion_service": {
                    "ok": True,
                    "redis_reachable": True,
                    "enqueue_test_ok": True,
                    "worker_heartbeat_status": "fresh",
                },
            }
        ).encode(),
        "/api/health/llm": json.dumps(
            {
                "status": "online",
                "ok": True,
                "models_available": True,
                "provider_runtime": {"enabled": True},
                "release_hold": False,
                "supported_profile": profile,
            }
        ).encode(),
        "/": b"<!doctype html><title>Codexify</title>",
    }


class FakeRunner:
    def __init__(
        self,
        *,
        ps: list[dict[str, Any]] | None = None,
        images: list[dict[str, Any]] | None = None,
        missing_cli: bool = False,
        version_failure: str | None = None,
        compose_failure: str | None = None,
    ) -> None:
        self.ps = ps_records() if ps is None else ps
        self.images = image_records(self.ps) if images is None else images
        self.missing_cli = missing_cli
        self.version_failure = version_failure
        self.compose_failure = compose_failure
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        self.calls.append((list(args), kwargs))
        if self.missing_cli:
            raise FileNotFoundError("docker")
        if args[:2] == ["docker", "version"]:
            if self.version_failure is not None:
                return SimpleNamespace(
                    returncode=1,
                    stdout=b"",
                    stderr=self.version_failure.encode(),
                )
            body = {
                "Client": {"Version": "27.1.1"},
                "Server": {"Version": "27.1.1"},
            }
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(body).encode(), stderr=b""
            )
        if self.compose_failure is not None:
            return SimpleNamespace(
                returncode=1, stdout=b"", stderr=self.compose_failure.encode()
            )
        if "ps" in args:
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.ps).encode(), stderr=b""
            )
        return SimpleNamespace(
            returncode=0, stdout=json.dumps(self.images).encode(), stderr=b""
        )


class FakeTransport:
    def __init__(
        self,
        bodies: dict[str, bytes] | None = None,
        statuses: dict[str, int] | None = None,
        timeout_path: str | None = None,
    ) -> None:
        self.bodies = healthy_bodies() if bodies is None else bodies
        self.statuses = statuses or {}
        self.timeout_path = timeout_path
        self.calls: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout: float) -> HttpResponse:
        self.calls.append((url, timeout))
        path = "/" + url.split("/", 3)[3] if url.count("/") >= 3 else "/"
        if path == self.timeout_path:
            raise TimeoutError("secret transport detail")
        return HttpResponse(
            self.statuses.get(path, 200), self.bodies[path], url
        )


def collect(
    tmp_path: Path,
    *,
    runner: FakeRunner | None = None,
    transport: FakeTransport | None = None,
    canonical: bool = False,
    **overrides: Any,
) -> dict[str, Any]:
    selected_runner = runner or FakeRunner()
    selected_transport = transport or FakeTransport()

    def identity(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return identity_result(canonical=canonical)

    def runtime(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return runtime_result()

    values: dict[str, Any] = {
        "machine_id": "vaultnode" if canonical else "test-machine",
        "machine_role": (
            "canonical_evidence_host"
            if canonical
            else "provisional_development_host"
        ),
        "authority_basis": "operator-confirmed"
        if canonical
        else "test-fixture",
        "assert_canonical_machine": canonical,
        "compose_files": ["docker-compose.yml"],
        "compose_project": "codexify-audit",
        "project_role": "audit",
        "profile_name": "v1-local-core-web-mcp",
        "audit_project": "codexify-audit",
        "serving_project": "codexify-serving",
        "api_base_url": "http://127.0.0.1:8888",
        "frontend_base_url": "http://localhost:5173",
        "clock": lambda: NOW,
        "subprocess_runner": selected_runner,
        "http_transport": selected_transport,
        "identity_collector": identity,
        "runtime_collector": runtime,
    }
    values.update(overrides)
    return collect_live_proof_receipt(tmp_path, **values)


def test_pass_receipt_is_schema_valid_deterministic_and_bounded(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    transport = FakeTransport()
    first = collect(tmp_path, runner=runner, transport=transport)
    second = collect(tmp_path)
    assert first["result"] == "pass"
    assert first["validation"] == {
        "result": "pass",
        "schema_valid": True,
        "issue_count": 0,
        "issues": [],
    }
    assert first["receipt"]["execution_outcome"] == "PASS"
    assert first["receipt"]["authority_status"] == "PROVISIONAL"
    assert first["receipt"]["receipt_id"] == second["receipt"]["receipt_id"]
    assert first["receipt"]["receipt_id"].startswith(
        "live-proof-receipt-sha256-"
    )
    assert first["receipt"]["commands"] == [
        ["docker", "version", "--format", "json"],
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-p",
            "codexify-audit",
            "ps",
            "--all",
            "--format",
            "json",
        ],
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-p",
            "codexify-audit",
            "images",
            "--format",
            "json",
        ],
    ]
    for _, kwargs in runner.calls:
        assert kwargs["shell"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is False
        assert kwargs["timeout"] == 10.0
    assert [
        call[0].split("127.0.0.1:8888")[-1] for call in transport.calls[:4]
    ] == [
        "/ping",
        "/health",
        "/health/chat",
        "/api/health/llm",
    ]
    assert transport.calls[4][0] == "http://localhost:5173/"
    encoded = json.dumps(first)
    assert "<!doctype html>" not in encoded
    assert "pong" not in encoded
    ping = first["receipt"]["probes"][0]
    assert ping["response_body_sha256"] == hashlib.sha256(b"pong\n").hexdigest()
    graph = next(
        item
        for item in first["receipt"]["services"]
        if item["service"] == "graph-init"
    )
    assert graph["observation_result"] == "OPTIONAL_ABSENT"


def test_authority_is_derived_only_from_predecessor_candidates(
    tmp_path: Path,
) -> None:
    assert (
        collect(tmp_path, canonical=True)["receipt"]["authority_status"]
        == "CANONICAL"
    )
    assert collect(tmp_path)["receipt"]["authority_status"] == "PROVISIONAL"


@pytest.mark.parametrize("subcommand", sorted(MUTATING_DOCKER_SUBCOMMANDS))
def test_every_mutating_docker_subcommand_is_rejected(subcommand: str) -> None:
    with pytest.raises(LiveProofError) as error:
        _validate_docker_command(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.yml",
                "-p",
                "x",
                subcommand,
            ]
        )
    assert error.value.code == "docker_command_not_allowed"


def test_internal_non_allowlisted_command_is_rejected_before_runner(
    tmp_path: Path,
) -> None:
    calls: list[Any] = []
    with pytest.raises(LiveProofError) as error:
        _run_docker_command(
            ["docker", "inspect", "container"],
            runner=lambda *args, **kwargs: calls.append((args, kwargs)),
            root=tmp_path,
            timeout=1,
            commands=[],
            blocked_on_failure=False,
        )
    assert error.value.code == "docker_command_not_allowed"
    assert calls == []


def test_compose_env_file_is_relative_and_only_passed_as_compose_argument(
    tmp_path: Path,
) -> None:
    (tmp_path / "compose.env").write_text(
        "SECRET_SHOULD_NOT_BE_READ=value\n", encoding="utf-8"
    )
    result = collect(tmp_path, compose_environment_file="compose.env")
    assert result["result"] == "pass"
    assert (
        result["receipt"]["target"]["compose_environment_file"] == "compose.env"
    )
    for command in result["receipt"]["commands"][1:]:
        assert command[4:6] == ["--env-file", "compose.env"]
    assert "SECRET_SHOULD_NOT_BE_READ" not in json.dumps(result)


@pytest.mark.parametrize(
    ("runner", "reason"),
    [
        (FakeRunner(missing_cli=True), "docker_cli_unavailable"),
        (
            FakeRunner(version_failure="cannot connect to daemon"),
            "docker_server_unavailable",
        ),
        (
            FakeRunner(compose_failure="compose is not available"),
            "docker_compose_unavailable",
        ),
        (FakeRunner(ps=[]), "compose_project_missing"),
    ],
)
def test_unavailable_prerequisites_are_blocked(
    tmp_path: Path, runner: FakeRunner, reason: str
) -> None:
    result = collect(tmp_path, runner=runner)
    assert result["result"] == "blocked"
    assert result["receipt"]["execution_outcome"] == "BLOCKED"
    assert reason in result["reason_codes"]
    assert result["validation"]["result"] == "pass"


def test_required_service_absence_is_fail_and_optional_absence_is_not(
    tmp_path: Path,
) -> None:
    records = [item for item in ps_records() if item["Service"] != "backend"]
    failed = collect(tmp_path, runner=FakeRunner(ps=records))
    assert failed["receipt"]["execution_outcome"] == "FAIL"
    assert "required_service_missing" in failed["reason_codes"]
    assert collect(tmp_path)["receipt"]["execution_outcome"] == "PASS"


@pytest.mark.parametrize(
    ("service", "changes", "reason"),
    [
        (
            "backend",
            {"State": "exited", "ExitCode": 1},
            "required_service_not_running",
        ),
        ("backend", {"Health": "unhealthy"}, "required_service_unhealthy"),
        (
            "migrator",
            {"State": "running", "ExitCode": None},
            "required_one_shot_incomplete",
        ),
        (
            "migrator",
            {"State": "exited", "ExitCode": 1},
            "required_one_shot_failed",
        ),
    ],
)
def test_required_service_lifecycle_failures_remain_fail(
    tmp_path: Path, service: str, changes: dict[str, Any], reason: str
) -> None:
    records = ps_records()
    next(item for item in records if item["Service"] == service).update(changes)
    result = collect(tmp_path, runner=FakeRunner(ps=records))
    assert result["receipt"]["execution_outcome"] == "FAIL"
    assert reason in result["reason_codes"]


def _mutated_transport(
    path: str, change: Any, *, status: int | None = None
) -> FakeTransport:
    bodies = healthy_bodies()
    if path != "/":
        payload = json.loads(bodies[path])
        change(payload)
        bodies[path] = json.dumps(payload).encode()
    statuses = {path: status} if status is not None else None
    return FakeTransport(bodies=bodies, statuses=statuses)


@pytest.mark.parametrize(
    ("path", "change", "status", "reason"),
    [
        (
            "/health",
            lambda value: value["supported_profile"].update(
                {"name": "wrong-profile"}
            ),
            None,
            "supported_profile_mismatch",
        ),
        (
            "/health",
            lambda value: value.update({"release_hold": True}),
            None,
            "release_hold_active",
        ),
        (
            "/health/chat",
            lambda value: value["completion_service"].update({"ok": False}),
            None,
            "chat_completion_service_unhealthy",
        ),
        (
            "/api/health/llm",
            lambda value: value.update({"models_available": False}),
            None,
            "llm_models_unavailable",
        ),
        ("/", lambda value: None, 503, "frontend_probe_failed"),
    ],
)
def test_observed_health_failures_are_fail_not_blocked(
    tmp_path: Path, path: str, change: Any, status: int | None, reason: str
) -> None:
    result = collect(
        tmp_path, transport=_mutated_transport(path, change, status=status)
    )
    assert result["result"] == "fail"
    assert result["receipt"]["execution_outcome"] == "FAIL"
    assert reason in result["reason_codes"]


def test_timeout_and_malformed_json_are_error(tmp_path: Path) -> None:
    timeout = collect(tmp_path, transport=FakeTransport(timeout_path="/health"))
    assert timeout["receipt"]["execution_outcome"] == "ERROR"
    assert "http_probe_timeout" in timeout["reason_codes"]
    bodies = healthy_bodies()
    bodies["/health"] = b"not-json database_url=postgres://user:secret@host/db"
    malformed = collect(tmp_path, transport=FakeTransport(bodies=bodies))
    assert malformed["receipt"]["execution_outcome"] == "ERROR"
    assert "http_json_invalid" in malformed["reason_codes"]
    assert "postgres://" not in json.dumps(malformed)


def test_schema_failure_is_error_and_cannot_write(tmp_path: Path) -> None:
    invalid_schema = tmp_path / "invalid-schema.json"
    invalid_schema.write_text("not json", encoding="utf-8")
    result = collect(
        tmp_path,
        schema_path=invalid_schema,
        output_path="receipt.json",
    )
    assert result["result"] == "error"
    assert result["receipt"]["execution_outcome"] == "ERROR"
    assert "receipt_schema_validation_failed" in result["reason_codes"]
    assert result["validation"]["result"] == "fail"
    assert not (tmp_path / "receipt.json").exists()


def test_raw_bodies_sensitive_fields_and_host_paths_are_never_emitted(
    tmp_path: Path,
) -> None:
    bodies = healthy_bodies()
    payload = json.loads(bodies["/health"])
    payload.update(
        {
            "database_url": "postgres://user:super-secret@db/private",
            "token": "top-secret-token",
            "trace": "/Users/operator/private/project/file.py",
            "headers": {"Authorization": "Bearer credential"},
        }
    )
    bodies["/health"] = json.dumps(payload).encode()
    result = collect(tmp_path, transport=FakeTransport(bodies=bodies))
    encoded = json.dumps(result)
    assert result["result"] == "pass"
    for forbidden in (
        "postgres://",
        "super-secret",
        "top-secret-token",
        "Authorization",
        "/Users/operator",
    ):
        assert forbidden not in encoded
    health = next(
        item
        for item in result["receipt"]["probes"]
        if item["probe_id"] == "api_health"
    )
    assert (
        health["response_body_sha256"]
        == hashlib.sha256(bodies["/health"]).hexdigest()
    )


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"authority_basis": "token=super-secret"}, "forbidden_secret_input"),
        (
            {"api_base_url": "http://user:password@localhost:8888"},
            "forbidden_secret_input",
        ),
        (
            {"api_base_url": "http://example.com:8888"},
            "probe_base_not_loopback",
        ),
        (
            {"api_base_url": "http://localhost:8888/arbitrary"},
            "probe_base_url_invalid",
        ),
        (
            {"authority_basis": "/Users/operator/private"},
            "forbidden_absolute_path_input",
        ),
        ({"receipt_id": "caller-value"}, "caller_receipt_id_forbidden"),
    ],
)
def test_secret_unsafe_and_caller_owned_inputs_fail_closed(
    tmp_path: Path, overrides: dict[str, Any], reason: str
) -> None:
    result = collect(tmp_path, **overrides)
    assert result["result"] == "error"
    assert reason in result["reason_codes"]
    assert "super-secret" not in json.dumps(result)


def test_cross_host_redirect_is_error(tmp_path: Path) -> None:
    class RedirectTransport(FakeTransport):
        def __call__(self, url: str, timeout: float) -> HttpResponse:
            return HttpResponse(302, b"", url, "http://example.com/")

    result = collect(tmp_path, transport=RedirectTransport())
    assert result["receipt"]["execution_outcome"] == "ERROR"
    assert "cross_host_redirect_forbidden" in result["reason_codes"]


def test_cli_infrastructure_error_returns_two_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "--repo",
            str(tmp_path),
            "--machine-id",
            "test-machine",
            "--machine-role",
            "provisional_development_host",
            "--authority-basis",
            "test-fixture",
            "--compose-file",
            "docker-compose.yml",
            "--compose-project",
            "codexify-audit",
            "--project-role",
            "audit",
            "--audit-project",
            "codexify-audit",
            "--api-base",
            "http://127.0.0.1:8888",
            "--frontend-base",
            "http://127.0.0.1:5173",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert output["result"] == "error"
    assert output["validation"] is None


def test_output_is_atomic_and_non_overwriting_by_default(
    tmp_path: Path,
) -> None:
    first = collect(tmp_path, output_path="artifacts/live/receipt.json")
    destination = tmp_path / "artifacts/live/receipt.json"
    assert first["result"] == "pass"
    assert (
        json.loads(destination.read_text(encoding="utf-8")) == first["receipt"]
    )
    before = destination.read_bytes()
    refused = collect(tmp_path, output_path="artifacts/live/receipt.json")
    assert refused["result"] == "error"
    assert refused["reason_codes"] == ["output_exists"]
    assert destination.read_bytes() == before
    replaced = collect(
        tmp_path, output_path="artifacts/live/receipt.json", replace=True
    )
    assert replaced["result"] == "pass"
    assert (
        json.loads(destination.read_text(encoding="utf-8"))
        == replaced["receipt"]
    )
    assert not list(destination.parent.glob(".receipt.json.*"))


def test_default_collection_does_not_mutate_repository_or_run_extra_commands(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "tracked.txt"
    marker.write_text("unchanged\n", encoding="utf-8")
    before = {
        path: path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    runner = FakeRunner()
    result = collect(tmp_path, runner=runner)
    after = {
        path: path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result["result"] == "pass"
    assert after == before
    assert len(runner.calls) == 3
    for command, _ in runner.calls:
        _validate_docker_command(command)
        assert not MUTATING_DOCKER_SUBCOMMANDS.intersection(command)


def test_receipt_id_changes_with_normalized_observation(tmp_path: Path) -> None:
    first = collect(tmp_path)
    records = deepcopy(ps_records())
    next(item for item in records if item["Service"] == "backend")[
        "Health"
    ] = "unhealthy"
    second = collect(tmp_path, runner=FakeRunner(ps=records))
    assert first["receipt"]["receipt_id"] != second["receipt"]["receipt_id"]
