import { describe, expect, it } from "vitest";

import {
  RUNTIME_STATUS_PRESENTATIONS,
  describeRuntimeStatusPresentation,
} from "@/contracts/runtimeTokens";

const EXPECTED_RUNTIME_STATUS_PRESENTATIONS = {
  healthy: { label: "healthy", tone: "active", isFallback: false },
  degraded: { label: "degraded", tone: "attention", isFallback: false },
  unknown: { label: "unknown", tone: "subtle", isFallback: false },
  active: { label: "active", tone: "active", isFallback: false },
  stale: { label: "stale", tone: "attention", isFallback: false },
  offline: { label: "offline", tone: "danger", isFallback: false },
  online: { label: "online", tone: "active", isFallback: false },
  running: { label: "running", tone: "info", isFallback: false },
  queued: { label: "queued", tone: "neutral", isFallback: false },
  open: { label: "open", tone: "active", isFallback: false },
  connecting: { label: "connecting", tone: "info", isFallback: false },
  closed: { label: "closed", tone: "subtle", isFallback: false },
  error: { label: "error", tone: "danger", isFallback: false },
  OK: { label: "OK", tone: "active", isFallback: false },
  FAIL: { label: "FAIL", tone: "danger", isFallback: false },
  UNKNOWN: { label: "UNKNOWN", tone: "subtle", isFallback: false },
  attention: { label: "attention", tone: "attention", isFallback: false },
  needs_attention: { label: "needs attention", tone: "attention", isFallback: false },
  succeeded: { label: "succeeded", tone: "active", isFallback: false },
  failed: { label: "failed", tone: "danger", isFallback: false },
  unauthorized: { label: "unauthorized", tone: "attention", isFallback: false },
} as const;

const FALLBACK_PRESENTATION = {
  label: "unknown",
  tone: "subtle",
  isFallback: true,
} as const;

describe("runtimeTokens contract", () => {
  it("keeps the runtime status registry bounded and explicit", () => {
    expect(RUNTIME_STATUS_PRESENTATIONS).toEqual(
      EXPECTED_RUNTIME_STATUS_PRESENTATIONS
    );
  });

  it("resolves canonical runtime statuses through the presentation helper", () => {
    for (const [status, presentation] of Object.entries(
      EXPECTED_RUNTIME_STATUS_PRESENTATIONS
    )) {
      expect(describeRuntimeStatusPresentation(status)).toEqual(presentation);
    }
  });

  it("keeps case handling explicit and trim-only", () => {
    expect(describeRuntimeStatusPresentation(" degraded ")).toEqual(
      EXPECTED_RUNTIME_STATUS_PRESENTATIONS.degraded
    );
    expect(describeRuntimeStatusPresentation("Degraded")).toEqual({
      label: "Degraded",
      tone: "subtle",
      isFallback: true,
    });
  });

  it("returns visible fallback presentations for unmapped and empty inputs", () => {
    for (const input of [null, undefined, "", "   "]) {
      expect(describeRuntimeStatusPresentation(input)).toEqual(
        FALLBACK_PRESENTATION
      );
    }

    const fallback = describeRuntimeStatusPresentation("mystery_signal");
    expect(fallback).toEqual({
      label: "mystery signal",
      tone: "subtle",
      isFallback: true,
    });
    expect(fallback.tone).not.toBe(EXPECTED_RUNTIME_STATUS_PRESENTATIONS.healthy.tone);
  });

  it("does not treat prototype-chain names as registered statuses", () => {
    expect(describeRuntimeStatusPresentation("constructor")).toEqual({
      label: "constructor",
      tone: "subtle",
      isFallback: true,
    });
  });
});
