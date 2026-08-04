"use strict";

const http = require("node:http");
const test = require("node:test");
const assert = require("node:assert/strict");
const contractPackage = require("../contracts");
const {
  ATTACHMENT_PATH,
  AUTHORIZATION_SCHEME,
  INSTANCE_HEADER,
  createOneShotGrantHolder,
  createGuardianAttachmentClient
} = require("../src/runtime/guardian-attachment-client");

const attachmentFixture = require("../contracts/fixtures/valid/attachment-attempt-ephemeral.json");

function attachment() {
  return JSON.parse(JSON.stringify(attachmentFixture));
}

function acceptedReceipt(value) {
  return {
    schemaVersion: "1.0.0",
    protocolVersion: "1.0.0",
    requestId: value.requestId,
    attemptNumber: value.attemptNumber,
    contextId: value.envelope.contextId,
    attachmentOutcome: "accepted",
    persistenceOutcome: "not_persisted",
    errorCode: null,
    receivedAt: new Date().toISOString(),
    guardianCorrelationId: "guardian-attachment-client-test"
  };
}

function rejectedReceipt(value, errorCode = "permission_denied") {
  return {
    ...acceptedReceipt(value),
    attachmentOutcome: "rejected",
    errorCode,
    guardianCorrelationId: null
  };
}

function boundedError(errorCode = "permission_denied") {
  return {
    schemaVersion: "1.0.0",
    errorCode,
    message: "bounded attachment rejection",
    retryable: false,
    requestCorrelationId: "request-error-1",
    generatedAt: new Date().toISOString(),
    safeDetails: {}
  };
}

async function startServer(handler) {
  const server = http.createServer(handler);
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  return {
    origin: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(() => resolve()))
  };
}

function clientFor(origin, holder, hooks = {}, timeoutMs = 1000) {
  return createGuardianAttachmentClient({
    enabled: true,
    origin,
    instanceId: "browser-host-client-test",
    timeoutMs,
    grantHolder: holder,
    ...hooks
  });
}

test("uses exact loopback path, grant authorization scheme, instance header, and unchanged body", async () => {
  const value = attachment();
  const grant = "SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789";
  const holder = createOneShotGrantHolder(grant);
  let observed;
  const server = await startServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      observed = {
        method: request.method,
        path: request.url,
        authorization: request.headers.authorization,
        instance: request.headers[INSTANCE_HEADER.toLowerCase()],
        body: JSON.parse(Buffer.concat(chunks).toString("utf8"))
      };
      const body = JSON.stringify(acceptedReceipt(value));
      response.writeHead(202, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
      response.end(body);
    });
  });
  let status;
  try {
    const client = clientFor(server.origin, holder, { onHttpStatus: (value) => { status = value; } });
    const result = await client.attach(value);
    assert.equal(result.attachmentOutcome, "accepted");
    assert.equal(status, 202);
    assert.deepEqual(observed, {
      method: "POST",
      path: ATTACHMENT_PATH,
      authorization: `${AUTHORIZATION_SCHEME} ${grant}`,
      instance: "browser-host-client-test",
      body: value
    });
    assert.equal(holder.available(), false);
  } finally {
    await server.close();
  }
});

test("validates locally before claiming the one-shot grant", async () => {
  const holder = createOneShotGrantHolder("SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789");
  let requests = 0;
  const server = await startServer((_request, response) => { requests += 1; response.writeHead(500).end(); });
  try {
    const client = clientFor(server.origin, holder);
    await assert.rejects(() => client.attach({ content: "invalid" }), (error) => error.code === "invalid_contract");
    assert.equal(holder.available(), true);
    assert.equal(requests, 0);
  } finally {
    await server.close();
  }
});

test("claims exactly once and makes a second invocation local without a network request", async () => {
  const value = attachment();
  let requests = 0;
  const server = await startServer((_request, response) => {
    requests += 1;
    const body = JSON.stringify(acceptedReceipt(value));
    response.writeHead(202, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
    response.end(body);
  });
  try {
    const client = clientFor(server.origin, createOneShotGrantHolder("SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789"));
    await client.attach(value);
    await assert.rejects(() => client.attach(value), (error) => error.code === "attachment_grant_consumed");
    assert.equal(requests, 1);
  } finally {
    await server.close();
  }
});

test("validates rejected receipts and bounded errors without exposing credentials or content", async () => {
  const value = attachment();
  for (const [status, payload, expected] of [
    [403, rejectedReceipt(value), "permission_denied"],
    [401, boundedError("permission_denied"), "permission_denied"],
    [409, rejectedReceipt(value, "attachment_failed"), "attachment_failed"]
  ]) {
    const server = await startServer((_request, response) => {
      const body = JSON.stringify(payload);
      response.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
      response.end(body);
    });
    try {
      const grant = "SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789";
      const client = clientFor(server.origin, createOneShotGrantHolder(grant));
      await assert.rejects(() => client.attach(value), (error) => {
        assert.equal(error.code, expected);
        assert.equal(error.status, status);
        assert.doesNotMatch(error.message, /SYNTHETIC|Selected evidence|Authorization/);
        return true;
      });
    } finally {
      await server.close();
    }
  }
});

test("rejects redirects and never follows them", async () => {
  let redirected = 0;
  const destination = await startServer((_request, response) => { redirected += 1; response.writeHead(204).end(); });
  const source = await startServer((_request, response) => {
    response.writeHead(302, { Location: `${destination.origin}${ATTACHMENT_PATH}` });
    response.end();
  });
  try {
    const client = clientFor(source.origin, createOneShotGrantHolder("SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789"));
    await assert.rejects(() => client.attach(attachment()), (error) => error.code === "guardian_rejected" && error.status === 302);
    assert.equal(redirected, 0);
  } finally {
    await source.close();
    await destination.close();
  }
});

test("timeouts and network errors consume availability without retry", async () => {
  for (const mode of ["timeout", "network"]) {
    let requests = 0;
    const server = await startServer((request, response) => {
      requests += 1;
      if (mode === "network") return request.socket.destroy();
      setTimeout(() => response.end(JSON.stringify(acceptedReceipt(attachment()))), 250);
    });
    try {
      const client = clientFor(server.origin, createOneShotGrantHolder("SYNTHETIC-GRANT-abcdefghijklmnopqrstuvwxyz-0123456789"), {}, 100);
      await assert.rejects(() => client.attach(attachment()), (error) => error.code === "guardian_rejected");
      assert.equal(requests, 1);
      await assert.rejects(() => client.attach(attachment()), (error) => error.code === "attachment_grant_consumed");
      assert.equal(requests, 1);
    } finally {
      await server.close();
    }
  }
});

test("contract receipt validation remains canonical", () => {
  const value = attachment();
  assert.equal(contractPackage.validate("attachment", value).valid, true);
  assert.equal(contractPackage.validate("receipt", acceptedReceipt(value)).valid, true);
});
