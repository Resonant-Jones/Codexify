"use strict";

const fs = require("node:fs");
const path = require("node:path");
const contractPackage = require("../contracts");

function fail(message) { throw new Error(`proof_invalid:${message}`); }
function requireValue(condition, message) { if (!condition) fail(message); }

const index = process.argv.indexOf("--proof");
if (index < 0 || !process.argv[index + 1]) fail("proof_path_required");
const proofPath = path.resolve(process.argv[index + 1]);
const directory = path.dirname(proofPath);
const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
const manifest = JSON.parse(fs.readFileSync(path.join(directory, "manifest.json"), "utf8"));
const cleanup = JSON.parse(fs.readFileSync(path.join(directory, "cleanup.json"), "utf8"));

requireValue(proof.proofKind === "browser_host_guardian_attachment_integration", "proof_kind");
requireValue(proof.proofStatus === "passed", "proof_status");
requireValue(manifest.proofStatus === "passed" && manifest.sanitized === true, "manifest_status");
requireValue(cleanup.proofStatus === "passed" && cleanup.rawSecretsRetained === false, "cleanup_status");
requireValue(proof.versions.browserHostPackage === "0.1.0", "browser_host_version");
requireValue(proof.versions.contractPackage === "0.2.0", "contract_package_version");
requireValue(proof.versions.protocol === contractPackage.contractMetadata.protocolVersion, "protocol_version");
requireValue(proof.versions.envelope === contractPackage.contractMetadata.envelopeVersion, "envelope_version");
requireValue(proof.versions.attachment === contractPackage.contractMetadata.attachmentVersion, "attachment_version");
requireValue(proof.versions.electron === "43.2.0", "electron_version");
requireValue(proof.versions.playwright === "1.62.1", "playwright_version");
requireValue(proof.guardianFeatureGates.developmentMode === true, "development_gate");
requireValue(proof.guardianFeatureGates.attachmentAdapterEnabled === true, "adapter_gate");
requireValue(proof.guardianFeatureGates.exposureMode === "local_safe", "exposure_gate");
requireValue(proof.attachmentTransport === "guardian_dev_adapter", "transport");
requireValue(proof.guardianAttachmentOriginClassification === "numeric_loopback_http", "origin_classification");
requireValue(proof.grantAuthorizationScheme === "browser_host_attachment_grant", "grant_scheme");
requireValue(proof.grantPassedToElectron === true, "grant_delivery");
requireValue(proof.reusableGuardianCredentialPassedToElectron === false, "credential_delivery");
requireValue(proof.apiKeyPresentInElectronEnvironment === false, "api_key_redaction");
requireValue(proof.sessionOrJwtPresentInElectronEnvironment === false, "session_redaction");
requireValue(proof.grantPresentInMainEnvironmentAfterConfig === false, "grant_process_redaction");
requireValue(proof.grantPresentInTrustedShellState === false, "trusted_state_redaction");
requireValue(proof.grantPresentInRemoteRenderer === false, "remote_renderer_redaction");
requireValue(proof.previewBeforeAttachment === true && proof.separateAttachmentAction === true, "capture_attachment_separation");
requireValue(proof.exactAcceptedRequestCount === 1 && proof.acceptedHttpStatus === 202, "accepted_request");
requireValue(proof.attachmentOutcome === "accepted" && proof.persistenceOutcome === "not_persisted", "accepted_receipt");
requireValue(proof.grantAvailableAfterRequest === false && proof.grantConsumedAfterRequest === true, "grant_exhaustion");
requireValue(proof.secondAttemptLocalRejection === true && proof.secondAttemptNetworkRequestCount === 0, "replay_rejection");
requireValue(proof.wrongInstanceStatus === 403, "wrong_instance");
requireValue(proof.expiredGrantStatus === 409, "expired_grant");
requireValue(proof.disabledAdapterStatus === 404, "disabled_adapter");
requireValue(proof.transportFailureStatus === null, "transport_failure");
requireValue(proof.retryCount === 0 && proof.guardianAdapterStubFallbackCount === 0, "retry_fallback");
requireValue(proof.deterministicStubRegression === true, "stub_regression");
requireValue(proof.noDurablePersistence === true && proof.redactionPassed === true, "redaction_persistence");
requireValue(proof.cleanupPassed === true, "cleanup");
for (const artifact of manifest.artifacts) requireValue(fs.existsSync(path.join(directory, artifact)), `missing_artifact:${artifact}`);
for (const value of Object.values(manifest)) {
  if (typeof value === "string") requireValue(!/GUARDIAN_API_KEY=|BrowserHostAttachmentGrant |SYNTHETIC_NON_SECRET_TEST_BEARER_/.test(value), "manifest_secret");
}

process.stdout.write(JSON.stringify({ valid: true, proofPath }) + "\n");
