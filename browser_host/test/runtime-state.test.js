"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createRuntimeState } = require("../src/runtime/runtime-state");
const { metadata } = require("../src/runtime/config");

test("runtime state is bounded, cloned, frozen, and explicitly redacted", () => {
  const state = createRuntimeState(metadata());
  const first = state.snapshot();
  assert.equal(Object.isFrozen(first), true);
  assert.equal(Object.isFrozen(first.selectedVersions), true);
  assert.equal(first.topologySkeletonImplemented, true);
  assert.equal(first.captureImplemented, true);
  assert.equal(first.attachmentImplemented, true);
  assert.equal(first.persistenceImplemented, false);
  assert.equal(first.attachmentTransport, "deterministic_stub");
  assert.equal(first.attachmentCredentialPosture, "no_reusable_guardian_credential");
  assert.equal(first.attachmentGrantAvailable, false);
  assert.equal(first.attachmentGrantConsumed, false);
  assert.equal(first.lastGuardianAttachmentHttpStatus, null);
  assert.equal(first.negotiationTransport, "deterministic_stub");
  assert.equal(first.guardianNegotiationAdapterEnabled, false);
  assert.equal(first.negotiationCredentialPosture, "no_credential_required_local_development_negotiation");
  assert.equal(first.guardianNegotiationHttpStatus, null);
  assert.equal("proofToken" in first, false);
  assert.equal("credentials" in first, false);
  assert.equal("pageBody" in first, false);
  const received = [];
  const unsubscribe = state.subscribe((next) => received.push(next));
  state.update({ runtimeStatus: "negotiating", negotiationRequestId: "request-1" });
  unsubscribe();
  state.update({ runtimeStatus: "degraded", errorCode: "guardian_rejected" });
  assert.equal(received.length, 1);
  assert.equal(received[0].runtimeStatus, "negotiating");
  assert.throws(() => state.update({ errorCode: "not-a-canonical-error" }), /state_error_code_invalid/);
});

test("runtime state exposes only bounded Guardian adapter posture", () => {
  const state = createRuntimeState({
    ...metadata(),
    guardianAttachmentAdapterEnabled: true,
    guardianAttachmentOrigin: "http://127.0.0.1:43125",
    guardianNegotiationAdapterEnabled: true,
    negotiationTransport: "guardian_dev_adapter",
    guardianNegotiationOrigin: "http://127.0.0.1:43125",
    browserHostInstanceId: "browser-host-state-test",
    guardianAttachmentGrantAvailable: true
  });
  const snapshot = state.snapshot();
  assert.equal(snapshot.attachmentTransport, "guardian_dev_adapter");
  assert.equal(snapshot.negotiationTransport, "guardian_dev_adapter");
  assert.equal(snapshot.guardianAttachmentAdapterEnabled, true);
  assert.equal(snapshot.guardianNegotiationAdapterEnabled, true);
  assert.equal(snapshot.guardianNegotiationOrigin, "http://127.0.0.1:43125");
  assert.equal(snapshot.guardianAttachmentOrigin, "http://127.0.0.1:43125");
  assert.equal(snapshot.browserHostInstanceId, "browser-host-state-test");
  assert.equal(snapshot.attachmentGrantAvailable, true);
  assert.equal(snapshot.attachmentGrantConsumed, false);
  assert.equal("grantBearer" in snapshot, false);
  assert.equal("guardianApiKey" in snapshot, false);
});
