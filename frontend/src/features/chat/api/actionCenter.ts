import api from "@/lib/api";

const SCHEDULED_JOB_LIMIT = 5;
const AGENT_RUN_LIMIT = 5;
const APPROVAL_LIMIT = 5;
const RECENT_TASK_LIMIT = 6;

export type GuardianActionCenterContext = {
  agentRuns?: AgentRunResponse[] | null;
  threadId?: number | null;
};

export type GuardianOperatorStatus =
  | "Idle"
  | "Running"
  | "Blocked"
  | "Awaiting approval"
  | "Succeeded"
  | "Failed"
  | "Unavailable";

export type GuardianSectionAvailability =
  | "available"
  | "empty"
  | "unavailable";

export type GuardianActionCenterSection<T> = {
  availability: GuardianSectionAvailability;
  items: T[];
  message: string;
};

export type GuardianScheduledJobItem = {
  id: number;
  isEnabled: boolean;
  jobType: string;
  latestRunAt: string | null;
  latestRunId: number | null;
  latestRunStatus: string | null;
  name: string;
  schedule: string;
  status: GuardianOperatorStatus;
  updatedAt: string | null;
};

export type GuardianAgentRunItem = {
  rawStatus: string | null;
  runId: string;
  runtimeTarget: string | null;
  status: GuardianOperatorStatus;
  threadId: number | null;
  worktreeId: string | null;
  worktreePath: string | null;
};

export type GuardianApprovalItem = {
  createdAt: string | null;
  id: number;
  operation: string;
  requestedBy: string | null;
  requestReason: string | null;
  status: GuardianOperatorStatus;
  target: string | null;
};

export type GuardianRecentTaskItem = {
  detail: string;
  id: string;
  label: string;
  source: string;
  status: GuardianOperatorStatus;
  timestamp: string | null;
};

export type GuardianActionCenterSnapshot = {
  agentRuns: GuardianActionCenterSection<GuardianAgentRunItem>;
  pendingApprovals: GuardianActionCenterSection<GuardianApprovalItem>;
  recentTaskStatus: GuardianActionCenterSection<GuardianRecentTaskItem>;
  scheduledJobs: GuardianActionCenterSection<GuardianScheduledJobItem>;
  warnings: string[];
};

type CronJobResponse = {
  created_at?: string | null;
  id?: number | null;
  is_enabled?: boolean | null;
  job_type?: string | null;
  name?: string | null;
  schedule?: string | null;
  updated_at?: string | null;
};

type CronRunResponse = {
  created_at?: string | null;
  error?: string | null;
  finished_at?: string | null;
  id?: number | null;
  job_id?: number | null;
  started_at?: string | null;
  status?: string | null;
};

type AgentRunsResponse = {
  runs?: AgentRunResponse[] | null;
};

export type AgentRunResponse = {
  run_id?: string | null;
  runtime_target?: string | null;
  status?: string | null;
  thread_id?: number | null;
  worktree_id?: string | null;
  worktree_path?: string | null;
};

