"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { execPath } = require("node:process");
const test = require("node:test");
const assert = require("node:assert/strict");
const { _electron: electron } = require("playwright");
const { startGuardianStub } = require("./support/guardian-stub");
const { startFixtureServer } = require("./support/fixture-server");

const root = path.resolve(__dirname, "..");
const mainPath = path.join(root, "src", "main.js");
const pythonPath = path.join(root, "..", ".venv", "bin", "python");
const adapterSupportPath = path.join(root, "..", "tests", "browser_host", "support", "guardian_attachment_dev_app.py");
const launcherPath = path.join(root, "..", "scripts", "browser_host", "launch_with_attachment_grant.py");
const integrationFile = __filename;
const API_KEY = "synthetic-integration-guardian-api-key";
const PROOF_TOKEN = "CODEXIFY-SYNTHETIC-1234567890abcdef";
const GRANT_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT";
const API_KEY_ENV = "GUARDIAN_API_KEY";
const ATTACHMENT_FLAG_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_DEV_ENABLED";
const ATTACHMENT_ORIGIN_ENV = "CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_ORIGIN";
const INSTANCE_ENV = "CODEXIFY_BROWSER_HOST_INSTANCE_ID";

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function token() { return `CODEXIFY-SYNTHETIC-${crypto.randomBytes(18).toString("hex")}`; }

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
      if (/^READY \d+$/m.test(output)) { cleanup(); resolve(output); }
    };
    const onExit = () => { cleanup(); reject(new Error("guardian_support_exited_before_ready")); };
    const cleanup = () => {
      clearTimeout(timer);
      child.stdout?.off("data", onData);
      child.off("exit", onExit);
    };
    child.stdout?.on("data", onData);
    child.once("exit", onExit);
  });
}

