import api from "@/lib/api";
import {
  interpretGuardianThreadIntervention,
  type GuardianPendingApprovalInput,
  type GuardianThreadRunInput,
} from "@/features/chat/approvals/threadIntervention";

export type {
  GuardianThreadApprovalDecision,
  GuardianThreadIntervention,
  GuardianThreadInterventionKind,
} from "@/features/chat/approvals/threadIntervention";

export type GuardianThreadApprovalSnapshot = {
  intervention: GuardianThreadIntervention | null;
  warnings: string[];
};

export type GuardianThreadApprovalContext = {
  agentRuns?: GuardianThreadRunInput[] | null;
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

type BrowserApprovalResponse = GuardianPendingApprovalInput;

type ApprovalDecisionResponse = {
  id?: number | null;
  operation?: string | null;
  status?: string | null;
  target?: string | null;
};

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

  const initialIntervention = interpretGuardianThreadIntervention({
    agentRuns: runs,
    pendingApprovals: [],
    threadId,
  });
  if (!initialIntervention) {
    return { intervention: null, warnings };
  }

  let pendingApprovals: BrowserApprovalResponse[] = [];
  if (initialIntervention.kind === "approval_required") {
    try {
      const approvalsResponse = await api.get<BrowserApprovalsResponse>(
        "/api/browser/approvals",
        { params: { status_value: "PENDING" } }
      );
      pendingApprovals = Array.isArray(approvalsResponse.data?.items)
        ? approvalsResponse.data.items
        : [];
    } catch {
      warnings.push("Approval decision route is currently unavailable.");
    }
  }

  return {
    intervention: interpretGuardianThreadIntervention({
      agentRuns: runs,
      pendingApprovals,
      threadId,
    }),
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
