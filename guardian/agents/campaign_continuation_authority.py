"""Validated Campaign Continuation Authority envelope records.

This module validates the operator-approved document for durable storage. It
does not evaluate continuation gates, authorize attempts, or dispatch work.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


class CampaignPromotionAuthorities(BaseModel):
    """Explicit promotion permissions, kept separate from continuation."""

    model_config = ConfigDict(extra="forbid")

    commit: StrictBool = False
    push: StrictBool = False
    merge: StrictBool = False
    release: StrictBool = False
    deploy: StrictBool = False
    destructive_production_mutation: StrictBool = False


class CampaignContinuationAuthorityEnvelope(BaseModel):
    """Versioned, bounded authority document approved for one Campaign."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal[1] = 1
    campaign_objective: StrictStr = Field(min_length=1)
    allowed_task_classes: list[StrictStr] = Field(min_length=1)
    permitted_execution_lanes: list[StrictStr] = Field(min_length=1)
    permitted_workspace_scope: list[StrictStr] = Field(min_length=1)
    permitted_validation_proof_classes: list[StrictStr] = Field(min_length=1)
    spend_posture: dict[str, Any] = Field(min_length=1)
    automatic_retry_permitted: StrictBool = False
    max_retries: StrictInt = Field(default=0, ge=0)
    automatic_downstream_dispatch_permitted: StrictBool = False
    promotion_authorities: CampaignPromotionAuthorities = Field(
        default_factory=CampaignPromotionAuthorities
    )
    explicit_stop_conditions: list[StrictStr] = Field(min_length=1)

    @field_validator(
        "allowed_task_classes",
        "permitted_execution_lanes",
        "permitted_workspace_scope",
        "permitted_validation_proof_classes",
        "explicit_stop_conditions",
    )
    @classmethod
    def normalize_unique_scope_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("scope values must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("scope values must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_retry_bound(self) -> CampaignContinuationAuthorityEnvelope:
        if self.automatic_retry_permitted and self.max_retries < 1:
            raise ValueError("permitted automatic retry requires max_retries >= 1")
        if not self.automatic_retry_permitted and self.max_retries != 0:
            raise ValueError("max_retries must be 0 when automatic retry is disabled")
        return self


__all__ = [
    "CampaignContinuationAuthorityEnvelope",
    "CampaignPromotionAuthorities",
]
