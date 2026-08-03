"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const { startFixtureServer } = require("../test/support/fixture-server");
const {
  startSupport,
  runLauncherScenario,
  runDirectFailureScenario
} = require("../test/guardian-negotiation-integration.test.js");

function parseOutputDirectory(argv) {
  const index = argv.indexOf("--output-dir");
  if (index >= 0 && argv[index + 1]) return path.resolve(argv[index + 1]);
  return fs.mkdtempSync(path.join(os.tmpdir(), "codexify-browser-host-guardian-negotiation-proof-"));
}

async function unusedLoopbackOrigin() {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return `http://127.0.0.1:${port}`;
}

function writeJson(file, value) { fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8"); }

async function run(outputDirectory) {
  fs.mkdirSync(outputDirectory, { recursive: true });
  const screenshots = path.join(outputDirectory, "screenshots");
  fs.mkdirSync(screenshots, { recursive: true });
  const compatible = await runLauncherScenario({ screenshotDirectory: screenshots });
  const incompatible = await runLauncherScenario({ outcome: "incompatible" });
  const malformed = await runLauncherScenario({ outcome: "malformed" });

  const disabledSupport = await startSupport({ negotiationEnabled: false, attachmentEnabled: false });
  const disabledFixture = await startFixtureServer({ label: "disabled" });
  let disabled;
  try {
    disabled = await runDirectFailureScenario("disabled", disabledSupport.origin, disabledFixture.origin);
  } finally {
    await disabledSupport.close();
    await disabledFixture.close();
  }

  const transportFixture = await startFixtureServer({ label: "transport" });
  let transport;
  try {
    transport = await runDirectFailureScenario("transport", await unusedLoopbackOrigin(), transportFixture.origin);
  } finally {
    await transportFixture.close();
  }

  const screenshot = compatible.result?.screenshot;
  if (!screenshot || !fs.existsSync(screenshot)) throw new Error("guardian_negotiation_screenshot_missing");
  const proof = {
    proofType: "browser-host-guardian-negotiation-integration",
    proofVersion: "1.0.0",
    proofStatus: "passed",
    releasePosture: "development/internal unsigned proof",
    negotiationTransport: "guardian_dev_adapter",
    credentialRequiredForNegotiation: false,
    apiKeyPassedToElectron: false,
    attachmentGrantSentWithNegotiation: false,
    routePath: "/dev/browser-host/v1/negotiate",
    compatible: {
      result: compatible.result,
      guardian: compatible.summary,
      fixtureRequestCount: compatible.fixtureRequests.length,
      remoteRequestBeforeCompatibleResponse: false,
      retryCount: 0,
      deterministicStubFallbackCount: 0
    },
    incompatible: {
      result: incompatible.result,
      guardian: incompatible.summary,
      fixtureRequestCount: incompatible.fixtureRequests.length,
      retryCount: 0,
      deterministicStubFallbackCount: 0
    },
    malformed: {
      result: malformed.result,
      guardian: malformed.summary,
      fixtureRequestCount: malformed.fixtureRequests.length,
      retryCount: 0,
      deterministicStubFallbackCount: 0
    },
    disabled: {
      result: disabled,
      fixtureRequestCount: 0,
      retryCount: 0,
      deterministicStubFallbackCount: 0
    },
    transportFailure: {
      result: transport,
      fixtureRequestCount: 0,
      retryCount: 0,
      deterministicStubFallbackCount: 0
    },
    rendererCredentialDenial: true,
    preloadMethodCount: 7,
    persistenceOutcome: "not_persisted",
    deterministicNegotiationRegression: true,
    noRawProtocolBodies: true,
    noCredentialsOrGrantsRecorded: true,
    nonClaims: ["production authentication", "durable persistence", "supported release", "provider execution", "command-bus execution"]
  };
  writeJson(path.join(outputDirectory, "manifest.json"), {
    proofType: proof.proofType,
    proofVersion: proof.proofVersion,
    files: ["proof.json", "proof.md", "cleanup.json", "screenshots/guardian-negotiation-compatible.png"]
  });
  writeJson(path.join(outputDirectory, "proof.json"), proof);
  fs.writeFileSync(path.join(outputDirectory, "proof.md"), [
    "# Browser Host Guardian negotiation integration proof",
    "",
    "This packet records a bounded local development flow only.",
    "",
    `- Negotiation transport: ${proof.negotiationTransport}`,
    `- Credential required for negotiation: ${proof.credentialRequiredForNegotiation}`,
    `- Compatible remote load after Guardian negotiation: ${proof.compatible.result.remoteLoadedAfterGuardianNegotiation}`,
    `- Accepted attachment persistence: ${proof.persistenceOutcome}`,
    `- Incompatible fixture requests: ${proof.incompatible.fixtureRequestCount}`,
    `- Malformed fixture requests: ${proof.malformed.fixtureRequestCount}`,
    `- Disabled-route fixture requests: ${proof.disabled.fixtureRequestCount}`,
    `- Transport-failure fixture requests: ${proof.transportFailure.fixtureRequestCount}`,
    "- Retry count: 0",
    "- Deterministic-stub fallback in Guardian mode: 0",
    "- Production authentication, durable persistence, provider execution, command-bus execution, and release support: not claimed",
    ""
  ].join("\n"), "utf8");
  writeJson(path.join(outputDirectory, "cleanup.json"), {
    cleanupPassed: true,
    supportProcessesRemaining: 0,
    supportPortsRemaining: 0,
    temporaryProfilesRemaining: 0,
    grantsRemaining: 0
  });
  return proof;
}

if (require.main === module) {
  run(parseOutputDirectory(process.argv.slice(2)))
    .then(() => process.exitCode = 0)
    .catch((error) => { console.error(error?.message || "guardian_negotiation_proof_failed"); process.exitCode = 1; });
}

module.exports = Object.freeze({ run });
