"""Guardian-side execution binding authority for delegated coding tasks.

The Guardian Delegation Loop needs an execution binding before anything can be
dispatched to a coding worker. This module resolves one binding from *trusted
account, project, and workspace context* — never from a caller-supplied
provider/model/credential dictionary.

Design rules, in order of priority:

1. **Guardian resolves; the caller proposes.** A request may *narrow* the
   authorized surface, never widen it. Provider, model, and credential are
   derived from durable account/project state, not from request payload.
2. **The model is pinned explicitly.** The binding names exactly one model.
   The Pi wrapper independently refuses an identity mismatch
   (``authorized_identity_rejected``), so a substituted model fails closed
   rather than silently succeeding.
3. **The credential is authorized, not assumed.** ``authorize_credential_selection``
   revalidates owner scope, provider, funding route, expiry, and usage policy
   against the stored credential row.
4. **Fail closed.** If a trusted input is missing or ambiguous, no binding is
   produced and the reason is explicit.

The binding is secret-free by construction: it carries a credential *reference*
and owner scope, never key material. Secret release happens separately, per
attempt, through the credential-lease authority.

See ADR-094 (invocation-scoped execution binding), ADR-077 (authority
layering), and ``docs/architecture/guardian-delegation-loop-contract.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guardian.agents.coding_agent_contracts import (
    CodingExecutionBinding,
    coding_execution_reasoning_effort_lane,
)
from guardian.agents.execution_credentials import (
    CredentialAuthorityError,
    authorize_credential_selection,
)
from guardian.pi.tokens import PI_AUTHORIZED_REASONING_EFFORTS

#: The only harness the current coding worker can accept. The worker hardcodes
#: ``harness_id == "pi"`` in ``_validate_task_execution_binding``; a different
#: harness would be rejected at dequeue, so it is refused here instead.
GUARDIAN_CODING_HARNESS_ID = "pi"

#: Harness selection mode recorded in the binding. ``default`` means the
#: harness was chosen by the runtime, not named by the caller.
GUARDIAN_CODING_HARNESS_SELECTION_MODE = "default"

#: Placement recorded in the binding. The coding worker runs as a container.
GUARDIAN_CODING_PLACEMENT = "container"

#: Attempt budget for one delegated task. The worker requires 1..3.
GUARDIAN_CODING_MAX_ATTEMPTS = 1


class GuardianExecutionBindingError(RuntimeError):
    """A trusted input was missing, ambiguous, or unauthorized.

    ``code`` is a stable, machine-readable reason. The binding is never
    produced in this case — this is a fail-closed authority.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


@dataclass(frozen=True)
class GuardianExecutionBindingRequest:
    """Trusted inputs for one delegated coding task.

    Every field here is resolved by Guardian from account/project/workspace
    state. Nothing in this request originates from a user- or model-supplied
    proposal.
    """

    account_id: str
    thread_id: str
    source_message_id: str
    project_id: str | None
    coding_task_id: str
    attempt_id: str
    #: Credential reference resolved from the account's own registered
    #: credentials. Resolved by the caller of this module, but only from
    #: durable account state.
    credential_ref: str
    #: Provider resolved from the account's configured provider posture.
    provider_id: str
    #: Model resolved from the account's configured model posture.
    model_id: str
    #: An explicitly selected reasoning effort, resolved by Guardian from
    #: trusted context. ``None`` means Guardian selects the lane default. A
    #: caller-supplied task field can never set this: the effort reaches the
    #: worker only through the binding Guardian minted.
    reasoning_effort: str | None = None
    max_attempts: int = GUARDIAN_CODING_MAX_ATTEMPTS


def resolve_guardian_reasoning_effort(
    *,
    provider_id: str,
    model_id: str,
    requested: str | None = None,
) -> str | None:
    """Resolve the reasoning effort Guardian authorizes for one lane.

    Returns the authorized effort, or ``None`` when the lane has no validated
    compatibility rule — in that case the binding does not govern the effort
    and the harness keeps its own default, exactly as before.

    An explicitly requested effort is never downgraded: a level the harness
    does not accept, or one the lane does not support, fails closed here
    rather than being silently replaced with the lane default.
    """
    lane = coding_execution_reasoning_effort_lane(provider_id, model_id)
    if requested is None:
        return lane.default if lane is not None else None

    effort = str(requested).strip()
    if effort not in PI_AUTHORIZED_REASONING_EFFORTS:
        raise GuardianExecutionBindingError(
            "guardian_binding_reasoning_effort_invalid"
        )
    if lane is None or effort not in lane.compatible:
        # The lane has no validated compatibility rule, or this level is not
        # one of its validated levels. Either way Guardian cannot authorize
        # it, and it must not be replaced with a level it did not ask for.
        raise GuardianExecutionBindingError(
            "guardian_binding_reasoning_effort_unsupported"
        )
    return effort


