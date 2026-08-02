"use strict";

const fs = require("node:fs");
const path = require("node:path");

function argument(argv, name) {
  const index = argv.indexOf(name);
  if (index < 0 || !argv[index + 1]) throw new Error(`${name}_required`);
  return path.resolve(argv[index + 1]);
}

function assert(condition, message) { if (!condition) throw new Error(message); }

function validate(proofPath) {
  const directory = path.dirname(proofPath);
  const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
  const manifest = JSON.parse(fs.readFileSync(path.join(directory, "manifest.json"), "utf8"));
  const cleanup = JSON.parse(fs.readFileSync(path.join(directory, "cleanup.json"), "utf8"));
  assert(proof.proofType === "browser-host-guardian-negotiation-integration", "proof_type_invalid");
  assert(proof.proofVersion === "1.0.0", "proof_version_invalid");
  const files = manifest.files || manifest.artifacts;
  assert(Array.isArray(files) && files.every((file) => fs.existsSync(path.join(directory, file))), "proof_file_missing");
  if (proof.proofStatus === "blocked_environment") {
    assert(proof.negotiationTransport === "guardian_dev_adapter", "guardian_transport_not_explicit");
    assert(proof.liveQualificationClaimed === false, "blocked_packet_claims_live_qualification");
    assert(proof.electronLaunchAttempted === true, "electron_attempt_missing");
    assert(proof.electronLaunchReachedHandshake === false, "electron_boundary_invalid");
    assert(proof.staticChecksPassed === true, "static_checks_missing");
    assert(proof.noCredentialsOrGrantsRecorded === true, "redaction_invariant_failed");
    assert(cleanup.cleanupPassed === true && cleanup.supportProcessesRemaining === 0 && cleanup.supportPortsRemaining === 0, "cleanup_failed");
    assert(!/api[_ -]?key|cookie|jwt|bearer|authorization|grantBearer|raw hello|raw negotiation|environment dump/i.test(fs.readFileSync(path.join(directory, "proof.md"), "utf8")), "forbidden_proof_text");
    return true;
  }
  assert(proof.proofStatus === "passed", "proof_status_invalid");
  assert(proof.negotiationTransport === "guardian_dev_adapter", "guardian_transport_not_explicit");
  assert(proof.credentialRequiredForNegotiation === false, "negotiation_credential_required");
  assert(proof.apiKeyPassedToElectron === false, "api_key_entered_electron");
  assert(proof.attachmentGrantSentWithNegotiation === false, "grant_sent_with_negotiation");
  assert(proof.compatible.result.outcome === "compatible", "compatible_result_invalid");
  assert(proof.compatible.result.remoteLoadedAfterGuardianNegotiation === true, "remote_loaded_before_negotiation");
  assert(proof.compatible.result.attachmentOutcome === "accepted", "attachment_not_accepted");
  assert(proof.compatible.result.persistenceOutcome === "not_persisted", "durable_persistence_claimed");
  for (const scenario of ["incompatible", "malformed", "disabled", "transportFailure"]) {
    assert(proof[scenario].fixtureRequestCount === 0, `${scenario}_loaded_remote_content`);
    assert(proof[scenario].retryCount === 0, `${scenario}_retried`);
    assert(proof[scenario].deterministicStubFallbackCount === 0, `${scenario}_fell_back`);
  }
  assert(proof.compatible.retryCount === 0, "compatible_retried");
  assert(proof.compatible.deterministicStubFallbackCount === 0, "compatible_fell_back");
  assert(proof.rendererCredentialDenial === true, "renderer_credential_denial_missing");
  assert(proof.preloadMethodCount === 7, "preload_allowlist_changed");
  assert(proof.noRawProtocolBodies === true && proof.noCredentialsOrGrantsRecorded === true, "redaction_invariant_failed");
  assert(cleanup.cleanupPassed === true && cleanup.supportProcessesRemaining === 0 && cleanup.supportPortsRemaining === 0, "cleanup_failed");
  assert(!/api[_ -]?key|cookie|jwt|bearer|authorization|grantBearer|raw hello|raw negotiation|environment dump/i.test(fs.readFileSync(path.join(directory, "proof.md"), "utf8")), "forbidden_proof_text");
  return true;
}

if (require.main === module) {
  try { validate(argument(process.argv.slice(2), "--proof")); process.exitCode = 0; }
  catch (error) { console.error(error?.message || "guardian_negotiation_proof_invalid"); process.exitCode = 1; }
}

module.exports = Object.freeze({ validate });
