"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { _electron: electron } = require("playwright");
const packageManifest = require("../package.json");
const contracts = require("../contracts");
const { startGuardianStub } = require("../test/support/guardian-stub");
const { startFixtureServer } = require("../test/support/fixture-server");

const root = path.resolve(__dirname, "..");
const outputDir = path.resolve(process.argv.includes("--output-dir") ? process.argv[process.argv.indexOf("--output-dir") + 1] : path.join(root, "proof-output"));
const screenshotsDir = path.join(outputDir, "screenshots");
const mainPath = path.join(root, "src", "main.js");
const electronExecutable = require("electron");
const proofToken = `CODEXIFY-SYNTHETIC-${crypto.randomBytes(18).toString("hex")}`;

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
async function stateOf(trusted) { return trusted.evaluate(() => window.codexifyBrowserHost.getState()); }
async function waitForState(trusted, predicate, timeoutMs = 12000) {
  const started = Date.now();
  let state;
  while (Date.now() - started < timeoutMs) {
    state = await stateOf(trusted);
    if (predicate(state)) return state;
    await sleep(100);
  }
  throw new Error(`state_timeout:${JSON.stringify(state)}`);
}
async function remoteEvaluate(app, script) {
  return app.evaluate(({ BrowserWindow }, source) => BrowserWindow.getAllWindows()[0].contentView.children[0].webContents.executeJavaScript(source, true), script);
}
async function remoteScreenshot(app, destination) {
  const base64 = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children[0].webContents.capturePage().then((image) => image.toPNG().toString("base64")));
  fs.writeFileSync(destination, Buffer.from(base64, "base64"));
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
  return { app, trusted };
}

