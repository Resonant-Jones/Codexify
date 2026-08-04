"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  loadConfig,
  numericLoopbackOrigin,
  validProofToken,
  parseGuardianAttachmentTimeout,
  validGuardianAttachmentGrant,
  parseGuardianNegotiationTimeout
} = require("../src/runtime/config");

test("config accepts only numeric loopback origins", () => {
  assert.equal(numericLoopbackOrigin("http://127.0.0.1:43123"), "http://127.0.0.1:43123");
  for (const value of ["http://localhost:43123", "https://127.0.0.1:43123", "http://127.0.0.1", "http://127.0.0.1:43123/path", "http://user:pass@127.0.0.1:43123"]) {
    assert.throws(() => numericLoopbackOrigin(value), /origin_invalid/);
  }
});

test("proof mode requires a bounded synthetic token and never changes the fixture origin policy", () => {
  const token = "CODEXIFY-SYNTHETIC-1234567890abcdef";
  assert.equal(validProofToken(token), true);
  assert.equal(validProofToken("real-secret"), false);
  assert.throws(() => loadConfig({ CODEXIFY_BROWSER_HOST_PROOF_MODE: "1" }), /proof_token_invalid/);
  const config = loadConfig({ CODEXIFY_BROWSER_HOST_PROOF_MODE: "1", CODEXIFY_BROWSER_HOST_PROOF_TOKEN: token, CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: "http://127.0.0.1:43123", CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: "http://127.0.0.1:43124" }, "darwin", "arm64");
  assert.equal(config.proofMode, true);
  assert.equal(config.proofToken, token);
  assert.deepEqual(config.supportedFeatureTokens, ["capture:selected", "capture:visible", "capture:attach"]);
  assert.equal(config.platform, "darwin");
  assert.equal(config.architecture, "arm64");
});

test("Guardian attachment configuration is explicit, loopback-only, and removes the raw grant from env", () => {
  const grant = "SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789ABCDEFGHI";
  const token = "CODEXIFY-SYNTHETIC-1234567890abcdef";
  const env = {
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: token,
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED: "true",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN: "http://127.0.0.1:43125",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT: grant,
    CODEXIFY_BROWSER_HOST_INSTANCE_ID: "browser-host-config-test",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_TIMEOUT_MS: "3000"
  };
  const config = loadConfig(env);
  assert.equal(config.guardianAttachmentAdapterEnabled, true);
  assert.equal(config.guardianAttachmentOrigin, "http://127.0.0.1:43125");
  assert.equal(config.browserHostInstanceId, "browser-host-config-test");
  assert.equal(config.guardianAttachmentGrantAvailable, true);
  assert.equal(config.guardianAttachmentTimeoutMs, 3000);
  assert.equal(env.CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT, undefined);
  assert.equal(Object.keys(config).includes("guardianAttachmentGrantHolder"), false);
  assert.equal("grant" in config, false);
  assert.equal(config.guardianAttachmentGrantHolder.claim(), grant);
  assert.equal(config.guardianAttachmentGrantHolder.available(), false);
  assert.equal(validGuardianAttachmentGrant(grant), true);
  assert.equal(parseGuardianAttachmentTimeout("1000"), 1000);
  assert.throws(() => parseGuardianAttachmentTimeout("999"), /guardian_attachment_timeout_invalid/);
});

test("Guardian adapter mode fails closed outside explicit proof mode or without bounded inputs", () => {
  const base = {
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED: "1",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN: "http://127.0.0.1:43125",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT: "SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789ABCDEFGHI",
    CODEXIFY_BROWSER_HOST_INSTANCE_ID: "browser-host-config-test"
  };
  const invalidProofEnvironment = { ...base };
  assert.throws(() => loadConfig(invalidProofEnvironment), /guardian_attachment_dev_requires_proof_mode/);
  assert.equal(invalidProofEnvironment.CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT, undefined);
  assert.throws(() => loadConfig({
    ...base,
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: "CODEXIFY-SYNTHETIC-1234567890abcdef",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN: "http://localhost:43125"
  }), /guardian_attachment_origin_invalid/);
});

test("Guardian negotiation mode is explicit, credential-free, numeric-loopback-only, and bounded", () => {
  const token = "CODEXIFY-SYNTHETIC-1234567890abcdef";
  const env = {
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: token,
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_DEV_ENABLED: "true",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN: "http://127.0.0.1:43126",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_TIMEOUT_MS: "3000",
    CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "guardian_dev_adapter"
  };
  const config = loadConfig(env);
  assert.equal(config.guardianNegotiationAdapterEnabled, true);
  assert.equal(config.negotiationTransport, "guardian_dev_adapter");
  assert.equal(config.guardianNegotiationOrigin, "http://127.0.0.1:43126");
  assert.equal(config.guardianNegotiationTimeoutMs, 3000);
  assert.equal(parseGuardianNegotiationTimeout("1000"), 1000);
  assert.throws(() => parseGuardianNegotiationTimeout("999"), /guardian_negotiation_timeout_invalid/);
  assert.throws(() => parseGuardianNegotiationTimeout("30001"), /guardian_negotiation_timeout_invalid/);
  for (const origin of [
    "http://localhost:43126",
    "https://127.0.0.1:43126",
    "http://127.0.0.1:43126/path",
    "http://user:pass@127.0.0.1:43126",
    "http://127.0.0.1:43126/?secret=1",
    "http://127.0.0.1:43126/#fragment"
  ]) {
    assert.throws(() => loadConfig({ ...env, CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN: origin }), /guardian_negotiation_origin_invalid/);
  }
  assert.throws(() => loadConfig({ ...env, CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_TIMEOUT_MS: "999" }), /guardian_negotiation_timeout_invalid/);
  assert.throws(() => loadConfig({ ...env, CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "deterministic_stub" }), /guardian_negotiation_transport_invalid/);
  assert.throws(() => loadConfig({ ...env, CODEXIFY_BROWSER_HOST_PROOF_MODE: undefined, CODEXIFY_BROWSER_HOST_PROOF_TOKEN: undefined }), /guardian_negotiation_dev_requires_proof_mode/);
});

test("combined Guardian negotiation and attachment modes require exactly one loopback origin", () => {
  const base = {
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: "CODEXIFY-SYNTHETIC-1234567890abcdef",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_DEV_ENABLED: "1",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN: "http://127.0.0.1:43127",
    CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "guardian_dev_adapter",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED: "1",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN: "http://127.0.0.1:43127",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT: "SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789ABCDEFGHI",
    CODEXIFY_BROWSER_HOST_INSTANCE_ID: "browser-host-config-test"
  };
  const mismatched = { ...base, CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN: "http://127.0.0.1:43128" };
  assert.equal(loadConfig(base).guardianAttachmentAdapterEnabled, true);
  assert.throws(() => loadConfig(mismatched), /guardian_origins_must_match/);
});

test("deterministic stub is retained only as the explicitly selected proof transport", () => {
  const config = loadConfig({
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: "CODEXIFY-SYNTHETIC-1234567890abcdef",
    CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "deterministic_stub",
    CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: "http://127.0.0.1:43129"
  });
  assert.equal(config.guardianNegotiationAdapterEnabled, false);
  assert.equal(config.negotiationTransport, "deterministic_stub");
  assert.throws(() => loadConfig({
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: "CODEXIFY-SYNTHETIC-1234567890abcdef",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN: "http://127.0.0.1:43129",
    CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "guardian_dev_adapter"
  }), /guardian_negotiation_requires_dev_flag/);
});
