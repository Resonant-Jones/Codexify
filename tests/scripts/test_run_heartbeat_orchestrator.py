"""Tests for the heartbeat orchestrator."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "content" / "run_heartbeat_orchestrator.py"

# Import the module for direct testing with mocked subprocess
sys.path.insert(0, str(ROOT))
from scripts.content import run_heartbeat_orchestrator as orch

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _run_cli(
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_md_file(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# mock subprocess helpers
# ---------------------------------------------------------------------------

_SUCCESSFUL_SENTINEL_OUTPUT = '{"markdown": "/tmp/sentinel.md", "json": "/tmp/sentinel.json", "changelog": "/tmp/CHANGELOG.beta.md"}'
_SUCCESSFUL_DEV_BLOG_OUTPUT = '{"ok": true, "target_path": "docs/Website/dev-blog/generated/2026-05-13.md", "written": true}'
_SUCCESSFUL_INSIGHT_OUTPUT = "Wrote: /tmp/insight/2026-05-13.md\n"


def _make_successful_run(
    args: list[str], **kw: object
) -> subprocess.CompletedProcess[str]:
    """Return a successful CompletedProcess based on which script is called."""
    cmd_str = " ".join(str(a) for a in args)
    if "beta_release_sentinel" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_SUCCESSFUL_SENTINEL_OUTPUT,
            stderr="",
        )
    elif "ingest_daily_dev_blog" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_SUCCESSFUL_DEV_BLOG_OUTPUT,
            stderr="",
        )
    elif "generate_resonant_daily_insight" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_SUCCESSFUL_INSIGHT_OUTPUT,
            stderr="",
        )
    elif "git" in " ".join(args):
        if "show-current" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="main\n", stderr=""
            )
        elif "rev-parse" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="abc123def\n", stderr=""
            )
        elif "status" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        else:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
    return subprocess.CompletedProcess(
        args=args, returncode=0, stdout="", stderr=""
    )


def _call_orchestrator(
    *,
    date_str: str = "2026-05-13",
    dev_blog_source: Path | None = None,
    insight_sources: list[Path] | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    skip_sentinel: bool = False,
    skip_dev_blog: bool = False,
    skip_daily_insight: bool = False,
    expect_failure: bool = False,
) -> str:
    """Call run_orchestrator directly with mocked subprocess."""
    if output_dir is None:
        output_dir = Path("/tmp/test-heartbeat")
    if insight_sources is None:
        insight_sources = []

    result = orch.run_orchestrator(
        date_str=date_str,
        dev_blog_source=dev_blog_source,
        insight_sources=insight_sources,
        output_dir=output_dir,
        dry_run=dry_run,
        force=force,
        skip_sentinel=skip_sentinel,
        skip_dev_blog=skip_dev_blog,
        skip_daily_insight=skip_daily_insight,
    )
    return result


# We patch 'scripts.content.run_heartbeat_orchestrator.subprocess.run'
# since the module imports subprocess at module scope.
PATCH_TARGET = "scripts.content.run_heartbeat_orchestrator.subprocess.run"


# ---------------------------------------------------------------------------
# dry-run (real subprocess, no mocking needed)
# ---------------------------------------------------------------------------


def test_dry_run_prints_planned_commands_and_writes_nothing(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Test\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--dev-blog-source",
        str(src),
        "--insight-source",
        str(insight_src),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    stdout = result.stdout

    # Should mention dry-run and planned commands
    assert "[DRY RUN]" in stdout

    # Should NOT write any files
    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert not report_path.exists()


def test_dry_run_no_files_written_anywhere(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nText.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nText.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--dev-blog-source",
        str(src),
        "--insight-source",
        str(insight_src),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    )

    assert result.returncode == 0
    # Nothing should be created under output_dir
    all_files = list(output_dir.glob("**/*")) if output_dir.exists() else []
    assert len(all_files) == 0


# ---------------------------------------------------------------------------
# successful orchestration (mocked subprocess, direct call)
# ---------------------------------------------------------------------------


def test_successful_orchestration_with_mocked_subprocesses(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "Heartbeat Orchestrator — 2026-05-13" in content
    assert "**Date:** 2026-05-13" in content
    assert "**Generated:**" in content
    assert "## Run Summary" in content
    assert "`passed`" in content


def test_report_includes_artifact_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Generated Artifacts" in content
    assert (
        "docs/Website/dev-blog/generated" in content or "target_path" in content
    )


# ---------------------------------------------------------------------------
# missing source failures (real CLI, no mocking needed)
# ---------------------------------------------------------------------------


def test_missing_dev_blog_source_fails_unless_skipped(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--insight-source",
        str(insight_src),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode != 0
    assert "dev-blog-source" in result.stderr.lower()


def test_missing_dev_blog_source_ok_when_skipped(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=None,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=True,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "skipped" in content.lower()


def test_missing_insight_source_fails_unless_skipped(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--dev-blog-source",
        str(src),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode != 0
    assert "insight-source" in result.stderr.lower()


def test_missing_insight_source_ok_when_skipped(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=True,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "skipped" in content.lower()


# ---------------------------------------------------------------------------
# existing report behaviour (real CLI for error, mocked for overwrite)
# ---------------------------------------------------------------------------


def test_existing_report_without_force_fails(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    output_dir.mkdir(parents=True)
    existing = output_dir / "2026-05-13-heartbeat.md"
    existing.write_text("preexisting report\n", encoding="utf-8")

    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--dev-blog-source",
        str(src),
        "--insight-source",
        str(insight_src),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode != 0
    assert (
        "already exists" in result.stderr.lower()
        or result.stderr.lower().find("already exists") >= 0
    )


def test_existing_report_with_force_overwrites(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    output_dir.mkdir(parents=True)
    existing = output_dir / "2026-05-13-heartbeat.md"
    existing.write_text("preexisting report content\n", encoding="utf-8")

    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    content = existing.read_text(encoding="utf-8")
    assert "preexisting" not in content
    assert "Heartbeat Orchestrator" in content


# ---------------------------------------------------------------------------
# child failure produces report and non-zero exit
# ---------------------------------------------------------------------------


def _make_failing_dev_blog(
    args: list[str], **kw: object
) -> subprocess.CompletedProcess[str]:
    cmd_str = " ".join(str(a) for a in args)
    if "ingest_daily_dev_blog" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="ingest-daily-dev-blog error: source file not found: /nonexistent/source.md",
        )
    if "git" in " ".join(args):
        if "show-current" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="main\n", stderr=""
            )
        elif "rev-parse" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="abc123\n", stderr=""
            )
        elif "status" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )
    if "beta_release_sentinel" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_SUCCESSFUL_SENTINEL_OUTPUT,
            stderr="",
        )
    if "generate_resonant_daily_insight" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_SUCCESSFUL_INSIGHT_OUTPUT,
            stderr="",
        )
    return subprocess.CompletedProcess(
        args=args, returncode=0, stdout="", stderr=""
    )


def test_child_failure_produces_report_and_nonzero_exit(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_failing_dev_blog):
        result_path = orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "`failed`" in content
    assert "Failures" in content

    # Verify the return path matches
    assert result_path == str(report_path)


# ---------------------------------------------------------------------------
# skipped steps appear in report
# ---------------------------------------------------------------------------


def test_skipped_steps_appear_in_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=True,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "`skipped`" in content
    assert "Skipped Steps" in content
    assert "Beta Release Sentinel" in content


# ---------------------------------------------------------------------------
# report sanitizes secret-like values
# ---------------------------------------------------------------------------


def _make_secret_leaking_run(
    args: list[str], **kw: object
) -> subprocess.CompletedProcess[str]:
    cmd_str = " ".join(str(a) for a in args)
    if "ingest_daily_dev_blog" in cmd_str:
        # Make dev blog FAIL with secret in stderr so it appears in Failures section
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="error: api_key=sk-abcdefghijklmnopqrstuvwxyz123456 not valid",  # gitleaks:allow
        )
    if "beta_release_sentinel" in cmd_str:
        # Make sentinel FAIL with secret in stdout
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout='{"markdown": "/tmp/sentinel.md"}\napi_key=sk-abcdefghijklmnopqrstuvwxyz123456',  # gitleaks:allow
            stderr="access_token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",  # gitleaks:allow
        )
    if "generate_resonant_daily_insight" in cmd_str:
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="Wrote: /tmp/insight/2026-05-13.md\ngithub_token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",  # gitleaks:allow
            stderr="",
        )
    if "git" in " ".join(args):
        if "show-current" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="main\n", stderr=""
            )
        elif "rev-parse" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="abc123\n", stderr=""
            )
        elif "status" in cmd_str:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )
    return subprocess.CompletedProcess(
        args=args, returncode=0, stdout="", stderr=""
    )


def test_report_sanitizes_secret_like_values(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_secret_leaking_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=False,
            skip_dev_blog=False,
            skip_daily_insight=False,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")

    # Secrets should be redacted
    assert (
        "sk-abcdefghijklmnopqrstuvwxyz123456" not in content
    )  # gitleaks:allow
    assert (
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890" not in content
    )  # gitleaks:allow
    assert "REDACTED" in content  # gitleaks:allow


# ---------------------------------------------------------------------------
# report uses only allowed statuses
# ---------------------------------------------------------------------------


def test_report_uses_only_allowed_statuses(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=src,
            insight_sources=[insight_src],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=True,
            skip_dev_blog=True,
            skip_daily_insight=True,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")

    ALLOWED = {"passed", "failed", "skipped"}
    # Extract all backtick-quoted status-like words from the run summary table
    # Only check status-like words in the Run Summary section
    statuses_found = set(re.findall(r"`([a-z_]+)`", content))
    for status in statuses_found:
        if status in ("passed", "failed", "skipped", "unknown"):
            assert status in ALLOWED, f"Unexpected status: {status}"
        # Other backtick-quoted things (branch names, paths) are fine


# ---------------------------------------------------------------------------
# dry-run prints planned commands
# ---------------------------------------------------------------------------


def test_dry_run_mentions_child_scripts(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"
    src = _make_md_file(tmp_path, "blog.md", "# Blog\n\nBody.\n")
    insight_src = _make_md_file(tmp_path, "insight.md", "# Insight\n\nBody.\n")

    result = _run_cli(
        "--date",
        "2026-05-13",
        "--dev-blog-source",
        str(src),
        "--insight-source",
        str(insight_src),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    )

    assert result.returncode == 0
    stdout = result.stdout
    assert "beta_release_sentinel" in stdout
    assert "ingest_daily_dev_blog" in stdout
    assert "generate_resonant_daily_insight" in stdout


# ---------------------------------------------------------------------------
# orchestrator can skip all three steps
# ---------------------------------------------------------------------------


def test_all_three_steps_can_be_skipped(tmp_path: Path) -> None:
    output_dir = tmp_path / "heartbeat-out"

    with patch(PATCH_TARGET, side_effect=_make_successful_run):
        orch.run_orchestrator(
            date_str="2026-05-13",
            dev_blog_source=None,
            insight_sources=[],
            output_dir=output_dir,
            dry_run=False,
            force=True,
            skip_sentinel=True,
            skip_dev_blog=True,
            skip_daily_insight=True,
        )

    report_path = output_dir / "2026-05-13-heartbeat.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert content.count("`skipped`") >= 3
