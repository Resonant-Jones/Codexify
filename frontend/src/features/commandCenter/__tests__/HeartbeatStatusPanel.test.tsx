import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import * as React from "react";

import HeartbeatStatusPanel from "@/features/commandCenter/HeartbeatStatusPanel";
import type { HeartbeatStatusResponse } from "@/features/commandCenter/api";

// Mock the hook
const mockStatus = vi.fn();
vi.mock("@/features/commandCenter/hooks/useHeartbeatStatus", () => ({
  default: () => mockStatus(),
}));

function makeStatus(overrides: Partial<HeartbeatStatusResponse> = {}): ReturnType<typeof mockStatus> {
  return {
    status: {
      latest_date: "2026-05-14",
      heartbeat_report_path: "docs/Heartbeat/generated/2026-05-14-heartbeat.md",
      staged_outbox_path: "docs/Heartbeat/staged/2026-05-14",
      review_status: "passed",
      outbox_status: "passed",
      publication_enabled: false,
      publication_targets: [],
      generated_files: ["a.md", "b.md", "release-summary.md"],
      warnings: [],
      failures: [],
      manual_commands: ["make heartbeat-full FORCE=1"],
      ...overrides,
    } satisfies HeartbeatStatusResponse,
    loading: false,
    error: null,
    lastCheckedAt: Date.now(),
    refresh: vi.fn(),
  };
}

describe("HeartbeatStatusPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders passed status successfully", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText("Heartbeat Status")).toBeInTheDocument();
    expect(screen.getByText("2026-05-14")).toBeInTheDocument();
    // Both review + outbox may render "Passed" — use getAllByText
    const passed = screen.getAllByText("Passed");
    expect(passed.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Read-only")).toBeInTheDocument();
    expect(screen.getByText("Manual-only")).toBeInTheDocument();
    expect(screen.getByText("Publishing disabled")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
  });

  it("shows manual command hint", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText("Manual command")).toBeInTheDocument();
    expect(screen.getByText(/make heartbeat-full/)).toBeInTheDocument();
  });

  it("renders missing status gracefully", () => {
    mockStatus.mockReturnValue(makeStatus({
      latest_date: null,
      review_status: "missing",
      outbox_status: "missing",
      generated_files: [],
    }));

    render(<HeartbeatStatusPanel enabled />);

    // Both review + outbox render "Missing" — expect at least 2
    const missing = screen.getAllByText("Missing");
    expect(missing.length).toBeGreaterThanOrEqual(2);
    // Should still render, not crash
    expect(screen.getByText("Heartbeat Status")).toBeInTheDocument();
  });

  it("renders warning status", () => {
    mockStatus.mockReturnValue(makeStatus({
      review_status: "warning",
      outbox_status: "warning",
      warnings: ["Review gate was skipped"],
    }));

    render(<HeartbeatStatusPanel enabled />);

    // Warning badge should appear (two: review + outbox)
    const warnings = screen.getAllByText("Warning");
    expect(warnings.length).toBeGreaterThanOrEqual(1);
    // Warning text is rendered with bullet prefix: "• Review gate was skipped"
    expect(document.body).toHaveTextContent("Review gate was skipped");
  });

  it("renders failed status with failures", () => {
    mockStatus.mockReturnValue(makeStatus({
      review_status: "failed",
      outbox_status: "failed",
      failures: ["Step failed: Beta Release Sentinel"],
    }));

    render(<HeartbeatStatusPanel enabled />);

    const faileds = screen.getAllByText("Failed");
    expect(faileds.length).toBeGreaterThanOrEqual(1);
    // Failure text is rendered with bullet prefix: "• Step failed: Beta Release Sentinel"
    expect(document.body).toHaveTextContent("Step failed: Beta Release Sentinel");
  });

  it("shows publication disabled label", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText("Publishing disabled")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
  });

  it("does not render run/publish/schedule buttons", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled />);

    // No buttons with "Run", "Publish", "Schedule" labels
    const buttons = screen.queryAllByRole("button");
    for (const btn of buttons) {
      const text = btn.textContent?.toLowerCase() ?? "";
      expect(text).not.toContain("run heartbeat");
      expect(text).not.toContain("publish");
      expect(text).not.toContain("schedule");
    }
  });

  it("shows staged file count", () => {
    mockStatus.mockReturnValue(makeStatus({ generated_files: ["a.md", "b.md", "c.md"] }));

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows deferred note", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText(/Agent Command Center execution deferred/)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockStatus.mockReturnValue({ status: null, loading: true, error: null, lastCheckedAt: null, refresh: vi.fn() });

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("shows error state with retry", () => {
    mockStatus.mockReturnValue({ status: null, loading: false, error: "Network error", lastCheckedAt: null, refresh: vi.fn() });

    render(<HeartbeatStatusPanel enabled />);

    expect(screen.getByText(/Network error/)).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("renders disabled state when not enabled", () => {
    mockStatus.mockReturnValue(makeStatus());

    render(<HeartbeatStatusPanel enabled={false} />);

    expect(screen.getByText("Heartbeat status not enabled.")).toBeInTheDocument();
  });
});
