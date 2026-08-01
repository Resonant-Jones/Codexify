"use strict";

const http = require("node:http");
const crypto = require("node:crypto");
const contractPackage = require("../../contracts");

class GuardianNegotiationError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "GuardianNegotiationError";
    this.code = contractPackage.tokens.errorCodes.includes(code) ? code : "guardian_rejected";
    this.details = details;
  }
}

function requestId() { return `browser-host-${crypto.randomUUID()}`; }

function buildHello(config, id = requestId()) {
  return {
    schemaVersion: "1.0.0",
    componentVersion: config.packageVersion,
    supportedProtocolVersions: [config.protocolVersion],
    supportedEnvelopeVersions: [config.envelopeVersion],
    supportedAttachmentVersions: [config.attachmentVersion],
    supportedFeatureTokens: [...config.supportedFeatureTokens],
    platform: config.platform,
    architecture: config.architecture,
    requestCorrelationId: id,
    generatedAt: new Date().toISOString()
  };
}

function postJson(origin, path, payload, token, timeoutMs) {
  return new Promise((resolve, reject) => {
    if (!origin) return reject(new GuardianNegotiationError("guardian_rejected", "guardian_origin_missing"));
    const url = new URL(path, origin);
    const body = JSON.stringify(payload);
    const headers = { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body), Accept: "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const request = http.request(url, { method: "POST", headers }, (response) => {
      const chunks = [];
      let size = 0;
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        size += Buffer.byteLength(chunk);
        if (size <= 65536) chunks.push(chunk);
        else request.destroy(new GuardianNegotiationError("invalid_contract", "guardian_response_too_large"));
      });
      response.on("end", () => {
        const text = chunks.join("");
        let value;
        try { value = JSON.parse(text); } catch { return reject(new GuardianNegotiationError("invalid_contract", "guardian_response_malformed")); }
        if (response.statusCode < 200 || response.statusCode >= 300) return reject(new GuardianNegotiationError("guardian_rejected", "guardian_http_rejected", { status: response.statusCode }));
        resolve(value);
      });
    });
    request.setTimeout(timeoutMs, () => request.destroy(new GuardianNegotiationError("guardian_rejected", "guardian_timeout")));
    request.on("error", (error) => reject(error instanceof GuardianNegotiationError ? error : new GuardianNegotiationError("guardian_rejected", "guardian_unreachable")));
    request.end(body);
  });
}

function assertNegotiation(hello, response, config) {
  const validation = contractPackage.validate("negotiation", response);
  if (!validation.valid) throw new GuardianNegotiationError("invalid_contract", "guardian_response_invalid", { field: validation.errors[0]?.field || "negotiation" });
  if (response.requestCorrelationId !== hello.requestCorrelationId) throw new GuardianNegotiationError("invalid_contract", "guardian_correlation_mismatch");
  if (response.compatibilityOutcome !== "compatible") throw new GuardianNegotiationError(response.errorCode || "no_compatible_version", "guardian_incompatible");
  if (response.selectedProtocolVersion !== config.protocolVersion || response.selectedEnvelopeVersion !== config.envelopeVersion || response.selectedAttachmentVersion !== config.attachmentVersion) {
    throw new GuardianNegotiationError("no_compatible_version", "guardian_selected_unsupported_version");
  }
  for (const feature of response.enabledFeatures) {
    if (!hello.supportedFeatureTokens.includes(feature)) throw new GuardianNegotiationError("undeclared_feature", "guardian_enabled_undeclared_feature", { feature });
  }
  return response;
}

async function negotiate(config) {
  const hello = buildHello(config);
  const helloValidation = contractPackage.validate("hello", hello);
  if (!helloValidation.valid) throw new GuardianNegotiationError("invalid_contract", "hello_invalid", { field: helloValidation.errors[0]?.field || "hello" });
  let response;
  try { response = await postJson(config.guardianOrigin, "/negotiate", hello, config.proofMode ? config.proofToken : null, config.negotiationTimeoutMs); }
  catch (error) { if (error instanceof GuardianNegotiationError) throw error; throw new GuardianNegotiationError("guardian_rejected", "guardian_unreachable"); }
  return { hello, response: assertNegotiation(hello, response, config) };
}

function assertReceipt(receipt, attachment) {
  const validation = contractPackage.validate("receipt", receipt);
  if (!validation.valid) throw new GuardianNegotiationError("invalid_contract", "guardian_receipt_invalid", { field: validation.errors[0]?.field || "receipt" });
  if (receipt.requestId !== attachment.requestId || receipt.attemptNumber !== attachment.attemptNumber || receipt.contextId !== attachment.envelope.contextId) throw new GuardianNegotiationError("invalid_contract", "guardian_receipt_correlation_mismatch");
  return receipt;
}

async function attachEnvelope(config, attachment) {
  const validation = contractPackage.validate("attachment", attachment);
  if (!validation.valid) throw new GuardianNegotiationError("invalid_contract", "attachment_invalid", { field: validation.errors[0]?.field || "attachment" });
  let response;
  try { response = await postJson(config.guardianOrigin, "/attach", attachment, config.proofMode ? config.proofToken : null, config.negotiationTimeoutMs); }
  catch (error) { if (error instanceof GuardianNegotiationError) throw error; throw new GuardianNegotiationError("guardian_rejected", "guardian_unreachable"); }
  return assertReceipt(response, attachment);
}

module.exports = Object.freeze({ GuardianNegotiationError, buildHello, negotiate, assertNegotiation, assertReceipt, attachEnvelope });
