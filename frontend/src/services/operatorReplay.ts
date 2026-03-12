import api, {
  buildChatCompletePath,
  getAuthToken,
  getDevApiKey,
  readRuntimeApiKey,
} from "@/lib/api";
import { buildChatCompletionPayload } from "@/lib/chatClient";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import type {
  OperatorCompletionStart,
  OperatorProgressUpdate,
  OperatorRunInput,
  OperatorRunResult,
  OperatorTaskTerminalEvent,
  OperatorTaskTerminalEventType,
} from "@/lib/operatorReplay";

const TASK_TERMINAL_TIMEOUT_MS = 60_000;

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeThreadId(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : null;
}

function toErrorMessage(error: unknown, fallback: string): string {
  const maybeError =
    error && typeof error === "object"
      ? (error as {
          response?: { data?: { detail?: string; error?: string } };
          message?: string;
        })
      : null;
  return (
    maybeError?.response?.data?.detail ??
    maybeError?.response?.data?.error ??
    maybeError?.message ??
    fallback
  );
}

function parseTaskEventPayload(event: Event): Record<string, unknown> | null {
  const message = event as MessageEvent<string>;
  const raw = typeof message.data === "string" ? message.data.trim() : "";
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function buildEventHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const authToken = getAuthToken();
  const apiKey = readRuntimeApiKey() || getDevApiKey();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  } else if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

function deriveThreadTitle(message: string): string {
  const firstLine = message.trim().split(/\n+/)[0] ?? "";
  return firstLine.slice(0, 60) || "Operator replay";
}

async function postOperatorMessage(input: OperatorRunInput): Promise<{
  threadId: number;
  createdThread: boolean;
}> {
  const response = await api.post("/chat/messages", {
    thread_id: normalizeThreadId(input.threadId),
    role: "user",
    content: input.userMessage.trim(),
    title: normalizeThreadId(input.threadId) == null ? deriveThreadTitle(input.userMessage) : undefined,
  });
  const payload = response?.data ?? {};
  const threadId = normalizeThreadId(
    payload.thread_id ?? payload.thread?.id ?? payload.message?.thread_id ?? payload.id
  );
  if (threadId == null) {
    throw new Error("Thread id missing from operator message response.");
  }
  return {
    threadId,
    createdThread: Boolean(payload.created_thread),
  };
}

async function startOperatorCompletion(
  threadId: number,
  input: OperatorRunInput
): Promise<OperatorCompletionStart> {
  const payload = buildChatCompletionPayload(input.depthMode, {
    providerId: normalizeString(input.provider),
    modelId: normalizeString(input.model),
  });
  const response = await api.post(buildChatCompletePath(threadId), payload);
  const data = response?.data ?? {};
  return {
    taskId: normalizeString(data.task_id),
    turnId: normalizeString(data.turn_id),
    traceUrl: normalizeString(data.trace_url),
    depthMode: normalizeString(data.depth_mode),
    requestedDepthMode: normalizeString(data.requested_depth_mode),
    effectiveDepthMode: normalizeString(data.effective_depth_mode),
    depthDowngradeReason: normalizeString(data.depth_downgrade_reason),
  };
}

async function waitForTaskTerminalEvent(
  taskId: string
): Promise<{
  taskTerminal: OperatorTaskTerminalEvent | null;
  taskWaitTimedOut: boolean;
  taskEventError: string | null;
}> {
  return new Promise((resolve) => {
    let settled = false;
    let lastError: string | null = null;

    const finalize = (
      taskTerminal: OperatorTaskTerminalEvent | null,
      taskWaitTimedOut: boolean
    ) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);
      stream.close();
      resolve({
        taskTerminal,
        taskWaitTimedOut,
        taskEventError: lastError,
      });
    };

    const attachTerminalListener = (type: OperatorTaskTerminalEventType) => {
      stream.addEventListener(type, (event: Event) => {
        finalize(
          {
            type,
            payload: parseTaskEventPayload(event),
          },
          false
        );
      });
    };

    const stream = new GuardianEventSource(
      `/api/tasks/${encodeURIComponent(taskId)}/events`,
      {
        headers: buildEventHeaders(),
        withCredentials: true,
        autoReconnect: true,
        retryInterval: 3000,
      }
    );

    attachTerminalListener("task.completed");
    attachTerminalListener("task.failed");
    attachTerminalListener("task.cancelled");
    attachTerminalListener("completion.error");

    stream.onerror = () => {
      lastError = "Task event stream interrupted while waiting for terminal status.";
    };

    const timeoutId = window.setTimeout(() => {
      finalize(null, true);
    }, TASK_TERMINAL_TIMEOUT_MS);
  });
}

