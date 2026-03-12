import React from "react";

import {
  buildPromptAnswerSummary,
  normalizeTracePayload,
  type CompletionDepthMode,
  type OperatorInspectionField,
  type OperatorInspectionStatus,
  type OperatorRunResult,
} from "@/lib/operatorReplay";
import { runOperatorReplay } from "@/services/operatorReplay";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const STATUS_BADGE_CLASSNAMES: Record<OperatorInspectionStatus, string> = {
  returned:
    "border border-emerald-400/40 bg-emerald-400/15 text-emerald-100",
  "not-returned":
    "border border-amber-400/40 bg-amber-400/15 text-amber-100",
  "not-exposed":
    "border border-slate-400/40 bg-slate-400/15 text-slate-100",
};

const RUN_STATUS_CLASSNAMES = {
  idle: "border border-slate-400/40 bg-slate-400/15 text-slate-100",
  running: "border border-sky-400/40 bg-sky-400/15 text-sky-100",
  succeeded: "border border-emerald-400/40 bg-emerald-400/15 text-emerald-100",
  failed: "border border-rose-400/40 bg-rose-400/15 text-rose-100",
} as const;

type RunState = "idle" | "running" | "succeeded" | "failed";

type CompletionReplayPageProps = {
  runReplay?: typeof runOperatorReplay;
};

type FormState = {
  userMessage: string;
  threadId: string;
  provider: string;
  model: string;
  depthMode: CompletionDepthMode;
};

function StatusBadge({
  status,
  children,
}: {
  status: OperatorInspectionStatus;
  children: React.ReactNode;
}) {
  return <Badge className={STATUS_BADGE_CLASSNAMES[status]}>{children}</Badge>;
}

function renderStatusLabel(status: OperatorInspectionStatus): string {
  if (status === "returned") return "Returned";
  if (status === "not-returned") return "Not Returned";
  return "Not Exposed";
}

function FieldRow({ field }: { field: OperatorInspectionField }) {
  return (
    <div className="rounded-2xl border border-[var(--panel-border)] bg-white/5 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-medium text-[var(--text)]">{field.label}</div>
        <StatusBadge status={field.status}>
          {renderStatusLabel(field.status)}
        </StatusBadge>
      </div>
      <div className="mt-2 text-sm text-[var(--muted)]">
        {field.value ?? "Unavailable for this run."}
      </div>
    </div>
  );
}

function SectionEmptyState({
  message,
}: {
  message: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--panel-border)] bg-white/4 p-4 text-sm text-[var(--muted)]">
      {message}
    </div>
  );
}

function parseThreadId(value: string): number | null {
  if (!value.trim()) return null;
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : null;
}

