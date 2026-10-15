import { cleanup, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WebRuntimeStartupGate from "@/components/bootstrap/WebRuntimeStartupGate";

const preflightMock = vi.fn();

vi.mock("@/lib/api", () => ({
  getBackendOutageRemainingMs: vi.fn(() => 0),
  preflightBackendAvailability: (...args: unknown[]) => preflightMock(...args),
}));

describe("WebRuntimeStartupGate", () => {
  beforeEach(() => {
    preflightMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("renders children immediately when disabled", () => {
    render(
      <WebRuntimeStartupGate enabled={false}>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    expect(screen.getByText("App shell")).toBeInTheDocument();
    expect(screen.queryByText("Waiting for the backend")).toBeNull();
  });

  it("shows a non-blocking degraded-state notice while the backend probe is failing", async () => {
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: "connect ECONNREFUSED 127.0.0.1:8888",
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    const gateTitle = await screen.findByText("Backend connection delayed");
    const gateOverlay = gateTitle.closest(".fixed");

    expect(gateTitle).toBeInTheDocument();
    expect(screen.getByText("App shell")).toBeInTheDocument();
    expect(gateOverlay).toHaveClass("z-[1300]");
    expect(gateOverlay).toHaveClass("pointer-events-none");
  });

  it("hides the degraded notice once the backend probe succeeds", async () => {
    preflightMock.mockResolvedValue({ ok: true });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    await screen.findByText("App shell");
    // The notice is only shown when ready=false; once preflight returns ok,
    // the gate clears and the notice is removed from the DOM.
    expect(screen.queryByText("Backend connection delayed")).toBeNull();
    expect(preflightMock).toHaveBeenCalled();
  });
});
