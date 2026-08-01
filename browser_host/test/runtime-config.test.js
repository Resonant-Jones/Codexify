"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { loadConfig, numericLoopbackOrigin, validProofToken } = require("../src/runtime/config");

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
  assert.deepEqual(config.supportedFeatureTokens, []);
  assert.equal(config.platform, "darwin");
  assert.equal(config.architecture, "arm64");
});