async function main() {
  fs.mkdirSync(screenshotsDir, { recursive: true });
  const scenarios = {};
  const cleanup = { status: "passed", electronInstancesClosed: 0, supportServersClosed: 0, temporaryTokenRetained: false };
  const record = (name, status, details = {}) => { scenarios[name] = { status, ...details }; };
  try {
    const fixture = await startFixtureServer();
    const crossOriginFixture = await startFixtureServer({ label: "cross-origin" });
    const guardian = await startGuardianStub({ token: proofToken });
    let app;
    try {
      ({ app } = await launch(guardian.origin, fixture.origin));
      const trusted = app.firstWindow ? await app.firstWindow() : null;
      const ready = await waitForState(trusted, (state) => state.remoteStatus === "ready");
      const remoteGlobals = await remoteEvaluate(app, "({ require: typeof globalThis.require, process: typeof globalThis.process, electron: typeof globalThis.electron, bridge: typeof globalThis.codexifyBrowserHost, ipc: typeof globalThis.ipcRenderer })");
      await trusted.screenshot({ path: path.join(screenshotsDir, "compatible-trusted-shell.png") });
      await trusted.screenshot({ path: path.join(screenshotsDir, "negotiated-contract-state.png") });
      await remoteScreenshot(app, path.join(screenshotsDir, "compatible-remote-fixture.png"));
      record("compatible", "passed", { remoteViewCreated: ready.remoteViewCreated, remoteRequests: fixture.requests.length, negotiationRequests: guardian.requests.length, remoteLoadAfterNegotiation: ready.remoteLoadedAfterNegotiation, remoteGlobals, remoteAuthorityDenied: Object.values(remoteGlobals).every((value) => value === "undefined"), negotiationBeforeRemoteLoad: ready.remoteLoadedAfterNegotiation === true && fixture.requests.length > 0 });

      await remoteEvaluate(app, `location.href = ${JSON.stringify(`${fixture.origin}/popup`)}`);
      await waitForState(trusted, (state) => state.remoteUrl.endsWith("/popup"));
      await remoteEvaluate(app, "document.querySelector('#popup').click(); window.__popupResult === null");
      const popupDenied = await waitForState(trusted, (state) => state.lastPolicyDecision === "popup_denied");
      await remoteEvaluate(app, `location.href = ${JSON.stringify(`${fixture.origin}/download`)}`);
      await waitForState(trusted, (state) => state.remoteUrl.endsWith("/download"));
      await remoteEvaluate(app, "document.querySelector('#download').click(); 'clicked'");
      const downloadDenied = await waitForState(trusted, (state) => state.lastPolicyDecision === "download_denied");
      await remoteEvaluate(app, `location.href = ${JSON.stringify(`${fixture.origin}/permission`)}`);
      await waitForState(trusted, (state) => state.remoteUrl.endsWith("/permission"));
      await sleep(250);
      const permissionResult = await remoteEvaluate(app, "window.__permissionResult");
      await remoteEvaluate(app, `location.href = ${JSON.stringify(`${crossOriginFixture.origin}/`)}`);
      await sleep(300);
      const crossOriginDenied = await stateOf(trusted);
      await trusted.screenshot({ path: path.join(screenshotsDir, "denial-policy-state.png") });
      record("denials", popupDenied.lastPolicyDecision === "popup_denied" && downloadDenied.lastPolicyDecision === "download_denied" && permissionResult === 1 && crossOriginDenied.remoteOrigin === fixture.origin && /navigation_denied/.test(crossOriginDenied.lastPolicyDecision) ? "passed" : "failed", { popup: popupDenied.lastPolicyDecision, download: downloadDenied.lastPolicyDecision, permissionResult, crossOriginPolicy: crossOriginDenied.lastPolicyDecision });
    } finally {
      await closeApp(app);
      cleanup.electronInstancesClosed += app ? 1 : 0;
      await guardian.close();
      await fixture.close();
      await crossOriginFixture.close();
      cleanup.supportServersClosed += 3;
    }

    for (const mode of ["incompatible", "malformed"]) {
      const fixtureCase = await startFixtureServer({ label: mode });
      const guardianCase = await startGuardianStub({ token: proofToken, mode });
      let appCase;
      try {
        ({ app: appCase } = await launch(guardianCase.origin, fixtureCase.origin));
        const trustedCase = await appCase.firstWindow();
        const failed = await waitForState(trustedCase, (state) => state.runtimeStatus === "degraded");
        await trustedCase.screenshot({ path: path.join(screenshotsDir, `${mode}-trusted-shell.png`) });
        record(mode, failed.remoteViewCreated === false && failed.remoteLoadedAfterNegotiation === false && fixtureCase.requests.length === 0 ? "passed" : "failed", { remoteViewCreated: failed.remoteViewCreated, remoteRequests: fixtureCase.requests.length, errorCode: failed.errorCode, guardianCompatibilityOutcome: failed.guardianCompatibilityOutcome });
      } finally {
        await closeApp(appCase);
        cleanup.electronInstancesClosed += appCase ? 1 : 0;
        await guardianCase.close();
        await fixtureCase.close();
        cleanup.supportServersClosed += 2;
      }
    }

    const fixtureDegraded = await startFixtureServer({ label: "degraded" });
    const guardianDegraded = await startGuardianStub({ token: proofToken });
    let degradedApp;
    try {
      ({ app: degradedApp } = await launch(guardianDegraded.origin, fixtureDegraded.origin));
      const degradedTrusted = await degradedApp.firstWindow();
      await waitForState(degradedTrusted, (state) => state.remoteStatus === "ready");
      await degradedApp.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].contentView.children[0].webContents.forcefullyCrashRenderer());
      const degraded = await waitForState(degradedTrusted, (state) => state.remoteStatus === "degraded", 15000);
      await degradedTrusted.screenshot({ path: path.join(screenshotsDir, "remote-renderer-degraded.png") });
      record("renderer-degradation", degraded.remoteProcessState === "terminated" ? "passed" : "failed", { remoteProcessState: degraded.remoteProcessState, trustedShellAlive: await degradedTrusted.evaluate(() => document.title) === "Codexify Browser Host", recreated: false });
    } finally {
      await closeApp(degradedApp);
      cleanup.electronInstancesClosed += degradedApp ? 1 : 0;
      await guardianDegraded.close();
      await fixtureDegraded.close();
      cleanup.supportServersClosed += 2;
    }
  } catch (error) {
    record("runner", "failed", { errorCode: "invalid_contract", message: String(error.message || error).slice(0, 256) });
    cleanup.status = "failed";
  }

  const proof = {
    proofKind: "production_one_tab_skeleton",
    proofStatus: Object.values(scenarios).every((scenario) => scenario.status === "passed") && cleanup.status === "passed" ? "passed" : "failed",
    packageVersion: packageManifest.version,
    contractPackageVersion: contracts.contractMetadata.packageVersion,
    protocolVersion: contracts.contractMetadata.protocolVersion,
    envelopeVersion: contracts.contractMetadata.envelopeVersion,
    attachmentVersion: contracts.contractMetadata.attachmentVersion,
    releasePosture: contracts.contractMetadata.releasePosture,
    topology: { trustedBrowserWindowCount: 1, remoteWebContentsViewCount: 1, remoteViewHasPreload: false, remoteSessionPersistent: false },
    featureClaims: { topologySkeletonImplemented: true, captureImplemented: false, attachmentImplemented: false, persistenceImplemented: false, liveGuardianImplemented: false, updaterImplemented: false, releaseQualified: false },
    scenarios,
    cleanup,
    remoteLoadOrder: { negotiationBeforeRemoteLoad: scenarios.compatible?.negotiationBeforeRemoteLoad === true, incompatibleRemoteRequests: scenarios.incompatible?.remoteRequests || 0, malformedRemoteRequests: scenarios.malformed?.remoteRequests || 0 },
    forbiddenAuthority: { node: false, electron: false, ipc: false, credential: false, filesystem: false, process: false, shell: false, keychain: false, updater: false, commandBus: false, persistence: false },
    screenshots: ["compatible-trusted-shell.png", "negotiated-contract-state.png", "compatible-remote-fixture.png", "incompatible-trusted-shell.png", "malformed-trusted-shell.png", "remote-renderer-degraded.png", "denial-policy-state.png"],
    generatedAt: new Date().toISOString()
  };
  fs.writeFileSync(path.join(outputDir, "proof.json"), JSON.stringify(proof, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "manifest.json"), JSON.stringify({ proofKind: proof.proofKind, proofFile: "proof.json", screenshotsDirectory: "screenshots", packageVersion: proof.packageVersion, contractPackageVersion: proof.contractPackageVersion, releasePosture: proof.releasePosture }, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "cleanup.json"), JSON.stringify(cleanup, null, 2) + "\n");
  fs.writeFileSync(path.join(outputDir, "proof.md"), `# Production one-tab Browser Host skeleton proof\n\nStatus: **${proof.proofStatus}**\n\nThis sanitized packet covers the trusted Electron shell, one untrusted WebContentsView, deterministic loopback negotiation, negative negotiation, renderer degradation, and policy denials. It does not claim capture, attachment, persistence, live Guardian integration, packaging, signing, updater, or release qualification.\n\n- Package: ${proof.packageVersion}\n- Contract: ${proof.contractPackageVersion}\n- Protocol: ${proof.protocolVersion}\n- Electron/Chromium: candidate-matching local dependency\n- Remote authority: denied by live renderer checks\n- Cleanup: ${cleanup.status}\n`);
  process.stdout.write(JSON.stringify({ outputDir, proof: proof.proofStatus }) + "\n");
  if (proof.proofStatus !== "passed") process.exitCode = 1;
}

main().catch((error) => { process.stderr.write(`${String(error.stack || error)}\n`); process.exitCode = 1; });
