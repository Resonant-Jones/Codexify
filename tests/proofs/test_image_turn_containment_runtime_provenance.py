from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.proofs.prove_image_turn_containment_runtime_provenance import (
    RUNTIME_COMMIT_SOURCE_AUTHORITATIVE,
    RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
    RUNTIME_COMMIT_SOURCE_UNTRUSTED,
    collect_runtime_provenance,
    emit_report,
)

EXPECTED_COMMIT = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
EXPECTED_COMMIT_TS = "2026-05-07T10:00:00+00:00"
REQUIRED_FIX_COMMIT = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
BACKEND_CREATED = "2026-05-07T10:05:00+00:00"
WORKER_CREATED = "2026-05-07T10:06:00+00:00"


@dataclass
class FakeResponse:
    payload: dict
    status_code: int = 200

    def json(self):
        return self.payload

    @property
    def text(self) -> str:
        return json.dumps(self.payload)


@dataclass
class FakeCommandOutcome:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def _fake_http_get_factory(payloads: dict[str, FakeResponse]):
    def _fake_http_get(url: str, timeout: float):
        if url not in payloads:
            raise AssertionError(f"unexpected URL: {url}")
        return payloads[url]

    return _fake_http_get


def _fake_run_command_factory(
    outputs: dict[tuple[str, ...], str | FakeCommandOutcome]
):
    def _fake_run_command(
        command,
        *,
        cwd=None,
        timeout=30,
        capture_output=True,
        text=True,
        check=True,
    ):
        key = tuple(command)
        if key not in outputs:
            raise AssertionError(f"unexpected command: {command}")
        outcome = outputs[key]
        if isinstance(outcome, str):
            outcome = FakeCommandOutcome(stdout=outcome)
        if check and outcome.returncode != 0:
            raise subprocess.CalledProcessError(
                outcome.returncode,
                command,
                output=outcome.stdout,
                stderr=outcome.stderr,
            )
        return subprocess.CompletedProcess(
            command,
            outcome.returncode,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
        )

    return _fake_run_command


def _healthy_payloads(
    *,
    endpoint_commit: str | None = EXPECTED_COMMIT,
    worker_status: str = "fresh",
    worker_heartbeat_age_seconds: float | None = 4.0,
    completion_worker_status: str = "fresh",
    completion_worker_age: float | None = 4.0,
):
    backend_health = {
        "status": "ok",
        "service": "core",
        "runtime_commit": endpoint_commit,
    }
    worker_payload: dict[str, object] = {
        "status": worker_status,
    }
    if worker_heartbeat_age_seconds is not None:
        worker_payload["heartbeat_age_seconds"] = worker_heartbeat_age_seconds
    completion_payload: dict[str, object] = {
        "ok": completion_worker_status == "fresh",
        "worker_heartbeat_status": completion_worker_status,
    }
    if completion_worker_age is not None:
        completion_payload[
            "worker_heartbeat_age_seconds"
        ] = completion_worker_age

    health_chat = {
        "status": "healthy",
        "provider": "local",
        "model": "library2/ministral-3:8b",
        "worker": worker_payload,
        "completion_service": completion_payload,
    }
    llm_health = {
        "status": "ok",
        "service": "llm",
        "model": "library2/ministral-3:8b",
    }
    llm_catalog = {
        "status": "ok",
        "providers": [],
    }
    return {
        "http://127.0.0.1:8888/health": FakeResponse(backend_health),
        "http://127.0.0.1:8888/health/chat": FakeResponse(health_chat),
        "http://127.0.0.1:8888/api/health/llm": FakeResponse(llm_health),
        "http://127.0.0.1:8888/api/llm/catalog": FakeResponse(llm_catalog),
    }


