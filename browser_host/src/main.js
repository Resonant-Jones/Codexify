"use strict";

const path = require("node:path");
const { app, BrowserWindow, WebContentsView, ipcMain, session } = require("electron");
const { loadConfig, unconfiguredConfig, PROOF_TOKEN_ENV } = require("./runtime/config");
const { negotiate, GuardianNegotiationError, attachEnvelope } = require("./runtime/guardian-client");
const {
  negotiate: negotiateWithGuardian,
  GuardianNegotiationClientError
} = require("./runtime/guardian-negotiation-client");
const { createGuardianAttachmentClient } = require("./runtime/guardian-attachment-client");
const { createRuntimeState } = require("./runtime/runtime-state");
const { createTrustedShell } = require("./runtime/trusted-shell");
const { createRemoteTab } = require("./runtime/remote-tab");
const { createCaptureController, clearPendingPreviewState } = require("./runtime/capture");

const ROOT = __dirname;
const PRELOAD_PATH = path.join(ROOT, "preload", "trusted-shell-preload.js");
const SHELL_PATH = path.join(ROOT, "shell", "index.html");

function isTrustedSender(event, trustedId) {
  if (!event?.sender || event.sender.id !== trustedId) throw new Error("trusted_sender_rejected");
  const frameUrl = event.senderFrame?.url;
  if (typeof frameUrl !== "string" || !frameUrl.startsWith("file://")) throw new Error("trusted_frame_rejected");
}
function boundedErrorCode(error) {
  return error instanceof GuardianNegotiationError || error instanceof GuardianNegotiationClientError
    ? error.code
    : "invalid_contract";
}