export function CompletionReplayPage({
  runReplay = runOperatorReplay,
}: CompletionReplayPageProps) {
  const [form, setForm] = React.useState<FormState>({
    userMessage: "",
    threadId: "",
    provider: "",
    model: "",
    depthMode: "diagnostic",
  });
  const [runState, setRunState] = React.useState<RunState>("idle");
  const [statusText, setStatusText] = React.useState(
    "Ready to inspect one completion end to end."
  );
  const [errorText, setErrorText] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<OperatorRunResult | null>(null);

  const traceSummary = React.useMemo(() => normalizeTracePayload(result?.trace ?? null), [result]);
  const promptAnswerSummary = React.useMemo(
    () => buildPromptAnswerSummary(result),
    [result]
  );

  const updateField = React.useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((current) => ({ ...current, [key]: value }));
    },
    []
  );

  const handleRun = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setErrorText(null);

      const trimmedMessage = form.userMessage.trim();
      if (!trimmedMessage) {
        setRunState("failed");
        setStatusText("Run failed before submission.");
        setErrorText("User message is required.");
        return;
      }

      if (form.threadId.trim() && parseThreadId(form.threadId) == null) {
        setRunState("failed");
        setStatusText("Run failed before submission.");
        setErrorText("Thread ID must be a positive integer.");
        return;
      }

      setRunState("running");
      setStatusText("Preparing operator replay…");
      setResult(null);

      try {
        const nextResult = await runReplay(
          {
            userMessage: trimmedMessage,
            threadId: parseThreadId(form.threadId),
            provider: form.provider.trim() || null,
            model: form.model.trim() || null,
            depthMode: form.depthMode,
          },
          {
            onProgress: (update) => setStatusText(update.message),
          }
        );

        React.startTransition(() => {
          setResult(nextResult);
          if (
            nextResult.taskTerminal?.type === "task.failed" ||
            nextResult.taskTerminal?.type === "completion.error"
          ) {
            setRunState("failed");
            setStatusText("Run failed, but partial diagnostics were collected.");
            return;
          }
          setRunState("succeeded");
          setStatusText(
            nextResult.taskWaitTimedOut
              ? "Run started; terminal worker status was not observed before timeout."
              : "Run complete. Operator diagnostics are ready."
          );
        });
      } catch (error) {
        setRunState("failed");
        setStatusText("Operator replay could not start.");
        setErrorText(
          error instanceof Error ? error.message : "Operator replay failed."
        );
      }
    },
    [form, runReplay]
  );

  return (
    <div className="space-y-4">
      <Card className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)] shadow-2xl">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Completion Replay</CardTitle>
              <p className="mt-2 max-w-3xl text-sm text-[var(--muted)]">
                This surface runs the real completion pipeline, then inspects the
                resulting task, thread, trace, and persisted answer without inventing
                diagnostics the backend did not return.
              </p>
            </div>
            <Badge className={RUN_STATUS_CLASSNAMES[runState]}>
              {runState === "idle"
                ? "Idle"
                : runState === "running"
                  ? "Running"
                  : runState === "succeeded"
                    ? "Diagnostics Ready"
                    : "Partial / Failed"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <div className="rounded-2xl border border-[var(--panel-border)] bg-white/5 p-3 text-sm text-[var(--muted)]">
            {statusText}
          </div>
          {errorText ? (
            <div
              role="alert"
              className="rounded-2xl border border-[var(--danger-border)] bg-[var(--danger-surface)] p-3 text-sm text-[var(--danger-text)]"
            >
              {errorText}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1fr)_minmax(0,1.05fr)]">
        <Card
          className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)]"
          aria-labelledby="operator-input-pane"
        >
          <CardHeader>
            <CardTitle id="operator-input-pane">
              Input / Runtime Parameters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <form className="space-y-4" onSubmit={handleRun}>
              <label className="block space-y-2 text-sm">
                <span className="font-medium text-[var(--text)]">User Message</span>
                <Textarea
                  value={form.userMessage}
                  onChange={(event) => updateField("userMessage", event.target.value)}
                  placeholder="Enter the operator message to replay through the live completion path."
                  rows={8}
                />
              </label>

              <label className="block space-y-2 text-sm">
                <span className="font-medium text-[var(--text)]">Thread ID (Optional)</span>
                <Input
                  inputMode="numeric"
                  value={form.threadId}
                  onChange={(event) => updateField("threadId", event.target.value)}
                  placeholder="Leave blank to create a fresh thread for this replay."
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2 text-sm">
                  <span className="font-medium text-[var(--text)]">Provider</span>
                  <Input
                    value={form.provider}
                    onChange={(event) => updateField("provider", event.target.value)}
                    placeholder="Optional override, for example local"
                  />
                </label>
                <label className="block space-y-2 text-sm">
                  <span className="font-medium text-[var(--text)]">Model</span>
                  <Input
                    value={form.model}
                    onChange={(event) => updateField("model", event.target.value)}
                    placeholder="Optional override, for example qwen3:14b"
                  />
                </label>
              </div>

              <label className="block space-y-2 text-sm">
                <span className="font-medium text-[var(--text)]">Retrieval Depth</span>
                <select
                  className="h-9 w-full rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 py-1 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                  value={form.depthMode}
                  onChange={(event) =>
                    updateField("depthMode", event.target.value as CompletionDepthMode)
                  }
                >
                  <option value="shallow">shallow</option>
                  <option value="normal">normal</option>
                  <option value="deep">deep</option>
                  <option value="diagnostic">diagnostic</option>
                </select>
              </label>

              <div className="flex flex-wrap gap-3">
                <Button type="submit" disabled={runState === "running"}>
                  {runState === "running" ? "Running…" : "Run"}
                </Button>
              </div>
            </form>

            <div className="rounded-2xl border border-dashed border-[var(--panel-border)] bg-white/4 p-4 text-sm text-[var(--muted)]">
              Available controls are limited to inputs the current completion API actually
              accepts. Temperature and Dry Run are not exposed by the current backend path.
            </div>

            {result ? (
              <div className="space-y-3">
                <div className="text-sm font-medium text-[var(--text)]">Current Run</div>
                <div className="grid gap-3 md:grid-cols-2">
                  <FieldRow
                    field={{
                      label: "Thread ID",
                      value: String(result.threadId),
                      status: "returned",
                    }}
                  />
                  <FieldRow
                    field={{
                      label: "Thread Created",
                      value: result.createdThread ? "yes" : "no",
                      status: "returned",
                    }}
                  />
                  <FieldRow
                    field={{
                      label: "Task ID",
                      value: result.completion.taskId,
                      status: result.completion.taskId ? "returned" : "not-returned",
                    }}
                  />
                  <FieldRow
                    field={{
                      label: "Turn ID",
                      value: result.completion.turnId,
                      status: result.completion.turnId ? "returned" : "not-returned",
                    }}
                  />
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card
          className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)]"
          aria-labelledby="operator-trace-pane"
        >
          <CardHeader>
            <CardTitle id="operator-trace-pane">Retrieved Context / RAG Trace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge
                status={
                  traceSummary.status === "returned"
                    ? "returned"
                    : traceSummary.status === "empty"
                      ? "not-returned"
                      : "not-exposed"
                }
              >
                {traceSummary.status === "returned"
                  ? "Trace Returned"
                  : traceSummary.status === "empty"
                    ? "Trace Empty"
                    : "Trace Unavailable"}
              </StatusBadge>
              <span className="text-sm text-[var(--muted)]">{traceSummary.message}</span>
            </div>

            {traceSummary.meta.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {traceSummary.meta.map((entry) => (
                  <FieldRow
                    key={entry.label}
                    field={{
                      label: entry.label,
                      value: entry.value,
                      status: "returned",
                    }}
                  />
                ))}
              </div>
            ) : null}

            {traceSummary.sections.some((section) => section.rows.length > 0) ? (
              <div className="space-y-4">
                {traceSummary.sections.map((section) =>
                  section.rows.length > 0 ? (
                    <div key={section.key} className="space-y-3">
                      <div className="text-sm font-medium text-[var(--text)]">
                        {section.title}
                      </div>
                      <div className="space-y-3">
                        {section.rows.map((row) => (
                          <div
                            key={row.id}
                            className="rounded-2xl border border-[var(--panel-border)] bg-white/5 p-4"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="text-sm font-medium text-[var(--text)]">
                                {row.label}
                              </div>
                              <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)]">
                                {row.rank != null ? <span>Rank {row.rank}</span> : null}
                                {row.score != null ? (
                                  <span>Score {row.score.toFixed(3)}</span>
                                ) : null}
                                {row.included != null ? (
                                  <span>{row.included ? "Included" : "Excluded"}</span>
                                ) : null}
                              </div>
                            </div>
                            {row.source ? (
                              <div className="mt-2 text-xs uppercase tracking-[0.12em] text-[var(--text-subtle)]">
                                Source: {row.source}
                              </div>
                            ) : null}
                            <div className="mt-2 text-sm text-[var(--muted)]">
                              {row.preview ?? "No snippet preview returned for this trace row."}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null
                )}
              </div>
            ) : (
              <SectionEmptyState message={traceSummary.message} />
            )}
          </CardContent>
        </Card>

        <Card
          className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)]"
          aria-labelledby="operator-answer-pane"
        >
          <CardHeader>
            <CardTitle id="operator-answer-pane">Prompt / Answer Inspection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-[var(--text)]">System / Context Summary</div>
                <StatusBadge status={promptAnswerSummary.systemSummary.status}>
                  {renderStatusLabel(promptAnswerSummary.systemSummary.status)}
                </StatusBadge>
              </div>
              {promptAnswerSummary.systemSummary.value ? (
                <div className="rounded-2xl border border-[var(--panel-border)] bg-white/5 p-4 text-sm text-[var(--muted)]">
                  {promptAnswerSummary.systemSummary.value}
                </div>
              ) : (
                <SectionEmptyState
                  message={
                    promptAnswerSummary.systemSummary.status === "not-exposed"
                      ? "Prompt and system-summary diagnostics are not exposed by the current API."
                      : "This run did not return a system/context summary."
                  }
                />
              )}
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-[var(--text)]">Final Answer</div>
                <StatusBadge status={promptAnswerSummary.answerStatus}>
                  {renderStatusLabel(promptAnswerSummary.answerStatus)}
                </StatusBadge>
              </div>
              {promptAnswerSummary.answerText ? (
                <pre className="rounded-2xl border border-[var(--panel-border)] bg-white/5 p-4 text-sm text-[var(--text)] whitespace-pre-wrap font-sans">
                  {promptAnswerSummary.answerText}
                </pre>
              ) : (
                <SectionEmptyState message={promptAnswerSummary.answerNote} />
              )}
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-[var(--text)]">
                Runtime / Provider Resolution
              </div>
              <div className="grid gap-3">
                {promptAnswerSummary.runtimeFields.map((field) => (
                  <FieldRow key={field.label} field={field} />
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-[var(--text)]">
                Timing / Latency Summary
              </div>
              <div className="grid gap-3">
                {promptAnswerSummary.timingFields.map((field) => (
                  <FieldRow key={field.label} field={field} />
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-[var(--text)]">
                Token / Cost / Usage Summary
              </div>
              <div className="grid gap-3">
                {promptAnswerSummary.usageFields.map((field) => (
                  <FieldRow key={field.label} field={field} />
                ))}
              </div>
              {promptAnswerSummary.usageFields.every(
                (field) => field.status !== "returned"
              ) ? (
                <SectionEmptyState message="Usage and cost telemetry are not exposed by the current API for this run." />
              ) : null}
            </div>

            {promptAnswerSummary.notes.length > 0 ? (
              <div className="space-y-2">
                <div className="text-sm font-medium text-[var(--text)]">
                  Diagnostic Notes
                </div>
                <div className="space-y-2">
                  {promptAnswerSummary.notes.map((note) => (
                    <div
                      key={note}
                      className="rounded-2xl border border-dashed border-[var(--panel-border)] bg-white/4 p-3 text-sm text-[var(--muted)]"
                    >
                      {note}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default CompletionReplayPage;
