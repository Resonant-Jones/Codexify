"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const qualification = require("../scripts/qualify-macos-electron-host");
const validator = require("../scripts/validate-macos-electron-host-proof");

function minimal(passed) {
  return {
    launch: {
      exitCode: passed ? 0 : null,
      signal: passed ? null : "SIGABRT",
      readySentinel: passed,
      windowCreated: passed,
      insecureFlagsUsed: false
    },
    cleanupPassed: true
  };
}

function bundle({ passed = true, codeSigningSubsystemError = false } = {}) {
  return {
    codesign: { verificationPassed: passed },
    gatekeeper: { passed, codeSigningSubsystemError }
  };
}

function matrix(overrides = {}) {
  return {
    apple: { passed: true, gatekeeper: { passed: true, codeSigningSubsystemError: false } },
    current: { bundle: bundle(), minimal: minimal(true) },
    clean: { install: { passed: true }, bundle: bundle(), minimal: minimal(true) },
    reinstall: { attempted: false, result: "not_justified" },
    liveProof: { status: "passed", artifactCreated: true, trustedWindowCreated: true, preloadLoaded: true, trustedStateRead: true, negotiationCompatible: true, remoteRequestBeforeCompatibility: false, remoteLoadedAfterCompatibility: true, cleanupResult: "passed" },
    cleanup: { cleanupPassed: true },
    packageLockChanged: false,
    systemSecurityModified: false,
    insecureFlagsUsed: false,
    ...overrides
  };
}

test("bounded sanitization removes repository and home paths without returning secrets", () => {
  const value = qualification.sanitizeText("/Users/chriscastillo/project\nAuthorization: Bearer abcdefghijkl\nnormal diagnostic", { root: "/Users/chriscastillo/project" });
  assert.equal(value.includes("/Users/"), false);
  assert.equal(value.includes("Authorization"), false);
  assert.equal(value.includes("normal diagnostic"), true);
});

test("classification uses the Apple control comparison before naming host signing failure", () => {
  const result = qualification.classify(matrix({
    apple: { passed: false, gatekeeper: { passed: false, codeSigningSubsystemError: true } },
    current: { bundle: bundle({ passed: false, codeSigningSubsystemError: true }), minimal: minimal(false) },
    clean: { install: { passed: true }, bundle: bundle({ passed: false, codeSigningSubsystemError: true }), minimal: minimal(false) },
    liveProof: { status: "next-proof-needed" }
  }));
  assert.equal(result, "host_code_signing_subsystem_unavailable");
});

test("classification distinguishes a blocked clean download from an Electron launch failure", () => {
  assert.equal(qualification.classify(matrix({ clean: { install: { passed: false }, bundle: null, minimal: null }, liveProof: { status: "next-proof-needed" } })), "dependency_redownload_blocked");
  assert.equal(qualification.classify(matrix({ current: { bundle: bundle(), minimal: minimal(false) }, clean: { install: { passed: true }, bundle: bundle(), minimal: minimal(false) }, liveProof: { status: "next-proof-needed" } })), "minimal_electron_launch_failure_unrelated_to_codexify");
});

test("identical signature failures are required before isolating the distribution", () => {
  const failingBundle = { codesign: { verificationPassed: false, verifyStderr: "same" }, gatekeeper: { passed: false, codeSigningSubsystemError: false, stderr: "same" } };
  const result = qualification.classify(matrix({ apple: { passed: true, gatekeeper: { passed: true, codeSigningSubsystemError: false } }, current: { bundle: failingBundle, minimal: minimal(false) }, clean: { install: { passed: true }, bundle: failingBundle, minimal: minimal(false) }, liveProof: { status: "next-proof-needed" } }));
  assert.equal(result, "isolated_electron_distribution_invalid");
  const different = qualification.classify(matrix({ apple: { passed: true, gatekeeper: { passed: true, codeSigningSubsystemError: false } }, current: { bundle: failingBundle, minimal: minimal(false) }, clean: { install: { passed: true }, bundle: { codesign: { verificationPassed: false, verifyStderr: "different" }, gatekeeper: { passed: false, codeSigningSubsystemError: false, stderr: "different" } }, minimal: minimal(false) }, liveProof: { status: "next-proof-needed" } }));
  assert.equal(different, "minimal_electron_launch_failure_unrelated_to_codexify");
});

test("production entrypoint failure requires both minimal apps to pass", () => {
  const result = qualification.classify(matrix({ liveProof: { status: "next-proof-needed", artifactCreated: true } }));
  assert.equal(result, "codexify_entrypoint_launch_failure");
  const blocked = qualification.classify(matrix({ current: { bundle: bundle(), minimal: minimal(false) }, clean: { install: { passed: true }, bundle: bundle(), minimal: minimal(false) }, liveProof: { status: "next-proof-needed", artifactCreated: false } }));
  assert.equal(blocked, "minimal_electron_launch_failure_unrelated_to_codexify");
});

test("passed status is impossible without cleanup and live proof", () => {
  const ready = matrix();
  assert.equal(qualification.statusFor(ready, "qualified_host_ready"), "passed");
  assert.equal(qualification.statusFor({ ...ready, cleanup: { cleanupPassed: false } }, "qualified_host_ready"), "failed");
  assert.equal(qualification.statusFor({ ...ready, liveProof: { status: "next-proof-needed" } }, "qualified_host_ready"), "next-proof-needed");
});

test("validator rejects sensitive fields and the qualification source contains no host-policy bypass", () => {
  assert.throws(() => validator.inspectObject({ environmentDump: "x" }), /sensitive_field/);
  const source = fs.readFileSync(path.join(__dirname, "..", "scripts", "qualify-macos-electron-host.js"), "utf8");
  for (const forbidden of ["sudo", "csrutil", "--no-sandbox", "xattr', ['-d", "xattr\", [\"-d", "codesign', ['--force", "killall"]) {
    assert.equal(source.includes(forbidden), false, `forbidden command present: ${forbidden}`);
  }
});

test("cleanup summary is explicit in the proof contract", () => {
  const source = fs.readFileSync(path.join(__dirname, "..", "scripts", "qualify-macos-electron-host.js"), "utf8");
  assert.match(source, /temporaryRootRemaining/);
  assert.match(source, /supportProcessesRemaining/);
  assert.match(source, /packageLockChanged/);
});
