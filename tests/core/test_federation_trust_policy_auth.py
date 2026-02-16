import json

from guardian.core.auth import (
    sign_federation_trust_policy,
    verify_federation_trust_policy,
)


def test_verify_federation_trust_policy_round_trip():
    policy_json = json.dumps(
        {
            "allowed_origins": ["https://peer.example.com"],
            "allowed_nodes": ["node-beta"],
            "allow_open_enrollment": False,
        }
    )
    signature = sign_federation_trust_policy(policy_json, "policy-secret")

    valid, parsed = verify_federation_trust_policy(
        policy_json,
        signature,
        signing_key="policy-secret",
    )

    assert valid is True
    assert parsed is not None
    assert parsed["allowed_nodes"] == ["node-beta"]


def test_verify_federation_trust_policy_rejects_tampered_payload():
    policy_json = json.dumps({"allowed_nodes": ["node-beta"]})
    signature = sign_federation_trust_policy(policy_json, "policy-secret")

    valid, parsed = verify_federation_trust_policy(
        json.dumps({"allowed_nodes": ["node-gamma"]}),
        signature,
        signing_key="policy-secret",
    )

    assert valid is False
    assert parsed is None


def test_verify_federation_trust_policy_rejects_missing_key():
    policy_json = json.dumps({"allowed_nodes": ["node-beta"]})
    signature = sign_federation_trust_policy(policy_json, "policy-secret")

    valid, parsed = verify_federation_trust_policy(
        policy_json,
        signature,
        signing_key=None,
    )

    assert valid is False
    assert parsed is None