async function startGuardianAttachmentSupport({ enabled = true, expireAfterIssuance = false, shutdownAfterIssuance = false } = {}) {
  const port = await freePort();
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-guardian-"));
  const summaryPath = path.join(directory, "summary.json");
  const args = [adapterSupportPath, "--port", String(port), "--summary-file", summaryPath];
  if (enabled) args.push("--adapter-enabled");
  if (expireAfterIssuance) args.push("--expire-after-issuance");
  if (shutdownAfterIssuance) args.push("--shutdown-after-issuance");
  const child = spawn(pythonPath, args, {
    cwd: root,
    env: {
      ...safeTestEnvironment(),
      CODEXIFY_DISABLE_DOTENV: "1",
      GUARDIAN_DEV_MODE: "true",
      GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED: enabled ? "true" : "false",
      GUARDIAN_EXPOSURE_MODE: "local_safe",
      GUARDIAN_AUTH_MODE: "local",
      GUARDIAN_API_KEY: API_KEY,
      CODEXIFY_SINGLE_USER_ID: "browser-host-integration-subject"
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
      await new Promise((resolve) => {
        if (child.exitCode !== null) return resolve();
        child.once("exit", resolve);
      });
      if (!fs.existsSync(summaryPath)) throw new Error("guardian_support_summary_missing");
      const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
      fs.rmSync(directory, { recursive: true, force: true });
      return summary;
    }
  };
}

function waitForState(trusted, predicate, timeoutMs = 15000) {
  const started = Date.now();
  return (async () => {
    let state;
    while (Date.now() - started < timeoutMs) {
      state = await trusted.evaluate(() => window.codexifyBrowserHost.getState());
      if (predicate(state)) return state;
      await sleep(100);
    }
    throw new Error(`state_timeout:${state?.runtimeStatus || "unknown"}`);
  })();
}

async function remoteEvaluate(app, script) {
  return app.evaluate(({ BrowserWindow }, source) => {
    const view = BrowserWindow.getAllWindows()[0].contentView.children[0];
    if (!view) throw new Error("remote_view_missing");
    return view.webContents.executeJavaScript(source, true);
  }, script);
}

async function runElectronChildScenario(scenario, env = process.env) {
  const browserEnv = { ...env };
  if (scenario === "wrong-instance") browserEnv[INSTANCE_ENV] = "browser-host-wrong-instance";
  const wrapperGrantPresent = Boolean(browserEnv[GRANT_ENV]);
  let app = null;
  let trusted;
  let result = {
    scenario,
    wrapperGrantPresent,
    grantPresentInElectronEnvironmentAfterConfig: null,
    apiKeyPresentInElectronEnvironment: null,
    sessionSecretPresentInElectronEnvironment: null,
    jwtSecretPresentInElectronEnvironment: null,
    providerCredentialPresentInElectronEnvironment: null,
    trustedStateHasGrant: null,
    remoteHasBridge: null,
    acceptedHttpStatus: null,
    attachmentOutcome: null,
    persistenceOutcome: null,
    attachmentGrantAvailable: null,
    attachmentGrantConsumed: null,
    noReusableCredential: null,
    networkStatus: null,
    screenshot: null,
    versions: null,
    browserEnvironmentPosture: {
      proofMode: browserEnv.CODEXIFY_BROWSER_HOST_PROOF_MODE === "1",
      proofToken: Boolean(browserEnv.CODEXIFY_BROWSER_HOST_PROOF_TOKEN),
      guardianOrigin: Boolean(browserEnv.CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN),
      fixtureOrigin: Boolean(browserEnv.CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN),
      attachmentEnabled: browserEnv[ATTACHMENT_FLAG_ENV] === "1",
      attachmentOrigin: Boolean(browserEnv[ATTACHMENT_ORIGIN_ENV]),
      instanceId: Boolean(browserEnv[INSTANCE_ENV])
    }
  };
  const resultPath = env.CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH;
  if (resultPath) fs.writeFileSync(resultPath, JSON.stringify({ scenario, wrapperGrantPresent, started: true }), "utf8");
  try {
    app = await electron.launch({ executablePath: require("electron"), args: [mainPath], cwd: root, env: browserEnv, timeout: 30000 });
    trusted = await app.firstWindow();
    await trusted.waitForLoadState("domcontentloaded");
    const mainEnvironment = await app.evaluate(() => ({
      grant: Boolean(process.env.CODEXIFY_BROWSER_HOST_GUARDIAN_ATTACHMENT_GRANT),
      apiKey: Boolean(process.env.GUARDIAN_API_KEY),
      session: Boolean(process.env.GUARDIAN_SESSION_SECRET),
      jwt: Boolean(process.env.GUARDIAN_JWT_SECRET),
      provider: Object.keys(process.env).some((name) => /(?:API_KEY|SECRET|TOKEN)/i.test(name) && !name.includes("PROOF_TOKEN")),
      versions: { electron: process.versions.electron, chrome: process.versions.chrome, node: process.versions.node, v8: process.versions.v8 }
    }));
    result.grantPresentInElectronEnvironmentAfterConfig = mainEnvironment.grant;
    result.apiKeyPresentInElectronEnvironment = mainEnvironment.apiKey;
    result.sessionSecretPresentInElectronEnvironment = mainEnvironment.session;
    result.jwtSecretPresentInElectronEnvironment = mainEnvironment.jwt;
    result.providerCredentialPresentInElectronEnvironment = mainEnvironment.provider;
    result.versions = mainEnvironment.versions;
    result.noReusableCredential = !mainEnvironment.apiKey && !mainEnvironment.session && !mainEnvironment.jwt && !mainEnvironment.provider;
    const negotiatedState = await waitForState(trusted, (state) => (
      state.runtimeStatus === "negotiated" && state.remoteStatus === "ready"
    ) || state.runtimeStatus === "degraded");
    if (negotiatedState.runtimeStatus === "degraded") throw new Error(`browser_host_degraded:${JSON.stringify(negotiatedState)}`);
    const initial = await trusted.evaluate(() => window.codexifyBrowserHost.getState());
    result.trustedStateHasGrant = JSON.stringify(initial).includes("grantBearer") || JSON.stringify(initial).includes("BrowserHostAttachmentGrant");
    result.remoteHasBridge = await remoteEvaluate(app, "typeof window.codexifyBrowserHost !== 'undefined' || typeof window.require !== 'undefined' || typeof window.process !== 'undefined'");

    if (scenario === "stub") {
      result.attachmentOutcome = (await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage())).captureStatus;
      const preview = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
      const attached = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
      assert.equal(attached.captureStatus, "attached");
      assert.equal(initial.attachmentTransport, "deterministic_stub");
      result.attachmentOutcome = attached.captureAttachmentOutcome;
      result.persistenceOutcome = attached.capturePersistenceOutcome;
      return result;
    }

    await remoteEvaluate(app, `location.href = ${JSON.stringify(`${env.CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN}/capture`)}`);
    await waitForState(trusted, (state) => state.remoteUrl.endsWith("/capture") && state.remoteStatus === "ready");
    await remoteEvaluate(app, "(() => { const node = document.querySelector('#selected-text'); const range = document.createRange(); range.selectNodeContents(node); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); })()");
    const preview = await trusted.evaluate(() => window.codexifyBrowserHost.captureSelectedText());
    assert.equal(preview.captureStatus, "preview_ready");
    assert.equal(preview.captureMode, "selected_text");
    assert.match(preview.capturePreviewContent, /Selected evidence/);
    assert.equal((await trusted.evaluate(() => window.codexifyBrowserHost.getState())).captureAttachmentOutcome, null);
    const attached = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), preview.captureTicketId);
    result.attachmentOutcome = attached.captureAttachmentOutcome;
    result.persistenceOutcome = attached.capturePersistenceOutcome;
    result.acceptedHttpStatus = attached.captureAttachmentOutcome === "accepted" ? 202 : null;
    result.networkStatus = attached.lastGuardianAttachmentHttpStatus;
    result.attachmentGrantAvailable = attached.attachmentGrantAvailable;
    result.attachmentGrantConsumed = attached.attachmentGrantConsumed;
    assert.equal(attached.attachmentGrantAvailable, false);
    assert.equal(attached.attachmentGrantConsumed, true);
    assert.equal(attached.capturePreviewContent, "");
    if (scenario === "accepted") {
      assert.equal(attached.captureAttachmentOutcome, "accepted");
      assert.equal(attached.capturePersistenceOutcome, "not_persisted");
      const secondPreview = await trusted.evaluate(() => window.codexifyBrowserHost.captureVisiblePage());
      const second = await trusted.evaluate((ticket) => window.codexifyBrowserHost.attachCapture(ticket), secondPreview.captureTicketId);
      assert.equal(second.captureErrorCode, "attachment_grant_consumed");
      result.secondAttemptError = second.captureErrorCode;
    } else if (scenario === "wrong-instance") {
      assert.equal(attached.captureAttachmentOutcome, "rejected");
      assert.equal(attached.lastGuardianAttachmentHttpStatus, 403);
    } else if (scenario === "expired") {
      assert.equal(attached.captureAttachmentOutcome, "rejected");
      assert.equal(attached.lastGuardianAttachmentHttpStatus, 409);
    } else if (scenario === "disabled") {
      assert.equal(attached.captureAttachmentOutcome, "rejected");
      assert.equal(attached.lastGuardianAttachmentHttpStatus, 404);
    } else if (scenario === "transport") {
      assert.equal(attached.captureAttachmentOutcome, "rejected");
      assert.equal(attached.lastGuardianAttachmentHttpStatus, null);
    }
    assert.equal(await trusted.evaluate(() => document.title), "Codexify Browser Host");
    const screenshotDirectory = env.CODEXIFY_BROWSER_HOST_PROOF_SCREENSHOT_DIR;
    if (scenario === "accepted" && screenshotDirectory) {
      result.screenshot = path.join(screenshotDirectory, "guardian-attachment-accepted.png");
      await trusted.screenshot({ path: result.screenshot });
    }
    return result;
  } catch (error) {
    result.failure = error?.code || error?.name || "electron_child_failure";
    throw error;
  } finally {
    if (app) await app.close();
    if (resultPath) fs.writeFileSync(resultPath, JSON.stringify(result), "utf8");
  }
}

