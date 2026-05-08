"""Canonical tokens for extension persistence."""

from __future__ import annotations

from enum import Enum


class ExtensionTargetSurface(str, Enum):
    """Bounded target surfaces for self-extending proposals."""

    COMMAND_BUS = "command_bus"
    WORKFLOW_BUILDER = "workflow_builder"
    RETRIEVAL_ROUTER = "retrieval_router"
    PERSONA_STUDIO = "persona_studio"


class ExtensionProposalScope(str, Enum):
    """Canonical scope bindings for extension proposals."""

    PROJECT = "project_scoped"
    PROFILE = "profile_scoped"
    ACCOUNT = "account_scoped"


class ExtensionProposalStatus(str, Enum):
    """Canonical proposal lifecycle statuses."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class InstallGateDecisionToken(str, Enum):
    """Canonical install-gate decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


class CapabilityRegistryStatus(str, Enum):
    """Canonical registry lifecycle statuses."""

    REGISTERED = "registered"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    ARCHIVED = "archived"


class CapabilityEntryProvenanceClass(str, Enum):
    """Canonical provenance classes for registry entries."""

    PROPOSAL_APPROVAL = "proposal_approval"


class CapabilityResultReinjectionOutcome(str, Enum):
    """Canonical reinjection outcomes for manual capability dispatch."""

    SUCCESS = "success"
    FAILURE = "failure"
    UNUSABLE = "unusable"


class CapabilityReinjectionResultShape(str, Enum):
    """Canonical normalized shapes for reinjected capability results."""

    NORMALIZED_SUCCESS = "normalized_success"
    NORMALIZED_FAILURE = "normalized_failure"
    FAILED_CLOSED = "failed_closed"


class CapabilityReinjectionFailureReason(str, Enum):
    """Canonical failure reasons for reinjection normalization."""

    OWNER_MISMATCH = "owner_mismatch"
    INCONSISTENT_PROVENANCE = "inconsistent_provenance"
    MISSING_COMMAND_BUS_RUN_LINKAGE = "missing_command_bus_run_linkage"
    INVALID_COMMAND_BUS_RESULT = "invalid_command_bus_result"
    MISSING_INLINE_RESULT = "missing_inline_result"
    MISSING_ERROR = "missing_error"
    INCONSISTENT_COMMAND_BUS_RESULT = "inconsistent_command_bus_result"


class CapabilityReinjectionSource(str, Enum):
    """Canonical reinjection source tokens."""

    MANUAL_DISPATCH = "manual_dispatch"


class ExtensionInstallBindingScope(str, Enum):
    """Canonical scope bindings for install bindings."""

    PROJECT = "project_scoped"
    PROFILE = "profile_scoped"
    ACCOUNT = "account_scoped"


class ExtensionInstallBindingStatus(str, Enum):
    """Canonical lifecycle states for install bindings."""

    ACTIVE = "active"
    UNBOUND = "unbound"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class CapabilityActivationContextToken(str, Enum):
    """Canonical activation contexts for read-time capability checks."""

    OWNER_ONLY = "owner_only"
    OWNER_PROJECT = "owner_project"
    OWNER_PROFILE = "owner_profile"
    OWNER_PROJECT_PROFILE = "owner_project_profile"


class CapabilityActivationOutcomeToken(str, Enum):
    """Canonical activation outcomes."""

    ALLOWED = "allowed"
    DENIED = "denied"
    CONFLICT = "conflict"


class CapabilityActivationDenyReasonToken(str, Enum):
    """Canonical activation denial reasons."""

    MISSING_IDENTITY = "missing_identity"
    NO_MATCHING_EXPOSURE = "no_matching_exposure"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"


class CapabilityActivationConflictClassToken(str, Enum):
    """Canonical activation conflict classes."""

    SAME_COMMAND_EXPOSURE = "same_command_exposure"
    RESOLUTION_AMBIGUITY = "resolution_ambiguity"


class CapabilityDispatchSourceToken(str, Enum):
    """Canonical dispatch source tags for prepared activation envelopes."""

    CAPABILITY_ACTIVATION = "capability_activation"


class CapabilityManualDispatchOutcomeToken(str, Enum):
    """Canonical outcomes for bounded manual capability dispatch."""

    DISPATCHED = "dispatched"
    DENIED = "denied"
    CONFLICT = "conflict"
    BUS_REJECTED = "bus_rejected"


