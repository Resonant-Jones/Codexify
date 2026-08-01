"use strict";

const fs = require("node:fs");
const path = require("node:path");
const contracts = require("../contracts");

const proofPath = path.resolve(process.argv.includes("--proof") ? process.argv[process.argv.indexOf("--proof") + 1] : path.join(__dirname, "..", "capture-proof-output", "proof.json"));
const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
const requiredScenarios = ["selected-preview-and-attachment", "visible-preview-redaction-and-stale-rejection", "cancelled-ticket-rejection", "attachment-failure-continuity"];
if (proof.proofKind !== "capture_preview_attachment") throw new Error("proof_kind_invalid");
if (proof.proofStatus !== "passed") throw new Error("proof_status_invalid");
if (!proof.featureClaims.captureImplemented || !proof.featureClaims.attachmentImplemented) throw new Error("capture_claim_missing");
if (proof.featureClaims.persistenceImplemented || proof.featureClaims.liveGuardianImplemented || proof.featureClaims.releaseQualified) throw new Error("forbidden_claim");
if (proof.rawPageContentRetained !== false || proof.temporaryTokenRetained !== false) throw new Error("redaction_claim_invalid");
if (proof.topology.remoteViewHasPreload !== false || proof.topology.remoteSessionPersistent !== false) throw new Error("topology_claim_invalid");
for (const name of requiredScenarios) if (proof.scenarios[name]?.status !== "passed") throw new Error(`scenario_invalid:${name}`);
for (const scenario of Object.values(proof.scenarios)) {
  if (Object.prototype.hasOwnProperty.call(scenario, "content") || Object.prototype.hasOwnProperty.call(scenario, "envelope") || Object.prototype.hasOwnProperty.call(scenario, "attachment")) throw new Error("raw_wire_object_in_proof");
  if (JSON.stringify(scenario).match(/CODEXIFY-SYNTHETIC-[A-Za-z0-9_-]{16,}/)) throw new Error("proof_token_leak");
}
if (proof.cleanup.status !== "passed" || proof.cleanup.temporaryTokenRetained !== false) throw new Error("cleanup_invalid");
if (!contracts.tokens.errorCodes.includes("stale_document_generation")) throw new Error("contract_registry_unavailable");
process.stdout.write(JSON.stringify({ valid: true, proofPath }) + "\n");
