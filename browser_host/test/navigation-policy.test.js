"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { classifyNavigation, isAllowedNavigation, denialCode } = require("../src/runtime/navigation-policy");

const origin = "http://127.0.0.1:43123";

test("same-origin numeric-loopback fixture navigation is allowed", () => {
  assert.equal(isAllowedNavigation(`${origin}/secondary?case=one`, origin), true);
  assert.deepEqual(classifyNavigation(`${origin}/secondary`, origin), { allowed: true, code: null, reason: "same_origin_loopback", origin });
});

test("aliases, public origins, credentials, and dangerous schemes are denied", () => {
  const denied = [
    ["http://localhost:43123/", "origin_mismatch"],
    ["http://127.0.0.1:43124/", "origin_mismatch"],
    ["https://127.0.0.1:43123/", "unsupported_scheme"],
    ["file:///tmp/proof", "unsupported_scheme"],
    ["data:text/html,proof", "unsupported_scheme"],
    ["blob:http://127.0.0.1:43123/id", "unsupported_scheme"],
    ["javascript:alert(1)", "unsupported_scheme"],
    ["http://user:pass@127.0.0.1:43123/", "permission_denied"]
  ];
  for (const [url, code] of denied) assert.equal(denialCode(url, origin), code, url);
});