async function runChildMode() {
  const index = process.argv.indexOf("--scenario");
  const scenario = index >= 0 ? process.argv[index + 1] : "accepted";
  try {
    await runElectronChildScenario(scenario, process.env);
    process.exitCode = 0;
  } catch {
    process.stdout.write("electron child scenario failed\n");
    process.exitCode = 1;
  }
}

function runChildProcess(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, options);
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += chunk.toString("utf8"); });
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
    child.once("error", reject);
    child.once("close", (code, signal) => resolve({ status: typeof code === "number" ? code : 1, signal, stdout, stderr }));
  });
}

async function runBroker({ issuanceOrigin, attachmentOrigin, stubOrigin, fixtureOrigin, instanceId, scenario, overrideInstance, proofScreenshotDirectory }) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-integration-"));
  const resultPath = path.join(directory, "child-result.json");
  const args = [
    launcherPath,
    "--guardian-origin", issuanceOrigin,
    "--attachment-origin", attachmentOrigin || issuanceOrigin,
    "--browser-host-instance-id", instanceId,
    "--grant-ttl-seconds", "120",
    "--max-attachment-bytes", "65536",
    "--timeout-ms", "1500",
    "--",
    execPath,
    integrationFile,
    "--electron-child-mode",
    "--scenario", scenario
  ];
  const environment = {
    ...safeTestEnvironment(),
    GUARDIAN_API_KEY: API_KEY,
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: PROOF_TOKEN,
    CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: stubOrigin,
    CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixtureOrigin,
    CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH: resultPath
  };
  if (overrideInstance) environment.CODEXIFY_BROWSER_HOST_CHILD_OVERRIDE_INSTANCE_ID = overrideInstance;
  if (proofScreenshotDirectory) environment.CODEXIFY_BROWSER_HOST_PROOF_SCREENSHOT_DIR = proofScreenshotDirectory;
  const completed = await runChildProcess(pythonPath, args, { cwd: root, env: environment });
  const result = fs.existsSync(resultPath) ? JSON.parse(fs.readFileSync(resultPath, "utf8")) : null;
  fs.rmSync(directory, { recursive: true, force: true });
  return { completed, result };
}