class CapabilityManualDispatchDenyReasonToken(str, Enum):
    """Canonical denial reasons for manual capability dispatch."""

    OWNER_ACCOUNT_MISMATCH = "owner_account_mismatch"
    INVALID_ENVELOPE = "invalid_envelope"
    ACTIVATION_DENIED = "activation_denied"
    ACTIVATION_CONFLICT = "activation_conflict"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    COMMAND_BUS_REJECTED = "command_bus_rejected"


class CapabilityManualDispatchSourceToken(str, Enum):
    """Canonical invocation sources for manual dispatch bridges."""

    MANUAL_CAPABILITY_DISPATCH = "manual_capability_dispatch"


class CapabilityManualDispatchIdempotencyClassToken(str, Enum):
    """Canonical idempotency posture tags for manual dispatch."""

    SINGLE_COMMAND_BUS_INVOCATION = "single_command_bus_invocation"


class CapabilityAssistantReentryOutcome(str, Enum):
    """Canonical reentry outcomes for one-turn assistant continuation."""

    SUCCESS = "success"
    FAILURE = "failure"
    FAILED_CLOSED = "failed_closed"


class CapabilityAssistantReentryFailureReason(str, Enum):
    """Canonical failure reasons for assistant reentry normalization."""

    OWNER_MISMATCH = "owner_mismatch"
    INCONSISTENT_PROVENANCE = "inconsistent_provenance"
    REINJECTION_RESULT_INCONSISTENT = "reinjection_result_inconsistent"
    REINJECTION_RESULT_SHAPE_MISMATCH = "reinjection_result_shape_mismatch"
    MISSING_MANIFEST_SNAPSHOT = "missing_manifest_snapshot"
    AMBIGUOUS_REINJECTION_SOURCE = "ambiguous_reinjection_source"


EXTENSION_TARGET_SURFACES: frozenset[str] = frozenset(
    surface.value for surface in ExtensionTargetSurface
)
EXTENSION_PROPOSAL_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in ExtensionProposalScope
)
EXTENSION_PROPOSAL_STATUSES: frozenset[str] = frozenset(
    status.value for status in ExtensionProposalStatus
)
INSTALL_GATE_DECISION_TOKENS: frozenset[str] = frozenset(
    decision.value for decision in InstallGateDecisionToken
)
CAPABILITY_REGISTRY_STATUSES: frozenset[str] = frozenset(
    status.value for status in CapabilityRegistryStatus
)
CAPABILITY_ENTRY_PROVENANCE_CLASSES: frozenset[str] = frozenset(
    provenance.value for provenance in CapabilityEntryProvenanceClass
)
CAPABILITY_RESULT_REINJECTION_OUTCOMES: frozenset[str] = frozenset(
    outcome.value for outcome in CapabilityResultReinjectionOutcome
)
CAPABILITY_REINJECTION_RESULT_SHAPES: frozenset[str] = frozenset(
    shape.value for shape in CapabilityReinjectionResultShape
)
CAPABILITY_REINJECTION_FAILURE_REASONS: frozenset[str] = frozenset(
    reason.value for reason in CapabilityReinjectionFailureReason
)
CAPABILITY_REINJECTION_SOURCES: frozenset[str] = frozenset(
    source.value for source in CapabilityReinjectionSource
)
EXTENSION_INSTALL_BINDING_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in ExtensionInstallBindingScope
)
EXTENSION_INSTALL_BINDING_STATUSES: frozenset[str] = frozenset(
    status.value for status in ExtensionInstallBindingStatus
)
CAPABILITY_ACTIVATION_CONTEXT_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityActivationContextToken
)
CAPABILITY_ACTIVATION_OUTCOME_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityActivationOutcomeToken
)
CAPABILITY_ACTIVATION_DENY_REASON_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityActivationDenyReasonToken
)
CAPABILITY_ACTIVATION_CONFLICT_CLASS_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityActivationConflictClassToken
)
CAPABILITY_DISPATCH_SOURCE_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityDispatchSourceToken
)
CAPABILITY_MANUAL_DISPATCH_OUTCOME_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityManualDispatchOutcomeToken
)
CAPABILITY_MANUAL_DISPATCH_DENY_REASON_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityManualDispatchDenyReasonToken
)
CAPABILITY_MANUAL_DISPATCH_SOURCE_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityManualDispatchSourceToken
)
CAPABILITY_MANUAL_DISPATCH_IDEMPOTENCY_CLASS_TOKENS: frozenset[str] = frozenset(
    token.value for token in CapabilityManualDispatchIdempotencyClassToken
)
CAPABILITY_ASSISTANT_REENTRY_OUTCOMES: frozenset[str] = frozenset(
    outcome.value for outcome in CapabilityAssistantReentryOutcome
)
CAPABILITY_ASSISTANT_REENTRY_FAILURE_REASONS: frozenset[str] = frozenset(
    reason.value for reason in CapabilityAssistantReentryFailureReason
)


