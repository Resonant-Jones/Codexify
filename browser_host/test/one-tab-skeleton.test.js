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
    const window = BrowserWindow.getAllWindows()[0];
    const child = window.contentView.children[0];
    if (!child) throw new Error("remote_view_missing");
    return child.webContents.executeJavaScript(source, true);
  }, script);
}

async function launchScenario({ guardian, fixture, tokenValue, timeout = 1500 }) {
  const instance = await electron.launch({
    executablePath: electronExecutable,
    args: [mainPath],
    cwd: root,
    env: {
      ...process.env,
      CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
      CODEXIFY_BROWSER_HOST_PROOF_TOKEN: tokenValue,
      CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: guardian,
      CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixture,
      CODEXIFY_BROWSER_HOST_NEGOTIATION_TIMEOUT_MS: String(timeout)
    },
    timeout: 30000
  });
  const trusted = await instance.firstWindow();
  await trusted.waitForLoadState("domcontentloaded");
  return { instance, trusted };
}

async function closeInstance(instance) {
  if (!instance) return;
  try { await instance.close(); } catch { /* cleanup is asserted by the proof runner */ }
}

test("compatible negotiation creates exactly one isolated remote view after the trusted shell", async () => {
  const proofToken = token();
  const guardian = await startGuardianStub({ token: proofToken });
  const fixture = await startFixtureServer();
  const otherFixture = await startFixtureServer({ label: "cross-origin" });
  let instance;
  try {
    const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
    instance = launched.instance;
    const trusted = launched.trusted;
    const state = await waitForState(trusted, (value) => value.remoteStatus === "ready");
    assert.equal(state.guardianCompatibilityOutcome, "compatible");
    assert.equal(state.remoteViewCreated, true);
    assert.equal(state.remoteLoadedAfterNegotiation, true);
    assert.equal(state.enabledFeatures.length, 0);
    assert.equal(state.captureImplemented, true);
    assert.equal(state.attachmentImplemented, true);
    assert.equal(state.persistenceImplemented, false);
    assert.equal(guardian.requests.length, 1);
    assert.ok(fixture.requests.length >= 1);

    const bridge = await trusted.evaluate(() => ({
      keys: Object.keys(window.codexifyBrowserHost).sort(),
      require: typeof globalThis.require,
      process: typeof globalThis.process
    }));
    assert.deepEqual(bridge.keys, ["attachCapture", "cancelCapture", "captureSelectedText", "captureVisiblePage", "getState", "onStateChanged", "reloadRemote"]);
    assert.equal(bridge.require, "undefined");
    assert.equal(bridge.process, "undefined");
    assert.deepEqual(await trusted.evaluate(async () => Object.keys(await window.codexifyBrowserHost.getState())), Object.keys(state));

    const remoteGlobals = await remoteEvaluate(instance, `({
      require: typeof globalThis.require,
      process: typeof globalThis.process,
      electron: typeof globalThis.electron,
      bridge: typeof globalThis.codexifyBrowserHost,
      ipc: typeof globalThis.ipcRenderer,
      tokenPresent: document.documentElement.outerHTML.includes(${JSON.stringify(proofToken)})
    })`);
    assert.deepEqual(remoteGlobals, { require: "undefined", process: "undefined", electron: "undefined", bridge: "undefined", ipc: "undefined", tokenPresent: false });
    assert.equal(await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children.length), 1);

    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/secondary`)}`);
    await waitForState(trusted, (value) => value.remoteUrl.endsWith("/secondary") && value.remoteStatus === "ready");
    const requestsBeforeReload = fixture.requests.length;
    await trusted.evaluate(() => window.codexifyBrowserHost.reloadRemote());
    await waitForState(trusted, (value) => value.remoteStatus === "ready" && value.remoteUrl.endsWith("/secondary"));
    assert.ok(fixture.requests.length > requestsBeforeReload);

    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/popup`)}`);
    await waitForState(trusted, (value) => value.remoteUrl.endsWith("/popup"));
    const popupResult = await remoteEvaluate(instance, `document.querySelector("#popup").click(); window.__popupResult === null`);
    assert.equal(popupResult, true);
    await waitForState(trusted, (value) => value.lastPolicyDecision === "popup_denied");

    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/download`)}`);
    await waitForState(trusted, (value) => value.remoteUrl.endsWith("/download"));
    await remoteEvaluate(instance, `document.querySelector("#download").click(); "clicked"`);
    await waitForState(trusted, (value) => value.lastPolicyDecision === "download_denied");

    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${fixture.origin}/permission`)}`);
    await waitForState(trusted, (value) => value.remoteUrl.endsWith("/permission"));
    await sleep(250);
    assert.equal(await remoteEvaluate(instance, "window.__permissionResult"), 1);

    await remoteEvaluate(instance, `location.href = ${JSON.stringify(`${otherFixture.origin}/`)}`);
    await sleep(400);
    const deniedCrossOrigin = await trustedState(trusted);
    assert.equal(deniedCrossOrigin.remoteOrigin, fixture.origin);
    assert.match(deniedCrossOrigin.lastPolicyDecision, /navigation_denied/);

    await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].setBounds({ width: 900, height: 650 }));
    await sleep(200);
    const bounds = await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children[0].getBounds());
    const contentHeight = await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getContentBounds().height);
    assert.equal(bounds.width, 900);
    assert.equal(bounds.height, contentHeight - 104);
  } finally {
    await closeInstance(instance);
    await guardian.close();
    await fixture.close();
    await otherFixture.close();
  }
});

