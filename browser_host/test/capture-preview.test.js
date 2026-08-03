"use strict";

const path = require("node:path");
const crypto = require("node:crypto");
const test = require("node:test");
const assert = require("node:assert/strict");
const { _electron: electron } = require("playwright");
const { startGuardianStub } = require("./support/guardian-stub");
const { startFixtureServer } = require("./support/fixture-server");

const root = path.resolve(__dirname, "..");
const mainPath = path.join(root, "src", "main.js");
const electronExecutable = require("electron");
const CAPTURE_FEATURES = ["capture:selected", "capture:visible", "capture:attach"];

function token() { return `CODEXIFY-SYNTHETIC-${crypto.randomBytes(18).toString("hex")}`; }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
async function trustedState(trusted) { return trusted.evaluate(() => window.codexifyBrowserHost.getState()); }
async function waitForState(trusted, predicate, timeoutMs = 12000) {
  const started = Date.now();
  let state;
  while (Date.now() - started < timeoutMs) {
    state = await trustedState(trusted);
    if (predicate(state)) return state;
    await sleep(100);
  }
  throw new Error(`state_timeout:${JSON.stringify(state)}`);
}
async function remoteEvaluate(app, script) {
  return app.evaluate(({ BrowserWindow }, source) => {
    const view = BrowserWindow.getAllWindows()[0].contentView.children[0];
    if (!view) throw new Error("remote_view_missing");
    return view.webContents.executeJavaScript(source, true);
  }, script);
}
async function launchScenario({ guardian, fixture, tokenValue }) {
  const instance = await electron.launch({
    executablePath: electronExecutable,
    args: [mainPath],
    cwd: root,
    env: {
      ...process.env,
      CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
      CODEXIFY_BROWSER_HOST_PROOF_TOKEN: tokenValue,
      CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: guardian,
      CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixture
    },
    timeout: 30000
  });
  const trusted = await instance.firstWindow();
  await trusted.waitForLoadState("domcontentloaded");
  await waitForState(trusted, (state) => state.remoteStatus === "ready");
  return { instance, trusted };
}
async function closeInstance(instance) { if (instance) { try { await instance.close(); } catch { /* cleanup is asserted by the proof packet */ } } }
async function navigateToCapture(instance, fixture) {
  await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/capture`)}`);
  await sleep(250);
}
async function selectCaptureText(instance) {
  return remoteEvaluate(instance, `(() => { const node = document.querySelector('#selected-text'); const range = document.createRange(); range.selectNodeContents(node); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); })()`);
}

test("selected and visible capture previews sanitize page data and require a separate ephemeral attachment", async () => {
  const proofToken = token();
  const guardian = await startGuardianStub({ token: proofToken, enabledFeatures: CAPTURE_FEATURES });
  const fixture = await startFixtureServer();
  let instance;
  try {
    const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
    instance = launched.instance;
    const { trusted } = launched;
    await navigateToCapture(instance, fixture);
    assert.equal(await selectCaptureText(instance), "Selected evidence is visible and user-scoped.");
    const selected = await trusted.evaluate(() => window.codexifyBrowserHost.captureSelectedText());
    assert.equal(selected.captureStatus, "preview_ready");
    assert.equal(selected.captureMode, "selected_text");
    assert.match(selected.capturePreviewContent, /Selected evidence/);
    assert.doesNotMatch(selected.capturePreviewContent, /credential-secret|password-secret|hidden-secret|iframe-secret|storage-secret/);
    assert.equal(guardian.attachments.length, 0);

    const selectedTicket = selected.captureTicketId;
    const selectedHtml = await trusted.evaluate(() => document.querySelector("#capture-preview").innerHTML);
    assert.doesNotMatch(selectedHtml, /<script|<img|onerror/i);
    const selectedAttachment = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), selectedTicket);
    assert.equal(selectedAttachment.captureStatus, "attached");
    assert.equal(selectedAttachment.captureAttachmentOutcome, "accepted");
    assert.equal(selectedAttachment.capturePersistenceOutcome, "not_persisted");
    assert.equal(guardian.attachments.length, 1);
    assert.equal(guardian.attachments[0].captureMode, "selected_text");
    assert.equal(guardian.attachments[0].retention, "ephemeral");
    assert.equal(guardian.attachments[0].userConfirmation, "trusted_shell");
    assert.equal(guardian.attachments[0].persisted, false);
    const replayed = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), selectedTicket);
    assert.equal(replayed.captureErrorCode, "context_rejected");
    assert.equal(guardian.attachments.length, 1);

    const visible = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
    assert.equal(visible.captureStatus, "preview_ready");
    assert.equal(visible.captureMode, "visible_page_text");
    assert.match(visible.capturePreviewContent, /Visible evidence/);
    assert.match(visible.capturePreviewContent, /Ignore previous instructions/);
    assert.doesNotMatch(visible.capturePreviewContent, /credential-secret|password-secret|hidden-secret|form-value-secret|iframe-secret|storage-secret/);
    assert.equal(visible.capturePreviewSanitization.localStorageExcluded, true);
    assert.equal(visible.capturePreviewSanitization.crossOriginIframeContentExcluded, true);
    const staleTicket = visible.captureTicketId;
    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/secondary`)}`);
    await waitForState(trusted, (state) => state.remoteUrl.endsWith("/secondary") && state.remoteStatus === "ready");
    const stale = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), staleTicket);
    assert.equal(stale.captureErrorCode, "stale_document_generation");
    assert.equal(guardian.attachments.length, 1);

    const cancelled = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
    const cancelledTicket = cancelled.captureTicketId;
    const cancelledState = await trusted.evaluate((ticket) => window.codexifyBrowserHost.cancelCapture(ticket), cancelledTicket);
    assert.equal(cancelledState.captureStatus, "cancelled");
    assert.equal(cancelledState.captureErrorCode, "user_cancelled");
    const cancelledReplay = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), cancelledTicket);
    assert.equal(cancelledReplay.captureErrorCode, "context_rejected");
    assert.equal(guardian.attachments.length, 1);
    assert.equal(await trusted.evaluate(() => document.title), "Codexify Browser Host");
  } finally {
    await closeInstance(instance);
    await guardian.close();
    await fixture.close();
  }
});

test("deterministic attachment failure keeps the trusted shell and preview usable without persistence", async () => {
  const proofToken = token();
  const guardian = await startGuardianStub({ token: proofToken, enabledFeatures: CAPTURE_FEATURES, attachmentMode: "failed" });
  const fixture = await startFixtureServer();
  let instance;
  try {
    const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
    instance = launched.instance;
    const { trusted } = launched;
    await navigateToCapture(instance, fixture);
    const preview = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
    const failed = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
    assert.equal(failed.captureStatus, "rejected");
    assert.equal(failed.captureAttachmentOutcome, "rejected");
    assert.equal(failed.captureErrorCode, "attachment_failed");
    assert.equal(failed.capturePersistenceOutcome, "not_persisted");
    assert.match(failed.capturePreviewContent, /Visible evidence/);
    assert.equal(guardian.attachments.length, 1);
    assert.equal(guardian.receipts[0].attachmentOutcome, "rejected");
    const replay = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
    assert.equal(replay.captureErrorCode, "context_rejected");
    assert.equal(guardian.attachments.length, 1);
    assert.equal(await trusted.evaluate(() => document.title), "Codexify Browser Host");
  } finally {
    await closeInstance(instance);
    await guardian.close();
    await fixture.close();
  }
});
