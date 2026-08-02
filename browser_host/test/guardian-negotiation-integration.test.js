"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const { spawn } = require("node:child_process");
const test = require("node:test");
const assert = require("node:assert/strict");
const { _electron: electron } = require("playwright");
const { startFixtureServer } = require("./support/fixture-server");

const root = path.resolve(__dirname, "..");
const mainPath = path.join(root, "src", "main.js");
const pythonPath = path.join(root, "..", ".venv", "bin", "python");
const supportPath = path.join(root, "..", "tests", "browser_host", "support", "guardian_browser_host_dev_app.py");
const launcherPath = path.join(root, "..", "scripts", "browser_host", "launch_with_attachment_grant.py");
const integrationFile = __filename;
const API_KEY = "synthetic-negotiation-guardian-api-key";
const PROOF_TOKEN = "CODEXIFY-SYNTHETIC-1234567890abcdef";

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function safeTestEnvironment() {
  const secretPattern = /(?:API_KEY|API_KEYS|SECRET|PASSWORD|COOKIE|JWT|PRIVATE_KEY|AUTHORIZATION|BEARER|TOKEN|CREDENTIAL)/i;
  return Object.fromEntries(Object.entries(process.env).filter(([name]) => !secretPattern.test(name)));
}

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

function waitForReady(child, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    let output = "";
    const timer = setTimeout(() => { cleanup(); reject(new Error("guardian_support_ready_timeout")); }, timeoutMs);
    const onData = (chunk) => {
      output += chunk.toString("utf8");
      if (/^READY \d+$/m.test(output)) { cleanup(); resolve(); }
    };
    const onExit = () => { cleanup(); reject(new Error("guardian_support_exited_before_ready")); };
    const cleanup = () => { clearTimeout(timer); child.stdout?.off("data", onData); child.off("exit", onExit); };
    child.stdout?.on("data", onData);
    child.once("exit", onExit);
  });
}