for (const mode of ["incompatible", "malformed"]) {
  test(`${mode} negotiation fails closed without creating a remote view`, async () => {
    const proofToken = token();
    const guardian = await startGuardianStub({ token: proofToken, mode });
    const fixture = await startFixtureServer();
    let instance;
    try {
      const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
      instance = launched.instance;
      const state = await waitForState(launched.trusted, (value) => value.runtimeStatus === "degraded");
      assert.equal(state.remoteViewCreated, false);
      assert.equal(state.remoteStatus, "not_created");
      assert.equal(state.remoteLoadedAfterNegotiation, false);
      assert.equal(state.guardianCompatibilityOutcome, mode === "incompatible" ? "incompatible" : "malformed");
      assert.equal(fixture.requests.length, 0);
      assert.equal(await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children.length), 0);
      assert.equal(await launched.trusted.evaluate(() => typeof window.codexifyBrowserHost.getState), "function");
    } finally {
      await closeInstance(instance);
      await guardian.close();
      await fixture.close();
    }
  });
}

test("unreachable Guardian fails closed while the trusted shell remains available", async () => {
  const proofToken = token();
  const fixture = await startFixtureServer();
  let instance;
  try {
    const launched = await launchScenario({ guardian: "http://127.0.0.1:9", fixture: fixture.origin, tokenValue: proofToken, timeout: 300 });
    instance = launched.instance;
    const state = await waitForState(launched.trusted, (value) => value.runtimeStatus === "degraded");
    assert.equal(state.errorCode, "guardian_rejected");
    assert.equal(state.remoteViewCreated, false);
    assert.equal(fixture.requests.length, 0);
    assert.equal(await launched.trusted.evaluate(() => document.title), "Codexify Browser Host");
  } finally {
    await closeInstance(instance);
    await fixture.close();
  }
});

test("fixture load failure removes the remote view and preserves fail-closed state", async () => {
  const proofToken = token();
  const guardian = await startGuardianStub({ token: proofToken, responseDelayMs: 250 });
  const fixture = await startFixtureServer();
  let instance;
  try {
    setTimeout(() => { fixture.close().catch(() => {}); }, 50);
    const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
    instance = launched.instance;
    const state = await waitForState(launched.trusted, (value) => value.runtimeStatus === "degraded");
    assert.equal(state.remoteViewCreated, false);
    assert.equal(state.remoteLoadedAfterNegotiation, false);
    assert.equal(state.remoteStatus, "not_created");
    assert.equal(await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children.length), 0);
  } finally {
    await closeInstance(instance);
    await guardian.close();
    await fixture.close();
  }
});

test("remote renderer termination degrades the view without recreating it", async () => {
  const proofToken = token();
  const guardian = await startGuardianStub({ token: proofToken });
  const fixture = await startFixtureServer();
  let instance;
  try {
    const launched = await launchScenario({ guardian: guardian.origin, fixture: fixture.origin, tokenValue: proofToken });
    instance = launched.instance;
    await waitForState(launched.trusted, (value) => value.remoteStatus === "ready");
    await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children[0].webContents.forcefullyCrashRenderer());
    const state = await waitForState(launched.trusted, (value) => value.remoteStatus === "degraded", 15000);
    assert.equal(state.remoteProcessState, "terminated");
    assert.equal(await launched.trusted.evaluate(() => document.title), "Codexify Browser Host");
    assert.equal(await instance.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children.length), 1);
  } finally {
    await closeInstance(instance);
    await guardian.close();
    await fixture.close();
  }
});
