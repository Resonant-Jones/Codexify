"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const { _electron: electron } = require("playwright");
const packageManifest = require("../package.json");
const contractManifest = require("../contracts/package.json");
const { startGuardianStub } = require("../test/support/guardian-stub");
const { startFixtureServer } = require("../test/support/fixture-server");

const ROOT = path.resolve(__dirname, "..");
const MAIN_PATH = path.join(ROOT, "src", "main.js");
const ELECTRON_EXECUTABLE = require("electron");
const PREREQUISITE_COMMIT = "3b1e736ee52ee22958e61e479f060382bf82ea96";
const PROOF_TOKEN = `CODEXIFY-SYNTHETIC-${crypto.randomBytes(18).toString("hex")}`;
const MAX_TEXT = 1200;
const MAX_STDERR_LINES = 12;
const EXPECTED_PRELOAD_METHODS = Object.freeze([
  "attachCapture", "cancelCapture", "captureSelectedText", "captureVisiblePage",
  "getState", "onStateChanged", "reloadRemote"
]);
const CLASSIFICATIONS = Object.freeze([
  "dependency_installation", "binary_architecture", "host_security_assessment",
  "graphical_session_unavailable", "playwright_launch_configuration", "child_environment",
  "entrypoint_resolution", "application_startup", "support_process_readiness",
  "cleanup_or_early_exit", "external_environment_restriction", "unknown_next_proof_needed"
]);

function boundedText(value, max = MAX_TEXT) {
  return String(value || "").replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, "").slice(0, max);
}

function sanitizePath(value) {
  return boundedText(value)
    .replaceAll(ROOT, "<browser-host-root>")
    .replaceAll(os.homedir(), "<home>")
    .replaceAll(os.tmpdir(), "<tmp>");
}

function sanitizeOutput(value) {
  return sanitizePath(value)
    .split(/\r?\n/)
    .filter((line) => !/(?:API_KEY|SECRET|PASSWORD|COOKIE|JWT|AUTHORIZATION|BEARER|GRANT|TOKEN)/i.test(line))
    .join("\n")
    .slice(0, MAX_TEXT);
}

function firstLine(value) {
  return sanitizeOutput(value).split(/\r?\n/).find((line) => line.trim()) || "";
}

function runCommand(command, args = [], options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || ROOT,
    env: options.env,
    encoding: "utf8",
    timeout: options.timeout || 5000,
    maxBuffer: 64 * 1024
  });
  return {
    command: sanitizePath(command),
    args: args.map((value) => sanitizePath(value)),
    exitCode: typeof result.status === "number" ? result.status : null,
    signal: result.signal || null,
    error: result.error ? boundedText(result.error.message) : null,
    stdout: sanitizeOutput(result.stdout),
    stderr: sanitizeOutput(result.stderr)
  };
}

function safeDiagnosticEnvironment(overrides = {}) {
  const secretName = /(?:API_KEY|API_KEYS|SECRET|PASSWORD|COOKIE|JWT|PRIVATE_KEY|AUTHORIZATION|BEARER|CREDENTIAL|ACCESS_TOKEN|SESSION_TOKEN)/i;
  const inherited = Object.fromEntries(Object.entries(process.env).filter(([name]) => !secretName.test(name)));
  return {
    ...inherited,
    CODEXIFY_DISABLE_DOTENV: "1",
    CODEXIFY_BROWSER_HOST_PROOF_MODE: "1",
    CODEXIFY_BROWSER_HOST_PROOF_TOKEN: PROOF_TOKEN,
    ...overrides
  };
}

function macAssessment() {
  if (process.platform !== "darwin") return null;
  const appBundle = path.dirname(path.dirname(path.dirname(ELECTRON_EXECUTABLE)));
  const uid = typeof process.getuid === "function" ? process.getuid() : "unknown";
  const graphical = spawnSync("launchctl", ["print", `gui/${uid}`], {
    encoding: "utf8",
    timeout: 3000,
    maxBuffer: 8 * 1024 * 1024,
    stdio: ["ignore", "pipe", "ignore"]
  });
  return {
    swVers: runCommand("sw_vers"),
    uname: runCommand("uname", ["-m"]),
    file: runCommand("file", [ELECTRON_EXECUTABLE]),
    xattr: runCommand("xattr", ["-l", appBundle]),
    codesign: runCommand("codesign", ["-dv", "--verbose=4", appBundle]),
    spctl: runCommand("spctl", ["--assess", "--type", "execute", appBundle]),
    graphicalSession: {
      available: graphical.status === 0,
      aquaSession: /session\s*=\s*Aqua/.test(graphical.stdout || ""),
      exitCode: typeof graphical.status === "number" ? graphical.status : null,
      signal: graphical.signal || null,
      error: graphical.error ? boundedText(graphical.error.message) : null
    }
  };
}

