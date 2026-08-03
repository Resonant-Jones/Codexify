"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const contracts = require("../contracts");
const {
  MAX_CAPTURE_BYTES,
  buildEnvelope,
  buildAttachment,
  buildRejectedReceipt,
  truncateUtf8,
  buildDocumentFingerprint
} = require("../src/runtime/capture");

const metadata = {
  remoteUrl: "http://127.0.0.1:43123/capture",
  remoteOrigin: "http://127.0.0.1:43123",
  remoteTitle: "Capture fixture"
};

function raw(overrides = {}) {
  const visibleText = "Visible evidence remains untrusted page content.";
  return {
    selectedText: "Selected evidence is visible and user-scoped.",
    selectedTextOriginalLength: Buffer.byteLength("Selected evidence is visible and user-scoped."),
    visibleText,
    visibleTextOriginalLength: Buffer.byteLength(visibleText),
    ...overrides
  };
}

test("trusted capture construction produces a versioned, sanitized selected-text envelope", () => {
  const envelope = buildEnvelope({ mode: "selected_text", requestId: "request-test-1", raw: raw(), metadata, documentGeneration: 3 });
  assert.equal(envelope.captureMode, "selected_text");
  assert.equal(envelope.userInitiated, true);
  assert.equal(envelope.retentionClass, "ephemeral");
  assert.equal(envelope.permissionScope, "browser_context_capture_only");
  assert.equal(envelope.sanitizationEvidence.localStorageExcluded, true);
  assert.equal(contracts.validate("envelope", envelope).valid, true);
});

test("visible-page content is bounded without splitting UTF-8 code points", () => {
  const content = truncateUtf8("🙂".repeat(MAX_CAPTURE_BYTES), MAX_CAPTURE_BYTES);
  assert.ok(Buffer.byteLength(content) <= MAX_CAPTURE_BYTES);
  assert.doesNotThrow(() => JSON.stringify(content));
  const fingerprint = buildDocumentFingerprint({ sourceUrl: metadata.remoteUrl, sourceTitle: metadata.remoteTitle, visibleText: content, visibleTextOriginalLength: MAX_CAPTURE_BYTES + 4 });
  assert.match(fingerprint, /^[a-f0-9]{64}$/);
});

test("attachment construction requires trusted-shell confirmation and rejected receipts never persist", () => {
  const envelope = buildEnvelope({ mode: "visible_page_text", requestId: "request-test-2", raw: raw(), metadata, documentGeneration: 1 });
  const attachment = buildAttachment({ envelope, idempotencyKey: "attach-test-2" });
  assert.equal(attachment.userConfirmation.method, "trusted_shell");
  assert.equal(attachment.requestedRetention, "ephemeral");
  assert.equal(contracts.validate("attachment", attachment).valid, true);
  const receipt = buildRejectedReceipt(envelope, "attachment_failed");
  assert.equal(receipt.persistenceOutcome, "not_persisted");
  assert.equal(receipt.guardianCorrelationId, null);
  assert.equal(contracts.validate("receipt", receipt).valid, true);
});
