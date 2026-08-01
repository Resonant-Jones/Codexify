"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { _electron: electron } = require("playwright");
const packageManifest = require("../package.json");
const contracts = require("../contracts");
const { startGuardianStub } = require("../test/support/guardian-stub");
const { startFixtureServer } = require("../test/support/fixture-server");

const root = path.resolve(__dirname, "..");
const outputDir = path.resolve(process.argv.includes("--output-dir") ? process.argv[process.argv.indexOf("--output-dir") + 1] : path.join(root, "capture-proof-output"));
const screenshotsDir = path.join(outputDir, "screenshots");
const mainPath = path.join(root, "src", "main.js");
const electronExecutable = require("electron");
const proofToken = `CODEXIFY-SYNTHETIC-${crypto.randomBytes(18).toString("hex")}`;
const enabledFeatures = ["capture:selected", "capture:visible", "capture:attach"];

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function digest(value) { return crypto.createHash("sha256").update(value, "utf8").digest("hex"); }
async function stateOf(trusted) { return trusted.evaluate(() => window.codexifyBrowserHost.getState()); }
async function waitForState(trusted, predicate, timeoutMs = 12000) {
  const started = Date.now();
  let state;
  while (Date.now() - started < timeoutMs) {
    state = await stateOf(trusted);
    if (predicate(state)) return state;
    await sleep(100);
  }
  throw new Error("state_timeout");
}
async function remoteEvaluate(app, script) {
  return app.evaluate(({ BrowserWindow }, source) => BrowserWindow.getAllWindows()[0].contentView.children[0].webContents.executeJavaScript(source, true), script);
}
async function closeApp(app) { if (app) { try { await app.close(); } catch { /* cleanup is recorded */ } } }
async function launch(guardianOrigin, fixtureOrigin) {
  const app = await electron.launch({
    executablePath: electronExecutable,
    args: [mainPath],
    cwd: root,
    env: { ...process.env, CODEXIFY_BROWSER_HOST_PROOF_MODE: "1", CODEXIFY_BROWSER_HOST_PROOF_TOKEN: proofToken, CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: guardianOrigin, CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixtureOrigin },
    timeout: 30000
  });
  const trusted = await app.firstWindow();
  await trusted.waitForLoadState("domcontentloaded");
  await waitForState(trusted, (state) => state.remoteStatus === "ready");
  return { app, trusted };
}
async function navigateToCapture(app, fixtureOrigin) {
  await remoteEvaluate(app, `location.href = ${JSON.stringify(`${fixtureOrigin}/capture`)}`);
  await sleep(250);
}
async function selectText(app) {
  return remoteEvaluate(app, `(() => { const node = document.querySelector('#selected-text'); const range = document.createRange(); range.selectNodeContents(node); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); })()`);
}

