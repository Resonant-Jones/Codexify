"""Obsidian indexing utilities for beta read-only vault ingestion."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from guardian.vector.store import VectorStore

logger = logging.getLogger(__name__)

OBSIDIAN_NAMESPACE = "obsidian:local"
BETA_READONLY_MODE = "beta_read_only"
_LOGGED_FRONTMATTER_FAILURES: set[str] = set()


def _utc_now_iso(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _normalize_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        tags: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                tags.append(text)
        return tags
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    text = str(value).strip()
    return [text] if text else []


def _warn_frontmatter_parse_failed(path: str) -> None:
    if path in _LOGGED_FRONTMATTER_FAILURES:
        return
    _LOGGED_FRONTMATTER_FAILURES.add(path)
    logger.warning("frontmatter_parse_failed:%s", path)


def _parse_frontmatter(text: str, *, path: str) -> dict[str, Any]:
    # Parse frontmatter only when file starts with a leading fence.
    if text.startswith("---"):
        first_newline = text.find("\n")
        if first_newline != -1 and text[:first_newline].strip() == "---":
            end = text.find("\n---\n", first_newline + 1)
            if end != -1:
                try:
                    import yaml  # type: ignore

                    fm = yaml.safe_load(text[first_newline + 1 : end]) or {}
                    if not isinstance(fm, dict):
                        raise ValueError("frontmatter must parse to a mapping")
                    content = text[end + 5 :]
                    return {"frontmatter": fm, "content": content}
                except Exception:
                    _warn_frontmatter_parse_failed(path)
                    return {"frontmatter": {}, "content": text}
    return {"frontmatter": {}, "content": text}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _obsidian_relpath(root: Path, note: Path) -> str:
    try:
        return note.relative_to(root).as_posix()
    except ValueError:
        return note.name


def _obsidian_source_id(
    root: Path, note: Path, relpath: str | None = None
) -> str:
    rel = relpath if relpath is not None else _obsidian_relpath(root, note)
    root_id = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[
        :12
    ]
    key = f"{root_id}:{rel}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"obsidian:{digest}"


def _resolve_vault_root(vault_root: str | Path) -> Path:
    root = Path(vault_root).expanduser().resolve()
    if not root.exists():
        raise ValueError(f"vault_root_not_found:{root}")
    if not root.is_dir():
        raise ValueError(f"vault_root_not_dir:{root}")
    return root


def _is_within_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_allowed_paths(
    vault_root: Path, allowed_paths: Sequence[str | Path] | None
) -> list[Path]:
    if allowed_paths is None:
        candidates = [vault_root]
    else:
        candidates = [Path(p) for p in allowed_paths]
        if not candidates:
            raise ValueError("allowed_paths_empty")

    resolved: list[Path] = []
    for candidate in candidates:
        path = candidate
        if not path.is_absolute():
            path = vault_root / path
        resolved_path = path.expanduser().resolve()
        if not _is_within_root(resolved_path, vault_root):
            raise ValueError(f"allowed_path_outside_vault:{candidate}")
        resolved.append(resolved_path)

    return resolved


def _yield_md_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def _collect_markdown_files(
    vault_root: Path, allowed_paths: Sequence[Path]
) -> list[Path]:
    files: list[Path] = []
    for scope in allowed_paths:
        if scope.is_file():
            if scope.suffix.lower() == ".md":
                resolved = scope.resolve()
                if not _is_within_root(resolved, vault_root):
                    raise ValueError(f"file_outside_vault:{scope}")
                files.append(resolved)
            continue
        if not scope.is_dir():
            continue
        for md in scope.rglob("*.md"):
            if not md.is_file():
                continue
            resolved = md.resolve()
            if not _is_within_root(resolved, vault_root):
                raise ValueError(f"file_outside_vault:{md}")
            files.append(resolved)

    unique: dict[str, Path] = {str(path): path for path in files}
    return [unique[key] for key in sorted(unique.keys())]


def _tags_match(
    note_tags: Sequence[str], allowed_tags: Sequence[str] | None
) -> bool:
    if not allowed_tags:
        return True
    # Exact match intersection; tags are already normalized to strings
    note_set = set(note_tags)
    allowed_set = set(allowed_tags)
    return bool(note_set & allowed_set)


def _build_obsidian_items_with_failures(
    vault_root: Path,
    allowed_paths: Sequence[Path],
    *,
    indexed_at: str,
    allowed_tags: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    markdown_files = _collect_markdown_files(vault_root, allowed_paths)
    scanned = len(markdown_files)
    allowed_tag_list = _normalize_tags(allowed_tags)

    for md in markdown_files:
        try:
            raw_text = md.read_text(encoding="utf-8", errors="ignore")
            parsed = _parse_frontmatter(raw_text, path=str(md))
            fm = parsed["frontmatter"]
            content = parsed["content"]
            title = fm.get("title") or md.stem
            tags = _normalize_tags(fm.get("tags"))
            if not _tags_match(tags, allowed_tag_list):
                continue
            source_relpath = _obsidian_relpath(vault_root, md)
            source_id = _obsidian_source_id(vault_root, md, source_relpath)
            content_hash = _hash_text(content)

            items.append(
                {
                    "id": source_id,
                    "text": content,
                    "meta": {
                        "path": str(md),
                        "tags": tags,
                        "title": title,
                        "source_type": "obsidian",
                        "source_root": str(vault_root),
                        "source_path": str(md),
                        "source_relpath": source_relpath,
                        "source_id": source_id,
                        "source_content_hash": content_hash,
                        "source_title": title,
                        "vault_namespace": OBSIDIAN_NAMESPACE,
                        "indexed_at": indexed_at,
                        "content_hash": content_hash,
                        "namespace": OBSIDIAN_NAMESPACE,
                    },
                }
            )
        except Exception as exc:
            failures.append({"path": str(md), "error": str(exc)})

    return items, failures, scanned


def _build_obsidian_items(
    vault_root: Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    root = _resolve_vault_root(vault_root)
    resolved_allowlist = _resolve_allowed_paths(root, allowed_paths)
    indexed_at = _utc_now_iso()
    items, _, _ = _build_obsidian_items_with_failures(
        root,
        resolved_allowlist,
        indexed_at=indexed_at,
        allowed_tags=allowed_tags,
    )
    return items


def _delete_namespace_vectors(vector_store: Any) -> int:
    embedder = getattr(vector_store, "embedder", None)
    if embedder is None:
        raise RuntimeError("vector_store_missing_embedder")

    get_ids = getattr(embedder, "get_ids", None)
    delete_by_ids = getattr(embedder, "delete_by_ids", None)
    if not callable(get_ids) or not callable(delete_by_ids):
        raise RuntimeError("vector_store_missing_namespace_delete")

    ids = get_ids(where={"namespace": OBSIDIAN_NAMESPACE})
    if ids is None:
        ids = []
    if not isinstance(ids, list):
        raise RuntimeError("vector_store_get_ids_invalid")

    if not ids:
        return 0

    deleted = delete_by_ids(ids)
    if deleted is None:
        return len(ids)
    try:
        return int(deleted)
    except (TypeError, ValueError):
        return len(ids)


def _scan_obsidian_vault(
    vault_root: str | Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
) -> tuple[list[str], int, list[dict[str, str]]]:
    root = _resolve_vault_root(vault_root)
    resolved_allowlist = _resolve_allowed_paths(root, allowed_paths)
    allowed_tag_list = _normalize_tags(allowed_tags)

    markdown_files = _collect_markdown_files(root, resolved_allowlist)
    scanned = len(markdown_files)
    matched: list[str] = []
    failures: list[dict[str, str]] = []

    for md in markdown_files:
        try:
            raw_text = md.read_text(encoding="utf-8", errors="ignore")
            parsed = _parse_frontmatter(raw_text, path=str(md))
            tags = _normalize_tags(parsed["frontmatter"].get("tags"))
            if not _tags_match(tags, allowed_tag_list):
                continue
            matched.append(str(md.resolve()))
        except Exception as exc:
            failures.append({"path": str(md), "error": str(exc)})

    # Deterministic ordering
    matched = sorted(dict.fromkeys(matched))
    return matched, scanned, failures


def clear_obsidian_namespace(vector_store: Any | None = None) -> int:
    """Delete all vectors in the Obsidian namespace."""
    store = vector_store or VectorStore()
    return _delete_namespace_vectors(store)


def index_obsidian_vault_readonly(
    vault_root: str | Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
    vector_store: Any | None = None,
    now: datetime | None = None,
    *,
    rebuild: bool = True,
) -> dict[str, Any]:
    """Index vault markdown into the Obsidian namespace in beta read-only mode.

    Beta semantics:
    - No live sync/file watching.
    - No incremental lifecycle/idempotency guarantees.
    - Refresh path is full namespace rebuild.
    """
    if not rebuild:
        raise ValueError("obsidian_beta_requires_rebuild_refresh")

    root = _resolve_vault_root(vault_root)
    resolved_allowlist = _resolve_allowed_paths(root, allowed_paths)
    indexed_at = _utc_now_iso(now)

    store = vector_store or VectorStore()

    deleted_count = clear_obsidian_namespace(store)

    items, failures, scanned = _build_obsidian_items_with_failures(
        root,
        resolved_allowlist,
        indexed_at=indexed_at,
        allowed_tags=allowed_tags,
    )

    indexed_count = 0
    if items:
        indexed_count = store.add_texts(items)

    summary = {
        "vault_root": str(root),
        "namespace": OBSIDIAN_NAMESPACE,
        "mode": BETA_READONLY_MODE,
        "read_only": True,
        "refresh_strategy": "rebuild",
        "allowed_paths": [str(p) for p in resolved_allowlist],
        "indexed_at": indexed_at,
        "scanned": scanned,
        "indexed": indexed_count,
        "deleted": deleted_count,
        "failures": failures,
        "failure_count": len(failures),
    }
    return summary


def _scan_obsidian_vault(
    vault_root: str | Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
) -> tuple[list[str], int, list[dict[str, str]]]:
    root = _resolve_vault_root(vault_root)
    resolved_allowlist = _resolve_allowed_paths(root, allowed_paths)
    allowed_tag_list = _normalize_tags(allowed_tags)

    markdown_files = _collect_markdown_files(root, resolved_allowlist)
    scanned = len(markdown_files)
    matched: list[str] = []
    failures: list[dict[str, str]] = []

    for md in markdown_files:
        try:
            raw_text = md.read_text(encoding="utf-8", errors="ignore")
            parsed = _parse_frontmatter(raw_text, path=str(md))
            tags = _normalize_tags(parsed["frontmatter"].get("tags"))
            if not _tags_match(tags, allowed_tag_list):
                continue
            matched.append(str(md.resolve()))
        except Exception as exc:
            failures.append({"path": str(md), "error": str(exc)})

    # Deterministic ordering
    matched = sorted(dict.fromkeys(matched))
    return matched, scanned, failures


def rebuild_obsidian_namespace(
    vault_root: str | Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
    vector_store: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Supported beta refresh path: clear + full reindex."""
    return index_obsidian_vault_readonly(
        vault_root,
        allowed_paths=allowed_paths,
        allowed_tags=allowed_tags,
        vector_store=vector_store,
        now=now,
        rebuild=True,
    )


def index_obsidian_vault(
    vault_root: str | Path,
    allowed_paths: Sequence[str | Path] | None = None,
    allowed_tags: Sequence[str] | None = None,
    vector_store: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper for existing call sites."""
    return index_obsidian_vault_readonly(
        vault_root,
        allowed_paths=allowed_paths,
        allowed_tags=allowed_tags,
        vector_store=vector_store,
        now=now,
        rebuild=True,
    )


__all__ = [
    "OBSIDIAN_NAMESPACE",
    "BETA_READONLY_MODE",
    "clear_obsidian_namespace",
    "index_obsidian_vault",
    "index_obsidian_vault_readonly",
    "rebuild_obsidian_namespace",
    "_scan_obsidian_vault",
    "_build_obsidian_items",
    "_parse_frontmatter",
    "_yield_md_files",
    "_obsidian_source_id",
]
