"""Atomic artifact publication for the provider-free Campaign Engine runtime.

Publication model (documented and test-covered):

1. All artifacts are staged under ``<output_root>/.staging-<run_id>/`` — a
   temporary SIBLING of the final ``<output_root>/<campaign_id>/`` directory
   on the same filesystem.
2. Only after every generated entity validates does the runtime promote the
   staged directory with a single atomic rename (``os.replace``).
3. Any failure removes the staged directory and leaves no promoted tree.
4. Rerun policy: if ``<output_root>/<campaign_id>/`` already exists the run
   fails fast with ``CampaignOutputExistsError``. Identical reruns into a
   fresh output root are byte-deterministic.

IDs are validated as safe path components before they ever touch the
filesystem; no path may escape ``output_root``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import CampaignArtifactError, CampaignOutputExistsError
from .validation import validate_path_component


def pretty_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def atomic_write_json(directory: Path, filename: str, payload: Any) -> Path:
    """Write one JSON file atomically inside ``directory`` (temp file + rename).

    No temporary file may remain after success or failure.
    """
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".tmp", dir=directory)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(pretty_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise CampaignArtifactError(f"failed to write {target}: {exc}") from exc
    return target


class ArtifactPublisher:
    """Stages, validates, and atomically promotes one campaign run's artifacts."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)

    def resolve_output_dir(self, campaign_id: str) -> Path:
        """Resolve and containment-check the final output directory."""
        validate_path_component(campaign_id, "campaign_id")
        resolved_root = self.output_root.resolve()
        final_dir = (resolved_root / campaign_id).resolve()
        if resolved_root not in final_dir.parents:
            raise CampaignArtifactError(
                f"resolved output path {final_dir} escapes output root {resolved_root}"
            )
        return final_dir

    def create_staging(self, campaign_id: str, run_id: str) -> tuple[Path, Path]:
        """Create the staging directory; fail fast if final output exists."""
        validate_path_component(run_id, "run_id")
        final_dir = self.resolve_output_dir(campaign_id)
        if final_dir.exists():
            raise CampaignOutputExistsError(
                f"output already exists for campaign {campaign_id!r} at {final_dir}; "
                "deterministic rerun policy requires a fresh output root "
                "(remove the existing directory to rerun)"
            )
        staging_name = f".staging-{run_id}"
        resolved_root = self.output_root.resolve()
        staging = resolved_root / staging_name
        if staging.exists():
            raise CampaignArtifactError(f"staging path already exists: {staging}")
        staging.mkdir()
        return staging, final_dir

    def promote(self, staging: Path, final_dir: Path) -> None:
        """Atomically rename the staged directory into place."""
        try:
            os.replace(staging, final_dir)
        except OSError as exc:
            raise CampaignArtifactError(
                f"failed to promote staged output to {final_dir}: {exc}"
            ) from exc

    def cleanup(self, staging: Path) -> None:
        """Remove a staged directory tree after failure (idempotent)."""
        shutil.rmtree(staging, ignore_errors=True)
