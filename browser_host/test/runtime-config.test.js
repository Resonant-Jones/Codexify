"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  loadConfig,
  numericLoopbackOrigin,
  validProofToken,
  parseGuardianAttachmentTimeout,
  validGuardianAttachmentGrant
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