def _healthy_command_outputs(
    *,
    head: str = EXPECTED_COMMIT,
    backend_created: str = BACKEND_CREATED,
    worker_created: str = WORKER_CREATED,
    backend_log_line: str = "backend started",
    worker_log_line: str = "worker started",
    contains_required_fix: bool = True,
):
    merge_base_result = (
        FakeCommandOutcome(stdout="", returncode=0)
        if contains_required_fix
        else FakeCommandOutcome(stdout="", returncode=1)
    )
    return {
        ("git", "rev-parse", "HEAD"): f"{head}\n",
        (
            "git",
            "rev-parse",
            "--verify",
            EXPECTED_COMMIT,
        ): f"{EXPECTED_COMMIT}\n",
        (
            "git",
            "show",
            "-s",
            "--format=%cI",
            EXPECTED_COMMIT,
        ): f"{EXPECTED_COMMIT_TS}\n",
        (
            "git",
            "rev-parse",
            "--verify",
            REQUIRED_FIX_COMMIT,
        ): f"{REQUIRED_FIX_COMMIT}\n",
        (
            "git",
            "merge-base",
            "--is-ancestor",
            REQUIRED_FIX_COMMIT,
            head,
        ): merge_base_result,
        ("docker", "compose", "ps", "-q", "backend"): "backend-container\n",
        ("docker", "inspect", "backend-container"): json.dumps(
            [
                {
                    "Id": "backend-container",
                    "Image": "sha256:backend-image",
                    "Created": backend_created,
                    "Config": {"Labels": {}},
                }
            ]
        ),
        (
            "docker",
            "compose",
            "logs",
            "--no-color",
            "--tail",
            "200",
            "backend",
        ): f"{backend_log_line}\n",
        ("docker", "compose", "ps", "-q", "worker-chat"): "worker-container\n",
        ("docker", "inspect", "worker-container"): json.dumps(
            [
                {
                    "Id": "worker-container",
                    "Image": "sha256:worker-image",
                    "Created": worker_created,
                    "Config": {"Labels": {}},
                }
            ]
        ),
        (
            "docker",
            "compose",
            "logs",
            "--no-color",
            "--tail",
            "200",
            "worker-chat",
        ): f"{worker_log_line}\n",
    }


def _collect(
    *,
    run_outputs: dict[tuple[str, ...], str | FakeCommandOutcome],
    payloads: dict[str, FakeResponse],
):
    return collect_runtime_provenance(
        EXPECTED_COMMIT,
        required_lineage_commit=REQUIRED_FIX_COMMIT,
        repo_root=Path("/tmp/proof-test"),
        run_command=_fake_run_command_factory(run_outputs),
        http_get=_fake_http_get_factory(payloads),
    )


def test_authoritative_runtime_commit_mismatch_fails(tmp_path):
    report = _collect(
        run_outputs=_healthy_command_outputs(),
        payloads=_healthy_payloads(
            endpoint_commit="cccccccccccccccccccccccccccccccccccccccc"
        ),
    )

    assert report["proof_ready"] is False
    assert report["backend"]["runtime_commit_source"] == (
        RUNTIME_COMMIT_SOURCE_AUTHORITATIVE
    )
    assert any(
        "authoritative runtime commit cccccccccccccccccccccccccccccccccccccccc does not match expected"
        in error
        for error in report["errors"]
    )


def test_untrusted_log_hint_mismatch_does_not_fail_when_stronger_evidence_passes():
    report = _collect(
        run_outputs=_healthy_command_outputs(
            backend_log_line="[Backend] OK: alembic_version=7a6b5c4d3e2f",
            worker_log_line="worker started",
        ),
        payloads=_healthy_payloads(endpoint_commit=None),
    )

    assert report["proof_ready"] is True
    assert (
        report["backend"]["runtime_commit_source"]
        == RUNTIME_COMMIT_SOURCE_UNTRUSTED
    )
    assert report["backend"]["runtime_commit"] == "7a6b5c4d3e2f"
    assert report["errors"] == []
    assert any(
        "runtime commit hint 7a6b5c4d3e2f" in warning
        for warning in report["warnings"]
    )


