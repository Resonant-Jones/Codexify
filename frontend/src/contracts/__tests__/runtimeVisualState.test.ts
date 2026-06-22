import { describe, expect, it } from "vitest";

import {
  PROVIDER_RUNTIME_STATES,
  LEGACY_PROVIDER_RUNTIME_STATES,
  normalizeProviderRuntimeState,
  describeProviderState,
} from "@/contracts/runtimeTokens";
import { mapRuntimeToVisualState } from "@/shared/runtimeVisualState";

// ── Canonical state vocabulary ────────────────────────────────────────────

describe("normalizeProviderRuntimeState", () => {
  it("returns distinct canonical values for all eight provider runtime states", () => {
    const results = new Set([
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.OFFLINE),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.CONNECTING),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.RUNTIME_AVAILABLE),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.MODEL_WARMING),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.READY),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.GENERATING),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.DEGRADED),
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.ERROR),
    ]);

    expect(results.size).toBe(8);
  });

  it("normalizes MODEL_WARMING to itself (not offline)", () => {
    const result = normalizeProviderRuntimeState(
      PROVIDER_RUNTIME_STATES.MODEL_WARMING
    );
    expect(result).toBe(PROVIDER_RUNTIME_STATES.MODEL_WARMING);
    expect(result).not.toBe(PROVIDER_RUNTIME_STATES.OFFLINE);
  });

  it("normalizes RUNTIME_AVAILABLE distinctly from READY", () => {
    const runtimeAvail = normalizeProviderRuntimeState(
      PROVIDER_RUNTIME_STATES.RUNTIME_AVAILABLE
    );
    const ready = normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.READY);
    expect(runtimeAvail).toBe(PROVIDER_RUNTIME_STATES.RUNTIME_AVAILABLE);
    expect(ready).toBe(PROVIDER_RUNTIME_STATES.READY);
    expect(runtimeAvail).not.toBe(ready);
  });

  it("normalizes GENERATING distinctly from READY", () => {
    const generating = normalizeProviderRuntimeState(
      PROVIDER_RUNTIME_STATES.GENERATING
    );
    const ready = normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.READY);
    expect(generating).toBe(PROVIDER_RUNTIME_STATES.GENERATING);
    expect(ready).toBe(PROVIDER_RUNTIME_STATES.READY);
    expect(generating).not.toBe(ready);
  });

  it("normalizes DEGRADED distinctly from ERROR", () => {
    const degraded = normalizeProviderRuntimeState(
      PROVIDER_RUNTIME_STATES.DEGRADED
    );
    const error = normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.ERROR);
    expect(degraded).toBe(PROVIDER_RUNTIME_STATES.DEGRADED);
    expect(error).toBe(PROVIDER_RUNTIME_STATES.ERROR);
    expect(degraded).not.toBe(error);
  });

  it("normalizes legacy ONLINE to READY", () => {
    const result = normalizeProviderRuntimeState(
      LEGACY_PROVIDER_RUNTIME_STATES.ONLINE
    );
    expect(result).toBe(PROVIDER_RUNTIME_STATES.READY);
  });

  it("normalizes legacy OFFLINE to OFFLINE", () => {
    const result = normalizeProviderRuntimeState(
      LEGACY_PROVIDER_RUNTIME_STATES.OFFLINE
    );
    expect(result).toBe(PROVIDER_RUNTIME_STATES.OFFLINE);
  });

  it("normalizes legacy DEGRADED to DEGRADED", () => {
    const result = normalizeProviderRuntimeState(
      LEGACY_PROVIDER_RUNTIME_STATES.DEGRADED
    );
    expect(result).toBe(PROVIDER_RUNTIME_STATES.DEGRADED);
  });

  it("does not normalize unknown state to READY", () => {
    const result = normalizeProviderRuntimeState("some_future_state");
    expect(result).not.toBe(PROVIDER_RUNTIME_STATES.READY);
    expect(result).toBe(PROVIDER_RUNTIME_STATES.OFFLINE);
  });

  it("does not normalize null/undefined to READY", () => {
    expect(normalizeProviderRuntimeState(null)).toBe(
      PROVIDER_RUNTIME_STATES.OFFLINE
    );
    expect(normalizeProviderRuntimeState(undefined)).toBe(
      PROVIDER_RUNTIME_STATES.OFFLINE
    );
  });

  it("does not normalize empty string to READY", () => {
    expect(normalizeProviderRuntimeState("")).toBe(
      PROVIDER_RUNTIME_STATES.OFFLINE
    );
    expect(normalizeProviderRuntimeState("   ")).toBe(
      PROVIDER_RUNTIME_STATES.OFFLINE
    );
  });

  it("maps CONNECTING to itself", () => {
    expect(
      normalizeProviderRuntimeState(PROVIDER_RUNTIME_STATES.CONNECTING)
    ).toBe(PROVIDER_RUNTIME_STATES.CONNECTING);
  });
});

