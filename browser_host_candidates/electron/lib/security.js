const { IPC_CHANNELS, MAX_STRING_LENGTH } = require("./constants");

const FIXTURE_PATHS = Object.freeze(new Set([
  "/basic-visible",
  "/prompt-injection",
  "/form-secret",
  "/cross-origin-iframe",
  "/origin-b-iframe-body",
  "/oversized",
  "/navigation-race",
  "/origin-change",
  "/popup-attempt",
  "/download-attempt",
  "/renderer-failure",
  "/protected-target",
  "/download-test.txt",
  "/manifest.json",
  "/health"
]));

function parseOrigin(value) {
  const url = new URL(value);
  if (!url.protocol || !url.hostname) throw new Error("origin_parse_failed");
  return `${url.protocol}//${url.hostname}${url.port ? `:${url.port}` : ""}`;
}

function isAllowedFixtureUrl(value, origins) {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:") return false;
    if (!origins.includes(url.origin)) return false;
    return FIXTURE_PATHS.has(url.pathname) && !url.search && !url.hash;
  } catch {
    return false;
  }
}

function isProtectedTarget(value) {
  return value === "codexify-harness://protected/synthetic";
}

function boundedString(value, field) {
  if (typeof value !== "string" || value.length === 0 || value.length > MAX_STRING_LENGTH) {
    throw new Error(`${field}_invalid`);
  }
  return value;
}

function assertTrustedSender(event, trustedId) {
  if (!event || !event.sender || event.sender.id !== trustedId) {
    throw new Error("trusted_sender_rejected");
  }
  const frameUrl = event.senderFrame && event.senderFrame.url;
  if (typeof frameUrl !== "string" || !frameUrl.startsWith("file://")) {
    throw new Error("trusted_frame_rejected");
  }
}

function assertEmptyArgs(args) {
  if (args !== undefined && args !== null && (typeof args !== "object" || Array.isArray(args))) {
    throw new Error("argument_shape_rejected");
  }
}

function assertRunId(args, runId) {
  if (args && args.runId !== undefined && args.runId !== runId) throw new Error("run_id_rejected");
}

module.exports = {
  FIXTURE_PATHS,
  IPC_CHANNELS,
  parseOrigin,
  isAllowedFixtureUrl,
  isProtectedTarget,
  boundedString,
  assertTrustedSender,
  assertEmptyArgs,
  assertRunId
};
