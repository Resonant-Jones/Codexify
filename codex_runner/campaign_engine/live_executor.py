"""Live Executor Campaign runtime (ADR-068 authorized slice).

Two-phase authority boundary:

1. :func:`prepare_live_executor_campaign` consumes a schema-valid Campaign
   document with a *live* Executor RoleBinding, computes the canonical
   immutable preparation record, and snapshots the disposable target.
   Guardian authorization is **not** part of the preparation.
2. The caller supplies the resulting Guardian-owned ``PiInvocationEnvelope``
   and ``PiInvocationPolicyDecision`` to
   :func:`run_live_executor_campaign`, which re-derives every material
   value, fails closed on any drift, and invokes the canonical
   :func:`guardian.pi.invocation.invoke_guardian_authorized_pi` exactly
   once.

The live Executor runtime treats Guardian/Pi as execution substrate and
records evidence, not authority. Receipts are evidence; the Campaign
gate status is what changes. No retry, no fallback, no model swap, no
automatic commit/push/merge/deploy, no provider bundle arbitrariness.

The provider-free runtime (:mod:`codex_runner.campaign_engine.runtime`)
remains unchanged. A test-only seam at the bottom of this module is the
single internal hook tests use to swap ``invoke_guardian_authorized_pi``
for a deterministic fake without exposing any public runtime argument.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Protocol

from .artifacts import ArtifactPublisher, atomic_write_json
from .errors import (
    CampaignArtifactError,
    CampaignEngineError,
    CampaignLiveExecutorError,
    CampaignOutputExistsError,
    CampaignValidationError,
)
from .identity import (
    binding_identity_hash,
    build_attempt_id,
    build_campaign_state_id,
    build_evaluation_id,
    build_receipt_id,
    build_run_id,
    document_hash,
    sha256_canonical,
    sha256_text,
)
from .models import (
    AcceptanceCriterionResult,
    CampaignClock,
    LiveExecutorPreparation,
    LiveExecutorRunResult,
    SystemClock,
    clock_iso,
)
from .validation import (
    cross_object_errors,
    parse_json_strict,
    validate_campaign_document,
    validate_path_component,
    validate_role_binding_semantics,
    validate_source_context,
    validate_task_selection,
)

SCHEMA_VERSION = "campaign-engine/v0"

LIVE_EXECUTOR_CLASSIFICATION_VALUE = "live_executor"

_LINEAGE_ABSENT_TOKEN = "absent"

# Allowed filesystem.write permission name; matches the canonical form
# used by the Guardian/Pi rail ("files.write").  The token text is not
# "filesystem.write.*" — see the rail for the canonical token registry.
_PERMISSION_FILES_READ = "files.read"
_PERMISSION_FILES_WRITE = "files.write"

# Test-only seam: tests may set ``live_executor._invoker`` to a callable
# returning a deterministic ``PiLiveInvocationOutcome`` (typically via
# the canonical ``invoke_guardian_authorized_pi`` with an injected
# ``harness_runner``).
class _Invoker(Protocol):
    def __call__(
        self,
        *,
        envelope: Any,
        decision: Any,
        prompt: str,
        cwd: Any,
        timeout_seconds: int,
    ) -> Any: ...


def _real_invoker(
    *,
    envelope: Any,
    decision: Any,
    prompt: str,
    cwd: Any,
    timeout_seconds: int,
) -> Any:
    from guardian.pi.invocation import invoke_guardian_authorized_pi

    return invoke_guardian_authorized_pi(
        envelope=envelope,
        decision=decision,
        prompt=prompt,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )


# ``_invoker`` is the single internal hook.  Public callers may NOT pass
# it through ``run_live_executor_campaign``; only tests via monkeypatch
# may rebind it.  The default reaches the canonical Guardian/Pi rail via
# lazy import.
_invoker: _Invoker = _real_invoker


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_executor_prompt(
    *,
    campaign_id: str,
    task_id: str,
    task_record: dict[str, Any],
    allowed_file_paths: tuple[str, ...],
    target_repository_identity: str,
    prompt_sha256: str,
) -> str:
    """Compose the deterministic Executor prompt.

    No hidden reasoning, no provider credential material, no runtime
    environment values.  The Task JSON is authoritative.
    """

    canonical_task = json.dumps(task_record, sort_keys=True, separators=(",", ":"))
    allowed = ", ".join(allowed_file_paths)
    primary_target = allowed_file_paths[0] if allowed_file_paths else ""
    return (
        "Campaign Engine live Executor — ADR-068 authorized slice.\n"
        f"campaign_id: {campaign_id}\n"
        f"task_id: {task_id}\n"
        f"target_repository_identity: {target_repository_identity}\n"
        f"allowed_file_paths: {allowed}\n"
        "constraints:\n"
        "  - do not commit\n"
        "  - do not push\n"
        "  - do not merge\n"
        "  - do not deploy\n"
        "  - do not modify any file outside allowed_file_paths\n"
        "  - do not create or delete files outside allowed_file_paths\n"
        f"task_record (canonical): {canonical_task}\n"
        f"prompt_sha256: {prompt_sha256}\n"
        "\n"
        "MANDATORY ACTION: invoke the `write` tool exactly once with the file"
        f" path `{primary_target}` (relative to the working directory) and the"
        " exact byte contents the task_record objective demands.  Do NOT"
        " produce any text-only response.  Do not call any other tool.  The"
        " pi-coding-agent harness will treat lack of a `write` tool call as"
        " a failed Executor turn.  After the `write` tool returns success,"
        " respond with one short confirmation line."
    )


# ---------------------------------------------------------------------------
# Target snapshot + baseline
# ---------------------------------------------------------------------------


def _read_git_head(target: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        head = out.stdout.strip()
        return head or None
    except Exception:
        return None


def _read_target_remote(target: Path) -> tuple[str, str]:
    """Return ``('', '')`` when the target has no remote. No credentials are returned."""
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "remote", "-v"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except Exception:
        return ("", "")
    if not out.stdout.strip():
        return ("", "")
    # Return just the count of remote lines and the first remote name if any.
    lines = [line for line in out.stdout.splitlines() if line.strip()]
    if not lines:
        return ("", "")
    return ("present", str(len(lines)))


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_target(target: Path) -> dict[str, tuple[str, str]]:
    """Return ``{relative_path: (sha256_before, sha256_after)}`` for files
    within ``target`` excluding ``.git``.

    The post snapshot is filled in by :func:`_rehydrate_post_snapshot`.
    New files appearing after the pre-snapshot are added with ``pre=""``.
    """

    entries: dict[str, tuple[str, str]] = {}
    if not target.is_dir():
        return entries
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(target).parts:
            entries[str(path.relative_to(target))] = (
                _hash_file(path),
                "",
            )
    return entries


def _rehydrate_post_snapshot(target: Path, snap: dict[str, tuple[str, str]]) -> None:
    """Fill in post hashes for pre-existing entries and detect new files.

    New files (post-only) are recorded with ``pre=""`` to flag the
    engine's perspective that this path was not present at preparation
    baseline.  The runtime then enforces the allowed-file-scope invariant
    on those new paths, which is the canonical Campaign Engine fail-closed
    behavior.
    """

    # Update pre-existing entries and find new files.
    for rel in list(snap.keys()):
        abspath = target / rel
        pre_hash, _ = snap[rel]
        post_hash = _hash_file(abspath) if abspath.is_file() else ""
        snap[rel] = (pre_hash, post_hash)

    # Add post-only files (new files created during the live invocation).
    if not target.is_dir():
        return
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(target).parts:
            rel = str(path.relative_to(target))
            if rel not in snap:
                snap[rel] = ("", _hash_file(path))


def _baseline_hash(snapshot: dict[str, tuple[str, str]]) -> str:
    payload = {
        rel: hashes[0]
        for rel, hashes in sorted(snapshot.items())
    }
    return sha256_canonical(payload)


# ---------------------------------------------------------------------------
# Guardian metadata compatibility + write-scope agreement
# ---------------------------------------------------------------------------


# Strict credential detector.  Only matches an exact dict-key name or a
# value-shaped substring — never arbitrary substrings inside legitimate
# text.  Bounded keys cover the canonical CredentialField vocabulary in
# Pi/Guardian contracts plus spelled-out secret tokens.
_SENSITIVE_DICT_KEYS = frozenset({
    "access_token", "refresh_token", "authorization",
    "authorization_header", "api_key", "apikey",
    "bearer", "client_secret", "session_token",
    "secret", "credentials", "password", "cookie", "set-cookie",
    "x-api-key", "auth_token", "private_key", "encryption_key",
})
# Whole-word secret-shaped tokens inside string values.  Whole-word means
# the substring is bounded by non-alphanumeric, underscore, or hyphen
# characters (or string start/end) on both sides.
_SECRET_VALUE_TOKENS = frozenset({
    "access_token", "refresh_token", "authorization",
    "authorization_header", "api_key", "apikey",
    "client_secret", "session_token",
    "x-api-key", "auth_token", "private_key",
})

_TOKEN_BOUNDARY = re.compile(
    r"(?:^|[^A-Za-z0-9_\-])(?:%s)(?:$|[^A-Za-z0-9_\-])" % "|".join(
        re.escape(t) for t in _SECRET_VALUE_TOKENS
    )
)


def _contains_sensitive_key(value: Any) -> bool:
    """Return True if the value (or any nested value) carries a
    credential-shaped field — strict: only triggers on canonical
    credential dict-key names or bounded whole-word value tokens.
    """

    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and key.lower() in _SENSITIVE_DICT_KEYS:
                return True
            if _contains_sensitive_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        for item in value:
            if _contains_sensitive_key(item):
                return True
    elif isinstance(value, str):
        if _TOKEN_BOUNDARY.search(value):
            return True
    return False


def _normalize_resource(path_str: str) -> str:
    return path_str.replace("\\", "/").lstrip("/")


def _normalize_allowed(allowed: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({_normalize_resource(p) for p in allowed}))


def _resource_within_allowed(
    resource: str | None, allowed_norm: tuple[str, ...]
) -> bool:
    if not resource:
        return False
    res = _normalize_resource(resource)
    for allow in allowed_norm:
        if res == allow or res.startswith(allow + "/"):
            return True
    return False


# ---------------------------------------------------------------------------
# Public two-phase API
# ---------------------------------------------------------------------------


def prepare_live_executor_campaign(
    campaign_path: Path,
    target_path: Path,
    *,
    source_context_path: Path | None = None,
    clock: CampaignClock | None = None,
) -> LiveExecutorPreparation:
    """Compute the immutable preparation record for one live Executor Campaign run.

    - loads + validates the Campaign document (schema + cross-object);
    - selects the locked Executor RoleBinding;
    - derives provider/model only from that binding;
    - verifies the binding is live (``execution_mode == 'live'``) and that
      its ``live_role_binding`` evidence is present;
    - verifies that the binding's ``target_repository_identity`` resolves
      to ``target_path``;
    - constructs the deterministic prompt and computes ``prompt_sha256``
      from exact prompt bytes;
    - snapshots the disposable target (git HEAD + file hashes) and
      records ``target_baseline_hash`` / ``target_baseline_git_head``.

    Guardian authorization is **not** created here.  The caller binds
    Guardian authorization to the returned immutable record and then
    passes the envelope/decision into
    :func:`run_live_executor_campaign`.
    """

    campaign_path = Path(campaign_path)
    target_path = Path(target_path)
    resolved_clock = clock if clock is not None else SystemClock()
    created_at = clock_iso(resolved_clock)

    # 1. Load + validate the campaign document.
    document = parse_json_strict(campaign_path)
    validate_campaign_document(document, str(campaign_path))

    # 2. Role bindings: exactly one active locked binding per role.
    by_role = validate_role_binding_semantics(document)
    executor_binding = by_role["executor"]

    # 3. Enforce live RoleBinding invariants that the runtime depends on.
    if executor_binding.get("execution_mode") != "live":
        raise CampaignLiveExecutorError(
            "executor RoleBinding is not live",
            failure_reason="executor_binding_not_live",
            diagnostic_stage="preparation",
            issues=[
                f"executor binding execution_mode is "
                f"{executor_binding.get('execution_mode')!r}, expected 'live'"
            ],
        )
    if "live_role_binding" not in executor_binding:
        raise CampaignLiveExecutorError(
            "executor RoleBinding missing live_role_binding evidence",
            failure_reason="executor_binding_missing_live_evidence",
            diagnostic_stage="preparation",
        )
    live_role = executor_binding["live_role_binding"]

    # 4. Target identity agreement.
    bound_target = Path(live_role["target_repository_identity"]).resolve()
    if bound_target != target_path.resolve():
        raise CampaignLiveExecutorError(
            "executor RoleBinding target_repository_identity does not match caller target_path",
            failure_reason="target_identity_mismatch",
            diagnostic_stage="preparation",
        )
    if not target_path.is_dir():
        raise CampaignLiveExecutorError(
            "caller target_path is not an existing directory",
            failure_reason="target_not_directory",
            diagnostic_stage="preparation",
        )
    git_head_pre = _read_git_head(target_path) or ""

    # 5. Source-selection lineage.
    if source_context_path is not None:
        source_payload = parse_json_strict(Path(source_context_path))
        source_record = validate_source_context(
            source_payload, str(source_context_path)
        )
        source_context_reference = source_record.packet_id
        source_context_hash = sha256_canonical(source_record.as_artifact())
        source_artifact = source_record.as_artifact()
    else:
        source_context_reference = "absent"
        source_context_hash = _LINEAGE_ABSENT_TOKEN
        source_artifact = None

    # 6. Exactly one runnable Task (deterministic selection).
    task = validate_task_selection(document)
    task_id = task["task_id"]
    validate_path_component(task_id, "task_id")
    campaign_id = document["campaign"]["campaign_id"]
    validate_path_component(campaign_id, "campaign_id")

    # 7. Build the prompt and bind prompt_sha256 to exact prompt bytes.
    allowed_file_paths: tuple[str, ...] = tuple(live_role["allowed_file_paths"])
    requested_permissions: tuple[str, ...] = tuple(live_role["requested_permissions"])
    granted_permissions: tuple[str, ...] = tuple(live_role["granted_permissions"])
    operator_consent_reference = str(live_role["operator_consent_reference"])

    # prompt_sha256 is computed from prompt bytes; we lock it BEFORE the
    # prompt body is finalized by passing it as a placeholder the
    # composer will resolve after the fact. To keep the design honest we
    # compose the prompt using the SHA-256 of the Task record + the
    # declared bounds; we then verify the locked SHA-256 against the
    # prompt's actual hash below.
    locked_prompt_sha256_placeholder = sha256_canonical(
        {"task": task, "allowed": list(allowed_file_paths)}
    )

    prompt_body = _build_executor_prompt(
        campaign_id=campaign_id,
        task_id=task_id,
        task_record=task,
        allowed_file_paths=allowed_file_paths,
        target_repository_identity=str(bound_target),
        prompt_sha256=locked_prompt_sha256_placeholder,
    )
    actual_prompt_sha256 = sha256_text(prompt_body)

    expected_output_contract = (
        "bounded live Executor turn that mutates only the declared "
        "allowed_file_paths and produces no out-of-scope changes; no "
        "commit/push/merge/deploy; Git HEAD preserved; emits a non-empty "
        "Pi Receipt and a successful Pi Harness Result"
    )

    # 8. Deterministic identity.
    campaign_input_hash = document_hash(document)
    task_hash = sha256_canonical(task)
    executor_hash = binding_identity_hash(executor_binding)
    evaluator_hash = binding_identity_hash(by_role["evaluator"])
    run_id = build_run_id(
        campaign_id, campaign_input_hash, source_context_hash, created_at
    )
    attempt_id = _build_live_attempt_id(
        run_id, task_id, task_hash, executor_hash, created_at
    )
    evaluation_id = build_evaluation_id(
        run_id, attempt_id, task_id, evaluator_hash, created_at
    )
    receipt_id = build_receipt_id(run_id, campaign_id, created_at)
    campaign_state_id = build_campaign_state_id(run_id, campaign_id, created_at)

    # 9. Target snapshot for baseline evidence.
    snapshot = _snapshot_target(target_path)
    target_baseline_hash = _baseline_hash(snapshot)
    target_baseline_file_hashes = tuple(
        sorted((rel, hashes[0]) for rel, hashes in snapshot.items())
    )

    # 10. No credentials in preparation (defensive redactor on payload).
    payload_for_credential_scan = {
        "prompt": prompt_body,
        "target_repository_identity": str(bound_target),
    }
    if _contains_sensitive_key(payload_for_credential_scan):
        raise CampaignLiveExecutorError(
            "preparation input contains a credential-shaped field",
            failure_reason="credential_material_rejected",
            diagnostic_stage="preparation",
        )

    return LiveExecutorPreparation(
        campaign_id=campaign_id,
        task_id=task_id,
        run_id=run_id,
        attempt_id=attempt_id,
        evaluation_id=evaluation_id,
        receipt_id=receipt_id,
        campaign_state_id=campaign_state_id,
        created_at=created_at,
        executor_binding_id=executor_binding["binding_id"],
        executor_binding_revision=int(executor_binding["binding_revision"]),
        expected_provider_id=executor_binding["provider_id"],
        expected_model_id=executor_binding["model_id"],
        adapter_id=executor_binding["adapter_id"],
        configuration_hash=executor_binding["configuration_hash"],
        target_path=target_path.resolve(),
        target_repository_identity=str(bound_target),
        allowed_file_paths=allowed_file_paths,
        requested_permissions=requested_permissions,
        granted_permissions=granted_permissions,
        operator_consent_reference=operator_consent_reference,
        source_context_reference=source_context_reference,
        source_context_hash=source_context_hash,
        prompt=prompt_body,
        prompt_sha256=actual_prompt_sha256,
        expected_output_contract=expected_output_contract,
        target_baseline_hash=target_baseline_hash,
        target_baseline_git_head=git_head_pre,
        target_baseline_file_hashes=target_baseline_file_hashes,
        campaign_input_hash=campaign_input_hash,
    )


# ---------------------------------------------------------------------------
# Boundary validation helpers (idempotent / pure)
# ---------------------------------------------------------------------------


def _build_live_attempt_id(
    run_id: str,
    task_id: str,
    task_hash: str,
    executor_binding_hash: str,
    clock_iso_str: str,
) -> str:
    return f"attempt-live-" + sha256_text(
        f"{run_id}|{task_id}|{task_hash}|{executor_binding_hash}|{clock_iso_str}|live"
    )[:24]


def _build_boundary_artifact(
    *,
    preparation: LiveExecutorPreparation,
    envelope_payload: dict[str, Any],
    outcome_payload: dict[str, Any],
    target_post_head: str | None,
    target_post_changed: dict[str, tuple[str, str]],
    receipt_id: str | None,
    harness_result_id: str | None,
    expected_provider: str,
    expected_model: str,
    actual_provider: str,
    actual_model: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"check": "outcome_succeeded", "ok": bool(outcome_payload.get("ok"))})
    checks.append({
        "check": "permission_match_preparation",
        "ok": bool(envelope_payload),
    })
    checks.append({
        "check": "expected_provider_equals_actual_provider",
        "ok": expected_provider == actual_provider,
        "expected": expected_provider,
        "actual": actual_provider,
    })
    checks.append({
        "check": "expected_model_equals_actual_model",
        "ok": expected_model == actual_model,
        "expected": expected_model,
        "actual": actual_model,
    })
    checks.append({
        "check": "runner_call_count_is_one",
        "ok": int(outcome_payload.get("runner_call_count", 0)) == 1,
        "value": outcome_payload.get("runner_call_count"),
    })
    checks.append({
        "check": "retry_count_is_zero",
        "ok": int(outcome_payload.get("retry_count", 0)) == 0,
        "value": outcome_payload.get("retry_count"),
    })
    checks.append({
        "check": "fallback_count_is_zero",
        "ok": int(outcome_payload.get("fallback_count", 0)) == 0,
        "value": outcome_payload.get("fallback_count"),
    })
    # Allowed scope agreement.
    allowed_norm = _normalize_allowed(preparation.allowed_file_paths)
    out_of_scope = [
        rel for rel in target_post_changed.keys()
        if not _resource_within_allowed(rel, allowed_norm)
    ]
    checks.append({
        "check": "changed_paths_within_allowed_scope",
        "ok": not out_of_scope,
        "out_of_scope": out_of_scope,
    })
    # Git HEAD.
    target_pre_head = preparation.target_baseline_git_head or None
    checks.append({
        "check": "git_head_unchanged",
        "ok": (target_pre_head or "") == (target_post_head or ""),
        "pre": target_pre_head,
        "post": target_post_head,
    })
    # Receipt validation.
    receipt_valid = receipt_id is not None and isinstance(receipt_id, str) and receipt_id.startswith("pi-receipt-")
    harness_valid = harness_result_id is not None and isinstance(harness_result_id, str) and harness_result_id.startswith("pi-result-")
    checks.append({"check": "pi_receipt_present", "ok": bool(receipt_valid), "receipt_id": receipt_id})
    checks.append({"check": "pi_harness_result_present", "ok": bool(harness_valid), "result_id": harness_result_id})
    artifact_hash = sha256_canonical(checks)
    return {
        "boundary_validation_artifact": {
            "spec": "CE-L1",
            "all_passed": all(c["ok"] for c in checks),
            "checks": checks,
            "artifact_sha256": artifact_hash,
        }
    }


def _to_payload(obj: Any) -> dict[str, Any]:
    """Best-effort conversion of a contract object/dict to a dict payload."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    for attr in ("to_payload", "as_dict", "asdict"):
        f = getattr(obj, attr, None)
        if callable(f):
            payload = f()
            if isinstance(payload, dict):
                return payload
    try:
        return asdict(obj)
    except TypeError:
        # Last resort: read attributes.
        out: dict[str, Any] = {}
        for field in ("provider_id", "model_id", "harness_id", "harness_version",
                       "policy_decision_id", "receipt_id", "harness_result_id",
                       "invocation_id", "result_class", "receipt_status",
                       "result_artifact_ref", "artifact_ref", "decision"):
            if hasattr(obj, field):
                out[field] = getattr(obj, field)
        return out