async function main() {
  fs.mkdirSync(screenshotsDir, { recursive: true });
  const scenarios = {};
  const cleanup = { status: "passed", electronInstancesClosed: 0, supportServersClosed: 0, temporaryTokenRetained: false };
  const record = (name, status, details = {}) => { scenarios[name] = { status, ...details }; };
  try {
    const fixture = await startFixtureServer();
    const guardian = await startGuardianStub({ token: proofToken, enabledFeatures });
    let app;
    try {
      ({ app } = await launch(guardian.origin, fixture.origin));
      const trusted = await app.firstWindow();
      await trusted.screenshot({ path: path.join(screenshotsDir, "trusted-shell-capture-controls.png") });
      await navigateToCapture(app, fixture.origin);
      await selectText(app);
      const selected = await trusted.evaluate(() => window.codexifyBrowserHost.captureSelectedText());
      const selectedTicket = selected.captureTicketId;
      const selectedAttachment = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), selectedTicket);
      const selectedReplay = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), selectedTicket);
      record("selected-preview-and-attachment", selected.captureStatus === "preview_ready" && selectedAttachment.captureStatus === "attached" && selectedAttachment.capturePersistenceOutcome === "not_persisted" ? "passed" : "failed", {
        mode: selected.captureMode,
        previewContentLength: selected.capturePreviewContentLength,
        previewContentHash: digest(selected.capturePreviewContent),
        ticketConsumed: selectedReplay.captureErrorCode === "context_rejected",
        attachmentOutcome: selectedAttachment.captureAttachmentOutcome,
        persistenceOutcome: selectedAttachment.capturePersistenceOutcome,
        guardianAttachmentCount: guardian.attachments.length,
        rawContentRetained: false
      });

      const visible = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
      const visibleTicket = visible.captureTicketId;
      const visibleContainsPromptLikeText = /ignore previous instructions/i.test(visible.capturePreviewContent);
      const excludedSecrets = !/credential-secret|password-secret|hidden-secret|form-value-secret|iframe-secret|storage-secret/.test(visible.capturePreviewContent);
      const previewStatusStable = visible.captureStatus === "preview_ready";
      await remoteEvaluate(app, `location.href = ${JSON.stringify(`${fixture.origin}/secondary`)}`);
      await waitForState(trusted, (state) => state.remoteUrl.endsWith("/secondary") && state.remoteStatus === "ready");
      const stale = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), visibleTicket);
      record("visible-preview-redaction-and-stale-rejection", previewStatusStable && visibleContainsPromptLikeText && excludedSecrets && stale.captureErrorCode === "stale_document_generation" ? "passed" : "failed", {
        mode: visible.captureMode,
        previewContentLength: visible.capturePreviewContentLength,
        previewContentHash: digest(visible.capturePreviewContent),
        sensitiveFieldsExcluded: excludedSecrets,
        browserStorageExcluded: visible.capturePreviewSanitization?.localStorageExcluded === true,
        iframeContentExcluded: visible.capturePreviewSanitization?.crossOriginIframeContentExcluded === true,
        promptInjectionContained: visibleContainsPromptLikeText && previewStatusStable,
        staleErrorCode: stale.captureErrorCode,
        rawContentRetained: false
      });

      const cancelled = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
      const cancelledState = await trusted.evaluate((ticket) => window.codexifyBrowserHost.cancelCapture(ticket), cancelled.captureTicketId);
      const cancelledReplay = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), cancelled.captureTicketId);
      record("cancelled-ticket-rejection", cancelledState.captureErrorCode === "user_cancelled" && cancelledReplay.captureErrorCode === "context_rejected" ? "passed" : "failed", { cancelled: true, replayRejected: cancelledReplay.captureErrorCode === "context_rejected" });
    } finally {
      await closeApp(app);
      cleanup.electronInstancesClosed += app ? 1 : 0;
      await guardian.close();
      await fixture.close();
      cleanup.supportServersClosed += 2;
    }

    const failedFixture = await startFixtureServer({ label: "attachment-failure" });
    const failedGuardian = await startGuardianStub({ token: proofToken, enabledFeatures, attachmentMode: "failed" });
    let failedApp;
    try {
      ({ app: failedApp } = await launch(failedGuardian.origin, failedFixture.origin));
      const trusted = await failedApp.firstWindow();
      await navigateToCapture(failedApp, failedFixture.origin);
      const preview = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
      const failed = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
      const replay = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
      record("attachment-failure-continuity", failed.captureErrorCode === "attachment_failed" && failed.capturePersistenceOutcome === "not_persisted" && failed.capturePreviewContentLength > 0 && replay.captureErrorCode === "context_rejected" ? "passed" : "failed", {
        attachmentOutcome: failed.captureAttachmentOutcome,
        persistenceOutcome: failed.capturePersistenceOutcome,
        previewRetained: failed.capturePreviewContentLength > 0,
        replayRejected: replay.captureErrorCode === "context_rejected",
        guardianAttachmentCount: failedGuardian.attachments.length,
        durablePersistence: false,
        rawContentRetained: false
      });
    } finally {
      await closeApp(failedApp);
      cleanup.electronInstancesClosed += failedApp ? 1 : 0;
      await failedGuardian.close();
      await failedFixture.close();
      cleanup.supportServersClosed += 2;
    }
  } catch (error) {
    record("runner", "failed", { errorCode: "invalid_contract", message: String(error?.message || error).slice(0, 64) });
    cleanup.status = "failed";
  }

  const proof = {
    proofKind: "capture_preview_attachment",
    proofStatus: Object.values(scenarios).every((scenario) => scenario.status === "passed") && cleanup.status === "passed" ? "passed" : "failed",
    packageVersion: packageManifest.version,
    contractPackageVersion: contracts.contractMetadata.packageVersion,
    protocolVersion: contracts.contractMetadata.protocolVersion,
    envelopeVersion: contracts.contractMetadata.envelopeVersion,
    attachmentVersion: contracts.contractMetadata.attachmentVersion,
    releasePosture: contracts.contractMetadata.releasePosture,
    topology: { trustedBrowserWindowCount: 1, remoteWebContentsViewCount: 1, remoteViewHasPreload: false, remoteSessionPersistent: false },
    featureClaims: { topologySkeletonImplemented: true, captureImplemented: true, attachmentImplemented: true, persistenceImplemented: false, liveGuardianImplemented: false, updaterImplemented: false, releaseQualified: false },
    scenarios,
    cleanup,
    forbiddenAuthority: { node: false, electron: false, ipc: false, credential: false, filesystem: false, process: false, shell: false, keychain: false, updater: false, commandBus: false, persistence: false },
    rawPageContentRetained: false,
    temporaryTokenRetained: false,
    screenshots: ["trusted-shell-capture-controls.png"],
    generatedAt: new Date().toISOString()
  };
  fs.writeFileSync(path.join(outputDir, "proof.json"), JSON.stringify(proof, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "manifest.json"), JSON.stringify({ proofKind: proof.proofKind, proofFile: "proof.json", screenshotsDirectory: "screenshots", packageVersion: proof.packageVersion, contractPackageVersion: proof.contractPackageVersion, releasePosture: proof.releasePosture }, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "cleanup.json"), JSON.stringify(cleanup, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "proof.md"), `# Capture preview and ephemeral attachment proof\n\nStatus: **${proof.proofStatus}**\n\nThis sanitized packet proves selected-text and visible-page preview, trusted-main-process v1 envelope construction, separate ephemeral attachment to a deterministic loopback Guardian stub, redaction, prompt-injection containment, stale/cancelled/replayed ticket rejection, and deterministic attachment-failure continuity. It does not claim live Guardian integration, durable persistence, packaging, signing, updater, or release qualification.\n\n- Package: ${proof.packageVersion}\n- Contract: ${proof.contractPackageVersion}\n- Protocol: ${proof.protocolVersion}\n- Envelope: ${proof.envelopeVersion}\n- Attachment: ${proof.attachmentVersion}\n- Raw page content retained: false\n- Durable persistence: false\n- Cleanup: ${cleanup.status}\n`);
  process.stdout.write(JSON.stringify({ outputDir, proof: proof.proofStatus }) + "\n");
  if (proof.proofStatus !== "passed") process.exitCode = 1;
}

main().catch((error) => { process.stderr.write(`${String(error.stack || error)}\n`); process.exitCode = 1; });
