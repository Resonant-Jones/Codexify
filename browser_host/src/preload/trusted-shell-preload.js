"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const CHANNELS = Object.freeze({
  getState: "browser-host:get-state",
  reloadRemote: "browser-host:reload-remote",
  captureSelectedText: "browser-host:capture-selected-text",
  captureVisiblePage: "browser-host:capture-visible-page",
  attachCapture: "browser-host:attach-capture",
  cancelCapture: "browser-host:cancel-capture",
  stateChanged: "browser-host:state-changed"
});

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function deepFreeze(value) { if (value && typeof value === "object" && !Object.isFrozen(value)) { for (const child of Object.values(value)) deepFreeze(child); Object.freeze(value); } return value; }
function boundedState(value) { return deepFreeze(clone(value)); }

const api = {
  getState: () => ipcRenderer.invoke(CHANNELS.getState).then(boundedState),
  reloadRemote: () => ipcRenderer.invoke(CHANNELS.reloadRemote).then(boundedState),
  captureSelectedText: () => ipcRenderer.invoke(CHANNELS.captureSelectedText).then(boundedState),
  captureVisiblePage: () => ipcRenderer.invoke(CHANNELS.captureVisiblePage).then(boundedState),
  attachCapture: (ticketId) => ipcRenderer.invoke(CHANNELS.attachCapture, typeof ticketId === "string" ? ticketId : "").then(boundedState),
  cancelCapture: (ticketId) => ipcRenderer.invoke(CHANNELS.cancelCapture, typeof ticketId === "string" ? ticketId : "").then(boundedState),
  onStateChanged: (callback) => {
    if (typeof callback !== "function") throw new TypeError("state_callback_required");
    const listener = (_event, state) => callback(boundedState(state));
    ipcRenderer.on(CHANNELS.stateChanged, listener);
    return () => ipcRenderer.removeListener(CHANNELS.stateChanged, listener);
  }
};

contextBridge.exposeInMainWorld("codexifyBrowserHost", Object.freeze(api));
