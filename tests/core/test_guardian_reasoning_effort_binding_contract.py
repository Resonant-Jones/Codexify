"""The Guardian-governed reasoning-effort contract at the binding boundary.

The reasoning effort reaches a coding worker only through the execution
binding Guardian minted. These cases pin that contract at the mint and at the
validator:

- a binding minted for a lane with a validated compatibility rule *governs*
  the effort, on every mint path;
- an unauthorized or lane-incompatible effort still fails closed, with the
  error code that says which rule it broke;
- the schema-version distinction between a binding that governs the effort
  (version 2) and one that does not (version 1) keeps working.
"""

from __future__ import annotations

import pytest

from guardian.agents.coding_agent_contracts import (
    CODING_EXECUTION_BINDING_EFFORT_SCHEMA_VERSION,
    CODING_EXECUTION_BINDING_SCHEMA_VERSION,
    CODING_EXECUTION_REASONING_EFFORT_LANES,
    CodingExecutionBinding,
    coding_execution_reasoning_effort_lane,
)
from guardian.core.guardian_execution_binding import (
    GuardianExecutionBindingError,
    resolve_guardian_reasoning_effort,
)
from guardian.pi.tokens import PI_AUTHORIZED_REASONING_EFFORTS

#: The one lane with a validated compatibility rule. The live delegation canary
#: exercised it, and it is the lane whose effort the worker forwards.
GOVERNED_PROVIDER_ID = "deepseek"
GOVERNED_MODEL_ID = "deepseek-v4-flash"


def _credential(provider_id: str) -> dict[str, object]:
    return {
        "credential_ref": "credential-account-a",
        "owner_scope": "account",
        "owner_id": "account-a",
        "provider_id": provider_id,
        "credential_type": "api_key",
        "funding_route": "user_byok",
        "source_class": "account_api_key",
        "usage_policy_ref": None,
    }


def _mint(
    *,
    provider_id: str,
    model_id: str,
    reasoning_effort: str | None = None,
) -> CodingExecutionBinding:
    return CodingExecutionBinding.authorized(
        harness_id="pi",
        harness_selection_mode="default",
        provider_id=provider_id,
        model_id=model_id,
        placement="container",
        credential=_credential(provider_id),
        user_id="account-a",
        project_id=None,
        thread_id="thread-a",
        source_message_id="message-a",
        coding_task_id="coding-task-a",
        attempt_id="attempt-a",
        max_attempts=1,
        reasoning_effort=reasoning_effort,
    )


def test_a_governed_lane_mints_a_binding_that_governs_the_effort() -> None:
    """A binding minted for a governed lane carries that lane's level.

    The lane table is the authority for the effort on a governed lane. A
    binding that left the effort ungoverned would hand the harness its own
    default instead — a level Guardian never authorized, and on this lane one
    the harness rejects before provider execution.
    """
    lane = coding_execution_reasoning_effort_lane(
        GOVERNED_PROVIDER_ID, GOVERNED_MODEL_ID
    )
    assert lane is not None

    binding = _mint(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
    )

    assert binding.schema_version == CODING_EXECUTION_BINDING_EFFORT_SCHEMA_VERSION
    assert binding.reasoning_effort == lane.default
    assert binding.reasoning_effort in lane.compatible


def test_an_ungoverned_lane_mints_a_binding_without_an_effort() -> None:
    """A lane with no validated rule keeps the harness default.

    Nothing about that lane has been validated, so Guardian does not govern its
    effort and the binding says so by carrying none.
    """
    binding = _mint(provider_id="test-provider", model_id="test-model")

    assert binding.schema_version == CODING_EXECUTION_BINDING_SCHEMA_VERSION
    assert binding.reasoning_effort is None


def test_an_explicitly_authorized_effort_is_never_replaced() -> None:
    """An explicit level is carried as given, never substituted."""
    binding = _mint(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
        reasoning_effort="high",
    )

    assert binding.reasoning_effort == "high"


def test_an_unauthorized_effort_fails_closed_with_the_invalid_code() -> None:
    """A level outside the authorized set is refused, not downgraded."""
    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_reasoning_effort(
            provider_id=GOVERNED_PROVIDER_ID,
            model_id=GOVERNED_MODEL_ID,
            requested="turbo",
        )

    assert excinfo.value.code == "guardian_binding_reasoning_effort_invalid"


def test_a_lane_incompatible_effort_fails_closed_with_the_unsupported_code() -> None:
    """An authorized level the lane never validated is refused.

    ``medium`` is an authorized level in general, but it is not one of the
    levels this lane validated. Guardian cannot authorize it here, and it must
    not be silently replaced with a level the caller did not ask for.
    """
    assert "medium" in PI_AUTHORIZED_REASONING_EFFORTS

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_reasoning_effort(
            provider_id=GOVERNED_PROVIDER_ID,
            model_id=GOVERNED_MODEL_ID,
            requested="medium",
        )

    assert excinfo.value.code == "guardian_binding_reasoning_effort_unsupported"


def test_a_binding_whose_effort_is_not_in_its_lane_is_refused() -> None:
    """The validator refuses a governing binding that carries an off-lane level.

    No minting path may persist an effort Guardian never authorized, so the
    binding is rejected when it is read back, before anything executes.
    """
    binding = _mint(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
        reasoning_effort="off",
    )
    payload = binding.to_dict()
    payload["reasoning_effort"] = "medium"

    with pytest.raises(ValueError) as excinfo:
        CodingExecutionBinding.from_dict(payload)

    assert str(excinfo.value) == "execution_binding_reasoning_effort_unsupported"


def test_a_binding_that_claims_to_govern_without_an_effort_is_refused() -> None:
    """A governing binding must carry the effort it was minted with."""
    binding = _mint(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
    )
    payload = binding.to_dict()
    payload.pop("reasoning_effort")

    with pytest.raises(ValueError) as excinfo:
        CodingExecutionBinding.from_dict(payload)

    assert str(excinfo.value) == "execution_binding_reasoning_effort_missing"


def test_schema_v1_and_v2_bindings_both_validate() -> None:
    """The schema-version distinction keeps working in both directions."""
    governed = _mint(
        provider_id=GOVERNED_PROVIDER_ID,
        model_id=GOVERNED_MODEL_ID,
    )
    ungoverned = _mint(provider_id="test-provider", model_id="test-model")

    validated_governed = CodingExecutionBinding.from_dict(governed.to_dict())
    validated_ungoverned = CodingExecutionBinding.from_dict(ungoverned.to_dict())

    assert validated_governed.schema_version == (
        CODING_EXECUTION_BINDING_EFFORT_SCHEMA_VERSION
    )
    assert validated_governed.reasoning_effort == governed.reasoning_effort
    assert validated_ungoverned.schema_version == CODING_EXECUTION_BINDING_SCHEMA_VERSION
    assert validated_ungoverned.reasoning_effort is None


def test_every_lane_default_is_inside_its_own_compatible_set() -> None:
    """The lane table is internally consistent.

    The lane's default is the level Guardian authorizes for it, so it has to
    be one of the levels that lane validated, and one of the authorized
    levels. A lane that broke this would authorize nothing, and the mint
    would have to fail closed.
    """
    for lane in CODING_EXECUTION_REASONING_EFFORT_LANES:
        assert lane.default in lane.compatible, lane
        assert lane.default in PI_AUTHORIZED_REASONING_EFFORTS, lane
        assert lane.compatible <= PI_AUTHORIZED_REASONING_EFFORTS, lane