async function runDirectStub({ stubOrigin, fixtureOrigin }) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-stub-"));
  const resultPath = path.join(directory, "child-result.json");
  const completed = await runChildProcess(execPath, [integrationFile, "--electron-child-mode", "--scenario", "stub"], {
    cwd: root,
    env: {
      ...safeTestEnvironment(),
      CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
      CODEXIFY_BROWSER_HOST_PROOF_TOKEN: PROOF_TOKEN,
      CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: stubOrigin,
      CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixtureOrigin,
      CODEXIFY_BROWSER_HOST_CHILD_RESULT_PATH: resultPath
    }
  });
  const result = fs.existsSync(resultPath) ? JSON.parse(fs.readFileSync(resultPath, "utf8")) : null;
  fs.rmSync(directory, { recursive: true, force: true });
  return { completed, result };
}

async function runIntegrationMatrix({ proofScreenshotDirectory = null } = {}) {
  const stub = await startGuardianStub({ token: PROOF_TOKEN, enabledFeatures: ["capture:selected", "capture:visible", "capture:attach"] });
  const fixture = await startFixtureServer();
  const results = {};
  try {
    const acceptedSupport = await startGuardianAttachmentSupport();
    try {
      const run = await runBroker({ issuanceOrigin: acceptedSupport.origin, stubOrigin: stub.origin, fixtureOrigin: fixture.origin, instanceId: "browser-host-accepted", scenario: "accepted", proofScreenshotDirectory });
      assert.equal(run.completed.status, 0, JSON.stringify(run.result));
      results.acceptedChild = run.result;
      results.acceptedBrokerOutput = `${run.completed.stdout}${run.completed.stderr}`;
    } finally {
      results.acceptedSupport = await acceptedSupport.close();
    }

    const wrongSupport = await startGuardianAttachmentSupport();
    try {
      const run = await runBroker({ issuanceOrigin: wrongSupport.origin, stubOrigin: stub.origin, fixtureOrigin: fixture.origin, instanceId: "browser-host-bound-instance", scenario: "wrong-instance", overrideInstance: "browser-host-wrong-instance" });
      assert.equal(run.completed.status, 0, JSON.stringify(run.result));
      results.wrongInstanceChild = run.result;
    } finally {
      results.wrongInstanceSupport = await wrongSupport.close();
    }

    const expiredSupport = await startGuardianAttachmentSupport({ expireAfterIssuance: true });
    try {
      const run = await runBroker({ issuanceOrigin: expiredSupport.origin, stubOrigin: stub.origin, fixtureOrigin: fixture.origin, instanceId: "browser-host-expired", scenario: "expired" });
      assert.equal(run.completed.status, 0, JSON.stringify(run.result));
      results.expiredChild = run.result;
    } finally {
      results.expiredSupport = await expiredSupport.close();
    }

    const issuanceSupport = await startGuardianAttachmentSupport();
    const disabledSupport = await startGuardianAttachmentSupport({ enabled: false });
    try {
      const run = await runBroker({ issuanceOrigin: issuanceSupport.origin, attachmentOrigin: disabledSupport.origin, stubOrigin: stub.origin, fixtureOrigin: fixture.origin, instanceId: "browser-host-disabled", scenario: "disabled" });
      assert.equal(run.completed.status, 0, JSON.stringify(run.result));
      results.disabledChild = run.result;
      results.disabledSupport = await disabledSupport.close();
    } finally {
      results.disabledSupport ||= await disabledSupport.close();
      results.issuanceSupport = await issuanceSupport.close();
    }

    const transportSupport = await startGuardianAttachmentSupport({ shutdownAfterIssuance: true });
    try {
      const run = await runBroker({ issuanceOrigin: transportSupport.origin, stubOrigin: stub.origin, fixtureOrigin: fixture.origin, instanceId: "browser-host-transport", scenario: "transport" });
      assert.equal(run.completed.status, 0, JSON.stringify(run.result));
      results.transportChild = run.result;
    } finally {
      results.transportSupport = await transportSupport.close();
    }

    const stubRun = await runDirectStub({ stubOrigin: stub.origin, fixtureOrigin: fixture.origin });
    assert.equal(stubRun.completed.status, 0, JSON.stringify(stubRun.result));
    results.stubChild = stubRun.result;
    results.stubAttachmentCount = stub.attachments.length;
    results.stubNegotiationCount = stub.requests.length;
    return results;
  } finally {
    await stub.close();
    await fixture.close();
  }
}

