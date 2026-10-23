import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InferenceStatusBanner } from "@/features/chat/components/InferenceStatusBanner";
import {
  createIdleInferenceRequestState,
  type InferenceRequestState,
} from "@/types/inference";

/**
 * MOB-G2-TASK-1 — phone lifecycle legibility.
 *
 * The request state machine already distinguishes queued, model warmup,
 * first-token wait, streaming, and degraded observation. The banner used to
 * collapse the first three into a single "Working…" label, and its diagnostic
 * detail was rendered inside `hidden … sm:inline`, so on a phone the
 * degraded/uncertainty text was never shown at all.
 *
 * These tests pin the corrected phone contract and prove desktop is unchanged.
 */

const DEGRADED_DETAIL =
  "Provider visibility is degraded; still waiting for a terminal task event.";

function state(overrides: Partial<InferenceRequestState>): InferenceRequestState {
  return {
    ...createIdleInferenceRequestState(),
    threadId: 42,
    taskId: "task-42",
    providerId: "local",
    modelId: "local-chat",
    startedAt: 1,
    updatedAt: 2,
    canCancel: true,
    ...overrides,
  };
}

describe("inference status banner on a phone shell", () => {
  it("names the canonical lifecycle stage instead of a single Working label", () => {
    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({
          phase: "sending",
          statusText: "Warming model…",
          detailText: "Guardian is warming the selected model.",
        })}
      />
    );

    expect(screen.getByText("Warming model…")).toBeInTheDocument();
    expect(screen.queryByText("Working…")).toBeNull();
  });

  it.each([
    ["Queued…", "Queued…"],
    ["Warming model…", "Warming model…"],
    ["Waiting for first token…", "Waiting for first token…"],
    ["Provider degraded…", "Provider degraded…"],
  ])("distinguishes %s from every other stage", (stage, expected) => {
    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({ phase: "sending", statusText: stage })}
      />
    );

    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it("shows the degraded observation detail on a phone", () => {
    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({
          phase: "sending",
          statusText: "Provider degraded…",
          detailText: DEGRADED_DETAIL,
        })}
      />
    );

    const detail = screen.getByText(DEGRADED_DETAIL);
    expect(detail).toBeInTheDocument();
    // The phone renders the detail as a visible line, not a desktop-only
    // `hidden … sm:inline` span.
    expect(detail.className).not.toContain("hidden");
  });

  it("keeps the desktop detail inside the desktop-only span", () => {
    render(
      <InferenceStatusBanner
        state={state({
          phase: "sending",
          statusText: "Provider degraded…",
          detailText: DEGRADED_DETAIL,
        })}
      />
    );

    expect(screen.getByText(DEGRADED_DETAIL).className).toContain("hidden");
  });

  it("keeps the coarse phase label on desktop", () => {
    render(
      <InferenceStatusBanner
        state={state({
          phase: "sending",
          statusText: "Warming model…",
          detailText: "Guardian is warming the selected model.",
        })}
      />
    );

    expect(screen.getByText("Working…")).toBeInTheDocument();
    expect(screen.queryByText("Warming model…")).toBeNull();
  });

  it("falls back to the phase label when no canonical stage is available", () => {
    render(
      <InferenceStatusBanner isPhoneShell state={state({ phase: "thinking" })} />
    );

    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("keeps the terminal labels unchanged on a phone", () => {
    const { unmount } = render(
      <InferenceStatusBanner isPhoneShell state={state({ phase: "failed" })} />
    );
    expect(screen.getByText("Reply failed")).toBeInTheDocument();
    unmount();

    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({
          phase: "completed",
          // A completed phase is only surfaced when latency metrics exist.
          latencyMetrics: [{ label: "Time to first token", value: "820ms" }],
        })}
      />
    );
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("reports a pending stop without naming a stage", () => {
    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({
          phase: "sending",
          statusText: "Warming model…",
          isPendingCancel: true,
        })}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText("Stopping…")).toBeInTheDocument();
  });

  it("never presents observation loss as a failed execution", () => {
    // Observation loss is reported by the attempt-observation surface, which
    // states that the request outcome has not changed. The banner must not
    // assert failure on its own.
    render(
      <InferenceStatusBanner
        isPhoneShell
        state={state({
          phase: "sending",
          statusText: "Waiting for first token…",
          detailText: DEGRADED_DETAIL,
        })}
      />
    );

    expect(screen.queryByText("Reply failed")).toBeNull();
    expect(screen.getByText("Waiting for first token…")).toBeInTheDocument();
  });
});
