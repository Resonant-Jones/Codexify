import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

import useGuardianActionCenter from "@/features/chat/hooks/useGuardianActionCenter";
import type {
  GuardianActionCenterSection,
  GuardianAgentRunItem,
  GuardianApprovalItem,
  GuardianOperatorStatus,
  GuardianRecentTaskItem,
  GuardianScheduledJobItem,
} from "@/features/chat/api/actionCenter";

type GuardianActionCenterProps = {
  className?: string;
  threadId?: number;
};

const STATUS_STYLE: Record<
  GuardianOperatorStatus,
  { background: string; borderColor: string }
> = {
  Idle: {
    background: "rgba(148, 163, 184, 0.12)",
    borderColor: "rgba(148, 163, 184, 0.28)",
  },
  Running: {
    background: "rgba(59, 130, 246, 0.12)",
    borderColor: "rgba(59, 130, 246, 0.35)",
  },
  Blocked: {
    background: "rgba(245, 158, 11, 0.12)",
    borderColor: "rgba(245, 158, 11, 0.35)",
  },
  "Awaiting approval": {
    background: "rgba(250, 204, 21, 0.12)",
    borderColor: "rgba(250, 204, 21, 0.35)",
  },
  Succeeded: {
    background: "rgba(34, 197, 94, 0.12)",
    borderColor: "rgba(34, 197, 94, 0.35)",
  },
  Failed: {
    background: "rgba(239, 68, 68, 0.12)",
    borderColor: "rgba(239, 68, 68, 0.35)",
  },
  Unavailable: {
    background: "rgba(148, 163, 184, 0.12)",
    borderColor: "rgba(148, 163, 184, 0.28)",
  },
};

