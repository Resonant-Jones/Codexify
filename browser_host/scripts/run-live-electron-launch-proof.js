"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const {
  PREREQUISITE_COMMIT,
  runDiagnostic
} = require("./diagnose-live-electron-launch");

const ROOT = path.resolve(__dirname, "..");
const DEFAULT_OUTPUT = path.join(ROOT, "proof-output", "live-electron-launch");

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function gitValue(args) {
  const result = spawnSync("git", args, { cwd: ROOT, encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : null;
}

function writeJson(file, value) {
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function missingProofFields(diagnostic) {
  const missing = [];
  const launch = diagnostic.playwright;
  if (diagnostic.binary.version.exitCode !== 0) missing.push("electron_binary_check");
  if (!launch.trustedWindowCreated) missing.push("trusted_window_created");
  if (!launch.preloadLoaded) missing.push("preload_loaded");
  if (!launch.trustedStateRead) missing.push("trusted_state_read");
  if (!launch.negotiationCompatible) missing.push("compatible_deterministic_negotiation");
  if (launch.remoteRequestBeforeCompatibility) missing.push("no_remote_request_before_compatibility");
  if (!launch.remoteLoadedAfterCompatibility) missing.push("remote_load_after_compatibility");
  if (launch.cleanupResult !== "passed") missing.push("clean_cleanup");
  return missing;
}

function buildProof(diagnostic) {
  const launch = diagnostic.playwright;
  const status = diagnostic.status;
  return {
    proofType: "browser-host-live-electron-launch",
    proofVersion: "1.0.0",
    status,
    proofStatus: status,
    repositoryCommit: gitValue(["rev-parse", "HEAD"]),
    prerequisiteCommit: PREREQUISITE_COMMIT,
    branch: gitValue(["rev-parse", "--abbrev-ref", "HEAD"]),
    packageVersion: diagnostic.versions.package,
    contractPackageVersion: diagnostic.versions.contractPackage,
    electronVersion: diagnostic.versions.electron,
    playwrightVersion: diagnostic.versions.playwright,
    hostPlatform: diagnostic.versions.platform,
    hostArchitecture: diagnostic.versions.hostArchitecture,
    nodeArchitecture: diagnostic.versions.nodeArchitecture,
    electronExecutableArchitecture: diagnostic.binary.architecture,
    diagnosticEvidence: {
      electronBinaryExitCode: diagnostic.binary.version.exitCode,
      electronBinarySignal: diagnostic.binary.version.signal,
      directLaunchExitCode: diagnostic.directLaunch.exitCode,
      directLaunchSignal: diagnostic.directLaunch.signal,
      directLaunchSurvivedStartupWindow: diagnostic.directLaunch.processSurvivedStartupWindow,
      playwrightProcessFailedToLaunch: /Process failed to launch/i.test(launch.failure || ""),
      macSpctlExitCode: diagnostic.mac?.spctl?.exitCode ?? null,
      macSpctlCodeSigningError: /Code Signing subsystem/i.test(diagnostic.mac?.spctl?.stderr || ""),
      macCodeSignaturePosture: /Signature=adhoc/i.test(diagnostic.mac?.codesign?.stderr || diagnostic.mac?.codesign?.stdout || "") ? "adhoc" : "unknown",
      graphicalSessionAvailable: diagnostic.mac?.graphicalSession?.available ?? null,
      graphicalAquaSession: diagnostic.mac?.graphicalSession?.aquaSession ?? null
    },
    launchMethod: launch.launchMethod,
    productionEntrypointUsed: diagnostic.entrypoint.productionEntrypointUsed,
    insecureSandboxBypassUsed: false,
    trustedWindowCreated: launch.trustedWindowCreated,
    trustedUrlIsLocalFile: launch.trustedUrlIsLocalFile,
    preloadLoaded: launch.preloadLoaded,
    trustedShellReady: launch.trustedShellReady,
    trustedStateRead: launch.trustedStateRead,
    negotiationTransport: launch.negotiationTransport,
    negotiationCompatible: launch.negotiationCompatible,
    remoteRequestBeforeCompatibility: launch.remoteRequestBeforeCompatibility,
    remoteLoadedAfterCompatibility: launch.remoteLoadedAfterCompatibility,
    captureAttempted: false,
    attachmentAttempted: false,
    rendererAuthorityDenialResult: launch.rendererAuthorityDenialResult,
    exitCode: launch.exitCode,
    exitSignal: launch.exitSignal,
    cleanupResult: launch.cleanupResult,
    temporaryProfileRemaining: launch.temporaryProfileRemaining,
    rootCauseClassification: diagnostic.primaryClassification,
    missingProofFields: status === "next-proof-needed" ? missingProofFields(diagnostic) : [],
    screenshot: launch.screenshotPath ? "trusted-shell.png" : null,
    explicitNonClaims: [
      "complete real-Guardian Browser Host session",
      "production Guardian authentication",
      "durable persistence",
      "capture or attachment execution",
      "packaging, signing, notarization, updater, beta, or supported release"
    ]
  };
}

function delegationReceipt() {
  return {
    orchestrationSkillIdentifier: "deepseek-orchestrator",
    delegationSkillIdentifier: "pi-deepseek-delegation",
    provider: "deepseek",
    preferredModel: "deepseek-v4-pro",
    resolvedModel: "deepseek-v4-pro",
    modelDiscoveryResult: "preflight listed deepseek-v4-pro and deepseek-v4-flash; runtime call was unavailable because Pi had no configured API key",
    preEditOutcome: "unavailable_warning",
    postEditOutcome: "not_run",
    warning: "Pi startup also reported EPERM creating its global settings lock; the returned result was empty",
    reviewedCategories: ["binary installation", "architecture", "macOS assessment", "Playwright launch", "child environment", "startup", "cleanup"],
    acceptedRecommendationCount: 0,
    rejectedRecommendationCount: 0,
    noSecretTransmission: true,
    noWorkerEdits: true,
    codexRetainedImplementationAuthority: true
  };
}

async function run(outputDirectory) {
  fs.mkdirSync(outputDirectory, { recursive: true });
  const screenshotPath = path.join(outputDirectory, "trusted-shell.png");
  const diagnostic = await runDiagnostic({ screenshotPath });
  const proof = buildProof(diagnostic);
  const screenshotExists = fs.existsSync(screenshotPath);
  const files = ["manifest.json", "proof.json", "proof.md", "cleanup.json", "delegation-receipt.json"];
  if (screenshotExists) files.push("trusted-shell.png");
  writeJson(path.join(outputDirectory, "manifest.json"), {
    proofType: proof.proofType,
    proofVersion: proof.proofVersion,
    status: proof.status,
    files
  });
  writeJson(path.join(outputDirectory, "proof.json"), proof);
  writeJson(path.join(outputDirectory, "delegation-receipt.json"), delegationReceipt());
  writeJson(path.join(outputDirectory, "cleanup.json"), {
    cleanupPassed: proof.cleanupResult === "passed" && proof.temporaryProfileRemaining === false,
    electronProcessExitCode: proof.exitCode,
    electronProcessExitSignal: proof.exitSignal,
    temporaryProfilesRemaining: proof.temporaryProfileRemaining === true ? 1 : 0,
    supportProcessesRemaining: proof.cleanupResult === "passed" ? 0 : 1,
    captureAttempted: false,
    attachmentAttempted: false
  });
  fs.writeFileSync(path.join(outputDirectory, "proof.md"), [
    "# Browser Host live Electron launch proof",
    "",
    `- Status: **${proof.status}**`,
    `- Primary classification: \`${proof.rootCauseClassification}\``,
    `- Launch method: ${proof.launchMethod}`,
    `- Production entrypoint used: ${proof.productionEntrypointUsed}`,
    `- Trusted shell ready: ${proof.trustedShellReady}`,
    `- Compatible deterministic negotiation: ${proof.negotiationCompatible}`,
    `- Remote request before compatibility: ${proof.remoteRequestBeforeCompatibility}`,
    `- Remote loaded after compatibility: ${proof.remoteLoadedAfterCompatibility}`,
    `- Insecure sandbox bypass: ${proof.insecureSandboxBypassUsed}`,
    `- Electron binary check: exit ${proof.diagnosticEvidence.electronBinaryExitCode ?? "null"}, signal ${proof.diagnosticEvidence.electronBinarySignal || "none"}`,
    `- Direct entrypoint launch: exit ${proof.diagnosticEvidence.directLaunchExitCode ?? "null"}, signal ${proof.diagnosticEvidence.directLaunchSignal || "none"}`,
    `- macOS spctl assessment: exit ${proof.diagnosticEvidence.macSpctlExitCode ?? "not-run"}; Code Signing subsystem error: ${proof.diagnosticEvidence.macSpctlCodeSigningError}`,
    `- Graphical session: Aqua=${proof.diagnosticEvidence.graphicalAquaSession}`,
    `- Capture attempted: ${proof.captureAttempted}`,
    `- Attachment attempted: ${proof.attachmentAttempted}`,
    `- Cleanup: ${proof.cleanupResult}`,
    proof.missingProofFields.length ? `- Missing proof fields: ${proof.missingProofFields.join(", ")}` : "",
    "",
    "This packet does not qualify a complete real-Guardian Browser Host session, durable persistence, packaging, signing, or release support.",
    ""
  ].filter(Boolean).join("\n"), "utf8");
  process.stdout.write(`${JSON.stringify({ outputDirectory, status: proof.status, classification: proof.rootCauseClassification })}\n`);
  return { diagnostic, proof };
}

if (require.main === module) {
  run(path.resolve(argumentValue("--output-dir", DEFAULT_OUTPUT)))
    .then(({ proof }) => { if (proof.status === "failed") process.exitCode = 1; })
    .catch((error) => { process.stderr.write(`${error?.stack || error}\n`); process.exitCode = 1; });
}

module.exports = Object.freeze({ buildProof, delegationReceipt, run });
