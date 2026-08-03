"use strict";

const http = require("node:http");
const contractPackage = require("../../contracts");
const { validProofToken } = require("../../src/runtime/config");

function json(response, status, value) {
  const body = JSON.stringify(value);
  response.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
  response.end(body);
}

function attachmentReceipt(attachment, outcome, errorCode, sequence) {
  return {
    schemaVersion: "1.0.0",
    protocolVersion: "1.0.0",
    requestId: attachment.requestId,
    attemptNumber: attachment.attemptNumber,
    contextId: attachment.envelope.contextId,
    attachmentOutcome: outcome,
    persistenceOutcome: "not_persisted",
    errorCode: errorCode || null,
    receivedAt: new Date().toISOString(),
    guardianCorrelationId: outcome === "accepted" ? `guardian-attach-${sequence}` : null
  };
}

function startGuardianStub({ token, mode = "compatible", responseDelayMs = 0, enabledFeatures = [], attachmentMode = "accepted" } = {}) {
  if (!validProofToken(token)) throw new Error("stub_token_invalid");
  const requests = [];
  const attachments = [];
  const receipts = [];
  let closed = false;
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    if (request.method === "GET" && url.pathname === "/health") return json(response, 200, { status: "ok", service: "guardian-stub" });
    if (request.method !== "POST" || !["/negotiate", "/attach"].includes(url.pathname)) return json(response, 404, { error: "not_found" });
    const isAttachment = url.pathname === "/attach";
    const chunks = [];
    let size = 0;
    let tooLarge = false;
    request.setEncoding("utf8");
    request.on("data", (chunk) => { size += Buffer.byteLength(chunk); if (size <= 131072) chunks.push(chunk); else tooLarge = true; });
    request.on("end", () => {
      let value = null;
      try { if (!tooLarge) value = JSON.parse(chunks.join("")); } catch { /* malformed request is recorded below */ }
      const validation = value ? contractPackage.validate(isAttachment ? "attachment" : "hello", value) : { valid: false, errors: [{ field: "body" }] };
      const authorized = request.headers.authorization === `Bearer ${token}`;
      if (isAttachment) {
        attachments.push({
          requestId: value?.requestId || null,
          attemptNumber: value?.attemptNumber || null,
          contextId: value?.envelope?.contextId || null,
          captureMode: value?.envelope?.captureMode || null,
          contentHash: value?.envelope?.contentHash || null,
          contentLength: value?.envelope?.contentLength || null,
          retention: value?.requestedRetention || null,
          userConfirmation: value?.userConfirmation?.method || null,
          validationPassed: validation.valid,
          authorized,
          persisted: false
        });
        if (!authorized) return json(response, 401, { error: "guardian_rejected" });
        if (!validation.valid) return json(response, 400, { error: "invalid_contract" });
        if (attachmentMode === "timeout") return undefined;
        if (attachmentMode === "http_failure") return json(response, 503, { error: "attachment_failed" });
        if (attachmentMode === "malformed") { response.writeHead(200, { "Content-Type": "application/json" }); return response.end("{ malformed"); }
        const rejected = attachmentMode === "failed" || attachmentMode === "rejected";
        const receipt = attachmentReceipt(value, rejected ? "rejected" : "accepted", rejected ? "attachment_failed" : null, receipts.length + 1);
        receipts.push(receipt);
        return json(response, 200, receipt);
      }
      requests.push({ method: request.method, path: url.pathname, authorized, helloValid: validation.valid, requestCorrelationId: value?.requestCorrelationId || null, mode });
      if (!authorized) return json(response, 401, { error: "guardian_rejected" });
      if (!validation.valid) return json(response, 400, { error: "invalid_contract" });
      if (mode === "timeout") return undefined;
      const respond = () => {
        if (mode === "malformed") { response.writeHead(200, { "Content-Type": "application/json" }); return response.end("{ malformed"); }
        const incompatible = mode === "incompatible";
        const enabled = incompatible ? [] : enabledFeatures.filter((feature) => contractPackage.tokens.featureIdentifiers.includes(feature));
        const body = {
          schemaVersion: "1.0.0",
          requestCorrelationId: value.requestCorrelationId,
          compatibilityOutcome: incompatible ? "incompatible" : "compatible",
          selectedProtocolVersion: incompatible ? null : "1.0.0",
          selectedEnvelopeVersion: incompatible ? null : "1.0.0",
          selectedAttachmentVersion: incompatible ? null : "1.0.0",
          enabledFeatures: enabled,
          disabledFeatures: contractPackage.tokens.featureIdentifiers.filter((feature) => !enabled.includes(feature)).map((feature) => ({ feature, reason: incompatible ? "incompatible_version" : "not_supported" })),
          errorCode: incompatible ? "no_compatible_version" : null,
          guardianContractId: "guardian-browser-host-contract",
          guardianContractVersion: "1.0.0",
          generatedAt: new Date().toISOString()
        };
        json(response, 200, body);
      };
      if (responseDelayMs > 0) setTimeout(respond, responseDelayMs); else respond();
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.removeListener("error", reject);
      const address = server.address();
      resolve(Object.freeze({
        origin: `http://127.0.0.1:${address.port}`,
        requests,
        attachments,
        receipts,
        close: () => {
          if (closed) return Promise.resolve();
          closed = true;
          return new Promise((done) => server.close(() => done()));
        }
      }));
    });
  });
}

module.exports = Object.freeze({ startGuardianStub });
