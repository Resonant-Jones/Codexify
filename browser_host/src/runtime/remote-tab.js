"use strict";

const crypto = require("node:crypto");
const { isAllowedNavigation, classifyNavigation } = require("./navigation-policy");
const { buildDocumentFingerprint } = require("./capture");

const REMOTE_WEB_PREFERENCES = Object.freeze({ nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true, webviewTag: false });

function captureRenderer(mode) {
  const MAX_BYTES = 65536;
  const EXCLUDED_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT", "OPTION", "BUTTON", "SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "IFRAME", "FRAME", "OBJECT", "EMBED", "PORTAL"]);
  const byteLength = (value) => new TextEncoder().encode(String(value)).length;
  const truncate = (value) => {
    const encoded = new TextEncoder().encode(String(value));
    if (encoded.length <= MAX_BYTES) return String(value);
    let end = MAX_BYTES;
    while (end > 0 && (encoded[end] & 0xc0) === 0x80) end -= 1;
    return new TextDecoder().decode(encoded.slice(0, end));
  };
  const normalize = (value) => String(value).replace(/\u0000/g, "").replace(/\u00a0/g, " ").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  const excluded = (element) => {
    if (!element || element.nodeType !== 1) return false;
    if (EXCLUDED_TAGS.has(element.tagName) || element.hidden || element.getAttribute("aria-hidden") === "true" || element.isContentEditable || element.getAttribute("contenteditable") === "true") return true;
    const style = getComputedStyle(element);
    return style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse";
  };
  const nodeExcluded = (node) => {
    let current = node?.nodeType === 1 ? node : node?.parentElement;
    while (current) {
      if (excluded(current)) return true;
      current = current.parentElement;
    }
    return false;
  };
  const collectVisible = () => {
    const parts = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (nodeExcluded(node)) continue;
      const text = normalize(node.nodeValue || "");
      if (text) parts.push(text);
    }
    const fullText = normalize(parts.join("\n"));
    return { text: truncate(fullText), originalLength: byteLength(fullText) };
  };
  const selection = () => {
    const current = window.getSelection();
    if (!current || current.isCollapsed || current.rangeCount < 1) return { text: "", originalLength: 0 };
    const range = current.getRangeAt(0);
    if (nodeExcluded(range.startContainer) || nodeExcluded(range.endContainer) || nodeExcluded(range.commonAncestorContainer)) return { text: "", originalLength: 0 };
    const fragment = range.cloneContents();
    if (fragment.querySelector && fragment.querySelector("input,textarea,select,option,button,script,style,noscript,template,iframe,frame,object,embed,portal,[contenteditable='true']")) return { text: "", originalLength: 0 };
    const fullText = normalize(current.toString());
    return { text: truncate(fullText), originalLength: byteLength(fullText) };
  };
  if (!["selected_text", "visible_page_text", "document_fingerprint"].includes(mode)) return { errorCode: "unknown_capture_mode" };
  const visible = collectVisible();
  const selected = selection();
  return {
    selectedText: selected.text,
    selectedTextOriginalLength: selected.originalLength,
    visibleText: visible.text,
    visibleTextOriginalLength: visible.originalLength
  };
}

const CAPTURE_SCRIPT = `(${captureRenderer.toString()})`;

