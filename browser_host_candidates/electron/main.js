const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {
  app,
  BrowserWindow,
  ipcMain,
  session
} = require("electron");

const constants = require("./lib/constants");
const {
  IPC_CHANNELS,
  MAX_CAPTURE_BYTES,
  EXTRACTOR_VERSION,
  CANDIDATE_ID
} = constants;
const {
  isAllowedFixtureUrl,
  isProtectedTarget,
  boundedString,
  assertTrustedSender,
  assertEmptyArgs,
  assertRunId
} = require("./lib/security");
const { makeEnvelope, safePreview, hashContent } = require("./lib/envelope");

const ROOT = __dirname;
const UI_FILE = path.join(ROOT, "ui", "index.html");
const runtimeManifestPath = process.env.CODEXIFY_BROWSER_HOST_RUNTIME_MANIFEST;
const userDataPath = process.env.CODEXIFY_ELECTRON_USER_DATA_DIR;
if (userDataPath) {
  app.setPath("userData", userDataPath);
  app.setPath("sessionData", path.join(userDataPath, "session-data"));
}

let runtimeManifest;
let guardianCredential;
let trustedWindow;
let remoteWindow;
let remoteSession;
let trustedWebContentsId = null;
let shutdownStarted = false;
let attachmentAttemptNumber = 0;

const state = {
  candidateId: CANDIDATE_ID,
  runId: "unknown",
  phase: "starting",
  remoteReady: false,
  url: "",
  origin: "",
  title: "",
  loading: "starting",
  documentGeneration: 0,
  remoteWebContentsId: null,
  lastPolicyDecision: "",
  lastError: "",
  preview: null,
  pendingCapture: null
};

function safeLog(event, values = {}) {
  const safe = {
    event,
    runId: state.runId,
    candidateId: CANDIDATE_ID,
    status: values.status || "observed"
  };
  for (const key of ["captureRequestId", "contextId", "requestId", "attemptNumber", "origin", "url", "failureCode", "durationMs", "processCount"]) {
    if (values[key] !== undefined) safe[key] = values[key];
  }
  console.log(JSON.stringify(safe));
}

function safeErrorCode(error) {
  if (!error) return "unknown_error";
  const message = String(error && error.message ? error.message : error);
  return message.replace(/[^a-zA-Z0-9_:-]/g, "_").slice(0, 120) || "unknown_error";
}

function loadRuntime() {
  if (!runtimeManifestPath) throw new Error("runtime_manifest_missing");
  runtimeManifest = JSON.parse(fs.readFileSync(runtimeManifestPath, "utf8"));
  if (!runtimeManifest.runId || !runtimeManifest.originAUrl || !runtimeManifest.originBUrl || !runtimeManifest.guardianBaseUrl) {
    throw new Error("runtime_manifest_invalid");
  }
  guardianCredential = fs.readFileSync(runtimeManifest.credentialFilePath, "utf8").trim();
  if (!guardianCredential.startsWith("CODEXIFY-HARNESS-SENTINEL-")) throw new Error("synthetic_credential_invalid");
  state.runId = runtimeManifest.runId;
}

function trustedSender(event, args) {
  assertTrustedSender(event, trustedWebContentsId);
  assertRunId(args, state.runId);
  if (shutdownStarted) throw new Error("candidate_shutting_down");
}

function safeState() {
  return {
    candidateId: state.candidateId,
    runId: state.runId,
    phase: state.phase,
    remoteReady: state.remoteReady,
    url: state.url,
    origin: state.origin,
    title: state.title,
    loading: state.loading,
    documentGeneration: state.documentGeneration,
    remoteWebContentsId: state.remoteWebContentsId,
    lastPolicyDecision: state.lastPolicyDecision,
    lastError: state.lastError,
    preview: state.preview ? safePreview(state.preview) : null,
    pendingCapture: state.pendingCapture ? {
      captureRequestId: state.pendingCapture.captureRequestId,
      documentGeneration: state.pendingCapture.documentGeneration,
      sourceOrigin: state.pendingCapture.sourceOrigin,
      sourceUrl: state.pendingCapture.sourceUrl,
      captureMode: state.pendingCapture.captureMode
    } : null
  };
}

