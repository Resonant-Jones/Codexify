import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Input from "@/components/ui/input";
import Textarea from "@/components/ui/textarea";

import useCodingWorkOrders from "@/features/commandCenter/hooks/useCodingWorkOrders";
import useOrchestratorRecommendations from "@/features/commandCenter/hooks/useOrchestratorRecommendations";
import type {
  CommandCenterCodingWorkOrder,
  CommandCenterWorkOrderCreateInput,
} from "@/features/commandCenter/types";

const TERMINAL_WORK_ORDER_STATUSES = new Set([
  "failed",
  "merged",
  "archived",
  "cancelled",
]);

const ACTIVEISH_WORK_ORDER_STATUSES = new Set([
  "ready",
  "leased",
  "running",
  "validating",
  "retrying",
]);

const IN_PROGRESS_WORK_ORDER_STATUSES = new Set([
  "leased",
  "running",
  "validating",
  "retrying",
]);

const BLOCKEDISH_WORK_ORDER_STATUSES = new Set(["blocked", "escalated"]);
const FAILED_OR_CANCELLED_STATUSES = new Set(["failed", "cancelled"]);

const PREVIEW_CHAR_LIMIT = 160;
const CHIP_CHAR_LIMIT = 96;

type BadgeTone = "active" | "attention" | "danger" | "info" | "subtle";

type JsonRecord = Record<string, unknown>;

type RunnerEvidence = {
  commitGateStatus: string | null;
  commitHash: string | null;
  leasePath: string | null;
  leaseStatus: string | null;
  mergeReady: boolean | null;
  resultStatus: string | null;
  validationAttempts: number | null;
  validationStatus: string | null;
  validationStopReason: string | null;
};

type EnrichedWorkOrder = {
  evidence: RunnerEvidence;
  order: CommandCenterCodingWorkOrder;
};

function statusTone(status: string): BadgeTone {
  if (status === "merge_ready" || status === "passed" || status === "merged") {
    return "active";
  }
  if (status === "failed") return "danger";
  if (BLOCKEDISH_WORK_ORDER_STATUSES.has(status)) return "attention";
  if (ACTIVEISH_WORK_ORDER_STATUSES.has(status) || status === "draft") {
    return "info";
  }
  return "subtle";
}

function toneStyle(tone: BadgeTone): React.CSSProperties {
  switch (tone) {
    case "active":
      return {
        background: "var(--accent-weak)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 35%, var(--panel-border))",
        color: "var(--text-on-accent)",
      };
    case "attention":
      return {
        background: "color-mix(in oklab, var(--chip-bg) 82%, var(--accent-strong) 18%)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 42%, var(--panel-border))",
        color: "var(--text)",
      };
    case "danger":
      return {
        background: "var(--danger-surface)",
        borderColor: "var(--danger-border)",
        color: "var(--danger-text)",
      };
    case "info":
      return {
        background: "var(--info-surface)",
        borderColor: "var(--panel-border)",
        color: "var(--info-text)",
      };
    case "subtle":
    default:
      return {
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
      };
  }
}

function formatStatus(status: string): string {
  const normalized = status.trim().replace(/_/g, " ");
  if (!normalized) return "Unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function truncateText(value: string | null | undefined, maxChars: number): string {
  const normalized = String(value ?? "").trim();
  if (!normalized) return "";
  if (normalized.length <= maxChars) return normalized;
  return `${normalized.slice(0, maxChars - 1)}…`;
}

function parseFileScopeInput(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\n,]/g)
        .map((token) => token.trim())
        .filter(Boolean)
    )
  );
}

function formatListPreview(values: string[], previewLimit = 3, maxChars = CHIP_CHAR_LIMIT): string {
  if (values.length === 0) return "None declared";
  const trimmed = values.map((value) => value.trim()).filter(Boolean);
  if (trimmed.length === 0) return "None declared";
  const preview = trimmed.slice(0, previewLimit).join(", ");
  const suffix = trimmed.length > previewLimit ? ` +${trimmed.length - previewLimit} more` : "";
  return truncateText(`${preview}${suffix}`, maxChars);
}

function isNonTerminalStatus(status: string): boolean {
  return !TERMINAL_WORK_ORDER_STATUSES.has(status);
}

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as JsonRecord;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function asBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  return null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return null;
}

function readPath(record: JsonRecord | null, ...path: string[]): unknown {
  let current: unknown = record;
  for (const key of path) {
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      return undefined;
    }
    current = (current as JsonRecord)[key];
  }
  return current;
}

