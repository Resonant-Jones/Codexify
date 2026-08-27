"""Provider-free Campaign Engine runtime package (ADR-066 authorized slice).

Public surface:

- :func:`run_provider_free_campaign` — provider-free lifecycle entrypoint
  (must remain unchanged at import and runtime);
- :mod:`codex_runner.campaign_engine.live_executor` — live Executor
  preparation/execution entrypoints (ADR-068 authorized slice);
- :class:`CampaignRunResult` / :class:`LiveExecutorRunResult` — structured
  run envelopes;
- :class:`CampaignClock` / :class:`SystemClock` / :class:`FixedClock` — the
  deterministic-time seam;
- :class:`LiveExecutorPreparation` — the immutable live-Executor
  preparation record produced before Guardian authorization is requested;
- bounded error hierarchy under :mod:`codex_runner.campaign_engine.errors`.

Importing this package pulls in only the Python standard library plus
``jsonschema``. The Guardian/Pi rail is imported *lazily* inside the live
Executor execution helpers so that ``import
codex_runner.campaign_engine`` itself remains safe for provider-free
importers; no provider, Coding Loop, Guardian execution, command bus,
subprocess, network, Git, or database code is pulled at import time.
"""

from .errors import (
    CampaignArtifactError,
    CampaignClockError,
    CampaignEngineError,
    CampaignLiveExecutorError,
    CampaignOutputExistsError,
    CampaignRoleBindingError,
    CampaignSourceContextError,
    CampaignTaskSelectionError,
    CampaignValidationError,
)
from .models import (
    LIVE_EXECUTOR_CLASSIFICATION,
    AcceptanceCriterionResult,
    CampaignClock,
    CampaignRunResult,
    FixedClock,
    LiveExecutorPreparation,
    LiveExecutorRunResult,
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
    "CampaignLiveExecutorError",
    "CampaignOutputExistsError",
    "CampaignRoleBindingError",
    "CampaignRunResult",
    "CampaignSourceContextError",
    "CampaignTaskSelectionError",
    "CampaignValidationError",
    "FixedClock",
    "LIVE_EXECUTOR_CLASSIFICATION",
    "LiveExecutorPreparation",
    "LiveExecutorRunResult",
    "SourceContextRecord",
    "SystemClock",
    "run_provider_free_campaign",
]
