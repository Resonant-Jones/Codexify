const fs = require("node:fs");
const path = require("node:path");
const { CANDIDATE_ID, CANDIDATE_FAMILY, ELECTRON_VERSION, PLAYWRIGHT_VERSION, PACKAGER_VERSION } = require("./constants");

function loadManifest(root) {
  const manifestPath = path.join(root, "candidate-manifest.json");
  return JSON.parse(fs.readFileSync(manifestPath, "utf8"));
}

function validateManifest(root, manifest = loadManifest(root)) {
  const errors = [];
  if (manifest.candidateId !== CANDIDATE_ID) errors.push("candidateId");
  if (manifest.candidateFamily !== CANDIDATE_FAMILY) errors.push("candidateFamily");
  if (manifest.electronVersion !== ELECTRON_VERSION) errors.push("electronVersion");
  if (manifest.playwrightVersion !== PLAYWRIGHT_VERSION) errors.push("playwrightVersion");
  if (manifest.packagerVersion !== PACKAGER_VERSION) errors.push("packagerVersion");
  if (manifest.sourceRoot !== "browser_host_candidates/electron") errors.push("sourceRoot");
  if (manifest.dependencyLockPath !== "browser_host_candidates/electron/package-lock.json") errors.push("dependencyLockPath");
  if (!manifest.rendererConfiguration || manifest.rendererConfiguration.remoteRenderer.preload !== null) errors.push("remotePreload");
  if (manifest.rendererConfiguration.remoteRenderer.nodeIntegration !== false) errors.push("remoteNodeIntegration");
  if (manifest.rendererConfiguration.remoteRenderer.contextIsolation !== true) errors.push("remoteContextIsolation");
  if (manifest.rendererConfiguration.remoteRenderer.sandbox !== true) errors.push("remoteSandbox");
  if (manifest.rendererConfiguration.remoteRenderer.webviewTag !== false) errors.push("remoteWebviewTag");
  return errors;
}

function validatePackage(root) {
  const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
  const deps = packageJson.devDependencies || {};
  const expected = {
    electron: ELECTRON_VERSION,
    playwright: PLAYWRIGHT_VERSION,
    "@electron/packager": PACKAGER_VERSION
  };
  const errors = [];
  for (const [name, version] of Object.entries(expected)) {
    if (deps[name] !== version || /[<>=^~*| ]/.test(deps[name] || "")) errors.push(`dependency:${name}`);
  }
  const lockPath = path.join(root, "package-lock.json");
  if (!fs.existsSync(lockPath)) errors.push("package-lock.json");
  return { errors, packageJson };
}

module.exports = { loadManifest, validateManifest, validatePackage };