describe("describeProviderState", () => {
  it("returns distinct operator-facing copy for all eight canonical states", () => {
    const states = [
      PROVIDER_RUNTIME_STATES.OFFLINE,
      PROVIDER_RUNTIME_STATES.CONNECTING,
      PROVIDER_RUNTIME_STATES.RUNTIME_AVAILABLE,
      PROVIDER_RUNTIME_STATES.MODEL_WARMING,
      PROVIDER_RUNTIME_STATES.READY,
      PROVIDER_RUNTIME_STATES.GENERATING,
      PROVIDER_RUNTIME_STATES.DEGRADED,
      PROVIDER_RUNTIME_STATES.ERROR,
    ];

    const titles = new Set(states.map((s) => describeProviderState(s).title));

    // All eight states must have distinct titles
    expect(titles.size).toBe(8);
  });

  it("produces operator-useful language for MODEL_WARMING", () => {
    const desc = describeProviderState(PROVIDER_RUNTIME_STATES.MODEL_WARMING);
    expect(desc.title.toLowerCase()).toContain("warm");
    expect(desc.detail.toLowerCase()).toContain("load");
    // Must explicitly state it is not an outage
    expect(desc.detail.toLowerCase()).toContain("not");
  });

  it("produces distinct detail for DEGRADED vs ERROR", () => {
    const degraded = describeProviderState(PROVIDER_RUNTIME_STATES.DEGRADED);
    const error = describeProviderState(PROVIDER_RUNTIME_STATES.ERROR);

    expect(degraded.title).not.toBe(error.title);
    expect(degraded.detail).not.toBe(error.detail);
    // Degraded implies still available
    expect(degraded.detail.toLowerCase()).toContain("available");
    // Error is explicit
    expect(error.detail.toLowerCase()).toContain("error");
  });

  it("handles legacy ONLINE by normalizing to READY copy", () => {
    const desc = describeProviderState(LEGACY_PROVIDER_RUNTIME_STATES.ONLINE);
    expect(desc.title).toBe("Ready");
  });
});

describe("mapRuntimeToVisualState", () => {
  it("does not classify MODEL_WARMING as offline", () => {
    const visual = mapRuntimeToVisualState(
      "awaiting_model",
      PROVIDER_RUNTIME_STATES.MODEL_WARMING
    );

    expect(visual.key).toBe("warming");
    expect(visual.label.toLowerCase()).toContain("warm");
    expect(visual.tone).not.toBe("error");
  });

  it("distinguishes MODEL_WARMING from online/ready", () => {
    const warming = mapRuntimeToVisualState(
      "awaiting_model",
      PROVIDER_RUNTIME_STATES.MODEL_WARMING
    );
    const ready = mapRuntimeToVisualState(
      "awaiting_model",
      PROVIDER_RUNTIME_STATES.READY
    );

    expect(warming.key).not.toBe(ready.key);
  });

  it("classifies ERROR as blocking terminal error state", () => {
    const visual = mapRuntimeToVisualState(
      "streaming",
      PROVIDER_RUNTIME_STATES.ERROR
    );

    expect(visual.key).toBe("error");
    expect(visual.isBlocking).toBe(true);
    expect(visual.isTerminal).toBe(true);
  });

  it("classifies DEGRADED during awaiting_model as delayed warning", () => {
    const visual = mapRuntimeToVisualState(
      "awaiting_model",
      PROVIDER_RUNTIME_STATES.DEGRADED
    );

    expect(visual.key).toBe("delayed");
    expect(visual.tone).toBe("warning");
    expect(visual.isBlocking).toBe(false);
  });

  it("classifies GENERATING during streaming as generating neutral state", () => {
    const visual = mapRuntimeToVisualState(
      "streaming",
      PROVIDER_RUNTIME_STATES.GENERATING
    );

    expect(visual.key).toBe("generating");
    expect(visual.tone).toBe("neutral");
    expect(visual.isBlocking).toBe(false);
    expect(visual.isTerminal).toBe(false);
  });

  it("accepts legacy ONLINE provider state without throwing", () => {
    const visual = mapRuntimeToVisualState(
      "awaiting_model",
      LEGACY_PROVIDER_RUNTIME_STATES.ONLINE
    );

    // Legacy ONLINE normalizes to READY — should map to starting (default awaiting_model path)
    expect(visual.key).toBe("starting");
    expect(visual.tone).not.toBe("error");
  });
});