function createRuntime(electronApi = { app, BrowserWindow, WebContentsView, ipcMain, session }, env = process.env) {
  const { app: electronApp, BrowserWindow: Window, WebContentsView: RemoteView, ipcMain: ipc, session: sessions } = electronApi;
  let config;
  let configurationError = null;
  try { config = loadConfig(env); } catch (error) { configurationError = error; config = unconfiguredConfig("invalid_contract"); }
  if (config.proofMode && env[PROOF_TOKEN_ENV]) {
    try { delete env[PROOF_TOKEN_ENV]; } finally { env[PROOF_TOKEN_ENV] = ""; }
  }
  const runtimeState = createRuntimeState(config);
  let trustedShell = null;
  let remoteTab = null;
  let negotiationStarted = false;
  let shutdownStarted = false;
  let finalQuit = false;
  let cleanupPromise = null;
  let stateUnsubscribe = null;

  function stateSnapshot() { return runtimeState.snapshot(); }
  function sendState(snapshot = stateSnapshot()) { if (trustedShell && !trustedShell.window.isDestroyed()) trustedShell.window.webContents.send("browser-host:state-changed", snapshot); }
  function update(patch) { const snapshot = runtimeState.update(patch); sendState(snapshot); return snapshot; }

  const guardianAttachmentClient = config.guardianAttachmentAdapterEnabled
    ? createGuardianAttachmentClient({
      enabled: true,
      origin: config.guardianAttachmentOrigin,
      instanceId: config.browserHostInstanceId,
      timeoutMs: config.guardianAttachmentTimeoutMs,
      grantHolder: config.guardianAttachmentGrantHolder,
      onGrantClaimed: () => update({
        attachmentGrantAvailable: false,
        attachmentGrantConsumed: true,
        ...clearPendingPreviewState()
      }),
      onHttpStatus: (status) => update({ lastGuardianAttachmentHttpStatus: Number.isInteger(status) ? status : null })
    })
    : null;

  const attachmentTransport = guardianAttachmentClient
    ? (unusedConfig, attachment) => guardianAttachmentClient.attach(attachment)
    : attachEnvelope;

  const captureController = createCaptureController({
    getRemoteTab: () => remoteTab,
    config: () => config,
    isFeatureEnabled: (feature) => runtimeState.snapshot().enabledFeatures.includes(feature),
    update,
    attachEnvelope: attachmentTransport
  });

  function registerIpc() {
    ipc.handle("browser-host:get-state", (event) => { isTrustedSender(event, trustedShell.window.webContents.id); return stateSnapshot(); });
    ipc.handle("browser-host:reload-remote", async (event) => { isTrustedSender(event, trustedShell.window.webContents.id); if (remoteTab) await remoteTab.reload(); return stateSnapshot(); });
    ipc.handle("browser-host:capture-selected-text", async (event) => { isTrustedSender(event, trustedShell.window.webContents.id); return captureController.capture("selected_text"); });
    ipc.handle("browser-host:capture-visible-page", async (event) => { isTrustedSender(event, trustedShell.window.webContents.id); return captureController.capture("visible_page_text"); });
    ipc.handle("browser-host:attach-capture", async (event, ticketId) => { isTrustedSender(event, trustedShell.window.webContents.id); return captureController.attach(ticketId); });
    ipc.handle("browser-host:cancel-capture", (event, ticketId) => { isTrustedSender(event, trustedShell.window.webContents.id); return captureController.cancel(ticketId); });
  }

  async function startNegotiation() {
    if (negotiationStarted || shutdownStarted) return;
    negotiationStarted = true;
    const guardianMode = config.negotiationTransport === "guardian_dev_adapter";
    const negotiationOrigin = guardianMode ? config.guardianNegotiationOrigin : config.guardianOrigin;
    if (configurationError || !negotiationOrigin || !config.fixtureOrigin) { update({ runtimeStatus: "degraded", guardianCompatibilityOutcome: "unavailable", errorCode: "guardian_rejected" }); return; }
    update({ runtimeStatus: "negotiating" });
    try {
      const result = guardianMode
        ? await negotiateWithGuardian(config, { onHttpStatus: (status) => update({ guardianNegotiationHttpStatus: Number.isInteger(status) ? status : null }) })
        : await negotiate(config);
      if (result.response.compatibilityOutcome !== "compatible") {
        const error = new (guardianMode ? GuardianNegotiationClientError : GuardianNegotiationError)(result.response.errorCode || "no_compatible_version", "guardian_incompatible");
        throw error;
      }
      update({ runtimeStatus: "negotiated", guardianCompatibilityOutcome: "compatible", negotiationRequestId: result.hello.requestCorrelationId, selectedVersions: { protocol: result.response.selectedProtocolVersion, envelope: result.response.selectedEnvelopeVersion, attachment: result.response.selectedAttachmentVersion }, enabledFeatures: result.response.enabledFeatures, disabledFeatures: result.response.disabledFeatures, errorCode: null });
      remoteTab = createRemoteTab({ WebContentsView: RemoteView, session: sessions, parentWindow: trustedShell.window, fixtureOrigin: config.fixtureOrigin, initialBounds: trustedShell.bounds(trustedShell.window), onState: (patch) => update(patch) });
      trustedShell.resize();
      await remoteTab.load();
      update({ remoteLoadedAfterGuardianNegotiation: guardianMode });
    } catch (error) {
      if (remoteTab) {
        await remoteTab.destroy();
        remoteTab = null;
      }
      const compatibilityOutcome = ["unsupported_protocol_version", "unsupported_envelope_version", "unsupported_attachment_version", "no_compatible_version", "undeclared_feature"].includes(error.code)
        ? "incompatible"
        : error.code === "guardian_rejected" ? "unavailable" : "malformed";
      update({ runtimeStatus: "degraded", guardianCompatibilityOutcome: compatibilityOutcome, negotiationRequestId: null, errorCode: boundedErrorCode(error), remoteStatus: "not_created", remoteProcessState: "not_started", remoteViewCreated: false, remoteLoadedAfterNegotiation: false });
    }
  }

  async function cleanup() {
    if (cleanupPromise) return cleanupPromise;
    cleanupPromise = (async () => {
      shutdownStarted = true;
      update({ runtimeStatus: "shutting_down" });
      captureController.dispose();
      guardianAttachmentClient?.dispose();
      if (remoteTab) { await remoteTab.destroy(); remoteTab = null; }
      stateUnsubscribe?.();
      stateUnsubscribe = null;
      for (const channel of ["browser-host:get-state", "browser-host:reload-remote", "browser-host:capture-selected-text", "browser-host:capture-visible-page", "browser-host:attach-capture", "browser-host:cancel-capture"]) ipc.removeHandler?.(channel);
      if (trustedShell) trustedShell.destroy();
      trustedShell = null;
      if (config.proofToken) config = Object.freeze({ ...config, proofToken: null });
    })();
    return cleanupPromise;
  }
  function requestQuit() { if (finalQuit) return; cleanup().finally(() => { finalQuit = true; electronApp.exit(0); }); }

  async function start() {
    await electronApp.whenReady();
    registerIpc();
    trustedShell = createTrustedShell({ BrowserWindow: Window, preloadPath: PRELOAD_PATH, shellPath: SHELL_PATH, onDidFinishLoad: startNegotiation, onResize: (bounds) => remoteTab?.setBounds(bounds) });
    stateUnsubscribe = runtimeState.subscribe(sendState);
    trustedShell.window.on("closed", () => { if (!shutdownStarted) requestQuit(); });
    electronApp.on("before-quit", (event) => { if (!finalQuit) { event.preventDefault(); requestQuit(); } });
    electronApp.on("window-all-closed", () => { if (process.platform !== "darwin" && !shutdownStarted) requestQuit(); });
    return trustedShell.window;
  }

  return Object.freeze({ start, cleanup, state: runtimeState, stateSnapshot, getTrustedWindow: () => trustedShell?.window || null, getRemoteTab: () => remoteTab });
}

if (process.type === "browser") createRuntime().start().catch((error) => {
  console.error("browser_host_start_failed", error instanceof Error ? error.message : "unknown_error");
  app.exit(1);
});
module.exports = Object.freeze({ createRuntime, isTrustedSender, boundedErrorCode });
