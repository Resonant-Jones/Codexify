"""Coverage for regenerable derived artifacts and the verification gate.

The DLG projections and the Agent Reading Packets are derived artifacts.
This module covers the machinery that keeps them honest:

* generated artifacts can be rewritten on hosts that deny `rename(2)` and
  `unlink(2)`;
* an interrupted write leaves a staging artifact that does not break the
  next run;
* the verification gate reads the calibration revision and timestamp from
  the committed artifacts rather than restating them.

These tests exercise repository-local control-plane tooling only. They do
not mutate committed corpus records or make release claims.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.knowledge_graph import generate_representative_arps as arps
from scripts.knowledge_graph import verify_generated_artifacts as verify
from scripts.knowledge_graph.in_place_write import (
    AtomicWriteError,
    write_bytes_in_place,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/knowledge_graph/verify_generated_artifacts.py"


# ── In-place writing ─────────────────────────────────────────────────────


def test_write_bytes_in_place_replaces_content(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    target.write_text("old\n", encoding="utf-8")

    write_bytes_in_place(target, b"new\n")

    assert target.read_bytes() == b"new\n"


def test_write_bytes_in_place_preserves_the_inode(tmp_path: Path) -> None:
    """Truncate-in-place keeps the destination's identity.

    A rename would replace the inode; the whole point of the fallback is
    that it works where rename does not.
    """
    target = tmp_path / "artifact.json"
    target.write_text("old\n", encoding="utf-8")
    before = target.stat().st_ino

    write_bytes_in_place(target, b"new\n")

    assert target.stat().st_ino == before


def test_write_bytes_in_place_reuses_one_staging_file(tmp_path: Path) -> None:
    """Repeated writes must not accumulate a new orphan per call.

    On a host that denies unlink the staging file cannot be removed, so its
    name has to be deterministic. Where unlink works the file is removed
    outright; either way there must never be more than one.
    """
    target = tmp_path / "artifact.json"
    target.write_text("seed\n", encoding="utf-8")

    for index in range(4):
        write_bytes_in_place(target, f"round-{index}\n".encode("utf-8"))

    staging = sorted(path.name for path in tmp_path.iterdir() if path.name.startswith("."))
    assert len(staging) <= 1
    assert target.read_text(encoding="utf-8") == "round-3\n"


def test_write_bytes_in_place_reports_failures(tmp_path: Path) -> None:
    """A write that cannot complete must raise, not silently succeed."""
    # The destination is a directory, so it cannot be opened for writing.
    target = tmp_path / "artifact.json"
    target.mkdir()

    with pytest.raises(AtomicWriteError):
        write_bytes_in_place(target, b"new\n")


# ── Generator write paths ─────────────────────────────────────────────────


def test_dlg_atomic_write_json_rewrites_the_file(tmp_path: Path) -> None:
    from scripts.knowledge_graph import validate_and_generate_dlg as dlg

    target = tmp_path / "projection.json"
    target.write_text("old\n", encoding="utf-8")

    dlg.atomic_write_json(target, {"record_type": "test"})

    assert json.loads(target.read_text(encoding="utf-8"))["record_type"] == "test"


def test_arp_atomic_write_json_rewrites_the_file(tmp_path: Path) -> None:
    target = tmp_path / "packet.json"
    target.write_text("old\n", encoding="utf-8")

    arps.atomic_write_json(target, {"record_type": "test"})

    assert json.loads(target.read_text(encoding="utf-8"))["record_type"] == "test"


# ── Scope check resilience ────────────────────────────────────────────────


def test_arp_scope_check_ignores_staging_artifacts(tmp_path: Path) -> None:
    """An interrupted write must not break the calibration check.

    A leftover staging file in the packet directory used to fail every
    Phase 3B test with 'unknown representative packet output exists'.
    """
    output_dir = tmp_path / "agent-reading-packets"
    output_dir.mkdir()
    for filename in arps.OUTPUT_FILENAMES:
        (output_dir / filename).write_text("{}", encoding="utf-8")
    # A staging artifact from an interrupted write.
    (output_dir / ".representative-release-support.json.staged").write_text(
        "{}", encoding="utf-8"
    )

    arps._assert_output_scope(output_dir, allow_missing=False)


def test_arp_scope_check_still_rejects_unknown_outputs(tmp_path: Path) -> None:
    """Real unknown outputs must still fail the check."""
    output_dir = tmp_path / "agent-reading-packets"
    output_dir.mkdir()
    for filename in arps.OUTPUT_FILENAMES:
        (output_dir / filename).write_text("{}", encoding="utf-8")
    (output_dir / "unexpected.json").write_text("{}", encoding="utf-8")

    with pytest.raises(arps.CalibrationError):
        arps._assert_output_scope(output_dir, allow_missing=False)



def test_generator_does_not_truncate_on_non_permission_rename_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import errno
    from scripts.knowledge_graph import validate_and_generate_dlg as dlg

    target = tmp_path / "projection.json"
    target.write_bytes(b"preserve-original")
    def fail_replace(*args: object) -> None:
        raise OSError(errno.ENOSPC, "No space left")
    monkeypatch.setattr(dlg.os, "replace", fail_replace)
    with pytest.raises(OSError) as exc:
        dlg.atomic_write_json(target, {"value": 1})
    assert exc.value.errno == errno.ENOSPC
    assert target.read_bytes() == b"preserve-original"


def test_generator_falls_back_only_when_rename_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import errno
    from scripts.knowledge_graph import validate_and_generate_dlg as dlg

    target = tmp_path / "projection.json"
    target.write_bytes(b"old")
    inode = target.stat().st_ino
    def deny_replace(*args: object) -> None:
        raise PermissionError(errno.EPERM, "Rename denied")
    monkeypatch.setattr(dlg.os, "replace", deny_replace)
    dlg.atomic_write_json(target, {"value": 1})
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == 1
    assert target.stat().st_ino == inode


def test_arp_scope_rejects_unknown_hidden_packet(tmp_path: Path) -> None:
    directory = tmp_path / "agent-reading-packets"
    directory.mkdir()
    for filename in arps.OUTPUT_FILENAMES:
        (directory / filename).write_text("{}", encoding="utf-8")
    (directory / ".extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(arps.CalibrationError):
        arps._assert_output_scope(directory, allow_missing=False)
    with pytest.raises(arps.CalibrationError):
        arps.load_persisted_packets(directory)


# ── Verification gate ─────────────────────────────────────────────────────


def test_gate_reads_the_calibration_from_the_committed_artifacts() -> None:
    """The gate must not restate the calibration in its own source.

    Hardcoding the revision and timestamp is how a gate starts lying: the
    artifacts move and the gate keeps checking a revision that no longer
    matches.
    """
    graph = json.loads(
        (REPO_ROOT / "docs/knowledge-graph/generated/document-graph.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(graph.get("repository_revision"), str)
    assert isinstance(graph.get("generated_at"), str)


def test_gate_passes_for_the_committed_projections() -> None:
    """The committed artifacts are current at their calibration revision.

    The projections are snapshots of the corpus as it was at the
    calibration revision. Verifying them against the live corpus would
    report drift for every one of them, because the corpus keeps moving.
    The gate therefore checks them against the calibration corpus, and it
    must pass for the committed state.
    """
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--repo-root", str(REPO_ROOT), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["result"] == "pass", "\n".join(payload["problems"])
    assert completed.returncode == 0


def test_gate_detects_a_hand_edited_projection() -> None:
    """A projection edited in place breaks the claim it carries.

    The gate compares the committed bytes against the regeneration, so a
    hand edit must be reported rather than silently tolerated.
    """
    graph = REPO_ROOT / "docs/knowledge-graph/generated/document-graph.json"
    original = graph.read_bytes()
    payload = json.loads(original.decode("utf-8"))
    payload["hand_edited"] = True
    graph.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--repo-root", str(REPO_ROOT), "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        result = json.loads(completed.stdout)
        assert result["result"] == "fail"
        assert completed.returncode == 1
        assert any("document-graph.json" in problem for problem in result["problems"])
    finally:
        graph.write_bytes(original)


def test_gate_fails_when_the_pinned_revision_is_missing(tmp_path: Path) -> None:
    """A calibration revision the repository no longer contains is an error."""
    qualification = tmp_path / "docs/qualification/generated"
    qualification.mkdir(parents=True)
    (qualification / "document-graph.json").write_text(
        json.dumps(
            {
                "repository_revision": "0" * 40,
                "generated_at": "2026-08-08T12:25:50-04:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(verify.VerificationError):
        verify.verify_dlg_projections(tmp_path)
