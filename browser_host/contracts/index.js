"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const CONTRACT_ROOT = __dirname;

function readJson(relativePath) {
  const absolutePath = path.join(CONTRACT_ROOT, relativePath);
  return JSON.parse(fs.readFileSync(absolutePath, "utf8"));
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

const manifest = readJson("manifest.json");
const tokens = readJson(manifest.tokenRegistryPath);
const schemas = Object.fromEntries(
  Object.entries(manifest.schemaPaths).map(([kind, relativePath]) => [kind, readJson(relativePath)])
);
const fixtureIndex = readJson(manifest.fixtureIndexPath);
const MAX_CAPTURE_BYTES = manifest.commonCaptureSizeBudgetBytes;
const GRANT_REQUEST_KEYS = [
  "schemaVersion", "protocolVersion", "attachmentVersion", "requestId",
  "browserHostInstanceId", "requestedRetention", "requestedAttachmentCount",
  "requestedMaxContentBytes", "requestedTtlSeconds", "userConfirmationMode",
  "generatedAt"
];
const GRANT_RESPONSE_KEYS = [
  "schemaVersion", "grantId", "authorizationScheme", "grantBearer",
  "protocolVersion", "attachmentVersion", "browserHostInstanceId", "requestId",
  "retentionClass", "maxContentBytes", "remainingUses", "issuedAt", "expiresAt"
];
const GRANT_TOKEN_DOMAINS = Object.freeze({
  authorizationSchemes: tokens.authorizationSchemes,
  grantLifecycle: tokens.grantLifecycle,
  grantErrorCodes: tokens.errorCodes.filter((token) => token.startsWith("attachment_grant_"))
});

const ENVELOPE_KEYS = [
  "schemaVersion", "contextId", "captureRequestId", "sourceKind", "sourceUrl",
  "sourceOrigin", "sourceTitle", "capturedAt", "captureMode", "contentType",
  "content", "contentHash", "contentLength", "originalContentLength", "truncated",
  "extractorVersion", "permissionScope", "retentionClass", "userInitiated", "requestId",
  "attemptNumber", "sanitizationEvidence", "documentGeneration", "documentFingerprint"
];

const FORBIDDEN_FIELD_CODES = new Map([
  ["credential", "credential_field_forbidden"],
  ["credentials", "credential_field_forbidden"],
  ["apiKey", "credential_field_forbidden"],
  ["token", "credential_field_forbidden"],
  ["jwt", "credential_field_forbidden"],
  ["cookie", "cookie_field_forbidden"],
  ["cookies", "cookie_field_forbidden"],
  ["localStorage", "storage_field_forbidden"],
  ["sessionStorage", "storage_field_forbidden"],
  ["formValue", "form_value_field_forbidden"],
  ["formValues", "form_value_field_forbidden"],
  ["password", "form_value_field_forbidden"],
  ["hiddenInput", "form_value_field_forbidden"],
  ["nativeCommand", "native_command_field_forbidden"],
  ["commandGrant", "native_command_field_forbidden"],
  ["content", "attachment_content_echo_forbidden"],
  ["persistenceAuthority", "invalid_contract"]
]);

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function addError(errors, code, field, message) {
  errors.push({ code, field, message });
}

function hasOwn(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function checkObject(value, errors, field) {
  if (!isObject(value)) {
    addError(errors, "invalid_contract", field, `${field} must be an object`);
    return false;
  }
  return true;
}

function checkExactKeys(value, allowed, errors) {
  if (!isObject(value)) return;
  const allowedSet = new Set(allowed);
  for (const key of Object.keys(value)) {
    if (allowedSet.has(key)) continue;
    const forbiddenCode = FORBIDDEN_FIELD_CODES.get(key);
    addError(errors, forbiddenCode || "unexpected_property", key, `unexpected field: ${key}`);
  }
}

function checkRequired(value, required, errors) {
  if (!isObject(value)) return;
  for (const key of required) {
    if (!hasOwn(value, key)) addError(errors, "invalid_contract", key, `missing required field: ${key}`);
  }
}

function checkId(value, field, errors) {
  if (typeof value !== "string" || !/^[A-Za-z0-9._:-]+$/.test(value) || value.length === 0) {
    addError(errors, "invalid_contract", field, `${field} must be a bounded identifier`);
  }
}

function checkVersion(value, field, errors, expected = "1.0.0") {
  if (value !== expected) addError(errors, "invalid_contract", field, `${field} must be ${expected}`);
}

function checkGrantVersion(value, field, errors) {
  if (value !== "1.0.0") addError(errors, "attachment_grant_version_mismatch", field, `${field} is not supported by the grant contract`);
}

function checkTimestamp(value, field, errors) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) || Number.isNaN(Date.parse(value))) {
    addError(errors, "invalid_contract", field, `${field} must be an RFC3339 UTC timestamp`);
  }
}

