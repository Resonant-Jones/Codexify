"""Deny-first policy evaluation for external connector transport requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence
from urllib.parse import urlsplit

ExternalTransport = Literal[
    "local",
    "http",
    "https",
    "stdio",
    "websocket",
    "mcp",
]

PolicyEffect = Literal["allow", "deny"]

SUPPORTED_TRANSPORTS: frozenset[str] = frozenset(
    {"local", "http", "https", "stdio", "websocket", "mcp"}
)


@dataclass(frozen=True)
class CommandTuple:
    namespace: str
    name: str


@dataclass(frozen=True)
class ExternalPolicyRequest:
    actor_id: str
    subject_id: str
    connector_name: str
    transport: ExternalTransport | str
    command: CommandTuple | None = None
    target_url: str | None = None
    project_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class ExternalPolicyRule:
    effect: PolicyEffect
    connector_name: str | None = None
    transport: ExternalTransport | str | None = None
    command: CommandTuple | None = None
    url_host_pattern: str | None = None
    url_scheme: str | None = None
    project_id: str | None = None
    thread_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class ExternalPolicyDecision:
    allowed: bool
    code: str
    reason: str
    matched_rule_index: int | None = None


@dataclass(frozen=True)
class _ParsedUrl:
    scheme: str
    hostname: str


def evaluate_external_transport_policy(
    request: ExternalPolicyRequest,
    rules: Sequence[ExternalPolicyRule],
) -> ExternalPolicyDecision:
    actor_id = request.actor_id.strip()
    if not actor_id:
        return _deny("missing_actor", "actor_id is required")

    subject_id = request.subject_id.strip()
    if not subject_id:
        return _deny("missing_subject", "subject_id is required")

    connector_name = request.connector_name.strip()
    if not connector_name:
        return _deny("missing_connector", "connector_name is required")

    transport = str(request.transport).strip()
    if not transport:
        return _deny("missing_transport", "transport is required")
    if transport not in SUPPORTED_TRANSPORTS:
        return _deny(
            "unsupported_transport",
            f"unsupported transport: {transport}",
        )

    parsed_url: _ParsedUrl | None = None
    if request.target_url is not None:
        parsed_url = _parse_target_url(request.target_url)
        if parsed_url is None:
            return _deny("malformed_url", "target_url is malformed")

    deny_match = _first_matching_rule(
        request=request,
        normalized_connector_name=connector_name,
        normalized_transport=transport,
        parsed_url=parsed_url,
        rules=rules,
        effect="deny",
    )
    if deny_match is not None:
        index, rule = deny_match
        return ExternalPolicyDecision(
            allowed=False,
            code="denied_by_rule",
            reason=rule.reason or "request denied by external transport policy",
            matched_rule_index=index,
        )

    allow_match = _first_matching_rule(
        request=request,
        normalized_connector_name=connector_name,
        normalized_transport=transport,
        parsed_url=parsed_url,
        rules=rules,
        effect="allow",
    )
    if allow_match is not None:
        index, rule = allow_match
        return ExternalPolicyDecision(
            allowed=True,
            code="allowed",
            reason=rule.reason
            or "request allowed by external transport policy",
            matched_rule_index=index,
        )

    return _deny("no_allow_rule", "no matching allow rule")


def _first_matching_rule(
    *,
    request: ExternalPolicyRequest,
    normalized_connector_name: str,
    normalized_transport: str,
    parsed_url: _ParsedUrl | None,
    rules: Sequence[ExternalPolicyRule],
    effect: PolicyEffect,
) -> tuple[int, ExternalPolicyRule] | None:
    for index, rule in enumerate(rules):
        if rule.effect != effect:
            continue
        if _rule_matches(
            request=request,
            rule=rule,
            normalized_connector_name=normalized_connector_name,
            normalized_transport=normalized_transport,
            parsed_url=parsed_url,
        ):
            return index, rule
    return None


def _rule_matches(
    *,
    request: ExternalPolicyRequest,
    rule: ExternalPolicyRule,
    normalized_connector_name: str,
    normalized_transport: str,
    parsed_url: _ParsedUrl | None,
) -> bool:
    if rule.connector_name is not None:
        if rule.connector_name != normalized_connector_name:
            return False

    if rule.transport is not None:
        if str(rule.transport).strip() != normalized_transport:
            return False

    if rule.command is not None:
        if request.command is None:
            return False
        if rule.command != request.command:
            return False

    if rule.project_id is not None and rule.project_id != request.project_id:
        return False

    if rule.thread_id is not None and rule.thread_id != request.thread_id:
        return False

    if rule.url_scheme is not None:
        if parsed_url is None:
            return False
        if rule.url_scheme.strip().lower() != parsed_url.scheme:
            return False

    if rule.url_host_pattern is not None:
        if parsed_url is None:
            return False
        if not _host_matches_pattern(
            hostname=parsed_url.hostname,
            pattern=rule.url_host_pattern,
        ):
            return False

    return True


def _parse_target_url(value: str) -> _ParsedUrl | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None

    scheme = parsed.scheme.strip().lower()
    hostname = (parsed.hostname or "").strip().lower()
    if not scheme or not hostname:
        return None
    return _ParsedUrl(scheme=scheme, hostname=hostname)


def _host_matches_pattern(*, hostname: str, pattern: str) -> bool:
    normalized_pattern = pattern.strip().lower()
    if not normalized_pattern:
        return False

    if normalized_pattern.startswith("*."):
        suffix = normalized_pattern[2:]
        if not suffix:
            return False
        # Require a dot boundary so "*.example.com" never matches
        # "badexample.com".
        return hostname.endswith(f".{suffix}")

    return hostname == normalized_pattern


def _deny(code: str, reason: str) -> ExternalPolicyDecision:
    return ExternalPolicyDecision(
        allowed=False,
        code=code,
        reason=reason,
        matched_rule_index=None,
    )