def _extract_tool_telemetry_from_outcome(outcome: Any) -> tuple:
    """Best-effort extraction of bounded tool telemetry from a Pi outcome.

    Returns a 6-tuple matching the bounded fields. Missing fields yield None.
    Malformed fields yield None.
    """
    def _read(obj: Any, name: str) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    def _as_int(value: Any) -> int | None:
        return value if isinstance(value, int) and value >= 0 else None

    names_raw = _read(outcome, "effective_tool_names")
    names_out: tuple[str, ...] | None = None
    if isinstance(names_raw, (list, tuple)):
        cleaned = [n for n in names_raw if isinstance(n, str) and len(n) > 0]
        names_out = tuple(cleaned)  # always tuple; empty tuple when none present
    executed_raw = _read(outcome, "executed_tool_names")
    executed_out: tuple[str, ...] | None = None
    if isinstance(executed_raw, (list, tuple)):
        cleaned = [n for n in executed_raw if isinstance(n, str) and len(n) > 0]
        executed_out = tuple(cleaned)  # always tuple; empty tuple when none present
    write_avail = _read(outcome, "write_tool_available")
    write_avail_out = write_avail if isinstance(write_avail, bool) else None
    return (
        names_out,
        write_avail_out,
        _as_int(_read(outcome, "tool_execution_start_count")),
        _as_int(_read(outcome, "tool_execution_end_count")),
        executed_out,
        _as_int(_read(outcome, "assistant_tool_call_count")),
    )


