from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_platform_readiness as readiness


def _write_file(root: Path, relative_path: str, content: str = "x") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_extension_boundary_baseline(root: Path) -> None:
    _write_file(root, "guardian/routes/command_bus.py")
    _write_file(root, "guardian/command_bus/contracts.py")
    _write_file(root, "guardian/routes/cron.py")
    _write_file(root, "guardian/workers/cron_worker.py")
    _write_file(root, "guardian/routes/agent_orchestration.py")
    _write_file(root, "guardian/agents/store.py")
    _write_file(root, "guardian/agents/events.py")
    _write_file(root, "guardian/workers/coding_worker.py")
    _write_file(
        root,
        "docs/architecture/system-overview.md",
        "Command bus layer.\nCron and job execution.\nlegacy `/tools` compatibility shim.\n",
    )
    _write_file(
        root,
        "docs/architecture/flows.md",
        "Command bus path plus Cron and job execution details.\n",
    )
    _write_file(
        root,
        "docs/architecture/00-current-state.md",
        "Coding results now return through Guardian before user-visible output.\n",
    )


def _check_by_label(
    report: readiness.DomainReport, label: str
) -> readiness.CheckResult:
    for check in report.checks:
        if check.label == label:
            return check
    raise AssertionError(f"missing check label: {label}")


def test_extension_boundary_missing_legacy_tools_route_is_not_fail(
    tmp_path, monkeypatch
) -> None:
    _seed_extension_boundary_baseline(tmp_path)
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    report = readiness.build_extension_boundary()

    legacy_check = _check_by_label(
        report, "Legacy /tools compatibility route status"
    )
    assert legacy_check.status == "WARN"
    assert not any(
        check.status == "FAIL" and "tools.py" in check.evidence
        for check in report.checks
    )


def test_extension_boundary_command_bus_presence_is_positive(
    tmp_path, monkeypatch
) -> None:
    _seed_extension_boundary_baseline(tmp_path)
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    report = readiness.build_extension_boundary()

    assert _check_by_label(report, "Command bus route present").status == "PASS"
    assert (
        _check_by_label(report, "Command bus contracts present").status
        == "PASS"
    )


def test_extension_boundary_cron_presence_is_positive(
    tmp_path, monkeypatch
) -> None:
    _seed_extension_boundary_baseline(tmp_path)
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    report = readiness.build_extension_boundary()

    assert _check_by_label(report, "Cron route present").status == "PASS"
    assert _check_by_label(report, "Cron worker present").status == "PASS"


def test_extension_boundary_agent_and_coding_seams_are_positive_when_present(
    tmp_path, monkeypatch
) -> None:
    _seed_extension_boundary_baseline(tmp_path)
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    report = readiness.build_extension_boundary()

    assert (
        _check_by_label(report, "Guardian intent spine route present").status
        == "PASS"
    )
    assert (
        _check_by_label(
            report, "Agent orchestration persistence seams present"
        ).status
        == "PASS"
    )
    assert (
        _check_by_label(
            report, "Guardian-mediated coding worker seam present"
        ).status
        == "PASS"
    )


def test_extension_boundary_keeps_manual_review_maturity_language(
    tmp_path, monkeypatch
) -> None:
    _seed_extension_boundary_baseline(tmp_path)
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    report = readiness.build_extension_boundary()

    assert report.suggested_score in {"manual review required", "1-2 likely"}
    assert len(report.manual_prompts) == 4
    assert any(check.status == "WARN" for check in report.checks)


def test_platform_readiness_json_mode_is_parseable(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    exit_code = readiness.main(["--json"])
    captured = capsys.readouterr()

    payload = json.loads(captured.out)
    assert exit_code in {0, 1}
    assert payload["repo_root_relative"] == "."
    assert set(payload["summary"]) == {"pass", "warn", "fail"}
    assert payload["domains"]
    assert all("checks" in domain for domain in payload["domains"])
