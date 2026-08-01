"use strict";

const contractPackage = require("../../contracts");

const FEATURE_TOKENS = Object.freeze(contractPackage.tokens.featureIdentifiers.slice());

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function createRuntimeState(metadata) {
  const state = {
    runtimeStatus: "starting",
    packageVersion: metadata.packageVersion,
    contractPackageVersion: metadata.contractPackageVersion,
    protocolVersion: metadata.protocolVersion,
    envelopeVersion: metadata.envelopeVersion,
    attachmentVersion: metadata.attachmentVersion,
    releasePosture: metadata.releasePosture,
    guardianCompatibilityOutcome: "pending",
    negotiationRequestId: null,
    selectedVersions: { protocol: null, envelope: null, attachment: null },
    enabledFeatures: [],
    disabledFeatures: FEATURE_TOKENS.map((feature) => ({ feature, reason: "not_supported" })),
    remoteStatus: "not_created",
    remoteUrl: "",
    remoteOrigin: "",
    remoteTitle: "",
    remoteLoadingState: "idle",
    remoteProcessState: "not_started",
    remoteViewCreated: false,
    remoteLoadedAfterNegotiation: false,
    lastPolicyDecision: "",
    errorCode: null,
    topologySkeletonImplemented: true,
    captureImplemented: false,
    attachmentImplemented: false,
    persistenceImplemented: false,
    liveGuardianImplemented: false,
    updaterImplemented: false,
    releaseQualified: false
  };
  const subscribers = new Set();

  function snapshot() { return deepFreeze(clone(state)); }

  function update(patch = {}) {
    for (const [key, value] of Object.entries(patch)) {
      if (!Object.prototype.hasOwnProperty.call(state, key)) throw new Error(`state_field_invalid:${key}`);
      if (key === "errorCode" && value !== null && !contractPackage.tokens.errorCodes.includes(value)) throw new Error("state_error_code_invalid");
      state[key] = clone(value);
    }
    const next = snapshot();
    for (const subscriber of [...subscribers]) subscriber(next);
    return next;
  }

  function subscribe(callback) {
    if (typeof callback !== "function") throw new TypeError("state_callback_required");
    subscribers.add(callback);
    return () => subscribers.delete(callback);
  }

  return Object.freeze({ snapshot, update, subscribe });
}

module.exports = Object.freeze({ createRuntimeState, clone, deepFreeze, FEATURE_TOKENS });
