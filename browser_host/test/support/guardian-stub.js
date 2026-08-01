"use strict";

const http = require("node:http");
const contractPackage = require("../../contracts");
const { validProofToken } = require("../../src/runtime/config");

function json(response, status, value) {
  const body = JSON.stringify(value);
  response.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
  response.end(body);
}

function startGuardianStub({ token, mode = "compatible", responseDelayMs = 0 } = {}) {
  if (!validProofToken(token)) throw new Error("stub_token_invalid");
  const requests = [];
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    if (request.method === "GET" && url.pathname === "/health") return json(response, 200, { status: "ok", service: "guardian-stub" });
    if (request.method !== "POST" || url.pathname !== "/negotiate") return json(response, 404, { error: "not_found" });
    const chunks = [];
    let size = 0;
    request.setEncoding("utf8");
    request.on("data", (chunk) => { size += Buffer.byteLength(chunk); if (size <= 65536) chunks.push(chunk); });
    request.on("end", () => {
      let hello = null;
      try { hello = JSON.parse(chunks.join("")); } catch { /* malformed request is recorded below */ }
      const validation = hello ? contractPackage.validate("hello", hello) : { valid: false, errors: [{ field: "body" }] };
      const authorized = request.headers.authorization === `Bearer ${token}`;
      requests.push({ method: request.method, path: url.pathname, authorized, helloValid: validation.valid, requestCorrelationId: hello?.requestCorrelationId || null, mode });
      if (!authorized) return json(response, 401, { error: "guardian_rejected" });
      if (!validation.valid) return json(response, 400, { error: "invalid_contract" });
      if (mode === "timeout") return undefined;
      const respond = () => {
        if (mode === "malformed") { response.writeHead(200, { "Content-Type": "application/json" }); return response.end("{ malformed"); }
        const incompatible = mode === "incompatible";
        const body = {
          schemaVersion: "1.0.0",
          requestCorrelationId: hello.requestCorrelationId,
          compatibilityOutcome: incompatible ? "incompatible" : "compatible",
          selectedProtocolVersion: incompatible ? null : "1.0.0",
          selectedEnvelopeVersion: incompatible ? null : "1.0.0",
          selectedAttachmentVersion: incompatible ? null : "1.0.0",
          enabledFeatures: [],
          disabledFeatures: contractPackage.tokens.featureIdentifiers.map((feature) => ({ feature, reason: incompatible ? "incompatible_version" : "not_supported" })),
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
        close: () => new Promise((done) => server.close(() => done()))
      }));
    });
  });
}

module.exports = Object.freeze({ startGuardianStub });