function updateRemoteMetadata() {
  if (!remoteWindow || remoteWindow.isDestroyed()) return;
  const url = remoteWindow.webContents.getURL() || "";
  state.url = url;
  try { state.origin = url ? new URL(url).origin : ""; } catch { state.origin = ""; }
  state.title = remoteWindow.webContents.getTitle() || "";
  state.remoteReady = Boolean(url && !remoteWindow.webContents.isLoading());
}

function invalidatePending(reason) {
  if (state.pendingCapture) safeLog("capture_invalidated", { status: reason, captureRequestId: state.pendingCapture.captureRequestId });
  state.pendingCapture = null;
  state.preview = null;
}

function policyOrigins() {
  return [runtimeManifest.originAUrl, runtimeManifest.originBUrl].map((value) => new URL(value).origin);
}

function isAllowedUrl(url) {
  return isAllowedFixtureUrl(url, policyOrigins());
}

async function navigateRemote(url) {
  boundedString(url, "url");
  if (!isAllowedUrl(url)) {
    state.lastPolicyDecision = isProtectedTarget(url) ? "protected_target_rejected" : "navigation_rejected";
    state.lastError = "navigation_rejected_by_allowlist";
    safeLog("navigation_policy", { status: "rejected", url });
    throw new Error(state.lastError);
  }
  state.lastPolicyDecision = "navigation_allowed";
  state.lastError = "";
  if (!remoteWindow || remoteWindow.isDestroyed()) throw new Error("remote_renderer_unavailable");
  await remoteWindow.loadURL(url);
  return safeState();
}

function extractionScript(mode) {
  return `(() => {
    const mode = ${JSON.stringify(mode)};
    const budget = ${MAX_CAPTURE_BYTES};
    const skipTags = new Set(['SCRIPT', 'STYLE', 'TEMPLATE', 'NOSCRIPT', 'IFRAME', 'INPUT', 'TEXTAREA', 'SELECT', 'OPTION', 'OBJECT', 'EMBED']);
    const isHidden = (element) => {
      if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;
      if (element.getAttribute('aria-hidden') === 'true') return true;
      const style = window.getComputedStyle(element);
      return style.display === 'none' || style.visibility === 'hidden' || style.contentVisibility === 'hidden';
    };
    const selected = () => {
      const value = window.getSelection ? String(window.getSelection() || '') : '';
      if (!value.trim()) throw new Error('empty_selection');
      return value;
    };
    const visible = () => {
      const parts = [];
      const walk = (node, hidden) => {
        if (!node) return;
        if (node.nodeType === Node.TEXT_NODE) {
          if (!hidden && node.nodeValue && node.nodeValue.trim()) parts.push(node.nodeValue.trim());
          return;
        }
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        const element = node;
        if (skipTags.has(element.tagName) || hidden || isHidden(element)) return;
        for (const child of element.childNodes) walk(child, false);
      };
      walk(document.body, false);
      return parts.join('\\n');
    };
    const content = mode === 'selected_text' ? selected() : visible();
    return { content: content.slice(0, budget + 1), fingerprintText: visible(), mode };
  })()`;
}