function checkEnum(value, field, values, errors, code = "invalid_contract") {
  if (!values.includes(value)) addError(errors, code, field, `${field} is not a canonical token`);
}

function checkString(value, field, errors, maxLength = Infinity) {
  if (typeof value !== "string" || value.length === 0 || value.length > maxLength) {
    addError(errors, "invalid_contract", field, `${field} must be a bounded string`);
  }
}

function checkUniqueStrings(value, field, allowed, errors) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string") || new Set(value).size !== value.length) {
    addError(errors, "invalid_contract", field, `${field} must be a unique string array`);
    return;
  }
  for (const item of value) {
    if (!allowed.includes(item)) addError(errors, "undeclared_feature", `${field}.${item}`, `${item} is not declared`);
  }
}

function validateHello(value) {
  const errors = [];
  const required = [
    "schemaVersion", "componentVersion", "supportedProtocolVersions", "supportedEnvelopeVersions",
    "supportedAttachmentVersions", "supportedFeatureTokens", "platform", "architecture",
    "requestCorrelationId", "generatedAt"
  ];
  if (!checkObject(value, errors, "hello")) return errors;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkString(value.componentVersion, "componentVersion", errors, 32);
  checkUniqueStrings(value.supportedFeatureTokens, "supportedFeatureTokens", tokens.featureIdentifiers, errors);
  for (const [field, code] of [
    ["supportedProtocolVersions", "unsupported_protocol_version"],
    ["supportedEnvelopeVersions", "unsupported_envelope_version"],
    ["supportedAttachmentVersions", "unsupported_attachment_version"]
  ]) {
    if (!Array.isArray(value[field]) || !value[field].includes("1.0.0")) addError(errors, code, field, `${field} does not advertise 1.0.0`);
  }
  checkString(value.platform, "platform", errors, 64);
  checkString(value.architecture, "architecture", errors, 64);
  checkId(value.requestCorrelationId, "requestCorrelationId", errors);
  checkTimestamp(value.generatedAt, "generatedAt", errors);
  return errors;
}

function validateNegotiation(value) {
  const errors = [];
  const required = [
    "schemaVersion", "requestCorrelationId", "compatibilityOutcome", "selectedProtocolVersion",
    "selectedEnvelopeVersion", "selectedAttachmentVersion", "enabledFeatures", "disabledFeatures",
    "errorCode", "guardianContractId", "guardianContractVersion", "generatedAt"
  ];
  if (!checkObject(value, errors, "negotiation")) return errors;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkId(value.requestCorrelationId, "requestCorrelationId", errors);
  checkEnum(value.compatibilityOutcome, "compatibilityOutcome", tokens.compatibilityOutcomes, errors);
  checkUniqueStrings(value.enabledFeatures, "enabledFeatures", tokens.featureIdentifiers, errors);
  if (!Array.isArray(value.disabledFeatures)) addError(errors, "invalid_contract", "disabledFeatures", "disabledFeatures must be an array");
  else {
    for (const disabled of value.disabledFeatures) {
      if (!checkObject(disabled, errors, "disabledFeatures")) continue;
      checkExactKeys(disabled, ["feature", "reason"], errors);
      checkRequired(disabled, ["feature", "reason"], errors);
      checkEnum(disabled.feature, "disabledFeatures.feature", tokens.featureIdentifiers, errors, "undeclared_feature");
      checkEnum(disabled.reason, "disabledFeatures.reason", tokens.disabledFeatureReasons, errors);
    }
  }
  const selected = [value.selectedProtocolVersion, value.selectedEnvelopeVersion, value.selectedAttachmentVersion];
  if (value.compatibilityOutcome === "compatible") {
    if (selected.some((item) => item !== "1.0.0")) addError(errors, "no_compatible_version", "selectedVersions", "compatible negotiation must select every v1 transport version");
    if (value.errorCode !== null) addError(errors, "invalid_contract", "errorCode", "compatible negotiation cannot carry an error code");
  } else {
    if (selected.some((item) => item !== null)) addError(errors, "no_compatible_version", "selectedVersions", "incompatible negotiation must select no transport version");
    if (!tokens.errorCodes.includes(value.errorCode)) addError(errors, "invalid_contract", "errorCode", "incompatible negotiation needs a canonical error code");
  }
  if (value.guardianContractId !== "guardian-browser-host-contract") addError(errors, "invalid_contract", "guardianContractId", "unexpected Guardian contract identity");
  checkVersion(value.guardianContractVersion, "guardianContractVersion", errors);
  checkTimestamp(value.generatedAt, "generatedAt", errors);
  return errors;
}

