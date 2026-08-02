"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const {
  NEGOTIATION_PATH,
  GuardianNegotiationClientError,
  buildHello,
  negotiate
} = require("../src/runtime/guardian-negotiation-client");

const compatible = JSON.parse(fs.readFileSync(path.join(__dirname, "../contracts/fixtures/valid/negotiation-compatible.json"), "utf8"));
const config = {
  packageVersion: "0.1.0",
  protocolVersion: "1.0.0",
  envelopeVersion: "1.0.0",
  attachmentVersion: "1.0.0",
  supportedFeatureTokens: ["capture:selected", "capture:visible", "capture:attach"],
  platform: "darwin",
  architecture: "arm64",
  guardianNegotiationTimeoutMs: 1000
};

function startServer(handler) {
  const server = http.createServer(handler);
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({
    server,
    origin: `http://127.0.0.1:${server.address().port}`
  })));
}

function close(server) { return new Promise((resolve) => server.close(resolve)); }

test("Guardian negotiation client posts the validated hello to the exact route without credentials", async () => {
  let seen;
  const running = await startServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      seen = { method: request.method, path: request.url, headers: request.headers, body: JSON.parse(Buffer.concat(chunks).toString("utf8")) };
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ ...compatible, requestCorrelationId: seen.body.requestCorrelationId }));
    });
  });
  try {
    const result = await negotiate({ ...config, guardianNegotiationOrigin: running.origin });
    assert.equal(seen.method, "POST");
    assert.equal(seen.path, NEGOTIATION_PATH);
    assert.equal(seen.headers.authorization, undefined);
    assert.equal(seen.headers.cookie, undefined);
    assert.equal(seen.headers["x-codexify-browser-host-attachment-grant"], undefined);
    assert.equal(seen.body.schemaVersion, "1.0.0");
    assert.equal(result.response.compatibilityOutcome, "compatible");
  } finally {
    await close(running.server);
  }
});

test("incompatible Guardian negotiation is a valid bounded result", async () => {
  const running = await startServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const hello = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ ...compatible, requestCorrelationId: hello.requestCorrelationId, compatibilityOutcome: "incompatible", selectedProtocolVersion: null, selectedEnvelopeVersion: null, selectedAttachmentVersion: null, enabledFeatures: [], disabledFeatures: [{ feature: "capture:selected", reason: "incompatible_version" }, { feature: "capture:visible", reason: "incompatible_version" }, { feature: "capture:attach", reason: "incompatible_version" }], errorCode: "unsupported_protocol_version" }));
    });
  });
  try {
    const result = await negotiate({ ...config, guardianNegotiationOrigin: running.origin });
    assert.equal(result.response.compatibilityOutcome, "incompatible");
    assert.equal(result.response.selectedProtocolVersion, null);
  } finally {
    await close(running.server);
  }
});

test("malformed, timeout, connection, and redirect failures are bounded and never retried", async () => {
  let calls = 0;
  const malformed = await startServer((_request, response) => { calls += 1; response.end("raw-negotiation-response"); });
  await assert.rejects(
    () => negotiate({ ...config, guardianNegotiationOrigin: malformed.origin }),
    (error) => error instanceof GuardianNegotiationClientError && error.code === "invalid_contract" && !error.message.includes("raw-negotiation-response")
  );
  await close(malformed.server);
  assert.equal(calls, 1);

  const slow = await startServer((_request, response) => { setTimeout(() => response.end(JSON.stringify(compatible)), 80); });
  await assert.rejects(() => negotiate({ ...config, guardianNegotiationOrigin: slow.origin, guardianNegotiationTimeoutMs: 10 }), /guardian_negotiation_timeout|guardian_negotiation_unreachable/);
  await close(slow.server);

  const redirect = await startServer((_request, response) => { response.writeHead(302, { Location: "/other" }); response.end(); });
  await assert.rejects(() => negotiate({ ...config, guardianNegotiationOrigin: redirect.origin }), /redirect_rejected/);
  await close(redirect.server);

  const closed = await startServer((_request, response) => response.end());
  const closedOrigin = closed.origin;
  await close(closed.server);
  await assert.rejects(() => negotiate({ ...config, guardianNegotiationOrigin: closedOrigin }), /unreachable|ECONNREFUSED/);
});

test("hello construction is contract-shaped and contains no authority material", () => {
  const hello = buildHello(config, "browser-host-negotiation-test");
  assert.equal(hello.requestCorrelationId, "browser-host-negotiation-test");
  assert.deepEqual(Object.keys(hello).sort(), ["architecture", "componentVersion", "generatedAt", "platform", "requestCorrelationId", "schemaVersion", "supportedAttachmentVersions", "supportedEnvelopeVersions", "supportedFeatureTokens", "supportedProtocolVersions"].sort());
  assert.equal("apiKey" in hello, false);
  assert.equal("cookie" in hello, false);
  assert.equal("jwt" in hello, false);
  assert.equal("grant" in hello, false);
});
