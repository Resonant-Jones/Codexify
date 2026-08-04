"use strict";

const fs = require("node:fs");
const path = require("node:path");
const packageManifest = require("../package.json");
const contractManifest = require("../contracts/package.json");
const { CLASSIFICATIONS } = require("./diagnose-live-electron-launch");

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function fail(message) { throw new Error(`proof_invalid:${message}`); }
function requireValue(condition, message) { if (!condition) fail(message); }

function inspectObject(value, location = "proof") {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    requireValue(!/^(?:apiKey|apiKeys|secret|password|cookie|cookies|jwt|authorizationHeader|grantBearer|proofToken|pageBody|environmentDump|rawProtocolBody|credentialValue)$/i.test(key), `sensitive_field:${location}.${key}`);
    inspectObject(child, `${location}.${key}`);
  }
}

function validate(proofDirectory) {
  const manifestPath = path.join(proofDirectory, "manifest.json");
  const proofPath = path.join(proofDirectory, "proof.json");
  const cleanupPath = path.join(proofDirectory, "cleanup.json");
  const receiptPath = path.join(proofDirectory, "delegation-receipt.json");
  for (const file of [manifestPath, proofPath, cleanupPath, receiptPath, path.join(proofDirectory, "proof.md")]) {
    requireValue(fs.existsSync(file), `missing_file:${path.basename(file)}`);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
  const cleanup = JSON.parse(fs.readFileSync(cleanupPath, "utf8"));
  const receipt = JSON.parse(fs.readFileSync(receiptPath, "utf8"));
  requireValue(manifest.proofType === "browser-host-live-electron-launch", "manifest_type");
  requireValue(proof.proofType === manifest.proofType, "proof_type");
  requireValue(["passed", "next-proof-needed", "failed"].includes(proof.status), "status");
  requireValue(proof.proofStatus === proof.status, "status_alias");
  requireValue(proof.packageVersion === packageManifest.version, "package_version");
  requireValue(proof.contractPackageVersion === contractManifest.version, "contract_version");
  requireValue(proof.launchMethod === "playwright_electron", "launch_method");
  requireValue(proof.productionEntrypointUsed === true, "production_entrypoint");
  requireValue(proof.insecureSandboxBypassUsed === false, "insecure_sandbox_bypass");
  requireValue(proof.captureAttempted === false, "capture_claim");
  requireValue(proof.attachmentAttempted === false, "attachment_claim");
  requireValue(CLASSIFICATIONS.includes(proof.rootCauseClassification), "root_cause_classification");
  requireValue(Array.isArray(proof.explicitNonClaims) && proof.explicitNonClaims.length > 0, "non_claims");
  requireValue(receipt.noSecretTransmission === true, "delegation_secret_posture");
  requireValue(receipt.noWorkerEdits === true, "delegation_worker_edits");
  inspectObject(proof);
  inspectObject(manifest, "manifest");
  inspectObject(cleanup, "cleanup");
  inspectObject(receipt, "delegationReceipt");

  if (proof.status === "passed") {
    for (const [key, value] of Object.entries({
      trustedWindowCreated: proof.trustedWindowCreated,
      trustedUrlIsLocalFile: proof.trustedUrlIsLocalFile,
      preloadLoaded: proof.preloadLoaded,
      trustedShellReady: proof.trustedShellReady,
      trustedStateRead: proof.trustedStateRead,
      negotiationCompatible: proof.negotiationCompatible,
      noRemoteRequestBeforeCompatibility: proof.remoteRequestBeforeCompatibility === false,
      remoteLoadedAfterCompatibility: proof.remoteLoadedAfterCompatibility,
      cleanExit: proof.exitSignal === null,
      cleanupPassed: cleanup.cleanupPassed === true,
      noTemporaryProfiles: proof.temporaryProfileRemaining === false
    })) requireValue(value === true, `passed_requirement:${key}`);
    requireValue(proof.rendererAuthorityDenialResult && Object.values(proof.rendererAuthorityDenialResult).every((value) => value === false), "renderer_authority_denial");
    requireValue(proof.screenshot === "trusted-shell.png" && fs.existsSync(path.join(proofDirectory, proof.screenshot)), "trusted_shell_screenshot");
    requireValue(proof.missingProofFields.length === 0, "passed_missing_fields");
  }
  if (proof.status === "next-proof-needed") {
    requireValue(Array.isArray(proof.missingProofFields) && proof.missingProofFields.length > 0, "next_proof_missing_fields");
  }
  requireValue(!JSON.stringify({ proof, manifest, cleanup, receipt }).match(/CODEXIFY-SYNTHETIC-[A-Za-z0-9_-]{16,128}/), "synthetic_token_leak");
  return { status: proof.status, rootCauseClassification: proof.rootCauseClassification };
}

if (require.main === module) {
  try {
    const result = validate(path.resolve(argumentValue("--proof-dir", path.join(__dirname, "..", "proof-output", "live-electron-launch"))));
    process.stdout.write(`live Electron launch proof validation PASSED (${result.status}; ${result.rootCauseClassification})\n`);
  } catch (error) {
    process.stderr.write(`${error?.message || error}\n`);
    process.exitCode = 1;
  }
}

module.exports = Object.freeze({ validate });
