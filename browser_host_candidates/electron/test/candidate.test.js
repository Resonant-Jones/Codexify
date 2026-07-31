const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const constants = require("../lib/constants");
const { loadManifest, validateManifest, validatePackage } = require("../lib/manifest");
const {
  parseOrigin,
  isAllowedFixtureUrl,
  isProtectedTarget,
  IPC_CHANNELS,
  assertTrustedSender,
  assertRunId,
  boundedString
} = require("../lib/security");
const { hashContent, truncateUtf8, makeEnvelope, safePreview } = require("../lib/envelope");

test("candidate identity and exact dependency pins are stable", () => {
  const manifest = loadManifest(root);
  assert.equal(manifest.candidateId, "codexify-electron-bundled-chromium-v1");
  assert.equal(manifest.candidateFamily, "bundled_chromium_electron");
  assert.deepEqual(validateManifest(root, manifest), []);
  const packageResult = validatePackage(root);
  assert.deepEqual(packageResult.errors, []);
  assert.equal(packageResult.packageJson.devDependencies.electron, "43.2.0");
  assert.equal(packageResult.packageJson.devDependencies.playwright, "1.62.1");
  assert.equal(packageResult.packageJson.devDependencies["@electron/packager"], "20.0.4");
  assert.ok(fs.existsSync(path.join(root, "package-lock.json")), "candidate lockfile required");
});

test("remote renderer configuration is least privilege by declaration", () => {
  const manifest = loadManifest(root);
  const remote = manifest.rendererConfiguration.remoteRenderer;
  assert.equal(remote.preload, null);
  assert.equal(remote.nodeIntegration, false);
  assert.equal(remote.contextIsolation, true);
  assert.equal(remote.sandbox, true);
  assert.equal(remote.webviewTag, false);
  assert.deepEqual(manifest.ipcTopology.remoteRendererChannels, []);
});

test("trusted IPC surface is fixed and does not expose generic transport", () => {
  const channels = Object.values(IPC_CHANNELS);
  assert.equal(new Set(channels).size, channels.length);
  assert.ok(channels.every((channel) => channel.startsWith("candidate:") || channel.startsWith("capture:")));
  assert.equal(Object.prototype.hasOwnProperty.call(IPC_CHANNELS, "send"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(IPC_CHANNELS, "invoke"), false);
});

test("trusted sender, run, and argument validation fail closed", () => {
  const trustedEvent = { sender: { id: 7 }, senderFrame: { url: "file:///trusted/index.html" } };
  assert.doesNotThrow(() => assertTrustedSender(trustedEvent, 7));
  assert.throws(() => assertTrustedSender({ ...trustedEvent, sender: { id: 8 } }, 7), /trusted_sender_rejected/);
  assert.throws(() => assertTrustedSender({ ...trustedEvent, senderFrame: { url: "http://127.0.0.1:1" } }, 7), /trusted_frame_rejected/);
  assert.doesNotThrow(() => assertRunId({ runId: "run-1" }, "run-1"));
  assert.throws(() => assertRunId({ runId: "run-2" }, "run-1"), /run_id_rejected/);
  assert.throws(() => boundedString("", "url"), /url_invalid/);
});

test("origin parser and navigation allowlist reject public and protected targets", () => {
  assert.equal(parseOrigin("http://127.0.0.1:1234/basic-visible"), "http://127.0.0.1:1234");
  const origins = ["http://127.0.0.1:1234", "http://127.0.0.1:5678"];
  assert.equal(isAllowedFixtureUrl("http://127.0.0.1:1234/basic-visible", origins), true);
  assert.equal(isAllowedFixtureUrl("https://example.com/basic-visible", origins), false);
  assert.equal(isAllowedFixtureUrl("http://127.0.0.1:1234/unknown", origins), false);
  assert.equal(isAllowedFixtureUrl("file:///tmp/fixture.html", origins), false);
  assert.equal(isProtectedTarget("codexify-harness://protected/synthetic"), true);
});

test("capture ticket content is bounded and hashed", () => {
  const source = "x".repeat(constants.MAX_CAPTURE_BYTES + 100);
  const bounded = truncateUtf8(source);
  assert.equal(bounded.truncated, true);
  assert.equal(Buffer.byteLength(bounded.content), constants.MAX_CAPTURE_BYTES);
  assert.equal(hashContent(bounded.content).length, 64);
});

test("envelope authors authority-bearing metadata in the main-process helper", () => {
  const envelope = makeEnvelope({
    runId: "run-1",
    sourceUrl: "http://127.0.0.1:1234/basic-visible",
    sourceTitle: "Basic Visible Page",
    captureMode: "visible_page_text",
    content: "visible evidence",
    captureRequestId: "capture-1",
    requestId: "request-1",
    attemptNumber: 1,
    userInitiated: true
  });
  assert.equal(envelope.sourceOrigin, "http://127.0.0.1:1234");
  assert.equal(envelope.contentHash, hashContent(envelope.content));
  assert.equal(envelope.userInitiated, true);
  assert.equal(envelope.retentionClass, "ephemeral");
  assert.equal(safePreview(envelope).contentPreview, "visible evidence");
  assert.throws(() => makeEnvelope({ ...envelope, userInitiated: false }), /user_initiation_required/);
});

test("candidate source has no production credential lookup", () => {
  const source = ["main.js", "trusted-preload.js", "ui/app.js"]
    .map((file) => fs.readFileSync(path.join(root, file), "utf8"))
    .join("\n");
  assert.equal(source.includes("GUARDIAN_API_KEY"), false);
  assert.equal(source.includes("process.env.GUARDIAN"), false);
  assert.equal(source.includes("ipcRenderer.send"), false);
  assert.equal(source.includes("ipcRenderer.on"), false);
});

test("permission, popup, download, and document lifecycle controls are declared", () => {
  const main = fs.readFileSync(path.join(root, "main.js"), "utf8");
  assert.match(main, /setPermissionRequestHandler/);
  assert.match(main, /setPermissionCheckHandler/);
  assert.match(main, /setWindowOpenHandler/);
  assert.match(main, /will-download/);
  assert.match(main, /preventDefault\(\)/);
  assert.match(main, /documentGeneration/);
  assert.match(main, /ticket/);
  assert.match(main, /expiresAt/);
});

test("proof driver keeps trusted-shell navigation argument order", () => {
  const proof = fs.readFileSync(path.join(root, "proof", "run-proof.js"), "utf8");
  assert.match(proof, /navigate\(trusted, remote, [a-zA-Z]+Url\)/);
  assert.doesNotMatch(proof, /navigate\(trusted, [a-zA-Z]+Url, remote\)/);
});

test("trusted preview is keyboard focusable", () => {
  const html = fs.readFileSync(path.join(root, "ui", "index.html"), "utf8");
  assert.match(html, /id="preview" tabindex="0"/);
});
