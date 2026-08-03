const api = window.codexifyBrowserHost;
const address = document.querySelector("#address");
const preview = document.querySelector("#preview");
const previewEmpty = document.querySelector("#preview-empty");
const previewMetadata = document.querySelector("#preview-metadata");
const attachmentActions = document.querySelector("#attachment-actions");
const status = document.querySelector("#status");
const stateList = document.querySelector("#state-list");
const attach = document.querySelector("#attach");

function setStatus(message, state = "") {
  status.textContent = message;
  status.dataset.state = state;
}

function renderState(state) {
  if (!state) return;
  if (state.url && document.activeElement !== address) address.value = state.url;
  const fields = [
    ["Phase", state.phase],
    ["Remote renderer", state.remoteReady ? "ready" : "not ready"],
    ["URL", state.url || "—"],
    ["Origin", state.origin || "—"],
    ["Title", state.title || "—"],
    ["Document generation", state.documentGeneration],
    ["Loading", state.loading],
    ["Last policy decision", state.lastPolicyDecision || "—"],
    ["Credential in renderer", "no — main process only"],
    ["Production authority", "no"]
  ];
  stateList.replaceChildren(...fields.flatMap(([key, value]) => {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = String(value);
    return [dt, dd];
  }));
  if (state.preview) renderPreview(state.preview);
  if (state.lastError) setStatus(state.lastError, "failure");
}

function renderPreview(data) {
  previewEmpty.hidden = true;
  previewMetadata.hidden = false;
  preview.hidden = false;
  attachmentActions.hidden = false;
  const fields = [
    ["Source title", data.sourceTitle],
    ["Source origin", data.sourceOrigin],
    ["Source URL", data.sourceUrl],
    ["Capture mode", data.captureMode],
    ["Content length", data.contentLength],
    ["Truncated", data.truncated ? "yes" : "no"],
    ["Permission scope", data.permissionScope],
    ["User initiated", data.userInitiated ? "yes" : "no"]
  ];
  previewMetadata.replaceChildren(...fields.flatMap(([key, value]) => {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = String(value);
    return [dt, dd];
  }));
  preview.textContent = data.contentPreview || "(empty)";
}

async function refresh() {
  try { renderState(await api.getState()); } catch (error) { setStatus(`state unavailable: ${String(error)}`, "failure"); }
}

async function run(action, successMessage = "") {
  try {
    const result = await action();
    renderState(result);
    if (successMessage) setStatus(successMessage, "success");
    return result;
  } catch (error) {
    await refresh();
    setStatus(`bounded action failure: ${String(error)}`, "failure");
    return null;
  }
}

document.querySelector("#navigate").addEventListener("click", () => run(() => api.navigate(address.value), "Navigation request accepted."));
document.querySelector("#back").addEventListener("click", () => run(() => api.back(), "Back request accepted."));
document.querySelector("#forward").addEventListener("click", () => run(() => api.forward(), "Forward request accepted."));
document.querySelector("#reload").addEventListener("click", () => run(() => api.reload(), "Reload request accepted."));
document.querySelector("#capture-selection").addEventListener("click", () => run(() => api.captureSelectedText(), "Selected-text preview ready."));
document.querySelector("#capture-page").addEventListener("click", () => run(() => api.captureVisiblePageText(), "Visible-page preview ready."));
document.querySelector("#cancel").addEventListener("click", () => run(() => api.cancelCapture(), "Capture cancelled."));
attach.addEventListener("click", () => run(() => api.attachCapture(), "Context attached; ephemeral host state cleared."));
document.querySelector("#attach-failure").addEventListener("click", () => run(() => api.requestAttachmentFailure(), "Bounded attachment failure recorded; companion remains available."));
document.querySelector("#companion").addEventListener("click", () => run(() => api.checkCompanion(), "Companion response received."));
document.querySelector("#renderer-failure").addEventListener("click", () => run(() => api.triggerRendererFailure(), "Remote renderer degraded; trusted shell remains alive."));
document.querySelector("#shutdown").addEventListener("click", () => run(() => api.shutdown(), "Clean shutdown requested."));

refresh();
window.setInterval(refresh, 250);
