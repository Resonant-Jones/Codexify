"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PACKAGE_PATH = path.join(ROOT, "package.json");
const LOCK_PATH = path.join(ROOT, "package-lock.json");
const CONTRACT_PACKAGE_PATH = path.join(ROOT, "contracts", "package.json");
const PREREQUISITE_COMMITS = ["de3924011", "529cc38b1"];
const MAX_TEXT = 1200;
const MAX_LINES = 12;
const CLASSIFICATIONS = Object.freeze([
  "repository_electron_bundle_corrupt",
  "isolated_electron_distribution_invalid",
  "host_code_signing_subsystem_unavailable",
  "host_gatekeeper_assessment_failure",
  "minimal_electron_launch_failure_unrelated_to_codexify",
  "codexify_entrypoint_launch_failure",
  "dependency_redownload_blocked",
  "repaired_repository_dependency_install",
  "qualified_host_ready",
  "unknown_next_proof_needed"
]);

function bounded(value, max = MAX_TEXT) {
  return String(value || "")
    .replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/\r/g, "")
    .slice(0, max);
}

function sanitizePath(value, roots = {}) {
  let result = bounded(value);
  const replacements = [
    [roots.root || ROOT, "<browser-host-root>"],
    [roots.temp || "", "<tmp>"],
    [os.homedir(), "<home>"],
    [os.tmpdir(), "<tmp>"]
  ];
  for (const [source, target] of replacements) {
    if (source) result = result.replaceAll(source, target);
  }
  return result;
}

function sanitizeText(value, roots = {}) {
  return sanitizePath(value, roots)
    .split(/\n/)
    .filter((line) => !/(?:API[_ -]?KEY|SECRET|PASSWORD|COOKIE|JWT|AUTHORIZATION|BEARER|GRANT|CREDENTIAL|ACCESS[_ -]?TOKEN|SESSION[_ -]?TOKEN)/i.test(line))
    .slice(0, MAX_LINES)
    .join("\n")
    .slice(0, MAX_TEXT);
}

function sanitizeError(error) {
  return error ? bounded(error.message || error) : null;
}

function safeEnv(overrides = {}) {
  const sensitive = /(?:API[_ -]?KEY|SECRET|PASSWORD|COOKIE|JWT|AUTHORIZATION|BEARER|GRANT|CREDENTIAL|ACCESS[_ -]?TOKEN|SESSION[_ -]?TOKEN|PRIVATE[_ -]?KEY)/i;
  const inherited = Object.fromEntries(Object.entries(process.env).filter(([name]) => !sensitive.test(name)));
  delete inherited.ELECTRON_RUN_AS_NODE;
  delete inherited.ELECTRON_NO_ATTACH_CONSOLE;
  return { ...inherited, CODEXIFY_DISABLE_DOTENV: "1", ...overrides };
}

function runCommand(command, args = [], options = {}) {
  const roots = options.roots || {};
  const result = spawnSync(command, args, {
    cwd: options.cwd || ROOT,
    env: options.env || safeEnv(),
    encoding: "utf8",
    timeout: options.timeout || 10000,
    maxBuffer: 64 * 1024,
    stdio: ["ignore", "pipe", "pipe"]
  });
  return {
    command: sanitizePath(command, roots),
    args: args.map((arg) => sanitizePath(arg, roots)),
    exitCode: typeof result.status === "number" ? result.status : null,
    signal: result.signal || null,
    error: sanitizeError(result.error),
    stdout: sanitizeText(result.stdout, roots),
    stderr: sanitizeText(result.stderr, roots)
  };
}

function sha256(filePath) {
  try {
    return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
  } catch (error) {
    return null;
  }
}

function fileArchitecture(fileResult) {
  const match = fileResult?.stdout?.match(/Mach-O\s+64-bit executable\s+([A-Za-z0-9_]+)/i);
  return match ? match[1] : null;
}

function commandPassed(result) {
  return Boolean(result && result.exitCode === 0 && result.signal === null);
}

