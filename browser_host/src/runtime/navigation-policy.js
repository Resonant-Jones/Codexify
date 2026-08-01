"use strict";

function classifyNavigation(value, allowedOrigin) {
  if (typeof value !== "string" || value.length === 0 || value.length > 4096) return { allowed: false, code: "invalid_contract", reason: "url_invalid", origin: "" };
  let url;
  try { url = new URL(value); } catch { return { allowed: false, code: "invalid_contract", reason: "url_invalid", origin: "" }; }
  if (url.username || url.password) return { allowed: false, code: "permission_denied", reason: "credentials_in_url", origin: url.origin };
  if (url.protocol !== "http:") return { allowed: false, code: "unsupported_scheme", reason: "scheme_denied", origin: url.origin };
  if (url.hostname !== "127.0.0.1" || !/^\d+$/.test(url.port)) return { allowed: false, code: "origin_mismatch", reason: "numeric_loopback_required", origin: url.origin };
  if (url.origin !== allowedOrigin) return { allowed: false, code: "origin_mismatch", reason: "origin_denied", origin: url.origin };
  return { allowed: true, code: null, reason: "same_origin_loopback", origin: url.origin };
}

function isAllowedNavigation(value, allowedOrigin) { return classifyNavigation(value, allowedOrigin).allowed; }
function denialCode(value, allowedOrigin) { return classifyNavigation(value, allowedOrigin).code; }

module.exports = Object.freeze({ classifyNavigation, isAllowedNavigation, denialCode });