def test_missing_runtime_commit_source_is_reported_honestly():
    report = _collect(
        run_outputs=_healthy_command_outputs(),
        payloads=_healthy_payloads(endpoint_commit=None),
    )

    assert report["proof_ready"] is True
    assert report["runtime_commit_source"] == RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    assert (
        report["backend"]["runtime_commit_source"]
        == RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    )
    assert (
        report["worker"]["runtime_commit_source"]
        == RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("payload_kwargs", "expected_error_fragment"),
    [
        (
            {
                "worker_status": "stale",
                "worker_heartbeat_age_seconds": 27.0,
                "completion_worker_status": "stale",
                "completion_worker_age": 27.0,
            },
            "worker.status not fresh",
        ),
        (
            {
                "worker_status": "fresh",
                "worker_heartbeat_age_seconds": None,
                "completion_worker_status": "fresh",
                "completion_worker_age": None,
            },
            "worker heartbeat age missing",
        ),
    ],
)
def test_worker_commit_unavailable_still_requires_fresh_worker_heartbeat(
    payload_kwargs, expected_error_fragment
):
    report = _collect(
        run_outputs=_healthy_command_outputs(),
        payloads=_healthy_payloads(endpoint_commit=None, **payload_kwargs),
    )

    assert (
        report["worker"]["runtime_commit_source"]
        == RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    )
    assert report["proof_ready"] is False
    assert any(expected_error_fragment in error for error in report["errors"])


def test_local_head_missing_required_fix_commit_fails_readiness():
    report = _collect(
        run_outputs=_healthy_command_outputs(contains_required_fix=False),
        payloads=_healthy_payloads(endpoint_commit=None),
    )

    assert report["proof_ready"] is False
    assert report["local_head_contains_required_lineage_commit"] is False
    assert any(
        "does not contain required lineage commit" in error
        for error in report["errors"]
    )


def test_local_head_containing_required_fix_commit_passes_lineage_check():
    report = _collect(
        run_outputs=_healthy_command_outputs(contains_required_fix=True),
        payloads=_healthy_payloads(endpoint_commit=None),
    )

    assert report["proof_ready"] is True
    assert report["local_head_contains_required_lineage_commit"] is True
    lineage_checks = [
        check
        for check in report["checks"]
        if check.get("name") == "local_head_contains_required_lineage_commit"
    ]
    assert lineage_checks and lineage_checks[0]["ok"] is True


def test_container_created_before_expected_commit_timestamp_fails():
    report = _collect(
        run_outputs=_healthy_command_outputs(
            backend_created="2026-05-07T09:59:59+00:00",
            worker_created=WORKER_CREATED,
        ),
        payloads=_healthy_payloads(endpoint_commit=None),
    )

    assert report["proof_ready"] is False
    assert any(
        "backend container was created before expected commit timestamp"
        in error
        for error in report["errors"]
    )


def test_emit_report_writes_human_text_and_json(capsys):
    report = {
        "proof_ready": True,
        "expected_commit": EXPECTED_COMMIT,
        "local_git_head": EXPECTED_COMMIT,
        "required_lineage_commit": REQUIRED_FIX_COMMIT,
        "local_head_contains_required_lineage_commit": True,
        "expected_commit_timestamp": EXPECTED_COMMIT_TS,
        "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
        "backend": {
            "container_id": "backend-container",
            "container_image_id": "sha256:backend-image",
            "container_created_at": BACKEND_CREATED,
            "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
            "runtime_commit": None,
            "authoritative_runtime_commit": None,
            "build_metadata_commit": None,
            "log_hint_commit": None,
            "untrusted_log_hint_commit": None,
            "runtime_version": None,
            "container_rebuilt_after_expected_commit_timestamp": True,
        },
        "worker": {
            "container_id": "worker-container",
            "container_image_id": "sha256:worker-image",
            "container_created_at": WORKER_CREATED,
            "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
            "runtime_commit": None,
            "authoritative_runtime_commit": None,
            "build_metadata_commit": None,
            "log_hint_commit": None,
            "untrusted_log_hint_commit": None,
            "runtime_version": None,
            "container_rebuilt_after_expected_commit_timestamp": True,
        },
        "health": {"/health": {"status_code": 200, "body": {"status": "ok"}}},
        "checks": [
            {
                "name": "local_git_head_matches_expected",
                "ok": True,
                "detail": "match",
            }
        ],
        "warnings": [],
        "errors": [],
        "ok": True,
    }

    emit_report(report)

    captured = capsys.readouterr()
    assert "Runtime provenance check" in captured.err
    assert '"proof_ready": true' in captured.out.lower()