type BrowserApprovalsResponse = {
  count?: number | null;
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

function toStatus(value: string | null | undefined): GuardianOperatorStatus {
  const normalized = String(value ?? "")
    .trim()
    .toLowerCase();

  if (!normalized) return "Unavailable";
  if (
    normalized === "running" ||
    normalized === "queued" ||
    normalized === "started" ||
    normalized === "in_progress"
  ) {
    return "Running";
  }
  if (normalized === "blocked") return "Blocked";
  if (
    normalized === "pending" ||
    normalized === "awaiting_approval" ||
    normalized === "approval_required"
  ) {
    return "Awaiting approval";
  }
  if (
    normalized === "succeeded" ||
    normalized === "completed" ||
    normalized === "approved"
  ) {
    return "Succeeded";
  }
  if (
    normalized === "failed" ||
    normalized === "error" ||
    normalized === "denied" ||
    normalized === "cancelled" ||
    normalized === "canceled"
  ) {
    return "Failed";
  }
  if (normalized === "idle") return "Idle";
  return "Unavailable";
}

function joinDetail(parts: Array<string | null | undefined>): string {
  return parts.filter((part): part is string => Boolean(part && part.trim())).join(" | ");
}

function normalizeScheduledJob(
  job: CronJobResponse,
  latestRun: CronRunResponse | null,
  latestRunUnavailable: boolean
): GuardianScheduledJobItem | null {
  if (typeof job.id !== "number") {
    return null;
  }

  const runStatus = toStatus(latestRun?.status);
  const status = latestRunUnavailable
    ? "Unavailable"
    : latestRun
    ? runStatus
    : job.is_enabled
    ? "Idle"
    : "Idle";

  return {
    id: job.id,
    isEnabled: Boolean(job.is_enabled),
    jobType: String(job.job_type ?? "unknown"),
    latestRunAt:
      typeof latestRun?.finished_at === "string"
        ? latestRun.finished_at
        : typeof latestRun?.started_at === "string"
        ? latestRun.started_at
        : typeof latestRun?.created_at === "string"
        ? latestRun.created_at
        : null,
    latestRunId:
      typeof latestRun?.id === "number" ? latestRun.id : null,
    latestRunStatus:
      typeof latestRun?.status === "string" ? latestRun.status : null,
    name: String(job.name ?? `Job ${job.id}`),
    schedule: String(job.schedule ?? "—"),
    status,
    updatedAt:
      typeof job.updated_at === "string" ? job.updated_at : null,
  };
}

function normalizeAgentRun(run: AgentRunResponse): GuardianAgentRunItem | null {
  if (typeof run.run_id !== "string" || !run.run_id.trim()) {
    return null;
  }

  return {
    rawStatus:
      typeof run.status === "string" ? run.status : null,
    runId: run.run_id,
    runtimeTarget:
      typeof run.runtime_target === "string" ? run.runtime_target : null,
    status: toStatus(run.status),
    threadId:
      typeof run.thread_id === "number" ? run.thread_id : null,
    worktreeId:
      typeof run.worktree_id === "string" ? run.worktree_id : null,
    worktreePath:
      typeof run.worktree_path === "string" ? run.worktree_path : null,
  };
}

function normalizeApproval(
  approval: BrowserApprovalResponse
): GuardianApprovalItem | null {
  if (typeof approval.id !== "number") {
    return null;
  }

  const rawStatus = String(approval.status ?? "");

  return {
    createdAt:
      typeof approval.created_at === "string" ? approval.created_at : null,
    id: approval.id,
    operation: String(approval.operation ?? "unknown"),
    requestedBy:
      typeof approval.requested_by === "string"
        ? approval.requested_by
        : null,
    requestReason:
      typeof approval.request_reason === "string"
        ? approval.request_reason
        : null,
    status:
      rawStatus.trim().toUpperCase() === "PENDING"
        ? "Awaiting approval"
        : toStatus(rawStatus),
    target:
      typeof approval.target === "string" ? approval.target : null,
  };
}

export async function fetchAgentRuns(threadId: number): Promise<AgentRunResponse[]> {
  const response = await api.get<AgentRunsResponse>(
    `/api/chat/${threadId}/agent-runs`
  );
  return Array.isArray(response.data?.runs) ? response.data.runs : [];
}

export function buildAgentRunsSection(
  runs: AgentRunResponse[] | null | undefined
): GuardianActionCenterSection<GuardianAgentRunItem> {
  if (!runs) {
    return {
      availability: "unavailable",
      items: [],
      message: "Delegation runs unavailable without thread context",
    };
  }

  const items = runs
    .map(normalizeAgentRun)
    .filter((item): item is GuardianAgentRunItem => Boolean(item))
    .slice(0, AGENT_RUN_LIMIT);

  return items.length > 0
    ? {
        availability: "available",
        items,
        message: "",
      }
    : {
        availability: "empty",
        items: [],
        message: "No recent delegation runs",
      };
}

export function buildRecentTaskItems(
  scheduledJobs: GuardianActionCenterSection<GuardianScheduledJobItem>,
  agentRuns: GuardianActionCenterSection<GuardianAgentRunItem>
): GuardianActionCenterSection<GuardianRecentTaskItem> {
  const items: GuardianRecentTaskItem[] = [];

  if (scheduledJobs.availability !== "unavailable") {
    for (const job of scheduledJobs.items) {
      if (!job.latestRunId) continue;
      items.push({
        detail: joinDetail([
          `Schedule ${job.schedule}`,
          job.latestRunStatus ? `Run ${job.latestRunStatus}` : null,
        ]),
        id: `cron-run-${job.id}-${job.latestRunId}`,
        label: job.name,
        source: "Scheduled job",
        status: job.status,
        timestamp: job.latestRunAt,
      });
    }
  }

  if (agentRuns.availability !== "unavailable") {
    for (const run of agentRuns.items) {
      items.push({
        detail: joinDetail([
          run.runtimeTarget ? `Runtime ${run.runtimeTarget}` : null,
          run.worktreeId ? `Worktree ${run.worktreeId}` : null,
        ]),
        id: `agent-run-${run.runId}`,
        label: run.runId,
        source: "Delegation run",
        status: run.status,
        timestamp: null,
      });
    }
  }

  items.sort((left, right) => {
    const leftTime = left.timestamp ? Date.parse(left.timestamp) : Number.NaN;
    const rightTime = right.timestamp ? Date.parse(right.timestamp) : Number.NaN;

    if (Number.isFinite(leftTime) && Number.isFinite(rightTime)) {
      return rightTime - leftTime;
    }
    if (Number.isFinite(rightTime)) return 1;
    if (Number.isFinite(leftTime)) return -1;
    return left.label.localeCompare(right.label);
  });

  const limitedItems = items.slice(0, RECENT_TASK_LIMIT);
  const sourcesAvailable =
    scheduledJobs.availability !== "unavailable" ||
    agentRuns.availability !== "unavailable";

  if (!sourcesAvailable) {
    return {
      availability: "unavailable",
      items: [],
      message: "Recent task status unavailable",
    };
  }

  if (limitedItems.length === 0) {
    return {
      availability: "empty",
      items: [],
      message: "No recent task status",
    };
  }

  return {
    availability: "available",
    items: limitedItems,
    message: "",
  };
}

export async function fetchGuardianActionCenterSnapshot(
  context: GuardianActionCenterContext = {}
): Promise<GuardianActionCenterSnapshot> {
  const warnings: string[] = [];

  let scheduledJobs: GuardianActionCenterSection<GuardianScheduledJobItem> = {
    availability: "unavailable",
    items: [],
    message: "Scheduled jobs unavailable",
  };
  let pendingApprovals: GuardianActionCenterSection<GuardianApprovalItem> = {
    availability: "unavailable",
    items: [],
    message: "Pending approvals unavailable",
  };

  const jobsPromise = api.get<CronJobResponse[]>("/api/cron/jobs");
  const approvalsPromise = api.get<BrowserApprovalsResponse>(
    "/api/browser/approvals",
    { params: { status_value: "PENDING" } }
  );
  const [jobsResult, approvalsResult] = await Promise.allSettled([
    jobsPromise,
    approvalsPromise,
  ]);

  if (jobsResult.status === "fulfilled") {
    const jobs = Array.isArray(jobsResult.value.data)
      ? jobsResult.value.data.slice(0, SCHEDULED_JOB_LIMIT)
      : [];

    const runResults = await Promise.allSettled(
      jobs.map((job) =>
        typeof job.id === "number"
          ? api.get<CronRunResponse[]>(`/api/cron/jobs/${job.id}/runs`)
          : Promise.resolve({ data: [] as CronRunResponse[] })
      )
    );

    const items = jobs
      .map((job, index) => {
        const runResult = runResults[index];
        const latestRun =
          runResult && runResult.status === "fulfilled"
            ? Array.isArray(runResult.value.data) && runResult.value.data.length > 0
              ? runResult.value.data[0] ?? null
              : null
            : null;
        const latestRunUnavailable = Boolean(
          runResult && runResult.status === "rejected"
        );

        if (
          runResult &&
          runResult.status === "rejected" &&
          typeof job.id === "number"
        ) {
          warnings.push(`Latest runs unavailable for scheduled job ${job.id}.`);
        }

        return normalizeScheduledJob(job, latestRun, latestRunUnavailable);
      })
      .filter((item): item is GuardianScheduledJobItem => Boolean(item));

    scheduledJobs =
      items.length > 0
        ? {
            availability: "available",
            items,
            message: "",
          }
        : {
            availability: "empty",
            items: [],
            message: "No recent scheduled jobs",
          };
  } else {
    warnings.push("Scheduled jobs source did not respond.");
  }

  if (approvalsResult.status === "fulfilled") {
    const items = Array.isArray(approvalsResult.value.data?.items)
      ? approvalsResult.value.data.items
          .map(normalizeApproval)
          .filter((item): item is GuardianApprovalItem => Boolean(item))
          .slice(0, APPROVAL_LIMIT)
      : [];

    pendingApprovals =
      items.length > 0
        ? {
            availability: "available",
            items,
            message: "",
          }
        : {
            availability: "empty",
            items: [],
            message: "No pending approvals",
          };
  } else {
    warnings.push("Pending approvals source did not respond.");
  }

  const agentRuns = buildAgentRunsSection(context.agentRuns ?? null);

  return {
    agentRuns,
    pendingApprovals,
    recentTaskStatus: buildRecentTaskItems(scheduledJobs, agentRuns),
    scheduledJobs,
    warnings,
  };
}
