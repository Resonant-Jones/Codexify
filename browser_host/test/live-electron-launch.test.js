"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

function runDiagnosticInChild() {
  const script = path.join(__dirname, "..", "scripts", "diagnose-live-electron-launch.js");
  const result = spawnSync(process.execPath, [script], { cwd: path.resolve(__dirname, ".."), encoding: "utf8", timeout: 60000 });
  const output = result.stdout.trim();
  return { result, diagnostic: JSON.parse(output) };
}

test("live Electron launch reaches the trusted shell and gates deterministic remote loading", async (t) => {
  const { result: child, diagnostic } = runDiagnosticInChild();
  assert.equal(child.error, undefined, child.error?.message);
  assert.equal(child.status, 0, child.stderr);
  if (diagnostic.primaryClassification === "graphical_session_unavailable") {
    t.skip("graphical user session unavailable; proof remains next-proof-needed");
    return;
  }
  assert.equal(diagnostic.status, "passed", JSON.stringify({
    status: diagnostic.status,
    classification: diagnostic.primaryClassification,
    binarySignal: diagnostic.binary.version.signal,
    launchFailed: Boolean(diagnostic.playwright.failure),
    missing: diagnostic.playwright.trustedWindowCreated ? [] : ["trusted_window"]
  }));
  assert.equal(diagnostic.playwright.trustedUrlIsLocalFile, true);
  assert.equal(diagnostic.playwright.preloadLoaded, true);
  assert.equal(diagnostic.playwright.trustedStateRead, true);
  assert.equal(diagnostic.playwright.negotiationCompatible, true);
  assert.equal(diagnostic.playwright.remoteRequestBeforeCompatibility, false);
  assert.equal(diagnostic.playwright.remoteLoadedAfterCompatibility, true);
  assert.deepEqual(diagnostic.playwright.rendererAuthorityDenialResult, { node: false, electron: false, bridge: false, ipc: false });
  assert.equal(diagnostic.playwright.captureAttempted, false);
  assert.equal(diagnostic.playwright.attachmentAttempted, false);
  assert.equal(diagnostic.playwright.cleanupResult, "passed");
  assert.equal(diagnostic.playwright.temporaryProfileRemaining, false);
});
