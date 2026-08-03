"use strict";

const api = window.codexifyBrowserHost;
const status = document.querySelector("#status");
const origin = document.querySelector("#origin");
const versions = document.querySelector("#versions");
const negotiationPosture = document.querySelector("#negotiation-posture");
const captureStatus = document.querySelector("#capture-status");
const capturePreview = document.querySelector("#capture-preview");
const captureSelected = document.querySelector("#capture-selected");
const captureVisible = document.querySelector("#capture-visible");
const attachCapture = document.querySelector("#attach-capture");
const cancelCapture = document.querySelector("#cancel-capture");
const attachmentPosture = document.querySelector("#attachment-posture");

function renderAttachmentPosture(state) {
  if (state.guardianAttachmentAdapterEnabled) {
    const originText = state.guardianAttachmentOrigin || "loopback origin unavailable";
    const grantText = state.attachmentGrantAvailable ? "one-use grant available" : "one-use grant unavailable";
    return `transport Guardian development adapter · ${originText} · ${grantText} · reusable Guardian credential: no · accepted attachment: non-durable · new grant requires a new trusted operator launch after use`;
  }
  return "transport deterministic stub · Guardian development adapter disabled · reusable Guardian credential: no · accepted attachment: non-durable";
}

function renderNegotiationPosture(state) {
  const selected = state.selectedVersions || {};
  const selectedText = selected.protocol ? `selected ${selected.protocol}/${selected.envelope}/${selected.attachment}` : "no versions selected";
  const transport = state.negotiationTransport || "deterministic_stub";
  const remote = state.remoteLoadedAfterGuardianNegotiation ? "remote loaded after compatible Guardian negotiation" : `remote ${state.remoteStatus}`;
  return `transport ${transport} · Guardian adapter ${state.guardianNegotiationAdapterEnabled ? "enabled" : "disabled"} · ${selectedText} · enabled features ${state.enabledFeatures.length} · disabled features ${state.disabledFeatures.length} · ${remote} · ${state.negotiationCredentialPosture === "no_credential_required_local_development_negotiation" ? "No credential required for local development negotiation" : "credential posture unavailable"}`;
}

function render(state) {
  if (!state) return;
  window.__captureTicketId = state.captureTicketId || "";
  status.textContent = `${state.runtimeStatus} · remote ${state.remoteStatus}`;
  origin.textContent = state.remoteOrigin || "No remote origin";
  versions.textContent = `protocol ${state.protocolVersion} · envelope ${state.envelopeVersion} · attachment ${state.attachmentVersion}`;
  negotiationPosture.textContent = renderNegotiationPosture(state);
  captureStatus.textContent = `capture ${state.captureStatus} · mode ${state.captureMode || "none"}${state.captureErrorCode ? ` · ${state.captureErrorCode}` : ""}`;
  attachmentPosture.textContent = renderAttachmentPosture(state);
  capturePreview.textContent = state.capturePreviewContent || "No page content has crossed the capture boundary.";
  const previewReady = state.captureStatus === "preview_ready" && typeof state.captureTicketId === "string";
  captureSelected.disabled = state.remoteStatus !== "ready";
  captureVisible.disabled = captureSelected.disabled;
  attachCapture.disabled = !previewReady || (state.guardianAttachmentAdapterEnabled && !state.attachmentGrantAvailable);
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