function createRemoteTab({ WebContentsView, session, parentWindow, fixtureOrigin, initialBounds, onState }) {
  if (!WebContentsView || !session || !parentWindow) throw new Error("remote_dependencies_missing");
  if (!isAllowedNavigation(fixtureOrigin, fixtureOrigin)) throw new Error("fixture_origin_denied");
  const partition = `codexify-browser-host-${crypto.randomUUID()}`;
  if (partition.startsWith("persist" + ":")) throw new Error("persistent_partition_denied");
  const remoteSession = session.fromPartition(partition);
  const view = new WebContentsView({ webPreferences: { ...REMOTE_WEB_PREFERENCES, session: remoteSession } });
  const contents = view.webContents;
  let destroyed = false;
  let loaded = false;
  let documentGeneration = 0;
  const listeners = [];
  const listen = (emitter, event, handler) => { emitter.on(event, handler); listeners.push(() => emitter.removeListener(event, handler)); };
  const notify = (patch) => { if (!destroyed) onState?.(patch); };
  const metadata = () => {
    const url = contents.isDestroyed() ? "" : contents.getURL() || "";
    let origin = "";
    try { origin = url ? new URL(url).origin : ""; } catch { origin = ""; }
    return { remoteUrl: url, remoteOrigin: origin, remoteTitle: contents.isDestroyed() ? "" : contents.getTitle() || "" };
  };
  const advanceDocument = () => {
    documentGeneration += 1;
    notify({ remoteDocumentGeneration: documentGeneration });
  };
  const policy = (url, kind) => {
    const decision = classifyNavigation(url, fixtureOrigin);
    if (!decision.allowed) notify({ lastPolicyDecision: `${kind}_denied:${decision.reason}`, errorCode: decision.code });
    return decision.allowed;
  };

  contents.setWindowOpenHandler(() => { notify({ lastPolicyDecision: "popup_denied", errorCode: "permission_denied" }); return { action: "deny" }; });
  listen(contents, "will-navigate", (event, url) => { if (!policy(url, "navigation")) event.preventDefault(); });
  listen(contents, "will-frame-navigate", (event, detailsOrUrl, _isInPlace, legacyIsMainFrame) => {
    const url = typeof detailsOrUrl === "string" ? detailsOrUrl : detailsOrUrl?.url;
    const isMainFrame = typeof detailsOrUrl === "string" ? legacyIsMainFrame !== false : detailsOrUrl?.isMainFrame !== false;
    if (!policy(url, isMainFrame ? "navigation" : "frame_navigation")) event.preventDefault();
  });
  listen(contents, "will-redirect", (event, detailsOrUrl) => {
    const url = typeof detailsOrUrl === "string" ? detailsOrUrl : detailsOrUrl?.url;
    if (!policy(url, "redirect")) event.preventDefault();
  });
  listen(contents, "did-start-loading", () => { loaded = false; notify({ remoteLoadingState: "loading", remoteStatus: "loading", ...metadata() }); });
  listen(contents, "did-navigate", () => { advanceDocument(); notify({ remoteLoadingState: "loading", remoteStatus: "loading", remoteProcessState: "running", ...metadata() }); });
  listen(contents, "did-navigate-in-page", (_event, _url, isMainFrame) => { if (isMainFrame !== false) advanceDocument(); notify({ remoteLoadingState: "ready", remoteStatus: "ready", ...metadata() }); });
  listen(contents, "did-finish-load", () => { if (documentGeneration === 0) advanceDocument(); loaded = true; notify({ remoteLoadingState: "ready", remoteStatus: "ready", remoteProcessState: "running", remoteDocumentGeneration: documentGeneration, ...metadata() }); });
  listen(contents, "did-fail-load", (_event, errorCode, _description, validatedURL, isMainFrame) => { if (isMainFrame && errorCode !== -3) { loaded = false; notify({ remoteLoadingState: "failed", remoteStatus: "degraded", errorCode: "guardian_rejected", ...metadata(), remoteUrl: validatedURL || "" }); } });
  listen(contents, "render-process-gone", () => { loaded = false; notify({ remoteStatus: "degraded", remoteProcessState: "terminated", remoteLoadingState: "failed", runtimeStatus: "degraded", errorCode: "guardian_rejected", ...metadata() }); });
  listen(contents, "destroyed", () => { loaded = false; notify({ remoteStatus: "degraded", remoteProcessState: "terminated", runtimeStatus: "degraded", errorCode: "guardian_rejected" }); });

  const denyPermission = (_webContents, _permission, callback) => callback(false);
  remoteSession.setPermissionRequestHandler(denyPermission);
  remoteSession.setPermissionCheckHandler(() => false);
  if (typeof remoteSession.setDevicePermissionHandler === "function") remoteSession.setDevicePermissionHandler(() => false);
  if (typeof remoteSession.setDisplayMediaRequestHandler === "function") remoteSession.setDisplayMediaRequestHandler((_request, callback) => callback({}));
  const downloadHandler = (event) => { event.preventDefault(); notify({ lastPolicyDecision: "download_denied", errorCode: "permission_denied" }); };
  remoteSession.on("will-download", downloadHandler);
  parentWindow.contentView.addChildView(view);
  view.setBounds(initialBounds);
  notify({ remoteViewCreated: true, remoteStatus: "loading", remoteLoadingState: "loading", remoteProcessState: "starting" });

  async function load() {
    if (destroyed || contents.isDestroyed()) throw new Error("remote_renderer_unavailable");
    if (!isAllowedNavigation(fixtureOrigin, fixtureOrigin)) throw new Error("fixture_origin_denied");
    await contents.loadURL(fixtureOrigin);
    if (documentGeneration === 0) advanceDocument();
    loaded = true;
    notify({ remoteLoadedAfterNegotiation: true });
    return metadata();
  }
  async function reload() { if (destroyed || contents.isDestroyed()) throw new Error("remote_renderer_unavailable"); await contents.reload(); return metadata(); }
  function documentState() { return Object.freeze({ ...metadata(), generation: documentGeneration, ready: loaded && !destroyed && !contents.isDestroyed() }); }
  async function capture(mode) {
    if (destroyed || contents.isDestroyed() || !loaded) { const error = new Error("remote_renderer_unavailable"); error.code = "tab_unavailable"; throw error; }
    const current = metadata();
    if (!isAllowedNavigation(current.remoteUrl, fixtureOrigin)) { const error = new Error("remote_origin_denied"); error.code = "origin_mismatch"; throw error; }
    try {
      const result = await contents.executeJavaScript(`${CAPTURE_SCRIPT}(${JSON.stringify(mode)})`, true);
      if (result?.errorCode) { const error = new Error(result.errorCode); error.code = result.errorCode; throw error; }
      return Object.freeze({ ...result, documentGeneration });
    } catch (error) {
      if (error?.code) throw error;
      const wrapped = new Error("capture_renderer_failed");
      wrapped.code = "capture_failed";
      throw wrapped;
    }
  }
  async function documentFingerprint() {
    const raw = await capture("document_fingerprint");
    const current = metadata();
    return Object.freeze({ ...current, generation: documentGeneration, documentFingerprint: buildDocumentFingerprint({ sourceUrl: current.remoteUrl, sourceTitle: current.remoteTitle, visibleText: raw.visibleText, visibleTextOriginalLength: raw.visibleTextOriginalLength }) });
  }
  async function destroy() {
    if (destroyed) return;
    destroyed = true;
    for (const remove of listeners.splice(0)) remove();
    remoteSession.removeListener("will-download", downloadHandler);
    if (!parentWindow.isDestroyed()) parentWindow.contentView.removeChildView(view);
    try { await remoteSession.clearStorageData(); } catch { /* ephemeral cleanup is best effort */ }
    if (!contents.isDestroyed()) contents.destroy();
  }

  return Object.freeze({ view, contents, session: remoteSession, partition, load, reload, capture, documentState, documentFingerprint, destroy, setBounds: (bounds) => { if (!destroyed) view.setBounds(bounds); }, metadata });
}

module.exports = Object.freeze({ REMOTE_WEB_PREFERENCES, createRemoteTab });
