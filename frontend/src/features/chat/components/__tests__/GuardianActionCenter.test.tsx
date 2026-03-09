import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GuardianActionCenter from "@/features/chat/components/GuardianActionCenter";
import { fetchGuardianActionCenterSnapshot } from "@/features/chat/api/actionCenter";
import type { GuardianActionCenterSnapshot } from "@/features/chat/api/actionCenter";

vi.mock("@/features/chat/api/actionCenter", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/chat/api/actionCenter")
  >("@/features/chat/api/actionCenter");
  return {
    ...actual,
    fetchGuardianActionCenterSnapshot: vi.fn(),
  };
});

const fetchGuardianActionCenterSnapshotMock = vi.mocked(
  fetchGuardianActionCenterSnapshot
);

function buildSnapshot(
  overrides: Partial<GuardianActionCenterSnapshot> = {}
): GuardianActionCenterSnapshot {
  return {
    agentRuns: {
      availability: "empty",
      items: [],
      message: "No recent delegation runs",
    },
    pendingApprovals: {
      availability: "empty",
      items: [],
      message: "No pending approvals",
    },
    recentTaskStatus: {
      availability: "empty",
      items: [],
      message: "No recent task status",
    },
    scheduledJobs: {
      availability: "empty",
      items: [],
      message: "No recent scheduled jobs",
    },
    warnings: [],
    ...overrides,
  };
}

describe("GuardianActionCenter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders each section heading and empty states", async () => {
    fetchGuardianActionCenterSnapshotMock.mockResolvedValue(buildSnapshot());

    render(<GuardianActionCenter />);

    expect(
      await screen.findByRole("heading", { name: "Guardian Action Center" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Scheduled Jobs" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Agent / Delegation Runs" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Pending Approvals / Blocked Actions",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Recent Task Status" })
    ).toBeInTheDocument();

    expect(screen.getByText("No recent scheduled jobs")).toBeInTheDocument();
    expect(screen.getByText("No recent delegation runs")).toBeInTheDocument();
    expect(screen.getByText("No pending approvals")).toBeInTheDocument();
    expect(screen.getByText("No recent task status")).toBeInTheDocument();
  });

  test("shows unavailable state when a source is unsupported", async () => {
    fetchGuardianActionCenterSnapshotMock.mockResolvedValue(
      buildSnapshot({
        agentRuns: {
          availability: "unavailable",
          items: [],
          message: "Delegation runs unavailable without thread context",
        },
        recentTaskStatus: {
          availability: "unavailable",
          items: [],
          message: "Recent task status unavailable",
        },
      })
    );

    render(<GuardianActionCenter />);

    expect(
      await screen.findByText("Delegation runs unavailable without thread context")
    ).toBeInTheDocument();
    expect(screen.getByText("Recent task status unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(2);
  });

  test("renders mixed section data correctly and stays read-only", async () => {
    fetchGuardianActionCenterSnapshotMock.mockResolvedValue(
      buildSnapshot({
        scheduledJobs: {
          availability: "available",
          items: [
            {
              id: 7,
              isEnabled: true,
              jobType: "webhook",
              latestRunAt: "2026-03-09T10:00:00Z",
              latestRunId: 17,
              latestRunStatus: "failed",
              name: "Morning webhook",
              schedule: "@daily",
              status: "Failed",
              updatedAt: "2026-03-09T09:55:00Z",
            },
          ],
          message: "",
        },
        agentRuns: {
          availability: "available",
          items: [
            {
              rawStatus: "running",
              runId: "run_abc123",
              runtimeTarget: "terminal",
              status: "Running",
              threadId: 41,
              worktreeId: "wt_001",
              worktreePath: null,
            },
          ],
          message: "",
        },
        pendingApprovals: {
          availability: "available",
          items: [
            {
              createdAt: "2026-03-09T09:50:00Z",
              id: 99,
              operation: "browser.open",
              requestedBy: "api_key",
              requestReason: "Needs a human check",
              status: "Awaiting approval",
              target: "https://example.com",
            },
          ],
          message: "",
        },
        recentTaskStatus: {
          availability: "available",
          items: [
            {
              detail: "Schedule @daily | Run failed",
              id: "cron-run-7-17",
              label: "Morning webhook",
              source: "Scheduled job",
              status: "Failed",
              timestamp: "2026-03-09T10:00:00Z",
            },
            {
              detail: "Runtime terminal | Worktree wt_001",
              id: "agent-run-run_abc123",
              label: "run_abc123",
              source: "Delegation run",
              status: "Running",
              timestamp: null,
            },
          ],
          message: "",
        },
      })
    );

    render(<GuardianActionCenter threadId={41} />);

    expect((await screen.findAllByText("Morning webhook")).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("run_abc123").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("browser.open")).toBeInTheDocument();
    expect(screen.getByText(/Reason: Needs a human check/)).toBeInTheDocument();
    expect(screen.getAllByText("Failed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Running").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Awaiting approval")).toBeInTheDocument();

    expect(
      screen.queryByRole("button", { name: /accept|reject|approve|create/i })
    ).not.toBeInTheDocument();
  });

  test("supports reload", async () => {
    const user = userEvent.setup();

    fetchGuardianActionCenterSnapshotMock
      .mockResolvedValueOnce(buildSnapshot())
      .mockResolvedValueOnce(
        buildSnapshot({
          scheduledJobs: {
            availability: "available",
            items: [
              {
                id: 21,
                isEnabled: true,
                jobType: "noop",
                latestRunAt: null,
                latestRunId: null,
                latestRunStatus: null,
                name: "Reloaded pulse",
                schedule: "@hourly",
                status: "Idle",
                updatedAt: "2026-03-09T11:00:00Z",
              },
            ],
            message: "",
          },
        })
      );

    render(<GuardianActionCenter />);

    expect(await screen.findByText("No recent scheduled jobs")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reload action center" }));

    await waitFor(() => {
      expect(fetchGuardianActionCenterSnapshotMock).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText("Reloaded pulse")).toBeInTheDocument();
  });

  test("handles backend failure cleanly", async () => {
    fetchGuardianActionCenterSnapshotMock.mockRejectedValue(
      Object.assign(new Error("backend unavailable"), {
        response: { data: { detail: "backend unavailable" } },
      })
    );

    render(<GuardianActionCenter />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "backend unavailable"
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
