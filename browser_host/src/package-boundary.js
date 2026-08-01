"use strict";

const packageManifest = require("../package.json");
const contractPackage = require("../contracts/package.json");
const contractManifest = require("../contracts/manifest.json");

module.exports = Object.freeze({
  packageName: packageManifest.name,
  componentVersion: packageManifest.version,
  contractPackageName: contractPackage.name,
  contractPackageVersion: contractPackage.version,
  protocolVersion: contractManifest.protocol.currentVersion,
  envelopeVersion: contractManifest.browserContextEnvelope.currentVersion,
  attachmentVersion: contractManifest.contextAttachment.currentVersion,
  releasePosture: "development/internal unsigned proof",
  runtimeImplemented: true,
  rendererImplemented: true,
  navigationImplemented: true,
  captureImplemented: false,
  attachmentTransportImplemented: false,
  persistenceImplemented: false,
  updaterImplemented: false,
  releaseImplemented: false
});
