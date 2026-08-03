"use strict";

async function closeResource(resource) {
  if (!resource) return;
  if (typeof resource.close === "function") await resource.close();
  else if (typeof resource.cleanup === "function") await resource.cleanup();
}

async function cleanupResources(resources) {
  for (const resource of [...resources].reverse()) {
    try { await closeResource(resource); } catch { /* cleanup continues so every resource gets a chance */ }
  }
}

async function waitForExit(pid, timeoutMs = 5000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try { process.kill(pid, 0); } catch { return true; }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  return false;
}

module.exports = Object.freeze({ closeResource, cleanupResources, waitForExit });
