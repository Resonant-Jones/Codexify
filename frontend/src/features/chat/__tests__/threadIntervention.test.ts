import { describe, expect, test } from "vitest";

import {
  interpretGuardianThreadIntervention,
  type GuardianPendingApprovalInput,
  type GuardianThreadRunInput,
} from "@/features/chat/approvals/threadIntervention";

const threadId = 42;

function run(
  status: string,
  overrides: Partial<GuardianThreadRunInput> = {}
): GuardianThreadRunInput {
  return {
    run_id: "run_123",
    runtime_target: "guardian",
    status,
    thread_id: threadId,
    worktree_id: "worktree_123",
    worktree_path: "/private/worktree",
    ...overrides,
  };
}

function approval(
  overrides: Partial<GuardianPendingApprovalInput> = {}
): GuardianPendingApprovalInput {
  return {
    id: 17,
    operation: "evaluate",
    request_reason: "Approval required for thread_id:42 run_123",
    status: "PENDING",
    target: "browser action",
    ...overrides,
  };
}

describe("interpretGuardianThreadIntervention", () => {
  test.each(["awaiting_approval", "approval_required", "pending"])(
    "maps %s to an approval-required presentation",
    (status) => {
      const result = interpretGuardianThreadIntervention({
        agentRuns: [run(status)],
        pendingApprovals: [approval()],
        threadId,
      });

      expect(result).toMatchObject({
        kind: "approval_required",
        statusLabel: "Approval required",
        decision: { approvalId: 17, supported: true },
      });
    }
  );

  test("maps clarification without manufacturing an approval decision", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("clarification_required")],
      pendingApprovals: [approval()],
      threadId,
    });

    expect(result).toMatchObject({
      kind: "clarification_required",
      decision: { approvalId: null, supported: false },
      title: "Guardian needs clarification",
    });
  });

  test("maps blocked state to user redirection without approval controls", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("blocked")],
      pendingApprovals: [],
      threadId,
    });

    expect(result).toMatchObject({
      kind: "blocked_waiting_for_user",
      decision: { approvalId: null, supported: false },
      canRedirect: true,
    });
  });

  test("ignores unrelated runs", () => {
    expect(
      interpretGuardianThreadIntervention({
        agentRuns: [run("running")],
        pendingApprovals: [approval()],
        threadId,
      })
    ).toBeNull();
  });

  test("correlates a pending approval by the exact thread context", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("awaiting_approval")],
      pendingApprovals: [
        approval({
          id: 31,
          request_reason: "Guardian paused /api/chat/42 before evaluate",
        }),
      ],
      threadId,
    });

    expect(result?.decision).toEqual({ approvalId: 31, supported: true });
  });

  test("correlates a pending approval by run ID", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("awaiting_approval")],
      pendingApprovals: [
        approval({
          id: 32,
          request_reason: "Guarded action for RUN_123",
        }),
      ],
      threadId,
    });

    expect(result?.decision).toEqual({ approvalId: 32, supported: true });
  });

  test("does not correlate unrelated or already-resolved approvals", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("awaiting_approval")],
      pendingApprovals: [
        approval({ id: 91, request_reason: "thread_id:99" }),
        approval({ id: 92, status: "APPROVED" }),
      ],
      threadId,
    });

    expect(result?.decision).toEqual({ approvalId: null, supported: false });
  });

  test("keeps diagnostic details secondary in the presentation model", () => {
    const result = interpretGuardianThreadIntervention({
      agentRuns: [run("awaiting_approval")],
      pendingApprovals: [],
      threadId,
    });

    expect(result?.title).toBe("Guardian needs your approval");
    expect(result?.details).toEqual([
      "Run: run_123",
      "Runtime: guardian",
      "Worktree: worktree_123",
      "Path: /private/worktree",
      "Raw status: awaiting_approval",
    ]);
  });
});
