"use strict";

const os = require("node:os");
const packageManifest = require("../../package.json");
const contractPackage = require("../../contracts/package.json");
const contractManifest = require("../../contracts/manifest.json");

const PROOF_MODE_ENV = "CODEXIFY_BROWSER_HOST_PROOF_MODE";
const PROOF_TOKEN_ENV = "CODEXIFY_BROWSER_HOST_PROOF_TOKEN";
const GUARDIAN_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN";
const FIXTURE_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN";
const NEGOTIATION_TIMEOUT_ENV = "CODEXIFY_BROWSER_HOST_NEGOTIATION_TIMEOUT_MS";

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
  const proofMode = env[PROOF_MODE_ENV] === "1";
  const proofToken = proofMode ? env[PROOF_TOKEN_ENV] : null;
  if (proofMode && !validProofToken(proofToken)) throw new Error("proof_token_invalid");
  const guardianOrigin = env[GUARDIAN_ORIGIN_ENV] ? numericLoopbackOrigin(env[GUARDIAN_ORIGIN_ENV], "guardian_origin") : null;
  const fixtureOrigin = env[FIXTURE_ORIGIN_ENV] ? numericLoopbackOrigin(env[FIXTURE_ORIGIN_ENV], "fixture_origin") : null;
  return Object.freeze({
    ...metadata(),
    platform: platform || os.platform(),
    architecture: architecture || os.arch(),
    proofMode,
    proofToken,
    guardianOrigin,
    fixtureOrigin,
    negotiationTimeoutMs: parseTimeout(env[NEGOTIATION_TIMEOUT_ENV]),
    supportedFeatureTokens: Object.freeze(contractManifest.featureTokens.slice())
  });
}

function unconfiguredConfig(errorCode = "invalid_contract") {
  return Object.freeze({
    ...metadata(),
    platform: process.platform,
    architecture: process.arch,
    proofMode: false,
    proofToken: null,
    guardianOrigin: null,
    fixtureOrigin: null,
    negotiationTimeoutMs: 1500,
    supportedFeatureTokens: Object.freeze([]),
    configurationError: errorCode
  });
}

module.exports = Object.freeze({
  PROOF_MODE_ENV,
  PROOF_TOKEN_ENV,
  GUARDIAN_ORIGIN_ENV,
  FIXTURE_ORIGIN_ENV,
  NEGOTIATION_TIMEOUT_ENV,
  numericLoopbackOrigin,
  validProofToken,
  metadata,
  loadConfig,
  unconfiguredConfig
});
