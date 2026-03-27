import api from "@/lib/api";
import { type AgentRunResponse } from "@/features/chat/api/actionCenter";

const APPROVAL_LIMIT = 12;
const RUN_LIMIT = 12;

export type GuardianApprovalInboxContext = {
  agentRuns?: AgentRunResponse[] | null;
  threadId?: number | null;
};

export type GuardianInterventionStatus =
  | "Awaiting approval"
  | "Blocked"
  | "Escalated"
  | "Clarification needed"
  | "Unavailable";

export type GuardianApprovalInboxAvailability =
  | "available"
  | "empty"
  | "unavailable";

export type GuardianApprovalInboxSection<T> = {
  availability: GuardianApprovalInboxAvailability;
  items: T[];
  message: string;
};

export type GuardianApprovalInboxItem = {
  createdAt: string | null;
  href: string | null;
  id: string;
  runId: string | null;
  sourceType: string;
  status: GuardianInterventionStatus;
  summary: string;
  taskId: string | null;
  threadId: number | null;
  title: string;
  updatedAt: string | null;
};

export type GuardianApprovalInboxSnapshot = {
  awaitingApprovals: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  blockedActions: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  clarificationNeeded: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  escalatedItems: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  warnings: string[];
};

type BrowserApprovalsResponse = {
  items?: BrowserApprovalResponse[] | null;
};

type BrowserApprovalResponse = {
  created_at?: string | null;
  id?: number | null;
  operation?: string | null;
  request_reason?: string | null;
  requested_by?: string | null;
  status?: string | null;
  target?: string | null;
};


function emptySection(
  message: string
): GuardianApprovalInboxSection<GuardianApprovalInboxItem> {
  return {
    availability: "empty",
    items: [],
    message,
  };
}

function unavailableSection(
  message: string
): GuardianApprovalInboxSection<GuardianApprovalInboxItem> {
  return {
    availability: "unavailable",
    items: [],
    message,
  };
}

function availableSection(
  items: GuardianApprovalInboxItem[],
  fallbackEmptyMessage: string
): GuardianApprovalInboxSection<GuardianApprovalInboxItem> {
  if (items.length === 0) {
    return emptySection(fallbackEmptyMessage);
  }
  return {
    availability: "available",
    items,
    message: "",
  };
}

function joinSummary(parts: Array<string | null | undefined>): string {
  return parts
    .filter((part): part is string => Boolean(part && part.trim()))
    .join(" | ");
}

function normalizeApproval(
  item: BrowserApprovalResponse
): GuardianApprovalInboxItem | null {
  if (typeof item.id !== "number") return null;

  const operation = String(item.operation ?? "Pending approval");
  const statusRaw = String(item.status ?? "").trim().toUpperCase();

  return {
    createdAt:
      typeof item.created_at === "string" ? item.created_at : null,
    href: null,
    id: `approval-${item.id}`,
    runId: null,
    sourceType: "Browser approval",
    status:
      statusRaw === "PENDING"
        ? "Awaiting approval"
        : "Awaiting approval",
    summary: joinSummary([
      item.target ? `Target ${item.target}` : null,
      item.request_reason ? `Reason ${item.request_reason}` : null,
      item.requested_by ? `Requested by ${item.requested_by}` : null,
    ]),
    taskId: null,
    threadId: null,
    title: operation,
    updatedAt: null,
  };
}

function normalizeRunItem(
  run: AgentRunResponse
): (GuardianApprovalInboxItem & { bucket: "awaiting" | "blocked" | "escalated" | "clarification" }) | null {
  if (typeof run.run_id !== "string" || !run.run_id.trim()) {
    return null;
  }

  const rawStatus = String(run.status ?? "")
    .trim()
    .toLowerCase();
  let bucket: "awaiting" | "blocked" | "escalated" | "clarification" | null = null;
  let status: GuardianInterventionStatus = "Unavailable";

  if (
    rawStatus === "awaiting_approval" ||
    rawStatus === "pending" ||
    rawStatus === "approval_required"
  ) {
    bucket = "awaiting";
    status = "Awaiting approval";
  } else if (rawStatus === "blocked") {
    bucket = "blocked";
    status = "Blocked";
  } else if (
    rawStatus === "escalated" ||
    rawStatus === "failed" ||
    rawStatus === "error" ||
    rawStatus === "canceled" ||
    rawStatus === "cancelled"
  ) {
    bucket = "escalated";
    status = "Escalated";
  } else if (
    rawStatus === "clarification_needed" ||
    rawStatus === "needs_clarification" ||
    rawStatus === "requires_clarification"
  ) {
    bucket = "clarification";
    status = "Clarification needed";
  } else {
    return null;
  }

  return {
    bucket,
    createdAt: null,
    href: null,
    id: `agent-run-${run.run_id}`,
    runId: run.run_id,
    sourceType: "Delegation run",
    status,
    summary: joinSummary([
      run.runtime_target ? `Runtime ${run.runtime_target}` : null,
      run.worktree_id ? `Worktree ${run.worktree_id}` : null,
      run.worktree_path ? `Path ${run.worktree_path}` : null,
      rawStatus ? `Raw status ${rawStatus}` : null,
    ]),
    taskId: null,
    threadId:
      typeof run.thread_id === "number" ? run.thread_id : null,
    title: `Run ${run.run_id}`,
    updatedAt: null,
  };
}

