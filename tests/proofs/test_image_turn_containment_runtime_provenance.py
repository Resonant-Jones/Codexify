from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.proofs.prove_image_turn_containment_runtime_provenance import (
    collect_runtime_provenance,
    emit_report,
)


EXPECTED_COMMIT = "2bce6aeb9416a25d77b931b4974db7573e8951b8"
EXPECTED_COMMIT_TS = "2026-05-07T10:00:00+00:00"
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


def _fake_http_get_factory(payloads: dict[str, FakeResponse]):
    def _fake_http_get(url: str, timeout: float):
        if url not in payloads:
            raise AssertionError(f"unexpected URL: {url}")
        return payloads[url]

    return _fake_http_get


def _fake_run_command_factory(outputs: dict[tuple[str, ...], str]):
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
        return subprocess.CompletedProcess(command, 0, stdout=outputs[key], stderr="")

    return _fake_run_command


def _healthy_payloads(*, commit_in_endpoint: bool = True):
    backend_health = {
        "status": "ok",
        "service": "core",
        "runtime_commit": EXPECTED_COMMIT if commit_in_endpoint else None,
    }
    health_chat = {
        "status": "healthy",
        "provider": "local",
        "model": "library2/ministral-3:8b",
        "worker": {
            "status": "fresh",
            "heartbeat_age_seconds": 4.0,
        },
        "completion_service": {
            "ok": True,
            "worker_heartbeat_status": "fresh",
            "worker_heartbeat_age_seconds": 4.0,
        },
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
    backend_log_line: str | None = None,
    worker_log_line: str | None = None,
):
    backend_log_line = backend_log_line or f"backend commit={EXPECTED_COMMIT}"
    worker_log_line = worker_log_line or f"worker commit={EXPECTED_COMMIT}"
    return {
        ("git", "rev-parse", "HEAD"): f"{head}\n",
        ("git", "rev-parse", "--verify", EXPECTED_COMMIT): f"{EXPECTED_COMMIT}\n",
        ("git", "show", "-s", "--format=%cI", EXPECTED_COMMIT): f"{EXPECTED_COMMIT_TS}\n",
        ("docker", "compose", "ps", "-q", "backend"): "backend-container\n",
        ("docker", "inspect", "backend-container"): json.dumps(
            [
                {
                    "Id": "backend-container",
                    "Image": "sha256:backend-image",
                    "Created": backend_created,
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


def test_matching_commit_and_healthy_runtime_emits_proof_ready_result(tmp_path):
    report = collect_runtime_provenance(
        EXPECTED_COMMIT,
        repo_root=tmp_path,
        run_command=_fake_run_command_factory(_healthy_command_outputs()),
        http_get=_fake_http_get_factory(_healthy_payloads(commit_in_endpoint=True)),
    )

    assert report["proof_ready"] is True
    assert report["ok"] is True
    assert report["local_git_head"] == EXPECTED_COMMIT
    assert report["runtime_commit_source"] == "endpoint"
    assert report["backend"]["runtime_commit_source"] == "endpoint"
    assert report["backend"]["runtime_commit"] == EXPECTED_COMMIT
    assert report["worker"]["runtime_commit_source"] == "logs"
    assert report["worker"]["runtime_commit"] == EXPECTED_COMMIT
    assert report["backend"]["container_rebuilt_after_expected_commit_timestamp"] is True
    assert report["worker"]["container_rebuilt_after_expected_commit_timestamp"] is True
    assert report["errors"] == []


def test_expected_commit_mismatch_fails_provenance_gate(tmp_path):
    report = collect_runtime_provenance(
        EXPECTED_COMMIT,
        repo_root=tmp_path,
        run_command=_fake_run_command_factory(
            _healthy_command_outputs(head="c088cf59")
        ),
        http_get=_fake_http_get_factory(_healthy_payloads(commit_in_endpoint=True)),
    )

    assert report["proof_ready"] is False
    assert any("local HEAD c088cf59" in error for error in report["errors"])


def test_missing_runtime_commit_source_is_reported_honestly(tmp_path):
    report = collect_runtime_provenance(
        EXPECTED_COMMIT,
        repo_root=tmp_path,
        run_command=_fake_run_command_factory(
            _healthy_command_outputs(
                backend_log_line="backend started",
                worker_log_line="worker started",
            )
        ),
        http_get=_fake_http_get_factory(_healthy_payloads(commit_in_endpoint=False)),
    )

    assert report["proof_ready"] is True
    assert report["runtime_commit_source"] == "unavailable"
    assert report["backend"]["runtime_commit_source"] == "unavailable"
    assert report["worker"]["runtime_commit_source"] == "unavailable"


@pytest.mark.parametrize(
    ("worker_payload", "expected_error_fragment"),
    [
        (
            {
                "status": "healthy",
                "provider": "local",
                "model": "library2/ministral-3:8b",
                "worker": {
                    "status": "stale",
                    "heartbeat_age_seconds": 27.0,
                },
                "completion_service": {
                    "ok": False,
                    "worker_heartbeat_status": "stale",
                    "worker_heartbeat_age_seconds": 27.0,
                },
            },
            "worker.status not fresh",
        ),
        (
            {
                "status": "healthy",
                "provider": "local",
                "model": "library2/ministral-3:8b",
                "completion_service": {
                    "ok": True,
                    "worker_heartbeat_status": "fresh",
                },
                "worker": {"status": "fresh"},
            },
            "worker heartbeat age missing",
        ),
    ],
)
def test_stale_or_missing_worker_heartbeat_fails(
    tmp_path, worker_payload, expected_error_fragment
):
    payloads = _healthy_payloads(commit_in_endpoint=False)
    payloads["http://127.0.0.1:8888/health/chat"] = FakeResponse(worker_payload)
    report = collect_runtime_provenance(
        EXPECTED_COMMIT,
        repo_root=tmp_path,
        run_command=_fake_run_command_factory(_healthy_command_outputs()),
        http_get=_fake_http_get_factory(payloads),
    )

    assert report["proof_ready"] is False
    assert any(expected_error_fragment in error for error in report["errors"])


def test_container_created_before_expected_commit_timestamp_fails(tmp_path):
    report = collect_runtime_provenance(
        EXPECTED_COMMIT,
        repo_root=tmp_path,
        run_command=_fake_run_command_factory(
            _healthy_command_outputs(
                backend_created="2026-05-07T09:59:59+00:00",
                worker_created="2026-05-07T10:06:00+00:00",
            )
        ),
        http_get=_fake_http_get_factory(_healthy_payloads(commit_in_endpoint=True)),
    )

    assert report["proof_ready"] is False
    assert any(
        "backend container was created before expected commit timestamp" in error
        for error in report["errors"]
    )


def test_emit_report_writes_human_text_and_json(capsys):
    report = {
        "proof_ready": True,
        "expected_commit": EXPECTED_COMMIT,
        "local_git_head": EXPECTED_COMMIT,
        "expected_commit_timestamp": EXPECTED_COMMIT_TS,
        "runtime_commit_source": "endpoint",
        "backend": {
            "container_id": "backend-container",
            "container_image_id": "sha256:backend-image",
            "container_created_at": BACKEND_CREATED,
            "runtime_commit_source": "endpoint",
            "runtime_commit": EXPECTED_COMMIT,
            "runtime_version": None,
            "container_rebuilt_after_expected_commit_timestamp": True,
        },
        "worker": {
            "container_id": "worker-container",
            "container_image_id": "sha256:worker-image",
            "container_created_at": WORKER_CREATED,
            "runtime_commit_source": "logs",
            "runtime_commit": EXPECTED_COMMIT,
            "runtime_version": None,
            "container_rebuilt_after_expected_commit_timestamp": True,
        },
        "health": {"/health": {"status_code": 200, "body": {"status": "ok"}}},
        "checks": [{"name": "local_git_head_matches_expected", "ok": True, "detail": "match"}],
        "errors": [],
        "ok": True,
    }

    emit_report(report)

    captured = capsys.readouterr()
    assert "Runtime provenance check" in captured.err
    assert '"proof_ready": true' in captured.out.lower()
