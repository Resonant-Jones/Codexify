"use strict";

const crypto = require("node:crypto");
const { isAllowedNavigation, classifyNavigation } = require("./navigation-policy");

const REMOTE_WEB_PREFERENCES = Object.freeze({ nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true, webviewTag: false });

function createRemoteTab({ WebContentsView, session, parentWindow, fixtureOrigin, initialBounds, onState }) {
  if (!WebContentsView || !session || !parentWindow) throw new Error("remote_dependencies_missing");
  if (!isAllowedNavigation(fixtureOrigin, fixtureOrigin)) throw new Error("fixture_origin_denied");
  const partition = `codexify-browser-host-${crypto.randomUUID()}`;
  if (partition.startsWith("persist" + ":")) throw new Error("persistent_partition_denied");
  const remoteSession = session.fromPartition(partition);
  const view = new WebContentsView({ webPreferences: { ...REMOTE_WEB_PREFERENCES, session: remoteSession } });
  const contents = view.webContents;
  let destroyed = false;
  const listeners = [];
  const listen = (emitter, event, handler) => { emitter.on(event, handler); listeners.push(() => emitter.removeListener(event, handler)); };
  const notify = (patch) => { if (!destroyed) onState?.(patch); };
  const metadata = () => {
    const url = contents.isDestroyed() ? "" : contents.getURL() || "";
    let origin = "";
    try { origin = url ? new URL(url).origin : ""; } catch { origin = ""; }
    return { remoteUrl: url, remoteOrigin: origin, remoteTitle: contents.isDestroyed() ? "" : contents.getTitle() || "" };
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
  listen(contents, "did-start-loading", () => notify({ remoteLoadingState: "loading", remoteStatus: "loading", ...metadata() }));
  listen(contents, "did-navigate", () => notify({ remoteLoadingState: "ready", remoteStatus: "ready", remoteProcessState: "running", ...metadata() }));
  listen(contents, "did-navigate-in-page", () => notify({ remoteLoadingState: "ready", remoteStatus: "ready", ...metadata() }));
  listen(contents, "did-finish-load", () => notify({ remoteLoadingState: "ready", remoteStatus: "ready", remoteProcessState: "running", ...metadata() }));
  listen(contents, "did-fail-load", (_event, errorCode, _description, validatedURL, isMainFrame) => { if (isMainFrame && errorCode !== -3) notify({ remoteLoadingState: "failed", remoteStatus: "degraded", errorCode: "guardian_rejected", ...metadata(), remoteUrl: validatedURL || "" }); });
  listen(contents, "render-process-gone", () => notify({ remoteStatus: "degraded", remoteProcessState: "terminated", remoteLoadingState: "failed", runtimeStatus: "degraded", errorCode: "guardian_rejected", ...metadata() }));
  listen(contents, "destroyed", () => notify({ remoteStatus: "degraded", remoteProcessState: "terminated", runtimeStatus: "degraded", errorCode: "guardian_rejected" }));

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
    notify({ remoteLoadedAfterNegotiation: true });
    return metadata();
  }
  async function reload() { if (destroyed || contents.isDestroyed()) throw new Error("remote_renderer_unavailable"); await contents.reload(); return metadata(); }
  async function destroy() {
    if (destroyed) return;
    destroyed = true;
    for (const remove of listeners.splice(0)) remove();
    remoteSession.removeListener("will-download", downloadHandler);
    if (!parentWindow.isDestroyed()) parentWindow.contentView.removeChildView(view);
    try { await remoteSession.clearStorageData(); } catch { /* ephemeral cleanup is best effort */ }
    if (!contents.isDestroyed()) contents.destroy();
  }

  return Object.freeze({ view, contents, session: remoteSession, partition, load, reload, destroy, setBounds: (bounds) => { if (!destroyed) view.setBounds(bounds); }, metadata });
}

module.exports = Object.freeze({ REMOTE_WEB_PREFERENCES, createRemoteTab });