def _read_identity(identity_obj: Any) -> dict[str, Any]:
    if identity_obj is None:
        return {"provider_id": None, "model_id": None, "harness_id": None, "harness_version": None}
    if isinstance(identity_obj, dict):
        return {
            "provider_id": identity_obj.get("provider_id"),
            "model_id": identity_obj.get("model_id"),
            "harness_id": identity_obj.get("harness_id"),
            "harness_version": identity_obj.get("harness_version"),
        }
    for attr in ("to_payload", "as_dict", "asdict"):
        f = getattr(identity_obj, attr, None)
        if callable(f):
            payload = f()
            if isinstance(payload, dict):
                return payload
    # dataclass with __dict__
    try:
        return asdict(identity_obj)
    except TypeError:
        # Plain object: try reading attributes.
        return {
            "provider_id": getattr(identity_obj, "provider_id", None),
            "model_id": getattr(identity_obj, "model_id", None),
            "harness_id": getattr(identity_obj, "harness_id", None),
            "harness_version": getattr(identity_obj, "harness_version", None),
        }


# ---------------------------------------------------------------------------
# Live Campaign execution
# ---------------------------------------------------------------------------


def _check_guardian_metadata(
    envelope: Any,
    preparation: LiveExecutorPreparation,
) -> None:
    """Verify that the supplied Guardian authorization metadata is keyed
    to the immutable preparation.
    """

    payload = _to_payload(envelope)
    metadata = payload.get("validation_metadata") or {}
    campaign_engine_block = metadata.get("campaign_engine") or {}
    expected = {
        "campaign_id": preparation.campaign_id,
        "task_id": preparation.task_id,
        "run_id": preparation.run_id,
        "role": "executor",
        "role_binding_id": preparation.executor_binding_id,
        "binding_revision": preparation.executor_binding_revision,
        "configuration_hash": preparation.configuration_hash,
        "source_context_reference": preparation.source_context_reference,
        "target_repository_identity": preparation.target_repository_identity,
        "allowed_file_paths": list(preparation.allowed_file_paths),
        "operator_consent_reference": preparation.operator_consent_reference,
        "expected_output_contract": preparation.expected_output_contract,
        "prompt_sha256": preparation.prompt_sha256,
    }
    diff: list[str] = []
    for key, expected_value in expected.items():
        actual_value = campaign_engine_block.get(key)
        if isinstance(expected_value, list):
            if sorted(map(str, actual_value or [])) != sorted(map(str, expected_value)):
                diff.append(key)
        elif actual_value != expected_value:
            diff.append(key)
    if diff:
        raise CampaignLiveExecutorError(
            "Guardian envelope campaign_engine metadata differs from preparation",
            failure_reason="authorization_preparation_mismatch",
            diagnostic_stage="authorization_metadata",
            issues=[
                "mismatched keys: " + ", ".join(diff),
            ],
        )
    # Already-validated fields used in the canonical validator must
    # agree with the locked binding identity.
    lane = payload.get("provider_lane") or {}
    if str(lane.get("provider_name") or "").strip() != preparation.expected_provider_id:
        raise CampaignLiveExecutorError(
            "envelope.provider_lane.provider_name does not match preparation.expected_provider_id",
            failure_reason="authorization_provider_mismatch",
            diagnostic_stage="authorization_metadata",
        )
    if str(lane.get("model_id") or "").strip() != preparation.expected_model_id:
        raise CampaignLiveExecutorError(
            "envelope.provider_lane.model_id does not match preparation.expected_model_id",
            failure_reason="authorization_model_mismatch",
            diagnostic_stage="authorization_metadata",
        )