function packageVersions() {
  return {
    package: packageManifest.version,
    contractPackage: contractManifest.version,
    electron: require("electron/package.json").version,
    playwright: require("playwright/package.json").version,
    node: process.versions.node,
    npm: runCommand("npm", ["--version"], { cwd: ROOT }).stdout.trim(),
    platform: process.platform,
    hostArchitecture: process.arch,
    nodeArchitecture: process.arch
  };
}

function architectureFromFile(fileResult) {
  const match = fileResult?.stdout?.match(/Mach-O\s+64-bit executable\s+([A-Za-z0-9_]+)/i);
  return match ? match[1] : null;
}

function resolveEntrypoint() {
  let resolved = null;
  let error = null;
  try { resolved = require.resolve(MAIN_PATH); } catch (caught) { error = boundedText(caught.message); }
  return {
    packageMain: packageManifest.main,
    resolvedMain: sanitizePath(resolved),
    productionEntrypointUsed: resolved === MAIN_PATH,
    error
  };
}

function binaryCheck() {
  const version = runCommand(ELECTRON_EXECUTABLE, ["--version"], { cwd: ROOT, timeout: 10000 });
  const file = runCommand("file", [ELECTRON_EXECUTABLE]);
  const architecture = architectureFromFile(file);
  return {
    executablePath: "<browser-host-electron-executable>",
    version,
    file,
    architecture,
    architectureMatchesHost: !architecture || architecture === process.arch || (architecture === "arm64" && process.arch === "arm64")
  };
}

function waitForChild(child, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => { if (!settled) { settled = true; clearTimeout(timer); resolve(value); } };
    const timer = setTimeout(() => {
      try { child.kill("SIGTERM"); } catch { /* process may already be gone */ }
      finish({ exitCode: null, signal: "SIGTERM", timedOut: true });
    }, timeoutMs);
    child.once("close", (exitCode, signal) => finish({ exitCode, signal, timedOut: false }));
    child.once("error", (error) => finish({ exitCode: null, signal: null, error: boundedText(error.message), timedOut: false }));
  });
}

async function directEntrypointLaunch() {
  const startedAt = Date.now();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-live-direct-"));
  try {
    const child = spawn(ELECTRON_EXECUTABLE, ["--user-data-dir", profile, MAIN_PATH], {
      cwd: ROOT,
      env: safeDiagnosticEnvironment({
        CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: "http://127.0.0.1:1",
        CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: "http://127.0.0.1:2"
      }),
      stdio: ["ignore", "pipe", "pipe"]
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += chunk.toString("utf8"); });
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
    const result = await waitForChild(child, 2500);
    return {
      ...result,
      startupDurationMs: Date.now() - startedAt,
      firstStdoutLine: firstLine(stdout),
      stderrLines: sanitizeOutput(stderr).split(/\r?\n/).filter(Boolean).slice(0, MAX_STDERR_LINES),
      processSurvivedStartupWindow: result.timedOut === true,
      temporaryProfileRemaining: false
    };
  } finally {
    fs.rmSync(profile, { recursive: true, force: true });
  }
}

function remoteEvaluate(app, source) {
  return app.evaluate(({ BrowserWindow }, script) => {
    const view = BrowserWindow.getAllWindows()[0]?.contentView?.children?.[0];
    if (!view) throw new Error("remote_view_missing");
    return view.webContents.executeJavaScript(script, true);
  }, source);
}

async function waitForState(trusted, predicate, timeoutMs = 12000) {
  const startedAt = Date.now();
  let state = null;
  while (Date.now() - startedAt < timeoutMs) {
    state = await trusted.evaluate(() => window.codexifyBrowserHost.getState());
    if (predicate(state)) return state;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`state_timeout:${state?.runtimeStatus || "unknown"}`);
}

