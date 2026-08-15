"""Provider-free Campaign Engine runtime package (ADR-066 authorized slice).

Public surface:

- :func:`run_provider_free_campaign` — callable runtime service (no CLI parsing);
- :class:`CampaignRunResult` — structured run envelope;
- :class:`CampaignClock` / :class:`SystemClock` / :class:`FixedClock` — the
  deterministic-time seam;
- bounded error hierarchy under :mod:`codex_runner.campaign_engine.errors`.

The package imports only the Python standard library plus (lazily)
``jsonschema`` for schema validation. It never imports or invokes providers,
Pi, Coding Loop, Guardian execution, the command bus, subprocess, network,
Git, or database code.
"""

from .errors import (
    CampaignArtifactError,
    CampaignClockError,
    CampaignEngineError,
    CampaignOutputExistsError,
    CampaignRoleBindingError,
    CampaignSourceContextError,
    CampaignTaskSelectionError,
    CampaignValidationError,
)
from .models import (
    AcceptanceCriterionResult,
    CampaignClock,
    CampaignRunResult,
    FixedClock,
    SourceContextRecord,
    SystemClock,
)
from .runtime import run_provider_free_campaign

__all__ = [
    "AcceptanceCriterionResult",
    "CampaignArtifactError",
    "CampaignClock",
    "CampaignClockError",
    "CampaignEngineError",
    "CampaignOutputExistsError",
    "CampaignRoleBindingError",
    "CampaignRunResult",
    "CampaignSourceContextError",
    "CampaignTaskSelectionError",
    "CampaignValidationError",
    "FixedClock",
    "SourceContextRecord",
    "SystemClock",
    "run_provider_free_campaign",
]