function extractRunnerEvidence(order: CommandCenterCodingWorkOrder): RunnerEvidence {
  const meta = asRecord(order.extra_meta);
  const validationSummary = asRecord(readPath(meta, "validation_summary"));
  const latestResult = asRecord(readPath(meta, "latest_result"));
  const latestLease = asRecord(readPath(meta, "latest_lease"));
  const commitGate = asRecord(readPath(meta, "commit_gate"));

  const validationStatus =
    asString(readPath(meta, "final_validation_status")) ??
    asString(readPath(validationSummary, "final_validation_status")) ??
    asString(readPath(latestResult, "final_validation_status")) ??
    asString(readPath(latestResult, "validation_status"));

  const validationAttempts =
    asNumber(readPath(meta, "validation_attempt_count")) ??
    asNumber(readPath(validationSummary, "validation_attempt_count"));

  const validationStopReason =
    asString(readPath(meta, "validation_stop_reason")) ??
    asString(readPath(validationSummary, "validation_stop_reason"));

  const commitGateStatus =
    asString(readPath(meta, "commit_status")) ??
    asString(readPath(meta, "commit_gate_status")) ??
    asString(readPath(commitGate, "status")) ??
    asString(readPath(latestResult, "commit_status"));

  const commitHash =
    asString(readPath(meta, "commit_hash")) ??
    asString(readPath(commitGate, "commit_hash")) ??
    asString(readPath(latestResult, "commit_hash"));

  const mergeReady =
    asBoolean(readPath(meta, "merge_ready")) ??
    asBoolean(readPath(commitGate, "merge_ready")) ??
    (order.status === "merge_ready" || order.status === "merged" ? true : null);

  const leaseStatus =
    asString(readPath(meta, "lease_status")) ??
    asString(readPath(latestLease, "status"));

  const leasePath =
    asString(readPath(meta, "worktree_path")) ??
    asString(readPath(latestLease, "worktree_path"));

  const resultStatus =
    asString(readPath(meta, "result_status")) ??
    asString(readPath(meta, "coding_result_status")) ??
    asString(readPath(latestResult, "status"));

  return {
    commitGateStatus,
    commitHash,
    leasePath,
    leaseStatus,
    mergeReady,
    resultStatus,
    validationAttempts,
    validationStatus,
    validationStopReason,
  };
}

function renderEvidenceText(value: string | null): string {
  return value ? formatStatus(value) : "Not reported";
}

function renderEvidenceBoolean(value: boolean | null): string {
  if (value === null) return "Not reported";
  return value ? "Yes" : "No";
}

