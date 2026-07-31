const CANDIDATE_ID = "codexify-electron-bundled-chromium-v1";
const CANDIDATE_FAMILY = "bundled_chromium_electron";
const ELECTRON_VERSION = "43.2.0";
const PLAYWRIGHT_VERSION = "1.62.1";
const PACKAGER_VERSION = "20.0.4";
const HARNESS_VERSION = "0.1.0";
const FIXTURE_VERSION = "1.0.0";
const GUARDIAN_STUB_VERSION = "0.1.0";
const MAX_CAPTURE_BYTES = 64 * 1024;
const PREVIEW_BYTES = 2400;
const EXTRACTOR_VERSION = "electron-dom-walker-v1";
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

module.exports = Object.freeze({
  CANDIDATE_ID,
  CANDIDATE_FAMILY,
  ELECTRON_VERSION,
  PLAYWRIGHT_VERSION,
  PACKAGER_VERSION,
  HARNESS_VERSION,
  FIXTURE_VERSION,
  GUARDIAN_STUB_VERSION,
  MAX_CAPTURE_BYTES,
  PREVIEW_BYTES,
  EXTRACTOR_VERSION,
  MAX_STRING_LENGTH,
  IPC_CHANNELS
});
