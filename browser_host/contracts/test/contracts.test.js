"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const contracts = require("../index");

const root = path.resolve(__dirname, "..");
const readFixture = (entry) => contracts.loadJson(path.join("fixtures", entry.path));

test("contract metadata, manifest paths, and exports are immutable", () => {
  assert.equal(contracts.contractMetadata.packageName, "@codexify/browser-host-contracts");
  assert.equal(contracts.contractMetadata.protocolVersion, "1.0.0");
  assert.equal(contracts.contractMetadata.envelopeVersion, "1.0.0");
  assert.equal(contracts.contractMetadata.attachmentVersion, "1.0.0");
  assert.equal(contracts.maxCaptureBytes, 65536);
  assert.equal(contracts.contractMetadata.failClosed, true);
  for (const value of [contracts.manifest, contracts.tokens, contracts.schemas, contracts.fixtureIndex, contracts.contractMetadata]) {
    assert.equal(Object.isFrozen(value), true);
  }
  for (const relativePath of [
    ...Object.values(contracts.manifest.schemaPaths),
    contracts.manifest.tokenRegistryPath,
    contracts.manifest.fixtureIndexPath,
    ...contracts.manifest.positiveFixturePaths,
    ...contracts.manifest.negativeFixturePaths
  ]) {
    assert.equal(fs.existsSync(path.join(root, relativePath)), true, relativePath);
  }
});

test("the shared fixture index is the sole validity and expected-error registry", () => {
  const entries = contracts.fixtureIndex.fixtures;
  assert.equal(entries.length, 27);
  assert.equal(entries.filter((entry) => entry.valid).length, 8);
  assert.equal(entries.filter((entry) => !entry.valid).length, 19);
  assert.equal(new Set(entries.map((entry) => entry.id)).size, entries.length);
  for (const entry of entries) {
    assert.equal(typeof entry.expectedError, entry.valid ? "undefined" : "string", entry.id);
  }
});

test("all positive fixtures satisfy the bounded contract", () => {
  for (const entry of contracts.fixtureIndex.fixtures.filter((item) => item.valid)) {
    const result = contracts.validate(entry.kind, readFixture(entry));
    assert.deepEqual(result.errors, [], entry.id);
    assert.equal(result.valid, true, entry.id);
  }
});

test("all negative fixtures fail closed for their recorded reason", () => {
  for (const entry of contracts.fixtureIndex.fixtures.filter((item) => !item.valid)) {
    const result = contracts.validate(entry.kind, readFixture(entry));
    assert.equal(result.valid, false, entry.id);
    assert.equal(result.errors.some((error) => error.code === entry.expectedError), true, `${entry.id}: ${JSON.stringify(result.errors)}`);
  }
});

test("wire objects preserve authority, identity, redaction, and persistence distinctions", () => {
  const envelope = readFixture({path: "valid/envelope-selected-text.json"});
  assert.equal(envelope.userInitiated, true);
  assert.equal(envelope.retentionClass, "ephemeral");
  assert.equal(envelope.requestId !== envelope.captureRequestId, true);
  assert.equal(envelope.sanitizationEvidence.cookiesExcluded, true);
  assert.equal(envelope.sanitizationEvidence.localStorageExcluded, true);
  assert.equal(envelope.sanitizationEvidence.formControlValuesExcluded, true);
  const receipt = readFixture({path: "valid/attachment-receipt-no-persistence.json"});
  assert.equal(receipt.attachmentOutcome, "accepted");
  assert.equal(receipt.persistenceOutcome, "not_persisted");
  assert.equal(Object.hasOwn(receipt, "content"), false);
});

test("the adapter has no runtime, transport, credential, or candidate imports", () => {
  const source = fs.readFileSync(path.join(root, "index.js"), "utf8");
  for (const forbidden of [
    "require(\"electron\")",
    "require(\"playwright\")",
    "BrowserWindow",
    "fetch(",
    "http.request",
    "process.env",
    "process.env",
    "browser_host_candidates",
    "src-tauri",
    "frontend",
    "guardian/"
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});
