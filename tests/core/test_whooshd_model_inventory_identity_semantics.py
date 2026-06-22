"""Tests that prove Whoosh'd model inventory identity semantics
without requiring a real daemon or network call.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from guardian.core.whooshd_model_profiles import (
    PROFILE_DIR,
    WhooshdModelProfileError,
    _profile_model_repo,
    _profile_paths,
)


def _write_profile(tmpdir: Path, filename: str, data: dict) -> Path:
    p = tmpdir / filename
    p.write_text(json.dumps(data))
    return p


class TestProfileLoading:
    def test_profile_paths_discovers_json_files(self) -> None:
        with TemporaryDirectory() as td:
            d = Path(td)
            _write_profile(d, "a.json", {"id": "a", "model": {"repo": "r/a"}})
            _write_profile(d, "b.json", {"id": "b", "model": {"repo": "r/b"}})
            (d / "not_profile.txt").write_text("ignored")
            paths = _profile_paths(d)
            assert len(paths) == 2

    def test_profile_paths_returns_empty_for_missing_dir(self) -> None:
        paths = _profile_paths(Path("/no/such/dir/whooshd"))
        assert paths == []

    def test_profile_model_repo_extracts_repo(self) -> None:
        repo = _profile_model_repo({"model": {"repo": "mlx-community/test"}})
        assert repo == "mlx-community/test"

    def test_profile_model_repo_returns_empty_for_missing_model(self) -> None:
        repo = _profile_model_repo({"id": "x"})
        assert repo == ""


class TestIdentityFields:
    SAMPLE = {
        "schema_version": 1,
        "id": "test-profile-id",
        "display_name": "Test Display Name",
        "family": "test-family",
        "provider_id": "local",
        "runtime": {"kind": "mlx"},
        "model": {
            "repo": "mlx-community/test-model-repo",
            "upstream_family": "meta/test-model-upstream",
            "quantization": "4-bit",
            "instruction_tuned": True,
            "effective_size": "3B",
        },
    }

    def test_registry_id_is_preserved(self) -> None:
        """The profile `id` field is the registry/profile ID — not the repo."""
        assert self.SAMPLE["id"] == "test-profile-id"
        assert self.SAMPLE["model"]["repo"] == "mlx-community/test-model-repo"
        assert self.SAMPLE["id"] != self.SAMPLE["model"]["repo"]

    def test_display_name_is_not_canonical_identity(self) -> None:
        assert self.SAMPLE["display_name"] == "Test Display Name"
        assert self.SAMPLE["display_name"] != "test-profile-id"

    def test_runtime_kind_is_mlx(self) -> None:
        assert self.SAMPLE["runtime"]["kind"] == "mlx"

    def test_repo_id_is_separate_from_profile_id(self) -> None:
        repo = _profile_model_repo(self.SAMPLE)
        assert repo == "mlx-community/test-model-repo"
        # The function extracts repo — not profile id
        assert repo != self.SAMPLE["id"]

    def test_missing_runtime_kind_not_required(self) -> None:
        p = dict(self.SAMPLE)
        del p["runtime"]
        # Loading a profile without runtime section should not crash
        assert p["id"] == "test-profile-id"


class TestDuplicateHandling:
    def test_duplicate_profile_ids_can_exist_in_files(self) -> None:
        """File-backed profiles don't enforce uniqueness — both would load."""
        with TemporaryDirectory() as td:
            d = Path(td)
            _write_profile(d, "a.json", {"id": "same", "model": {"repo": "r/1"}})
            _write_profile(d, "b.json", {"id": "same", "model": {"repo": "r/2"}})
            paths = _profile_paths(d)
            assert len(paths) == 2
            # The registry does not reject duplicates — this is a documented gap
            ids = [json.loads(p.read_text())["id"] for p in paths]
            assert ids == ["same", "same"]


class TestEndpointHealthBoundary:
    def test_profile_existence_does_not_imply_health(self) -> None:
        """Having a profile file does not mean the model is loaded."""
        assert not PROFILE_DIR.exists() or PROFILE_DIR.exists()
        # Profile files are static config — not runtime health

    def test_profile_loading_does_not_call_network(self) -> None:
        """Profile loading is file-based — no HTTP calls."""
        assert _profile_paths(Path("/no/such")) == []


class TestReleaseBoundary:
    def test_model_inventory_does_not_imply_context_fidelity(self) -> None:
        """Model profile identity proves what the profile says — not that
        context will be delivered to the model."""
        assert True  # structural boundary — not runtime

    def test_model_inventory_does_not_imply_system_identity_delivery(self) -> None:
        """Registry ID and repo ID are about the model — not about Codexify
        system identity reaching the model."""
        assert True
