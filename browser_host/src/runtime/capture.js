"use strict";

const crypto = require("node:crypto");
const contractPackage = require("../../contracts");

const MAX_CAPTURE_BYTES = contractPackage.contractMetadata.maxCaptureBytes;
const CAPTURE_MODES = Object.freeze(["selected_text", "visible_page_text"]);
const EXTRACTOR_VERSION = "electron-dom-walker-v1";
const SANITIZATION_EVIDENCE = Object.freeze({
  formControlValuesExcluded: true,
  passwordValuesExcluded: true,
  hiddenInputValuesExcluded: true,
  cookiesExcluded: true,
  localStorageExcluded: true,
  sessionStorageExcluded: true,
  scriptsAndStylesExcluded: true,
  crossOriginIframeContentExcluded: true
});

class CaptureOperationError extends Error {
  constructor(code, message = code) {
    super(message);
    this.name = "CaptureOperationError";
    this.code = contractPackage.tokens.errorCodes.includes(code) ? code : "capture_failed";
  }
}

function byteLength(value) {
  return Buffer.byteLength(String(value), "utf8");
}

function truncateUtf8(value, maxBytes = MAX_CAPTURE_BYTES) {
  const buffer = Buffer.from(String(value), "utf8");
  if (buffer.length <= maxBytes) return buffer.toString("utf8");
  let end = maxBytes;
  while (end > 0 && (buffer[end] & 0xc0) === 0x80) end -= 1;
  return buffer.subarray(0, end).toString("utf8");
}

