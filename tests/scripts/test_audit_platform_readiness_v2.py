from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_platform_readiness_v2 as audit


def write(root: Path, path: str, content: str = "x") -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def seed_current_state(root: Path) -> None:
    write(
        root,
        "docs/architecture/00-current-state.md",
        """## Last updated
2026-08-01

Local Docker Compose is the supported install path.

## Active blockers
Queue-coupled chat still requires healthy Redis.

The Browser campaign does not widen the default release promise and is not shipped beta behavior.
""",
    )


def test_phrase_mismatch_is_scanner_drift(tmp_path, monkeypatch) -> None:
    write(tmp_path, "docs/architecture/example.md", "renamed contract wording")
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)

    result = audit.contains(
        "example",
        ["docs/architecture/example.md"],
        ["old exact phrase"],
    )

    assert result.status == audit.INFO
    assert result.finding_type == audit.SCANNER_DRIFT


def test_current_state_contract_mismatch_is_warning(tmp_path, monkeypatch) -> None:
    write(tmp_path, "docs/architecture/00-current-state.md", "## Last updated\n2026-08-01\n")
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)

    report = audit.release_truth_domain()
    supported_path = next(
        check for check in report.checks if check.label == "Supported install path is explicit"
    )

    assert supported_path.status == audit.WARN
    assert supported_path.finding_type == audit.DOCUMENTATION_DRIFT


def test_browser_host_is_first_class_domain(tmp_path, monkeypatch) -> None:
    seed_current_state(tmp_path)
    write(tmp_path, "browser_host/package.json")
    write(tmp_path, "browser_host/src/main.js")
    write(tmp_path, "browser_host/src/runtime/navigation-policy.js")
    write(tmp_path, "browser_host/src/runtime/guardian-client.js")
    write(tmp_path, "browser_host/contracts/fixtures/fixture-index.json")
    write(tmp_path, "docs/architecture/browser-host-guardian-contract.md")
    write(tmp_path, "docs/architecture/adr/054-browser-host-topology-and-release-ownership.md")
    write(tmp_path, "docs/architecture/proofs/browser-host/example/proof.json", "{}")
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)

    report = audit.browser_host_domain()

    assert report.name == "Browser Host Readiness"
    assert any(check.status == audit.PASS for check in report.checks)
    assert any(check.finding_type == audit.PROOF_GAP for check in report.checks)


def test_json_payload_exposes_evidence_classes(tmp_path, monkeypatch, capsys) -> None:
    seed_current_state(tmp_path)
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audit, "run_git", lambda args: "")

    exit_code = audit.main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code in {0, 1}
    assert payload["audit_version"] == 2
    assert set(payload["summary"]) == {"pass", "warn", "fail", "info"}
    assert "finding_counts" in payload
    assert all(
        "finding_type" in check and "evidence_level" in check
        for domain in payload["domains"]
        for check in domain["checks"]
    )
