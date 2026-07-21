"""Content-free terminal evidence for one provider completion attempt."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from guardian.protocol_tokens import CompletionTerminalStatus


@dataclass(frozen=True)
class CompletionTerminalEvidence:
    status: CompletionTerminalStatus
    visible_output_emitted: bool
    explicit_provider_terminal_observed: bool
    finish_reason: str | None
    transport_ended_cleanly: bool
    provider: str
    model: str
    failure_kind: str | None = None
    retry_permitted: bool = False
    runtime_provenance: dict[str, Any] | None = None

    @property
    def successful(self) -> bool:
        return self.status is CompletionTerminalStatus.SUCCESS

    def with_visible_output(self, emitted: bool) -> "CompletionTerminalEvidence":
        return replace(self, visible_output_emitted=bool(emitted))

    def as_dict(self) -> dict[str, Any]:
        """Return bounded metadata; response content is deliberately absent."""
        payload = {
            "status": self.status.value,
            "visible_output_emitted": self.visible_output_emitted,
            "explicit_provider_terminal_observed": (
                self.explicit_provider_terminal_observed
            ),
            "finish_reason": self.finish_reason,
            "transport_ended_cleanly": self.transport_ended_cleanly,
            "provider": self.provider,
            "model": self.model,
            "failure_kind": self.failure_kind,
            "retry_permitted": self.retry_permitted,
        }
        if self.runtime_provenance is not None:
            payload["runtime_provenance"] = dict(self.runtime_provenance)
        return payload

    @classmethod
    def from_dict(cls, raw: Any) -> "CompletionTerminalEvidence | None":
        if not isinstance(raw, dict):
            return None
        try:
            status = CompletionTerminalStatus(str(raw.get("status") or ""))
        except ValueError:
            return None
        runtime_provenance = None
        if isinstance(raw.get("runtime_provenance"), dict):
            # Re-apply the provider boundary when evidence crosses a
            # persistence or retry boundary.  Stored metadata is not trusted
            # merely because it was previously shaped like a dict.
            from guardian.providers.whooshd_control_plane import (
                parse_whooshd_runtime_provenance,
            )

            parsed_provenance = parse_whooshd_runtime_provenance(
                raw["runtime_provenance"]
            )
            if parsed_provenance is not None:
                runtime_provenance = parsed_provenance.as_dict()
        return cls(
            status=status,
            visible_output_emitted=bool(raw.get("visible_output_emitted")),
            explicit_provider_terminal_observed=bool(
                raw.get("explicit_provider_terminal_observed")
            ),
            finish_reason=(
                str(raw.get("finish_reason"))
                if raw.get("finish_reason") is not None
                else None
            ),
            transport_ended_cleanly=bool(raw.get("transport_ended_cleanly")),
            provider=str(raw.get("provider") or ""),
            model=str(raw.get("model") or ""),
            failure_kind=(
                str(raw.get("failure_kind"))
                if raw.get("failure_kind") is not None
                else None
            ),
            retry_permitted=bool(raw.get("retry_permitted")),
            runtime_provenance=runtime_provenance,
        )


@dataclass(frozen=True)
class CompletionAttemptResult:
    output: Any
    terminal: CompletionTerminalEvidence
    runtime_provenance: dict[str, Any] | None = None


class CompletionTerminalError(RuntimeError):
    """Raised when provider output lacks accepted successful terminal proof."""

    def __init__(self, evidence: CompletionTerminalEvidence):
        self.evidence = evidence
        self.metadata = {
            "failure_kind": evidence.failure_kind or evidence.status.value,
            "terminal_evidence": evidence.as_dict(),
            "provider": evidence.provider,
            "model": evidence.model,
        }
        super().__init__(evidence.failure_kind or evidence.status.value)


def successful_non_stream_terminal(
    *, provider: str, model: str, finish_reason: str | None = None
) -> CompletionTerminalEvidence:
    return CompletionTerminalEvidence(
        status=CompletionTerminalStatus.SUCCESS,
        visible_output_emitted=False,
        explicit_provider_terminal_observed=True,
        finish_reason=finish_reason,
        transport_ended_cleanly=True,
        provider=provider,
        model=model,
        failure_kind=None,
        retry_permitted=False,
    )


def require_successful_terminal(
    result: dict[str, Any],
) -> CompletionTerminalEvidence:
    evidence = CompletionTerminalEvidence.from_dict(result.get("terminal_evidence"))
    if evidence is not None and evidence.successful:
        return evidence
    if evidence is None:
        evidence = CompletionTerminalEvidence(
            status=CompletionTerminalStatus.MALFORMED_TERMINAL,
            visible_output_emitted=False,
            explicit_provider_terminal_observed=False,
            finish_reason=None,
            transport_ended_cleanly=False,
            provider=str(result.get("provider") or result.get("final_provider") or ""),
            model=str(result.get("model") or result.get("final_model") or ""),
            failure_kind="terminal_evidence_missing",
            retry_permitted=False,
        )
    raise CompletionTerminalError(evidence)
