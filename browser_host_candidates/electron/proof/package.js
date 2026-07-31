const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { packager } = require("@electron/packager");

const root = path.resolve(__dirname, "..");
const out = path.join(root, "package-output");
const cacheRoot = path.join(os.tmpdir(), `codexify-electron-packager-${process.pid}`);
fs.mkdirSync(cacheRoot, { recursive: true });
process.env.electron_config_cache = cacheRoot;
fs.rmSync(out, { recursive: true, force: true });

(async () => {
  const started = Date.now();
  const paths = await packager({
    dir: root,
    out,
    name: "CodexifyElectronBrowserHostProof",
    electronVersion: "43.2.0",
    download: { cacheRoot },
    platform: "darwin",
    arch: "arm64",
    overwrite: true,
    asar: true,
    prune: true,
    quiet: true,
    appVersion: "0.1.0",
    ignore: [
      /^\/node_modules/,
      /^\/proof\//,
      /^\/test\//,
      /^\/package-output\//,
      /^\/proof-output\//,
      /^\/\.git\//
    ]
  });
  const packagePath = paths[0];
  const stat = fs.statSync(packagePath);
  const result = {
    status: "passed",
    command: "npm run package",
    durationMs: Date.now() - started,
    outputPath: packagePath,
    platform: "darwin",
    arch: "arm64",
    fileCount: countFiles(packagePath),
    unpackedSizeBytes: directorySize(packagePath),
    appBundleSizeBytes: stat.isDirectory() ? directorySize(packagePath) : stat.size,
    signingState: "unsigned",
    notarizationState: "notarized",
    updaterState: "not configured",
    rollbackState: "not configured"
  };
  result.notarizationState = "not notarized";
  fs.writeFileSync(path.join(out, "package-result.json"), `${JSON.stringify(result, null, 2)}\n`);
  fs.rmSync(cacheRoot, { recursive: true, force: true });
  console.log(JSON.stringify(result, null, 2));
})().catch((error) => {
  fs.rmSync(cacheRoot, { recursive: true, force: true });
  console.error(JSON.stringify({ status: "failed", error: String(error && error.message ? error.message : error) }, null, 2));
  process.exitCode = 1;
});

function countFiles(target) {
  let count = 0;
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    const child = path.join(target, entry.name);
    count += entry.isDirectory() ? countFiles(child) : 1;
  }
  return count;
}

function directorySize(target) {
  let size = 0;
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    const child = path.join(target, entry.name);
    size += entry.isDirectory() ? directorySize(child) : fs.statSync(child).size;
  }
  return size;
}