function validateSanitization(value, errors) {
  const required = [
    "formControlValuesExcluded", "passwordValuesExcluded", "hiddenInputValuesExcluded",
    "cookiesExcluded", "localStorageExcluded", "sessionStorageExcluded",
    "scriptsAndStylesExcluded", "crossOriginIframeContentExcluded"
  ];
  if (!checkObject(value, errors, "sanitizationEvidence")) return;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  for (const key of required) if (value[key] !== true) addError(errors, "invalid_contract", `sanitizationEvidence.${key}`, `${key} must be true`);
}

function validateEnvelope(value) {
  const errors = [];
  if (!checkObject(value, errors, "envelope")) return errors;
  checkExactKeys(value, ENVELOPE_KEYS, errors);
  checkRequired(value, ENVELOPE_KEYS, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  for (const field of ["contextId", "captureRequestId", "requestId"]) checkId(value[field], field, errors);
  if (value.sourceKind !== "browser_page") addError(errors, "invalid_contract", "sourceKind", "sourceKind must be browser_page");
  checkString(value.sourceUrl, "sourceUrl", errors, 2048);
  try {
    const parsed = new URL(value.sourceUrl);
    if (!["http:", "https:"].includes(parsed.protocol)) addError(errors, "unsupported_scheme", "sourceUrl", "sourceUrl must use http or https");
    if (parsed.origin !== value.sourceOrigin) addError(errors, "origin_mismatch", "sourceOrigin", "sourceOrigin must match sourceUrl origin");
  } catch {
    addError(errors, "invalid_contract", "sourceUrl", "sourceUrl must be an absolute URL");
  }
  checkString(value.sourceOrigin, "sourceOrigin", errors, 512);
  checkString(value.sourceTitle, "sourceTitle", errors, 512);
  checkTimestamp(value.capturedAt, "capturedAt", errors);
  checkEnum(value.captureMode, "captureMode", tokens.captureModes, errors, "unknown_capture_mode");
  if (value.contentType !== "text/plain") addError(errors, "invalid_contract", "contentType", "contentType must be text/plain");
  if (typeof value.content !== "string") addError(errors, "invalid_contract", "content", "content must be a string");
  else {
    const contentLength = Buffer.byteLength(value.content, "utf8");
    if (contentLength > MAX_CAPTURE_BYTES || value.contentLength > MAX_CAPTURE_BYTES) addError(errors, "payload_too_large", "content", "content exceeds the common capture budget");
    if (contentLength !== value.contentLength) addError(errors, "content_length_mismatch", "contentLength", "contentLength does not match content bytes");
    const actualHash = crypto.createHash("sha256").update(value.content, "utf8").digest("hex");
    if (actualHash !== value.contentHash) addError(errors, "content_hash_mismatch", "contentHash", "contentHash does not match content");
    if (typeof value.originalContentLength !== "number" || value.originalContentLength < contentLength) addError(errors, "invalid_contract", "originalContentLength", "originalContentLength must cover content");
    if (value.truncated === false && value.originalContentLength !== contentLength) addError(errors, "invalid_contract", "truncated", "non-truncated content must have matching original length");
  }
  if (typeof value.contentHash !== "string" || !/^[a-f0-9]{64}$/.test(value.contentHash)) addError(errors, "invalid_contract", "contentHash", "contentHash must be a sha256 digest");
  if (!Number.isInteger(value.contentLength) || value.contentLength < 0) addError(errors, "invalid_contract", "contentLength", "contentLength must be a non-negative integer");
  if (!Number.isInteger(value.originalContentLength) || value.originalContentLength < 0) addError(errors, "invalid_contract", "originalContentLength", "originalContentLength must be a non-negative integer");
  if (typeof value.truncated !== "boolean") addError(errors, "invalid_contract", "truncated", "truncated must be boolean");
  checkString(value.extractorVersion, "extractorVersion", errors, 128);
  if (value.permissionScope !== "browser_context_capture_only") addError(errors, "invalid_contract", "permissionScope", "permission scope is not canonical");
  if (value.retentionClass !== "ephemeral") addError(errors, "retention_not_supported", "retentionClass", "v1 accepts only ephemeral retention");
  if (value.userInitiated !== true) addError(errors, "user_initiation_required", "userInitiated", "capture requires explicit user initiation");
  if (!Number.isInteger(value.attemptNumber) || value.attemptNumber < 1) addError(errors, "invalid_contract", "attemptNumber", "attemptNumber must be positive");
  validateSanitization(value.sanitizationEvidence, errors);
  if (!Number.isInteger(value.documentGeneration) || value.documentGeneration < 0) addError(errors, "invalid_contract", "documentGeneration", "documentGeneration must be non-negative");
  if (typeof value.documentFingerprint !== "string" || !/^[a-f0-9]{64}$/.test(value.documentFingerprint)) addError(errors, "invalid_contract", "documentFingerprint", "documentFingerprint must be a sha256 digest");
  return errors;
}

function validateAttachment(value) {
  const errors = [];
  const required = ["schemaVersion", "protocolVersion", "attachmentVersion", "requestId", "attemptNumber", "idempotencyKey", "envelope", "requestedRetention", "userConfirmation", "targetScope", "generatedAt"];
  if (!checkObject(value, errors, "attachment")) return errors;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkVersion(value.protocolVersion, "protocolVersion", errors);
  checkVersion(value.attachmentVersion, "attachmentVersion", errors);
  checkId(value.requestId, "requestId", errors);
  if (!Number.isInteger(value.attemptNumber) || value.attemptNumber < 1) addError(errors, "invalid_contract", "attemptNumber", "attemptNumber must be positive");
  checkString(value.idempotencyKey, "idempotencyKey", errors, 256);
  if (typeof value.idempotencyKey === "string" && value.idempotencyKey.length < 8) addError(errors, "invalid_contract", "idempotencyKey", "idempotencyKey must be bounded and non-trivial");
  const envelopeErrors = validateEnvelope(value.envelope);
  errors.push(...envelopeErrors);
  if (value.requestedRetention !== "ephemeral") addError(errors, "retention_not_supported", "requestedRetention", "v1 accepts only ephemeral retention");
  if (!checkObject(value.userConfirmation, errors, "userConfirmation")) return errors;
  checkExactKeys(value.userConfirmation, ["confirmed", "confirmedAt", "method"], errors);
  checkRequired(value.userConfirmation, ["confirmed", "confirmedAt", "method"], errors);
  if (value.userConfirmation.confirmed !== true) addError(errors, "user_confirmation_required", "userConfirmation.confirmed", "attachment requires separate confirmation");
  checkTimestamp(value.userConfirmation.confirmedAt, "userConfirmation.confirmedAt", errors);
  if (value.userConfirmation.method !== "trusted_shell") addError(errors, "user_confirmation_required", "userConfirmation.method", "confirmation must come from the trusted shell");
  if (value.targetScope !== null) {
    if (!checkObject(value.targetScope, errors, "targetScope")) return errors;
    checkExactKeys(value.targetScope, ["kind", "id"], errors);
    checkRequired(value.targetScope, ["kind", "id"], errors);
    checkEnum(value.targetScope.kind, "targetScope.kind", ["request", "thread", "project"], errors);
    checkId(value.targetScope.id, "targetScope.id", errors);
  }
  checkTimestamp(value.generatedAt, "generatedAt", errors);
  return errors;
}

function validateAttachmentGrantRequest(value) {
  const errors = [];
  if (!checkObject(value, errors, "attachmentGrantRequest")) return errors;
  checkExactKeys(value, GRANT_REQUEST_KEYS, errors);
  checkRequired(value, GRANT_REQUEST_KEYS, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkGrantVersion(value.protocolVersion, "protocolVersion", errors);
  checkGrantVersion(value.attachmentVersion, "attachmentVersion", errors);
  checkId(value.requestId, "requestId", errors);
  checkId(value.browserHostInstanceId, "browserHostInstanceId", errors);
  if (value.requestedRetention !== manifest.attachmentGrant.retentionClass) addError(errors, "attachment_grant_retention_denied", "requestedRetention", "attachment grants are ephemeral only");
  if (value.requestedAttachmentCount !== manifest.attachmentGrant.allowedUses) addError(errors, "attachment_grant_invalid", "requestedAttachmentCount", "one attachment grant request permits exactly one attachment");
  if (!Number.isInteger(value.requestedMaxContentBytes) || value.requestedMaxContentBytes < 1 || value.requestedMaxContentBytes > MAX_CAPTURE_BYTES) addError(errors, "attachment_grant_budget_exceeded", "requestedMaxContentBytes", "requested budget exceeds the common capture budget");
  if (!Number.isInteger(value.requestedTtlSeconds) || value.requestedTtlSeconds < manifest.attachmentGrant.minimumTtlSeconds || value.requestedTtlSeconds > manifest.attachmentGrant.maximumTtlSeconds) addError(errors, "attachment_grant_invalid", "requestedTtlSeconds", "requested TTL is outside the bounded grant window");
  if (value.userConfirmationMode !== "explicit_each_attachment") addError(errors, "attachment_grant_confirmation_required", "userConfirmationMode", "each attachment requires explicit confirmation");
  checkTimestamp(value.generatedAt, "generatedAt", errors);
  return errors;
}

function validateAttachmentGrant(value) {
  const errors = [];
  if (!checkObject(value, errors, "attachmentGrant")) return errors;
  checkExactKeys(value, GRANT_RESPONSE_KEYS, errors);
  checkRequired(value, GRANT_RESPONSE_KEYS, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkGrantVersion(value.protocolVersion, "protocolVersion", errors);
  checkGrantVersion(value.attachmentVersion, "attachmentVersion", errors);
  checkId(value.grantId, "grantId", errors);
  checkEnum(value.authorizationScheme, "authorizationScheme", tokens.authorizationSchemes, errors, "attachment_grant_invalid");
  if (typeof value.grantBearer !== "string" || !/^[A-Za-z0-9._~-]{43,128}$/.test(value.grantBearer)) addError(errors, "attachment_grant_invalid", "grantBearer", "grant bearer must be opaque bounded material");
  checkId(value.browserHostInstanceId, "browserHostInstanceId", errors);
  checkId(value.requestId, "requestId", errors);
  if (value.retentionClass !== manifest.attachmentGrant.retentionClass) addError(errors, "attachment_grant_retention_denied", "retentionClass", "attachment grants are ephemeral only");
  if (!Number.isInteger(value.maxContentBytes) || value.maxContentBytes < 1 || value.maxContentBytes > MAX_CAPTURE_BYTES) addError(errors, "attachment_grant_budget_exceeded", "maxContentBytes", "grant budget exceeds the common capture budget");
  if (value.remainingUses !== manifest.attachmentGrant.allowedUses) addError(errors, "attachment_grant_invalid", "remainingUses", "attachment grants are single-use");
  checkTimestamp(value.issuedAt, "issuedAt", errors);
  checkTimestamp(value.expiresAt, "expiresAt", errors);
  const issued = Date.parse(value.issuedAt);
  const expires = Date.parse(value.expiresAt);
  if (!Number.isNaN(issued) && !Number.isNaN(expires) && expires <= issued) addError(errors, "attachment_grant_invalid", "expiresAt", "grant expiry must be later than issue time");
  return errors;
}

function validateReceipt(value) {
  const errors = [];
  const required = ["schemaVersion", "protocolVersion", "requestId", "attemptNumber", "contextId", "attachmentOutcome", "persistenceOutcome", "errorCode", "receivedAt", "guardianCorrelationId"];
  if (!checkObject(value, errors, "receipt")) return errors;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  checkVersion(value.protocolVersion, "protocolVersion", errors);
  checkId(value.requestId, "requestId", errors);
  checkId(value.contextId, "contextId", errors);
  if (!Number.isInteger(value.attemptNumber) || value.attemptNumber < 1) addError(errors, "invalid_contract", "attemptNumber", "attemptNumber must be positive");
  checkEnum(value.attachmentOutcome, "attachmentOutcome", tokens.attachmentOutcomes, errors);
  if (value.persistenceOutcome !== "not_persisted") addError(errors, "invalid_contract", "persistenceOutcome", "v1 receipts never claim durable persistence");
  if (value.errorCode !== null && !tokens.errorCodes.includes(value.errorCode)) addError(errors, "unknown_error_code", "errorCode", "receipt errorCode is not canonical");
  if (value.attachmentOutcome === "accepted" && value.errorCode !== null) addError(errors, "invalid_contract", "errorCode", "accepted receipt cannot contain an error");
  if (value.attachmentOutcome === "rejected" && typeof value.errorCode !== "string") addError(errors, "invalid_contract", "errorCode", "rejected receipt requires an error");
  if (value.attachmentOutcome === "accepted" && (typeof value.guardianCorrelationId !== "string" || value.guardianCorrelationId.length === 0)) addError(errors, "invalid_contract", "guardianCorrelationId", "accepted receipt requires Guardian correlation");
  if (value.attachmentOutcome === "rejected" && value.guardianCorrelationId !== null) addError(errors, "invalid_contract", "guardianCorrelationId", "rejected receipt does not claim Guardian acceptance");
  checkTimestamp(value.receivedAt, "receivedAt", errors);
  return errors;
}

function validateError(value) {
  const errors = [];
  const required = ["schemaVersion", "errorCode", "message", "retryable", "requestCorrelationId", "generatedAt", "safeDetails"];
  if (!checkObject(value, errors, "error")) return errors;
  checkExactKeys(value, required, errors);
  checkRequired(value, required, errors);
  checkVersion(value.schemaVersion, "schemaVersion", errors);
  if (!tokens.errorCodes.includes(value.errorCode)) addError(errors, "unknown_error_code", "errorCode", "errorCode is not canonical");
  checkString(value.message, "message", errors, 256);
  if (typeof value.retryable !== "boolean") addError(errors, "invalid_contract", "retryable", "retryable must be boolean");
  checkId(value.requestCorrelationId, "requestCorrelationId", errors);
  checkTimestamp(value.generatedAt, "generatedAt", errors);
  if (checkObject(value.safeDetails, errors, "safeDetails")) {
    const allowed = ["contract", "version", "feature", "field", "expected", "actual"];
    checkExactKeys(value.safeDetails, allowed, errors);
    for (const key of Object.keys(value.safeDetails)) {
      if (!["string", "number", "boolean"].includes(typeof value.safeDetails[key]) && value.safeDetails[key] !== null) addError(errors, "invalid_contract", `safeDetails.${key}`, "safeDetails values must be scalar");
    }
  }
  return errors;
}

const validators = Object.freeze({
  hello: validateHello,
  negotiation: validateNegotiation,
  envelope: validateEnvelope,
  attachment: validateAttachment,
  attachmentGrantRequest: validateAttachmentGrantRequest,
  attachmentGrant: validateAttachmentGrant,
  receipt: validateReceipt,
  error: validateError
});

function validate(kind, value) {
  const validator = validators[kind];
  if (!validator) return {valid: false, errors: [{code: "invalid_contract", field: "kind", message: `unknown contract kind: ${kind}`}]};
  const errors = validator(value);
  return {valid: errors.length === 0, errors};
}

const contractMetadata = deepFreeze({
  packageName: manifest.contractPackageName,
  packageVersion: manifest.contractPackageVersion,
  protocolVersion: manifest.protocol.currentVersion,
  envelopeVersion: manifest.browserContextEnvelope.currentVersion,
  attachmentVersion: manifest.contextAttachment.currentVersion,
  maxCaptureBytes: MAX_CAPTURE_BYTES,
  hashAlgorithm: manifest.hashAlgorithm,
  releasePosture: manifest.releasePosture,
  failClosed: manifest.protocol.failClosed,
  grant: {
    authorizationScheme: manifest.attachmentGrant.supportedAuthorizationSchemes[0],
    defaultTtlSeconds: manifest.attachmentGrant.defaultTtlSeconds,
    minimumTtlSeconds: manifest.attachmentGrant.minimumTtlSeconds,
    maximumTtlSeconds: manifest.attachmentGrant.maximumTtlSeconds,
    allowedUses: manifest.attachmentGrant.allowedUses,
    retentionClass: manifest.attachmentGrant.retentionClass,
    authorizationMaterial: manifest.attachmentGrant.authorizationMaterial,
    reusableGuardianCredential: manifest.attachmentGrant.reusableGuardianCredential
  }
});

function validateToken(domain, value) {
  const allowed = GRANT_TOKEN_DOMAINS[domain];
  if (!allowed) return { valid: false, errors: [{ code: "invalid_contract", field: "domain", message: `unknown token domain: ${domain}` }] };
  return allowed.includes(value)
    ? { valid: true, errors: [] }
    : { valid: false, errors: [{ code: "invalid_contract", field: "value", message: `value is not canonical for ${domain}` }] };
}

module.exports = deepFreeze({
  manifest,
  tokens,
  schemas,
  fixtureIndex,
  contractMetadata,
  maxCaptureBytes: MAX_CAPTURE_BYTES,
  loadJson: readJson,
  validate,
  validateToken,
  grantTokenDomains: GRANT_TOKEN_DOMAINS,
  validators
});
