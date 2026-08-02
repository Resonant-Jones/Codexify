"use strict";

const http = require("node:http");
const contractPackage = require("../../contracts");

const ATTACHMENT_PATH = "/dev/browser-host/v1/attachments";
const AUTHORIZATION_SCHEME = "BrowserHostAttachmentGrant";
const INSTANCE_HEADER = "X-Codexify-Browser-Host-Instance-Id";
const MAX_RESPONSE_BYTES = 65536;

class GuardianAttachmentError extends Error {
  constructor(code, message, status = null) {
    super(message);
    this.name = "GuardianAttachmentError";
    this.code = contractPackage.tokens.errorCodes.includes(code) ? code : "guardian_rejected";
    this.status = Number.isInteger(status) ? status : null;
  }
}

function createOneShotGrantHolder(rawGrant) {
  let grant = typeof rawGrant === "string" && rawGrant.length > 0 ? rawGrant : null;
  let consumed = false;

  return Object.freeze({
    available: () => grant !== null,
    claim: () => {
      if (grant === null) return null;
      const claimed = grant;
      grant = null;
      consumed = true;
      return claimed;
    },
    discard: () => {
      grant = null;
      consumed = true;
    },
    consumed: () => consumed
  });
}

function safeErrorCode(value, fallback = "guardian_rejected") {
  return contractPackage.tokens.errorCodes.includes(value) ? value : fallback;
}

function assertAttachment(value) {
  const validation = contractPackage.validate("attachment", value);
  if (!validation.valid) {
    throw new GuardianAttachmentError("invalid_contract", "attachment_invalid");
  }
}

function assertAcceptedReceipt(value, attachment) {
  const validation = contractPackage.validate("receipt", value);
  if (!validation.valid || value.attachmentOutcome !== "accepted" || value.persistenceOutcome !== "not_persisted") {
    throw new GuardianAttachmentError("invalid_contract", "guardian_receipt_invalid");
  }
  if (
    value.requestId !== attachment.requestId ||
    value.attemptNumber !== attachment.attemptNumber ||
    value.contextId !== attachment.envelope.contextId
  ) {
    throw new GuardianAttachmentError("invalid_contract", "guardian_receipt_correlation_mismatch");
  }
  return value;
}

function rejectionCode(value, status) {
  if (contractPackage.validate("receipt", value).valid) {
    return safeErrorCode(value.errorCode, status === 409 ? "attachment_failed" : "guardian_rejected");
  }
  if (contractPackage.validate("error", value).valid) {
    return safeErrorCode(value.errorCode);
  }
  return status === 409 ? "attachment_failed" : "guardian_rejected";
}

function parseResponseBody(chunks) {
  try {
    return JSON.parse(chunks.join(""));
  } catch {
    throw new GuardianAttachmentError("invalid_contract", "guardian_response_malformed");
  }
}

function requestAttachment({ origin, instanceId, grant, timeoutMs, attachment, onHttpStatus }) {
  return new Promise((resolve, reject) => {
    const url = new URL(ATTACHMENT_PATH, origin);
    const body = JSON.stringify(attachment);
    const headers = {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
      Accept: "application/json",
      Authorization: `${AUTHORIZATION_SCHEME} ${grant}`,
      [INSTANCE_HEADER]: instanceId
    };
    let settled = false;
    let responseTooLarge = false;

    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      if (error) reject(error);
      else resolve(value);
    };

    const request = http.request(url, { method: "POST", headers }, (response) => {
      onHttpStatus?.(response.statusCode);
      const chunks = [];
      let size = 0;
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        size += Buffer.byteLength(chunk);
        if (size <= MAX_RESPONSE_BYTES) chunks.push(chunk);
        else responseTooLarge = true;
      });
      response.on("end", () => {
        if (responseTooLarge) {
          finish(new GuardianAttachmentError("invalid_contract", "guardian_response_too_large", response.statusCode));
          return;
        }
        if (response.statusCode >= 300 && response.statusCode < 400) {
          finish(new GuardianAttachmentError("guardian_rejected", "guardian_redirect_rejected", response.statusCode));
          return;
        }
        let value;
        try {
          value = parseResponseBody(chunks);
        } catch (error) {
          finish(error instanceof GuardianAttachmentError ? error : new GuardianAttachmentError("invalid_contract", "guardian_response_malformed", response.statusCode));
          return;
        }
        if (response.statusCode === 202) {
          try { finish(null, assertAcceptedReceipt(value, attachment)); }
          catch (error) { finish(error instanceof GuardianAttachmentError ? error : new GuardianAttachmentError("invalid_contract", "guardian_receipt_invalid", response.statusCode)); }
          return;
        }
        const code = rejectionCode(value, response.statusCode);
        finish(new GuardianAttachmentError(code, "guardian_attachment_rejected", response.statusCode));
      });
    });

    request.setTimeout(timeoutMs, () => {
      request.destroy(new GuardianAttachmentError("guardian_rejected", "guardian_attachment_timeout"));
    });
    request.on("error", (error) => {
      finish(
        error instanceof GuardianAttachmentError
          ? error
          : new GuardianAttachmentError("guardian_rejected", "guardian_attachment_unreachable")
      );
    });
    request.end(body);
  });
}

function createGuardianAttachmentClient({
  enabled,
  origin,
  instanceId,
  timeoutMs,
  grantHolder,
  onGrantClaimed,
  onHttpStatus
}) {
  if (!enabled) throw new Error("guardian_attachment_client_disabled");
  if (!grantHolder || typeof grantHolder.claim !== "function") throw new Error("guardian_attachment_grant_holder_missing");

  async function attach(attachment) {
    assertAttachment(attachment);
    const grant = grantHolder.claim();
    if (!grant) throw new GuardianAttachmentError("attachment_grant_consumed", "guardian_attachment_grant_unavailable");
    onGrantClaimed?.();
    return requestAttachment({ origin, instanceId, grant, timeoutMs, attachment, onHttpStatus });
  }

  function dispose() {
    grantHolder.discard?.();
  }

  return Object.freeze({ attach, dispose, grantAvailable: () => grantHolder.available() });
}

module.exports = Object.freeze({
  ATTACHMENT_PATH,
  AUTHORIZATION_SCHEME,
  INSTANCE_HEADER,
  GuardianAttachmentError,
  createOneShotGrantHolder,
  createGuardianAttachmentClient
});
