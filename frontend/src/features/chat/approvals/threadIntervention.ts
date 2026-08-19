export type GuardianThreadInterventionKind =
  | "approval_required"
  | "clarification_required"
  | "blocked_waiting_for_user";

export type GuardianThreadApprovalDecision = {
  approvalId: number | null;
  supported: boolean;
};

export type GuardianThreadIntervention = {
  canRedirect: boolean;
  decision: GuardianThreadApprovalDecision;
  details: string[];
  id: string;
  kind: GuardianThreadInterventionKind;
  rawStatus: string;
  redirectPrompt: string;
  runId: string | null;
  statusLabel: string;
  summary: string;
  threadId: number;
  title: string;
};

export type GuardianThreadRunInput = {
  run_id?: string | null;
  runtime_target?: string | null;
  status?: string | null;
  thread_id?: number | null;
  worktree_id?: string | null;
  worktree_path?: string | null;
};

export type GuardianPendingApprovalInput = {
  id?: number | null;
  operation?: string | null;
  request_reason?: string | null;
  status?: string | null;
  target?: string | null;
};

export type GuardianThreadInterventionInput = {
  agentRuns?: readonly GuardianThreadRunInput[] | null;
  pendingApprovals?: readonly GuardianPendingApprovalInput[] | null;
  threadId?: number | null;
};

type ActionableRun = {
  kind: GuardianThreadInterventionKind;
  rawStatus: string;
  runId: string | null;
  runtimeTarget: string | null;
  worktreeId: string | null;
  worktreePath: string | null;
};

function normalizeStatus(status: unknown): string {
  return String(status ?? "")
    .trim()
    .toLowerCase();
}

export function classifyGuardianThreadRunKind(
  status: unknown
): GuardianThreadInterventionKind | null {
  const rawStatus = normalizeStatus(status);
  if (
    rawStatus === "awaiting_approval" ||
    rawStatus === "approval_required" ||
    rawStatus === "pending"
  ) {
    return "approval_required";
  }

  if (
    rawStatus === "clarification_required" ||
    rawStatus === "requires_clarification" ||
    rawStatus === "clarification_needed" ||
    rawStatus === "needs_clarification"
  ) {
    return "clarification_required";
  }

  if (rawStatus === "blocked" || rawStatus === "escalated") {
    return "blocked_waiting_for_user";
  }

  return null;
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function findActionableRun(
  runs: readonly GuardianThreadRunInput[]
): ActionableRun | null {
  for (const run of runs) {
    const rawStatus = normalizeStatus(run.status);
    const kind = classifyGuardianThreadRunKind(rawStatus);
    if (!kind) continue;

    return {
      kind,
      rawStatus,
      runId: optionalString(run.run_id),
      runtimeTarget: optionalString(run.runtime_target),
      worktreeId: optionalString(run.worktree_id),
      worktreePath: optionalString(run.worktree_path),
    };
  }

  return null;
}

function kindStatusLabel(kind: GuardianThreadInterventionKind): string {
  if (kind === "approval_required") return "Approval required";
  if (kind === "clarification_required") return "Clarification required";
  return "Blocked waiting for user";
}

function kindTitle(kind: GuardianThreadInterventionKind): string {
  if (kind === "approval_required") return "Guardian needs your approval";
  if (kind === "clarification_required") return "Guardian needs clarification";
  return "Guardian is blocked in this thread";
}

function interventionSummary(run: ActionableRun): string {
  if (run.kind === "approval_required") {
    return "A guarded action for this thread is waiting for explicit user approval.";
  }
  if (run.kind === "clarification_required") {
    return "Guardian paused this run and needs direction before it can continue.";
  }
  return "This thread run is blocked and waiting for user intervention.";
}

function buildRedirectPrompt(run: ActionableRun): string {
  const runFragment = run.runId ? ` for run ${run.runId}` : "";
  return `Guardian, do this instead${runFragment}: `;
}

export function guardianApprovalMatchesThread(
  approval: GuardianPendingApprovalInput,
  threadId: number,
  runId: string | null
): boolean {
  if (normalizeStatus(approval.status) !== "pending") return false;

  const haystack = [
    approval.operation,
    approval.target,
    approval.request_reason,
  ]
    .filter((value): value is string => typeof value === "string")
    .join(" ")
    .toLowerCase();

  if (!haystack.trim()) return false;

  const threadTokens = [
    `thread ${threadId}`,
    `thread:${threadId}`,
    `thread_id:${threadId}`,
    `thread_id=${threadId}`,
    `"thread_id":${threadId}`,
    `/chat/${threadId}`,
  ];

  if (threadTokens.some((token) => haystack.includes(token))) {
    return true;
  }

  return Boolean(runId && haystack.includes(runId.toLowerCase()));
}

export function interpretGuardianThreadIntervention({
  agentRuns,
  pendingApprovals,
  threadId,
}: GuardianThreadInterventionInput): GuardianThreadIntervention | null {
  if (typeof threadId !== "number") return null;

  const actionableRun = findActionableRun(
    Array.isArray(agentRuns) ? agentRuns : []
  );
  if (!actionableRun) return null;

  const matchingApproval =
    actionableRun.kind === "approval_required" &&
    Array.isArray(pendingApprovals)
      ? pendingApprovals.find((approval) =>
          guardianApprovalMatchesThread(
            approval,
            threadId,
            actionableRun.runId
          )
        ) ?? null
      : null;
  const linkedApprovalId =
    matchingApproval && typeof matchingApproval.id === "number"
      ? matchingApproval.id
      : null;
  const details = [
    actionableRun.runId ? `Run: ${actionableRun.runId}` : null,
    actionableRun.runtimeTarget
      ? `Runtime: ${actionableRun.runtimeTarget}`
      : null,
    actionableRun.worktreeId
      ? `Worktree: ${actionableRun.worktreeId}`
      : null,
    actionableRun.worktreePath
      ? `Path: ${actionableRun.worktreePath}`
      : null,
    actionableRun.rawStatus
      ? `Raw status: ${actionableRun.rawStatus}`
      : null,
  ].filter((value): value is string => Boolean(value));

  return {
    canRedirect: true,
    decision: {
      approvalId: linkedApprovalId,
      supported: linkedApprovalId != null,
    },
    details,
    id: `${threadId}:${actionableRun.runId ?? actionableRun.kind}`,
    kind: actionableRun.kind,
    rawStatus: actionableRun.rawStatus,
    redirectPrompt: buildRedirectPrompt(actionableRun),
    runId: actionableRun.runId,
    statusLabel: kindStatusLabel(actionableRun.kind),
    summary: interventionSummary(actionableRun),
    threadId,
    title: kindTitle(actionableRun.kind),
  };
}
