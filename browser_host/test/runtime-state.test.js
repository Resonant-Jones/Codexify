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
  assert.equal(first.captureImplemented, false);
  assert.equal(first.attachmentImplemented, false);
  assert.equal(first.persistenceImplemented, false);
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
