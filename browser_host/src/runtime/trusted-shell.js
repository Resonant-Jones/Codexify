"use strict";

const path = require("node:path");

const TRUSTED_SHELL_PREFERENCES = Object.freeze({ nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true, webviewTag: false });

function trustedShellBounds(window) {
  const bounds = window.getContentBounds();
  return { x: 0, y: 104, width: bounds.width, height: Math.max(0, bounds.height - 104) };
}

function createTrustedShell({ BrowserWindow, preloadPath, shellPath, onDidFinishLoad, onResize }) {
  const window = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 720,
    minHeight: 520,
    title: "Codexify Browser Host",
    webPreferences: { ...TRUSTED_SHELL_PREFERENCES, preload: path.resolve(preloadPath) }
  });
  const resize = () => onResize?.(trustedShellBounds(window));
  window.on("resize", resize);
  window.webContents.on("did-finish-load", () => onDidFinishLoad?.(window));
  window.loadFile(path.resolve(shellPath));
  return Object.freeze({ window, bounds: trustedShellBounds, resize, destroy: () => { window.removeListener("resize", resize); if (!window.isDestroyed()) window.destroy(); } });
}

module.exports = Object.freeze({ TRUSTED_SHELL_PREFERENCES, trustedShellBounds, createTrustedShell });
