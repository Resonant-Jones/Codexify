"use strict";

const os = require("node:os");
const packageManifest = require("../../package.json");
const contractPackage = require("../../contracts/package.json");
const contractManifest = require("../../contracts/manifest.json");
const { createOneShotGrantHolder } = require("./guardian-attachment-client");

const PROOF_MODE_ENV = "CODEXIFY_BROWSER_HOST_PROOF_MODE";
const PROOF_TOKEN_ENV = "CODEXIFY_BROWSER_HOST_PROOF_TOKEN";
const GUARDIAN_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN";
const FIXTURE_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN";
const NEGOTIATION_TIMEOUT_ENV = "CODEXIFY_BROWSER_HOST_NEGOTIATION_TIMEOUT_MS";
const GUARDIAN_ATTACHMENT_ENABLED_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED";
const GUARDIAN_ATTACHMENT_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN";
const GUARDIAN_ATTACHMENT_GRANT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT";
const BROWSER_HOST_INSTANCE_ID_ENV = "CODEXIFY_BROWSER_HOST_INSTANCE_ID";
const GUARDIAN_ATTACHMENT_TIMEOUT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_TIMEOUT_MS";

const INSTANCE_ID_PATTERN = /^[A-Za-z0-9._:-]{1,256}$/;
const GRANT_PATTERN = /^[A-Za-z0-9._~-]{43,128}$/;

function numericLoopbackOrigin(value, field = "origin") {
  if (typeof value !== "string" || value.length === 0 || value.length > 256) throw new Error(`${field}_invalid`);
  let parsed;
  try { parsed = new URL(value); } catch { throw new Error(`${field}_invalid`); }
  if (
    parsed.protocol !== "http:" || parsed.hostname !== "127.0.0.1" || !/^\d+$/.test(parsed.port) ||
    Number(parsed.port) < 1 || Number(parsed.port) > 65535 || parsed.username || parsed.password ||
    parsed.pathname !== "/" || parsed.search || parsed.hash
  ) throw new Error(`${field}_invalid`);
  return parsed.origin;
}

function parseTimeout(value) {
  if (value === undefined || value === "") return 1500;
  const timeout = Number(value);
  if (!Number.isInteger(timeout) || timeout < 100 || timeout > 10000) throw new Error("negotiation_timeout_invalid");
  return timeout;
}

function parseGuardianAttachmentTimeout(value) {
  if (value === undefined || value === "") return 3000;
  const timeout = Number(value);
  if (!Number.isInteger(timeout) || timeout < 1000 || timeout > 30000) throw new Error("guardian_attachment_timeout_invalid");
  return timeout;
}

function boundedInstanceId(value) {
  return typeof value === "string" && INSTANCE_ID_PATTERN.test(value);
}

function validGuardianAttachmentGrant(value) {
  return typeof value === "string" && GRANT_PATTERN.test(value);
}

function readAndRemoveGrant(env) {
  const value = typeof env?.[GUARDIAN_ATTACHMENT_GRANT_ENV] === "string"
    ? env[GUARDIAN_ATTACHMENT_GRANT_ENV]
    : "";
  try {
    delete env[GUARDIAN_ATTACHMENT_GRANT_ENV];
  } catch {
    try { env[GUARDIAN_ATTACHMENT_GRANT_ENV] = ""; } catch { /* fail closed below */ }
  }
  return value;
}

function freezeConfig(publicConfig, grantHolder) {
  Object.defineProperty(publicConfig, "guardianAttachmentGrantHolder", {
    value: grantHolder,
    enumerable: false,
    writable: false,
    configurable: false
  });
  return Object.freeze(publicConfig);
}

function validProofToken(value) {
  return typeof value === "string" && /^CODEXIFY-SYNTHETIC-[A-Za-z0-9_-]{16,128}$/.test(value);
}

function metadata() {
  return Object.freeze({
    packageName: packageManifest.name,
    packageVersion: packageManifest.version,
    contractPackageName: contractPackage.name,
    contractPackageVersion: contractPackage.version,
    protocolVersion: contractManifest.protocol.currentVersion,
    envelopeVersion: contractManifest.browserContextEnvelope.currentVersion,
    attachmentVersion: contractManifest.contextAttachment.currentVersion,
    releasePosture: contractManifest.releasePosture
  });
}