function formatTimestamp(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function StatusBadge({ status }: { status: GuardianOperatorStatus }) {
  return (
    <span
      className="rounded-full border px-2 py-1 text-xs font-medium"
      style={{
        ...STATUS_STYLE[status],
        color: "var(--text)",
      }}
    >
      {status}
    </span>
  );
}

function SectionShell({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section
      className="space-y-3 rounded-xl border p-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
        {title}
      </h3>
      {children}
    </section>
  );
}

function SectionState<T>({
  renderItem,
  section,
}: {
  renderItem: (item: T) => React.ReactNode;
  section: GuardianActionCenterSection<T>;
}) {
  if (section.availability === "unavailable") {
    return (
      <div className="space-y-2 text-sm" style={{ color: "var(--muted)" }}>
        <StatusBadge status="Unavailable" />
        <div>{section.message}</div>
      </div>
    );
  }

  if (section.items.length === 0) {
    return (
      <div className="space-y-2 text-sm" style={{ color: "var(--muted)" }}>
        <div>{section.message}</div>
      </div>
    );
  }

  return <ul className="space-y-2">{section.items.map(renderItem)}</ul>;
}

function ScheduledJobRow({ job }: { job: GuardianScheduledJobItem }) {
  return (
    <li
      className="rounded-xl border px-3 py-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {job.name}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {job.schedule}
          </div>
        </div>
        <StatusBadge status={job.status} />
      </div>
      <ul className="mt-3 flex flex-wrap gap-2 text-xs">
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Job type: {job.jobType}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          {job.isEnabled ? "Enabled" : "Disabled"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Last run: {job.latestRunStatus ?? "none"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Updated: {formatTimestamp(job.updatedAt) ?? "Not exposed"}
        </li>
      </ul>
    </li>
  );
}

function AgentRunRow({ run }: { run: GuardianAgentRunItem }) {
  return (
    <li
      className="rounded-xl border px-3 py-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {run.runId}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            Runtime: {run.runtimeTarget ?? "unknown"}
          </div>
        </div>
        <StatusBadge status={run.status} />
      </div>
      <ul className="mt-3 flex flex-wrap gap-2 text-xs">
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Thread: {run.threadId ?? "—"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Raw status: {run.rawStatus ?? "unknown"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Worktree: {run.worktreeId ?? "Not exposed"}
        </li>
      </ul>
    </li>
  );
}

function ApprovalRow({ approval }: { approval: GuardianApprovalItem }) {
  return (
    <li
      className="rounded-xl border px-3 py-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {approval.operation}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {approval.target ?? "No target exposed"}
          </div>
        </div>
        <StatusBadge status={approval.status} />
      </div>
      <ul className="mt-3 flex flex-wrap gap-2 text-xs">
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Requested by: {approval.requestedBy ?? "unknown"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Requested: {formatTimestamp(approval.createdAt) ?? "Not exposed"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Reason: {approval.requestReason ?? "Not provided"}
        </li>
      </ul>
    </li>
  );
}

function RecentTaskRow({ item }: { item: GuardianRecentTaskItem }) {
  return (
    <li
      className="rounded-xl border px-3 py-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {item.label}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {item.source}
          </div>
        </div>
        <StatusBadge status={item.status} />
      </div>
      <div className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
        {item.detail || "No additional detail exposed"}
      </div>
      <div className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
        {formatTimestamp(item.timestamp) ?? "Timestamp not exposed"}
      </div>
    </li>
  );
}

export default function GuardianActionCenter({
  className,
  threadId,
}: GuardianActionCenterProps) {
  const { error, hasLoaded, loading, reload, snapshot } =
    useGuardianActionCenter({ threadId });
  const reloadLabel = error && !snapshot ? "Retry" : hasLoaded ? "Reload action center" : "Retry";

  return (
    <section
      className={[
        "space-y-4 rounded-2xl border p-4 sm:p-5",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 88%, transparent)",
        borderColor: "var(--panel-border)",
      }}
      data-testid="guardian-action-center"
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Guardian Action Center
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Read-only operator visibility across scheduled jobs, delegation runs,
          pending approvals, and recent task outcomes. Unsupported sources are
          marked explicitly instead of being inferred.
        </p>
      </div>

      <div
        className="rounded-xl border px-3 py-2 text-sm"
        style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
      >
        This view is read-only in this task. Use it to inspect current Guardian
        operational state, then reload when you need a fresh snapshot.
      </div>

      {loading ? (
        <div
          className="rounded-xl border px-3 py-4 text-sm"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          role="status"
        >
          Loading Guardian Action Center…
        </div>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          <SectionShell title="Scheduled Jobs">
            <SectionState
              section={
                snapshot?.scheduledJobs ?? {
                  availability: "unavailable",
                  items: [],
                  message: "Scheduled jobs unavailable",
                }
              }
              renderItem={(job) => <ScheduledJobRow key={job.id} job={job} />}
            />
          </SectionShell>

          <SectionShell title="Agent / Delegation Runs">
            <SectionState
              section={
                snapshot?.agentRuns ?? {
                  availability: "unavailable",
                  items: [],
                  message: "Delegation runs unavailable",
                }
              }
              renderItem={(run) => <AgentRunRow key={run.runId} run={run} />}
            />
          </SectionShell>

          <SectionShell title="Pending Approvals / Blocked Actions">
            <SectionState
              section={
                snapshot?.pendingApprovals ?? {
                  availability: "unavailable",
                  items: [],
                  message: "Pending approvals unavailable",
                }
              }
              renderItem={(approval) => (
                <ApprovalRow key={approval.id} approval={approval} />
              )}
            />
          </SectionShell>

          <SectionShell title="Recent Task Status">
            <SectionState
              section={
                snapshot?.recentTaskStatus ?? {
                  availability: "unavailable",
                  items: [],
                  message: "Recent task status unavailable",
                }
              }
              renderItem={(item) => <RecentTaskRow key={item.id} item={item} />}
            />
          </SectionShell>
        </div>
      )}

      {error ? (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(239, 68, 68, 0.35)",
            background: "rgba(239, 68, 68, 0.12)",
            color: "var(--text)",
          }}
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <div className="flex justify-end">
        <Button
          type="button"
          variant="ghost"
          className="border border-[var(--panel-border)]"
          onClick={() => void reload()}
          disabled={loading}
        >
          {reloadLabel}
        </Button>
      </div>
    </section>
  );
}
