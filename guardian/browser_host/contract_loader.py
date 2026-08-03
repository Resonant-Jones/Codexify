"""Load the canonical Browser Host contract without creating a second registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class ContractLoadError(RuntimeError):
    """Raised when the shared Browser Host contract cannot be loaded safely."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractLoadError("browser_host_contract_unavailable") from exc
    if not isinstance(value, dict):
        raise ContractLoadError("browser_host_contract_invalid")
    return value


@dataclass(frozen=True)
class BrowserHostContractMetadata:
    """Immutable, bounded metadata needed by the pure grant seam."""

    root: Path
    manifest: Mapping[str, Any]
    tokens: Mapping[str, Any]
    schemas: Mapping[str, Mapping[str, Any]]
    package_name: str
    package_version: str
    protocol_version: str
    envelope_version: str
    attachment_version: str
    max_capture_bytes: int
    authorization_scheme: str
    retention_class: str
    default_ttl_seconds: int
    minimum_ttl_seconds: int
    maximum_ttl_seconds: int
    allowed_uses: int
    authorization_material: bool
    reusable_guardian_credential: bool

    @property
    def grant_error_codes(self) -> tuple[str, ...]:
        return tuple(
            token
            for token in self.tokens["errorCodes"]
            if token.startswith("attachment_grant_")
        )

    @property
    def authorization_schemes(self) -> tuple[str, ...]:
        return tuple(self.tokens["authorizationSchemes"])

    @property
    def grant_lifecycle(self) -> tuple[str, ...]:
        return tuple(self.tokens["grantLifecycle"])


def _default_contract_root() -> Path:
    return Path(__file__).resolve().parents[2] / "browser_host" / "contracts"