if (process.argv.includes("--electron-child-mode")) {
  runChildMode();
} else if (process.env.NODE_TEST_CONTEXT || process.argv.includes("--test")) {
  test("real Guardian development adapter integration is explicit, one-shot, redacted, and no-fallback", async () => {
    const matrix = await runIntegrationMatrix();
    assert.equal(matrix.acceptedSupport.attachmentStatuses[0], 202);
    assert.deepEqual(matrix.acceptedSupport.attachmentStatuses, [202]);
    assert.equal(matrix.acceptedChild.attachmentOutcome, "accepted");
    assert.equal(matrix.acceptedChild.persistenceOutcome, "not_persisted");
    assert.equal(matrix.acceptedChild.secondAttemptError, "attachment_grant_consumed");
    assert.equal(matrix.acceptedChild.wrapperGrantPresent, true);
    assert.equal(matrix.acceptedChild.grantPresentInElectronEnvironmentAfterConfig, false);
    assert.equal(matrix.acceptedChild.apiKeyPresentInElectronEnvironment, false);
    assert.equal(matrix.acceptedChild.trustedStateHasGrant, false);
    assert.equal(matrix.acceptedChild.remoteHasBridge, false);
    assert.equal(matrix.wrongInstanceChild.networkStatus, 403);
    assert.equal(matrix.expiredChild.networkStatus, 409);
    assert.equal(matrix.disabledChild.networkStatus, 404);
    assert.equal(matrix.transportChild.networkStatus, null);
    assert.equal(matrix.stubAttachmentCount, 1);
    assert.equal(matrix.acceptedSupport.rawSecretsIncluded, false);
  });
}

module.exports = Object.freeze({ runIntegrationMatrix, runElectronChildScenario });
