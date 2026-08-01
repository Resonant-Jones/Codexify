"use strict";

const api = window.codexifyBrowserHost;
const status = document.querySelector("#status");
const origin = document.querySelector("#origin");
const versions = document.querySelector("#versions");
const captureStatus = document.querySelector("#capture-status");
const capturePreview = document.querySelector("#capture-preview");
const captureSelected = document.querySelector("#capture-selected");
const captureVisible = document.querySelector("#capture-visible");
const attachCapture = document.querySelector("#attach-capture");
const cancelCapture = document.querySelector("#cancel-capture");

function render(state) {
  if (!state) return;
  window.__captureTicketId = state.captureTicketId || "";
  status.textContent = `${state.runtimeStatus} · remote ${state.remoteStatus}`;
  origin.textContent = state.remoteOrigin || "No remote origin";
  versions.textContent = `protocol ${state.protocolVersion} · envelope ${state.envelopeVersion} · attachment ${state.attachmentVersion}`;
  captureStatus.textContent = `capture ${state.captureStatus} · mode ${state.captureMode || "none"}${state.captureErrorCode ? ` · ${state.captureErrorCode}` : ""}`;
  capturePreview.textContent = state.capturePreviewContent || "No page content has crossed the capture boundary.";
  const previewReady = state.captureStatus === "preview_ready" && typeof state.captureTicketId === "string";
  captureSelected.disabled = state.remoteStatus !== "ready";
  captureVisible.disabled = captureSelected.disabled;
  attachCapture.disabled = !previewReady;
  cancelCapture.disabled = !previewReady;
  document.body.dataset.runtimeStatus = state.runtimeStatus;
  document.body.dataset.errorCode = state.errorCode || "";
}

api.getState().then(render).catch(() => { status.textContent = "trusted shell state unavailable"; });
const unsubscribe = api.onStateChanged(render);
window.addEventListener("pagehide", unsubscribe, { once: true });
document.querySelector("#reload").addEventListener("click", () => api.reloadRemote().then(render).catch(() => {
  status.textContent = "remote reload unavailable";
  document.body.dataset.errorCode = "guardian_rejected";
}));

function invokeCapture(operation) {
  operation().then(render).catch(() => {
    captureStatus.textContent = "capture unavailable";
    document.body.dataset.errorCode = "capture_failed";
  });
}

captureSelected.addEventListener("click", () => invokeCapture(() => api.captureSelectedText()));
captureVisible.addEventListener("click", () => invokeCapture(() => api.captureVisiblePage()));
attachCapture.addEventListener("click", () => invokeCapture(() => api.attachCapture(window.__captureTicketId || "")));
cancelCapture.addEventListener("click", () => invokeCapture(() => api.cancelCapture(window.__captureTicketId || "")));
