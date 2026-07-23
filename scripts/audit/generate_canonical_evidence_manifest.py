#!/usr/bin/env python3
"""Generate one bounded, validated canonical audit evidence manifest.

This producer assembles explicit operator metadata with the existing machine,
Git, and static runtime identity collectors. It never executes proof commands,
inspects a live runtime, stores evidence, or promotes a pointer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from scripts.audit.collect_canonical_evidence_identity import (  # noqa: E402
    CollectorError,
    collect_identity,
)
from scripts.audit.collect_canonical_live_proof_receipt import (  # noqa: E402
    receipt_id as compute_receipt_id,
)
from scripts.audit.collect_canonical_live_proof_receipt import validate_receipt
from scripts.audit.collect_canonical_runtime_identity import (  # noqa: E402
    RuntimeIdentityError,
    collect_runtime_identity,
)
from scripts.audit.validate_canonical_evidence import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    validate_manifest,
)

RESULT_SCHEMA_VERSION = "canonical_audit_evidence_manifest_result.v1"
PRODUCER_VERSION = "canonical_audit_evidence_manifest_producer.v1"
MANIFEST_SCHEMA_VERSION = "canonical_audit_evidence.v1"
VALID_PROOF_CLASSES = {
    "CURRENT_LIVE_PROOF",
    "CURRENT_TEST_PROOF",
    "HISTORICAL_LIVE_PROOF",
    "IMPLEMENTED_UNPROVEN",
    "PARTIAL_VERTICAL_SLICE",
    "DOCS_ONLY",
    "BLOCKED",
    "UNKNOWN",
}
VALID_FRESHNESS = {"CURRENT", "STALE"}
VALID_DISPOSITIONS = {"ACCEPTED", "SUPERSEDED", "CONTRADICTED", "REJECTED"}
VALID_OUTCOMES = {"PASS", "FAIL", "BLOCKED", "ERROR", "NOT_APPLICABLE"}
CLAIM_BUCKETS = ("supported", "disproved", "unresolved")
RELATIONSHIP_BUCKETS = ("supersedes", "contradicts", "derived_from")
LIVE_PROOF_REASON_CODES = frozenset(
    {
        "live_proof_receipt_required",
        "live_proof_receipt_not_found",
        "live_proof_receipt_schema_invalid",
        "live_proof_receipt_id_invalid",
        "live_proof_receipt_hash_mismatch",
        "live_proof_receipt_not_pass",
        "live_proof_machine_identity_mismatch",
        "live_proof_repository_identity_mismatch",
        "live_proof_commit_mismatch",
        "live_proof_runtime_identity_mismatch",
        "live_proof_effective_config_mismatch",
        "live_proof_compose_project_mismatch",
        "live_proof_role_mismatch",
        "live_proof_profile_mismatch",
        "live_proof_authority_ineligible",
        "live_proof_relationship_invalid",
    }
)
SECRET_KEY_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|private[_-]?key|credential)"
)
SECRET_VALUE_RE = re.compile(
    r"(?i)([a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@|"
    r"(?:postgres(?:ql)?|mysql|mariadb|redis|rediss|mongodb(?:\+srv)?|sqlite|mssql|oracle|amqp|nats)://|"
    r"(?:password|secret|token|api[_-]?key|private[_-]?key)\s*[=:])"
)


class ProducerError(Exception):
    """A bounded, machine-readable producer failure."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def _safe_text(value: Any) -> str:
    text = " ".join(str(value).split())
    text = re.sub(
        r"(?i)(https?://)([^/@\s]+):[^/@\s]+@", r"\1[redacted]@", text
    )
    text = re.sub(
        r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*\S+",
        r"\1=[redacted]",
        text,
    )
    return text[:240]


def _error_envelope(code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "result": "error",
        "manifest": None,
        "validation": None,
        "reason_codes": [code],
        "error": {"code": code, "message": _safe_text(message)},
    }