async function fetchMessages(threadId: number): Promise<{
  messages: Record<string, unknown>[];
  messagesError: string | null;
}> {
  try {
    const response = await api.get(`/chat/${threadId}/messages`);
    const payload = response?.data;
    const messages = Array.isArray(payload?.messages)
      ? payload.messages
      : Array.isArray(payload)
        ? payload
        : [];
    return {
      messages: messages.filter(
        (entry): entry is Record<string, unknown> =>
          Boolean(entry) && typeof entry === "object" && !Array.isArray(entry)
      ),
      messagesError: null,
    };
  } catch (error) {
    return {
      messages: [],
      messagesError: toErrorMessage(error, "Unable to load thread messages."),
    };
  }
}

async function fetchTrace(
  threadId: number,
  traceUrl: string | null
): Promise<{
  trace: Record<string, unknown> | null;
  traceError: string | null;
}> {
  try {
    const response = await api.get(
      traceUrl || `/api/chat/debug/rag-trace/${threadId}/latest`
    );
    const payload = response?.data;
    return {
      trace:
        payload && typeof payload === "object" && !Array.isArray(payload)
          ? (payload as Record<string, unknown>)
          : null,
      traceError: null,
    };
  } catch (error) {
    return {
      trace: null,
      traceError: toErrorMessage(error, "Trace data not returned by current API."),
    };
  }
}

export async function runOperatorReplay(
  input: OperatorRunInput,
  options: { onProgress?: (update: OperatorProgressUpdate) => void } = {}
): Promise<OperatorRunResult> {
  const userMessage = input.userMessage.trim();
  if (!userMessage) {
    throw new Error("User message is required.");
  }

  options.onProgress?.({
    stage: "posting-message",
    message: "Persisting operator input into the real chat pipeline…",
  });
  const { threadId, createdThread } = await postOperatorMessage({
    ...input,
    userMessage,
  });

  options.onProgress?.({
    stage: "starting-completion",
    message: "Starting a real completion task for this thread…",
  });
  const completion = await startOperatorCompletion(threadId, input);

  let taskTerminal: OperatorTaskTerminalEvent | null = null;
  let taskWaitTimedOut = false;
  let taskEventError: string | null = null;

  if (completion.taskId) {
    options.onProgress?.({
      stage: "waiting-task",
      message: "Waiting for worker events and terminal completion status…",
    });
    const taskResult = await waitForTaskTerminalEvent(completion.taskId);
    taskTerminal = taskResult.taskTerminal;
    taskWaitTimedOut = taskResult.taskWaitTimedOut;
    taskEventError = taskResult.taskEventError;
  }

  options.onProgress?.({
    stage: "collecting-results",
    message: "Collecting persisted messages and retrieval trace…",
  });

  const [messagesResult, traceResult] = await Promise.all([
    fetchMessages(threadId),
    fetchTrace(threadId, completion.traceUrl),
  ]);

  return {
    threadId,
    createdThread,
    completion,
    taskTerminal,
    taskWaitTimedOut,
    taskEventError,
    messages: messagesResult.messages,
    messagesError: messagesResult.messagesError,
    trace: traceResult.trace,
    traceError: traceResult.traceError,
  };
}
