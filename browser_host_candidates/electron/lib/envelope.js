const crypto = require("node:crypto");
const { MAX_CAPTURE_BYTES, PREVIEW_BYTES, EXTRACTOR_VERSION } = require("./constants");
const { parseOrigin } = require("./security");

function hashContent(content) {
  return crypto.createHash("sha256").update(content, "utf8").digest("hex");
}

function truncateUtf8(content, budget = MAX_CAPTURE_BYTES) {
  const source = String(content);
  const bytes = Buffer.from(source, "utf8");
  if (bytes.length <= budget) return { content: source, truncated: false, originalLength: bytes.length };
  return {
    content: bytes.subarray(0, budget).toString("utf8"),
    truncated: true,
    originalLength: bytes.length
  };
}

function makeEnvelope({
  runId,
  sourceUrl,
  sourceTitle,
  captureMode,
  content,
  captureRequestId,
  requestId,
  attemptNumber,
  userInitiated,
  documentGeneration,
  documentFingerprint
}) {
  if (!userInitiated) throw new Error("user_initiation_required");
  const bounded = truncateUtf8(content);
  const sourceOrigin = parseOrigin(sourceUrl);
  return {
    runId,
    contextId: `context-${crypto.randomBytes(12).toString("hex")}`,
    captureRequestId,
    sourceKind: "browser_page",
    sourceUrl,
    sourceOrigin,
    sourceTitle: String(sourceTitle).slice(0, 512),
    capturedAt: new Date().toISOString(),
    captureMode,
    contentType: "text/plain",
    content: bounded.content,
    contentHash: hashContent(bounded.content),
    contentLength: Buffer.byteLength(bounded.content, "utf8"),
    truncated: bounded.truncated,
    originalContentLength: bounded.originalLength,
    documentGeneration,
    documentFingerprint,
    extractorVersion: EXTRACTOR_VERSION,
    permissionScope: "browser_context_capture_only",
    retentionClass: "ephemeral",
    userInitiated: true,
    requestId,
    attemptNumber: Number(attemptNumber) || 1
  };
}

function safePreview(envelope) {
  return {
    contextId: envelope.contextId,
    captureRequestId: envelope.captureRequestId,
    sourceKind: envelope.sourceKind,
    sourceUrl: envelope.sourceUrl,
    sourceOrigin: envelope.sourceOrigin,
    sourceTitle: envelope.sourceTitle,
    captureMode: envelope.captureMode,
    contentLength: envelope.contentLength,
    originalContentLength: envelope.originalContentLength,
    truncated: envelope.truncated,
    contentPreview: envelope.content.slice(0, PREVIEW_BYTES),
    permissionScope: envelope.permissionScope,
    retentionClass: envelope.retentionClass,
    userInitiated: envelope.userInitiated,
    requestId: envelope.requestId,
    attemptNumber: envelope.attemptNumber,
    contentHash: envelope.contentHash
  };
}

module.exports = { hashContent, truncateUtf8, makeEnvelope, safePreview };