def _normalize_datetime(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProducerError(
            f"{field}_invalid", f"{field} must be an explicit date-time."
        )
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProducerError(
            f"{field}_invalid", f"{field} is not a valid date-time."
        ) from exc
    if parsed.tzinfo is None:
        raise ProducerError(
            f"{field}_invalid", f"{field} must include a timezone."
        )
    parsed = parsed.astimezone(dt.timezone.utc)
    if parsed.microsecond:
        return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _check_secret_values(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                raise ProducerError(
                    "forbidden_secret_input",
                    "Secret-bearing metadata is not accepted.",
                )
            _check_secret_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _check_secret_values(item)
    elif isinstance(value, str) and SECRET_VALUE_RE.search(value):
        raise ProducerError(
            "forbidden_secret_input", "Secret-bearing metadata is not accepted."
        )


def _require_mapping(value: Any, code: str, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProducerError(code, f"{label} must be an object.")
    return value


def _normalize_execution(
    value: Any,
    execution_outcome: str | None,
) -> tuple[str, dict[str, Any]]:
    execution = dict(_require_mapping(value, "execution_invalid", "execution"))
    declared_outcome = execution.pop("outcome", None)
    if (
        declared_outcome is not None
        and execution_outcome is not None
        and declared_outcome != execution_outcome
    ):
        raise ProducerError(
            "execution_outcome_inconsistent",
            "Execution outcome inputs disagree.",
        )
    outcome = (
        declared_outcome if declared_outcome is not None else execution_outcome
    )
    if outcome not in VALID_OUTCOMES:
        raise ProducerError(
            "execution_invalid", "execution outcome is not accepted vocabulary."
        )
    required = (
        "suite_id",
        "commands",
        "started_at",
        "completed_at",
        "exit_code",
        "summary",
    )
    if set(execution) != set(required):
        raise ProducerError(
            "execution_invalid",
            "execution fields are incomplete or unsupported.",
        )
    if (
        not isinstance(execution["suite_id"], str)
        or not execution["suite_id"].strip()
    ):
        raise ProducerError("execution_invalid", "suite_id must be non-empty.")
    commands = execution["commands"]
    if (
        not isinstance(commands, list)
        or not commands
        or any(
            not isinstance(command, str) or not command.strip()
            for command in commands
        )
    ):
        raise ProducerError(
            "execution_invalid",
            "commands must be a non-empty ordered list of strings.",
        )
    if (
        not isinstance(execution["summary"], str)
        or not execution["summary"].strip()
    ):
        raise ProducerError("execution_invalid", "summary must be non-empty.")
    normalized = {
        "suite_id": execution["suite_id"].strip(),
        "commands": [command.strip() for command in commands],
        "started_at": _normalize_datetime(
            execution["started_at"], "execution_started_at"
        ),
        "completed_at": _normalize_datetime(
            execution["completed_at"], "execution_completed_at"
        ),
        "exit_code": execution["exit_code"],
        "summary": execution["summary"].strip(),
    }
    started = dt.datetime.fromisoformat(
        normalized["started_at"].replace("Z", "+00:00")
    )
    completed = dt.datetime.fromisoformat(
        normalized["completed_at"].replace("Z", "+00:00")
    )
    if completed < started:
        raise ProducerError(
            "execution_invalid", "completed_at must not precede started_at."
        )
    exit_code = normalized["exit_code"]
    if exit_code is not None and (
        isinstance(exit_code, bool)
        or not isinstance(exit_code, int)
        or exit_code < 0
    ):
        raise ProducerError(
            "execution_invalid",
            "exit_code must be null or a non-negative integer.",
        )
    if outcome == "PASS" and exit_code != 0:
        raise ProducerError(
            "execution_outcome_inconsistent", "PASS requires exit_code 0."
        )
    if outcome in {"FAIL", "ERROR"} and (exit_code is None or exit_code == 0):
        raise ProducerError(
            "execution_outcome_inconsistent",
            f"{outcome} requires a non-zero exit_code.",
        )
    if outcome in {"BLOCKED", "NOT_APPLICABLE"} and exit_code is not None:
        raise ProducerError(
            "execution_outcome_inconsistent",
            f"{outcome} cannot claim executed exit_code.",
        )
    return outcome, normalized


def _safe_relative_path(
    raw: Any, root: Path, *, code_prefix: str, allow_absolute: bool = False
) -> tuple[str, Path]:
    if not isinstance(raw, str) or not raw.strip():
        raise ProducerError(
            f"{code_prefix}_invalid",
            "Path must be a non-empty repository-relative string.",
        )
    value = raw.strip().replace("\\", "/")
    is_absolute = (
        Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
    )
    if is_absolute and not allow_absolute:
        raise ProducerError(
            f"{code_prefix}_absolute", "Absolute paths are not accepted."
        )
    if is_absolute:
        candidate = Path(value).expanduser().resolve()
        try:
            relative = candidate.relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise ProducerError(
                f"{code_prefix}_outside_repository",
                "Path resolves outside the repository.",
            ) from exc
        return relative, candidate
    parts = PurePosixPath(value).parts
    if ".." in parts:
        raise ProducerError(
            f"{code_prefix}_parent_traversal",
            "Parent traversal is not accepted.",
        )
    relative = PurePosixPath(value).as_posix()
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ProducerError(
            f"{code_prefix}_outside_repository",
            "Path resolves outside the repository.",
        ) from exc
    return relative, candidate


def _load_metadata(path_value: str, root: Path) -> dict[str, Any]:
    _, path = _safe_relative_path(
        path_value, root, code_prefix="input_path", allow_absolute=True
    )
    try:
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProducerError(
            "input_read_failed",
            "Structured producer input could not be read as UTF-8 JSON.",
        ) from exc
    if not isinstance(parsed, dict):
        raise ProducerError(
            "input_invalid", "Structured producer input must be a JSON object."
        )
    _check_secret_values(parsed)
    return parsed


def _normalize_claims(
    value: Any, artifact_ids: set[str], suite_id: str
) -> dict[str, list[dict[str, Any]]]:
    source = (
        {bucket: [] for bucket in CLAIM_BUCKETS}
        if value is None
        else dict(_require_mapping(value, "claim_invalid", "claims"))
    )
    if set(source) != set(CLAIM_BUCKETS):
        raise ProducerError(
            "claim_invalid",
            "claims must contain exactly the supported claim buckets.",
        )
    seen: set[str] = set()
    result: dict[str, list[dict[str, Any]]] = {}
    for bucket in CLAIM_BUCKETS:
        entries = source[bucket]
        if not isinstance(entries, list):
            raise ProducerError(
                "claim_invalid", "claim buckets must be arrays."
            )
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            item = dict(_require_mapping(entry, "claim_invalid", "claim"))
            required = {
                "claim_id",
                "statement",
                "scope",
                "evidence_refs",
                "reason",
            }
            if set(item) != required or any(
                not isinstance(item[field], str) or not item[field].strip()
                for field in required - {"evidence_refs"}
            ):
                raise ProducerError(
                    "claim_invalid", "claim fields are incomplete or invalid."
                )
            claim_id = item["claim_id"].strip()
            if claim_id in seen:
                raise ProducerError(
                    "claim_id_duplicate", "claim_id values must be unique."
                )
            seen.add(claim_id)
            refs = item["evidence_refs"]
            if (
                not isinstance(refs, list)
                or not refs
                or any(
                    not isinstance(ref, str) or not ref.strip() for ref in refs
                )
            ):
                raise ProducerError(
                    "claim_invalid",
                    "claim evidence_refs must be non-empty strings.",
                )
            normalized_refs = sorted({ref.strip() for ref in refs})
            for ref in normalized_refs:
                if ref not in artifact_ids and ref != f"execution:{suite_id}":
                    raise ProducerError(
                        "claim_evidence_reference_unresolved",
                        "claim evidence_refs must resolve to an artifact or execution suite.",
                    )
            normalized.append(
                {
                    "claim_id": claim_id,
                    "statement": item["statement"].strip(),
                    "scope": item["scope"].strip(),
                    "evidence_refs": normalized_refs,
                    "reason": item["reason"].strip(),
                }
            )
        result[bucket] = sorted(
            normalized,
            key=lambda item: (
                item["claim_id"],
                json.dumps(item, sort_keys=True, separators=(",", ":")),
            ),
        )
    return result


def _normalize_relationships(value: Any) -> dict[str, list[str]]:
    source = (
        {bucket: [] for bucket in RELATIONSHIP_BUCKETS}
        if value is None
        else dict(
            _require_mapping(value, "relationship_invalid", "relationships")
        )
    )
    if set(source) != set(RELATIONSHIP_BUCKETS):
        raise ProducerError(
            "relationship_invalid",
            "relationships must contain exactly the supported buckets.",
        )
    seen: dict[str, str] = {}
    result: dict[str, list[str]] = {}
    for bucket in RELATIONSHIP_BUCKETS:
        entries = source[bucket]
        if not isinstance(entries, list):
            raise ProducerError(
                "relationship_invalid", "relationship buckets must be arrays."
            )
        normalized: list[str] = []
        for entry in entries:
            if not isinstance(entry, str) or not entry.strip():
                raise ProducerError(
                    "relationship_invalid",
                    "relationship references must be non-empty strings.",
                )
            reference = entry.strip()
            if reference in seen:
                if seen[reference] == bucket:
                    raise ProducerError(
                        "relationship_duplicate",
                        "relationship references must be unique within a bucket.",
                    )
                raise ProducerError(
                    "relationship_bucket_conflict",
                    "A relationship reference cannot occupy incompatible buckets.",
                )
            seen[reference] = bucket
            normalized.append(reference)
        result[bucket] = sorted(normalized)
    return result


def _normalize_artifacts(
    value: Any, root: Path
) -> tuple[list[dict[str, Any]], set[str]]:
    if value is None:
        return [], set()
    if not isinstance(value, list):
        raise ProducerError(
            "artifact_descriptor_invalid", "artifacts must be an array."
        )
    records: list[dict[str, Any]] = []
    artifact_ids: set[str] = set()
    artifact_paths: set[str] = set()
    for descriptor in value:
        item = dict(
            _require_mapping(
                descriptor, "artifact_descriptor_invalid", "artifact descriptor"
            )
        )
        required = {"artifact_id", "path", "media_type", "artifact_role"}
        if set(item) != required:
            raise ProducerError(
                "artifact_descriptor_invalid",
                "artifact descriptors must contain id, path, media type, and role only.",
            )
        if any(
            not isinstance(item[field], str) or not item[field].strip()
            for field in required
        ):
            raise ProducerError(
                "artifact_descriptor_invalid",
                "artifact descriptor fields must be non-empty strings.",
            )
        artifact_id = item["artifact_id"].strip()
        if artifact_id in artifact_ids:
            raise ProducerError(
                "artifact_id_duplicate", "artifact_id values must be unique."
            )
        raw_path = item["path"].strip().replace("\\", "/")
        if (
            not Path(raw_path).is_absolute()
            and not PureWindowsPath(raw_path).is_absolute()
            and ".." not in PurePosixPath(raw_path).parts
        ):
            lexical_path = root / Path(*PurePosixPath(raw_path).parts)
            if lexical_path.is_symlink():
                raise ProducerError(
                    "artifact_symlink_escape",
                    "Symlink artifacts are not accepted.",
                )
        relative, path = _safe_relative_path(
            item["path"], root, code_prefix="artifact_path"
        )
        if relative in artifact_paths:
            raise ProducerError(
                "artifact_path_duplicate", "artifact paths must be unique."
            )
        if not path.exists():
            raise ProducerError(
                "artifact_missing", "Declared artifact is missing."
            )
        if not path.is_file():
            raise ProducerError(
                "artifact_not_file", "Declared artifact is not a regular file."
            )
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise ProducerError(
                "artifact_read_failed", "Declared artifact could not be read."
            ) from exc
        artifact_ids.add(artifact_id)
        artifact_paths.add(relative)
        records.append(
            {
                "artifact_id": artifact_id,
                "path": relative,
                "sha256": digest.hexdigest(),
                "media_type": item["media_type"].strip(),
                "artifact_role": item["artifact_role"].strip(),
            }
        )
    return (
        sorted(records, key=lambda item: (item["artifact_id"], item["path"])),
        artifact_ids,
    )


def _runtime_manifest(runtime: Mapping[str, Any] | None) -> dict[str, Any]:
    if runtime is None:
        return {
            "supported_profile": None,
            "effective_config_hash": None,
            "compose_project": None,
            "compose_files": None,
            "migration_head": None,
            "service_identities": None,
        }
    return {
        field: runtime.get(field)
        for field in (
            "supported_profile",
            "effective_config_hash",
            "compose_project",
            "compose_files",
            "migration_head",
            "service_identities",
        )
    }


def _evidence_projection(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": manifest["schema_version"],
        "authority_status": manifest["authority_status"],
        "proof_class": manifest["proof_class"],
        "freshness_status": manifest["freshness_status"],
        "disposition": manifest["disposition"],
        "execution_outcome": manifest["execution_outcome"],
        "created_at": manifest["created_at"],
        "machine": manifest["machine"],
        "repository": {
            field: manifest["repository"][field]
            for field in (
                "repository_root_identity",
                "branch",
                "commit_sha",
                "upstream_sha",
                "dirty",
                "worktree_identity",
            )
        },
        "runtime": manifest["runtime"],
        "execution": manifest["execution"],
        "claims": manifest["claims"],
        "artifacts": manifest["artifacts"],
        "relationships": manifest["relationships"],
    }


def _evidence_id(manifest: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _evidence_projection(manifest),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"evidence-sha256-{hashlib.sha256(payload).hexdigest()}"


def _validate_generated_manifest(
    manifest: dict[str, Any], schema_path: str | Path, repo_root: Path
) -> dict[str, Any]:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(
                manifest, handle, ensure_ascii=False, indent=2, sort_keys=True
            )
            handle.write("\n")
        validation = validate_manifest(
            temporary_path, schema_path=schema_path, repo_root=repo_root
        )
    except OSError as exc:
        raise ProducerError(
            "manifest_validation_failed",
            "Temporary manifest validation file could not be created.",
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
    validation["validated_manifest_ref"] = "generated-manifest.json"
    return validation


def _write_output(
    manifest: Mapping[str, Any], output_path: str, root: Path, replace: bool
) -> None:
    relative, destination = _safe_relative_path(
        output_path, root, code_prefix="output_path", allow_absolute=True
    )
    lexical_destination = root / Path(*PurePosixPath(relative).parts)
    if lexical_destination.is_symlink():
        raise ProducerError(
            "output_path_invalid", "Symlink output paths are not accepted."
        )
    if destination.exists() and not replace:
        raise ProducerError(
            "output_exists", "Output exists; pass --replace to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(
                manifest, handle, ensure_ascii=False, indent=2, sort_keys=True
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise ProducerError(
            "output_write_failed",
            "Manifest output could not be written atomically.",
        ) from exc


def _process_live_proof_receipt(
    receipt_path_value: str,
    root: Path,
    machine_data: Mapping[str, Any],
    repository_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Load, validate, and extract identity from a live proof receipt.

    Returns a dict with keys:
      receipt, receipt_bytes, receipt_sha256, receipt_id_value,
      execution, artifact, derived_from_refs.

    Raises ProducerError on any validation failure.
    """
    # --- path safety ---
    relative, path = _safe_relative_path(
        receipt_path_value, root, code_prefix="live_proof_receipt_path"
    )
    # also check lexical (unresolved) path for symlinks
    lexical = (
        root / Path(*PurePosixPath(relative).parts)
        if not PurePosixPath(relative).is_absolute()
        else Path(relative)
    )
    if lexical.is_symlink() or path.is_symlink():
        raise ProducerError(
            "live_proof_receipt_path_symlink",
            "Symlink receipt paths are not accepted.",
        )
    if not path.exists():
        raise ProducerError(
            "live_proof_receipt_not_found",
            "Live proof receipt file does not exist.",
        )
    if not path.is_file():
        raise ProducerError(
            "live_proof_receipt_not_found",
            "Live proof receipt path is not a regular file.",
        )
    # --- exact-byte read ---
    try:
        receipt_bytes = path.read_bytes()
    except OSError as exc:
        raise ProducerError(
            "live_proof_receipt_not_found",
            "Live proof receipt could not be read.",
        ) from exc
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    # --- parse ---
    try:
        receipt_text = receipt_bytes.decode("utf-8")
        receipt = json.loads(receipt_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProducerError(
            "live_proof_receipt_schema_invalid",
            "Live proof receipt is not valid UTF-8 JSON.",
        ) from exc
    if not isinstance(receipt, dict):
        raise ProducerError(
            "live_proof_receipt_schema_invalid",
            "Live proof receipt must be a JSON object.",
        )
    # --- schema validation ---
    validation = validate_receipt(receipt)
    if validation["result"] != "pass":
        raise ProducerError(
            "live_proof_receipt_schema_invalid",
            "Live proof receipt failed schema validation.",
        )
    # --- field checks ---
    if receipt.get("schema_version") != "canonical_live_proof_receipt.v1":
        raise ProducerError(
            "live_proof_receipt_schema_invalid",
            "Receipt schema_version is not canonical_live_proof_receipt.v1.",
        )
    if receipt.get("proof_class") != "CURRENT_LIVE_PROOF":
        raise ProducerError(
            "live_proof_receipt_schema_invalid",
            "Receipt proof_class is not CURRENT_LIVE_PROOF.",
        )
    if receipt.get("execution_outcome") != "PASS":
        raise ProducerError(
            "live_proof_receipt_not_pass",
            "Only PASS receipts qualify for CURRENT_LIVE_PROOF manifest generation.",
        )
    # --- receipt identity ---
    declared_id = receipt.get("receipt_id", "")
    computed_id = compute_receipt_id(receipt)
    if declared_id != computed_id:
        raise ProducerError(
            "live_proof_receipt_id_invalid",
            "Declared receipt_id does not match the deterministic receipt identity.",
        )
    # --- machine identity comparison ---
    receipt_machine = receipt.get("machine", {})
    for field in ("machine_id", "machine_role", "hostname", "authority_basis"):
        if receipt_machine.get(field) != machine_data.get(field):
            raise ProducerError(
                "live_proof_machine_identity_mismatch",
                f"Receipt machine {field} does not match current observation.",
            )
    # --- repository identity comparison ---
    receipt_repo = receipt.get("repository", {})
    # commit_sha gets a dedicated reason code
    if receipt_repo.get("commit_sha") != repository_data.get("commit_sha"):
        raise ProducerError(
            "live_proof_commit_mismatch",
            "Receipt commit does not match the current checked-out commit.",
        )
    for field in (
        "repository_root_identity",
        "branch",
        "upstream_sha",
        "dirty",
        "worktree_identity",
    ):
        if receipt_repo.get(field) != repository_data.get(field):
            raise ProducerError(
                "live_proof_repository_identity_mismatch",
                f"Receipt repository {field} does not match current observation.",
            )
    # --- execution mapping ---
    receipt_commands = receipt.get("commands", [])
    encoded_commands = [
        json.dumps(
            cmd, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
        for cmd in receipt_commands
    ]
    execution = {
        "suite_id": receipt.get("suite_id", ""),
        "commands": encoded_commands,
        "started_at": receipt.get("started_at", ""),
        "completed_at": receipt.get("completed_at", ""),
        "exit_code": 0,
        "summary": f"Current live proof receipt {computed_id}; PASS observation of supported Compose project.",
    }
    # --- artifact ---
    artifact = {
        "artifact_id": computed_id,
        "path": relative,
        "sha256": receipt_sha256,
        "media_type": "application/json",
        "artifact_role": "canonical_live_proof_receipt",
    }
    # --- lineage ---
    derived_from_refs = [computed_id]
    return {
        "receipt": receipt,
        "receipt_bytes": receipt_bytes,
        "receipt_sha256": receipt_sha256,
        "receipt_id_value": computed_id,
        "execution": execution,
        "artifact": artifact,
        "derived_from_refs": derived_from_refs,
    }


def _compare_runtime_identity(
    receipt: Mapping[str, Any],
    runtime_data: Mapping[str, Any],
    audit_project: str | None,
    serving_project: str | None,
) -> None:
    """Compare receipt runtime/target identity with freshly collected runtime."""
    receipt_runtime = receipt.get("runtime", {})
    # compose_project gets dedicated reason code
    if receipt_runtime.get("compose_project") != runtime_data.get(
        "compose_project"
    ):
        raise ProducerError(
            "live_proof_compose_project_mismatch",
            "Receipt compose_project does not match.",
        )
    if receipt_runtime.get("supported_profile") != runtime_data.get(
        "supported_profile"
    ):
        raise ProducerError(
            "live_proof_profile_mismatch",
            "Receipt supported_profile does not match.",
        )
    if receipt_runtime.get("effective_config_hash") != runtime_data.get(
        "effective_config_hash"
    ):
        raise ProducerError(
            "live_proof_effective_config_mismatch",
            "Receipt effective_config_hash does not match.",
        )
    for field in ("migration_head",):
        if receipt_runtime.get(field) != runtime_data.get(field):
            raise ProducerError(
                "live_proof_runtime_identity_mismatch",
                f"Receipt runtime {field} does not match.",
            )
    # compose_files
    receipt_files = list(receipt_runtime.get("compose_files") or [])
    collected_files = list(runtime_data.get("compose_files") or [])
    if receipt_files != collected_files:
        raise ProducerError(
            "live_proof_runtime_identity_mismatch",
            "Receipt compose_files do not match.",
        )
    # service_identities (normalized sorted)
    receipt_services = sorted(receipt_runtime.get("service_identities") or [])
    collected_services = sorted(runtime_data.get("service_identities") or [])
    if receipt_services != collected_services:
        raise ProducerError(
            "live_proof_runtime_identity_mismatch",
            "Receipt service_identities do not match.",
        )
    # target comparison
    receipt_target = receipt.get("target", {})
    receipt_compose = receipt_target.get("compose_project", "")
    receipt_audit = receipt_target.get("audit_project", "")
    receipt_serving = receipt_target.get("serving_project")
    receipt_role = receipt_target.get("project_role", "")
    if audit_project is not None and receipt_audit != audit_project:
        raise ProducerError(
            "live_proof_compose_project_mismatch",
            "Receipt audit_project does not match.",
        )
    if serving_project is not None and receipt_serving != serving_project:
        raise ProducerError(
            "live_proof_compose_project_mismatch",
            "Receipt serving_project does not match.",
        )
    if receipt_role == "audit" and receipt_compose != receipt_audit:
        raise ProducerError(
            "live_proof_role_mismatch",
            "Audit receipt must select the audit project.",
        )
    if receipt_role == "serving" and (
        receipt_serving is None or receipt_compose != receipt_serving
    ):
        raise ProducerError(
            "live_proof_role_mismatch",
            "Serving receipt must select the serving project.",
        )


def generate_manifest(
    repo_path: str | Path = ".",
    *,
    machine_id: str = "local",
    machine_role: str = "provisional_development_host",
    authority_basis: str = "operator_not_asserted",
    assert_canonical_machine: bool = False,
    diagnostic_working_path: bool = False,
    machine_timeout: float = 5.0,
    hostname: str | None = None,
    runtime_identity_requested: bool = True,
    profile_name: str = "v1-local-core-web-mcp",
    profiles_dir: str | Path | None = None,
    compose_files: Sequence[str] | None = None,
    audit_project: str | None = None,
    serving_project: str | None = None,
    migration_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    proof_class: str | None = None,
    freshness_status: str | None = None,
    disposition: str | None = None,
    execution_outcome: str | None = None,
    execution: Mapping[str, Any] | None = None,
    claims: Mapping[str, Any] | None = None,
    artifacts: Sequence[Mapping[str, Any]] | None = None,
    relationships: Mapping[str, Any] | None = None,
    evidence_id: str | None = None,
    authority_status: str | None = None,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    output_path: str | None = None,
    replace: bool = False,
    live_proof_receipt_path: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic producer envelope; never execute proof work."""
    try:
        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            raise ProducerError(
                "repository_path_invalid", "Repository path is unavailable."
            )
        if (
            isinstance(machine_timeout, bool)
            or not isinstance(machine_timeout, (int, float))
            or machine_timeout <= 0
        ):
            raise ProducerError(
                "machine_timeout_invalid", "machine_timeout must be positive."
            )
        if diagnostic_working_path:
            raise ProducerError(
                "nonportable_absolute_path",
                "Diagnostic absolute paths are not emitted in manifests.",
            )
        supplied = dict(metadata or {})
        _check_secret_values(supplied)
        if evidence_id is not None or "evidence_id" in supplied:
            raise ProducerError(
                "caller_evidence_id_forbidden",
                "evidence_id is producer-generated.",
            )
        if authority_status is not None or "authority_status" in supplied:
            raise ProducerError(
                "authority_status_input_forbidden",
                "authority_status is producer-derived.",
            )
        values = {
            "created_at": created_at
            if created_at is not None
            else supplied.get("created_at"),
            "proof_class": proof_class
            if proof_class is not None
            else supplied.get("proof_class"),
            "freshness_status": freshness_status
            if freshness_status is not None
            else supplied.get("freshness_status"),
            "disposition": disposition
            if disposition is not None
            else supplied.get("disposition"),
            "execution_outcome": execution_outcome
            if execution_outcome is not None
            else supplied.get("execution_outcome"),
            "execution": execution
            if execution is not None
            else supplied.get("execution"),
            "claims": claims if claims is not None else supplied.get("claims"),
            "artifacts": artifacts
            if artifacts is not None
            else supplied.get("artifacts"),
            "relationships": relationships
            if relationships is not None
            else supplied.get("relationships"),
        }
        if values["proof_class"] not in VALID_PROOF_CLASSES:
            raise ProducerError(
                "proof_class_invalid", "proof_class is not accepted vocabulary."
            )
        is_live_proof = values["proof_class"] == "CURRENT_LIVE_PROOF"
        receipt_path = (
            live_proof_receipt_path
            if live_proof_receipt_path is not None
            else supplied.get("live_proof_receipt_path")
        )
        if is_live_proof:
            if (
                not receipt_path
                or not isinstance(receipt_path, str)
                or not receipt_path.strip()
            ):
                raise ProducerError(
                    "live_proof_receipt_required",
                    "CURRENT_LIVE_PROOF requires live_proof_receipt_path.",
                )
        if values["freshness_status"] not in VALID_FRESHNESS:
            raise ProducerError(
                "freshness_status_invalid",
                "freshness_status is not accepted vocabulary.",
            )
        if values["disposition"] not in VALID_DISPOSITIONS:
            raise ProducerError(
                "disposition_invalid", "disposition is not accepted vocabulary."
            )
        normalized_created_at = _normalize_datetime(
            values["created_at"], "created_at"
        )
        outcome, normalized_execution = _normalize_execution(
            values["execution"], values["execution_outcome"]
        )

        machine = collect_identity(
            root,
            machine_id=machine_id,
            machine_role=machine_role,
            authority_basis=authority_basis,
            assert_canonical_machine=assert_canonical_machine,
            timeout=machine_timeout,
            hostname=hostname,
        )
        machine_data = machine.get("machine")
        repository_data = machine.get("repository")
        eligibility = machine.get("eligibility", {})
        if not isinstance(machine_data, Mapping) or not isinstance(
            repository_data, Mapping
        ):
            raise ProducerError(
                "machine_identity_incomplete",
                "Machine/Git collector did not return identity fields.",
            )
        reason_codes = set(eligibility.get("reason_codes", []))
        if not eligibility.get(
            "repository_identity_complete"
        ) or not machine.get("observation_complete"):
            reason_codes.add("repository_identity_incomplete")
            return {
                "schema_version": RESULT_SCHEMA_VERSION,
                "producer_version": PRODUCER_VERSION,
                "result": "ineligible",
                "manifest": None,
                "validation": None,
                "reason_codes": sorted(reason_codes),
            }

        # --- live proof receipt processing ---
        receipt_bundle: dict[str, Any] | None = None
        if is_live_proof:
            receipt_bundle = _process_live_proof_receipt(
                receipt_path, root, machine_data, repository_data
            )
            # receipt authority must agree with freshly derived manifest authority
            receipt_authority = receipt_bundle["receipt"].get(
                "authority_status", ""
            )
            # forced runtime identity for live proof comparison
            if not runtime_identity_requested:
                runtime_identity_requested = True

        requested_runtime = supplied.get(
            "runtime_identity_requested", runtime_identity_requested
        )
        if not isinstance(requested_runtime, bool):
            raise ProducerError(
                "runtime_identity_invalid",
                "runtime_identity_requested must be boolean.",
            )
        runtime_data: Mapping[str, Any] | None = None
        if requested_runtime:
            runtime = collect_runtime_identity(
                root,
                profile_name=profile_name,
                profiles_dir=profiles_dir,
                compose_files=compose_files,
                audit_project=audit_project,
                serving_project=serving_project,
                migration_dir=migration_dir,
            )
            runtime_eligibility = runtime.get("eligibility", {})
            reason_codes.update(runtime_eligibility.get("reason_codes", []))
            if not runtime_eligibility.get("runtime_identity_complete"):
                reason_codes.add("runtime_identity_incomplete")
                return {
                    "schema_version": RESULT_SCHEMA_VERSION,
                    "producer_version": PRODUCER_VERSION,
                    "result": "ineligible",
                    "manifest": None,
                    "validation": None,
                    "reason_codes": sorted(reason_codes),
                }
            runtime_data = runtime.get("runtime")
            if not isinstance(runtime_data, Mapping):
                raise ProducerError(
                    "runtime_identity_incomplete",
                    "Runtime collector did not return identity fields.",
                )

        # --- live proof runtime identity comparison ---
        if receipt_bundle is not None and runtime_data is not None:
            _compare_runtime_identity(
                receipt_bundle["receipt"],
                runtime_data,
                audit_project,
                serving_project,
            )

        normalized_artifacts, artifact_ids = _normalize_artifacts(
            values["artifacts"], root
        )
        normalized_claims = _normalize_claims(
            values["claims"], artifact_ids, normalized_execution["suite_id"]
        )
        normalized_relationships = _normalize_relationships(
            values["relationships"]
        )
        authority_status = (
            "CANONICAL"
            if (
                eligibility.get("canonical_machine_candidate") is True
                and eligibility.get("canonical_repository_candidate") is True
                and machine_data.get("machine_id") == "vaultnode"
                and machine_data.get("machine_role")
                == "canonical_evidence_host"
            )
            else "PROVISIONAL"
        )
        # --- live proof integration: authority agreement, execution, artifact, lineage ---
        if receipt_bundle is not None:
            receipt_authority = receipt_bundle["receipt"].get(
                "authority_status", ""
            )
            if receipt_authority != authority_status:
                raise ProducerError(
                    "live_proof_authority_ineligible",
                    "Receipt authority_status must agree with derived manifest authority.",
                )
            outcome = "PASS"
            normalized_execution = receipt_bundle["execution"]
            # add receipt artifact
            receipt_artifact = receipt_bundle["artifact"]
            normalized_artifacts = [receipt_artifact] + normalized_artifacts
            artifact_ids.add(receipt_artifact["artifact_id"])
            # add receipt lineage
            receipt_refs = receipt_bundle["derived_from_refs"]
            existing_derived = set(
                normalized_relationships.get("derived_from", [])
            )
            for ref in receipt_refs:
                if ref not in existing_derived:
                    normalized_relationships["derived_from"] = sorted(
                        list(normalized_relationships["derived_from"]) + [ref]
                    )
            # re-normalize claims now that artifact_ids may include the receipt
            if normalized_claims:
                normalized_claims = _normalize_claims(
                    values["claims"],
                    artifact_ids,
                    normalized_execution["suite_id"],
                )
        manifest: dict[str, Any] = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "evidence_id": "",
            "authority_status": authority_status,
            "proof_class": values["proof_class"],
            "freshness_status": values["freshness_status"],
            "disposition": values["disposition"],
            "execution_outcome": outcome,
            "created_at": normalized_created_at,
            "machine": {
                field: machine_data[field]
                for field in (
                    "machine_id",
                    "machine_role",
                    "hostname",
                    "authority_basis",
                )
            },
            "repository": {
                field: repository_data[field]
                for field in (
                    "repository_root_identity",
                    "branch",
                    "commit_sha",
                    "upstream_sha",
                    "dirty",
                    "worktree_identity",
                )
            },
            "runtime": _runtime_manifest(runtime_data),
            "execution": normalized_execution,
            "claims": normalized_claims,
            "artifacts": normalized_artifacts,
            "relationships": normalized_relationships,
        }
        manifest["evidence_id"] = _evidence_id(manifest)
        if any(
            reference == manifest["evidence_id"]
            for references in normalized_relationships.values()
            for reference in references
        ):
            raise ProducerError(
                "relationship_self_reference",
                "A manifest cannot reference its newly generated evidence ID.",
            )
        validation = _validate_generated_manifest(manifest, schema_path, root)
        if validation["result"] != "pass":
            reason_codes.add("manifest_validation_failed")
            return {
                "schema_version": RESULT_SCHEMA_VERSION,
                "producer_version": PRODUCER_VERSION,
                "result": "fail",
                "manifest": manifest,
                "validation": validation,
                "reason_codes": sorted(reason_codes),
            }
        if output_path is not None:
            _write_output(manifest, output_path, root, replace)
        ineligible = (
            not eligibility.get("canonical_repository_candidate")
            or values["freshness_status"] != "CURRENT"
            or values["disposition"] != "ACCEPTED"
        )
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "producer_version": PRODUCER_VERSION,
            "result": "ineligible" if ineligible else "pass",
            "manifest": manifest,
            "validation": validation,
            "reason_codes": sorted(reason_codes),
        }
    except (CollectorError, RuntimeIdentityError) as exc:
        return _error_envelope(exc.code, exc.message)
    except ProducerError as exc:
        return _error_envelope(exc.code, exc.message)


generate_canonical_evidence_manifest = generate_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate one bounded canonical audit evidence manifest."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--metadata-input",
        required=True,
        help="Repository-relative JSON input for explicit evidence metadata.",
    )
    parser.add_argument("--machine-id", default="local")
    parser.add_argument(
        "--machine-role", default="provisional_development_host"
    )
    parser.add_argument("--authority-basis", default="operator_not_asserted")
    parser.add_argument("--assert-canonical-machine", action="store_true")
    parser.add_argument("--diagnostic-working-path", action="store_true")
    parser.add_argument("--machine-timeout", type=float, default=5.0)
    parser.add_argument("--profile-name", default="v1-local-core-web-mcp")
    parser.add_argument("--profiles-dir")
    parser.add_argument("--compose-file", action="append")
    parser.add_argument("--audit-project")
    parser.add_argument("--serving-project")
    parser.add_argument("--migration-dir")
    parser.add_argument("--no-runtime-identity", action="store_true")
    parser.add_argument(
        "--live-proof-receipt",
        help="Repository-relative path to a live proof receipt for CURRENT_LIVE_PROOF manifests.",
    )
    parser.add_argument("--output")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    if args.machine_timeout <= 0:
        parser.error("--machine-timeout must be positive")
    try:
        root = Path(args.repo).expanduser().resolve()
        metadata = _load_metadata(args.metadata_input, root)
    except ProducerError as exc:
        envelope = _error_envelope(exc.code, exc.message)
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 2
    result = generate_manifest(
        root,
        machine_id=args.machine_id,
        machine_role=args.machine_role,
        authority_basis=args.authority_basis,
        assert_canonical_machine=args.assert_canonical_machine,
        diagnostic_working_path=args.diagnostic_working_path,
        machine_timeout=args.machine_timeout,
        runtime_identity_requested=not args.no_runtime_identity,
        profile_name=args.profile_name,
        profiles_dir=args.profiles_dir,
        compose_files=args.compose_file,
        audit_project=args.audit_project,
        serving_project=args.serving_project,
        migration_dir=args.migration_dir,
        metadata=metadata,
        output_path=args.output,
        replace=args.replace,
        live_proof_receipt_path=args.live_proof_receipt,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["result"] == "pass":
        return 0
    if result["result"] == "ineligible":
        return 1
    return 2 if "error" in result else 1


if __name__ == "__main__":
    sys.exit(main())
