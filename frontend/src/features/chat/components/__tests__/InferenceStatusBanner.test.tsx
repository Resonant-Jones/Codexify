import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";
import type { InferenceRequestState } from "@/types/inference";

function buildState(
  overrides: Partial<InferenceRequestState> = {}
): InferenceRequestState {
  return {
    phase: "idle",
    threadId: 42,
    taskId: "task-1",
    providerId: "local",
    modelId: "model-a",
    mode: "think",
    startedAt: Date.now(),
    updatedAt: Date.now(),
    statusText: null,
    detailText: null,
    errorText: null,
    canCancel: false,
    canSwitchToFast: false,
    isPendingCancel: false,
    ...overrides,
  };
}

describe("InferenceStatusBanner", () => {
  it("renders a low-emphasis active status with interruption controls", () => {
    const onCancel = vi.fn();
    const onSwitchToFast = vi.fn();

    render(
      <InferenceStatusBanner
        state={buildState({
          phase: "thinking",
          canCancel: true,
          canSwitchToFast: true,
        })}
        onCancel={onCancel}
        onSwitchToFast={onSwitchToFast}
      />
    );

    expect(screen.getByText("Thinking…")).toBeInTheDocument();
    expect(screen.getByText("This may take a few minutes.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    fireEvent.click(screen.getByRole("button", { name: "No Think" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSwitchToFast).toHaveBeenCalledTimes(1);
  });

  it("stays hidden for idle and completed states", () => {
    const { rerender } = render(
      <InferenceStatusBanner state={buildState({ phase: "idle" })} />
    );
    expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();

    rerender(<InferenceStatusBanner state={buildState({ phase: "completed" })} />);
    expect(screen.queryByText("Replying…")).not.toBeInTheDocument();
  });
});