class ExtensionTokenError(ValueError):
    """Raised when a caller supplies an invalid extension token."""


def _normalize_token(
    value: str | None, *, allowed: frozenset[str], kind: str
) -> str:
    token = str(value or "").strip()
    if token not in allowed:
        raise ExtensionTokenError(f"Invalid {kind}: {value!r}")
    return token


def normalize_extension_target_surface(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_TARGET_SURFACES, kind="target_surface"
    )


def normalize_extension_proposal_scope(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_SCOPES, kind="proposal_scope"
    )


def normalize_extension_proposal_status(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_STATUSES, kind="proposal_status"
    )


def normalize_install_gate_decision_token(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=INSTALL_GATE_DECISION_TOKENS,
        kind="install_gate_decision",
    )


def normalize_capability_registry_status(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_REGISTRY_STATUSES,
        kind="capability_registry_status",
    )


def normalize_capability_entry_provenance_class(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ENTRY_PROVENANCE_CLASSES,
        kind="capability_entry_provenance_class",
    )


def normalize_capability_result_reinjection_outcome(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_RESULT_REINJECTION_OUTCOMES,
        kind="capability_result_reinjection_outcome",
    )


def normalize_capability_reinjection_result_shape(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_REINJECTION_RESULT_SHAPES,
        kind="capability_reinjection_result_shape",
    )


def normalize_capability_reinjection_failure_reason(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_REINJECTION_FAILURE_REASONS,
        kind="capability_reinjection_failure_reason",
    )


def normalize_capability_reinjection_source(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_REINJECTION_SOURCES,
        kind="capability_reinjection_source",
    )


def normalize_extension_install_binding_scope(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=EXTENSION_INSTALL_BINDING_SCOPES,
        kind="install_binding_scope",
    )


def normalize_extension_install_binding_status(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=EXTENSION_INSTALL_BINDING_STATUSES,
        kind="install_binding_status",
    )


def normalize_capability_activation_context_token(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ACTIVATION_CONTEXT_TOKENS,
        kind="capability_activation_context",
    )


def normalize_capability_activation_outcome_token(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ACTIVATION_OUTCOME_TOKENS,
        kind="capability_activation_outcome",
    )


def normalize_capability_activation_deny_reason_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ACTIVATION_DENY_REASON_TOKENS,
        kind="capability_activation_deny_reason",
    )


def normalize_capability_activation_conflict_class_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ACTIVATION_CONFLICT_CLASS_TOKENS,
        kind="capability_activation_conflict_class",
    )


def normalize_capability_dispatch_source_token(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_DISPATCH_SOURCE_TOKENS,
        kind="capability_dispatch_source",
    )


def normalize_capability_manual_dispatch_outcome_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_MANUAL_DISPATCH_OUTCOME_TOKENS,
        kind="capability_manual_dispatch_outcome",
    )


def normalize_capability_manual_dispatch_deny_reason_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_MANUAL_DISPATCH_DENY_REASON_TOKENS,
        kind="capability_manual_dispatch_deny_reason",
    )


def normalize_capability_manual_dispatch_source_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_MANUAL_DISPATCH_SOURCE_TOKENS,
        kind="capability_manual_dispatch_source",
    )


def normalize_capability_manual_dispatch_idempotency_class_token(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_MANUAL_DISPATCH_IDEMPOTENCY_CLASS_TOKENS,
        kind="capability_manual_dispatch_idempotency_class",
    )


def normalize_capability_assistant_reentry_outcome(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ASSISTANT_REENTRY_OUTCOMES,
        kind="capability_assistant_reentry_outcome",
    )


