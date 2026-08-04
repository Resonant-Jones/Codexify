"use strict";

const fs = require("node:fs");
const path = require("node:path");
const packageManifest = require("../package.json");
const contracts = require("../contracts");

const proofArg = process.argv.indexOf("--proof");
const proofPath = path.resolve(proofArg >= 0 ? process.argv[proofArg + 1] : path.join(__dirname, "..", "proof-output", "proof.json"));
const proofDir = path.dirname(proofPath);
const proof = JSON.parse(fs.readFileSync(proofPath, "utf8"));
const manifest = JSON.parse(fs.readFileSync(path.join(proofDir, "manifest.json"), "utf8"));
const cleanup = JSON.parse(fs.readFileSync(path.join(proofDir, "cleanup.json"), "utf8"));

function fail(message) { throw new Error(`proof_invalid:${message}`); }
function requireValue(condition, message) { if (!condition) fail(message); }

requireValue(manifest.proofFile === "proof.json", "manifest_proof_file");
requireValue(proof.proofKind === "production_one_tab_skeleton", "proof_kind");
requireValue(proof.proofStatus === "passed", "proof_status");
requireValue(proof.packageVersion === packageManifest.version, "package_version");
requireValue(proof.contractPackageVersion === contracts.contractMetadata.packageVersion, "contract_version");
requireValue(proof.protocolVersion === contracts.contractMetadata.protocolVersion, "protocol_version");
requireValue(proof.envelopeVersion === contracts.contractMetadata.envelopeVersion, "envelope_version");
requireValue(proof.attachmentVersion === contracts.contractMetadata.attachmentVersion, "attachment_version");
requireValue(proof.releasePosture === "development/internal unsigned proof", "release_posture");
requireValue(proof.topology.trustedBrowserWindowCount === 1, "trusted_window_count");
requireValue(proof.topology.remoteWebContentsViewCount === 1, "remote_view_count");
requireValue(proof.topology.remoteViewHasPreload === false, "remote_preload");
requireValue(proof.topology.remoteSessionPersistent === false, "persistent_session");
for (const [key, value] of Object.entries(proof.featureClaims)) requireValue(value === (key === "topologySkeletonImplemented"), `feature_claim:${key}`);
for (const scenario of ["compatible", "denials", "incompatible", "malformed", "renderer-degradation"]) requireValue(proof.scenarios[scenario]?.status === "passed", `scenario:${scenario}`);
requireValue(proof.remoteLoadOrder.negotiationBeforeRemoteLoad === true, "negotiation_order");
requireValue(proof.remoteLoadOrder.incompatibleRemoteRequests === 0, "incompatible_remote_requests");
requireValue(proof.remoteLoadOrder.malformedRemoteRequests === 0, "malformed_remote_requests");
for (const [key, value] of Object.entries(proof.forbiddenAuthority)) requireValue(value === false, `authority:${key}`);
requireValue(cleanup.status === "passed", "cleanup_status");
requireValue(cleanup.temporaryTokenRetained === false, "token_retained");
for (const screenshot of new Set(proof.screenshots)) requireValue(fs.existsSync(path.join(proofDir, "screenshots", screenshot)), `screenshot:${screenshot}`);

function inspectObject(value, pathName = "proof") {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    requireValue(!["proofToken", "authorizationHeader", "credentialValue", "cookieValue", "pageBody", "capturedContent", "environmentDump"].includes(key), `forbidden_field:${pathName}.${key}`);
    inspectObject(child, `${pathName}.${key}`);
  }
}
inspectObject(proof);
inspectObject(manifest, "manifest");
inspectObject(cleanup, "cleanup");
const serialized = fs.readFileSync(proofPath, "utf8") + fs.readFileSync(path.join(proofDir, "proof.md"), "utf8");
requireValue(!serialized.includes("CODEXIFY-SYNTHETIC-"), "token_leak");
requireValue(!serialized.includes("live production Guardian"), "release_claim");
process.stdout.write("one-tab proof validation PASSED\n");
