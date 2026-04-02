import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import GuardianActionCenter from "@/features/chat/components/GuardianActionCenter";
import {
  fetchAgentRuns,
  fetchGuardianActionCenterSnapshot,
} from "@/features/chat/api/actionCenter";
import type { GuardianActionCenterSnapshot } from "@/features/chat/api/actionCenter";
import {
  __resetAgentRunsStoreForTests,
  applyAgentRunEvent,
} from "@/features/chat/hooks/useAgentRuns";

vi.mock("@/features/chat/api/actionCenter", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/chat/api/actionCenter")
  >("@/features/chat/api/actionCenter");
  return {
    ...actual,
    fetchAgentRuns: vi.fn(),
    fetchGuardianActionCenterSnapshot: vi.fn(),
  };
});

const fetchAgentRunsMock = vi.mocked(fetchAgentRuns);
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
    __resetAgentRunsStoreForTests();
    vi.clearAllMocks();
    fetchAgentRunsMock.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
    __resetAgentRunsStoreForTests();
  });

  test(
    "renders each section heading and empty states",
    async () => {
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

      await waitFor(() => {
        expect(screen.getByText("No recent scheduled jobs")).toBeInTheDocument();
        expect(
          screen.getByText("Delegation runs unavailable without thread context")
        ).toBeInTheDocument();
        expect(screen.getByText("No pending approvals")).toBeInTheDocument();
        expect(screen.getByText("No recent task status")).toBeInTheDocument();
      });
    },
    15_000
  );

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

    await waitFor(() => {
      expect(screen.getByText("No recent task status")).toBeInTheDocument();
      expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(1);
    });
  });

  test("renders mixed section data correctly across task lifecycle events and stays read-only", async () => {
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
          availability: "empty",
          items: [],
          message: "No recent delegation runs",
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
          availability: "empty",
          items: [],
          message: "No recent task status",
        },
      })
    );

    render(<GuardianActionCenter threadId={41} />);

    expect(
      (await screen.findAllByText("Morning webhook")).length
    ).toBeGreaterThanOrEqual(2);

    act(() => {
      applyAgentRunEvent("41", {
        event_type: "task.running",
        run_id: "run_abc123",
        runtime_target: "terminal",
        thread_id: 41,
        worktree_id: "wt_001",
      });
    });

    await waitFor(() => {
      expect(screen.getAllByText("run_abc123").length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText("Running").length).toBeGreaterThanOrEqual(1);
    });

    act(() => {
      applyAgentRunEvent("41", {
        event_type: "task.completed",
        run_id: "run_abc123",
        runtime_target: "terminal",
        thread_id: 41,
        worktree_id: "wt_001",
      });
    });

    await waitFor(() => {
      expect(screen.getAllByText("run_abc123").length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText("browser.open")).toBeInTheDocument();
      expect(screen.getByText(/Reason: Needs a human check/)).toBeInTheDocument();
      expect(screen.getAllByText("Failed").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Succeeded").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Awaiting approval")).toBeInTheDocument();
    });

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
