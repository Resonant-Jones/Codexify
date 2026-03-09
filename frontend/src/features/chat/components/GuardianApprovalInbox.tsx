import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

import useGuardianApprovalInbox from "@/features/chat/hooks/useGuardianApprovalInbox";
import type {
  GuardianApprovalInboxItem,
  GuardianApprovalInboxSection,
  GuardianInterventionStatus,
} from "@/features/chat/api/approvalInbox";

type GuardianApprovalInboxProps = {
  className?: string;
  threadId?: number;
};

const STATUS_STYLE: Record<
  GuardianInterventionStatus,
  { background: string; borderColor: string }
> = {
  "Awaiting approval": {
    background: "rgba(250, 204, 21, 0.12)",
    borderColor: "rgba(250, 204, 21, 0.35)",
  },
  Blocked: {
    background: "rgba(245, 158, 11, 0.12)",
    borderColor: "rgba(245, 158, 11, 0.35)",
  },
  Escalated: {
    background: "rgba(239, 68, 68, 0.12)",
    borderColor: "rgba(239, 68, 68, 0.35)",
  },
  "Clarification needed": {
    background: "rgba(59, 130, 246, 0.12)",
    borderColor: "rgba(59, 130, 246, 0.35)",
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

function StatusBadge({ status }: { status: GuardianInterventionStatus }) {
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

function SectionState({
  renderItem,
  section,
}: {
  renderItem: (item: GuardianApprovalInboxItem) => ReactNode;
  section: GuardianApprovalInboxSection<GuardianApprovalInboxItem>;
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

function InboxRow({ item }: { item: GuardianApprovalInboxItem }) {
  return (
    <li
      className="rounded-xl border px-3 py-3"
      style={{ borderColor: "var(--panel-border)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {item.title}
          </div>
          <div className="text-xs" style={{ color: "var(--muted)" }}>
            {item.summary || "No summary available"}
          </div>
        </div>
        <StatusBadge status={item.status} />
      </div>

      <ul className="mt-3 flex flex-wrap gap-2 text-xs">
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Source: {item.sourceType}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Thread: {item.threadId ?? "—"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Run: {item.runId ?? "—"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Task: {item.taskId ?? "—"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Created: {formatTimestamp(item.createdAt) ?? "Not exposed"}
        </li>
        <li
          className="rounded-full border px-2 py-1"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          Updated: {formatTimestamp(item.updatedAt) ?? "Not exposed"}
        </li>
      </ul>

      {item.href ? (
        <div className="mt-3">
          <a
            href={item.href}
            className="text-xs underline"
            style={{ color: "var(--accent)" }}
          >
            Open source
          </a>
        </div>
      ) : null}
    </li>
  );
}

export default function GuardianApprovalInbox({
  className,
  threadId,
}: GuardianApprovalInboxProps) {
  const { error, hasLoaded, loading, reload, snapshot } =
    useGuardianApprovalInbox({ threadId });

  const allUnavailable =
    snapshot &&
    snapshot.awaitingApprovals.availability === "unavailable" &&
    snapshot.blockedActions.availability === "unavailable" &&
    snapshot.escalatedItems.availability === "unavailable" &&
    snapshot.clarificationNeeded.availability === "unavailable";

  const reloadLabel =
    error && !snapshot ? "Retry" : hasLoaded ? "Reload inbox" : "Retry";

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
      data-testid="guardian-approval-inbox"
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Guardian Approval Inbox
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Read-only intervention queue for actions that need user attention.
          This inbox surfaces pending approvals, blocked work, escalation
          candidates, and clarification-required items when existing sources
          expose them.
        </p>
      </div>

      <div
        className="rounded-xl border px-3 py-2 text-sm"
        style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
      >
        This panel is visibility-only in this task. Use reload to refresh
        state, then take action through the dedicated control surfaces.
      </div>

      {loading ? (
        <div
          className="rounded-xl border px-3 py-4 text-sm"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          role="status"
        >
          Loading approval inbox…
        </div>
      ) : (
        <>
          {allUnavailable ? (
            <div
              className="rounded-xl border px-3 py-3 text-sm"
              style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
            >
              Approval inbox unavailable
            </div>
          ) : null}

          <div className="grid gap-3 xl:grid-cols-2">
            <SectionShell title="Awaiting Approval">
              <SectionState
                section={
                  snapshot?.awaitingApprovals ?? {
                    availability: "unavailable",
                    items: [],
                    message: "Pending approvals unavailable",
                  }
                }
                renderItem={(item) => <InboxRow key={item.id} item={item} />}
              />
            </SectionShell>

            <SectionShell title="Blocked">
              <SectionState
                section={
                  snapshot?.blockedActions ?? {
                    availability: "unavailable",
                    items: [],
                    message: "Blocked actions unavailable",
                  }
                }
                renderItem={(item) => <InboxRow key={item.id} item={item} />}
              />
            </SectionShell>

            <SectionShell title="Escalated">
              <SectionState
                section={
                  snapshot?.escalatedItems ?? {
                    availability: "unavailable",
                    items: [],
                    message: "Escalation items unavailable",
                  }
                }
                renderItem={(item) => <InboxRow key={item.id} item={item} />}
              />
            </SectionShell>

            <SectionShell title="Clarification Needed">
              <SectionState
                section={
                  snapshot?.clarificationNeeded ?? {
                    availability: "unavailable",
                    items: [],
                    message: "Clarification items unavailable",
                  }
                }
                renderItem={(item) => <InboxRow key={item.id} item={item} />}
              />
            </SectionShell>
          </div>
        </>
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
