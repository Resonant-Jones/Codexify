import api from "@/lib/api";
import { type AgentRunResponse } from "@/features/chat/api/actionCenter";

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

export type GuardianThreadApprovalSnapshot = {
  intervention: GuardianThreadIntervention | null;
  warnings: string[];
};

export type GuardianThreadApprovalContext = {
  agentRuns?: AgentRunResponse[] | null;
  threadId?: number | null;
};

export type GuardianThreadDecisionResult = {
  approvalId: number;
  operation: string | null;
  status: string;
  target: string | null;
};

type BrowserApprovalsResponse = {
  items?: BrowserApprovalResponse[] | null;
};

type BrowserApprovalResponse = {
  id?: number | null;
  operation?: string | null;
  request_reason?: string | null;
  status?: string | null;
  target?: string | null;
};

type ApprovalDecisionResponse = {
  id?: number | null;
  operation?: string | null;
  status?: string | null;
  target?: string | null;
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

function classifyRunKind(rawStatus: string): GuardianThreadInterventionKind | null {
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

function findActionableRun(runs: AgentRunResponse[]): ActionableRun | null {
  for (const run of runs) {
    const rawStatus = normalizeStatus(run.status);
    const kind = classifyRunKind(rawStatus);
    if (!kind) continue;

    return {
      kind,
      rawStatus,
      runId:
        typeof run.run_id === "string" && run.run_id.trim()
          ? run.run_id
          : null,
      runtimeTarget:
        typeof run.runtime_target === "string" && run.runtime_target.trim()
          ? run.runtime_target
          : null,
      worktreeId:
        typeof run.worktree_id === "string" && run.worktree_id.trim()
          ? run.worktree_id
          : null,
      worktreePath:
        typeof run.worktree_path === "string" && run.worktree_path.trim()
          ? run.worktree_path
          : null,
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

function maybeMatchesThreadContext(
  approval: BrowserApprovalResponse,
  threadId: number,
  runId: string | null
): boolean {
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

  if (runId && haystack.includes(runId.toLowerCase())) {
    return true;
  }

  return false;
}

function buildIntervention(
  run: ActionableRun,
  threadId: number,
  linkedApprovalId: number | null
): GuardianThreadIntervention {
  const details = [
    run.runId ? `Run: ${run.runId}` : null,
    run.runtimeTarget ? `Runtime: ${run.runtimeTarget}` : null,
    run.worktreeId ? `Worktree: ${run.worktreeId}` : null,
    run.worktreePath ? `Path: ${run.worktreePath}` : null,
    run.rawStatus ? `Raw status: ${run.rawStatus}` : null,
  ].filter((value): value is string => Boolean(value));

  return {
    canRedirect: true,
    decision: {
      approvalId: linkedApprovalId,
      supported: linkedApprovalId != null,
    },
    details,
    id: `${threadId}:${run.runId ?? run.kind}`,
    kind: run.kind,
    rawStatus: run.rawStatus,
    redirectPrompt: buildRedirectPrompt(run),
    runId: run.runId,
    statusLabel: kindStatusLabel(run.kind),
    summary: interventionSummary(run),
    threadId,
    title: kindTitle(run.kind),
  };
}

function parseDecisionResult(
  data: ApprovalDecisionResponse,
  fallbackApprovalId: number
): GuardianThreadDecisionResult {
  return {
    approvalId:
      typeof data.id === "number" ? data.id : fallbackApprovalId,
    operation:
      typeof data.operation === "string" && data.operation.trim()
        ? data.operation
        : null,
    status:
      typeof data.status === "string" && data.status.trim()
        ? data.status
        : "UNKNOWN",
    target:
      typeof data.target === "string" && data.target.trim()
        ? data.target
        : null,
  };
}

export async function fetchGuardianThreadApprovalSnapshot(
  context: GuardianThreadApprovalContext = {}
): Promise<GuardianThreadApprovalSnapshot> {
  const threadId = context.threadId;
  if (typeof threadId !== "number") {
    return { intervention: null, warnings: [] };
  }

  const warnings: string[] = [];
  const runs = Array.isArray(context.agentRuns) ? context.agentRuns : [];
  if (!context.agentRuns) {
    warnings.push("Thread intervention state is currently unavailable.");
    return { intervention: null, warnings };
  }

  const actionableRun = findActionableRun(runs);
  if (!actionableRun) {
    return { intervention: null, warnings };
  }

  let linkedApprovalId: number | null = null;
  if (actionableRun.kind === "approval_required") {
    try {
      const approvalsResponse = await api.get<BrowserApprovalsResponse>(
        "/api/browser/approvals",
        { params: { status_value: "PENDING" } }
      );
      const matchingApproval = Array.isArray(approvalsResponse.data?.items)
        ? approvalsResponse.data.items.find((approval) =>
            maybeMatchesThreadContext(
              approval,
              threadId,
              actionableRun.runId
            )
          ) ?? null
        : null;

      linkedApprovalId =
        matchingApproval && typeof matchingApproval.id === "number"
          ? matchingApproval.id
          : null;
    } catch {
      warnings.push("Approval decision route is currently unavailable.");
    }
  }

  return {
    intervention: buildIntervention(actionableRun, threadId, linkedApprovalId),
    warnings,
  };
}

async function decideThreadApproval(
  approvalId: number,
  decision: "approve" | "deny",
  reason: string
): Promise<GuardianThreadDecisionResult> {
  const normalizedReason = reason.trim();
  const response = await api.post<ApprovalDecisionResponse>(
    `/api/browser/approvals/${approvalId}/${decision}`,
    {
      reason:
        normalizedReason || `Guardian thread rail ${decision} decision.`,
    }
  );

  return parseDecisionResult(response.data ?? {}, approvalId);
}

export async function approveGuardianThreadApproval(input: {
  approvalId: number;
  reason: string;
}): Promise<GuardianThreadDecisionResult> {
  return decideThreadApproval(input.approvalId, "approve", input.reason);
}

export async function denyGuardianThreadApproval(input: {
  approvalId: number;
  reason: string;
}): Promise<GuardianThreadDecisionResult> {
  return decideThreadApproval(input.approvalId, "deny", input.reason);
}
