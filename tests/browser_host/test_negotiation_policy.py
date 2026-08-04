from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from guardian.browser_host.negotiation import (
    BrowserHostNegotiationPolicy,
    build_default_negotiation_policy,
    negotiate_browser_host_hello,
    validate_browser_host_hello,
    validate_browser_host_hello_request,
)


ROOT = Path(__file__).resolve().parents[2]
HELLO = json.loads(
    (ROOT / "browser_host/contracts/fixtures/valid/hello-compatible.json").read_text()
)


def test_compatible_hello_selects_only_mutually_supported_versions_and_features() -> None:
    decision = negotiate_browser_host_hello(HELLO)
    assert decision.compatible is True
    assert decision.response["compatibilityOutcome"] == "compatible"
    assert decision.response["selectedProtocolVersion"] == "1.0.0"
    assert decision.response["selectedEnvelopeVersion"] == "1.0.0"
    assert decision.response["selectedAttachmentVersion"] == "1.0.0"
    assert decision.response["enabledFeatures"] == HELLO["supportedFeatureTokens"]
    assert decision.response["disabledFeatures"] == []


def test_disallowed_and_undeclared_features_remain_disabled() -> None:
    hello = copy.deepcopy(HELLO)
    hello["supportedFeatureTokens"] = ["capture:selected", "capture:attach"]
    policy = BrowserHostNegotiationPolicy(
        supported_protocol_versions=("1.0.0",),
        supported_envelope_versions=("1.0.0",),
        supported_attachment_versions=("1.0.0",),
        allowed_feature_tokens=("capture:selected",),
    )
    response = negotiate_browser_host_hello(hello, policy).response
    assert response["enabledFeatures"] == ["capture:selected"]
    assert {item["feature"]: item["reason"] for item in response["disabledFeatures"]} == {
        "capture:attach": "not_supported",
        "capture:visible": "undeclared_feature",
    }


@pytest.mark.parametrize(
    ("field", "error_code"),
    [
        ("supportedProtocolVersions", "unsupported_protocol_version"),
        ("supportedEnvelopeVersions", "unsupported_envelope_version"),
        ("supportedAttachmentVersions", "unsupported_attachment_version"),
    ],
)
def test_incompatible_hello_is_valid_fail_closed_negotiation(
    field: str, error_code: str
) -> None:
    hello = copy.deepcopy(HELLO)
    hello[field] = ["9.0.0"]
    decision = negotiate_browser_host_hello(hello)
    assert decision.compatible is False
    assert decision.response["compatibilityOutcome"] == "incompatible"
    assert decision.response["errorCode"] == error_code
    assert decision.response["selectedProtocolVersion"] is None
    assert decision.response["selectedEnvelopeVersion"] is None
    assert decision.response["selectedAttachmentVersion"] is None
    assert decision.response["enabledFeatures"] == []


def test_future_version_hello_uses_canonical_shape_validation_before_rejection() -> None:
    hello = copy.deepcopy(HELLO)
    hello["supportedProtocolVersions"] = ["9.0.0"]
    hello["supportedEnvelopeVersions"] = ["9.0.0"]
    hello["supportedAttachmentVersions"] = ["9.0.0"]
    assert validate_browser_host_hello_request(hello) is True
    assert validate_browser_host_hello(hello) is False


def test_policy_is_deterministic_for_identical_inputs() -> None:
    first = negotiate_browser_host_hello(HELLO).to_dict()
    second = negotiate_browser_host_hello(HELLO).to_dict()
    assert first == second


def test_malformed_hello_is_rejected_before_policy_evaluation() -> None:
    assert validate_browser_host_hello({}) is False
    with pytest.raises(ValueError, match="browser_host_hello_invalid"):
        negotiate_browser_host_hello({})


def test_default_policy_is_loaded_from_the_canonical_contract() -> None:
    policy = build_default_negotiation_policy()
    assert policy.supported_protocol_versions == ("1.0.0",)
    assert policy.supported_envelope_versions == ("1.0.0",)
    assert policy.supported_attachment_versions == ("1.0.0",)
    assert policy.allowed_feature_tokens == (
        "capture:selected",
        "capture:visible",
        "capture:attach",
    )
    response = negotiate_browser_host_hello(HELLO, policy).response
    forbidden = {"apiKey", "cookie", "jwt", "grant", "subject", "pageContent"}
    assert forbidden.isdisjoint(response)
