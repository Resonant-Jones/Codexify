"""Bounded error hierarchy for the provider-free Campaign Engine runtime.

All runtime failures surface as CampaignEngineError subclasses. No failure
path raises a bare exception: callers (and the CLI) can catch the base class
and report a bounded failure without leaking internals.
"""

from __future__ import annotations

from typing import Any


class CampaignEngineError(RuntimeError):
    """Base class for all provider-free Campaign Engine runtime errors."""


class CampaignValidationError(CampaignEngineError):
    """Campaign document failed strict parsing, schema, or cross-object validation."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues: list[str] = list(issues or [])


class CampaignRoleBindingError(CampaignValidationError):
    """Role-binding invariants were violated before any artifact publication."""


class CampaignTaskSelectionError(CampaignValidationError):
    """Task selection invariants were violated before any artifact publication."""


class CampaignSourceContextError(CampaignEngineError):
    """The optional source-selection lineage fixture is malformed."""


class CampaignArtifactError(CampaignEngineError):
    """Artifact publication failure: unsafe path, atomic write, or promotion."""


class CampaignOutputExistsError(CampaignArtifactError):
    """Deterministic rerun policy: the target campaign output directory already exists.

    Selected rerun behavior (documented and test-covered): a provider-free run
    fails fast when `<output_root>/<campaign_id>/` already exists. Reruns of
    identical inputs into a fresh output root are byte-deterministic; rerunning
    into a used root requires the operator to remove the prior output first.
    """


class CampaignClockError(CampaignEngineError):
    """The injected clock produced an unusable timestamp."""


def format_issues(issues: list[Any]) -> str:
    """Render a bounded issue list as one line, capped for CLI readability."""
    rendered = "; ".join(str(issue) for issue in issues[:12])
    if len(issues) > 12:
        rendered += f"; ... ({len(issues)} total)"
    return rendered
