"""Cross-language conformance for the Browser Host contract package.

The JSON manifest, schemas, token registry, and fixture index are the shared
wire source of truth. This test intentionally keeps its semantic checks narrow
and mirrors only the fail-closed rules that a non-JavaScript consumer needs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "browser_host" / "contracts"
MANIFEST = json.loads((CONTRACT_ROOT / "manifest.json").read_text(encoding="utf-8"))
TOKENS = json.loads(
    (CONTRACT_ROOT / MANIFEST["tokenRegistryPath"]).read_text(encoding="utf-8")
)
FIXTURE_INDEX = json.loads(
    (CONTRACT_ROOT / MANIFEST["fixtureIndexPath"]).read_text(encoding="utf-8")
)


def _load(relative_path: str) -> object:
    return json.loads((CONTRACT_ROOT / relative_path).read_text(encoding="utf-8"))


def _schema_validator(kind: str) -> Draft202012Validator:
    relative_path = MANIFEST["schemaPaths"][kind]
    schema_path = CONTRACT_ROOT / relative_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_store = {}
    for candidate_path in (CONTRACT_ROOT / "schemas").glob("*.json"):
        candidate_schema = json.loads(candidate_path.read_text(encoding="utf-8"))
        schema_store[candidate_schema["$id"]] = candidate_schema
        schema_store[candidate_path.name] = candidate_schema
    resolver = RefResolver(
        base_uri=f"{schema_path.parent.as_uri()}/",
        referrer=schema,
        store=schema_store,
    )
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _semantic_error_codes(kind: str, payload: dict) -> set[str]:
    codes: set[str] = set()

    if kind == "hello":
        if "1.0.0" not in payload.get("supportedProtocolVersions", []):
            codes.add("unsupported_protocol_version")
        if "1.0.0" not in payload.get("supportedEnvelopeVersions", []):
            codes.add("unsupported_envelope_version")
        if "1.0.0" not in payload.get("supportedAttachmentVersions", []):
            codes.add("unsupported_attachment_version")
        if any(feature not in TOKENS["featureIdentifiers"] for feature in payload.get("supportedFeatureTokens", [])):
            codes.add("undeclared_feature")

    if kind == "negotiation":
        if any(feature not in TOKENS["featureIdentifiers"] for feature in payload.get("enabledFeatures", [])):
            codes.add("undeclared_feature")
        selected = [
            payload.get("selectedProtocolVersion"),
            payload.get("selectedEnvelopeVersion"),
            payload.get("selectedAttachmentVersion"),
        ]
        if payload.get("compatibilityOutcome") == "incompatible" and any(value is not None for value in selected):
            codes.add("no_compatible_version")

    if kind == "envelope":
        forbidden = {
            "credential": "credential_field_forbidden",
            "credentials": "credential_field_forbidden",
            "apiKey": "credential_field_forbidden",
            "token": "credential_field_forbidden",
            "jwt": "credential_field_forbidden",
            "cookie": "cookie_field_forbidden",
            "cookies": "cookie_field_forbidden",
            "localStorage": "storage_field_forbidden",
            "sessionStorage": "storage_field_forbidden",
            "formValue": "form_value_field_forbidden",
            "formValues": "form_value_field_forbidden",
            "password": "form_value_field_forbidden",
            "hiddenInput": "form_value_field_forbidden",
            "nativeCommand": "native_command_field_forbidden",
            "commandGrant": "native_command_field_forbidden",
        }
        for field, code in forbidden.items():
            if field in payload:
                codes.add(code)
        if payload.get("userInitiated") is not True:
            codes.add("user_initiation_required")
        if payload.get("retentionClass") != "ephemeral":
            codes.add("retention_not_supported")
        if payload.get("captureMode") not in TOKENS["captureModes"]:
            codes.add("unknown_capture_mode")
        content = payload.get("content")
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > MANIFEST["commonCaptureSizeBudgetBytes"] or payload.get("contentLength", 0) > MANIFEST["commonCaptureSizeBudgetBytes"]:
                codes.add("payload_too_large")
            if payload.get("contentLength") != len(content_bytes):
                codes.add("content_length_mismatch")
            if payload.get("contentHash") != hashlib.sha256(content_bytes).hexdigest():
                codes.add("content_hash_mismatch")
        allowed = {
            "schemaVersion", "contextId", "captureRequestId", "sourceKind", "sourceUrl", "sourceOrigin",
            "sourceTitle", "capturedAt", "captureMode", "contentType", "content", "contentHash",
            "contentLength", "originalContentLength", "truncated", "extractorVersion", "permissionScope",
            "retentionClass", "userInitiated", "requestId", "attemptNumber", "sanitizationEvidence",
            "documentGeneration", "documentFingerprint",
        }
        if any(key not in allowed for key in payload):
            codes.add("unexpected_property")

    if kind == "attachment":
        confirmation = payload.get("userConfirmation")
        if not isinstance(confirmation, dict) or confirmation.get("confirmed") is not True:
            codes.add("user_confirmation_required")

    if kind == "attachmentGrantRequest":
        forbidden = {
            "apiKey": "credential_field_forbidden",
            "cookie": "cookie_field_forbidden",
            "cookies": "cookie_field_forbidden",
            "jwt": "credential_field_forbidden",
            "password": "form_value_field_forbidden",
        }
        for field, code in forbidden.items():
            if field in payload:
                codes.add(code)
        allowed = {
            "schemaVersion", "protocolVersion", "attachmentVersion", "requestId",
            "browserHostInstanceId", "requestedRetention", "requestedAttachmentCount",
            "requestedMaxContentBytes", "requestedTtlSeconds", "userConfirmationMode",
            "generatedAt",
        }
        if any(key not in allowed for key in payload):
            codes.add("unexpected_property")
        if payload.get("protocolVersion") != "1.0.0" or payload.get("attachmentVersion") != "1.0.0":
            codes.add("attachment_grant_version_mismatch")
        if payload.get("requestedRetention") != "ephemeral":
            codes.add("attachment_grant_retention_denied")
        if payload.get("requestedAttachmentCount") != 1:
            codes.add("attachment_grant_invalid")
        if not isinstance(payload.get("requestedMaxContentBytes"), int) or not 1 <= payload.get("requestedMaxContentBytes", 0) <= MANIFEST["commonCaptureSizeBudgetBytes"]:
            codes.add("attachment_grant_budget_exceeded")
        if not isinstance(payload.get("requestedTtlSeconds"), int) or not 30 <= payload.get("requestedTtlSeconds", 0) <= 300:
            codes.add("attachment_grant_invalid")
        if payload.get("userConfirmationMode") != "explicit_each_attachment":
            codes.add("attachment_grant_confirmation_required")

    if kind == "attachmentGrant":
        forbidden = {
            "apiKey": "credential_field_forbidden",
            "cookie": "cookie_field_forbidden",
            "cookies": "cookie_field_forbidden",
            "jwt": "credential_field_forbidden",
            "password": "form_value_field_forbidden",
        }
        for field, code in forbidden.items():
            if field in payload:
                codes.add(code)
        allowed = {
            "schemaVersion", "grantId", "authorizationScheme", "grantBearer",
            "protocolVersion", "attachmentVersion", "browserHostInstanceId", "requestId",
            "retentionClass", "maxContentBytes", "remainingUses", "issuedAt", "expiresAt",
        }
        if any(key not in allowed for key in payload):
            codes.add("unexpected_property")
        if payload.get("protocolVersion") != "1.0.0" or payload.get("attachmentVersion") != "1.0.0":
            codes.add("attachment_grant_version_mismatch")
        if payload.get("authorizationScheme") not in TOKENS.get("authorizationSchemes", []):
            codes.add("attachment_grant_invalid")
        if payload.get("retentionClass") != "ephemeral":
            codes.add("attachment_grant_retention_denied")
        if not isinstance(payload.get("maxContentBytes"), int) or not 1 <= payload.get("maxContentBytes", 0) <= MANIFEST["commonCaptureSizeBudgetBytes"]:
            codes.add("attachment_grant_budget_exceeded")
        if payload.get("remainingUses") != 1:
            codes.add("attachment_grant_invalid")
        issued = payload.get("issuedAt")
        expires = payload.get("expiresAt")
        try:
            if issued and expires and expires <= issued:
                codes.add("attachment_grant_invalid")
        except TypeError:
            pass

    if kind == "receipt":
        if "content" in payload:
            codes.add("attachment_content_echo_forbidden")
        if payload.get("errorCode") is not None and payload.get("errorCode") not in TOKENS["errorCodes"]:
            codes.add("unknown_error_code")

    if kind == "error" and payload.get("errorCode") not in TOKENS["errorCodes"]:
        codes.add("unknown_error_code")

    return codes


def test_every_contract_json_file_parses_and_manifest_paths_exist() -> None:
    json_files = sorted(CONTRACT_ROOT.rglob("*.json"))
    assert json_files
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))

    declared_paths = [
        *MANIFEST["schemaPaths"].values(),
        MANIFEST["tokenRegistryPath"],
        MANIFEST["fixtureIndexPath"],
        *MANIFEST["positiveFixturePaths"],
        *MANIFEST["negativeFixturePaths"],
    ]
    for relative_path in declared_paths:
        assert (CONTRACT_ROOT / relative_path).is_file(), relative_path


def test_manifest_versions_and_fixture_index_are_consistent() -> None:
    assert MANIFEST["contractPackageName"] == "@codexify/browser-host-contracts"
    assert MANIFEST["contractPackageVersion"] == "0.2.0"
    assert MANIFEST["protocol"] == {
        "currentVersion": "1.0.0",
        "minimumCompatibleVersion": "1.0.0",
        "maximumCompatibleVersion": "1.0.0",
        "failClosed": True,
    }
    assert MANIFEST["browserContextEnvelope"]["supportedVersions"] == ["1.0.0"]
    assert MANIFEST["contextAttachment"]["supportedVersions"] == ["1.0.0"]
    assert MANIFEST["hashAlgorithm"] == "sha256"
    assert MANIFEST["commonCaptureSizeBudgetBytes"] == 64 * 1024
    indexed_valid = {entry["path"] for entry in FIXTURE_INDEX["fixtures"] if entry["valid"]}
    indexed_invalid = {entry["path"] for entry in FIXTURE_INDEX["fixtures"] if not entry["valid"]}
    assert {f"fixtures/{path}" for path in indexed_valid} == set(MANIFEST["positiveFixturePaths"])
    assert {f"fixtures/{path}" for path in indexed_invalid} == set(MANIFEST["negativeFixturePaths"])
    assert MANIFEST["attachmentGrant"] == {
        "requestSchema": "schemas/browser-host-attachment-grant-request.v1.schema.json",
        "responseSchema": "schemas/browser-host-attachment-grant.v1.schema.json",
        "supportedAuthorizationSchemes": ["browser_host_attachment_grant"],
        "defaultTtlSeconds": 120,
        "minimumTtlSeconds": 30,
        "maximumTtlSeconds": 300,
        "allowedUses": 1,
        "retentionClass": "ephemeral",
        "authorizationMaterial": True,
        "reusableGuardianCredential": False,
    }
    assert len(FIXTURE_INDEX["fixtures"]) == 50


def test_token_domains_are_bounded_and_non_duplicate() -> None:
    for key, values in TOKENS.items():
        if isinstance(values, list):
            assert len(values) == len(set(values)), key
    assert set(TOKENS["captureModes"]) == {"selected_text", "visible_page_text"}
    assert TOKENS["retentionClasses"] == ["ephemeral"]
    assert TOKENS["persistenceOutcomes"] == ["not_persisted"]
    assert TOKENS["authorizationSchemes"] == ["browser_host_attachment_grant"]
    assert TOKENS["grantLifecycle"] == ["grant_issued", "grant_consumed", "grant_rejected", "grant_expired", "grant_replayed"]
    assert {
        "attachment_grant_required", "attachment_grant_invalid", "attachment_grant_expired",
        "attachment_grant_consumed", "attachment_grant_scope_mismatch", "attachment_grant_version_mismatch",
        "attachment_grant_retention_denied", "attachment_grant_budget_exceeded", "attachment_grant_confirmation_required",
    }.issubset(TOKENS["errorCodes"])


def test_grant_schemas_exclude_identity_and_reusable_credential_fields() -> None:
    for kind in ("attachmentGrantRequest", "attachmentGrant"):
        schema = _load(MANIFEST["schemaPaths"][kind])
        properties = set(schema["properties"])
        assert not properties.intersection({
            "userId", "accountId", "email", "role", "subjectId", "apiKey",
            "cookie", "cookies", "jwt", "password", "envelope", "attachment",
            "pageUrl", "pageTitle", "localStorage", "sessionStorage", "nativeCommand",
        })
        assert schema["additionalProperties"] is False


@pytest.mark.parametrize("entry", FIXTURE_INDEX["fixtures"], ids=lambda item: item["id"])
def test_shared_fixture_validity_and_expected_error(entry: dict) -> None:
    payload = _load(f"fixtures/{entry['path']}")
    validator = _schema_validator(entry["kind"])
    schema_errors = list(validator.iter_errors(payload))
    semantic_errors = _semantic_error_codes(entry["kind"], payload)
    if entry["valid"]:
        assert schema_errors == [], [error.message for error in schema_errors]
        assert semantic_errors == set(), semantic_errors
    else:
        assert schema_errors or semantic_errors
        assert entry["expectedError"] in semantic_errors or any(
            entry["expectedError"] in error.message for error in schema_errors
        ), (entry["id"], semantic_errors, [error.message for error in schema_errors])


def test_python_reads_the_same_wire_fields_without_runtime_authority() -> None:
    envelope = _load("fixtures/valid/envelope-selected-text.json")
    assert envelope["userInitiated"] is True
    assert envelope["retentionClass"] == "ephemeral"
    assert envelope["requestId"] != envelope["captureRequestId"]
    assert set(envelope["sanitizationEvidence"]) == {
        "formControlValuesExcluded", "passwordValuesExcluded", "hiddenInputValuesExcluded",
        "cookiesExcluded", "localStorageExcluded", "sessionStorageExcluded",
        "scriptsAndStylesExcluded", "crossOriginIframeContentExcluded",
    }
    receipt = _load("fixtures/valid/attachment-receipt-no-persistence.json")
    assert receipt["attachmentOutcome"] == "accepted"
    assert receipt["persistenceOutcome"] == "not_persisted"
    assert "content" not in receipt
    assert "credential" not in envelope
    assert "cookie" not in envelope
    assert "localStorage" not in envelope
    assert "nativeCommand" not in envelope
