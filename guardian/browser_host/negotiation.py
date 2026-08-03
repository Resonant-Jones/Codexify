"""Pure Guardian-owned Browser Host compatibility negotiation.

The policy deliberately has no authentication, persistence, provider, queue, or
attachment dependencies.  It consumes the versioned Browser Host contract and
returns only the bounded Negotiation v1 wire object.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import re
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from guardian.browser_host.contract_loader import (
    BrowserHostContractMetadata,
    load_contract_metadata,
)


CONTRACT_ID = "guardian-browser-host-contract"
CONTRACT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"


def _wire_timestamp(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


@lru_cache(maxsize=1)
def _contract() -> BrowserHostContractMetadata:
    return load_contract_metadata()


@lru_cache(maxsize=1)
def _hello_validator() -> Draft202012Validator:
    metadata = _contract()
    schema = metadata.schemas["hello"]
    store: dict[str, Mapping[str, Any]] = {}
    for candidate in metadata.schemas.values():
        identifier = candidate.get("$id")
        if isinstance(identifier, str):
            store[identifier] = candidate
            store[identifier.rsplit("/", 1)[-1]] = candidate
    return Draft202012Validator(
        schema,
        resolver=RefResolver(
            base_uri="https://codexify.local/contracts/",
            referrer=schema,
            store=store,
        ),
        format_checker=FormatChecker(),
    )


def validate_browser_host_hello(hello: Any) -> bool:
    """Validate shape and the shared semantic v1 compatibility requirements."""

    if not validate_browser_host_hello_request(hello):
        return False
    return (
        "1.0.0" in hello["supportedProtocolVersions"]
        and "1.0.0" in hello["supportedEnvelopeVersions"]
        and "1.0.0" in hello["supportedAttachmentVersions"]
        and all(
            feature in _contract().manifest["featureTokens"]
            for feature in hello["supportedFeatureTokens"]
        )
    )


_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]+$")


def validate_browser_host_hello_request(hello: Any) -> bool:
    """Validate the closed request shape while permitting incompatible versions.

    The v1 JSON schema intentionally advertises the currently supported
    envelope and attachment versions as constants.  Negotiation still needs to
    receive a well-formed future-version hello in order to return a valid
    incompatible result, so the request boundary applies the same closed
    fields and scalar constraints without narrowing those three arrays.
    """

    if not isinstance(hello, Mapping):
        return False
    required = {
        "schemaVersion", "componentVersion", "supportedProtocolVersions",
        "supportedEnvelopeVersions", "supportedAttachmentVersions",
        "supportedFeatureTokens", "platform", "architecture",
        "requestCorrelationId", "generatedAt",
    }
    if set(hello) != required or hello.get("schemaVersion") != SCHEMA_VERSION:
        return False
    if not isinstance(hello.get("componentVersion"), str) or not _SEMVER.fullmatch(hello["componentVersion"]):
        return False
    for field in (
        "supportedProtocolVersions", "supportedEnvelopeVersions",
        "supportedAttachmentVersions",
    ):
        versions = hello.get(field)
        if not isinstance(versions, list) or not versions:
            return False
        if any(not isinstance(version, str) or not _SEMVER.fullmatch(version) for version in versions):
            return False
        if len(versions) != len(set(versions)):
            return False
    features = hello.get("supportedFeatureTokens")
    if not isinstance(features, list) or any(not isinstance(feature, str) for feature in features):
        return False
    if len(features) != len(set(features)):
        return False
    if any(feature not in _contract().manifest["featureTokens"] for feature in features):
        return False
    for field in ("platform", "architecture"):
        value = hello.get(field)
        if not isinstance(value, str) or not value or len(value) > 64 or not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            return False
    request_id = hello.get("requestCorrelationId")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 256 or not _IDENTIFIER.fullmatch(request_id):
        return False
    if not isinstance(hello.get("generatedAt"), str):
        return False
    try:
        parsed = datetime.fromisoformat(hello["generatedAt"].replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    # Reuse the canonical closed Hello schema for every non-version field.
    # Its v1 constants intentionally reject future envelope/attachment values,
    # so normalize only the version arrays after the bounded shape checks above;
    # the policy still evaluates the caller's original arrays for compatibility.
    canonical_shape = dict(hello)
    for field in (
        "supportedProtocolVersions", "supportedEnvelopeVersions",
        "supportedAttachmentVersions",
    ):
        canonical_shape[field] = [SCHEMA_VERSION]
    return _hello_validator().is_valid(canonical_shape)


@dataclass(frozen=True)
class BrowserHostNegotiationPolicy:
    """Immutable supported-version and feature policy for one Guardian app."""

    supported_protocol_versions: tuple[str, ...]
    supported_envelope_versions: tuple[str, ...]
    supported_attachment_versions: tuple[str, ...]
    allowed_feature_tokens: tuple[str, ...]
    contract_id: str = CONTRACT_ID
    contract_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class BrowserHostNegotiationDecision:
    """A bounded decision plus its canonical Negotiation v1 representation."""

    response: Mapping[str, Any]
    compatible: bool
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.response)

    def __getitem__(self, key: str) -> Any:
        return self.response[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.response.get(key, default)


def build_default_negotiation_policy(
    metadata: BrowserHostContractMetadata | None = None,
) -> BrowserHostNegotiationPolicy:
    contract = metadata or _contract()
    manifest = contract.manifest
    return BrowserHostNegotiationPolicy(
        supported_protocol_versions=(manifest["protocol"]["currentVersion"],),
        supported_envelope_versions=(
            manifest["browserContextEnvelope"]["currentVersion"],
        ),
        supported_attachment_versions=(manifest["contextAttachment"]["currentVersion"],),
        allowed_feature_tokens=tuple(manifest["featureTokens"]),
    )


def _selected(caller: Any, supported: tuple[str, ...]) -> str | None:
    # The contract currently has one version, but this preserves the declared
    # caller order while making policy order the deterministic tie breaker.
    return next((version for version in supported if version in caller), None)


def _decision_response(
    hello: Mapping[str, Any],
    policy: BrowserHostNegotiationPolicy,
) -> BrowserHostNegotiationDecision:
    protocol = _selected(
        hello["supportedProtocolVersions"], policy.supported_protocol_versions
    )
    envelope = _selected(
        hello["supportedEnvelopeVersions"], policy.supported_envelope_versions
    )
    attachment = _selected(
        hello["supportedAttachmentVersions"], policy.supported_attachment_versions
    )
    compatible = protocol is not None and envelope is not None and attachment is not None

    if not compatible:
        if protocol is None:
            error_code = "unsupported_protocol_version"
        elif envelope is None:
            error_code = "unsupported_envelope_version"
        elif attachment is None:
            error_code = "unsupported_attachment_version"
        else:  # pragma: no cover - defensive, the compatibility predicate is total.
            error_code = "no_compatible_version"
    else:
        error_code = None

    declared = set(hello["supportedFeatureTokens"])
    canonical_features = tuple(_contract().manifest["featureTokens"])
    enabled: list[str] = []
    disabled: list[dict[str, str]] = []
    for feature in canonical_features:
        if not compatible:
            disabled.append({"feature": feature, "reason": "incompatible_version"})
        elif feature not in declared:
            disabled.append({"feature": feature, "reason": "undeclared_feature"})
        elif feature not in policy.allowed_feature_tokens:
            disabled.append({"feature": feature, "reason": "not_supported"})
        else:
            enabled.append(feature)

    response = {
        "schemaVersion": SCHEMA_VERSION,
        "requestCorrelationId": hello["requestCorrelationId"],
        "compatibilityOutcome": "compatible" if compatible else "incompatible",
        "selectedProtocolVersion": protocol if compatible else None,
        "selectedEnvelopeVersion": envelope if compatible else None,
        "selectedAttachmentVersion": attachment if compatible else None,
        "enabledFeatures": enabled,
        "disabledFeatures": disabled,
        "errorCode": error_code,
        "guardianContractId": policy.contract_id,
        "guardianContractVersion": policy.contract_version,
        # Reusing the validated caller timestamp keeps identical hello/policy
        # inputs deterministic without adding a second time source to policy.
        "generatedAt": _wire_timestamp(hello.get("generatedAt")),
    }
    return BrowserHostNegotiationDecision(response, compatible, error_code)


def negotiate_browser_host_hello(
    hello: Mapping[str, Any],
    policy: BrowserHostNegotiationPolicy | None = None,
) -> BrowserHostNegotiationDecision:
    """Validate and negotiate a Browser Host Hello v1 payload."""

    if not validate_browser_host_hello_request(hello):
        raise ValueError("browser_host_hello_invalid")
    decision = _decision_response(hello, policy or build_default_negotiation_policy())
    validator = Draft202012Validator(
        _contract().schemas["negotiation"], format_checker=FormatChecker()
    )
    if not validator.is_valid(decision.response):
        raise RuntimeError("browser_host_negotiation_contract_invalid")
    return decision


__all__ = [
    "BrowserHostNegotiationDecision",
    "BrowserHostNegotiationPolicy",
    "build_default_negotiation_policy",
    "negotiate_browser_host_hello",
    "validate_browser_host_hello",
    "validate_browser_host_hello_request",
]
