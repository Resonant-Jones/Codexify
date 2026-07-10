#!/usr/bin/env python3
"""Read explicitly allowlisted local evidence references with bounded output."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.guardian.validate_reducer_input_bundle import validate_bundle_file


READ_RESULT_SCHEMA_VERSION = "guardian_evidence_bounded_read_result.v1"
BATCH_RESULT_SCHEMA_VERSION = "guardian_evidence_bounded_read_batch_result.v1"
READ_CONTRACT_VERSION = "guardian_evidence_bounded_read_contract.v1"
DEFAULT_MAX_BYTES = 12000

READ_STATUSES = ("read", "skipped", "blocked", "missing", "too_large", "unsupported")
ALLOWED_DIRECTORIES = (
    Path("docs/architecture"),
    Path("docs/architecture/fixtures"),
    Path("docs/architecture/templates"),
)
ALLOWED_EXTENSIONS = frozenset({".md", ".json", ".txt", ".yml", ".yaml"})
LIMITS = (
    "no_execution",
    "no_evidence_ingestion",
    "no_packet_generation",
    "no_command_bus",
    "no_codex_runner",
    "no_pi_loop",
    "no_source_mutation",
    "no_provider_execution",
    "no_workorder_mutation",
    "no_execution_ledger_write",
    "no_release_support_expansion",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_result(
    bundle_ref: str,
    input_id: str,
    input_class: str,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "schema_version": READ_RESULT_SCHEMA_VERSION,
        "read_contract_version": READ_CONTRACT_VERSION,
        "input_bundle_ref": bundle_ref,
        "input_id": input_id,
        "input_class": input_class,
        "source_ref": source_ref,
        "resolved_repo_relative_path": None,
        "read_status": "skipped",
        "content_hash": None,
        "content_excerpt": None,
        "excerpt_truncated": False,
        "omitted_content_reason": None,
        "warnings": [],
        "errors": [],
        "provenance": {
            "reader": "scripts/guardian/read_bounded_evidence.py",
            "read_at": _now(),
            "source_ref_read": False,
        },
        "limits": list(LIMITS),
    }


def _set_status(
    result: dict[str, Any],
    status: str,
    *,
    warning: str | None = None,
    error: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    if status not in READ_STATUSES:
        raise ValueError(f"unknown bounded-read status: {status}")
    result["read_status"] = status
    if warning:
        result["warnings"].append(warning)
    if error:
        result["errors"].append(error)
    if reason:
        result["omitted_content_reason"] = reason
    return result


def _is_network_reference(source_ref: str) -> bool:
    parsed = urlparse(source_ref)
    return bool(parsed.scheme and parsed.scheme not in {""}) or source_ref.startswith("//")


def _is_secret_like(source_ref: str) -> bool:
    lowered = source_ref.lower()
    name = Path(lowered).name
    return (
        name in {".env", ".env.local", ".env.development", ".env.production", "credentials", "credentials.json"}
        or name in {"git-credentials", ".gitconfig"}
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
        or "private" in name
        or "/.git/" in f"/{lowered}/"
        or "/docker/volumes/" in f"/{lowered}/"
    )


def _repo_relative_path(source_ref: str) -> tuple[Path | None, str | None]:
    candidate = Path(source_ref)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, "source_ref_outside_repo"
    resolved = ( _REPO_ROOT / candidate).resolve(strict=False)
    try:
        relative = resolved.relative_to(_REPO_ROOT)
    except ValueError:
        return None, "source_ref_outside_repo"
    return relative, None


def _is_allowed_directory(relative: Path) -> bool:
    return any(
        relative == directory or directory in relative.parents
        for directory in ALLOWED_DIRECTORIES
    )


def _excerpt(raw: bytes, max_bytes: int) -> tuple[str, bool]:
    truncated = len(raw) > max_bytes
    excerpt_bytes = raw[:max_bytes]
    while True:
        try:
            return excerpt_bytes.decode("utf-8"), truncated
        except UnicodeDecodeError as exc:
            if exc.start == 0:
                raise
            excerpt_bytes = excerpt_bytes[:exc.start]


def _read_one(
    bundle_ref: str,
    item: dict[str, Any],
    max_bytes: int,
) -> dict[str, Any]:
    input_id = str(item.get("input_id", ""))
    input_class = str(item.get("input_class", ""))
    source_ref = str(item.get("source_ref", ""))
    result = _empty_result(bundle_ref, input_id, input_class, source_ref)

    if _is_network_reference(source_ref):
        return _set_status(
            result,
            "blocked",
            error="source_ref_network_url_blocked",
            reason="Network and URL references are not read.",
        )
    if _is_secret_like(source_ref):
        return _set_status(
            result,
            "blocked",
            error="source_ref_secret_risk_blocked",
            reason="Secret-like, credential, private-key, or external-volume paths are not read.",
        )

    relative, path_error = _repo_relative_path(source_ref)
    if path_error:
        return _set_status(
            result,
            "blocked",
            error=path_error,
            reason="The source reference is not a repo-relative path inside the repository.",
        )
    assert relative is not None
    result["resolved_repo_relative_path"] = relative.as_posix()

    if not _is_allowed_directory(relative):
        return _set_status(
            result,
            "skipped",
            warning="source_ref_not_allowlisted",
            reason="The repository path is outside the bounded evidence-read allowlist.",
        )
    if relative.suffix.lower() not in ALLOWED_EXTENSIONS:
        return _set_status(
            result,
            "unsupported",
            error="source_ref_unsupported_type",
            reason="Only UTF-8 text-like extensions are supported.",
        )

    target = _REPO_ROOT / relative
    if not target.exists():
        return _set_status(
            result,
            "missing",
            error="source_ref_missing",
            reason="The allowlisted source reference does not exist.",
        )
    if not target.is_file():
        return _set_status(
            result,
            "unsupported",
            error="source_ref_unsupported_type",
            reason="The allowlisted source reference is not a regular file.",
        )

    try:
        raw = target.read_bytes()
        content_hash = hashlib.sha256(raw).hexdigest()
        excerpt, truncated = _excerpt(raw, max_bytes)
    except UnicodeDecodeError:
        return _set_status(
            result,
            "unsupported",
            error="source_ref_unsupported_type",
            reason="The source file is not valid UTF-8 text.",
        )
    except OSError as exc:
        return _set_status(
            result,
            "blocked",
            error="source_ref_unsupported_type",
            reason=f"The source file could not be read: {exc}",
        )

    result["read_status"] = "read"
    result["content_hash"] = content_hash
    result["content_excerpt"] = excerpt
    result["excerpt_truncated"] = truncated
    result["provenance"].update(
        {
            "source_ref_read": True,
            "resolved_repo_relative_path": relative.as_posix(),
            "content_hash_algorithm": "sha256",
            "max_bytes": max_bytes,
        }
    )
    if truncated:
        result["warnings"].append("content_truncated")
        result["omitted_content_reason"] = (
            f"Content exceeds max_bytes={max_bytes}; excerpt is truncated."
        )
    return result


def _batch_result(
    bundle_ref: str,
    validation_result: dict[str, Any],
    read_results: list[dict[str, Any]],
    max_bytes: int,
) -> dict[str, Any]:
    counts = {status: sum(item["read_status"] == status for item in read_results) for status in READ_STATUSES}
    warning_count = sum(len(item["warnings"]) for item in read_results)
    error_count = sum(len(item["errors"]) for item in read_results)
    validation_failed = validation_result["result"] == "fail"
    has_blocking_status = any(
        item["read_status"] in {"blocked", "missing", "too_large", "unsupported"}
        for item in read_results
    )
    if validation_failed or has_blocking_status or error_count:
        result = "fail"
    elif warning_count:
        result = "pass_with_warnings"
    else:
        result = "pass"
    return {
        "schema_version": BATCH_RESULT_SCHEMA_VERSION,
        "read_contract_version": READ_CONTRACT_VERSION,
        "input_bundle_ref": bundle_ref,
        "input_bundle_validation_result": validation_result,
        "result": result,
        "source_count": len(read_results),
        "read_count": counts["read"],
        "skipped_count": counts["skipped"],
        "blocked_count": counts["blocked"],
        "missing_count": counts["missing"],
        "too_large_count": counts["too_large"],
        "unsupported_count": counts["unsupported"],
        "warning_count": warning_count,
        "error_count": error_count,
        "read_results": read_results,
        "limits": list(LIMITS) + [f"max_bytes={max_bytes}"],
    }


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--max-bytes must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--max-bytes must be greater than zero")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read explicitly allowlisted local evidence references with bounded excerpts."
    )
    parser.add_argument("input_bundle", type=Path, help="validated ReducerInputBundle JSON file")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON output")
    parser.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    bundle_ref = str(args.input_bundle)
    validation_result = validate_bundle_file(args.input_bundle)
    if validation_result["result"] == "fail":
        output = _batch_result(bundle_ref, validation_result, [], args.max_bytes)
        if args.as_json:
            print(json.dumps(output, indent=2))
        else:
            print(f"Bounded evidence read stopped: bundle validation={output['result']}")
        return 1

    try:
        bundle = json.loads(args.input_bundle.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"input bundle could not be read after validation: {exc}", file=sys.stderr)
        return 1
    read_results = [
        _read_one(bundle_ref, item, args.max_bytes)
        for item in bundle["inputs"]
    ]
    output = _batch_result(bundle_ref, validation_result, read_results, args.max_bytes)
    if args.as_json:
        print(json.dumps(output, indent=2))
    else:
        print(
            f"Bounded evidence read: result={output['result']} "
            f"sources={output['source_count']} read={output['read_count']}"
        )
    return 0 if output["result"] != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