async function runPlaywrightSmoke({ screenshotPath = null } = {}) {
  const fixture = await startFixtureServer({ label: "live-electron-launch" });
  const guardian = await startGuardianStub({
    token: PROOF_TOKEN,
    responseDelayMs: 250,
    enabledFeatures: ["capture:selected", "capture:visible", "capture:attach"]
  });
  let app = null;
  let trusted = null;
  let appProcess = null;
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-live-electron-"));
  const observation = {
    launchMethod: "playwright_electron",
    productionEntrypointUsed: false,
    whenReadyCompleted: false,
    trustedWindowCreated: false,
    trustedUrlIsLocalFile: false,
    preloadLoaded: false,
    trustedShellReady: false,
    trustedStateRead: false,
    preloadMethodInventory: [],
    negotiationTransport: "deterministic_stub",
    negotiationCompatible: false,
    remoteRequestBeforeCompatibility: false,
    remoteLoadedAfterCompatibility: false,
    rendererAuthorityDenialResult: null,
    captureAttempted: false,
    attachmentAttempted: false,
    exitCode: null,
    exitSignal: null,
    cleanupResult: "not_run",
    failure: null,
    unhandledRejections: [],
    temporaryProfileCreated: true,
    temporaryProfileRemaining: null,
    screenshotPath: null
  };
  const unhandledRejectionHandler = (reason) => {
    const message = boundedText(reason?.message || reason, 240);
    if (message && !observation.unhandledRejections.includes(message)) observation.unhandledRejections.push(message);
  };
  process.on("unhandledRejection", unhandledRejectionHandler);
  try {
    observation.productionEntrypointUsed = true;
    app = await electron.launch({
      executablePath: ELECTRON_EXECUTABLE,
      args: ["--user-data-dir", profile, MAIN_PATH],
      cwd: ROOT,
      env: safeDiagnosticEnvironment({
        CODEXIFY_BROWSER_HOST_GUARDIAN_ORIGIN: guardian.origin,
        CODEXIFY_BROWSER_HOST_FIXTURE_ORIGIN: fixture.origin
      }),
      timeout: 30000
    });
    appProcess = typeof app.process === "function" ? app.process() : null;
    observation.whenReadyCompleted = true;
    trusted = await app.firstWindow();
    observation.trustedWindowCreated = Boolean(trusted);
    await trusted.waitForLoadState("domcontentloaded");
    observation.trustedUrlIsLocalFile = trusted.url().startsWith("file://");
    const preload = await trusted.evaluate((expected) => {
      const api = window.codexifyBrowserHost;
      return { loaded: Boolean(api), methods: api ? Object.keys(api).sort() : [], expectedMatch: api ? JSON.stringify(Object.keys(api).sort()) === JSON.stringify(expected) : false };
    }, EXPECTED_PRELOAD_METHODS);
    observation.preloadLoaded = preload.loaded && preload.expectedMatch;
    observation.preloadMethodInventory = preload.methods;
    const initial = await trusted.evaluate(() => window.codexifyBrowserHost.getState());
    observation.trustedStateRead = Boolean(initial && typeof initial.runtimeStatus === "string");
    observation.trustedShellReady = observation.trustedUrlIsLocalFile && observation.preloadLoaded && observation.trustedStateRead;
    let negotiating = initial;
    try {
      negotiating = await waitForState(trusted, (state) => state.runtimeStatus === "negotiating" || state.runtimeStatus === "negotiated" || state.runtimeStatus === "degraded", 3000);
    } catch { /* final state below remains authoritative for the bounded smoke */ }
    observation.remoteRequestBeforeCompatibility = negotiating.runtimeStatus === "negotiating" && fixture.requests.length > 0;
    const compatible = await waitForState(trusted, (state) => state.runtimeStatus === "negotiated" && state.remoteStatus === "ready", 15000);
    observation.negotiationCompatible = compatible.guardianCompatibilityOutcome === "compatible";
    observation.remoteLoadedAfterCompatibility = compatible.remoteLoadedAfterGuardianNegotiation === true && fixture.requests.length > 0;
    observation.rendererAuthorityDenialResult = await remoteEvaluate(app, "({ node: typeof globalThis.process !== 'undefined', electron: typeof globalThis.require !== 'undefined', bridge: typeof globalThis.codexifyBrowserHost !== 'undefined', ipc: typeof globalThis.ipcRenderer !== 'undefined' })");
    if (screenshotPath) {
      fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
      await trusted.screenshot({ path: screenshotPath });
      observation.screenshotPath = sanitizePath(screenshotPath);
    }
    return observation;
  } catch (error) {
    observation.failure = sanitizeOutput(error?.message || error);
    return observation;
  } finally {
    try {
      if (app) {
        await app.close();
        observation.exitCode = typeof appProcess?.exitCode === "number" ? appProcess.exitCode : null;
        observation.exitSignal = appProcess?.signalCode || null;
      }
      observation.cleanupResult = "passed";
    } catch (error) {
      observation.cleanupResult = `failed:${boundedText(error?.message || error, 180)}`;
    }
    await guardian.close().catch(() => {});
    await fixture.close().catch(() => {});
    fs.rmSync(profile, { recursive: true, force: true });
    observation.temporaryProfileRemaining = fs.existsSync(profile);
    if (observation.temporaryProfileRemaining) observation.cleanupResult = "failed:temporary_profile_remaining";
    await new Promise((resolve) => setImmediate(resolve));
    process.off("unhandledRejection", unhandledRejectionHandler);
  }
}