async function startSupport({ negotiationEnabled = true, attachmentEnabled = true, outcome = "compatible" } = {}) {
  const port = await freePort();
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-negotiation-"));
  const summaryPath = path.join(directory, "summary.json");
  const args = [supportPath, "--port", String(port), "--summary-file", summaryPath, "--negotiation-outcome", outcome];
  if (negotiationEnabled) args.push("--negotiation-enabled");
  if (attachmentEnabled) args.push("--attachment-enabled");
  const child = spawn(pythonPath, args, {
    cwd: root,
    env: {
      ...safeTestEnvironment(),
      CODEXIFY_DISABLE_DOTENV: "1",
      GUARDIAN_DEV_MODE: "true",
      GUARDIAN_BROWSER_HOST_NEGOTIATION_DEV_ENABLED: negotiationEnabled ? "true" : "false",
      GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED: attachmentEnabled ? "true" : "false",
      GUARDIAN_EXPOSURE_MODE: "local_safe",
      GUARDIAN_AUTH_MODE: "local",
      GUARDIAN_API_KEY: API_KEY,
      CODEXIFY_SINGLE_USER_ID: "browser-host-negotiation-proof"
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  await waitForReady(child);
  return {
    origin: `http://127.0.0.1:${port}`,
    child,
    summaryPath,
    directory,
    async close() {
      if (child.exitCode === null) child.kill("SIGTERM");
      await new Promise((resolve) => { if (child.exitCode !== null) return resolve(); child.once("exit", resolve); });
      const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
      fs.rmSync(directory, { recursive: true, force: true });
      return summary;
    }
  };
}

async function waitForState(trusted, predicate, timeoutMs = 15000) {
  const started = Date.now();
  let state;
  while (Date.now() - started < timeoutMs) {
    state = await trusted.evaluate(() => window.codexifyBrowserHost.getState());
    if (predicate(state)) return state;
    await sleep(100);
  }
  throw new Error(`state_timeout:${state?.runtimeStatus || "unknown"}`);
}

async function remoteEvaluate(app, script) {
  return app.evaluate(({ BrowserWindow }, source) => {
    const view = BrowserWindow.getAllWindows()[0].contentView.children[0];
    if (!view) throw new Error("remote_view_missing");
    return view.webContents.executeJavaScript(source, true);
  }, script);
}

async function runElectronScenario(scenario, env) {
  const app = await electron.launch({ executablePath: require("electron"), args: [mainPath], cwd: root, env, timeout: 30000 });
  const trusted = await app.firstWindow();
  await trusted.waitForLoadState("domcontentloaded");
  try {
    const mainEnvironment = await app.evaluate(() => ({
      grant: Boolean(process.env.CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT),
      apiKey: Boolean(process.env.GUARDIAN_API_KEY),
      jwt: Boolean(process.env.GUARDIAN_JWT_SECRET),
      provider: Object.keys(process.env).some((name) => /(?:API_KEY|SECRET|TOKEN)/i.test(name) && !name.includes("PROOF_TOKEN")),
      versions: { electron: process.versions.electron, chrome: process.versions.chrome, node: process.versions.node, v8: process.versions.v8 }
    }));
    const outcome = scenario === "compatible" ? await waitForState(trusted, (state) => (state.runtimeStatus === "negotiated" && state.remoteStatus === "ready" && state.remoteLoadedAfterGuardianNegotiation) || state.runtimeStatus === "degraded") : await waitForState(trusted, (state) => state.runtimeStatus === "degraded");
    const result = {
      scenario,
      outcome: outcome.guardianCompatibilityOutcome,
      remoteStatus: outcome.remoteStatus,
      remoteLoadedAfterGuardianNegotiation: outcome.remoteLoadedAfterGuardianNegotiation,
      selectedVersions: outcome.selectedVersions,
      enabledFeatures: outcome.enabledFeatures,
      disabledFeatures: outcome.disabledFeatures,
      negotiationHttpStatus: outcome.guardianNegotiationHttpStatus,
      noReusableCredential: !mainEnvironment.apiKey && !mainEnvironment.jwt && !mainEnvironment.provider,
      grantInElectron: mainEnvironment.grant,
      preloadMethodCount: await trusted.evaluate(() => Object.keys(window.codexifyBrowserHost).length),
      versions: mainEnvironment.versions,
      fixtureRequestsBeforeCompatibility: 0,
      fixtureRequestsAfterCompatibility: 0,
      attachmentOutcome: null,
      persistenceOutcome: null,
      screenshot: null
    };
    if (scenario !== "compatible") {
      assert.equal(outcome.remoteStatus, "not_created");
      assert.equal(outcome.remoteLoadedAfterGuardianNegotiation, false);
      assert.equal(result.preloadMethodCount, 7);
      return result;
    }
    assert.equal(outcome.runtimeStatus, "negotiated");
    assert.equal(outcome.remoteLoadedAfterGuardianNegotiation, true);
    assert.equal(result.preloadMethodCount, 7);
    if (env.CODEXIFY_BROWSER_HOST_PROOF_SCREENSHOT_DIR) {
      result.screenshot = path.join(env.CODEXIFY_BROWSER_HOST_PROOF_SCREENSHOT_DIR, "guardian-negotiation-compatible.png");
      await trusted.screenshot({ path: result.screenshot });
    }
    await remoteEvaluate(app, `location.href = ${JSON.stringify(`${env.CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN}/capture`)}`);
    await waitForState(trusted, (state) => state.remoteUrl.endsWith("/capture") && state.remoteStatus === "ready");
    await remoteEvaluate(app, "(() => { const node = document.querySelector('#selected-text'); const range = document.createRange(); range.selectNodeContents(node); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); })()");
    const preview = await trusted.evaluate(() => window.codexifyBrowserHost.captureSelectedText());
    assert.equal(preview.captureStatus, "preview_ready");
    if (env.CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED === "1") {
      const attached = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
      result.attachmentOutcome = attached.captureAttachmentOutcome;
      result.persistenceOutcome = attached.capturePersistenceOutcome;
      assert.equal(attached.captureAttachmentOutcome, "accepted");
      assert.equal(attached.capturePersistenceOutcome, "not_persisted");
      assert.equal(attached.attachmentGrantConsumed, true);
    }
    return result;
  } finally {
    await app.close();
  }
}

async function runLauncherScenario({ outcome = "compatible", screenshotDirectory = null } = {}) {
  const support = await startSupport({ outcome });
  const fixture = await require("./support/fixture-server").startFixtureServer({ label: "guardian-negotiation" });
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-negotiation-run-"));
  const resultPath = path.join(directory, "result.json");
  const environment = {
    ...safeTestEnvironment(),
    GUARDIAN_API_KEY: API_KEY,
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: PROOF_TOKEN,
    CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixture.origin,
    CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH: resultPath
  };
  if (screenshotDirectory) environment.CODEXIFY_BROWSER_HOST_PROOF_SCREENSHOT_DIR = screenshotDirectory;
  const child = await new Promise((resolve, reject) => {
    const launcherProcess = spawn(pythonPath, [launcherPath, "--guardian-origin", support.origin, "--browser-host-instance-id", `browser-host-${outcome}`, "--timeout-ms", "3000", "--", process.execPath, integrationFile, "--electron-child-mode", "--scenario", outcome], { cwd: root, env: { ...environment }, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    launcherProcess.stdout.on("data", (chunk) => { stdout += chunk.toString("utf8"); });
    launcherProcess.stderr.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
    launcherProcess.on("error", reject);
    launcherProcess.on("close", (status) => resolve({ status, stdout, stderr }));
  });
  const result = fs.existsSync(resultPath) ? JSON.parse(fs.readFileSync(resultPath, "utf8")) : null;
  fs.rmSync(directory, { recursive: true, force: true });
  const summary = await support.close();
  await fixture.close();
  return { child, result, summary, fixtureRequests: fixture.requests };
}

async function runDirectFailureScenario(scenario, origin, fixtureOrigin) {
  return runElectronScenario(scenario, {
    ...safeTestEnvironment(),
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: PROOF_TOKEN,
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_DEV_ENABLED: "1",
    CODEXIFY_BROWSER_HOST_GUARDIAN_NEGOTIATION_ORIGIN: origin,
    CODEXIFY_BROWSER_HOST_NEGOTIATION_TRANSPORT: "guardian_dev_adapter",
    CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixtureOrigin
  });
}

async function runChildMode() {
  const scenario = process.argv[process.argv.indexOf("--scenario") + 1] || "compatible";
  try {
    const result = await runElectronScenario(scenario, process.env);
    if (process.env.CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH) fs.writeFileSync(process.env.CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH, JSON.stringify(result), "utf8");
    process.exitCode = 0;
  } catch (error) {
    if (process.env.CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH) fs.writeFileSync(process.env.CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH, JSON.stringify({ scenario, failure: error?.message || "electron_failure" }), "utf8");
    process.exitCode = 1;
  }
}

if (process.argv.includes("--electron-child-mode")) {
  runChildMode();
} else if (process.env.NODE_TEST_CONTEXT || process.argv.includes("--test")) {
  test("real Guardian negotiation gates remote loading and preserves separate attachment authority", async () => {
    const compatible = await runLauncherScenario();
    assert.equal(compatible.child.status, 0, `${compatible.child.stdout}\n${compatible.child.stderr}`);
    assert.equal(compatible.result.outcome, "compatible");
    assert.equal(compatible.result.remoteLoadedAfterGuardianNegotiation, true);
    assert.equal(compatible.result.attachmentOutcome, "accepted");
    assert.equal(compatible.result.persistenceOutcome, "not_persisted");
    assert.equal(compatible.result.noReusableCredential, true);
    assert.equal(compatible.result.grantInElectron, false);
    assert.equal(compatible.result.preloadMethodCount, 7);
    assert.equal(compatible.summary.negotiationCount, 1);
    assert.equal(compatible.summary.grantIssuanceCount, 1);
    assert.equal(compatible.summary.attachmentStatuses[0], 202);
    assert.equal(compatible.fixtureRequests.some((request) => request.path === "/capture"), true);

    const incompatible = await runLauncherScenario({ outcome: "incompatible" });
    assert.equal(incompatible.child.status, 0, `${incompatible.child.stdout}\n${incompatible.child.stderr}`);
    assert.equal(incompatible.result.outcome, "incompatible");
    assert.equal(incompatible.result.remoteStatus, "not_created");
    assert.equal(incompatible.summary.negotiationCount, 1);
    assert.equal(incompatible.summary.attachmentCount, 0);
    assert.equal(incompatible.fixtureRequests.length, 0);

    const malformed = await runLauncherScenario({ outcome: "malformed" });
    assert.equal(malformed.child.status, 0, `${malformed.child.stdout}\n${malformed.child.stderr}`);
    assert.equal(malformed.result.outcome, "malformed");
    assert.equal(malformed.result.remoteStatus, "not_created");
    assert.equal(malformed.summary.negotiationCount, 1);
    assert.equal(malformed.fixtureRequests.length, 0);

    const disabledSupport = await startSupport({ negotiationEnabled: false, attachmentEnabled: false });
    const disabledFixture = await require("./support/fixture-server").startFixtureServer({ label: "disabled" });
    const disabled = await runDirectFailureScenario("disabled", disabledSupport.origin, disabledFixture.origin);
    assert.equal(disabled.outcome, "unavailable");
    assert.equal(disabled.negotiationHttpStatus, 404);
    assert.equal(disabled.remoteStatus, "not_created");
    assert.equal(disabledFixture.requests.length, 0);
    await disabledSupport.close();
    await disabledFixture.close();

    const transportFixture = await require("./support/fixture-server").startFixtureServer({ label: "transport" });
    const missing = await freePort();
    const transport = await runDirectFailureScenario("transport", `http://127.0.0.1:${missing}`, transportFixture.origin);
    assert.equal(transport.outcome, "unavailable");
    assert.equal(transport.remoteStatus, "not_created");
    assert.equal(transportFixture.requests.length, 0);
    await transportFixture.close();
  });
}

module.exports = Object.freeze({
  startSupport,
  runElectronScenario,
  runLauncherScenario,
  runDirectFailureScenario
});
