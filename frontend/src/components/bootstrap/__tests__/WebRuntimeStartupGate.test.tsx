import { cleanup, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getBackendOutageRemainingMs: vi.fn(() => 0),
  preflightBackendAvailability: vi.fn(async () => ({
    ok: false,
    technicalDetail: "connect ECONNREFUSED 127.0.0.1:8888",
  })),
}));

import WebRuntimeStartupGate from "@/components/bootstrap/WebRuntimeStartupGate";

describe("WebRuntimeStartupGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("shows a waiting screen while the backend probe is failing", async () => {
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    expect(await screen.findByText("Waiting for the backend")).toBeInTheDocument();
    expect(screen.queryByText("App shell")).toBeNull();
  });
});