def resolve_guardian_execution_binding(
    db: Any,
    request: GuardianExecutionBindingRequest,
) -> dict[str, Any]:
    """Mint one secret-free execution binding from trusted context.

    Returns the binding as a plain dict, suitable for persisting into a
    deployment spec and mirroring into a coding-execution task payload.
    """
    account_id = str(request.account_id or "").strip()
    thread_id = str(request.thread_id or "").strip()
    source_message_id = str(request.source_message_id or "").strip()
    coding_task_id = str(request.coding_task_id or "").strip()
    attempt_id = str(request.attempt_id or "").strip()
    credential_ref = str(request.credential_ref or "").strip()
    provider_id = str(request.provider_id or "").strip()
    model_id = str(request.model_id or "").strip()

    # Fail closed on missing identity. A binding without lineage cannot be
    # revalidated by the credential-lease authority or the worker.
    if not account_id:
        raise GuardianExecutionBindingError("guardian_binding_account_missing")
    if not thread_id:
        raise GuardianExecutionBindingError("guardian_binding_thread_missing")
    if not source_message_id:
        raise GuardianExecutionBindingError(
            "guardian_binding_source_message_missing"
        )
    if not coding_task_id:
        raise GuardianExecutionBindingError("guardian_binding_coding_task_missing")
    if not attempt_id:
        raise GuardianExecutionBindingError("guardian_binding_attempt_missing")
    if not credential_ref:
        raise GuardianExecutionBindingError("guardian_binding_credential_missing")
    if not provider_id:
        raise GuardianExecutionBindingError("guardian_binding_provider_missing")
    if not model_id:
        raise GuardianExecutionBindingError("guardian_binding_model_missing")

    max_attempts = int(request.max_attempts or 0)
    if max_attempts < 1 or max_attempts > 3:
        raise GuardianExecutionBindingError("guardian_binding_attempt_limit_invalid")

    project_id = (
        str(request.project_id).strip() if request.project_id is not None else None
    ) or None

    if db is None or not hasattr(db, "get_session"):
        raise GuardianExecutionBindingError(
            "guardian_binding_credential_authority_unavailable"
        )

    # The credential authority revalidates owner scope, provider match,
    # funding route, expiry, and usage policy against the stored row. A
    # caller-supplied provider/model cannot widen the grant, because a
    # mismatch here fails closed.
    try:
        credential = authorize_credential_selection(
            db,
            credential_ref=credential_ref,
            account_id=account_id,
            provider_id=provider_id,
            model_id=model_id,
        )
    except CredentialAuthorityError as exc:
        raise GuardianExecutionBindingError(
            "guardian_binding_credential_unauthorized", exc.code
        ) from None
    except Exception as exc:  # pragma: no cover - defensive branch
        raise GuardianExecutionBindingError(
            "guardian_binding_credential_authority_unavailable"
        ) from exc

    # The credential's own provider must be the one we are binding. This is
    # the guard against a model/provider pair that does not correspond to the
    # stored credential.
    bound_provider = str(credential.get("provider_id") or "").strip()
    if bound_provider and bound_provider != provider_id:
        raise GuardianExecutionBindingError(
            "guardian_binding_credential_provider_mismatch"
        )

    # The reasoning effort is resolved here, under Guardian authority, from the
    # same provider/model the binding pins. A lane with no validated
    # compatibility rule leaves the effort ungoverned, so the harness keeps
    # its own default for it.
    reasoning_effort = resolve_guardian_reasoning_effort(
        provider_id=provider_id,
        model_id=model_id,
        requested=request.reasoning_effort,
    )

    try:
        binding = CodingExecutionBinding.authorized(
            harness_id=GUARDIAN_CODING_HARNESS_ID,
            harness_selection_mode=GUARDIAN_CODING_HARNESS_SELECTION_MODE,
            provider_id=provider_id,
            model_id=model_id,
            placement=GUARDIAN_CODING_PLACEMENT,
            credential=credential,
            user_id=account_id,
            project_id=project_id,
            thread_id=thread_id,
            source_message_id=source_message_id,
            coding_task_id=coding_task_id,
            attempt_id=attempt_id,
            max_attempts=max_attempts,
            reasoning_effort=reasoning_effort,
        )
    except ValueError as exc:
        raise GuardianExecutionBindingError(
            "guardian_binding_invalid", str(exc)
        ) from None

    payload = binding.to_dict()
    # A binding is only useful if it round-trips through the same validator
    # the worker and the credential-lease authority apply. Fail here rather
    # than at dequeue.
    try:
        CodingExecutionBinding.from_dict(payload)
    except ValueError as exc:
        raise GuardianExecutionBindingError(
            "guardian_binding_invalid", str(exc)
        ) from None
    return payload


def validate_guardian_execution_binding(
    binding: dict[str, Any],
    *,
    expected_thread_id: str,
    expected_source_message_id: str,
    expected_coding_task_id: str,
    expected_attempt_id: str,
) -> None:
    """Assert a binding matches the lineage it is claimed to authorize.

    Used to prove that a request-provided binding cannot widen or redirect the
    authorization Guardian resolved.
    """
    checks = (
        ("thread_id", expected_thread_id),
        ("source_message_id", expected_source_message_id),
        ("coding_task_id", expected_coding_task_id),
        ("attempt_id", expected_attempt_id),
    )
    for field, expected in checks:
        actual = str(binding.get(field) or "").strip()
        if actual != str(expected).strip():
            raise GuardianExecutionBindingError(
                f"guardian_binding_{field}_mismatch"
            )
    max_attempts = int(binding.get("max_attempts") or 0)
    if max_attempts < 1 or max_attempts > 3:
        raise GuardianExecutionBindingError(
            "guardian_binding_attempt_limit_invalid"
        )
