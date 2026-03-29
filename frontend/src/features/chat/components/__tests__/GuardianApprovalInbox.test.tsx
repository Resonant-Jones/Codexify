import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import GuardianApprovalInbox from "@/features/chat/components/GuardianApprovalInbox";
import { fetchAgentRuns } from "@/features/chat/api/actionCenter";
import { fetchGuardianApprovalInboxSnapshot } from "@/features/chat/api/approvalInbox";
import type { GuardianApprovalInboxSnapshot } from "@/features/chat/api/approvalInbox";
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
  };
});

vi.mock("@/features/chat/api/approvalInbox", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/chat/api/approvalInbox")
  >("@/features/chat/api/approvalInbox");
  return {
    ...actual,
    fetchGuardianApprovalInboxSnapshot: vi.fn(),
  };
});

const fetchGuardianApprovalInboxSnapshotMock = vi.mocked(
  fetchGuardianApprovalInboxSnapshot
);
const fetchAgentRunsMock = vi.mocked(fetchAgentRuns);

function buildSnapshot(
  overrides: Partial<GuardianApprovalInboxSnapshot> = {}
): GuardianApprovalInboxSnapshot {
  return {
    awaitingApprovals: {
      availability: "empty",
      items: [],
      message: "No pending approvals",
    },
    blockedActions: {
      availability: "empty",
      items: [],
      message: "No blocked actions",
    },
    clarificationNeeded: {
      availability: "empty",
      items: [],
      message: "No clarification-needed items",
    },
    escalatedItems: {
      availability: "empty",
      items: [],
      message: "No escalation items",
    },
    warnings: [],
    ...overrides,
  };
}

describe("GuardianApprovalInbox", () => {
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
    "renders inbox heading and core sections",
    async () => {
      fetchGuardianApprovalInboxSnapshotMock.mockResolvedValue(buildSnapshot());

      render(<GuardianApprovalInbox />);

      expect(
        await screen.findByRole("heading", { name: "Guardian Approval Inbox" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "Awaiting Approval" })
      ).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Blocked" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Escalated" })).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "Clarification Needed" })
      ).toBeInTheDocument();
    },
    15_000
  );

  test("shows empty state when there are no pending items", async () => {
    fetchGuardianApprovalInboxSnapshotMock.mockResolvedValue(buildSnapshot());

    render(<GuardianApprovalInbox />);

    expect(await screen.findByText("No pending approvals")).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText("Blocked actions unavailable without thread context")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Escalation items unavailable without thread context")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Clarification items unavailable without thread context")
      ).toBeInTheDocument();
    });
  });

  test("shows unavailable state when sources are unsupported", async () => {
    fetchGuardianApprovalInboxSnapshotMock.mockResolvedValue(
      buildSnapshot({
        awaitingApprovals: {
          availability: "unavailable",
          items: [],
          message: "Pending approvals unavailable",
        },
        blockedActions: {
          availability: "unavailable",
          items: [],
          message: "Blocked actions unavailable without thread context",
        },
        escalatedItems: {
          availability: "unavailable",
          items: [],
          message: "Escalation items unavailable without thread context",
        },
        clarificationNeeded: {
          availability: "unavailable",
          items: [],
          message: "Clarification items unavailable without thread context",
        },
      })
    );

    render(<GuardianApprovalInbox />);

    expect(await screen.findByText("Approval inbox unavailable")).toBeInTheDocument();
    expect(screen.getByText("Pending approvals unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("Blocked actions unavailable without thread context")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Escalation items unavailable without thread context")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Clarification items unavailable without thread context")
    ).toBeInTheDocument();
  });

  test("renders mixed pending items correctly from emitted run events", async () => {
    fetchGuardianApprovalInboxSnapshotMock.mockResolvedValue(
      buildSnapshot({
        awaitingApprovals: {
          availability: "available",
          items: [
            {
              createdAt: "2026-03-09T10:00:00Z",
              href: null,
              id: "approval-42",
              runId: null,
              sourceType: "Browser approval",
              status: "Awaiting approval",
              summary: "Target https://example.com | Reason confirm destructive action",
              taskId: null,
              threadId: null,
              title: "browser.click",
              updatedAt: null,
            },
          ],
          message: "",
        },
        blockedActions: {
          availability: "empty",
          items: [],
          message: "No blocked actions",
        },
        escalatedItems: {
          availability: "empty",
          items: [],
          message: "No escalation items",
        },
        clarificationNeeded: {
          availability: "empty",
          items: [],
          message: "No clarification-needed items",
        },
      })
    );

    render(<GuardianApprovalInbox threadId={81} />);

    expect(await screen.findByText("browser.click")).toBeInTheDocument();

    act(() => {
      applyAgentRunEvent("81", {
        run_id: "run_blocked",
        runtime_target: "terminal",
        status: "blocked",
        thread_id: 81,
      });
      applyAgentRunEvent("81", {
        run_id: "run_failed",
        runtime_target: "container",
        status: "failed",
        thread_id: 81,
      });
      applyAgentRunEvent("81", {
        run_id: "run_clarify",
        runtime_target: "terminal",
        status: "clarification_needed",
        thread_id: 81,
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Run run_blocked")).toBeInTheDocument();
      expect(screen.getByText("Run run_failed")).toBeInTheDocument();
      expect(screen.getByText("Run run_clarify")).toBeInTheDocument();
      expect(screen.getByText("Source: Browser approval")).toBeInTheDocument();
      expect(screen.getAllByText("Source: Delegation run").length).toBeGreaterThanOrEqual(3);
      expect(screen.getAllByText("Awaiting approval").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Blocked").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Escalated").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Clarification needed").length).toBeGreaterThanOrEqual(1);
    });

    expect(
      screen.queryByRole("button", { name: /approve|reject|accept|deny|create/i })
    ).not.toBeInTheDocument();
  });

  test("supports reload", async () => {
    const user = userEvent.setup();

    fetchGuardianApprovalInboxSnapshotMock
      .mockResolvedValueOnce(buildSnapshot())
      .mockResolvedValueOnce(
        buildSnapshot({
          awaitingApprovals: {
            availability: "available",
            items: [
              {
                createdAt: "2026-03-09T11:00:00Z",
                href: null,
                id: "approval-84",
                runId: null,
                sourceType: "Browser approval",
                status: "Awaiting approval",
                summary: "Target https://example.net | Reason manual review",
                taskId: null,
                threadId: null,
                title: "browser.navigate",
                updatedAt: null,
              },
            ],
            message: "",
          },
        })
      );

    render(<GuardianApprovalInbox />);

    expect(await screen.findByText("No pending approvals")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reload inbox" }));

    await waitFor(() => {
      expect(fetchGuardianApprovalInboxSnapshotMock).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText("browser.navigate")).toBeInTheDocument();
  });

  test("handles backend failure cleanly", async () => {
    fetchGuardianApprovalInboxSnapshotMock.mockRejectedValue(
      Object.assign(new Error("inbox backend unavailable"), {
        response: { data: { detail: "inbox backend unavailable" } },
      })
    );

    render(<GuardianApprovalInbox />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "inbox backend unavailable"
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