function SummaryCard({
  label,
  value,
  testId,
  tone = "subtle",
}: {
  label: string;
  testId: string;
  tone?: BadgeTone;
  value: string | number;
}) {
  return (
    <div
      className="rounded-[var(--tile-radius)] border px-3 py-2"
      data-testid={testId}
      style={{
        ...toneStyle(tone),
        borderStyle: "solid",
      }}
    >
      <div className="text-[10px] uppercase tracking-[0.14em]">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

function WorkOrderMeta({
  evidence,
  order,
}: {
  evidence: RunnerEvidence;
  order: CommandCenterCodingWorkOrder;
}) {
  const scopePreview = formatListPreview(order.file_scope);
  const dependencyPreview = formatListPreview(order.dependency_ids, 2);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          Priority {order.priority}
        </span>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          Adapter: {truncateText(order.adapter_kind || "Not reported", CHIP_CHAR_LIMIT)}
        </span>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          Validate: {truncateText(order.validation_command || "Not reported", CHIP_CHAR_LIMIT)}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          File scope: {scopePreview}
        </span>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          Dependencies: {dependencyPreview}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        <span>Run: {truncateText(order.latest_run_id || "Not reported", CHIP_CHAR_LIMIT)}</span>
        <span>Lease: {truncateText(order.latest_lease_id || "Not reported", CHIP_CHAR_LIMIT)}</span>
        <span>Receipt: {truncateText(order.latest_receipt_id || "Not reported", CHIP_CHAR_LIMIT)}</span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        <span>Validation: {renderEvidenceText(evidence.validationStatus)}</span>
        <span>Commit gate: {renderEvidenceText(evidence.commitGateStatus)}</span>
        <span>Merge ready: {renderEvidenceBoolean(evidence.mergeReady)}</span>
      </div>
    </div>
  );
}

export default function CodingWorkOrdersPanel() {
  const {
    cancelWorkOrder,
    createWorkOrder,
    error: workOrderError,
    fetchWorkOrderDetail,
    items,
    loading: workOrderLoading,
    refresh: refreshWorkOrders,
  } = useCodingWorkOrders();

  const {
    decisionReasons,
    error: recommendationError,
    loading: recommendationsLoading,
    recommendations,
    refresh: refreshRecommendations,
    skipped,
  } = useOrchestratorRecommendations({ limit: 5 });

  const [title, setTitle] = React.useState("");
  const [objective, setObjective] = React.useState("");
  const [campaignId, setCampaignId] = React.useState("");
  const [validationCommand, setValidationCommand] = React.useState("");
  const [adapterKind, setAdapterKind] = React.useState("");
  const [priority, setPriority] = React.useState("0");
  const [fileScopeInput, setFileScopeInput] = React.useState("");
  const [requireWorktreeLease, setRequireWorktreeLease] = React.useState(false);
  const [commitAfterValidation, setCommitAfterValidation] = React.useState(false);
  const [requireHumanReviewBeforeMerge, setRequireHumanReviewBeforeMerge] = React.useState(true);
  const [submitting, setSubmitting] = React.useState(false);
  const [createFormExpanded, setCreateFormExpanded] = React.useState(false);
  const [cancelingId, setCancelingId] = React.useState<string | null>(null);
  const [showSkippedReasons, setShowSkippedReasons] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [actionNotice, setActionNotice] = React.useState<string | null>(null);
  const [selectedWorkOrderId, setSelectedWorkOrderId] = React.useState<string | null>(null);
  const [selectedWorkOrder, setSelectedWorkOrder] =
    React.useState<CommandCenterCodingWorkOrder | null>(null);
  const [selectedWorkOrderLoading, setSelectedWorkOrderLoading] = React.useState(false);
  const [selectedWorkOrderError, setSelectedWorkOrderError] = React.useState<string | null>(null);

  const enrichedWorkOrders = React.useMemo<EnrichedWorkOrder[]>(
    () => items.map((order) => ({ evidence: extractRunnerEvidence(order), order })),
    [items]
  );

  const summary = React.useMemo(() => {
    const ready = items.filter((item) => item.status === "ready").length;
    const activeish = items.filter((item) => ACTIVEISH_WORK_ORDER_STATUSES.has(item.status)).length;
    const blocked = items.filter((item) => BLOCKEDISH_WORK_ORDER_STATUSES.has(item.status)).length;
    const mergeReady = items.filter((item) => item.status === "merge_ready").length;
    return {
      activeish,
      blocked,
      mergeReady,
      ready,
      total: items.length,
    };
  }, [items]);

  const runnerSummary = React.useMemo(() => {
    const openReady = items.filter((item) => isNonTerminalStatus(item.status)).length;
    const inProgress = items.filter((item) => IN_PROGRESS_WORK_ORDER_STATUSES.has(item.status)).length;
    const failedCancelled = items.filter((item) => FAILED_OR_CANCELLED_STATUSES.has(item.status)).length;

    const leaseBound = items.filter((item) => item.require_worktree_lease).length;
    const leaseReported = enrichedWorkOrders.filter(
      ({ evidence, order }) => Boolean(order.latest_lease_id || evidence.leaseStatus || evidence.leasePath)
    ).length;
    const validationReported = enrichedWorkOrders.filter(
      ({ evidence }) => Boolean(evidence.validationStatus)
    ).length;
    const commitGateReported = enrichedWorkOrders.filter(
      ({ evidence }) => Boolean(evidence.commitGateStatus || evidence.commitHash)
    ).length;
    const mergeReadyReported = items.filter((item) => item.status === "merge_ready" || item.status === "merged").length;

    return {
      commitGateReported,
      failedCancelled,
      inProgress,
      leaseBound,
      leaseReported,
      mergeReadyReported,
      openReady,
      validationReported,
    };
  }, [enrichedWorkOrders, items]);

  React.useEffect(() => {
    if (items.length === 0) {
      setSelectedWorkOrderId(null);
      setSelectedWorkOrder(null);
      setSelectedWorkOrderError(null);
      setSelectedWorkOrderLoading(false);
      return;
    }
    if (!selectedWorkOrderId || !items.some((item) => item.work_order_id === selectedWorkOrderId)) {
      setSelectedWorkOrderId(items[0].work_order_id);
    }
  }, [items, selectedWorkOrderId]);

  React.useEffect(() => {
    let cancelled = false;
    if (!selectedWorkOrderId) return () => {};
    setSelectedWorkOrderLoading(true);
    setSelectedWorkOrderError(null);
    void fetchWorkOrderDetail(selectedWorkOrderId)
      .then((detail) => {
        if (cancelled) return;
        setSelectedWorkOrder(detail);
      })
      .catch((detailError) => {
        if (cancelled) return;
        setSelectedWorkOrder(null);
        setSelectedWorkOrderError(
          detailError instanceof Error && detailError.message
            ? detailError.message
            : "Unable to load work-order detail."
        );
      })
      .finally(() => {
        if (!cancelled) setSelectedWorkOrderLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchWorkOrderDetail, selectedWorkOrderId]);

  const selectedEvidence = React.useMemo(
    () => (selectedWorkOrder ? extractRunnerEvidence(selectedWorkOrder) : null),
    [selectedWorkOrder]
  );

  const onSubmit = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setActionError(null);
      setActionNotice(null);

      const trimmedTitle = title.trim();
      const trimmedObjective = objective.trim();
      if (!trimmedTitle || !trimmedObjective) {
        setActionError("Title and objective are required.");
        return;
      }

      const parsedPriority = Number.parseInt(priority.trim(), 10);
      const payload: CommandCenterWorkOrderCreateInput = {
        adapter_kind: adapterKind.trim() || undefined,
        campaign_id: campaignId.trim() || undefined,
        commit_after_validation: commitAfterValidation,
        file_scope: parseFileScopeInput(fileScopeInput),
        objective: trimmedObjective,
        priority: Number.isFinite(parsedPriority) ? parsedPriority : 0,
        require_human_review_before_merge: requireHumanReviewBeforeMerge,
        require_worktree_lease: requireWorktreeLease,
        title: trimmedTitle,
        validation_command: validationCommand.trim() || undefined,
      };

      setSubmitting(true);
      try {
        await createWorkOrder(payload);
        setTitle("");
        setObjective("");
        setCampaignId("");
        setValidationCommand("");
        setAdapterKind("");
        setPriority("0");
        setFileScopeInput("");
        setRequireWorktreeLease(false);
        setCommitAfterValidation(false);
        setRequireHumanReviewBeforeMerge(true);
        setActionNotice("Work order created.");
      } catch (submitError) {
        setActionError(
          submitError instanceof Error && submitError.message
            ? submitError.message
            : "Unable to create work order."
        );
      } finally {
        setSubmitting(false);
      }
    },
    [
      adapterKind,
      campaignId,
      commitAfterValidation,
      createWorkOrder,
      fileScopeInput,
      objective,
      priority,
      requireHumanReviewBeforeMerge,
      requireWorktreeLease,
      title,
      validationCommand,
    ]
  );

  const onCancel = React.useCallback(
    async (workOrderId: string) => {
      setActionError(null);
      setActionNotice(null);
      setCancelingId(workOrderId);
      try {
        await cancelWorkOrder(workOrderId, "operator_cancelled_from_command_center");
        setActionNotice(`Work order ${workOrderId} cancelled.`);
      } catch (cancelError) {
        setActionError(
          cancelError instanceof Error && cancelError.message
            ? cancelError.message
            : "Unable to cancel work order."
        );
      } finally {
        setCancelingId(null);
      }
    },
    [cancelWorkOrder]
  );

  return (
    <div className="space-y-4">
      <section
        className="rounded-[var(--tile-radius)] border px-4 py-3"
        data-testid="command-center-agent-lens-header"
        style={{
          borderColor: "color-mix(in oklab, var(--accent-strong) 18%, var(--panel-border))",
          background:
            "linear-gradient(105deg, color-mix(in oklab, var(--accent-weak) 14%, var(--panel-bg)), color-mix(in oklab, var(--panel-bg) 96%, transparent))",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08)",
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <h2
              className="text-base font-semibold leading-tight"
              data-testid="command-center-agent-lens-title"
              style={{ color: "var(--text)" }}
            >
              Agent Command Center
            </h2>
            <p
              className="text-xs leading-5"
              data-testid="command-center-agent-lens-subtitle"
              style={{ color: "var(--muted)" }}
            >
              Watch/create/cancel/recommendation-only surface. Dispatch, lease allocation, merge automation, and terminal execution are not enabled here.
            </p>
          </div>

          <div className="flex flex-wrap gap-2" data-testid="command-center-agent-lens-chips">
            <Badge
              className="border text-[11px] font-medium"
              data-testid="command-center-agent-chip-work-orders"
              style={toneStyle("info")}
            >
              Work orders: {summary.total}
            </Badge>
            <Badge
              className="border text-[11px] font-medium"
              data-testid="command-center-agent-chip-recommendations"
              style={toneStyle("subtle")}
            >
              Recommendation posture: advisory only
            </Badge>
            <Badge
              className="border text-[11px] font-medium"
              data-testid="command-center-agent-chip-dispatch"
              style={toneStyle("attention")}
            >
              Dispatch: disabled
            </Badge>
          </div>
        </div>
      </section>

      <Card
        className="bezel-none border"
        data-testid="coding-work-orders-panel"
        style={{
          background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
          borderColor: "var(--panel-border)",
        }}
      >
        <CardHeader className="space-y-2 border-b border-[var(--panel-border)] pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="space-y-1">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                Worker Control
              </div>
              <CardTitle className="text-base" style={{ color: "var(--text)" }}>
                Automated Worker Control Plane
              </CardTitle>
            </div>
            <div className="flex gap-2">
              <Button size="sm" type="button" variant="ghost" onClick={() => void refreshWorkOrders()}>
                {workOrderLoading ? "Refreshing…" : "Refresh work orders"}
              </Button>
              <Button size="sm" type="button" variant="ghost" onClick={() => void refreshRecommendations()}>
                {recommendationsLoading ? "Refreshing…" : "Refresh recommendations"}
              </Button>
            </div>
          </div>
          <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
            Work orders are durable control-plane state. Recommendations are read-only guidance. Dispatch, lease allocation, merge automation, and worker launch are not enabled in this panel.
          </p>
        </CardHeader>

        <CardContent className="space-y-4 p-[var(--card-pad)]">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5" data-testid="command-center-work-order-summary-cards">
            <SummaryCard label="Total" testId="command-center-work-order-summary-total" tone="subtle" value={summary.total} />
            <SummaryCard label="Ready" testId="command-center-work-order-summary-ready" tone="info" value={summary.ready} />
            <SummaryCard label="Active-ish" testId="command-center-work-order-summary-active" tone="info" value={summary.activeish} />
            <SummaryCard label="Blocked/escalated" testId="command-center-work-order-summary-blocked" tone="attention" value={summary.blocked} />
            <SummaryCard label="Merge-ready" testId="command-center-work-order-summary-merge-ready" tone="active" value={summary.mergeReady} />
          </div>

          <section
            className="space-y-2 rounded-[var(--tile-radius)] border p-3"
            data-testid="command-center-runner-supervision-summary"
            style={{
              borderColor: "color-mix(in oklab, var(--accent-strong) 25%, var(--panel-border))",
              background:
                "linear-gradient(120deg, color-mix(in oklab, var(--surface-soft) 88%, var(--panel-bg)), color-mix(in oklab, var(--panel-bg) 95%, transparent))",
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Runner Supervision
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                Recommendation-only visibility. No dispatch or lease allocation actions.
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" data-testid="command-center-runner-supervision-cards">
              <SummaryCard
                label="Open / ready"
                testId="command-center-runner-summary-open-ready"
                tone="info"
                value={`${runnerSummary.openReady} / ${summary.ready}`}
              />
              <SummaryCard
                label="In progress"
                testId="command-center-runner-summary-in-progress"
                tone={runnerSummary.inProgress > 0 ? "info" : "subtle"}
                value={runnerSummary.inProgress}
              />
              <SummaryCard
                label="Failed / cancelled"
                testId="command-center-runner-summary-failed-cancelled"
                tone={runnerSummary.failedCancelled > 0 ? "danger" : "subtle"}
                value={runnerSummary.failedCancelled}
              />
              <SummaryCard
                label="Recommendations"
                testId="command-center-runner-summary-recommendations"
                tone={recommendations.length > 0 ? "active" : "subtle"}
                value={recommendations.length > 0 ? `${recommendations.length} available` : "None"}
              />
              <SummaryCard
                label="Lease-bound"
                testId="command-center-runner-summary-lease"
                tone={runnerSummary.leaseBound > 0 ? "attention" : "subtle"}
                value={
                  runnerSummary.leaseReported > 0
                    ? `${runnerSummary.leaseBound} policy / ${runnerSummary.leaseReported} reported`
                    : "Not reported"
                }
              />
              <SummaryCard
                label="Validation"
                testId="command-center-runner-summary-validation"
                tone={runnerSummary.validationReported > 0 ? "info" : "subtle"}
                value={
                  runnerSummary.validationReported > 0
                    ? `${runnerSummary.validationReported} reported`
                    : "Not reported"
                }
              />
              <SummaryCard
                label="Commit gate"
                testId="command-center-runner-summary-commit-gate"
                tone={runnerSummary.commitGateReported > 0 ? "info" : "subtle"}
                value={
                  runnerSummary.commitGateReported > 0
                    ? `${runnerSummary.commitGateReported} reported`
                    : "Not reported"
                }
              />
              <SummaryCard
                label="Merge-ready"
                testId="command-center-runner-summary-merge-ready"
                tone={runnerSummary.mergeReadyReported > 0 ? "active" : "subtle"}
                value={
                  runnerSummary.mergeReadyReported > 0
                    ? `${runnerSummary.mergeReadyReported}`
                    : "Not reported"
                }
              />
            </div>
          </section>

          <div
            className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            data-testid="command-center-worker-control-card"
            style={{
              borderColor: "color-mix(in oklab, var(--accent-strong) 28%, var(--panel-border))",
              background:
                "linear-gradient(120deg, color-mix(in oklab, var(--panel-bg) 94%, transparent), color-mix(in oklab, var(--surface-soft) 76%, transparent))",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06)",
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Create work order
              </div>
              <Button
                size="sm"
                type="button"
                variant="ghost"
                onClick={() => setCreateFormExpanded((current) => !current)}
              >
                {createFormExpanded ? "Collapse form" : "Expand form"}
              </Button>
            </div>
            <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              Keep this bounded for operator speed. Expand to set full task metadata.
            </p>

            <form
              className={createFormExpanded ? "space-y-3" : "hidden"}
              data-testid="coding-work-order-create-form"
              onSubmit={onSubmit}
            >
              <div className="grid gap-2">
                <label className="text-xs" htmlFor="coding-wo-title" style={{ color: "var(--muted)" }}>
                  Title
                </label>
                <Input
                  id="coding-wo-title"
                  onChange={(event) => setTitle(event.target.value)}
                  value={title}
                />
              </div>

              <div className="grid gap-2">
                <label className="text-xs" htmlFor="coding-wo-objective" style={{ color: "var(--muted)" }}>
                  Objective
                </label>
                <Textarea
                  id="coding-wo-objective"
                  onChange={(event) => setObjective(event.target.value)}
                  rows={3}
                  value={objective}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="grid gap-2">
                  <label className="text-xs" htmlFor="coding-wo-campaign-id" style={{ color: "var(--muted)" }}>
                    Campaign ID (optional)
                  </label>
                  <Input
                    id="coding-wo-campaign-id"
                    onChange={(event) => setCampaignId(event.target.value)}
                    value={campaignId}
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-xs" htmlFor="coding-wo-priority" style={{ color: "var(--muted)" }}>
                    Priority
                  </label>
                  <Input
                    id="coding-wo-priority"
                    onChange={(event) => setPriority(event.target.value)}
                    type="number"
                    value={priority}
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="grid gap-2">
                  <label className="text-xs" htmlFor="coding-wo-validation-command" style={{ color: "var(--muted)" }}>
                    Validation command (optional)
                  </label>
                  <Input
                    id="coding-wo-validation-command"
                    onChange={(event) => setValidationCommand(event.target.value)}
                    value={validationCommand}
                  />
                </div>
                <div className="grid gap-2">
                  <label className="text-xs" htmlFor="coding-wo-adapter-kind" style={{ color: "var(--muted)" }}>
                    Adapter kind (optional)
                  </label>
                  <Input
                    id="coding-wo-adapter-kind"
                    onChange={(event) => setAdapterKind(event.target.value)}
                    value={adapterKind}
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <label className="text-xs" htmlFor="coding-wo-file-scope" style={{ color: "var(--muted)" }}>
                  File scope (comma or newline separated)
                </label>
                <Textarea
                  id="coding-wo-file-scope"
                  onChange={(event) => setFileScopeInput(event.target.value)}
                  rows={3}
                  value={fileScopeInput}
                />
              </div>

              <div className="grid gap-2 text-xs" style={{ color: "var(--muted)" }}>
                <label className="inline-flex items-center gap-2">
                  <input
                    checked={requireWorktreeLease}
                    className="h-4 w-4 rounded border"
                    onChange={(event) => setRequireWorktreeLease(event.target.checked)}
                    type="checkbox"
                  />
                  Require worktree lease
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    checked={commitAfterValidation}
                    className="h-4 w-4 rounded border"
                    onChange={(event) => setCommitAfterValidation(event.target.checked)}
                    type="checkbox"
                  />
                  Commit after validation
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    checked={requireHumanReviewBeforeMerge}
                    className="h-4 w-4 rounded border"
                    onChange={(event) => setRequireHumanReviewBeforeMerge(event.target.checked)}
                    type="checkbox"
                  />
                  Require human review before merge
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button disabled={submitting} type="submit">
                  {submitting ? "Creating…" : "Create work order"}
                </Button>
                {actionNotice ? (
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    {actionNotice}
                  </span>
                ) : null}
              </div>

              {actionError ? (
                <div
                  className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
                  style={{
                    background: "var(--danger-surface)",
                    borderColor: "var(--danger-border)",
                    color: "var(--danger-text)",
                  }}
                >
                  {actionError}
                </div>
              ) : null}
            </form>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-4">
              <div
                className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
                data-testid="command-center-work-orders-card"
                style={{
                  borderColor: "var(--panel-border)",
                  background: "color-mix(in oklab, var(--surface-soft) 90%, var(--panel-bg))",
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    Work orders
                  </div>
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    {items.length} total
                  </span>
                </div>

                {workOrderLoading ? (
                  <div className="text-sm" style={{ color: "var(--muted)" }}>
                    Loading work orders…
                  </div>
                ) : null}

                {workOrderError ? (
                  <div
                    className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
                    style={{
                      background: "var(--danger-surface)",
                      borderColor: "var(--danger-border)",
                      color: "var(--danger-text)",
                    }}
                  >
                    {workOrderError}
                  </div>
                ) : null}

                {!workOrderLoading && items.length === 0 ? (
                  <div className="text-sm" style={{ color: "var(--muted)" }}>
                    No coding work orders yet. Expand the create form above to add one.
                  </div>
                ) : null}

                <div className="max-h-[20rem] space-y-2 overflow-auto pr-1">
                  {enrichedWorkOrders.map(({ evidence, order }) => (
                    <div
                      key={order.work_order_id}
                      className="space-y-2 rounded-[var(--tile-radius)] border p-3"
                      data-testid="coding-work-order-row"
                      style={{
                        borderColor:
                          order.work_order_id === selectedWorkOrderId
                            ? "var(--accent)"
                            : "var(--panel-border)",
                        background: "var(--surface-soft)",
                      }}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0 space-y-1">
                          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                            {truncateText(order.title, PREVIEW_CHAR_LIMIT)}
                          </div>
                          <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                            {truncateText(order.objective, PREVIEW_CHAR_LIMIT) || "No objective provided."}
                          </div>
                          <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                            ID: {truncateText(order.work_order_id, CHIP_CHAR_LIMIT)}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Badge className="border text-[11px] font-medium" style={toneStyle(statusTone(order.status))}>
                            {formatStatus(order.status)}
                          </Badge>
                          <Badge className="border text-[11px] font-medium" style={toneStyle("subtle")}>
                            Priority {order.priority}
                          </Badge>
                        </div>
                      </div>

                      <WorkOrderMeta evidence={evidence} order={order} />

                      {order.blocked_reason ? (
                        <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                          Blocked reason: {truncateText(order.blocked_reason, PREVIEW_CHAR_LIMIT)}
                        </div>
                      ) : null}

                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={() => setSelectedWorkOrderId(order.work_order_id)}
                          size="sm"
                          type="button"
                          variant="ghost"
                        >
                          {order.work_order_id === selectedWorkOrderId ? "Inspecting" : "Inspect detail"}
                        </Button>
                        {isNonTerminalStatus(order.status) ? (
                          <Button
                            aria-label={`Cancel ${order.work_order_id}`}
                            disabled={cancelingId === order.work_order_id}
                            onClick={() => void onCancel(order.work_order_id)}
                            size="sm"
                            type="button"
                            variant="ghost"
                          >
                            {cancelingId === order.work_order_id ? "Cancelling…" : "Cancel"}
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div
                className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
                data-testid="command-center-work-order-detail-card"
                style={{
                  borderColor: "var(--panel-border)",
                  background: "color-mix(in oklab, var(--surface-soft) 90%, var(--panel-bg))",
                }}
              >
                <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  Runner detail
                </div>
                {selectedWorkOrderLoading ? (
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Loading detail…
                  </div>
                ) : null}
                {selectedWorkOrderError ? (
                  <div className="text-xs" style={{ color: "var(--danger-text)" }}>
                    {selectedWorkOrderError}
                  </div>
                ) : null}
                {!selectedWorkOrderLoading && !selectedWorkOrder && !selectedWorkOrderError ? (
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Select a work order to inspect durable detail.
                  </div>
                ) : null}

                {selectedWorkOrder && selectedEvidence ? (
                  <div className="grid gap-2 text-xs" style={{ color: "var(--muted)" }}>
                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div style={{ color: "var(--text)" }}>
                        {truncateText(selectedWorkOrder.title, PREVIEW_CHAR_LIMIT)}
                      </div>
                      <div className="mt-1 leading-5">
                        {truncateText(selectedWorkOrder.objective, 320) || "No objective provided."}
                      </div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Status: {formatStatus(selectedWorkOrder.status)}</div>
                      <div>Acceptance scope: {truncateText(selectedWorkOrder.scope || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Blocked reason: {truncateText(selectedWorkOrder.blocked_reason || "Not reported", CHIP_CHAR_LIMIT)}</div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Validation command: {truncateText(selectedWorkOrder.validation_command || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Validation status: {renderEvidenceText(selectedEvidence.validationStatus)}</div>
                      <div>
                        Validation attempts:{" "}
                        {selectedEvidence.validationAttempts !== null ? selectedEvidence.validationAttempts : "Not reported"}
                      </div>
                      <div>Validation stop reason: {truncateText(selectedEvidence.validationStopReason || "Not reported", CHIP_CHAR_LIMIT)}</div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Dependencies: {formatListPreview(selectedWorkOrder.dependency_ids, 4, 220)}</div>
                      <div>File scope: {formatListPreview(selectedWorkOrder.file_scope, 4, 220)}</div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Latest run: {truncateText(selectedWorkOrder.latest_run_id || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Latest receipt: {truncateText(selectedWorkOrder.latest_receipt_id || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Latest lease: {truncateText(selectedWorkOrder.latest_lease_id || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Lease status: {renderEvidenceText(selectedEvidence.leaseStatus)}</div>
                      <div>Lease worktree path: {truncateText(selectedEvidence.leasePath || "Not reported", CHIP_CHAR_LIMIT)}</div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Commit gate status: {renderEvidenceText(selectedEvidence.commitGateStatus)}</div>
                      <div>Commit hash: {truncateText(selectedEvidence.commitHash || "Not reported", CHIP_CHAR_LIMIT)}</div>
                      <div>Merge-ready evidence: {renderEvidenceBoolean(selectedEvidence.mergeReady)}</div>
                      <div>Latest result status: {renderEvidenceText(selectedEvidence.resultStatus)}</div>
                    </div>

                    <div className="rounded-[var(--tile-radius)] border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                      <div>Created: {selectedWorkOrder.created_at}</div>
                      <div>Updated: {selectedWorkOrder.updated_at}</div>
                      <div>
                        Lease required: {selectedWorkOrder.require_worktree_lease ? "yes" : "no"} · Commit after validation:{" "}
                        {selectedWorkOrder.commit_after_validation ? "yes" : "no"}
                      </div>
                      <div>
                        Human review before merge:{" "}
                        {selectedWorkOrder.require_human_review_before_merge ? "yes" : "no"}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div
              className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
              data-testid="command-center-recommendations-card"
              style={{
                borderColor: "var(--panel-border)",
                background: "color-mix(in oklab, var(--surface-soft) 90%, var(--panel-bg))",
              }}
            >
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Recommendation-only next tasks
              </div>
              <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                Recommendations are advisory only and do not dispatch workers. Refresh calls the recommendation endpoint only.
              </p>

              {recommendationsLoading ? (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  Loading recommendations…
                </div>
              ) : null}
              {recommendationError ? (
                <div
                  className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
                  style={{
                    background: "var(--danger-surface)",
                    borderColor: "var(--danger-border)",
                    color: "var(--danger-text)",
                  }}
                >
                  {recommendationError}
                </div>
              ) : null}

              <div className="max-h-[18rem] space-y-2 overflow-auto pr-1" data-testid="coding-orchestrator-recommendations">
                {recommendations.length === 0 && !recommendationsLoading ? (
                  <div className="text-sm" style={{ color: "var(--muted)" }}>
                    No recommendations available right now. This is expected when ready work is unavailable.
                  </div>
                ) : (
                  recommendations.map((recommendation) => (
                    <div
                      key={`${recommendation.work_order_id}:${recommendation.rank}`}
                      className="rounded-[var(--tile-radius)] border p-3"
                      style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)" }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          #{recommendation.rank} {recommendation.title}
                        </div>
                        <Badge className="border text-[11px] font-medium" style={toneStyle("info")}>
                          {recommendation.decision}
                        </Badge>
                      </div>
                      <div className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                        Work order: {recommendation.work_order_id} · Priority: {recommendation.priority}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {recommendation.reason_codes.map((reasonCode) => (
                          <Badge
                            key={`${recommendation.work_order_id}:${reasonCode}`}
                            className="border text-[11px]"
                            style={toneStyle("subtle")}
                          >
                            {reasonCode}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="space-y-2" data-testid="coding-orchestrator-skipped">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--muted)" }}>
                    Skipped
                  </div>
                  {skipped.length > 0 ? (
                    <Button
                      size="sm"
                      type="button"
                      variant="ghost"
                      onClick={() => setShowSkippedReasons((current) => !current)}
                    >
                      {showSkippedReasons
                        ? "Hide skipped reasons"
                        : `Show skipped reasons (${skipped.length})`}
                    </Button>
                  ) : null}
                </div>
                {skipped.length === 0 ? (
                  <div className="text-sm" style={{ color: "var(--muted)" }}>
                    No skipped work orders.
                  </div>
                ) : showSkippedReasons ? (
                  skipped.map((entry) => (
                    <div
                      key={`${entry.work_order_id}:${entry.reason_code}`}
                      className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5"
                      style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)", color: "var(--muted)" }}
                    >
                      <div style={{ color: "var(--text)" }}>
                        {entry.work_order_id} · {entry.reason_code}
                      </div>
                      <div>{truncateText(entry.message, 220)}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm" style={{ color: "var(--muted)" }}>
                    Skipped reasons are collapsed to keep recommendations scannable.
                  </div>
                )}
              </div>

              {decisionReasons.length > 0 ? (
                <div className="rounded-[var(--tile-radius)] border p-3" style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)" }}>
                  <div className="text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--muted)" }}>
                    Decision reasons
                  </div>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs" style={{ color: "var(--muted)" }}>
                    {decisionReasons.map((reason) => (
                      <li key={reason}>{truncateText(reason, 220)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