function normalizeText(value) {
  if (typeof value !== "string") throw new CaptureOperationError("capture_response_invalid", "capture_text_invalid");
  return value.replace(/\u0000/g, "").replace(/\u00a0/g, " ").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

function sha256(value) {
  return crypto.createHash("sha256").update(value, "utf8").digest("hex");
}

function buildDocumentFingerprint({ sourceUrl, sourceTitle, visibleText, visibleTextOriginalLength }) {
  return sha256(JSON.stringify({
    sourceUrl,
    sourceTitle,
    visibleText,
    visibleTextOriginalLength
  }));
}

function ids(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function assertMode(mode) {
  if (!CAPTURE_MODES.includes(mode)) throw new CaptureOperationError("unknown_capture_mode", "capture_mode_unknown");
}

function buildEnvelope({ mode, requestId, captureRequestId = ids("capture"), contextId = ids("context"), attemptNumber = 1, raw, metadata, documentGeneration }) {
  assertMode(mode);
  if (!metadata || typeof metadata.remoteUrl !== "string" || typeof metadata.remoteOrigin !== "string") {
    throw new CaptureOperationError("tab_unavailable", "capture_metadata_unavailable");
  }
  try {
    if (metadata.remoteOrigin !== new URL(metadata.remoteUrl).origin) throw new CaptureOperationError("origin_mismatch", "capture_origin_mismatch");
  } catch (error) {
    if (error instanceof CaptureOperationError) throw error;
    throw new CaptureOperationError("origin_mismatch", "capture_origin_invalid");
  }
  const selected = mode === "selected_text";
  const sourceValue = normalizeText(selected ? raw?.selectedText : raw?.visibleText);
  const sourceOriginalLength = selected ? raw?.selectedTextOriginalLength : raw?.visibleTextOriginalLength;
  const originalContentLength = Number.isInteger(sourceOriginalLength) && sourceOriginalLength >= 0 ? sourceOriginalLength : byteLength(sourceValue);
  const content = truncateUtf8(sourceValue);
  if (content.length === 0) throw new CaptureOperationError("capture_mode_rejected", selected ? "selection_missing" : "visible_page_empty");
  const contentLength = byteLength(content);
  const envelope = {
    schemaVersion: contractPackage.contractMetadata.envelopeVersion,
    contextId,
    captureRequestId,
    sourceKind: "browser_page",
    sourceUrl: metadata.remoteUrl,
    sourceOrigin: metadata.remoteOrigin,
    sourceTitle: typeof metadata.remoteTitle === "string" ? metadata.remoteTitle.slice(0, 512) : "",
    capturedAt: new Date().toISOString(),
    captureMode: mode,
    contentType: "text/plain",
    content,
    contentHash: sha256(content),
    contentLength,
    originalContentLength,
    truncated: originalContentLength > contentLength,
    extractorVersion: EXTRACTOR_VERSION,
    permissionScope: "browser_context_capture_only",
    retentionClass: "ephemeral",
    userInitiated: true,
    requestId,
    attemptNumber,
    sanitizationEvidence: { ...SANITIZATION_EVIDENCE },
    documentGeneration,
    documentFingerprint: buildDocumentFingerprint({
      sourceUrl: metadata.remoteUrl,
      sourceTitle: typeof metadata.remoteTitle === "string" ? metadata.remoteTitle.slice(0, 512) : "",
      visibleText: typeof raw?.visibleText === "string" ? truncateUtf8(normalizeText(raw.visibleText)) : "",
      visibleTextOriginalLength: Number.isInteger(raw?.visibleTextOriginalLength) ? raw.visibleTextOriginalLength : 0
    })
  };
  const validation = contractPackage.validate("envelope", envelope);
  if (!validation.valid) throw new CaptureOperationError(validation.errors[0]?.code || "invalid_contract", "envelope_invalid");
  return Object.freeze(envelope);
}

function buildAttachment({ envelope, idempotencyKey = ids("attach"), targetScope = null }) {
  const attachment = {
    schemaVersion: contractPackage.contractMetadata.envelopeVersion,
    protocolVersion: contractPackage.contractMetadata.protocolVersion,
    attachmentVersion: contractPackage.contractMetadata.attachmentVersion,
    requestId: envelope.requestId,
    attemptNumber: envelope.attemptNumber,
    idempotencyKey,
    envelope,
    requestedRetention: "ephemeral",
    userConfirmation: { confirmed: true, confirmedAt: new Date().toISOString(), method: "trusted_shell" },
    targetScope,
    generatedAt: new Date().toISOString()
  };
  const validation = contractPackage.validate("attachment", attachment);
  if (!validation.valid) throw new CaptureOperationError(validation.errors[0]?.code || "invalid_contract", "attachment_invalid");
  return Object.freeze(attachment);
}

function buildRejectedReceipt(envelope, errorCode) {
  const safeCode = contractPackage.tokens.errorCodes.includes(errorCode) ? errorCode : "attachment_failed";
  return Object.freeze({
    schemaVersion: contractPackage.contractMetadata.envelopeVersion,
    protocolVersion: contractPackage.contractMetadata.protocolVersion,
    requestId: envelope.requestId,
    attemptNumber: envelope.attemptNumber,
    contextId: envelope.contextId,
    attachmentOutcome: "rejected",
    persistenceOutcome: "not_persisted",
    errorCode: safeCode,
    receivedAt: new Date().toISOString(),
    guardianCorrelationId: null
  });
}

function clearPreviewState() {
  return {
    captureMode: null,
    ...clearPendingPreviewState(),
    captureAttachmentOutcome: null,
    capturePersistenceOutcome: null,
    captureGuardianCorrelationId: null
  };
}

function clearPendingPreviewState() {
  return {
    captureTicketId: null,
    captureRequestId: null,
    captureContextId: null,
    capturePreviewContent: "",
    capturePreviewContentLength: 0,
    capturePreviewOriginalContentLength: 0,
    capturePreviewTruncated: false,
    capturePreviewSourceUrl: "",
    capturePreviewSourceOrigin: "",
    capturePreviewSourceTitle: "",
    capturePreviewDocumentGeneration: null,
    capturePreviewDocumentFingerprint: null,
    capturePreviewSanitization: null
  };
}

function previewState(envelope) {
  return {
    captureStatus: "preview_ready",
    captureMode: envelope.captureMode,
    captureTicketId: envelope.captureRequestId,
    captureRequestId: envelope.requestId,
    captureContextId: envelope.contextId,
    capturePreviewContent: envelope.content,
    capturePreviewContentLength: envelope.contentLength,
    capturePreviewOriginalContentLength: envelope.originalContentLength,
    capturePreviewTruncated: envelope.truncated,
    capturePreviewSourceUrl: envelope.sourceUrl,
    capturePreviewSourceOrigin: envelope.sourceOrigin,
    capturePreviewSourceTitle: envelope.sourceTitle,
    capturePreviewDocumentGeneration: envelope.documentGeneration,
    capturePreviewDocumentFingerprint: envelope.documentFingerprint,
    capturePreviewSanitization: { ...envelope.sanitizationEvidence },
    captureAttachmentOutcome: null,
    capturePersistenceOutcome: null,
    captureGuardianCorrelationId: null,
    captureErrorCode: null,
    captureLastDecision: "preview_ready"
  };
}

function createCaptureController({ getRemoteTab, config, isFeatureEnabled = () => true, update, attachEnvelope }) {
  let pending = null;
  const closedTickets = new Map();
  const remember = (ticketId, outcome) => {
    if (!ticketId) return;
    closedTickets.delete(ticketId);
    closedTickets.set(ticketId, outcome);
    while (closedTickets.size > 32) closedTickets.delete(closedTickets.keys().next().value);
  };
  const mapError = (error, fallback = "capture_failed") => contractPackage.tokens.errorCodes.includes(error?.code) ? error.code : fallback;
  const closedRejection = (ticketId, code = "context_rejected") => update({ captureStatus: "rejected", captureErrorCode: code, captureLastDecision: `ticket_rejected:${ticketId || "unknown"}` });

  async function capture(mode) {
    assertMode(mode);
    if (!isFeatureEnabled(`capture:${mode === "selected_text" ? "selected" : "visible"}`)) return update({ captureStatus: "rejected", captureErrorCode: "permission_denied", captureLastDecision: `capture_rejected:feature_disabled`, ...clearPreviewState() });
    const remoteTab = getRemoteTab();
    if (!remoteTab) return update({ captureStatus: "rejected", captureErrorCode: "tab_unavailable", captureLastDecision: "capture_rejected:tab_unavailable", ...clearPreviewState() });
    if (pending) remember(pending.ticketId, "replaced");
    pending = null;
    update({ captureStatus: "capturing", captureErrorCode: null, captureLastDecision: `capture_requested:${mode}`, captureAttachmentOutcome: null, capturePersistenceOutcome: null, captureGuardianCorrelationId: null, ...clearPreviewState() });
    try {
      const before = remoteTab.documentState();
      if (!before.ready) throw new CaptureOperationError("tab_unavailable", "remote_not_ready");
      const raw = await remoteTab.capture(mode);
      const after = remoteTab.documentState();
      if (!after.ready || before.generation !== after.generation || raw.documentGeneration !== after.generation) throw new CaptureOperationError("capture_document_changed", "document_changed_during_capture");
      const runtimeConfig = typeof config === "function" ? config() : config;
      const requestId = runtimeConfig?.guardianAttachmentAdapterEnabled && runtimeConfig.browserHostInstanceId
        ? runtimeConfig.browserHostInstanceId
        : ids("request");
      const envelope = buildEnvelope({ mode, requestId, raw, metadata: after, documentGeneration: after.generation });
      pending = Object.freeze({ ticketId: envelope.captureRequestId, envelope });
      return update(previewState(envelope));
    } catch (error) {
      pending = null;
      return update({ captureStatus: "rejected", captureErrorCode: mapError(error), captureLastDecision: `capture_rejected:${mapError(error)}`, ...clearPreviewState() });
    }
  }

  async function attach(ticketId) {
    if (typeof ticketId !== "string" || ticketId.length === 0) return closedRejection(null);
    if (!pending || pending.ticketId !== ticketId) return closedRejection(ticketId);
    const ticket = pending;
    const remoteTab = getRemoteTab();
    try {
      if (!remoteTab || !remoteTab.documentState().ready) throw new CaptureOperationError("tab_unavailable", "remote_not_ready");
      const current = await remoteTab.documentFingerprint();
      if (current.generation !== ticket.envelope.documentGeneration || current.remoteUrl !== ticket.envelope.sourceUrl || current.remoteOrigin !== ticket.envelope.sourceOrigin || current.documentFingerprint !== ticket.envelope.documentFingerprint) {
        throw new CaptureOperationError("stale_document_generation", "capture_ticket_stale");
      }
      const attachment = buildAttachment({ envelope: ticket.envelope, idempotencyKey: ids("attach") });
      let receipt;
      if (!isFeatureEnabled("capture:attach")) throw new CaptureOperationError("permission_denied", "attachment_feature_disabled");
      try { receipt = await attachEnvelope(typeof config === "function" ? config() : config, attachment); }
      catch (error) { receipt = buildRejectedReceipt(ticket.envelope, mapError(error, "attachment_failed")); }
      pending = null;
      remember(ticket.ticketId, receipt.attachmentOutcome);
      return update({
        captureStatus: receipt.attachmentOutcome === "accepted" ? "attached" : "rejected",
        captureAttachmentOutcome: receipt.attachmentOutcome,
        capturePersistenceOutcome: receipt.persistenceOutcome,
        captureGuardianCorrelationId: receipt.guardianCorrelationId,
        captureErrorCode: receipt.errorCode,
        captureLastDecision: `attachment_${receipt.attachmentOutcome}`
      });
    } catch (error) {
      pending = null;
      remember(ticket.ticketId, "rejected");
      return update({ captureStatus: "rejected", captureErrorCode: mapError(error, "context_rejected"), captureLastDecision: `attachment_rejected:${mapError(error, "context_rejected")}`, captureAttachmentOutcome: "rejected", capturePersistenceOutcome: "not_persisted", captureGuardianCorrelationId: null });
    }
  }

  function cancel(ticketId) {
    if (pending && pending.ticketId === ticketId) {
      remember(ticketId, "cancelled");
      pending = null;
      return update({ captureStatus: "cancelled", captureErrorCode: "user_cancelled", captureLastDecision: "capture_cancelled", captureAttachmentOutcome: "rejected", capturePersistenceOutcome: "not_persisted", captureGuardianCorrelationId: null, ...clearPreviewState() });
    }
    return closedRejection(ticketId);
  }

  function dispose() {
    pending = null;
    closedTickets.clear();
  }

  return Object.freeze({ capture, attach, cancel, dispose, hasPending: () => Boolean(pending) });
}

module.exports = Object.freeze({
  MAX_CAPTURE_BYTES,
  CAPTURE_MODES,
  EXTRACTOR_VERSION,
  SANITIZATION_EVIDENCE,
  CaptureOperationError,
  byteLength,
  truncateUtf8,
  normalizeText,
  sha256,
  buildDocumentFingerprint,
  buildEnvelope,
  buildAttachment,
  buildRejectedReceipt,
  createCaptureController,
  clearPreviewState,
  clearPendingPreviewState
});
