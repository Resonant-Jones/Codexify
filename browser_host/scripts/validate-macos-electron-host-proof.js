"use strict";

const fs = require("node:fs");
const path = require("node:path");
const packageManifest = require("../package.json");
const contractManifest = require("../contracts/package.json");
const { CLASSIFICATIONS, minimalPassed, sameCodeSigningError, sameSignatureFailure } = require("./qualify-macos-electron-host");

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function fail(message) { throw new Error(`proof_invalid:${message}`); }
function requireValue(condition, message) { if (!condition) fail(message); }

const SENSITIVE_KEYS = /^(?:apiKey|apiKeys|secret|password|cookie|cookies|jwt|authorization|authorizationHeader|bearer|grant|grantBearer|credential|credentialValue|proofToken|pageBody|rawProtocolBody|environmentDump|environment|env|openDocuments|unrelatedProcesses|fullImages|uuid|incidentIdentifier)$/i;
const SENSITIVE_TEXT = [
  /\/Users\/[^/\s]+/i,
  /\/home\/[^/\s]+/i,
  /(?:HOME|USER|USERNAME|GUARDIAN_API_KEY|AUTHORIZATION|BEARER|COOKIE|PASSWORD|SECRET|CREDENTIAL)\s*[=:]/i,
  /(?:Authorization|Proxy-Authorization):\s*\S+/i,
  /\bBearer\s+[A-Za-z0-9._~+/=-]{8,}/i,
  /CODEXIFY-SYNTHETIC-[A-Za-z0-9_-]{16,128}/,
  /(?:Incident Identifier|Thread \d+ Crashed|Binary Images|DiagnosticReports)/i
];

function inspectObject(value, location = "proof") {
  if (value === null || value === undefined) return;
  if (typeof value === "string") {
    for (const pattern of SENSITIVE_TEXT) requireValue(!pattern.test(value), `sensitive_text:${location}`);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((child, index) => inspectObject(child, `${location}[${index}]`));
    return;
  }
  if (typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    requireValue(!SENSITIVE_KEYS.test(key), `sensitive_field:${location}.${key}`);
    inspectObject(child, `${location}.${key}`);
  }
}

function signatureFailed(bundle) {
  return Boolean(bundle && (!bundle.codesign?.verificationPassed || !bundle.gatekeeper?.passed));
}

function matrixClassMatches(proof) {
  const apple = proof.appleControl;
  const current = proof.currentElectron;
  const clean = proof.cleanElectron;
  const reinstall = proof.reinstall;
  const live = proof.liveProofRerun;
  const classification = proof.rootClassification;
  switch (classification) {
    case "host_code_signing_subsystem_unavailable":
      return sameCodeSigningError(apple, current, clean) && proof.status !== "passed";
    case "repository_electron_bundle_corrupt":
      return apple.passed === true && signatureFailed(current.bundle) && !signatureFailed(clean.bundle) && minimalPassed(clean.minimal) && reinstall.attempted === false;
    case "isolated_electron_distribution_invalid":
      return apple.passed === true && sameSignatureFailure(current, clean);
    case "host_gatekeeper_assessment_failure":
      return apple.passed === true && (current.bundle.gatekeeper.passed === false || clean.bundle.gatekeeper.passed === false) && !sameCodeSigningError(apple, current, clean);
    case "minimal_electron_launch_failure_unrelated_to_codexify":
      return !minimalPassed(current.minimal) && !minimalPassed(clean.minimal);
    case "codexify_entrypoint_launch_failure":
      return minimalPassed(current.minimal) && minimalPassed(clean.minimal) && live.artifactCreated === true && live.status !== "passed";
    case "dependency_redownload_blocked":
      return clean.install.passed === false;
    case "repaired_repository_dependency_install":
      return reinstall.attempted === true && reinstall.result === "repaired" && proof.packageLockChanged === false && live.status === "passed";
    case "qualified_host_ready":
      return minimalPassed(current.minimal) && minimalPassed(clean.minimal) && live.status === "passed";
    case "unknown_next_proof_needed":
      return proof.status === "next-proof-needed";
    default:
      return false;
  }
}

