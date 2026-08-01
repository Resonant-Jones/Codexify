"use strict";

const api = window.codexifyBrowserHost;
const status = document.querySelector("#status");
const origin = document.querySelector("#origin");
const versions = document.querySelector("#versions");

function render(state) {
  if (!state) return;
  status.textContent = `${state.runtimeStatus} · remote ${state.remoteStatus}`;
  origin.textContent = state.remoteOrigin || "No remote origin";
  versions.textContent = `protocol ${state.protocolVersion} · envelope ${state.envelopeVersion} · attachment ${state.attachmentVersion}`;
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
