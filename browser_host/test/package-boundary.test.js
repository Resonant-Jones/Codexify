"use strict";

const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const boundary = require("../src/package-boundary");
const packageManifest = require("../package.json");
const contractPackage = require("../contracts/package.json");

const root = path.resolve(__dirname, "..");

test("production package identity and local contract ownership are explicit", () => {
  assert.equal(boundary.packageName, "@codexify/browser-host");
  assert.equal(boundary.componentVersion, "0.1.0");
  assert.equal(boundary.contractPackageName, "@codexify/browser-host-contracts");
  assert.equal(boundary.contractPackageVersion, "0.2.0");
  assert.equal(packageManifest.private, true);
  assert.equal(contractPackage.private, true);
  assert.equal(packageManifest.dependencies["@codexify/browser-host-contracts"], "file:./contracts");
  assert.deepEqual(Object.keys(packageManifest.dependencies), ["@codexify/browser-host-contracts"]);
});

test("the bounded runtime and capture transport are implemented while release features remain closed", () => {
  for (const key of ["runtimeImplemented", "rendererImplemented", "navigationImplemented"]) {
    assert.equal(boundary[key], true, key);
  }
  assert.equal(boundary.captureImplemented, true);
  assert.equal(boundary.attachmentTransportImplemented, true);
  for (const key of ["persistenceImplemented", "updaterImplemented", "releaseImplemented"]) assert.equal(boundary[key], false, key);
  assert.equal(boundary.releasePosture, "development/internal unsigned proof");
  assert.equal(Object.isFrozen(boundary), true);
});

test("the package boundary contains no browser runtime or transport implementation", () => {
  const source = fs.readFileSync(path.join(root, "src/package-boundary.js"), "utf8");
  for (const forbidden of [
    "electron",
    "playwright",
    "BrowserWindow",
    "fetch(",
    "http://",
    "https://",
    "process.env",
    "browser_host_candidates",
    "src-tauri",
    "frontend",
    "guardian"
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});