function validate(proofDirectory) {
  const files = ["manifest.json", "proof.json", "proof.md", "cleanup.json", "delegation-receipt.json"];
  for (const file of files) requireValue(fs.existsSync(path.join(proofDirectory, file)), `missing_file:${file}`);
  let manifest;
  let proof;
  let cleanup;
  let receipt;
  try {
    manifest = JSON.parse(fs.readFileSync(path.join(proofDirectory, "manifest.json"), "utf8"));
    proof = JSON.parse(fs.readFileSync(path.join(proofDirectory, "proof.json"), "utf8"));
    cleanup = JSON.parse(fs.readFileSync(path.join(proofDirectory, "cleanup.json"), "utf8"));
    receipt = JSON.parse(fs.readFileSync(path.join(proofDirectory, "delegation-receipt.json"), "utf8"));
  } catch (error) {
    fail(`invalid_json:${error.message}`);
  }
  requireValue(manifest.proofType === "browser-host-macos-electron-host-qualification", "manifest_type");
  requireValue(manifest.proofVersion === "1.0.0", "manifest_version");
  requireValue(proof.proofType === manifest.proofType, "proof_type");
  requireValue(["passed", "next-proof-needed", "failed"].includes(proof.status), "status");
  requireValue(proof.proofStatus === proof.status, "status_alias");
  requireValue(CLASSIFICATIONS.includes(proof.rootClassification), "root_classification");
  requireValue(proof.packageVersion === packageManifest.version, "package_version");
  requireValue(proof.contractPackageVersion === contractManifest.version, "contract_version");
  requireValue(proof.host?.platform === "darwin", "host_platform");
  requireValue(Array.isArray(proof.prerequisiteCommits) && proof.prerequisiteCommits.includes("de3924011") && proof.prerequisiteCommits.includes("529cc38b1"), "prerequisite_commits");
  requireValue(proof.packageLockChanged === false, "package_lock_changed");
  requireValue(proof.systemSecurityModified === false, "system_security_modified");
  requireValue(proof.insecureFlagsUsed === false, "insecure_flags_used");
  requireValue(proof.appleControl && proof.currentElectron && proof.cleanElectron, "matrix_fields");
  requireValue(proof.reinstall && proof.liveProofRerun && proof.cleanupResult, "result_fields");
  requireValue(cleanup.cleanupPassed === true && cleanup.temporaryRootRemaining === false && cleanup.supportProcessesRemaining === 0, "cleanup");
  requireValue(proof.cleanupResult.cleanupPassed === true, "proof_cleanup");
  requireValue(receipt.orchestrationSkillIdentifier === "deepseek-orchestrator", "delegation_orchestration");
  requireValue(receipt.delegationSkillIdentifier === "pi-deepseek-delegation", "delegation_skill");
  requireValue(receipt.provider === "deepseek", "delegation_provider");
  requireValue(receipt.preferredModel === "deepseek-v4-pro", "delegation_preferred_model");
  requireValue(receipt.noSecretTransmission === true && receipt.noCrashDataTransmission === true && receipt.noEnvironmentDumpTransmission === true, "delegation_redaction");
  requireValue(receipt.noWorkerEdits === true && receipt.codexRetainedImplementationAuthority === true, "delegation_authority");
  requireValue(matrixClassMatches(proof), "classification_evidence");
  if (proof.status === "passed") {
    requireValue(["qualified_host_ready", "repaired_repository_dependency_install"].includes(proof.rootClassification), "passed_classification");
    requireValue(proof.liveProofRerun.status === "passed", "passed_live_proof");
    requireValue(proof.liveProofRerun.insecureSandboxBypassUsed === false, "passed_insecure_flags");
  }
  if (proof.status === "next-proof-needed") requireValue(Array.isArray(proof.explicitNonClaims) && proof.explicitNonClaims.length > 0, "next_proof_non_claims");
  inspectObject(manifest, "manifest");
  inspectObject(proof, "proof");
  inspectObject(cleanup, "cleanup");
  inspectObject(receipt, "delegationReceipt");
  return { status: proof.status, rootClassification: proof.rootClassification };
}

if (require.main === module) {
  try {
    const result = validate(path.resolve(argumentValue("--proof-dir", path.join(__dirname, "..", "proof-output", "macos-electron-host"))));
    process.stdout.write(`macOS Electron host qualification validation PASSED (${result.status}; ${result.rootClassification})\n`);
  } catch (error) {
    process.stderr.write(`${error.message || error}\n`);
    process.exitCode = 1;
  }
}

module.exports = Object.freeze({ validate, inspectObject, matrixClassMatches });
