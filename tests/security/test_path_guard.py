from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_path_guard_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "guardian"
        / "security"
        / "path_guard.py"
    )
    spec = importlib.util.spec_from_file_location(
        "path_guard_test_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


path_guard = _load_path_guard_module()
PathGuardError = path_guard.PathGuardError
validate_write_path = path_guard.validate_write_path


def _symlink_or_skip(
    link_path: Path, target_path: Path, *, is_dir: bool
) -> None:
    try:
        link_path.symlink_to(target_path, target_is_directory=is_dir)
    except OSError as exc:  # pragma: no cover - platform capability branch
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")


def test_validate_write_path_accepts_relative_path_and_returns_shape(
    tmp_path: Path,
) -> None:
    root = tmp_path / "allowed"
    root.mkdir()

    validated = validate_write_path(
        "nested/file.txt",
        root,
        scope_kind="artifact",
        scope_id="artifact-1",
    )

    assert validated.requested_path == "nested/file.txt"
    assert validated.normalized_path == root / "nested" / "file.txt"
    assert validated.resolved_parent_path == root / "nested"
    assert validated.allowed_root == root.resolve()
    assert validated.scope_kind == "artifact"
    assert validated.scope_id == "artifact-1"
    assert not (root / "nested").exists()
    assert not (root / "nested" / "file.txt").exists()


def test_validate_write_path_rejects_lexical_traversal(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    escape = root.parent / "outside.txt"

    with pytest.raises(PathGuardError) as exc_info:
        validate_write_path(
            "../outside.txt",
            root,
            scope_kind="document",
            scope_id="doc-1",
        )

    assert exc_info.value.code == "PATH_GUARD_PATH_TRAVERSAL"
    assert not escape.exists()


def test_validate_write_path_rejects_symlink_escape_via_deepest_existing_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "allowed"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    escape_link = root / "escape"
    _symlink_or_skip(escape_link, outside, is_dir=True)

    with pytest.raises(PathGuardError) as exc_info:
        validate_write_path(
            "escape/new/sub/file.txt",
            root,
            scope_kind="sandbox",
            scope_id="sandbox-1",
        )

    assert exc_info.value.code == "PATH_GUARD_SYMLINK_ESCAPE"
    assert not (outside / "new" / "sub" / "file.txt").exists()


def test_validate_write_path_rejects_dangling_symlink(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    dangling_link = root / "dangling"
    _symlink_or_skip(dangling_link, outside / "missing-target", is_dir=False)

    with pytest.raises(PathGuardError) as exc_info:
        validate_write_path(
            "dangling/child.txt",
            root,
            scope_kind="memory",
            scope_id="memory-1",
        )

    assert exc_info.value.code == "PATH_GUARD_DANGLING_SYMLINK"


def test_validate_write_path_rejects_missing_allowed_root(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing-root"

    with pytest.raises(PathGuardError) as exc_info:
        validate_write_path(
            "file.txt",
            missing_root,
            scope_kind="workspace",
            scope_id="workspace-1",
        )

    assert exc_info.value.code == "PATH_GUARD_ALLOWED_ROOT_NOT_FOUND"


def test_validate_write_path_rejects_blank_scope_id(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    root.mkdir()

    with pytest.raises(PathGuardError) as exc_info:
        validate_write_path(
            "file.txt",
            root,
            scope_kind="thread",
            scope_id="  ",
        )

    assert exc_info.value.code == "PATH_GUARD_INVALID_SCOPE_ID"
