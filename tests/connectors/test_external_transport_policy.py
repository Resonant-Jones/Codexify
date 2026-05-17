from guardian.connectors.external_transport_policy import (
    CommandTuple,
    ExternalPolicyRequest,
    ExternalPolicyRule,
    evaluate_external_transport_policy,
)


def _request(**overrides: object) -> ExternalPolicyRequest:
    payload: dict[str, object] = {
        "actor_id": "actor-1",
        "subject_id": "subject-1",
        "connector_name": "github",
        "transport": "https",
        "command": None,
        "target_url": None,
        "project_id": "project-1",
        "thread_id": "thread-1",
    }
    payload.update(overrides)
    return ExternalPolicyRequest(**payload)


def test_missing_actor_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(actor_id=""),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "missing_actor"


def test_missing_subject_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(subject_id=""),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "missing_subject"


def test_missing_connector_name_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(connector_name=""),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "missing_connector"


def test_missing_transport_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(transport=""),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "missing_transport"


def test_unknown_transport_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(transport="ftp"),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "unsupported_transport"


def test_no_rules_denies_with_no_allow_rule() -> None:
    decision = evaluate_external_transport_policy(_request(), [])

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_matching_allow_rule_allows() -> None:
    decision = evaluate_external_transport_policy(
        _request(),
        [
            ExternalPolicyRule(
                effect="allow",
                connector_name="github",
                transport="https",
            )
        ],
    )

    assert decision.allowed is True
    assert decision.code == "allowed"
    assert decision.matched_rule_index == 0


def test_deny_rule_overrides_allow_even_if_allow_is_first() -> None:
    decision = evaluate_external_transport_policy(
        _request(),
        [
            ExternalPolicyRule(
                effect="allow",
                connector_name="github",
                transport="https",
                reason="general allow",
            ),
            ExternalPolicyRule(
                effect="deny",
                connector_name="github",
                transport="https",
                reason="explicit deny",
            ),
        ],
    )

    assert decision.allowed is False
    assert decision.code == "denied_by_rule"
    assert decision.reason == "explicit deny"
    assert decision.matched_rule_index == 1


def test_connector_name_mismatch_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(connector_name="notion"),
        [ExternalPolicyRule(effect="allow", connector_name="github")],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_transport_mismatch_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(transport="http"),
        [
            ExternalPolicyRule(
                effect="allow",
                connector_name="github",
                transport="https",
            )
        ],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_command_tuple_must_match_exactly() -> None:
    rules = [
        ExternalPolicyRule(
            effect="allow",
            connector_name="github",
            transport="https",
            command=CommandTuple(namespace="repos", name="read"),
        )
    ]
    allowed = evaluate_external_transport_policy(
        _request(command=CommandTuple(namespace="repos", name="read")),
        rules,
    )
    denied = evaluate_external_transport_policy(
        _request(command=CommandTuple(namespace="repos", name="write")),
        rules,
    )

    assert allowed.allowed is True
    assert allowed.code == "allowed"
    assert denied.allowed is False
    assert denied.code == "no_allow_rule"


def test_project_scope_mismatch_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(project_id="project-2"),
        [ExternalPolicyRule(effect="allow", project_id="project-1")],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_thread_scope_mismatch_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(thread_id="thread-2"),
        [ExternalPolicyRule(effect="allow", thread_id="thread-1")],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_exact_url_host_match_allows() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url="https://api.example.com/v1/repos"),
        [
            ExternalPolicyRule(
                effect="allow",
                url_host_pattern="api.example.com",
                url_scheme="https",
            )
        ],
    )

    assert decision.allowed is True
    assert decision.code == "allowed"


def test_url_scheme_mismatch_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url="http://api.example.com/v1/repos"),
        [
            ExternalPolicyRule(
                effect="allow",
                url_host_pattern="api.example.com",
                url_scheme="https",
            )
        ],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_wildcard_host_match_allows_subdomain() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url="https://api.example.com/resource"),
        [ExternalPolicyRule(effect="allow", url_host_pattern="*.example.com")],
    )

    assert decision.allowed is True
    assert decision.code == "allowed"


def test_wildcard_host_does_not_match_badexample_domain() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url="https://badexample.com/resource"),
        [ExternalPolicyRule(effect="allow", url_host_pattern="*.example.com")],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_malformed_url_denies() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url="http://[::1"),
        [ExternalPolicyRule(effect="allow", url_host_pattern="example.com")],
    )

    assert decision.allowed is False
    assert decision.code == "malformed_url"


def test_url_rule_does_not_match_when_request_has_no_url() -> None:
    decision = evaluate_external_transport_policy(
        _request(target_url=None),
        [ExternalPolicyRule(effect="allow", url_host_pattern="example.com")],
    )

    assert decision.allowed is False
    assert decision.code == "no_allow_rule"


def test_matched_decision_exposes_stable_rule_index() -> None:
    rules = [
        ExternalPolicyRule(effect="deny", connector_name="github"),
        ExternalPolicyRule(effect="allow", connector_name="github"),
        ExternalPolicyRule(effect="allow", connector_name="github"),
    ]

    denied = evaluate_external_transport_policy(_request(), rules)
    allowed = evaluate_external_transport_policy(
        _request(),
        rules[1:],
    )

    assert denied.allowed is False
    assert denied.code == "denied_by_rule"
    assert denied.matched_rule_index == 0
    assert allowed.allowed is True
    assert allowed.code == "allowed"
    assert allowed.matched_rule_index == 0