def load_contract_metadata(contract_root: Path | str | None = None) -> BrowserHostContractMetadata:
    """Load and fail closed on the versioned Browser Host contract package."""

    root = Path(contract_root) if contract_root is not None else _default_contract_root()
    package = _read_json(root / "package.json")
    manifest = _read_json(root / "manifest.json")
    token_path = manifest.get("tokenRegistryPath")
    fixture_index_path = manifest.get("fixtureIndexPath")
    if not isinstance(token_path, str) or not isinstance(fixture_index_path, str):
        raise ContractLoadError("browser_host_contract_paths_missing")
    tokens = _read_json(root / token_path)
    _read_json(root / fixture_index_path)

    required_manifest = {
        "contractPackageName", "contractPackageVersion", "protocol",
        "browserContextEnvelope", "contextAttachment", "schemaPaths",
        "commonCaptureSizeBudgetBytes", "attachmentGrant",
    }
    if not required_manifest.issubset(manifest):
        raise ContractLoadError("browser_host_contract_manifest_incomplete")
    if package.get("name") != manifest["contractPackageName"]:
        raise ContractLoadError("browser_host_contract_package_mismatch")
    if package.get("version") != manifest["contractPackageVersion"]:
        raise ContractLoadError("browser_host_contract_version_mismatch")

    protocol = manifest["protocol"]
    envelope = manifest["browserContextEnvelope"]
    attachment = manifest["contextAttachment"]
    grant = manifest["attachmentGrant"]
    if not isinstance(protocol, dict) or not isinstance(envelope, dict) or not isinstance(attachment, dict) or not isinstance(grant, dict):
        raise ContractLoadError("browser_host_contract_versions_invalid")
    if protocol.get("currentVersion") != "1.0.0" or envelope.get("currentVersion") != "1.0.0" or attachment.get("currentVersion") != "1.0.0":
        raise ContractLoadError("browser_host_contract_versions_unsupported")
    if manifest.get("commonCaptureSizeBudgetBytes") != 65536:
        raise ContractLoadError("browser_host_contract_budget_changed")

    required_grant = {
        "requestSchema", "responseSchema", "supportedAuthorizationSchemes",
        "defaultTtlSeconds", "minimumTtlSeconds", "maximumTtlSeconds",
        "allowedUses", "retentionClass", "authorizationMaterial",
        "reusableGuardianCredential",
    }
    if not required_grant.issubset(grant):
        raise ContractLoadError("browser_host_grant_manifest_incomplete")
    if grant["supportedAuthorizationSchemes"] != ["browser_host_attachment_grant"]:
        raise ContractLoadError("browser_host_grant_scheme_invalid")
    if grant["retentionClass"] != "ephemeral" or grant["allowedUses"] != 1:
        raise ContractLoadError("browser_host_grant_lifecycle_invalid")
    if not (30 <= grant["minimumTtlSeconds"] <= grant["defaultTtlSeconds"] <= grant["maximumTtlSeconds"] <= 300):
        raise ContractLoadError("browser_host_grant_ttl_invalid")
    if grant["authorizationMaterial"] is not True or grant["reusableGuardianCredential"] is not False:
        raise ContractLoadError("browser_host_grant_authority_posture_invalid")

    schema_paths = manifest["schemaPaths"]
    if not isinstance(schema_paths, dict):
        raise ContractLoadError("browser_host_contract_schema_paths_invalid")
    expected_schema_names = {
        "attachmentGrantRequest": grant["requestSchema"],
        "attachmentGrant": grant["responseSchema"],
    }
    for key, expected_path in expected_schema_names.items():
        if schema_paths.get(key) != expected_path:
            raise ContractLoadError("browser_host_grant_schema_path_mismatch")
    schemas: dict[str, Mapping[str, Any]] = {}
    for kind, relative_path in schema_paths.items():
        if not isinstance(relative_path, str):
            raise ContractLoadError("browser_host_contract_schema_path_invalid")
        schema = _read_json(root / relative_path)
        if schema.get("additionalProperties") is not False:
            raise ContractLoadError("browser_host_contract_schema_not_closed")
        schemas[kind] = _freeze(schema)

    required_token_lists = ("authorizationSchemes", "grantLifecycle", "errorCodes")
    if any(not isinstance(tokens.get(key), list) for key in required_token_lists):
        raise ContractLoadError("browser_host_grant_tokens_missing")
    if len(tokens["authorizationSchemes"]) != len(set(tokens["authorizationSchemes"])) or len(tokens["grantLifecycle"]) != len(set(tokens["grantLifecycle"])) or len(tokens["errorCodes"]) != len(set(tokens["errorCodes"])):
        raise ContractLoadError("browser_host_contract_duplicate_token")
    required_errors = {
        "attachment_grant_required", "attachment_grant_invalid", "attachment_grant_expired",
        "attachment_grant_consumed", "attachment_grant_scope_mismatch", "attachment_grant_version_mismatch",
        "attachment_grant_retention_denied", "attachment_grant_budget_exceeded", "attachment_grant_confirmation_required",
    }
    if not required_errors.issubset(set(tokens["errorCodes"])):
        raise ContractLoadError("browser_host_grant_error_tokens_missing")

    frozen_manifest = _freeze(manifest)
    frozen_tokens = _freeze(tokens)
    return BrowserHostContractMetadata(
        root=root,
        manifest=frozen_manifest,
        tokens=frozen_tokens,
        schemas=MappingProxyType(schemas),
        package_name=package["name"],
        package_version=package["version"],
        protocol_version=protocol["currentVersion"],
        envelope_version=envelope["currentVersion"],
        attachment_version=attachment["currentVersion"],
        max_capture_bytes=manifest["commonCaptureSizeBudgetBytes"],
        authorization_scheme=grant["supportedAuthorizationSchemes"][0],
        retention_class=grant["retentionClass"],
        default_ttl_seconds=grant["defaultTtlSeconds"],
        minimum_ttl_seconds=grant["minimumTtlSeconds"],
        maximum_ttl_seconds=grant["maximumTtlSeconds"],
        allowed_uses=grant["allowedUses"],
        authorization_material=grant["authorizationMaterial"],
        reusable_guardian_credential=grant["reusableGuardianCredential"],
    )
