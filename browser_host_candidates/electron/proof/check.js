const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { loadManifest, validateManifest, validatePackage } = require("../lib/manifest");

const root = path.resolve(__dirname, "..");
const jsFiles = [
  "main.js",
  "trusted-preload.js",
  "ui/app.js",
  "proof/check.js",
  "proof/package.js",
  "proof/print-versions.js",
  "proof/run-proof.js",
  ...fs.readdirSync(path.join(root, "lib")).filter((name) => name.endsWith(".js")).map((name) => path.join("lib", name))
];
const errors = [];
for (const file of jsFiles) {
  const result = spawnSync(process.execPath, ["--check", path.join(root, file)], { encoding: "utf8" });
  if (result.status !== 0) errors.push(`${file}: syntax check failed`);
}
let manifest;
try { manifest = loadManifest(root); } catch (error) { errors.push(`manifest: ${error.message}`); }
if (manifest) errors.push(...validateManifest(root, manifest));
const packageResult = validatePackage(root);
errors.push(...packageResult.errors);
const forbidden = [
  "GUARDIAN_API_KEY",
  "production Guardian configuration",
  "src-tauri/",
  "frontend/src/",
  "Command Bus invocation"
];
for (const file of jsFiles.filter((file) => file !== "proof/check.js").concat(["candidate-manifest.json", "package.json", "README.md"])) {
  const text = fs.readFileSync(path.join(root, file), "utf8");
  for (const token of forbidden) if (text.includes(token)) errors.push(`${file}: forbidden token ${token}`);
}
if (errors.length) {
  console.error(JSON.stringify({ status: "failed", errors }, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ status: "passed", checkedFiles: jsFiles, candidateId: manifest.candidateId }, null, 2));
}