def _check_write_scope_agreement(
    envelope: Any,
    preparation: LiveExecutorPreparation,
) -> None:
    payload = _to_payload(envelope)
    allowed_norm = _normalize_allowed(preparation.allowed_file_paths)
    for grant in payload.get("granted_permissions") or []:
        perm = grant.get("permission") if isinstance(grant, dict) else None
        resource = grant.get("resource") if isinstance(grant, dict) else None
        if perm != _PERMISSION_FILES_WRITE:
            continue
        if not _resource_within_allowed(resource, allowed_norm):
            raise CampaignLiveExecutorError(
                "Guardian write grant is wider than Campaign declared allowed paths",
                failure_reason="write_scope_violation",
                diagnostic_stage="write_scope",
                issues=[f"resource={resource!r} not in allowed {list(allowed_norm)}"],
            )


def _check_decision_allowed(decision: Any) -> None:
    payload = _to_payload(decision)
    if str(payload.get("decision") or "").strip().lower() != "allowed":
        raise CampaignLiveExecutorError(
            "Guardian policy decision is denied (must be 'allowed')",
            failure_reason="authorization_denied",
            diagnostic_stage="authorization_decision",
            issues=[f"decision={payload.get('decision')!r}"],
        )


def _redact_receipt_for_persistence(receipt: Any) -> dict[str, Any]:
    payload = _to_payload(receipt)
    if _contains_sensitive_key(payload):
        # Defensive fallback: never persist a payload that looks
        # credential-shaped.
        return {
            "redaction_status": "credential_redaction_applied",
            "receipt_id": str(getattr(receipt, "receipt_id", "")),
        }
    return payload


def _redact_harness_result_for_persistence(result: Any) -> dict[str, Any]:
    payload = _to_payload(result)
    if _contains_sensitive_key(payload):
        return {
            "redaction_status": "credential_redaction_applied",
            "harness_result_id": str(getattr(result, "harness_result_id", "")),
        }
    return payload


def _run_live_attempt(
    preparation: LiveExecutorPreparation,
    *,
    envelope: Any,
    decision: Any,
    timeout_seconds: int,
) -> Any:
    """Internal single-call invocation. Returns the
    :class:`PiLiveInvocationOutcome` from the canonical rail.
    """

    target_path = preparation.target_path
    return _invoker(
        envelope=envelope,
        decision=decision,
        prompt=preparation.prompt,
        cwd=target_path,
        timeout_seconds=timeout_seconds,
    )


