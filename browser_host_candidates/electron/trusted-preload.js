const { contextBridge, ipcRenderer } = require("electron");
const MAX_STRING_LENGTH = 2048;
const IPC_CHANNELS = Object.freeze({
  state: "candidate:state",
  navigate: "candidate:navigate",
  back: "candidate:back",
  forward: "candidate:forward",
  reload: "candidate:reload",
  selectedCapture: "capture:selected",
  visibleCapture: "capture:visible",
  preview: "capture:preview",
  attach: "capture:attach",
  attachFailure: "capture:attach-failure",
  cancel: "capture:cancel",
  companion: "candidate:companion",
  rendererFailure: "candidate:renderer-failure",
  shutdown: "candidate:shutdown"
});

function boundedUrl(value) {
  if (typeof value !== "string" || value.length === 0 || value.length > MAX_STRING_LENGTH) {
    throw new Error("url_invalid");
  }
  return value;
}

function boundedMode(value) {
  if (value !== "selected_text" && value !== "visible_page_text") throw new Error("capture_mode_invalid");
  return value;
}

const api = {
  getState: () => ipcRenderer.invoke(IPC_CHANNELS.state),
  navigate: (url) => ipcRenderer.invoke(IPC_CHANNELS.navigate, { url: boundedUrl(url) }),
  back: () => ipcRenderer.invoke(IPC_CHANNELS.back),
  forward: () => ipcRenderer.invoke(IPC_CHANNELS.forward),
  reload: () => ipcRenderer.invoke(IPC_CHANNELS.reload),
  captureSelectedText: () => ipcRenderer.invoke(IPC_CHANNELS.selectedCapture, { mode: boundedMode("selected_text") }),
  captureVisiblePageText: () => ipcRenderer.invoke(IPC_CHANNELS.visibleCapture, { mode: boundedMode("visible_page_text") }),
  getCapturePreview: () => ipcRenderer.invoke(IPC_CHANNELS.preview),
  attachCapture: () => ipcRenderer.invoke(IPC_CHANNELS.attach),
  requestAttachmentFailure: () => ipcRenderer.invoke(IPC_CHANNELS.attachFailure),
  cancelCapture: () => ipcRenderer.invoke(IPC_CHANNELS.cancel),
  checkCompanion: () => ipcRenderer.invoke(IPC_CHANNELS.companion),
  triggerRendererFailure: () => ipcRenderer.invoke(IPC_CHANNELS.rendererFailure),
  shutdown: () => ipcRenderer.invoke(IPC_CHANNELS.shutdown)
};

contextBridge.exposeInMainWorld("codexifyBrowserHost", Object.freeze(api));