function classifyRootCause(result) {
  if (!result.entrypoint.productionEntrypointUsed) return "entrypoint_resolution";
  if (!result.binary.architectureMatchesHost) return "binary_architecture";
  if (result.binary.version.exitCode !== 0) {
    if (result.mac?.spctl?.exitCode !== 0 || /adhoc/i.test(result.mac?.codesign?.stderr || result.mac?.codesign?.stdout || "")) return "host_security_assessment";
    if (result.mac?.graphicalSession?.available === false) return "graphical_session_unavailable";
    return "external_environment_restriction";
  }
  if (result.playwright.failure && result.playwright.failure.includes("Process failed to launch")) return "unknown_next_proof_needed";
  if (!result.playwright.trustedWindowCreated) return "application_startup";
  if (!result.playwright.preloadLoaded || !result.playwright.trustedStateRead) return "application_startup";
  if (result.playwright.remoteRequestBeforeCompatibility) return "application_startup";
  if (result.playwright.cleanupResult !== "passed") return "cleanup_or_early_exit";
  return null;
}

function statusFor(result, classification) {
  const invariantFailure = result.playwright.trustedWindowCreated && (
    !result.playwright.trustedUrlIsLocalFile || !result.playwright.preloadLoaded ||
    !result.playwright.trustedStateRead || result.playwright.remoteRequestBeforeCompatibility ||
    (result.playwright.negotiationCompatible && !result.playwright.remoteLoadedAfterCompatibility) ||
    result.playwright.rendererAuthorityDenialResult?.node || result.playwright.rendererAuthorityDenialResult?.electron ||
    result.playwright.rendererAuthorityDenialResult?.bridge || result.playwright.rendererAuthorityDenialResult?.ipc ||
    result.playwright.cleanupResult !== "passed"
  );
  if (invariantFailure) return "failed";
  if (!classification && result.playwright.negotiationCompatible && result.playwright.remoteLoadedAfterCompatibility) return "passed";
  return "next-proof-needed";
}

async function runDiagnostic({ screenshotPath = null } = {}) {
  const versions = packageVersions();
  const result = {
    diagnosticVersion: "1.0.0",
    repositoryRoot: "<browser-host-root>",
    versions,
    entrypoint: resolveEntrypoint(),
    mac: macAssessment(),
    binary: binaryCheck(),
    directLaunch: await directEntrypointLaunch(),
    playwright: await runPlaywrightSmoke({ screenshotPath })
  };
  result.primaryClassification = classifyRootCause(result);
  result.status = statusFor(result, result.primaryClassification);
  result.nonClaims = [
    "real Guardian authentication", "durable persistence", "attachment execution", "packaging", "signing", "notarization", "supported release"
  ];
  return result;
}

if (require.main === module) {
  runDiagnostic()
    .then((result) => process.stdout.write(`${JSON.stringify(result, null, 2)}\n`))
    .catch((error) => {
      process.stdout.write(`${JSON.stringify({ status: "next-proof-needed", primaryClassification: "unknown_next_proof_needed", failure: boundedText(error?.message || error) }, null, 2)}\n`);
    });
}

module.exports = Object.freeze({
  CLASSIFICATIONS,
  EXPECTED_PRELOAD_METHODS,
  MAIN_PATH,
  PREREQUISITE_COMMIT,
  runDiagnostic,
  runPlaywrightSmoke,
  classifyRootCause,
  statusFor
});