def normalize_capability_assistant_reentry_failure_reason(
    value: str | None,
) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ASSISTANT_REENTRY_FAILURE_REASONS,
        kind="capability_assistant_reentry_failure_reason",
    )


__all__ = [
    "ExtensionTargetSurface",
    "ExtensionProposalScope",
    "ExtensionProposalStatus",
    "InstallGateDecisionToken",
    "CapabilityRegistryStatus",
    "CapabilityEntryProvenanceClass",
    "CapabilityResultReinjectionOutcome",
    "CapabilityReinjectionResultShape",
    "CapabilityReinjectionFailureReason",
    "CapabilityReinjectionSource",
    "ExtensionInstallBindingScope",
    "ExtensionInstallBindingStatus",
    "CapabilityActivationContextToken",
    "CapabilityActivationOutcomeToken",
    "CapabilityActivationDenyReasonToken",
    "CapabilityActivationConflictClassToken",
    "CapabilityDispatchSourceToken",
    "CapabilityManualDispatchOutcomeToken",
    "CapabilityManualDispatchDenyReasonToken",
    "CapabilityManualDispatchSourceToken",
    "CapabilityManualDispatchIdempotencyClassToken",
    "CapabilityAssistantReentryOutcome",
    "CapabilityAssistantReentryFailureReason",
    "ExtensionTokenError",
    "EXTENSION_TARGET_SURFACES",
    "EXTENSION_PROPOSAL_SCOPES",
    "EXTENSION_PROPOSAL_STATUSES",
    "INSTALL_GATE_DECISION_TOKENS",
    "CAPABILITY_REGISTRY_STATUSES",
    "CAPABILITY_ENTRY_PROVENANCE_CLASSES",
    "CAPABILITY_RESULT_REINJECTION_OUTCOMES",
    "CAPABILITY_REINJECTION_RESULT_SHAPES",
    "CAPABILITY_REINJECTION_FAILURE_REASONS",
    "CAPABILITY_REINJECTION_SOURCES",
    "EXTENSION_INSTALL_BINDING_SCOPES",
    "EXTENSION_INSTALL_BINDING_STATUSES",
    "CAPABILITY_ACTIVATION_CONTEXT_TOKENS",
    "CAPABILITY_ACTIVATION_OUTCOME_TOKENS",
    "CAPABILITY_ACTIVATION_DENY_REASON_TOKENS",
    "CAPABILITY_ACTIVATION_CONFLICT_CLASS_TOKENS",
    "CAPABILITY_DISPATCH_SOURCE_TOKENS",
    "CAPABILITY_MANUAL_DISPATCH_OUTCOME_TOKENS",
    "CAPABILITY_MANUAL_DISPATCH_DENY_REASON_TOKENS",
    "CAPABILITY_MANUAL_DISPATCH_SOURCE_TOKENS",
    "CAPABILITY_MANUAL_DISPATCH_IDEMPOTENCY_CLASS_TOKENS",
    "CAPABILITY_ASSISTANT_REENTRY_OUTCOMES",
    "CAPABILITY_ASSISTANT_REENTRY_FAILURE_REASONS",
    "normalize_extension_target_surface",
    "normalize_extension_proposal_scope",
    "normalize_extension_proposal_status",
    "normalize_install_gate_decision_token",
    "normalize_capability_registry_status",
    "normalize_capability_entry_provenance_class",
    "normalize_capability_result_reinjection_outcome",
    "normalize_capability_reinjection_result_shape",
    "normalize_capability_reinjection_failure_reason",
    "normalize_capability_reinjection_source",
    "normalize_extension_install_binding_scope",
    "normalize_extension_install_binding_status",
    "normalize_capability_activation_context_token",
    "normalize_capability_activation_outcome_token",
    "normalize_capability_activation_deny_reason_token",
    "normalize_capability_activation_conflict_class_token",
    "normalize_capability_dispatch_source_token",
    "normalize_capability_manual_dispatch_outcome_token",
    "normalize_capability_manual_dispatch_deny_reason_token",
    "normalize_capability_manual_dispatch_source_token",
    "normalize_capability_manual_dispatch_idempotency_class_token",
    "normalize_capability_assistant_reentry_outcome",
    "normalize_capability_assistant_reentry_failure_reason",
]
