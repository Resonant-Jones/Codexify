"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const CHANNELS = Object.freeze({ getState: "browser-host:get-state", reloadRemote: "browser-host:reload-remote", stateChanged: "browser-host:state-changed" });

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function deepFreeze(value) { if (value && typeof value === "object" && !Object.isFrozen(value)) { for (const child of Object.values(value)) deepFreeze(child); Object.freeze(value); } return value; }
function boundedState(value) { return deepFreeze(clone(value)); }

const api = {
  getState: () => ipcRenderer.invoke(CHANNELS.getState).then(boundedState),
  reloadRemote: () => ipcRenderer.invoke(CHANNELS.reloadRemote).then(boundedState),
  onStateChanged: (callback) => {
    if (typeof callback !== "function") throw new TypeError("state_callback_required");
    const listener = (_event, state) => callback(boundedState(state));
    ipcRenderer.on(CHANNELS.stateChanged, listener);
    return () => ipcRenderer.removeListener(CHANNELS.stateChanged, listener);
  }
};

contextBridge.exposeInMainWorld("codexifyBrowserHost", Object.freeze(api));