export function buildGuardianApprovalRunSections(
  runs: AgentRunResponse[] | null | undefined,
  awaitingApprovals: GuardianApprovalInboxSection<GuardianApprovalInboxItem>
): {
  awaitingApprovals: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  blockedActions: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  escalatedItems: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
  clarificationNeeded: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
} {
  if (!runs) {
    return {
      awaitingApprovals,
      blockedActions: unavailableSection(
        "Blocked actions unavailable without thread context"
      ),
      escalatedItems: unavailableSection(
        "Escalation items unavailable without thread context"
      ),
      clarificationNeeded: unavailableSection(
        "Clarification items unavailable without thread context"
      ),
    };
  }

  const normalized = runs
    .map(normalizeRunItem)
    .filter(
      (
        item
      ): item is GuardianApprovalInboxItem & {
        bucket: "awaiting" | "blocked" | "escalated" | "clarification";
      } => Boolean(item)
    )
    .slice(0, RUN_LIMIT);

  const awaitingFromRuns = normalized
    .filter((item) => item.bucket === "awaiting")
    .map(({ bucket: _bucket, ...item }) => item);
  const blockedFromRuns = normalized
    .filter((item) => item.bucket === "blocked")
    .map(({ bucket: _bucket, ...item }) => item);
  const escalatedFromRuns = normalized
    .filter((item) => item.bucket === "escalated")
    .map(({ bucket: _bucket, ...item }) => item);
  const clarificationFromRuns = normalized
    .filter((item) => item.bucket === "clarification")
    .map(({ bucket: _bucket, ...item }) => item);

  let mergedAwaiting = awaitingApprovals;
  if (awaitingFromRuns.length > 0) {
    const combined = [
      ...awaitingApprovals.items,
      ...awaitingFromRuns,
    ].slice(0, APPROVAL_LIMIT);
    mergedAwaiting = availableSection(combined, "No pending approvals");
  }

  return {
    awaitingApprovals: mergedAwaiting,
    blockedActions: availableSection(blockedFromRuns, "No blocked actions"),
    escalatedItems: availableSection(
      escalatedFromRuns,
      "No escalation items"
    ),
    clarificationNeeded: availableSection(
      clarificationFromRuns,
      "No clarification-needed items"
    ),
  };
}

export async function fetchGuardianApprovalInboxSnapshot(
  context: GuardianApprovalInboxContext = {}
): Promise<GuardianApprovalInboxSnapshot> {
  const warnings: string[] = [];

  let awaitingApprovals: GuardianApprovalInboxSection<GuardianApprovalInboxItem> =
    unavailableSection("Pending approvals unavailable");
  let blockedActions: GuardianApprovalInboxSection<GuardianApprovalInboxItem> =
    unavailableSection("Blocked actions unavailable");
  let escalatedItems: GuardianApprovalInboxSection<GuardianApprovalInboxItem> =
    unavailableSection("Escalation items unavailable");
  let clarificationNeeded: GuardianApprovalInboxSection<GuardianApprovalInboxItem> =
    unavailableSection("Clarification items unavailable");

  const approvalsPromise = api.get<BrowserApprovalsResponse>(
    "/api/browser/approvals",
    { params: { status_value: "PENDING" } }
  );
  const [approvalsResult] = await Promise.allSettled([approvalsPromise]);

  if (approvalsResult.status === "fulfilled") {
    const approvalItems = Array.isArray(approvalsResult.value.data?.items)
      ? approvalsResult.value.data.items
          .map(normalizeApproval)
          .filter((item): item is GuardianApprovalInboxItem => Boolean(item))
          .slice(0, APPROVAL_LIMIT)
      : [];

    awaitingApprovals = availableSection(
      approvalItems,
      "No pending approvals"
    );
  } else {
    warnings.push("Pending approvals source did not respond.");
  }

  const runSections = buildGuardianApprovalRunSections(
    context.agentRuns ?? null,
    awaitingApprovals
  );
  awaitingApprovals = runSections.awaitingApprovals;
  blockedActions = runSections.blockedActions;
  escalatedItems = runSections.escalatedItems;
  clarificationNeeded = runSections.clarificationNeeded;

  return {
    awaitingApprovals,
    blockedActions,
    clarificationNeeded,
    escalatedItems,
    warnings,
  };
}