async function beginCapture(mode) {
  if (mode !== "selected_text" && mode !== "visible_page_text") throw new Error("capture_mode_rejected");
  if (!remoteWindow || remoteWindow.isDestroyed()) throw new Error("remote_renderer_unavailable");
  const sourceUrl = remoteWindow.webContents.getURL();
  if (!isAllowedUrl(sourceUrl)) throw new Error("source_policy_rejected");
  const sourceTitle = remoteWindow.webContents.getTitle();
  const captureRequestId = `capture-${crypto.randomBytes(12).toString("hex")}`;
  const ticket = crypto.randomBytes(24).toString("hex");
  const generation = state.documentGeneration;
  const requestStarted = Date.now();
  state.pendingCapture = {
    ticket,
    captureRequestId,
    remoteWebContentsId: remoteWindow.webContents.id,
    sourceUrl,
    sourceOrigin: new URL(sourceUrl).origin,
    sourceTitle,
    documentGeneration: generation,
    captureMode: mode,
    expiresAt: Date.now() + 15000
  };
  try {
    const result = await remoteWindow.webContents.executeJavaScript(extractionScript(mode), true);
    if (!state.pendingCapture || state.pendingCapture.ticket !== ticket) throw new Error("capture_ticket_invalidated");
    if (Date.now() > state.pendingCapture.expiresAt) throw new Error("capture_ticket_expired");
    if (remoteWindow.webContents.id !== state.pendingCapture.remoteWebContentsId || state.documentGeneration !== generation) {
      throw new Error("capture_document_changed");
    }
    if (!result || typeof result.content !== "string" || result.mode !== mode) throw new Error("capture_response_invalid");
    const pending = state.pendingCapture;
    state.pendingCapture = null;
    const envelope = makeEnvelope({
      runId: state.runId,
      sourceUrl: pending.sourceUrl,
      sourceTitle: pending.sourceTitle,
      captureMode: pending.captureMode,
      content: result.content,
      captureRequestId: pending.captureRequestId,
      requestId: runtimeManifest.syntheticRequestId,
      attemptNumber: attachmentAttemptNumber + 1,
      userInitiated: true,
      documentGeneration: pending.documentGeneration,
      documentFingerprint: hashContent(String(result.fingerprintText || ""))
    });
    state.preview = envelope;
    safeLog("capture_preview_ready", {
      status: "passed",
      captureRequestId: envelope.captureRequestId,
      contextId: envelope.contextId,
      requestId: envelope.requestId,
      durationMs: Date.now() - requestStarted,
      origin: envelope.sourceOrigin
    });
    return safeState();
  } catch (error) {
    invalidatePending("capture_failed");
    state.lastError = safeErrorCode(error);
    safeLog("capture_failed", { status: "failed", failureCode: state.lastError, durationMs: Date.now() - requestStarted });
    throw new Error(state.lastError);
  }
}

