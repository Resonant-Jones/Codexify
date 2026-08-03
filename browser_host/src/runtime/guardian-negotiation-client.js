"use strict";

const http = require("node:http");
const crypto = require("node:crypto");
const contractPackage = require("../../contracts");

const NEGOTIATION_PATH = "/dev/browser-host/v1/negotiate";
const MAX_RESPONSE_BYTES = 65536;

class GuardianNegotiationClientError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "GuardianNegotiationClientError";
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

function requestNegotiation(origin, hello, timeoutMs, onHttpStatus) {
  return new Promise((resolve, reject) => {
    if (!origin) return reject(new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_origin_missing"));
    let url;
    try { url = new URL(NEGOTIATION_PATH, origin); } catch { return reject(new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_origin_invalid")); }
    const body = JSON.stringify(hello);
    const request = http.request(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body)
      }
    }, (response) => {
      onHttpStatus?.(response.statusCode);
      const chunks = [];
      let size = 0;
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        size += Buffer.byteLength(chunk);
        if (size <= MAX_RESPONSE_BYTES) chunks.push(chunk);
        else request.destroy(new GuardianNegotiationClientError("invalid_contract", "guardian_negotiation_response_too_large"));
      });
      response.on("end", () => {
        if (response.statusCode >= 300 && response.statusCode < 400) {
          return reject(new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_redirect_rejected", { status: response.statusCode }));
        }
        const text = chunks.join("");
        let value;
        try { value = JSON.parse(text); } catch {
          return reject(new GuardianNegotiationClientError("invalid_contract", "guardian_negotiation_response_malformed"));
        }
        if (response.statusCode !== 200) {
          return reject(new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_http_rejected", { status: response.statusCode }));
        }
        resolve(value);
      });
    });
    request.setTimeout(timeoutMs, () => request.destroy(new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_timeout")));
    request.on("error", (error) => reject(error instanceof GuardianNegotiationClientError
      ? error
      : new GuardianNegotiationClientError("guardian_rejected", "guardian_negotiation_unreachable")));
    request.end(body);
  });
}

function assertNegotiation(hello, response, config) {
  const validation = contractPackage.validate("negotiation", response);
  if (!validation.valid) throw new GuardianNegotiationClientError("invalid_contract", "guardian_negotiation_response_invalid");
  if (response.requestCorrelationId !== hello.requestCorrelationId) throw new GuardianNegotiationClientError("invalid_contract", "guardian_negotiation_correlation_mismatch");
  if (response.compatibilityOutcome === "incompatible") return response;
  if (
    response.selectedProtocolVersion !== config.protocolVersion
    || response.selectedEnvelopeVersion !== config.envelopeVersion
    || response.selectedAttachmentVersion !== config.attachmentVersion
  ) throw new GuardianNegotiationClientError("no_compatible_version", "guardian_selected_unsupported_version");
  for (const feature of response.enabledFeatures) {
    if (!hello.supportedFeatureTokens.includes(feature)) throw new GuardianNegotiationClientError("undeclared_feature", "guardian_enabled_undeclared_feature");
  }
  return response;
}

async function negotiate(config, { onHttpStatus } = {}) {
  const hello = buildHello(config);
  const helloValidation = contractPackage.validate("hello", hello);
  if (!helloValidation.valid) throw new GuardianNegotiationClientError("invalid_contract", "hello_invalid");
  const response = await requestNegotiation(
    config.guardianNegotiationOrigin,
    hello,
    config.guardianNegotiationTimeoutMs,
    onHttpStatus
  );
  return { hello, response: assertNegotiation(hello, response, config) };
}

module.exports = Object.freeze({
  NEGOTIATION_PATH,
  GuardianNegotiationClientError,
  buildHello,
  requestNegotiation,
  assertNegotiation,
  negotiate
});