function loadConfig(env = process.env, platform = process.platform, architecture = process.arch) {
  const rawAttachmentGrant = readAndRemoveGrant(env);
  const proofMode = env[PROOF_MODE_ENV] === "1";
  const proofToken = proofMode ? env[PROOF_TOKEN_ENV] : null;
  if (proofMode && !validProofToken(proofToken)) throw new Error("proof_token_invalid");
  const guardianAttachmentAdapterEnabled = ["1", "true", "yes", "on"].includes(
    String(env[GUARDIAN_ATTACHMENT_ENABLED_ENV] || "").trim().toLowerCase()
  );
  const guardianOrigin = env[GUARDIAN_ORIGIN_ENV] ? numericLoopbackOrigin(env[GUARDIAN_ORIGIN_ENV], "guardian_origin") : null;
  const fixtureOrigin = env[FIXTURE_ORIGIN_ENV] ? numericLoopbackOrigin(env[FIXTURE_ORIGIN_ENV], "fixture_origin") : null;
  let guardianAttachmentOrigin = null;
  let browserHostInstanceId = null;
  let guardianAttachmentTimeoutMs = 3000;
  let grantHolder = createOneShotGrantHolder(null);
  if (guardianAttachmentAdapterEnabled) {
    if (!proofMode) throw new Error("guardian_attachment_dev_requires_proof_mode");
    guardianAttachmentOrigin = numericLoopbackOrigin(env[GUARDIAN_ATTACHMENT_ORIGIN_ENV], "guardian_attachment_origin");
    browserHostInstanceId = env[BROWSER_HOST_INSTANCE_ID_ENV];
    if (!boundedInstanceId(browserHostInstanceId)) throw new Error("browser_host_instance_id_invalid");
    guardianAttachmentTimeoutMs = parseGuardianAttachmentTimeout(env[GUARDIAN_ATTACHMENT_TIMEOUT_ENV]);
    if (!validGuardianAttachmentGrant(rawAttachmentGrant)) throw new Error("guardian_attachment_grant_invalid");
    grantHolder = createOneShotGrantHolder(rawAttachmentGrant);
  }
  return freezeConfig({
    ...metadata(),
    platform: platform || os.platform(),
    architecture: architecture || os.arch(),
    proofMode,
    proofToken,
    guardianOrigin,
    fixtureOrigin,
    negotiationTimeoutMs: parseTimeout(env[NEGOTIATION_TIMEOUT_ENV]),
    supportedFeatureTokens: Object.freeze(contractManifest.featureTokens.slice()),
    guardianAttachmentAdapterEnabled,
    guardianAttachmentOrigin,
    browserHostInstanceId,
    guardianAttachmentTimeoutMs,
    guardianAttachmentGrantAvailable: guardianAttachmentAdapterEnabled && grantHolder.available()
  }, grantHolder);
}

function unconfiguredConfig(errorCode = "invalid_contract") {
  return freezeConfig({
    ...metadata(),
    platform: process.platform,
    architecture: process.arch,
    proofMode: false,
    proofToken: null,
    guardianOrigin: null,
    fixtureOrigin: null,
    negotiationTimeoutMs: 1500,
    supportedFeatureTokens: Object.freeze([]),
    guardianAttachmentAdapterEnabled: false,
    guardianAttachmentOrigin: null,
    browserHostInstanceId: null,
    guardianAttachmentTimeoutMs: 3000,
    guardianAttachmentGrantAvailable: false,
    configurationError: errorCode
  }, createOneShotGrantHolder(null));
}

module.exports = Object.freeze({
  PROOF_MODE_ENV,
  PROOF_TOKEN_ENV,
  GUARDIAN_ORIGIN_ENV,
  FIXTURE_ORIGIN_ENV,
  NEGOTIATION_TIMEOUT_ENV,
  GUARDIAN_ATTACHMENT_ENABLED_ENV,
  GUARDIAN_ATTACHMENT_ORIGIN_ENV,
  GUARDIAN_ATTACHMENT_GRANT_ENV,
  BROWSER_HOST_INSTANCE_ID_ENV,
  GUARDIAN_ATTACHMENT_TIMEOUT_ENV,
  numericLoopbackOrigin,
  parseGuardianAttachmentTimeout,
  boundedInstanceId,
  validGuardianAttachmentGrant,
  validProofToken,
  metadata,
  loadConfig,
  unconfiguredConfig
});
