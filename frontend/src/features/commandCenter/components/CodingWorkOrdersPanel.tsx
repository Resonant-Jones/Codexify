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

const BLOCKEDISH_WORK_ORDER_STATUSES = new Set(["blocked", "escalated"]);

function statusTone(status: string): "active" | "attention" | "danger" | "info" | "subtle" {
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

function toneStyle(
  tone: "active" | "attention" | "danger" | "info" | "subtle"
): React.CSSProperties {
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
  if (!normalized) return "unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
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

function isNonTerminalStatus(status: string): boolean {
  return !TERMINAL_WORK_ORDER_STATUSES.has(status);
}

function WorkOrderMeta({ order }: { order: CommandCenterCodingWorkOrder }) {
  const scopePreview =
    order.file_scope.length <= 3
      ? order.file_scope.join(", ")
      : `${order.file_scope.slice(0, 3).join(", ")} +${order.file_scope.length - 3} more`;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
          Priority {order.priority}
        </span>
        {order.campaign_id ? (
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Campaign {order.campaign_id}
          </span>
        ) : null}
        {order.validation_command ? (
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Validate: {order.validation_command}
          </span>
        ) : null}
        {order.adapter_kind ? (
          <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
            Adapter: {order.adapter_kind}
          </span>
        ) : null}
      </div>

      <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
        {order.file_scope.length > 0 ? `File scope (${order.file_scope.length}): ${scopePreview}` : "File scope: none declared"}
      </div>

      <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
        {order.latest_run_id ? <span>Run: {order.latest_run_id}</span> : null}
        {order.latest_lease_id ? <span>Lease: {order.latest_lease_id}</span> : null}
        {order.latest_receipt_id ? <span>Receipt: {order.latest_receipt_id}</span> : null}
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

  const summary = React.useMemo(() => {
    const ready = items.filter((item) => item.status === "ready").length;
    const activeish = items.filter((item) =>
      ACTIVEISH_WORK_ORDER_STATUSES.has(item.status)
    ).length;
    const blocked = items.filter((item) =>
      BLOCKEDISH_WORK_ORDER_STATUSES.has(item.status)
    ).length;
    const mergeReady = items.filter((item) => item.status === "merge_ready").length;
    return {
      activeish,
      blocked,
      mergeReady,
      ready,
      total: items.length,
    };
  }, [items]);

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
          <CardTitle className="text-base" style={{ color: "var(--text)" }}>
            Automated Worker Control Plane
          </CardTitle>
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
          Work orders are durable control-plane state. Recommendations are read-only guidance.
          Dispatch, lease allocation, merge automation, and worker launch are not enabled in this panel.
        </p>
      </CardHeader>

      <CardContent className="space-y-4 p-[var(--card-pad)]">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)" }}>
            Total: <strong style={{ color: "var(--text)" }}>{summary.total}</strong>
          </div>
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)" }}>
            Ready: <strong style={{ color: "var(--text)" }}>{summary.ready}</strong>
          </div>
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)" }}>
            Active-ish: <strong style={{ color: "var(--text)" }}>{summary.activeish}</strong>
          </div>
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)" }}>
            Blocked/escalated: <strong style={{ color: "var(--text)" }}>{summary.blocked}</strong>
          </div>
          <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs" style={{ borderColor: "var(--panel-border)" }}>
            Merge-ready: <strong style={{ color: "var(--text)" }}>{summary.mergeReady}</strong>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <div className="space-y-4">
            <div
              className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
              style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)" }}
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
                      onChange={(event) =>
                        setRequireHumanReviewBeforeMerge(event.target.checked)
                      }
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

            <div className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]" style={{ borderColor: "var(--panel-border)" }}>
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
                {items.map((order) => (
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
                      <div className="min-w-0">
                        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          {order.title}
                        </div>
                        <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                          {order.objective}
                        </div>
                        <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                          ID: {order.work_order_id}
                        </div>
                      </div>
                      <Badge className="border text-[11px] font-medium" style={toneStyle(statusTone(order.status))}>
                        {formatStatus(order.status)}
                      </Badge>
                    </div>

                    <WorkOrderMeta order={order} />

                    {order.blocked_reason ? (
                      <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                        Blocked reason: {order.blocked_reason}
                      </div>
                    ) : null}

                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => setSelectedWorkOrderId(order.work_order_id)}
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {order.work_order_id === selectedWorkOrderId
                          ? "Inspecting"
                          : "Inspect detail"}
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

              <div
                className="space-y-2 rounded-[var(--tile-radius)] border p-3"
                style={{ borderColor: "var(--panel-border)", background: "var(--surface-soft)" }}
              >
                <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  Work-order detail
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
                {selectedWorkOrder ? (
                  <div className="space-y-1 text-xs" style={{ color: "var(--muted)" }}>
                    <div>Work order: {selectedWorkOrder.work_order_id}</div>
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
                ) : null}
              </div>
            </div>
          </div>

          <div className="space-y-3 rounded-[var(--tile-radius)] border p-[var(--card-pad)]" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Recommendation-only next tasks
            </div>
            <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
              Recommendations are advisory only. Dispatch is not implemented in this panel.
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
                    <div>{entry.message}</div>
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
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