async function postGuardian(pathname, payload) {
  const response = await fetch(`${runtimeManifest.guardianBaseUrl}${pathname}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${guardianCredential}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  let body = {};
  try { body = await response.json(); } catch { body = {}; }
  return { ok: response.ok, status: response.status, body };
}

async function attachCapture(forceFailure = false) {
  if (!state.preview) throw new Error("capture_preview_missing");
  const envelope = state.preview;
  if (!remoteWindow || remoteWindow.isDestroyed() || remoteWindow.webContents.id !== state.remoteWebContentsId) throw new Error("stale_remote_renderer");
  if (state.documentGeneration !== envelope.documentGeneration && envelope.documentGeneration !== undefined) throw new Error("stale_document_generation");
  if (remoteWindow.webContents.getURL() !== envelope.sourceUrl) throw new Error("stale_source_url");
  if (new URL(envelope.sourceUrl).origin !== envelope.sourceOrigin) throw new Error("source_origin_mismatch");
  if (envelope.documentFingerprint) {
    const current = await remoteWindow.webContents.executeJavaScript(extractionScript("visible_page_text"), true);
    if (!current || hashContent(String(current.fingerprintText || "")) !== envelope.documentFingerprint) {
      invalidatePending("stale_document_content");
      throw new Error("stale_document_content");
    }
  }
  attachmentAttemptNumber += 1;
  const started = Date.now();
  const result = await postGuardian(forceFailure ? "/api/context/attach-fail" : "/api/context/attach", envelope);
  if (!result.ok) {
    state.lastError = `attachment_${result.status}`;
    safeLog("attachment", { status: "failed", captureRequestId: envelope.captureRequestId, contextId: envelope.contextId, requestId: envelope.requestId, attemptNumber: attachmentAttemptNumber, failureCode: result.body.failureCode || "guardian_rejected", durationMs: Date.now() - started });
    return safeState();
  }
  state.preview = null;
  state.lastError = "";
  state.phase = "ready";
  safeLog("attachment", { status: "passed", captureRequestId: envelope.captureRequestId, contextId: envelope.contextId, requestId: envelope.requestId, attemptNumber: attachmentAttemptNumber, durationMs: Date.now() - started });
  return safeState();
}

async function companion() {
  const response = await fetch(`${runtimeManifest.guardianBaseUrl}/api/companion`, {
    headers: { "Authorization": `Bearer ${guardianCredential}` }
  });
  if (!response.ok) throw new Error(`companion_${response.status}`);
  state.lastError = "";
  return safeState();
}

function configureRemoteWindow() {
  if (!remoteWindow) return;
  const contents = remoteWindow.webContents;
  contents.setWindowOpenHandler(({ url }) => {
    state.lastPolicyDecision = isAllowedUrl(url) ? "popup_rejected" : "popup_rejected";
    safeLog("popup_policy", { status: "rejected", url });
    return { action: "deny" };
  });
  contents.on("will-navigate", (event, details) => {
    const url = typeof details === "string" ? details : details.url;
    if (!isAllowedUrl(url)) {
      event.preventDefault();
      state.lastPolicyDecision = isProtectedTarget(url) ? "protected_target_rejected" : "navigation_rejected";
      state.lastError = "navigation_rejected_by_allowlist";
      safeLog("navigation_policy", { status: "rejected", url });
    }
  });
  contents.on("will-frame-navigate", (event, details) => {
    if (details.isMainFrame && !isAllowedUrl(details.url)) event.preventDefault();
  });
  contents.on("did-start-navigation", (_event, details) => {
    if (details.isMainFrame) {
      state.documentGeneration += 1;
      state.loading = "loading";
      invalidatePending("navigation_started");
    }
  });
  contents.on("did-navigate-in-page", (_event, url, isMainFrame) => {
    if (isMainFrame) {
      state.documentGeneration += 1;
      state.loading = "ready";
      invalidatePending("in_page_navigation");
      updateRemoteMetadata();
    }
  });
  contents.on("did-finish-load", () => {
    state.loading = "ready";
    state.lastError = "";
    updateRemoteMetadata();
    state.remoteReady = true;
    state.phase = "ready";
  });
  contents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (!isMainFrame) return;
    state.loading = "failed";
    state.lastError = `navigation_failed_${errorCode}`;
    state.url = validatedURL || state.url;
    safeLog("navigation", { status: "failed", url: validatedURL || "", failureCode: errorDescription || String(errorCode) });
  });
  contents.on("destroyed", () => {
    state.remoteReady = false;
    state.phase = "degraded";
    state.loading = "failed";
    invalidatePending("remote_destroyed");
  });
  remoteSession.on("will-download", (event, item) => {
    event.preventDefault();
    state.lastPolicyDecision = "download_rejected";
    safeLog("download_policy", { status: "rejected", url: item.getURL() });
  });
}

function configureSession() {
  remoteSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  remoteSession.setPermissionCheckHandler(() => false);
  if (remoteSession.setDevicePermissionHandler) remoteSession.setDevicePermissionHandler(() => false);
  if (remoteSession.setDisplayMediaRequestHandler) remoteSession.setDisplayMediaRequestHandler((_request, callback) => callback({}));
}

function createTrustedWindow() {
  trustedWindow = new BrowserWindow({
    width: 980,
    height: 900,
    title: "Codexify Electron Browser Host Proof — Trusted Shell",
    webPreferences: {
      preload: path.join(ROOT, "trusted-preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webviewTag: false,
      spellcheck: false
    }
  });
  trustedWebContentsId = trustedWindow.webContents.id;
  trustedWindow.loadFile(UI_FILE);
}

async function createRemoteWindow() {
  const partition = `electron-proof-${state.runId}`;
  remoteSession = session.fromPartition(partition, { cache: true });
  configureSession();
  remoteWindow = new BrowserWindow({
    width: 960,
    height: 720,
    title: "Codexify Electron Browser Host Proof — Remote Fixture",
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webviewTag: false,
      spellcheck: false,
      session: remoteSession
    }
  });
  state.remoteWebContentsId = remoteWindow.webContents.id;
  configureRemoteWindow();
  const initialUrl = `${runtimeManifest.originAUrl}/basic-visible`;
  await remoteWindow.loadURL(initialUrl);
  trustedWindow.focus();
}

function registerIpc() {
  const handler = (channel, fn) => {
    ipcMain.handle(channel, async (event, args) => {
      trustedSender(event, args);
      return fn(args);
    });
  };
  handler(IPC_CHANNELS.state, (args) => { assertEmptyArgs(args); return safeState(); });
  handler(IPC_CHANNELS.navigate, (args) => navigateRemote(boundedString(args && args.url, "url")));
  handler(IPC_CHANNELS.back, () => { remoteWindow.webContents.goBack(); return safeState(); });
  handler(IPC_CHANNELS.forward, () => { remoteWindow.webContents.goForward(); return safeState(); });
  handler(IPC_CHANNELS.reload, () => { remoteWindow.webContents.reload(); return safeState(); });
  handler(IPC_CHANNELS.selectedCapture, () => beginCapture("selected_text"));
  handler(IPC_CHANNELS.visibleCapture, () => beginCapture("visible_page_text"));
  handler(IPC_CHANNELS.preview, () => safeState());
  handler(IPC_CHANNELS.attach, () => attachCapture(false));
  handler(IPC_CHANNELS.attachFailure, () => attachCapture(true));
  handler(IPC_CHANNELS.cancel, () => { invalidatePending("cancelled"); state.lastError = ""; return safeState(); });
  handler(IPC_CHANNELS.companion, () => companion());
  handler(IPC_CHANNELS.rendererFailure, () => {
    if (remoteWindow && !remoteWindow.isDestroyed()) remoteWindow.destroy();
    state.phase = "degraded";
    state.remoteReady = false;
    return safeState();
  });
  handler(IPC_CHANNELS.shutdown, async () => { await cleanShutdown(); return safeState(); });
}

async function cleanShutdown() {
  if (shutdownStarted) return;
  shutdownStarted = true;
  invalidatePending("shutdown");
  state.phase = "shutting_down";
  try { if (remoteSession) await remoteSession.clearStorageData(); } catch { /* best effort bounded cleanup */ }
  if (remoteWindow && !remoteWindow.isDestroyed()) remoteWindow.destroy();
  if (trustedWindow && !trustedWindow.isDestroyed()) trustedWindow.destroy();
  if (guardianCredential) guardianCredential = "";
  state.remoteReady = false;
  safeLog("shutdown", { status: "passed" });
  app.quit();
}

app.whenReady().then(async () => {
  try {
    loadRuntime();
    registerIpc();
    createTrustedWindow();
    await createRemoteWindow();
    updateRemoteMetadata();
    state.phase = "ready";
    safeLog("launch", { status: "passed", origin: state.origin });
  } catch (error) {
    state.phase = "failed";
    state.lastError = safeErrorCode(error);
    safeLog("launch", { status: "failed", failureCode: state.lastError });
    app.exit(1);
  }
});

app.on("window-all-closed", () => {
  if (!shutdownStarted) cleanShutdown().catch(() => app.quit());
});

process.on("uncaughtException", (error) => {
  safeLog("main_exception", { status: "failed", failureCode: safeErrorCode(error) });
});
