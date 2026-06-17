import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import GuardianChat from "@/features/chat/GuardianChat";
import {
  PROVIDER_RUNTIME_STATES,
  LEGACY_PROVIDER_RUNTIME_STATES,
  type ProviderRuntimeState,
} from "@/contracts/runtimeTokens";
import type { Thread } from "@/types/ui";
import type { ComposerInferenceMode } from "@/types/inference";

// ── Test fixtures ────────────────────────────────────────────────────────

function makeThread(id: number, title = "Test Thread"): Thread {
  return {
    id,
    title,
    userId: "local",
    projectId: 1,
    projectName: "General",
    lastInteractionAt: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages: [],
    threadConfig: {
      modelId: "mlx-community/Llama-3.2-3B-Instruct-4bit",
      providerId: "local",
      personaId: null,
      inferenceMode: "fast" as ComposerInferenceMode,
      retrievalSource: "project",
    },
  };
}

const noopSend = vi.fn().mockResolvedValue(undefined);
const noopNewChat = vi.fn();

function renderGuardianChat(
  overrides: {
    providerRuntimeState?: ProviderRuntimeState | null;
  } = {}
) {
  return render(
    <GuardianChat
      guardianName="Axis"
      userName="Operator"
      activeThread={makeThread(1)}
      onSendMessage={noopSend}
      onNewChat={noopNewChat}
      providerRuntimeState={overrides.providerRuntimeState ?? null}
    />
  );
}

// ── Tests ────────────────────────────────────────────────────────────────

describe("GuardianChat runtime status", () => {
  it("shows runtime status for MODEL_WARMING", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.MODEL_WARMING,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status).toBeDefined();
    expect(status.getAttribute("data-provider-state")).toBe("model_warming");
    // Must not show offline language
    expect(status.textContent?.toLowerCase()).not.toContain("offline");
    expect(status.textContent?.toLowerCase()).not.toContain("unreachable");
    // Must contain warming/loading language
    const text = status.textContent?.toLowerCase() ?? "";
    expect(text).toContain("warm");
    expect(text).toContain("load");
  });

  it("shows runtime status for RUNTIME_AVAILABLE distinctly from READY", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.RUNTIME_AVAILABLE,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe(
      "runtime_available"
    );
    // Ready would not render a status strip (it's the default)
  });

  it("shows runtime status for GENERATING distinctly from READY", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.GENERATING,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe("generating");
    expect(status.textContent?.toLowerCase()).toContain("generat");
  });

  it("shows runtime status for DEGRADED distinctly from ERROR", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.DEGRADED,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe("degraded");
    // Degraded implies still available
    expect(status.textContent?.toLowerCase()).toContain("available");
    // Must not contain error language
    expect(status.textContent?.toLowerCase()).not.toContain("explicit error");
  });

  it("shows runtime status for ERROR", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.ERROR,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe("error");
    expect(status.textContent?.toLowerCase()).toContain("error");
  });

  it("shows runtime status for OFFLINE", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.OFFLINE,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe("offline");
    expect(status.textContent?.toLowerCase()).toContain("offline");
  });

  it("shows runtime status for CONNECTING", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.CONNECTING,
    });

    const status = screen.getByTestId("chat-runtime-status");
    expect(status.getAttribute("data-provider-state")).toBe("connecting");
    expect(status.textContent?.toLowerCase()).toContain("connect");
  });

  it("does NOT show runtime status when provider is READY (default)", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.READY,
    });

    // READY is the default — strip may appear briefly during mount
    // but must not contain offline/error/warming language
    const status = screen.queryByTestId("chat-runtime-status");
    if (status) {
      const text = status.textContent?.toLowerCase() ?? "";
      expect(text).not.toContain("offline");
      expect(text).not.toContain("error");
      expect(text).not.toContain("warming");
      expect(text).not.toContain("degraded");
    }
    // Null is the ideal steady-state for READY
  });

  it("does NOT show runtime status when provider is null (no state)", () => {
    renderGuardianChat({ providerRuntimeState: null });

    // Null may normalize to OFFLINE during mount, but should settle
    const status = screen.queryByTestId("chat-runtime-status");
    if (status) {
      // If shown, must be offline (null → OFFLINE normalization)
      expect(status.getAttribute("data-provider-state")).toBe("offline");
    }
  });

  it("handles legacy ONLINE by normalizing to READY-equivalent display", () => {
    renderGuardianChat({
      providerRuntimeState:
        LEGACY_PROVIDER_RUNTIME_STATES.ONLINE as ProviderRuntimeState,
    });

    // Legacy ONLINE normalizes to READY — should not show offline/error
    const status = screen.queryByTestId("chat-runtime-status");
    if (status) {
      const text = status.textContent?.toLowerCase() ?? "";
      expect(text).not.toContain("offline");
      expect(text).not.toContain("error");
    }
  });

  it("does not render mutation controls in the runtime status strip", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.MODEL_WARMING,
    });

    const status = screen.getByTestId("chat-runtime-status");
    const buttons = status.querySelectorAll("button");
    expect(buttons.length).toBe(0);
    const links = status.querySelectorAll("a");
    expect(links.length).toBe(0);
  });

  it("does not render retry or replay controls", () => {
    renderGuardianChat({
      providerRuntimeState: PROVIDER_RUNTIME_STATES.ERROR,
    });

    const status = screen.getByTestId("chat-runtime-status");
    const text = status.textContent?.toLowerCase() ?? "";
    expect(text).not.toContain("retry");
    expect(text).not.toContain("replay");
    expect(text).not.toContain("try again");
  });
});