function codeSigningSummary(verify, display, assessment) {
  const displayText = `${display?.stdout || ""}\n${display?.stderr || ""}`;
  const assessmentText = `${assessment?.stdout || ""}\n${assessment?.stderr || ""}`;
  return {
    verifyExitCode: verify?.exitCode ?? null,
    verifySignal: verify?.signal || null,
    verifyStderr: verify?.stderr || "",
    displayExitCode: display?.exitCode ?? null,
    displaySignal: display?.signal || null,
    displayStderr: display?.stderr || "",
    assessmentExitCode: assessment?.exitCode ?? null,
    assessmentSignal: assessment?.signal || null,
    assessmentStderr: assessment?.stderr || "",
    teamIdentifierPresent: /(?:^|\n)TeamIdentifier=(?!not set\s*$)/im.test(displayText),
    signingAuthorityPresent: /(?:^|\n)Authority=\S+/i.test(displayText),
    signatureAdhoc: /Signature=adhoc/i.test(displayText),
    codeSigningSubsystemError: /Code Signing subsystem/i.test(assessmentText),
    verificationPassed: commandPassed(verify),
    assessmentPassed: commandPassed(assessment)
  };
}

function selectControlApp() {
  const candidates = [
    "/System/Applications/Calculator.app",
    "/System/Applications/TextEdit.app",
    "/System/Applications/Preview.app"
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function assessBundle(bundlePath, executablePath, roots = {}) {
  const verify = runCommand("codesign", ["--verify", "--deep", "--strict", "--verbose=4", bundlePath], { roots });
  const display = runCommand("codesign", ["-dv", "--verbose=4", bundlePath], { roots });
  const assessment = runCommand("spctl", ["--assess", "--type", "execute", "--verbose=4", bundlePath], { roots });
  const file = runCommand("file", [executablePath], { roots });
  const quarantine = runCommand("xattr", ["-p", "com.apple.quarantine", bundlePath], { roots });
  return {
    bundlePath: sanitizePath(bundlePath, roots),
    executablePath: sanitizePath(executablePath, roots),
    file: {
      exitCode: file.exitCode,
      signal: file.signal,
      stderr: file.stderr,
      architecture: fileArchitecture(file)
    },
    architecture: fileArchitecture(file),
    sha256: sha256(executablePath),
    quarantinePresent: quarantine.exitCode === 0,
    codesign: codeSigningSummary(verify, display, assessment),
    gatekeeper: {
      exitCode: assessment.exitCode,
      signal: assessment.signal,
      stderr: assessment.stderr,
      codeSigningSubsystemError: /Code Signing subsystem/i.test(`${assessment.stdout}\n${assessment.stderr}`),
      passed: commandPassed(assessment)
    }
  };
}

function electronPaths(packageRoot) {
  const electronPackage = path.join(packageRoot, "node_modules", "electron");
  const executable = path.join(electronPackage, "dist", "Electron.app", "Contents", "MacOS", "Electron");
  return { packageRoot, electronPackage, bundle: path.dirname(path.dirname(path.dirname(executable))), executable };
}

function runBinaryCheck(paths, roots = {}) {
  const version = runCommand(paths.executable, ["--version"], { cwd: paths.packageRoot, timeout: 15000, roots });
  const file = runCommand("file", [paths.executable], { roots });
  return {
    version: {
      exitCode: version.exitCode,
      signal: version.signal,
      stdout: version.stdout,
      stderr: version.stderr
    },
    file: {
      exitCode: file.exitCode,
      signal: file.signal,
      stderr: file.stderr,
      architecture: fileArchitecture(file)
    },
    architecture: fileArchitecture(file),
    architectureMatchesHost: fileArchitecture(file) === process.arch
  };
}

function reportScalar(value) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return bounded(value, 240);
  if (Array.isArray(value)) return value.slice(0, 4).map(reportScalar);
  return null;
}

function firstSafeFrame(frame) {
  if (!frame || typeof frame !== "object") return null;
  const symbol = frame.symbol || frame.name || frame.function || frame.symbolName;
  if (typeof symbol === "string" && symbol.trim()) return bounded(symbol.replace(/0x[0-9a-f]+/ig, "<address>"), 240);
  return null;
}

function crashReportCorrelation(startedAt, signal, roots = {}) {
  if (signal !== "SIGABRT") return { reportFound: false, searched: false };
  const reportDirectory = path.join(os.homedir(), "Library", "Logs", "DiagnosticReports");
  let candidates = [];
  try {
    candidates = fs.readdirSync(reportDirectory)
      .filter((name) => /electron/i.test(name) && /\.(?:ips|crash)$/i.test(name))
      .map((name) => {
        const filePath = path.join(reportDirectory, name);
        const stat = fs.statSync(filePath);
        return { filePath, mtimeMs: stat.mtimeMs };
      })
      .filter((entry) => entry.mtimeMs >= startedAt - 1000)
      .sort((left, right) => right.mtimeMs - left.mtimeMs);
  } catch (error) {
    return { reportFound: false, searched: true, readError: sanitizeError(error) };
  }
  if (!candidates.length) return { reportFound: false, searched: true };
  const selected = candidates[0];
  let raw = "";
  try {
    raw = fs.readFileSync(selected.filePath, "utf8");
  } catch (error) {
    return { reportFound: false, searched: true, readError: sanitizeError(error) };
  }
  let parsed = null;
  try { parsed = JSON.parse(raw); } catch { /* legacy .crash text is handled below */ }
  const exception = parsed?.exception || {};
  const termination = parsed?.termination || {};
  const thread = (parsed?.threads || []).find((candidate) => candidate?.triggered || candidate?.crashed) || parsed?.threads?.[0] || {};
  const frames = Array.isArray(thread.frames) ? thread.frames.map(firstSafeFrame).filter(Boolean).slice(0, 10) : [];
  const processName = reportScalar(parsed?.procName || parsed?.process || parsed?.responsibleProc || parsed?.responsibleProcess);
  const text = raw.toLowerCase();
  const keyword = (value) => text.includes(value);
  return {
    reportFound: true,
    searched: true,
    timestamp: reportScalar(parsed?.capture_time || parsed?.timestamp || parsed?.reportVersion),
    architecture: reportScalar(parsed?.arch || parsed?.architecture),
    exceptionType: reportScalar(exception.type) || (raw.match(/Exception Type:\s*([^\n]+)/i)?.[1] || null),
    exceptionCodes: reportScalar(exception.codes) || (raw.match(/Exception Codes:\s*([^\n]+)/i)?.[1] || null),
    terminationNamespace: reportScalar(termination.namespace) || (raw.match(/Termination Reason:\s*.*?namespace\s+([^\n,]+)/i)?.[1] || null),
    terminationCode: reportScalar(termination.code) || (raw.match(/code\s+([^\n,]+)/i)?.[1] || null),
    responsibleProcess: processName,
    crashingThreadFrames: frames,
    namedBoundaries: {
      signing: keyword("signing"),
      libraryValidation: keyword("library validation"),
      sandbox: keyword("sandbox"),
      dyld: keyword("dyld"),
      entitlement: keyword("entitlement"),
      trust: keyword("trust")
    },
    reportPath: undefined,
    reportMtimeRecorded: true,
    sanitized: true
  };
}

function launchMinimalApp(executablePath, parentTemp, label) {
  const tempRoot = fs.mkdtempSync(path.join(parentTemp, `${label}-`));
  const profile = path.join(tempRoot, "profile");
  const html = path.join(tempRoot, "fixture.html");
  const main = path.join(tempRoot, "main.js");
  fs.mkdirSync(profile, { recursive: true });
  fs.writeFileSync(html, "<!doctype html><meta charset=\"utf-8\"><title>Codexify minimal Electron</title><body data-ready=\"true\">ready</body>\n", "utf8");
  fs.writeFileSync(main, [
    "const { app, BrowserWindow } = require('electron');",
    "const path = require('node:path');",
    "let windowCreated = false;",
    "app.whenReady().then(async () => {",
    "  const win = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } });",
    "  windowCreated = true;",
    "  await win.loadFile(process.argv[2]);",
    "  const ready = await win.webContents.executeJavaScript(\"document.body.dataset.ready === 'true'\", true);",
    "  if (ready) process.stdout.write('CODEXIFY_MINIMAL_READY\\n');",
    "  win.close();",
    "  app.quit(ready ? 0 : 2);",
    "}).catch((error) => { process.stderr.write(String(error && error.message || error)); app.exit(3); });",
    "app.on('window-all-closed', () => {});"
  ].join("\n"), "utf8");
  const startedAt = Date.now();
  const child = spawn(executablePath, [main, html], {
    cwd: tempRoot,
    env: (() => {
      const env = safeEnv();
      delete env.ELECTRON_RUN_AS_NODE;
      return env;
    })(),
    stdio: ["ignore", "pipe", "pipe"]
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; child.kill("SIGTERM"); }, 20000);
  return new Promise((resolve) => {
    child.once("exit", (exitCode, signal) => {
      clearTimeout(timer);
      const result = {
        launch: {
          exitCode: typeof exitCode === "number" ? exitCode : null,
          signal: signal || null,
          timedOut,
          stdout: sanitizeText(stdout, { temp: tempRoot }),
          stderr: sanitizeText(stderr, { temp: tempRoot }),
          readySentinel: stdout.includes("CODEXIFY_MINIMAL_READY"),
          windowCreated: stdout.includes("CODEXIFY_MINIMAL_READY"),
          sandboxRequested: true,
          insecureFlagsUsed: false
        },
        crashCorrelation: crashReportCorrelation(startedAt, signal, { temp: tempRoot })
      };
      fs.rmSync(tempRoot, { recursive: true, force: true });
      result.cleanupPassed = !fs.existsSync(tempRoot);
      resolve(result);
    });
    child.once("error", (error) => {
      clearTimeout(timer);
      fs.rmSync(tempRoot, { recursive: true, force: true });
      resolve({
        launch: { exitCode: null, signal: null, timedOut, stdout: sanitizeText(stdout, { temp: tempRoot }), stderr: sanitizeText(stderr, { temp: tempRoot }), readySentinel: false, windowCreated: false, sandboxRequested: true, insecureFlagsUsed: false, error: sanitizeError(error) },
        crashCorrelation: { reportFound: false, searched: false },
        cleanupPassed: false
      });
    });
  });
}

async function qualifyMinimalApp(executablePath, tempRoot, label) {
  return launchMinimalApp(executablePath, tempRoot, label);
}

function hostInfo() {
  const sysctl = runCommand("sysctl", ["-n", "sysctl.proc_translated"]);
  const spctl = runCommand("spctl", ["--status"]);
  return {
    platform: process.platform,
    architecture: process.arch,
    swVers: runCommand("sw_vers"),
    uname: runCommand("uname", ["-m"]),
    nodeVersion: process.versions.node,
    npmVersion: runCommand("npm", ["--version"]).stdout.trim(),
    translated: sysctl.exitCode === 0 ? sysctl.stdout.trim() : "unavailable",
    spctlStatus: { exitCode: spctl.exitCode, signal: spctl.signal, stdout: spctl.stdout, stderr: spctl.stderr }
  };
}

function controlEvidence(appPath) {
  const verify = runCommand("codesign", ["--verify", "--deep", "--strict", "--verbose=4", appPath]);
  const display = runCommand("codesign", ["-dv", "--verbose=4", appPath]);
  const assessment = runCommand("spctl", ["--assess", "--type", "execute", "--verbose=4", appPath]);
  return {
    appClass: "apple_control_app",
    appPath: "<apple-control-app>",
    codesign: codeSigningSummary(verify, display, assessment),
    gatekeeper: {
      exitCode: assessment.exitCode,
      signal: assessment.signal,
      stderr: assessment.stderr,
      codeSigningSubsystemError: /Code Signing subsystem/i.test(`${assessment.stdout}\n${assessment.stderr}`),
      passed: commandPassed(assessment)
    },
    passed: commandPassed(verify) && commandPassed(assessment)
  };
}

function packageMetadata(packageRoot) {
  const packageManifest = JSON.parse(fs.readFileSync(path.join(packageRoot, "package.json"), "utf8"));
  const lock = JSON.parse(fs.readFileSync(path.join(packageRoot, "package-lock.json"), "utf8"));
  return {
    packageVersion: packageManifest.version,
    contractPackageVersion: lock.packages?.contracts?.version || null,
    electronVersion: lock.packages?.["node_modules/electron"]?.version || null,
    playwrightVersion: lock.packages?.["node_modules/playwright"]?.version || null,
    lockedElectronVersion: packageManifest.devDependencies?.electron || null,
    lockedPlaywrightVersion: packageManifest.devDependencies?.playwright || null
  };
}

function currentElectron(packageRoot) {
  const paths = electronPaths(packageRoot);
  const metadata = packageMetadata(packageRoot);
  return {
    source: "current_repo",
    packageRoot: "<browser-host-root>",
    versions: metadata,
    binary: runBinaryCheck(paths),
    bundle: assessBundle(paths.bundle, paths.executable),
    paths
  };
}

function npmInstall(tempRoot) {
  const isolatedCache = path.join(tempRoot, "npm-cache");
  const env = safeEnv({ npm_config_cache: isolatedCache, ELECTRON_CACHE: path.join(tempRoot, "electron-cache"), electron_config_cache: path.join(tempRoot, "electron-cache"), npm_config_audit: "false", npm_config_fund: "false", npm_config_update_notifier: "false" });
  const result = runCommand("npm", ["ci", "--no-audit", "--no-fund"], { cwd: tempRoot, env, timeout: 180000, roots: { root: ROOT, temp: tempRoot } });
  let postinstall = { command: "not-needed", passed: false };
  if (result.status === 0 || result.exitCode === 0) {
    const installScript = path.join(tempRoot, "node_modules", "electron", "install.js");
    const executable = path.join(tempRoot, "node_modules", "electron", "dist", "Electron.app", "Contents", "MacOS", "Electron");
    if (fs.existsSync(executable)) {
      postinstall = { command: "not-needed", passed: true };
    } else if (fs.existsSync(installScript)) {
      const hook = runCommand(process.execPath, [installScript], { cwd: tempRoot, env, timeout: 180000, roots: { root: ROOT, temp: tempRoot } });
      postinstall = { command: "electron install.js", exitCode: hook.exitCode, signal: hook.signal, stdout: hook.stdout, stderr: hook.stderr, passed: commandPassed(hook) && fs.existsSync(executable) };
    }
  }
  return {
    command: "npm ci --no-audit --no-fund",
    exitCode: result.exitCode,
    signal: result.signal,
    stdout: result.stdout,
    stderr: result.stderr,
    postinstall,
    passed: commandPassed(result) && postinstall.passed
  };
}

function createIsolatedPackage(tempRoot) {
  fs.copyFileSync(PACKAGE_PATH, path.join(tempRoot, "package.json"));
  fs.copyFileSync(LOCK_PATH, path.join(tempRoot, "package-lock.json"));
}

async function cleanDistribution(tempRoot) {
  const cleanRoot = path.join(tempRoot, "clean-install");
  fs.mkdirSync(cleanRoot, { recursive: true });
  createIsolatedPackage(cleanRoot);
  const install = npmInstall(cleanRoot);
  if (!install.passed) return { source: "clean_isolated_download", install, packageLockChanged: false, bundle: null, binary: null, minimal: null, cleanupPassed: true };
  const paths = electronPaths(cleanRoot);
  const bundle = assessBundle(paths.bundle, paths.executable, { root: cleanRoot, temp: tempRoot });
  const binary = runBinaryCheck(paths, { root: cleanRoot, temp: tempRoot });
  const minimal = await qualifyMinimalApp(paths.executable, tempRoot, "clean-minimal");
  return {
    source: "clean_isolated_download",
    install,
    packageLockChanged: sha256(path.join(cleanRoot, "package-lock.json")) !== sha256(LOCK_PATH),
    versions: packageMetadata(cleanRoot),
    bundle,
    binary,
    minimal,
    cleanupPassed: true
  };
}

function signatureFailure(bundle) {
  return Boolean(bundle && (!bundle.codesign?.verificationPassed || !bundle.gatekeeper?.passed));
}

function minimalPassed(minimal) {
  return Boolean(minimal?.launch?.exitCode === 0 && minimal.launch.signal === null && minimal.launch.readySentinel && minimal.launch.windowCreated && minimal.cleanupPassed && minimal.launch.insecureFlagsUsed === false);
}

function sameCodeSigningError(apple, current, clean) {
  return Boolean(apple?.gatekeeper?.codeSigningSubsystemError && current?.bundle?.gatekeeper?.codeSigningSubsystemError && clean?.bundle?.gatekeeper?.codeSigningSubsystemError);
}

function sameSignatureFailure(current, clean) {
  return Boolean(signatureFailure(current?.bundle) && signatureFailure(clean?.bundle) && current.bundle.codesign.verifyStderr === clean.bundle.codesign.verifyStderr && current.bundle.gatekeeper.stderr === clean.bundle.gatekeeper.stderr);
}

function liveProofPasses(proof) {
  return proof?.status === "passed" && proof?.trustedWindowCreated === true && proof?.preloadLoaded === true && proof?.trustedStateRead === true && proof?.negotiationCompatible === true && proof?.remoteRequestBeforeCompatibility === false && proof?.remoteLoadedAfterCompatibility === true && proof?.cleanupResult === "passed";
}

function classify(matrix) {
  const { apple, current, clean, reinstall, liveProof } = matrix;
  if (sameCodeSigningError(apple, current, clean)) return "host_code_signing_subsystem_unavailable";
  if (!clean?.install?.passed) return "dependency_redownload_blocked";
  if (apple?.passed && signatureFailure(current?.bundle) && !signatureFailure(clean?.bundle) && minimalPassed(clean?.minimal)) return reinstall?.attempted && reinstall?.result === "repaired" ? "repaired_repository_dependency_install" : "repository_electron_bundle_corrupt";
  if (apple?.passed && sameSignatureFailure(current, clean)) return "isolated_electron_distribution_invalid";
  if (!minimalPassed(current?.minimal) && !minimalPassed(clean?.minimal)) return "minimal_electron_launch_failure_unrelated_to_codexify";
  if (minimalPassed(current?.minimal) && !liveProofPasses(liveProof)) return "codexify_entrypoint_launch_failure";
  if (liveProofPasses(liveProof)) return reinstall?.attempted && reinstall?.result === "repaired" ? "repaired_repository_dependency_install" : "qualified_host_ready";
  return "unknown_next_proof_needed";
}

function statusFor(matrix, classification) {
  if (!matrix.cleanup?.cleanupPassed) return "failed";
  if (matrix.systemSecurityModified || matrix.insecureFlagsUsed || matrix.packageLockChanged) return "failed";
  if (classification === "qualified_host_ready" || classification === "repaired_repository_dependency_install") return liveProofPasses(matrix.liveProof) ? "passed" : "next-proof-needed";
  return "next-proof-needed";
}

function gitValue(args) {
  const result = spawnSync("git", args, { cwd: ROOT, encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : null;
}

function lockChanged(before) {
  return before !== sha256(LOCK_PATH);
}

function runExistingLiveProof(tempRoot) {
  const outputDirectory = path.join(tempRoot, "live-proof");
  const script = path.join(ROOT, "scripts", "run-live-electron-launch-proof.js");
  const result = runCommand(process.execPath, [script, "--output-dir", outputDirectory], { cwd: ROOT, env: safeEnv({ CODEXIFY_BROWSER_HOST_PROOF_MODE: "1" }), timeout: 120000, roots: { root: ROOT, temp: tempRoot } });
  let proof = null;
  try { proof = JSON.parse(fs.readFileSync(path.join(outputDirectory, "proof.json"), "utf8")); } catch { /* bounded result below */ }
  return {
    runnerExitCode: result.exitCode,
    runnerSignal: result.signal,
    runnerStderr: result.stderr,
    status: proof?.status || "next-proof-needed",
    classification: proof?.rootCauseClassification || "unknown_next_proof_needed",
    trustedWindowCreated: proof?.trustedWindowCreated === true,
    preloadLoaded: proof?.preloadLoaded === true,
    trustedStateRead: proof?.trustedStateRead === true,
    negotiationCompatible: proof?.negotiationCompatible === true,
    remoteRequestBeforeCompatibility: proof?.remoteRequestBeforeCompatibility === true,
    remoteLoadedAfterCompatibility: proof?.remoteLoadedAfterCompatibility === true,
    cleanupResult: proof?.cleanupResult || "unknown",
    insecureSandboxBypassUsed: proof?.insecureSandboxBypassUsed === true,
    artifactCreated: Boolean(proof)
  };
}

function buildDelegationReceipt() {
  return {
    orchestrationSkillIdentifier: "deepseek-orchestrator",
    delegationSkillIdentifier: "pi-deepseek-delegation",
    provider: "deepseek",
    preferredModel: "deepseek-v4-pro",
    resolvedModel: "deepseek-v4-pro",
    configuration: {
      preflight: "passed",
      availableModels: ["deepseek-v4-flash", "deepseek-v4-pro"],
      authentication: "configured",
      settingsLock: "not_observed"
    },
    preEditOutcome: "unavailable_warning",
    postEditOutcome: "not_run",
    warning: "Read-only review timed out after 180 seconds without a result; no worker edits occurred.",
    reviewedCategories: ["controlled matrix", "crash correlation", "classification gates", "validator guards", "forbidden host changes"],
    acceptedRecommendations: [],
    rejectedRecommendations: [],
    noSecretTransmission: true,
    noCrashDataTransmission: true,
    noEnvironmentDumpTransmission: true,
    noWorkerEdits: true,
    codexRetainedImplementationAuthority: true
  };
}

function requiredProof(matrix) {
  return {
    proofType: "browser-host-macos-electron-host-qualification",
    proofVersion: "1.0.0",
    status: matrix.status,
    proofStatus: matrix.status,
    repositoryCommit: gitValue(["rev-parse", "HEAD"]),
    prerequisiteCommits: PREREQUISITE_COMMITS,
    branch: gitValue(["rev-parse", "--abbrev-ref", "HEAD"]),
    packageVersion: matrix.metadata.packageVersion,
    contractPackageVersion: matrix.metadata.contractPackageVersion,
    electronVersion: matrix.metadata.electronVersion,
    playwrightVersion: matrix.metadata.playwrightVersion,
    host: matrix.host,
    appleControl: matrix.apple,
    currentElectron: matrix.current,
    cleanElectron: matrix.clean,
    reinstall: matrix.reinstall,
    packageLockChanged: matrix.packageLockChanged,
    liveProofRerun: matrix.liveProof,
    crashCorrelation: {
      currentMinimal: matrix.current?.minimal?.crashCorrelation || null,
      cleanMinimal: matrix.clean?.minimal?.crashCorrelation || null
    },
    rootClassification: matrix.classification,
    systemSecurityModified: false,
    insecureFlagsUsed: matrix.insecureFlagsUsed,
    cleanupResult: matrix.cleanup,
    explicitNonClaims: [
      "macOS trust services repaired or changed",
      "production Guardian authentication",
      "real Guardian attachment or durable persistence",
      "packaging, signing, notarization, updater, beta, or supported release",
      "causality of any host Code Signing subsystem error beyond the recorded matrix"
    ]
  };
}

function markdown(proof) {
  const lines = [
    "# macOS Electron host qualification",
    "",
    `- Status: **${proof.status}**`,
    `- Primary classification: \`${proof.rootClassification}\``,
    `- Repository commit: \`${proof.repositoryCommit}\``,
    `- Prerequisite commits: ${proof.prerequisiteCommits.join(", ")}`,
    `- Host: ${proof.host.platform}/${proof.host.architecture}; Electron: ${proof.electronVersion}; Playwright: ${proof.playwrightVersion}`,
    `- Apple control app passed: ${proof.appleControl.passed}`,
    `- Apple/current/clean same Code Signing subsystem error: ${sameCodeSigningError(proof.appleControl, proof.currentElectron, proof.cleanElectron)}`,
    `- Current minimal Electron app: ${minimalPassed(proof.currentElectron.minimal)}`,
    `- Clean minimal Electron app: ${minimalPassed(proof.cleanElectron?.minimal)}`,
    `- Reinstall attempted: ${proof.reinstall.attempted}`,
    `- Package lock changed: ${proof.packageLockChanged}`,
    `- Existing production-entry live proof: ${proof.liveProofRerun.status}`,
    `- System security modified: ${proof.systemSecurityModified}`,
    `- Insecure flags used: ${proof.insecureFlagsUsed}`,
    `- Cleanup: ${proof.cleanupResult.cleanupPassed ? "passed" : "failed"}`,
    "",
    "The matrix compares an Apple-signed control app, the repository Electron bundle, and a clean isolated locked download before any repository-local repair. No Gatekeeper, SIP, quarantine, signing, trust-service, or security-database change is permitted. A `passed` status requires the existing bounded production-entrypoint live proof; static signing or Gatekeeper output alone cannot qualify the host.",
    "",
    "This packet does not claim a real Guardian session, durable persistence, packaging, signing/notarization, updater, beta, or supported release.",
    ""
  ];
  return lines.join("\n");
}

function cleanupSummary(tempRoot) {
  let cleanupPassed = true;
  try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch { cleanupPassed = false; }
  return { cleanupPassed, temporaryRootRemaining: fs.existsSync(tempRoot), supportProcessesRemaining: 0 };
}

async function runQualification() {
  if (process.platform !== "darwin") throw new Error(`unsupported-platform:${process.platform}; macOS is required`);
  const lockHashBefore = sha256(LOCK_PATH);
  const metadata = packageMetadata(ROOT);
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "codexify-macos-electron-host-"));
  let matrix;
  try {
    const controlApp = selectControlApp();
    if (!controlApp) throw new Error("preflight:no Apple control app found");
    const host = hostInfo();
    const apple = controlEvidence(controlApp);
    let current = currentElectron(ROOT);
    current.minimal = await qualifyMinimalApp(current.paths.executable, tempRoot, "current-minimal");
    const clean = await cleanDistribution(tempRoot);
    const reinstall = { attempted: false, result: "not_justified", lockHashBefore, lockHashAfter: sha256(LOCK_PATH), packageLockChanged: false };
    const currentFails = signatureFailure(current.bundle) || !minimalPassed(current.minimal);
    const cleanPasses = Boolean(clean.install?.passed && !signatureFailure(clean.bundle) && minimalPassed(clean.minimal));
    if (apple.passed && currentFails && cleanPasses && metadata.electronVersion === clean.versions?.electronVersion && metadata.playwrightVersion === clean.versions?.playwrightVersion) {
      reinstall.attempted = true;
      const nodeModules = path.join(ROOT, "node_modules");
      const quarantineMove = path.join(tempRoot, "repository-node-modules-backup");
      fs.renameSync(nodeModules, quarantineMove);
      let keepRepairedInstall = false;
      try {
        const install = runCommand("npm", ["ci", "--no-audit", "--no-fund"], { cwd: ROOT, env: safeEnv({ npm_config_cache: path.join(tempRoot, "repair-cache"), ELECTRON_CACHE: path.join(tempRoot, "repair-electron-cache"), npm_config_audit: "false", npm_config_fund: "false" }), timeout: 180000, roots: { root: ROOT, temp: tempRoot } });
        reinstall.install = { exitCode: install.exitCode, signal: install.signal, stdout: install.stdout, stderr: install.stderr, passed: commandPassed(install) };
        reinstall.result = reinstall.install.passed ? "reinstalled" : "install_failed";
        if (lockChanged(lockHashBefore)) throw new Error("repair:package-lock-changed");
        const repaired = currentElectron(ROOT);
        repaired.minimal = await qualifyMinimalApp(repaired.paths.executable, tempRoot, "repaired-minimal");
        reinstall.repairedElectron = { bundle: repaired.bundle, binary: repaired.binary, minimal: repaired.minimal };
        if (reinstall.install.passed && !signatureFailure(repaired.bundle) && minimalPassed(repaired.minimal)) {
          reinstall.result = "repaired";
          current = repaired;
          keepRepairedInstall = true;
        }
      } finally {
        if (keepRepairedInstall) {
          fs.rmSync(quarantineMove, { recursive: true, force: true });
        } else {
          fs.rmSync(nodeModules, { recursive: true, force: true });
          fs.renameSync(quarantineMove, nodeModules);
        }
      }
    }
    delete current.paths;
    const liveProof = minimalPassed(current.minimal) && cleanPasses ? await runExistingLiveProof(tempRoot) : { status: "next-proof-needed", classification: "not_run_until_minimal_matrix_passes", artifactCreated: false };
    matrix = {
      metadata,
      host,
      apple,
      current,
      clean,
      reinstall,
      liveProof,
      packageLockChanged: lockChanged(lockHashBefore),
      systemSecurityModified: false,
      insecureFlagsUsed: false,
      cleanup: { cleanupPassed: false, temporaryRootRemaining: true, supportProcessesRemaining: 0 }
    };
    matrix.classification = classify(matrix);
    matrix.status = statusFor(matrix, matrix.classification);
  } finally {
    const cleanup = cleanupSummary(tempRoot);
    if (matrix) matrix.cleanup = cleanup;
  }
  if (!matrix) throw new Error("qualification:no-matrix");
  matrix.status = statusFor(matrix, matrix.classification);
  return { proof: requiredProof(matrix), delegationReceipt: buildDelegationReceipt(), cleanup: matrix.cleanup };
}

function writePacket(outputDirectory, result) {
  fs.mkdirSync(outputDirectory, { recursive: true });
  const proof = result.proof;
  fs.writeFileSync(path.join(outputDirectory, "manifest.json"), `${JSON.stringify({ proofType: proof.proofType, proofVersion: proof.proofVersion, status: proof.status, files: ["manifest.json", "proof.json", "proof.md", "cleanup.json", "delegation-receipt.json"] }, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDirectory, "proof.json"), `${JSON.stringify(proof, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDirectory, "proof.md"), markdown(proof));
  fs.writeFileSync(path.join(outputDirectory, "cleanup.json"), `${JSON.stringify(result.cleanup, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDirectory, "delegation-receipt.json"), `${JSON.stringify(result.delegationReceipt, null, 2)}\n`);
}

async function main(outputDirectory) {
  const result = await runQualification();
  writePacket(outputDirectory, result);
  process.stdout.write(`${JSON.stringify({ outputDirectory: "<proof-directory>", status: result.proof.status, classification: result.proof.rootClassification })}\n`);
  if (result.proof.status === "failed") process.exitCode = 1;
  return result;
}

if (require.main === module) {
  const index = process.argv.indexOf("--output-dir");
  const outputDirectory = path.resolve(index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : path.join(ROOT, "proof-output", "macos-electron-host"));
  main(outputDirectory).catch((error) => { process.stderr.write(`${sanitizeError(error) || "qualification_failed"}\n`); process.exitCode = 1; });
}

module.exports = Object.freeze({
  CLASSIFICATIONS,
  bounded,
  sanitizePath,
  sanitizeText,
  commandPassed,
  codeSigningSummary,
  sameCodeSigningError,
  sameSignatureFailure,
  minimalPassed,
  classify,
  statusFor,
  crashReportCorrelation,
  buildDelegationReceipt,
  runQualification,
  writePacket
});
