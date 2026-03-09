import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GuardianThreadApprovalRail from "@/features/chat/components/GuardianThreadApprovalRail";
import useGuardianThreadApprovalRail, {
  type UseGuardianThreadApprovalRailResult,
} from "@/features/chat/hooks/useGuardianThreadApprovalRail";
import type { GuardianThreadIntervention } from "@/features/chat/api/threadApprovals";

vi.mock("@/features/chat/hooks/useGuardianThreadApprovalRail", () => ({
  default: vi.fn(),
}));

const useGuardianThreadApprovalRailMock = vi.mocked(useGuardianThreadApprovalRail);

function buildIntervention(
  overrides: Partial<GuardianThreadIntervention> = {}
): GuardianThreadIntervention {
  return {
    canRedirect: true,
    decision: {
      approvalId: null,
      supported: false,
    },
    details: ["Run: run_123", "Raw status: approval_required"],
    id: "42:run_123",
    kind: "approval_required",
    rawStatus: "approval_required",
    redirectPrompt: "Guardian, do this instead for run run_123: ",
    runId: "run_123",
    statusLabel: "Approval required",
    summary:
      "A guarded action for this thread is waiting for explicit user approval.",
    threadId: 42,
    title: "Guardian needs your approval",
    ...overrides,
  };
}

function buildHookState(
  overrides: Partial<UseGuardianThreadApprovalRailResult> = {}
): UseGuardianThreadApprovalRailResult {
  return {
    approve: vi.fn().mockResolvedValue(true),
    canSubmitDecision: false,
    deny: vi.fn().mockResolvedValue(true),
    error: null,
    hasLoaded: true,
    intervention: null,
    loading: false,
    notice: null,
    reload: vi.fn().mockResolvedValue(undefined),
    submittingAction: null,
    visible: false,
    ...overrides,
  };
}

describe("GuardianThreadApprovalRail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("is hidden when there is no actionable thread intervention", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(buildHookState());

    render(<GuardianThreadApprovalRail threadId={42} />);

    expect(
      screen.queryByTestId("guardian-thread-approval-rail")
    ).not.toBeInTheDocument();
  });

  test("shows a compact rail when active thread has pending intervention", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(
      buildHookState({
        intervention: buildIntervention(),
        visible: true,
      })
    );

    render(<GuardianThreadApprovalRail threadId={42} />);

    expect(
      screen.getByTestId("guardian-thread-approval-rail")
    ).toBeInTheDocument();
    expect(screen.getByText("Guardian needs your approval")).toBeInTheDocument();
    expect(
      screen.getByText(
        "A guarded action for this thread is waiting for explicit user approval."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deny" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tell Guardian what to do instead" })
    ).toBeInTheDocument();
  });

  test("passes thread context to the rail hook", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(buildHookState());

    render(<GuardianThreadApprovalRail threadId={77} reloadSignal={4} />);

    expect(useGuardianThreadApprovalRailMock).toHaveBeenCalledWith({
      threadId: 77,
      reloadSignal: 4,
    });
  });

  test("handles unsaved draft thread context gracefully", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(buildHookState());

    render(<GuardianThreadApprovalRail />);

    expect(useGuardianThreadApprovalRailMock).toHaveBeenCalledWith({
      threadId: undefined,
      reloadSignal: undefined,
    });
    expect(
      screen.queryByTestId("guardian-thread-approval-rail")
    ).not.toBeInTheDocument();
  });

  test("renders compact actions and avoids giant dashboard sections", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(
      buildHookState({
        intervention: buildIntervention(),
        visible: true,
      })
    );

    render(<GuardianThreadApprovalRail threadId={42} />);

    expect(screen.queryByText("Guardian Approval Inbox")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Awaiting Approval" })
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Blocked" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Inspect context" })
    ).toBeInTheDocument();
  });

  test("shows Tell Guardian affordance and invokes callback when present", async () => {
    const user = userEvent.setup();
    const onTellGuardianWhatToDoInstead = vi.fn();

    useGuardianThreadApprovalRailMock.mockReturnValue(
      buildHookState({
        intervention: buildIntervention(),
        visible: true,
      })
    );

    render(
      <GuardianThreadApprovalRail
        threadId={42}
        onTellGuardianWhatToDoInstead={onTellGuardianWhatToDoInstead}
      />
    );

    await user.click(
      screen.getByRole("button", {
        name: "Tell Guardian what to do instead",
      })
    );

    expect(onTellGuardianWhatToDoInstead).toHaveBeenCalledWith({
      runId: "run_123",
      suggestedPrompt: "Guardian, do this instead for run run_123: ",
      threadId: 42,
    });
  });

  test("keeps approve and deny disabled when mutation is unsupported", () => {
    useGuardianThreadApprovalRailMock.mockReturnValue(
      buildHookState({
        canSubmitDecision: false,
        intervention: buildIntervention({
          decision: { approvalId: null, supported: false },
        }),
        visible: true,
      })
    );

    render(<GuardianThreadApprovalRail threadId={42} />);

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Deny" })).toBeDisabled();
    expect(
      screen.getByText(
        "Direct approve/deny is unavailable for this thread intervention."
      )
    ).toBeInTheDocument();
  });
});