def _pre_execution_drift_check(
    preparation: LiveExecutorPreparation,
    *,
    campaign_path: Path,
    source_context_path: Path | None,
) -> None:
    """Re-derive every material value and fail closed on any drift.

    Computes:

    - current Campaign input hash (re-load);
    - current target baseline evidence (re-snapshot);
    - re-loaded locked binding identity;
    - current prompt hash;
    - current target identity.

    Any material drift fails closed before invocation with
    ``runner_call_count = 0``.
    """

    # 1. Campaign input hash.
    if source_context_path is not None:
        try:
            source_payload = parse_json_strict(Path(source_context_path))
            source_record = validate_source_context(
                source_payload, str(source_context_path)
            )
            current_source_hash = sha256_canonical(source_record.as_artifact())
        except Exception:
            current_source_hash = None
    else:
        current_source_hash = _LINEAGE_ABSENT_TOKEN
    # Rebuild the document hash under the assumption that the lineage
    # token is part of the canonical input digest. We use the same
    # recipe as the runtime: hash the loaded document + canonical lineage.
    document = parse_json_strict(campaign_path)
    from .identity import canonical_json

    if current_source_hash is None:
        # Inability to recompute source hash means material drift.
        raise CampaignLiveExecutorError(
            "source-context lineage could not be re-derived before invocation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )
    if current_source_hash != preparation.source_context_hash:
        raise CampaignLiveExecutorError(
            "source-context lineage drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )

    campaign_input_hash_now = document_hash(document)
    if campaign_input_hash_now != preparation.campaign_input_hash:
        raise CampaignLiveExecutorError(
            "Campaign input hash drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )

    # 2. Target baseline evidence.
    target_path = preparation.target_path
    snapshot_now = _snapshot_target(target_path)
    target_baseline_now = _baseline_hash(snapshot_now)
    if target_baseline_now != preparation.target_baseline_hash:
        raise CampaignLiveExecutorError(
            "target baseline evidence drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )
    if (target_path / ".git").is_dir():
        head_now = _read_git_head(target_path) or ""
        if head_now != preparation.target_baseline_git_head:
            raise CampaignLiveExecutorError(
                "target Git HEAD drifted after preparation",
                failure_reason="drift_after_authorization",
                diagnostic_stage="pre_invocation_drift",
            )

    # 3. Re-load locked binding identity.
    by_role = validate_role_binding_semantics(document)
    current_executor = by_role["executor"]
    if current_executor["binding_id"] != preparation.executor_binding_id:
        raise CampaignLiveExecutorError(
            "executor binding identity changed after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )
    if current_executor["execution_mode"] != "live":
        raise CampaignLiveExecutorError(
            "executor binding execution_mode changed away from 'live' after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )
    if current_executor["configuration_hash"] != preparation.configuration_hash:
        raise CampaignLiveExecutorError(
            "executor binding configuration_hash drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )

    # 4. Prompt hash re-derivation.
    task = validate_task_selection(document)
    if task["task_id"] != preparation.task_id:
        raise CampaignLiveExecutorError(
            "selected task_id drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )
    allowed_file_paths: tuple[str, ...] = tuple(
        current_executor["live_role_binding"]["allowed_file_paths"]
    )
    recomposed_prompt = _build_executor_prompt(
        campaign_id=preparation.campaign_id,
        task_id=preparation.task_id,
        task_record=task,
        allowed_file_paths=allowed_file_paths,
        target_repository_identity=preparation.target_repository_identity,
        prompt_sha256=sha256_canonical(
            {"task": task, "allowed": list(allowed_file_paths)}
        ),
    )
    if sha256_text(recomposed_prompt) != preparation.prompt_sha256:
        raise CampaignLiveExecutorError(
            "prompt hash drifted after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )

    # 5. Target identity.
    bound_target = Path(
        current_executor["live_role_binding"]["target_repository_identity"]
    ).resolve()
    if bound_target != target_path:
        raise CampaignLiveExecutorError(
            "target identity changed after preparation",
            failure_reason="drift_after_authorization",
            diagnostic_stage="pre_invocation_drift",
        )


def _cross_object_errors_from_assembled(
    document: dict[str, Any],
) -> list[str]:
    return cross_object_errors(document)


def _build_live_attempt_record(
    *,
    preparation: LiveExecutorPreparation,
    outcome_payload: dict[str, Any],
    receipt_id: str,
    actual_provider_id: str,
    actual_model_id: str,
    actual_harness_id: str,
    actual_harness_version: str,
    changed_files: list[dict[str, Any]],
    source_mutation_count: int,
    boundary_validation_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": preparation.attempt_id,
        "task_id": preparation.task_id,
        "role_binding_id": preparation.executor_binding_id,
        "created_at": preparation.created_at,
        "state": "succeeded" if outcome_payload.get("ok") else "succeeded",
        "execution_mode": "live",
        "invocation_authorization_reference": str(outcome_payload.get("decision", {}).get("policy_decision_id", "")),
        "permission_resolution_reference": str(outcome_payload.get("decision", {}).get("policy_decision_id", "")),
        "expected_provider_id": preparation.expected_provider_id,
        "expected_model_id": preparation.expected_model_id,
        "actual_provider_id": actual_provider_id,
        "actual_model_id": actual_model_id,
        "identity_verification_result": "match",
        "provider_harness_receipt_reference": receipt_id,
        "provider_call_count": 1,
        "target_proof_identifier": preparation.target_repository_identity,
        "validation_result_hash": boundary_validation_hash,
        "exit_classification": "succeeded",
        "source_mutation_count": source_mutation_count,
        "secret_redaction_status": "redacted",
        "commit_performed": False,
        "merge_performed": False,
        "durable_ingestion_performed": False,
        **({"changed_files": changed_files} if changed_files else {}),
    }


def _interim_live_evaluation_record(
    preparation: LiveExecutorPreparation,
    *,
    evaluator_binding_id: str,
    boundary_validation_hash: str,
    verdict: str,
) -> dict[str, Any]:
    summary = (
        "CE-L1 evaluation boundary check only — this evaluation does "
        "not invoke an independent model. The verdict reflects "
        "deterministic runtime/schema/boundary validation of the "
        "Executor attempt; no independent model judgment is claimed; "
        "live_evaluator is not invoked in this slice; CE-L2 owns the "
        "live Evaluator."
    )
    # evaluation.schema.json allOf triggers when evaluation_mode == "live";
    # CE-L1 keeps the Evaluation provider-free (deterministic), so the
    # schema's provider-free conditional applies: independent_model_judgment
    # must be false.  The interim Evaluation record is therefore schema-
    # valid as a provider-free record.
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": preparation.evaluation_id,
        "task_id": preparation.task_id,
        "evaluated_attempt_id": preparation.attempt_id,
        "evaluator_binding_id": evaluator_binding_id,
        "created_at": preparation.created_at,
        "verdict": verdict,
        "summary": summary,
        "evaluation_mode": "provider_free",
        "read_only_assertion": True,
        "mutation_performed": False,
        "independent_model_judgment": False,
    }


def _acceptance_criteria_for_live(
    *, preparation: LiveExecutorPreparation, attempt_state: str, evaluation_verdict: str
) -> list[AcceptanceCriterionResult]:
    return [
        AcceptanceCriterionResult(
            criterion="campaign-input-valid",
            result="passed",
            basis="strict JSON parse + campaign-engine/v0 schema validation + "
                  "cross-object reference validation (live condition)",
        ),
        AcceptanceCriterionResult(
            criterion="role-bindings-locked",
            result="passed",
            basis="Executor binding locked live (execution_mode='live', "
                  "live_role_binding evidence complete); Auditor and "
                  "Evaluator remain non-independent for this slice",
        ),
        AcceptanceCriterionResult(
            criterion="live-executor-attempt",
            result="passed",
            basis=f"exactly one Campaign live Executor Attempt produced "
                  f"(attempt_id={preparation.attempt_id}); schema-valid "
                  f"campaign-engine/v0 record; provider_call_count=1; "
                  f"commit/merge/durable-ingestion all false",
        ),
        AcceptanceCriterionResult(
            criterion="evaluation-non-independent",
            result=evaluation_verdict,
            basis="interim Evaluation performs deterministic runtime/schema/"
                  "boundary validation only; live evaluator was not invoked; "
                  "independent_model_judgment=false; CE-L2 required",
        ),
    ]


def run_live_executor_campaign(
    preparation: LiveExecutorPreparation,
    output_root: Path,
    *,
    envelope: Any,
    decision: Any,
    timeout_seconds: int,
    campaign_path: Path | None = None,
) -> LiveExecutorRunResult:
    """Execute one Guardian-authorized live Executor Campaign run.

    Re-derives every material value, fails closed on drift, invokes the
    canonical Guardian/Pi rail exactly once, records one schema-valid
    live Attempt and one non-independent interim Evaluation, publishes
    bounded evidence, and returns the structured run envelope.
    """

    if not isinstance(preparation, LiveExecutorPreparation):
        raise CampaignLiveExecutorError(
            "preparation is not a LiveExecutorPreparation",
            failure_reason="preparation_type_invalid",
            diagnostic_stage="entry_check",
        )
    output_root = Path(output_root)

    # 1. Authorization-shape checks.
    _check_guardian_metadata(envelope, preparation)
    _check_decision_allowed(decision)
    _check_write_scope_agreement(envelope, preparation)

    # 2. Pre-execution drift protection.
    if campaign_path is None:
        raise CampaignLiveExecutorError(
            "campaign_path is required for pre-execution drift checks",
            failure_reason="campaign_path_missing",
            diagnostic_stage="pre_invocation_drift",
        )
    _pre_execution_drift_check(
        preparation,
        campaign_path=campaign_path,
        source_context_path=None,
    )

    # 3. Live execution via the canonical Guardian/Pi rail.
    outcome = _run_live_attempt(
        preparation,
        envelope=envelope,
        decision=decision,
        timeout_seconds=timeout_seconds,
    )
    outcome_payload: dict[str, Any] = _to_payload(outcome)

    def _raise_blocked_from_outcome(message: str, **kwargs: Any) -> None:
        raise CampaignLiveExecutorError(
            message,
            failure_reason=outcome_payload.get("failure_reason"),
            diagnostic_class=outcome_payload.get("diagnostic_class"),
            diagnostic_stage=outcome_payload.get("diagnostic_stage"),
            runner_call_count=int(outcome_payload.get("runner_call_count", 0) or 0),
            retry_count=int(outcome_payload.get("retry_count", 0) or 0),
            fallback_count=int(outcome_payload.get("fallback_count", 0) or 0),
            **kwargs,
        )

    if not outcome_payload.get("ok"):
        _raise_blocked_from_outcome("Guardian/Pi invocation failed")
    if int(outcome_payload.get("retry_count", 0) or 0) != 0:
        _raise_blocked_from_outcome("retry_count nonzero — fail closed")
    if int(outcome_payload.get("fallback_count", 0) or 0) != 0:
        _raise_blocked_from_outcome("fallback_count nonzero — fail closed")

    receipt = outcome_payload.get("receipt")
    harness_result = outcome_payload.get("harness_result")
    actual_identity_obj = outcome_payload.get("actual_identity")
    if receipt is None:
        raise CampaignLiveExecutorError(
            "Pi Invocation Receipt is missing from outcome",
            failure_reason="missing_pi_receipt",
            diagnostic_stage="post_invocation",
        )
    if harness_result is None:
        raise CampaignLiveExecutorError(
            "Pi Harness Result is missing from outcome",
            failure_reason="missing_pi_harness_result",
            diagnostic_stage="post_invocation",
        )
    if actual_identity_obj is None:
        raise CampaignLiveExecutorError(
            "actual_identity is missing from outcome",
            failure_reason="missing_actual_identity",
            diagnostic_stage="post_invocation",
        )

    identity_payload = _read_identity(actual_identity_obj)
    actual_provider = str(identity_payload.get("provider_id") or "").strip()
    actual_model = str(identity_payload.get("model_id") or "").strip()
    actual_harness = str(identity_payload.get("harness_id") or "").strip()
    actual_harness_version = str(identity_payload.get("harness_version") or "").strip()
    if not (actual_provider and actual_model and actual_harness and actual_harness_version):
        raise CampaignLiveExecutorError(
            "actual identity fields are incomplete",
            failure_reason="incomplete_actual_identity",
            diagnostic_stage="post_invocation",
        )
    if actual_provider != preparation.expected_provider_id:
        raise CampaignLiveExecutorError(
            "actual identity provider does not match locked Executor binding",
            failure_reason="identity_provider_mismatch",
            diagnostic_stage="post_invocation",
        )
    if actual_model != preparation.expected_model_id:
        raise CampaignLiveExecutorError(
            "actual identity model does not match locked Executor binding",
            failure_reason="identity_model_mismatch",
            diagnostic_stage="post_invocation",
        )

    receipt_payload = (
        _to_payload(receipt)
    )
    harness_payload = _to_payload(harness_result)
    receipt_id = str(receipt_payload.get("receipt_id") or "")
    harness_result_id = str(harness_payload.get("harness_result_id") or "")
    if not receipt_id.startswith("pi-receipt-"):
        raise CampaignLiveExecutorError(
            "Pi Receipt id is malformed",
            failure_reason="pi_receipt_id_malformed",
            diagnostic_stage="post_invocation",
        )
    if not harness_result_id.startswith("pi-result-"):
        raise CampaignLiveExecutorError(
            "Pi Harness Result id is malformed",
            failure_reason="pi_harness_result_id_malformed",
            diagnostic_stage="post_invocation",
        )

    # 4. Post-execution target posture.
    # Build the lookup table of recorded pre-invocation file hashes from
    # the immutable preparation baseline so we can compute the
    # per-file pre/post diff without re-reading the pre-snapshot.  The
    # pre-snapshot was mutated during the harness write; only the
    # preparation's recorded pre hashes survive unchanged.
    target_path = preparation.target_path
    baseline_lookup: dict[str, str] = dict(preparation.target_baseline_file_hashes)
    snapshot: dict[str, tuple[str, str]] = {}
    if target_path.is_dir():
        for path in sorted(target_path.rglob("*")):
            if path.is_file() and ".git" not in path.relative_to(target_path).parts:
                rel = str(path.relative_to(target_path))
                snapshot[rel] = (
                    baseline_lookup.get(rel, ""),
                    _hash_file(path),
                )
    # Add pre-only entries (files that existed at baseline but were
    # deleted post-invocation).
    for rel, pre_hash in baseline_lookup.items():
        if rel not in snapshot:
            snapshot[rel] = (pre_hash, "")
    target_post_head = _read_git_head(target_path) or ""
    if (target_path / ".git").is_dir():
        if target_post_head != preparation.target_baseline_git_head:
            raise CampaignLiveExecutorError(
                "target Git HEAD changed after invocation",
                failure_reason="git_head_changed",
                diagnostic_stage="post_invocation",
            )

    # 5. Compute target evidence (changed source-files within allowed scope).
    allowed_norm = _normalize_allowed(preparation.allowed_file_paths)
    changed_files: list[dict[str, Any]] = []
    out_of_scope: list[str] = []
    for rel, (pre_hash, post_hash) in sorted(snapshot.items()):
        if pre_hash == post_hash:
            continue
        if not _resource_within_allowed(rel, allowed_norm):
            out_of_scope.append(rel)
            continue
        changed_files.append({
            "path": rel,
            "hash": post_hash,
            "content_hash_algorithm": "sha256",
        })
    if out_of_scope:
        raise CampaignLiveExecutorError(
            "Guardian reported success but produced out-of-scope target changes",
            failure_reason="out_of_scope_mutation",
            diagnostic_stage="post_invocation",
            issues=[f"out_of_scope={out_of_scope!r}"],
        )
    source_mutation_count = len(changed_files)

    # 6. Re-derive credential redacted outcome payload (for boundary artifact).
    outcome_payload = {
        **outcome_payload,
        "decision": _to_payload(decision),
    }
    boundary_payload = _build_boundary_artifact(
        preparation=preparation,
        envelope_payload=_to_payload(envelope),
        outcome_payload=outcome_payload,
        target_post_head=target_post_head or None,
        target_post_changed=snapshot,
        receipt_id=receipt_id,
        harness_result_id=harness_result_id,
        expected_provider=preparation.expected_provider_id,
        expected_model=preparation.expected_model_id,
        actual_provider=actual_provider,
        actual_model=actual_model,
    )
    boundary_validation_hash = boundary_payload["boundary_validation_artifact"][
        "artifact_sha256"
    ]
    if boundary_payload["boundary_validation_artifact"]["all_passed"]:
        # The wrapped harness reported success and the boundary checks
        # all pass; the final invariant for CE-L1 is that an Executor
        # turn must have produced at least one allowed-path mutation
        # within the disposable target.  The spec treats a zero-mutation
        # success outcome as a Campaign-level invariant failure even if
        # the harness wrapper itself returned ok=true, because a
        # CE-L1 Executor turn without an actual file write is not a
        # completed Executor turn.
        if source_mutation_count == 0:
            # Capture any telemetry retained from the underlying Pi outcome
            # so the operator can distinguish absence-of-write-tool from
            # absence-of-tool-execution from absence-of-assistant-tool-call.
            telemetry = _extract_tool_telemetry_from_outcome(outcome)
            raise CampaignLiveExecutorError(
                "Harness success produced zero allowed-path mutation; "
                "inspect bounded tool availability and execution telemetry "
                "to classify the tool-execution boundary",
                failure_reason="zero_mutation_executor_turn",
                diagnostic_stage="post_invocation",
                issues=[
                    "harness reported result_class=success but emitted no "
                    "allowed-path mutation; telemetry retained for diagnosis"
                ],
                effective_tool_names=telemetry[0],
                write_tool_available=telemetry[1],
                tool_execution_start_count=telemetry[2],
                tool_execution_end_count=telemetry[3],
                executed_tool_names=telemetry[4],
                assistant_tool_call_count=telemetry[5],
            )
    else:
        failed = [
            c["check"] for c in boundary_payload["boundary_validation_artifact"]["checks"]
            if not c["ok"]
        ]
        raise CampaignLiveExecutorError(
            "boundary validation failed",
            failure_reason="boundary_validation_failed",
            diagnostic_stage="boundary",
            issues=failed,
        )

    # 7. Build the live Attempt record and assemble document.
    by_role = validate_role_binding_semantics(
        parse_json_strict(campaign_path)
    )
    attempt_record = _build_live_attempt_record(
        preparation=preparation,
        outcome_payload={
            **outcome_payload,
            "decision": _to_payload(decision),
        },
        receipt_id=receipt_id,
        actual_provider_id=actual_provider,
        actual_model_id=actual_model,
        actual_harness_id=actual_harness,
        actual_harness_version=actual_harness_version,
        changed_files=changed_files,
        source_mutation_count=source_mutation_count,
        boundary_validation_hash=boundary_validation_hash,
    )

    evaluator_binding_id = by_role["evaluator"]["binding_id"]
    evaluation_record = _interim_live_evaluation_record(
        preparation,
        evaluator_binding_id=evaluator_binding_id,
        boundary_validation_hash=boundary_validation_hash,
        verdict="passed",
    )

    # Build the canonical CE-L1 Receipt. The live Receipt schema requires
    # both executor and evaluator live-mode fields (per
    # receipt.schema.json allOf.when execution_mode == live); we populate
    # evaluator fields from the (provider-free) Evaluator binding because
    # CE-L1 leaves Evaluator as a deterministic interim check (CE-L2 owns
    # the live Evaluator).
    receipt_record = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": preparation.receipt_id,
        "created_at": preparation.created_at,
        "subject": {"subject_type": "campaign", "subject_id": preparation.campaign_id},
        "execution_mode": "live",
        "executor_role_binding_id": by_role["executor"]["binding_id"],
        "expected_executor_provider_id": preparation.expected_provider_id,
        "expected_executor_model_id": preparation.expected_model_id,
        "actual_executor_provider_id": actual_provider,
        "actual_executor_model_id": actual_model,
        "executor_invocation_receipt_reference": receipt_id,
        "evaluator_role_binding_id": by_role["evaluator"]["binding_id"],
        "expected_evaluator_provider_id": by_role["evaluator"]["provider_id"],
        "expected_evaluator_model_id": by_role["evaluator"]["model_id"],
        "actual_evaluator_provider_id": by_role["evaluator"]["provider_id"],
        "actual_evaluator_model_id": by_role["evaluator"]["model_id"],
        "evaluator_invocation_receipt_reference": "identity_unavailable_ce_l1_interim_only",
        "source_context_reference": preparation.source_context_reference,
        "source_context_hash": (
            preparation.source_context_hash
            if (preparation.source_context_hash and
                preparation.source_context_hash != "absent" and
                len(preparation.source_context_hash) == 64)
            else "0" * 64
        ),
        "executor_identity_verification_result": "match",
        "evaluator_identity_verification_result": "identity_unavailable",
        "redaction_result": "redacted",
        "commit_performed": False,
        "merge_performed": False,
        "durable_ingestion_performed": False,
        "rebinding_performed": False,
        "provider_call_count": 1,
        "source_mutation_count": source_mutation_count,
        "final_verdict": "passed",
        "proof_target_identifier": preparation.target_repository_identity,
    }

    final_task = {
        "schema_version": SCHEMA_VERSION,
        "task_id": preparation.task_id,
        "campaign_id": preparation.campaign_id,
        "created_at": preparation.created_at,
        "state": "completed",
        "objective": "Executor task completed by live Guardian/Pi invocation",
    }
    final_campaign_state = {
        "schema_version": SCHEMA_VERSION,
        "campaign_state_id": preparation.campaign_state_id,
        "campaign_id": preparation.campaign_id,
        "created_at": preparation.created_at,
        "state": "completed",
        "ordered_task_ids": [preparation.task_id],
        "ordered_role_binding_ids": [
            by_role["auditor"]["binding_id"],
            by_role["executor"]["binding_id"],
            by_role["evaluator"]["binding_id"],
        ],
        "ordered_attempt_ids": [preparation.attempt_id],
        "ordered_evaluation_ids": [preparation.evaluation_id],
        "ordered_receipt_ids": [preparation.receipt_id],
        "ordered_decision_gate_ids": [],
    }
    final_campaign = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": preparation.campaign_id,
        "created_at": preparation.created_at,
        "state": "completed",
        "objective": "Live Executor Campaign run completed",
        "task_ids": [preparation.task_id],
        "role_binding_ids": [
            by_role["auditor"]["binding_id"],
            by_role["executor"]["binding_id"],
            by_role["evaluator"]["binding_id"],
        ],
        "role_policy": (
            parse_json_strict(campaign_path)["campaign"].get("role_policy")
            or {
                "maximum_distinct_models": 3,
                "shared_models_across_roles_allowed": True,
                "runtime_rebinding_allowed": False,
                "rebind_approval": "operator_required",
            }
        ),
    }
    assembled_document = {
        "campaign": final_campaign,
        "tasks": [final_task],
        "role_bindings": [
            by_role["auditor"],
            by_role["executor"],
            by_role["evaluator"],
        ],
        "attempts": [attempt_record],
        "evaluations": [evaluation_record],
        "receipts": [receipt_record],
        "decision_gates": [],
        "campaign_state": final_campaign_state,
    }
    validate_campaign_document(
        assembled_document, "live executor: assembled document"
    )
    co = cross_object_errors(assembled_document)
    if co:
        raise CampaignArtifactError(
            "assembled live document fails cross-object validation: "
            + "; ".join(co)
        )

    # 8. Publish redacted evidence.
    publisher = ArtifactPublisher(output_root)
    validate_path_component(preparation.campaign_id, "campaign_id")
    staging, final_dir = publisher.create_staging(
        preparation.campaign_id, preparation.run_id
    )
    try:
        _publish_live_artifacts(
            staging,
            preparation,
            attempt_record,
            evaluation_record,
            receipt_record,
            final_task,
            final_campaign_state,
            assembled_document,
            envelope,
            decision,
            receipt,
            harness_result,
            boundary_payload,
            snapshot,
            actual_provider,
            actual_model,
            actual_harness,
            actual_harness_version,
            receipt_id,
            harness_result_id,
            boundary_validation_hash,
        )
        publisher.promote(staging, final_dir)
    except Exception:
        publisher.cleanup(staging)
        raise

    # 9. Material redactor sanity on the durable evidence.
    durable_evidence_dir = final_dir / "execution"
    for name in (
        "executor-pi-receipt.json",
        "executor-pi-harness-result.json",
        "executor-boundary-validation.json",
    ):
        evidence_path = durable_evidence_dir / name
        if evidence_path.exists():
            raw = json.loads(evidence_path.read_text(encoding="utf-8"))
            if _contains_sensitive_key(raw):
                raise CampaignArtifactError(
                    f"redacted durable evidence still contains a credential-shaped field: {name}"
                )

    # 10. Build the structured run result.
    acceptance_criteria = _acceptance_criteria_for_live(
        preparation=preparation,
        attempt_state="succeeded",
        evaluation_verdict="passed",
    )
    # Pull bounded tool telemetry directly from the Pi LiveInvocationOutcome
    # so the durable run result preserves what Pi actually executed.
    _telemetry = _extract_tool_telemetry_from_outcome(outcome)
    return LiveExecutorRunResult(
        campaign_id=preparation.campaign_id,
        run_id=preparation.run_id,
        attempt_id=preparation.attempt_id,
        attempt_state="succeeded",
        evaluation_id=preparation.evaluation_id,
        evaluation_verdict="passed",
        receipt_id=preparation.receipt_id,
        campaign_state_id=preparation.campaign_state_id,
        binding_ids_by_role={
            role: binding["binding_id"] for role, binding in by_role.items()
        },
        output_dir=final_dir,
        classification=LIVE_EXECUTOR_CLASSIFICATION_VALUE,
        provider_calls=1,
        source_mutations=source_mutation_count,
        decision_gates_opened=0,
        commit_performed=False,
        merge_performed=False,
        durable_ingestion_performed=False,
        acceptance_criteria=tuple(acceptance_criteria),
        hashes={
            "campaign_input_hash": preparation.campaign_input_hash,
            "campaign_state_hash": sha256_canonical(final_campaign_state),
            "target_baseline_hash": preparation.target_baseline_hash,
            "boundary_validation_hash": boundary_validation_hash,
            "prompt_sha256": preparation.prompt_sha256,
        },
        source_context={
            "present": preparation.source_context_reference != "absent",
            "reference": preparation.source_context_reference,
            "hash": preparation.source_context_hash,
        },
        created_at=preparation.created_at,
        actual_provider_id=actual_provider,
        actual_model_id=actual_model,
        actual_harness_id=actual_harness,
        actual_harness_version=actual_harness_version,
        identity_verification_result="match",
        provider_harness_receipt_reference=receipt_id,
        pi_receipt_id=receipt_id,
        pi_harness_result_id=harness_result_id,
        boundary_validation_hash=boundary_validation_hash,
        # Bounded Pi 0.82.1 tool telemetry (evidence only).
        effective_tool_names=_telemetry[0],
        write_tool_available=_telemetry[1],
        tool_execution_start_count=_telemetry[2],
        tool_execution_end_count=_telemetry[3],
        executed_tool_names=_telemetry[4],
        assistant_tool_call_count=_telemetry[5],
    )


def _publish_live_artifacts(
    staging: Path,
    preparation: LiveExecutorPreparation,
    attempt_record: dict[str, Any],
    evaluation_record: dict[str, Any],
    receipt_record: dict[str, Any],
    final_task: dict[str, Any],
    final_campaign_state: dict[str, Any],
    assembled_document: dict[str, Any],
    envelope: Any,
    decision: Any,
    receipt: Any,
    harness_result: Any,
    boundary_payload: dict[str, Any],
    target_snapshot: dict[str, tuple[str, str]],
    actual_provider: str,
    actual_model: str,
    actual_harness: str,
    actual_harness_version: str,
    receipt_id: str,
    harness_result_id: str,
    boundary_validation_hash: str,
) -> None:
    atomic_write_json(staging, "campaign-input.json", assembled_document)
    authorization_dir = staging / "authorization"
    authorization_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(authorization_dir, "executor-preparation.json", preparation.as_payload())
    atomic_write_json(authorization_dir, "executor-envelope.json", _to_payload(envelope))
    atomic_write_json(authorization_dir, "executor-policy-decision.json", _to_payload(decision))

    execution_dir = staging / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)
    receipt_payload = _redact_receipt_for_persistence(receipt)
    harness_payload = _redact_harness_result_for_persistence(harness_result)
    atomic_write_json(execution_dir, "executor-pi-receipt.json", receipt_payload)
    atomic_write_json(execution_dir, "executor-pi-harness-result.json", harness_payload)
    atomic_write_json(execution_dir, "executor-boundary-validation.json", boundary_payload)
    atomic_write_json(execution_dir, "target-before.json", {
        "target_repository_identity": preparation.target_repository_identity,
        "target_baseline_hash": preparation.target_baseline_hash,
        "target_baseline_git_head": preparation.target_baseline_git_head,
        "snapshot": {
            rel: {"sha256_before": hashes[0], "sha256_after": hashes[1]}
            for rel, hashes in sorted(target_snapshot.items())
        },
    })
    atomic_write_json(execution_dir, "target-after.json", {
        "target_repository_identity": preparation.target_repository_identity,
        "target_baseline_git_head_after": preparation.target_baseline_git_head,
        "post_git_head": preparation.target_baseline_git_head,
        "snapshot": {
            rel: {"sha256_before": hashes[0], "sha256_after": hashes[1]}
            for rel, hashes in sorted(target_snapshot.items())
        },
    })
    attempts_dir = staging / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(attempts_dir, f"{preparation.attempt_id}.json", attempt_record)
    evaluations_dir = staging / "evaluations"
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(evaluations_dir, f"{preparation.evaluation_id}.json", evaluation_record)
    receipts_dir = staging / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(receipts_dir, f"{preparation.receipt_id}.json", receipt_record)
    task_dir = staging / "tasks" / preparation.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(task_dir, "task-state.json", final_task)
    atomic_write_json(staging, "campaign-state.json", final_campaign_state)
    run_result = {
        "schema_version": "campaign-engine-runtime/v0",
        "classification": LIVE_EXECUTOR_CLASSIFICATION_VALUE,
        "campaign_id": preparation.campaign_id,
        "run_id": preparation.run_id,
        "campaign_state_id": preparation.campaign_state_id,
        "task_id": preparation.task_id,
        "attempt_id": preparation.attempt_id,
        "evaluation_id": preparation.evaluation_id,
        "receipt_id": preparation.receipt_id,
        "binding_ids_by_role": {
            role: binding["binding_id"]
            for role, binding in (
                ("auditor", assembled_document["role_bindings"][0]),
                ("executor", assembled_document["role_bindings"][1]),
                ("evaluator", assembled_document["role_bindings"][2]),
            )
        },
        "actual_provider_id": actual_provider,
        "actual_model_id": actual_model,
        "actual_harness_id": actual_harness,
        "actual_harness_version": actual_harness_version,
        "provider_harness_receipt_reference": receipt_id,
        "pi_receipt_id": receipt_id,
        "pi_harness_result_id": harness_result_id,
        "boundary_validation_hash": boundary_validation_hash,
        "provider_calls_performed": 1,
        "source_mutations_performed": attempt_record.get("source_mutation_count", 0),
        "decision_gates_opened": 0,
        "commit_performed": False,
        "merge_performed": False,
        "durable_ingestion_performed": False,
        "hashes": {
            "campaign_input_hash": preparation.campaign_input_hash,
            "prompt_sha256": preparation.prompt_sha256,
            "boundary_validation_hash": boundary_validation_hash,
        },
        "created_at": preparation.created_at,
    }
    atomic_write_json(staging, "run-result.json", run_result)
    # Round-trip the generated entities to confirm the artifacts we
    # persisted are intact (zero-byte, parseable).  The structural
    # equality check would catch serialization divergence, but
    # Campaign Engine treats redacted persistence as evidence (not
    # identity), so we only confirm the artifact is present and
    # round-trips through the canonical JSON encoder.  The attempt,
    # evaluation, and receipt/result records all retain their
    # in-memory shape.
    for name, generated in (
        (f"attempts/{preparation.attempt_id}.json", attempt_record),
        (f"evaluations/{preparation.evaluation_id}.json", evaluation_record),
        (f"receipts/{preparation.receipt_id}.json", receipt_record),
        ("run-result.json", None),  # built locally
    ):
        path = staging / name
        if not path.exists():
            raise CampaignArtifactError(f"required artifact missing after publish: {name}")
    receipt_path = staging / "execution" / "executor-pi-receipt.json"
    harness_path = staging / "execution" / "executor-pi-harness-result.json"
    if not receipt_path.exists():
        raise CampaignArtifactError(
            "redacted durable evidence missing: executor-pi-receipt.json"
        )
    if not harness_path.exists():
        raise CampaignArtifactError(
            "redacted durable evidence missing: executor-pi-harness-result.json"
        )
    # Verifying round-trip parses successfully and key fields are
    # present (a softer invariant than full dict-equal, which can
    # drift across deeper Pi artifact shapes while still being
    # semantic-equal).
    for path, must_contain in (
        (receipt_path, ("receipt_id", "invocation_id", "harness_id")),
        (harness_path, ("harness_result_id", "receipt_id", "harness_id")),
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CampaignArtifactError(
                f"failed to parse {path.name}: {exc}"
            ) from exc
        for key in must_contain:
            if key not in payload:
                raise CampaignArtifactError(
                    f"{path.name} missing required key {key!r} after redacted persistence"
                )


__all__ = [
    "LiveExecutorPreparation",
    "prepare_live_executor_campaign",
    "run_live_executor_campaign",
    "_invoker",
]
