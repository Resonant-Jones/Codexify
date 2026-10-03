import { useEffect, useRef, useState } from "react";

import api from "@/lib/api";

type AttemptReceipt = {
  task_id: string;
  request_id: string;
  thread_id: number;
  turn_id: string;
  completed_message_id: number | null;
  state: "unknown" | "nonterminal" | "terminal";
  event_type: string | null;
};

type Props = {
  threadId: number;
  enabled: boolean;
  identityEpoch?: string;
  currentTaskId: string | null;
  onTerminalObserved: (threadId: number, reason: string) => unknown;
};

const TERMINALS = new Set(["task.completed", "task.failed", "task.cancelled"]);
const POLL_MS = 10_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function readPage(
  data: unknown,
  threadId: number,
): { rows: AttemptReceipt[]; hasMore: boolean } {
  if (
    !isRecord(data) ||
    data.ok !== true ||
    data.thread_id !== threadId ||
    !Array.isArray(data.tasks) ||
    typeof data.has_more !== "boolean"
  ) {
    throw new Error("Invalid attempt receipt page");
  }

  const rows = data.tasks.map((candidate: unknown): AttemptReceipt => {
    if (!isRecord(candidate)) {
      throw new Error("Invalid attempt identity or observation");
    }
    const taskId = candidate.task_id;
    const requestId = candidate.request_id;
    const receiptThreadId = candidate.thread_id;
    const turnId = candidate.turn_id;
    const completedMessageId = candidate.completed_message_id;
    const state = candidate.state;
    const eventType = candidate.event_type;
    const eventTypeString = typeof eventType === "string" ? eventType : null;
    if (
      !isNonEmptyString(taskId) ||
      !isNonEmptyString(requestId) ||
      receiptThreadId !== threadId ||
      !isNonEmptyString(turnId) ||
      (completedMessageId !== null &&
        (typeof completedMessageId !== "number" ||
          !Number.isSafeInteger(completedMessageId) ||
          completedMessageId <= 0)) ||
      (state !== "unknown" && state !== "nonterminal" && state !== "terminal") ||
      (state === "terminal"
        ? eventTypeString === null || !TERMINALS.has(eventTypeString)
        : eventType !== null)
    ) {
      throw new Error("Invalid attempt identity or observation");
    }
    return {
      task_id: taskId,
      request_id: requestId,
      thread_id: receiptThreadId,
      turn_id: turnId,
      completed_message_id: completedMessageId,
      state,
      event_type: eventTypeString,
    };
  });
  return { rows, hasMore: data.has_more };
}

/** Re-read existing attempt evidence; never create or replay a completion. */
export function ThreadAttemptObservation({
  threadId,
  enabled,
  identityEpoch,
  currentTaskId,
  onTerminalObserved,
}: Props) {
  const callback = useRef(onTerminalObserved);
  callback.current = onTerminalObserved;
  const [snapshot, setSnapshot] = useState<{
    threadId: number;
    identityEpoch?: string;
    rows: AttemptReceipt[];
    hasMore: boolean;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    setSnapshot(null);
    if (!enabled) return;

    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    const observedTerminals = new Set<string>();

    const read = async () => {
      controller = new AbortController();
      let keepObserving = true;
      try {
        const response = await api.get(`/chat/threads/${threadId}/tasks`, {
          params: { limit: 100, offset: 0 },
          signal: controller.signal,
          timeout: 5_000,
        });
        if (disposed) return;

        const page = readPage(response.data, threadId);
        const rows = page.rows.filter(
          (row) => row.task_id !== currentTaskId,
        );
        const newTerminals = rows.filter(
          (row) =>
            row.state === "terminal" && !observedTerminals.has(row.task_id),
        );
        if (newTerminals.length > 0) {
          await callback.current(threadId, "attempt-observation-terminal");
          if (disposed) return;
          newTerminals.forEach((row) => observedTerminals.add(row.task_id));
        }

        keepObserving = rows.some((row) => row.state !== "terminal");
        setSnapshot({
          threadId,
          identityEpoch,
          rows,
          hasMore: page.hasMore,
          error: null,
        });
      } catch {
        if (disposed) return;
        setSnapshot((previous) => ({
          threadId,
          identityEpoch,
          rows:
            previous?.threadId === threadId &&
            previous.identityEpoch === identityEpoch
              ? previous.rows
              : [],
          hasMore: previous?.hasMore ?? false,
          error:
            "Response observation is unavailable. The request outcome has not been changed.",
        }));
      } finally {
        if (!disposed && keepObserving) {
          timer = setTimeout(read, POLL_MS);
        }
      }
    };

    void read();
    return () => {
      disposed = true;
      controller?.abort();
      if (timer) clearTimeout(timer);
    };
  }, [threadId, enabled, identityEpoch, currentTaskId]);

  if (
    !enabled ||
    snapshot?.threadId !== threadId ||
    snapshot.identityEpoch !== identityEpoch
  ) {
    return null;
  }

  const unresolved = snapshot.rows.filter((row) => row.state !== "terminal");
  const failed = snapshot.rows.filter(
    (row) => row.event_type === "task.failed",
  ).length;
  const cancelled = snapshot.rows.filter(
    (row) => row.event_type === "task.cancelled",
  ).length;
  if (
    !unresolved.length &&
    !failed &&
    !cancelled &&
    !snapshot.error &&
    !snapshot.hasMore
  ) {
    return null;
  }

  return (
    <div
      data-testid="thread-attempt-observation"
      role="status"
      aria-live="polite"
      className="mx-auto w-full px-[var(--card-pad)] py-2 text-xs"
      style={{ color: "var(--muted)" }}
    >
      {unresolved.length > 0 ? (
        <>
          <div className="font-medium" style={{ color: "var(--text)" }}>
            Response outcome unconfirmed
          </div>
          <div>
            No terminal outcome has been observed for {unresolved.length} recorded
            {unresolved.length === 1 ? " attempt" : " attempts"}. Checking
            existing status without sending again.
          </div>
        </>
      ) : null}
      {failed > 0 ? (
        <div>
          {failed} earlier {failed === 1 ? "response task failed" : "response tasks failed"}.
        </div>
      ) : null}
      {cancelled > 0 ? (
        <div>
          {cancelled} earlier {cancelled === 1 ? "response task stopped" : "response tasks stopped"}.
        </div>
      ) : null}
      {snapshot.error ? <div>{snapshot.error}</div> : null}
      {snapshot.hasMore ? (
        <div>Only the newest 100 attempts are shown; earlier outcomes are outside this view.</div>
      ) : null}
    </div>
  );
}
