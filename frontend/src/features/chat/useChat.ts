/**
 * useChat - shared Guardian chat state with lane-scoped fetching and
 * session-keyed completion reconciliation.
 */
import {
  type MutableRefObject,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useTaskEvents, type TaskStreamEvent } from "./hooks/useTaskEvents";
import api from "@/lib/api";
import { logOnce } from "@/lib/logging/logOnce";
import {
  CHAT_REQUEST_STATES,
  canTransitionRequestState,
  type ChatRequestState,
} from "@/contracts/runtimeTokens";
import type { ChatExecution, StreamChunk } from "@/types/chat";

export type ChatAttachment = {
  id: string;
  kind: "image" | "document";
  src_url: string;
  filename?: string;
  mime_type?: string;
  filesize?: number;
  created_at?: string;
};

export type ChatMessage = {
  id: number;
  thread_id: number;
  role: string;
  content: string;
  created_at: string;
  attachments?: ChatAttachment[];
  execution?: ChatExecution;
  turn_id?: string | null;
  audio_status?: "unavailable" | "pending" | "ready" | "failed";
  audio_url?: string | null;
  audio_mime_type?: string | null;
  audio_duration_ms?: number | null;
  audio_error?: string | null;
};

export type CompletionState = {
  isCompleting: boolean;
  activeTaskId: string | null;
  activeThreadId: number | null;
  startedAt: number | null;
  requestState: ChatRequestState | null;
};

export type StreamingDraft = {
  threadId: number | null;
  content: string;
  updatedAt: number | null;
};

type CompletionTerminalState = "completed" | "failed" | "cancelled" | "error";

type CompletionSessionInput = {
  threadId: number;
  taskId: string;
  turnId?: string | null;
  reloadVersion: number;
};

type ReassociateCompletionSessionInput = {
  threadId: number;
  provisionalTaskId: string;
  realTaskId: string;
  reloadVersion: number;
};

type FinalizeCompletionSessionInput = {
  taskId: string;
  terminalState: CompletionTerminalState;
};

type RefreshOptions = {
  limit?: number;
  preserveError?: boolean;
};

type UseChatOptions = {
  completionSlowPathMs?: number;
  completionHardTimeoutMs?: number;
};

type RequestLaneState = {
  controller: AbortController | null;
  promise: Promise<any> | null;
  threadId: number | null;
  token: number;
};

type CompletionSession = {
  sessionId: string;
  threadId: number;
  reloadVersion: number;
  taskId: string;
  taskIdAliases: Set<string>;
  turnId: string | null;
  startedAt: number;
  baselineLastUserMessageId: number;
  baselineLatestAssistantId: number;
  taskTerminalState: CompletionTerminalState | null;
  finalSnapshotStatus: "idle" | "running" | "done" | "failed";
  finalSnapshotError: string | null;
  finalSnapshotPromise: Promise<boolean> | null;
  assistantMatchedMessageId: number | null;
  audioReconcileStartedAt: number | null;
  requestState: ChatRequestState;
};

type ScheduledRefreshState = {
  threadId: number | null;
  promise: Promise<ChatMessage[]> | null;
  resolve: ((value: ChatMessage[]) => void) | null;
  reject: ((reason?: unknown) => void) | null;
};

const DEFAULT_COMPLETION_SLOW_PATH_MS = 15_000;
const DEFAULT_COMPLETION_HARD_TIMEOUT_MS = 300_000;
const ACTIVE_SNAPSHOT_LIMIT = 100;
const AUDIO_RECONCILE_POLL_MS = 5_000;
const AUDIO_RECONCILE_MAX_MS = 45_000;
const DEBOUNCED_REFRESH_MS = 250;
const UUID_V4ISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isAbortError(error: any): boolean {
  const name = String(error?.name ?? "").trim();
  const code = String(error?.code ?? "").trim().toUpperCase();
  const message = String(error?.message ?? "").toLowerCase();
  return (
    name === "AbortError" ||
    name === "CanceledError" ||
    code === "ERR_CANCELED" ||
    message.includes("aborted") ||
    message.includes("canceled")
  );
}

function isInternalPollBackpressureError(error: any): boolean {
  const code = String(error?.code ?? "").trim().toUpperCase();
  if (code === "ERR_CLIENT_RATE_GUARD" || code === "ERR_BACKEND_OUTAGE_FUSE") {
    return true;
  }
  const message = String(error?.message ?? "").toLowerCase();
  return (
    message.includes("request guard active") ||
    message.includes("backend outage fuse active")
  );
}

function toUserFacingLoadMessagesError(error: any): string | null {
  if (isInternalPollBackpressureError(error)) {
    return "Guardian chat is temporarily unavailable right now. Please retry in a moment.";
  }
  const status = Number(error?.response?.status ?? 0);
  if (status === 401 || status === 403) {
    return "You are not authorized to load this thread.";
  }
  if (status === 404) {
    return "Thread not found.";
  }
  return "Unable to refresh messages right now.";
}

export const parseMessagesResponse = (
  data: any
): [ChatMessage[], number] | null => {
  if (data?.ok && Array.isArray(data.messages)) {
    return [data.messages, data.total ?? data.messages.length];
  }
  if (Array.isArray(data)) {
    return [data, data.length];
  }
  return null;
};

export function renderStreamChunk(chunk: unknown): string {
  // Only render the explicit public content channel.
  if (!chunk || typeof chunk !== "object" || !("content" in chunk)) {
    return "";
  }

  const content = (chunk as StreamChunk).content;
  return typeof content === "string" ? content : "";
}

function normalizeMessageContent(raw: unknown): string {
  if (typeof raw === "string") return raw;
  if (raw && typeof raw === "object" && "content" in raw) {
    return renderStreamChunk(raw);
  }
  return String(raw ?? "");
}

const normalizeSrcUrl = (src: any): string => {
  if (typeof src !== "string") return "";
  return src.trim();
};

const normalizeAudioUrl = (value: unknown): string | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const normalizeAttachments = (raw: any): ChatAttachment[] => {
  const base = raw?.message && typeof raw.message === "object" ? raw.message : raw;
  const candidates: any[] = [];

  if (Array.isArray(base?.attachments)) candidates.push(...base.attachments);
  if (Array.isArray(base?.images)) {
    candidates.push(...base.images.map((x: any) => ({ ...x, kind: "image" })));
  }
  if (Array.isArray(base?.documents)) {
    candidates.push(
      ...base.documents.map((x: any) => ({ ...x, kind: "document" }))
    );
  }
  if (base?.media && typeof base.media === "object") {
    if (Array.isArray(base.media.images)) {
      candidates.push(
        ...base.media.images.map((x: any) => ({ ...x, kind: "image" }))
      );
    }
    if (Array.isArray(base.media.documents)) {
      candidates.push(
        ...base.media.documents.map((x: any) => ({ ...x, kind: "document" }))
      );
    }
  }

  const out: ChatAttachment[] = [];
  for (const candidate of candidates) {
    if (!candidate) continue;
    const kind = String(
      candidate.kind ??
        candidate.type ??
        candidate.media_type ??
        candidate.mime_type ??
        ""
    ).toLowerCase();
    const inferredKind: "image" | "document" = kind.includes("image")
      ? "image"
      : kind === "document" ||
          kind.includes("pdf") ||
          kind.includes("text")
        ? "document"
        : "image";
    const id = String(candidate.id ?? candidate.media_id ?? candidate.uuid ?? "");
    const src_url = normalizeSrcUrl(
      candidate.src_url ?? candidate.srcUrl ?? candidate.url ?? candidate.path
    );
    if (!id || !src_url) continue;
    out.push({
      id,
      kind: inferredKind,
      src_url,
      filename:
        typeof candidate.filename === "string" ? candidate.filename : undefined,
      mime_type:
        typeof candidate.mime_type === "string"
          ? candidate.mime_type
          : typeof candidate.mimeType === "string"
            ? candidate.mimeType
            : undefined,
      filesize: Number.isFinite(Number(candidate.filesize))
        ? Number(candidate.filesize)
        : Number.isFinite(Number(candidate.size))
          ? Number(candidate.size)
          : undefined,
      created_at:
        candidate.created_at ?? candidate.createdAt
          ? String(candidate.created_at ?? candidate.createdAt)
          : undefined,
    });
  }

  return out;
};

function normalizeTurnId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return UUID_V4ISH_RE.test(trimmed) ? trimmed.toLowerCase() : null;
}

function normalizeTaskId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  return trimmed ? trimmed : null;
}

function normalizeStreamTaskId(raw: unknown): string | null {
  const normalized = normalizeTaskId(raw);
  if (!normalized) return null;
  return normalized.startsWith("pending-") ? null : normalized;
}

function normalizeTaskChunkDelta(raw: unknown): string {
  return typeof raw === "string" ? raw : "";
}

function normalizeExecution(raw: unknown): ChatExecution | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const candidate = raw as Record<string, unknown>;
  const attemptedProvider =
    typeof candidate.attempted_provider === "string"
      ? candidate.attempted_provider.trim()
      : "";
  const attemptedModel =
    typeof candidate.attempted_model === "string"
      ? candidate.attempted_model.trim()
      : "";
  const finalProvider =
    typeof candidate.final_provider === "string"
      ? candidate.final_provider.trim()
      : "";
  const finalModel =
    typeof candidate.final_model === "string"
      ? candidate.final_model.trim()
      : "";
  if (!attemptedProvider || !attemptedModel || !finalProvider || !finalModel) {
    return undefined;
  }

  const rawFallback = candidate.fallback_triggered;
  const fallbackTriggered =
    typeof rawFallback === "boolean"
      ? rawFallback
      : typeof rawFallback === "number"
        ? Boolean(rawFallback)
        : typeof rawFallback === "string"
          ? ["1", "true", "yes", "on"].includes(
              rawFallback.trim().toLowerCase()
            )
          : undefined;
  if (fallbackTriggered === undefined) return undefined;

  return {
    attempted_provider: attemptedProvider,
    attempted_model: attemptedModel,
    final_provider: finalProvider,
    final_model: finalModel,
    fallback_triggered: fallbackTriggered,
  };
}

function readTurnId(raw: any): string | null {
  const direct = normalizeTurnId(raw?.turn_id ?? raw?.turnId);
  if (direct) return direct;
  const base = raw?.message && typeof raw.message === "object" ? raw.message : raw;
  const metadataCandidate = base?.metadata ?? base?.extra_meta ?? base?.extraMeta;
  if (metadataCandidate && typeof metadataCandidate === "object") {
    return normalizeTurnId(
      (metadataCandidate as Record<string, unknown>).turn_id ??
        (metadataCandidate as Record<string, unknown>).turnId
    );
  }
  return null;
}

function readExecution(raw: any): ChatExecution | undefined {
  const base = raw?.message && typeof raw.message === "object" ? raw.message : raw;
  const direct = normalizeExecution(raw?.execution ?? base?.execution);
  if (direct) return direct;
  const metadataCandidate = base?.metadata ?? base?.extra_meta ?? base?.extraMeta;
  if (metadataCandidate && typeof metadataCandidate === "object") {
    return normalizeExecution(
      (metadataCandidate as Record<string, unknown>).execution
    );
  }
  return undefined;
}

const normalizeMessage = (
  raw: any,
  fallbackThreadId?: number
): ChatMessage | null => {
  if (!raw) return null;
  const base = raw.message && typeof raw.message === "object" ? raw.message : raw;
  const threadId = Number(base.thread_id ?? base.threadId ?? fallbackThreadId);
  const id = Number(base.id ?? base.message_id ?? base.messageId);
  const role = String(base.role ?? "").trim();
  const content = normalizeMessageContent(base.content);
  const createdAtRaw = base.created_at ?? base.createdAt;
  const createdAt = createdAtRaw ? String(createdAtRaw) : "";
  const attachments = normalizeAttachments(raw);
  const execution = readExecution(raw);
  const turnId = readTurnId(raw);
  const audioStatusRaw = base.audio_status ?? base.audioStatus;
  const audioStatus =
    audioStatusRaw === "pending" ||
    audioStatusRaw === "ready" ||
    audioStatusRaw === "failed" ||
    audioStatusRaw === "unavailable"
      ? audioStatusRaw
      : undefined;
  const audioUrlRaw = base.audio_url ?? base.audioUrl;
  const audioMimeTypeRaw = base.audio_mime_type ?? base.audioMimeType;
  const audioDurationRaw = base.audio_duration_ms ?? base.audioDurationMs;
  const audioErrorRaw = base.audio_error ?? base.audioError;
  if (!Number.isFinite(threadId) || !Number.isFinite(id)) return null;
  const hasText = Boolean(content.trim());
  const hasAttachments = attachments.length > 0;
  if (!role || (!hasText && !hasAttachments)) return null;
  return {
    id,
    thread_id: threadId,
    role,
    content,
    created_at: createdAt,
    attachments: attachments.length ? attachments : undefined,
    execution,
    turn_id: turnId,
    audio_status: audioStatus,
    audio_url: normalizeAudioUrl(audioUrlRaw),
    audio_mime_type:
      typeof audioMimeTypeRaw === "string" ? audioMimeTypeRaw : null,
    audio_duration_ms: Number.isFinite(Number(audioDurationRaw))
      ? Number(audioDurationRaw)
      : null,
    audio_error: typeof audioErrorRaw === "string" ? audioErrorRaw : null,
  };
};

const sameExecution = (
  left: ChatExecution | undefined,
  right: ChatExecution | undefined
): boolean => {
  if (!left && !right) return true;
  if (!left || !right) return false;
  return (
    left.attempted_provider === right.attempted_provider &&
    left.attempted_model === right.attempted_model &&
    left.final_provider === right.final_provider &&
    left.final_model === right.final_model &&
    left.fallback_triggered === right.fallback_triggered
  );
};

const sameMessage = (a: ChatMessage, b: ChatMessage): boolean => {
  const aAtt = a.attachments ?? [];
  const bAtt = b.attachments ?? [];
  if (aAtt.length !== bAtt.length) return false;
  for (let i = 0; i < aAtt.length; i += 1) {
    const left = aAtt[i];
    const right = bAtt[i];
    if (
      left.id !== right.id ||
      left.kind !== right.kind ||
      left.src_url !== right.src_url ||
      (left.filename || "") !== (right.filename || "") ||
      (left.mime_type || "") !== (right.mime_type || "") ||
      (left.filesize ?? null) !== (right.filesize ?? null)
    ) {
      return false;
    }
  }
  return (
    a.id === b.id &&
    a.thread_id === b.thread_id &&
    a.role === b.role &&
    a.content === b.content &&
    (a.created_at || "") === (b.created_at || "") &&
    sameExecution(a.execution, b.execution) &&
    (a.turn_id || null) === (b.turn_id || null) &&
    (a.audio_status || null) === (b.audio_status || null) &&
    (a.audio_url || null) === (b.audio_url || null) &&
    (a.audio_mime_type || null) === (b.audio_mime_type || null) &&
    (a.audio_duration_ms ?? null) === (b.audio_duration_ms ?? null) &&
    (a.audio_error || null) === (b.audio_error || null)
  );
};

const equalMessageLists = (left: ChatMessage[], right: ChatMessage[]): boolean => {
  if (left === right) return true;
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    if (!sameMessage(left[i], right[i])) return false;
  }
  return true;
};

function isAssistantWithTurnId(message: ChatMessage): boolean {
  return (
    String(message.role || "").trim().toLowerCase() === "assistant" &&
    Boolean(message.turn_id)
  );
}

function collapseAssistantTurnDuplicates(messages: ChatMessage[]): ChatMessage[] {
  if (messages.length < 2) return messages;
  const seenTurns = new Set<string>();
  const next: ChatMessage[] = [];
  // Keep the newest assistant row per turn because completion refreshes can
  // briefly surface a placeholder before the persisted final response lands.
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (isAssistantWithTurnId(message)) {
      const turnId = message.turn_id as string;
      if (seenTurns.has(turnId)) continue;
      seenTurns.add(turnId);
    }
    next.push(message);
  }
  next.reverse();
  return next;
}

function coercePositiveDurationMs(value: unknown, fallback: number): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
  return Math.round(numeric);
}

function getMessageTimestamp(message: ChatMessage): number {
  const parsed = Date.parse(String(message.created_at ?? ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function compareMessagesChronologically(left: ChatMessage, right: ChatMessage): number {
  const byTime = getMessageTimestamp(left) - getMessageTimestamp(right);
  if (byTime !== 0) return byTime;
  return left.id - right.id;
}

function getLastUserMessageId(messages: ChatMessage[]): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (String(message.role ?? "").trim().toLowerCase() !== "user") continue;
    if (Number.isFinite(message.id)) {
      return Number(message.id);
    }
  }
  return 0;
}

function getLastAssistantMessageId(messages: ChatMessage[]): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (String(message.role ?? "").trim().toLowerCase() !== "assistant") continue;
    if (Number.isFinite(message.id)) {
      return Number(message.id);
    }
  }
  return 0;
}

function buildVisibleMessages(
  snapshotMessages: ChatMessage[],
  paginationMessages: ChatMessage[]
): ChatMessage[] {
  const canonicalById = new Map<number, ChatMessage>();
  for (const message of paginationMessages) {
    canonicalById.set(message.id, message);
  }
  for (const message of snapshotMessages) {
    canonicalById.set(message.id, message);
  }
  const next = Array.from(canonicalById.values()).sort(compareMessagesChronologically);
  return collapseAssistantTurnDuplicates(next);
}

function upsertMessageIntoLane(
  lane: ChatMessage[],
  incoming: ChatMessage
): ChatMessage[] {
  const index = lane.findIndex((message) => message.id === incoming.id);
  if (index < 0) {
    return [...lane, incoming].sort(compareMessagesChronologically);
  }
  const existing = lane[index];
  const merged = {
    ...existing,
    ...incoming,
    created_at: incoming.created_at || existing.created_at,
  };
  if (sameMessage(existing, merged)) return lane;
  const next = [...lane];
  next[index] = merged;
  return next.sort(compareMessagesChronologically);
}

export function useChat(options: UseChatOptions = {}) {
  const completionSlowPathMs = coercePositiveDurationMs(
    options.completionSlowPathMs,
    DEFAULT_COMPLETION_SLOW_PATH_MS
  );
  const completionHardTimeoutMs = Math.max(
    completionSlowPathMs,
    coercePositiveDurationMs(
      options.completionHardTimeoutMs,
      DEFAULT_COMPLETION_HARD_TIMEOUT_MS
    )
  );

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [streamTaskId, setStreamTaskId] = useState<string | null>(null);
  const [completionState, setCompletionState] = useState<CompletionState>({
    isCompleting: false,
    activeTaskId: null,
    activeThreadId: null,
    startedAt: null,
  });
  const [streamingDraft, setStreamingDraft] = useState<StreamingDraft>({
    threadId: null,
    content: "",
    updatedAt: null,
  });

  const activeThreadRef = useRef<number | null>(null);
  const snapshotMessagesRef = useRef<ChatMessage[]>([]);
  const paginationMessagesRef = useRef<ChatMessage[]>([]);
  const totalRef = useRef(0);
  const messagesRef = useRef<ChatMessage[]>([]);
  const lastRefreshGuardRef = useRef<{
    threadId: number;
    messageCount: number;
    timestamp: number;
  }>({
    threadId: 0,
    messageCount: 0,
    timestamp: 0,
  });
  const lastRefreshRef = useRef<Record<number, number>>({});
  const snapshotLaneRef = useRef<RequestLaneState>({
    controller: null,
    promise: null,
    threadId: null,
    token: 0,
  });
  const paginationLaneRef = useRef<RequestLaneState>({
    controller: null,
    promise: null,
    threadId: null,
    token: 0,
  });
  const completionSessionRef = useRef<CompletionSession | null>(null);
  const audioReconcileTimerRef = useRef<number | null>(null);
  const completionSlowTimeoutRef = useRef<number | null>(null);
  const completionHardTimeoutRef = useRef<number | null>(null);
  const inFlightCompletionRef = useRef<Record<number, boolean>>({});
  const completionGenerationRef = useRef(0);
  const loadingCountRef = useRef(0);
  const activeTaskIdRef = useRef<string | null>(null);
  const refreshTimeoutRef = useRef<number | null>(null);
  const scheduledRefreshRef = useRef<ScheduledRefreshState>({
    threadId: null,
    promise: null,
    resolve: null,
    reject: null,
  });

  const beginLoading = useCallback(() => {
    loadingCountRef.current += 1;
    setLoading(true);
  }, []);

  const endLoadingCount = useCallback(() => {
    loadingCountRef.current = Math.max(0, loadingCountRef.current - 1);
    setLoading(loadingCountRef.current > 0);
  }, []);

  const rebuildVisibleState = useCallback(() => {
    const nextMessages = buildVisibleMessages(
      snapshotMessagesRef.current,
      paginationMessagesRef.current
    );
    messagesRef.current = nextMessages;
    setMessages((previous) =>
      equalMessageLists(previous, nextMessages) ? previous : nextMessages
    );
    setTotal((previous) => (previous === totalRef.current ? previous : totalRef.current));
    const nextHasMore = nextMessages.length < totalRef.current;
    setHasMore((previous) => (previous === nextHasMore ? previous : nextHasMore));
  }, []);

  const resetMessageState = useCallback(() => {
    snapshotMessagesRef.current = [];
    paginationMessagesRef.current = [];
    totalRef.current = 0;
    messagesRef.current = [];
    setMessages((previous) => (previous.length ? [] : previous));
    setTotal((previous) => (previous === 0 ? previous : 0));
    setHasMore((previous) => (previous === false ? previous : false));
    setError(null);
  }, []);

  const clearLane = useCallback((laneRef: MutableRefObject<RequestLaneState>) => {
    laneRef.current.controller?.abort();
    laneRef.current.controller = null;
    laneRef.current.promise = null;
    laneRef.current.threadId = null;
  }, []);

  const stopAudioReconcile = useCallback(() => {
    if (audioReconcileTimerRef.current !== null) {
      window.clearTimeout(audioReconcileTimerRef.current);
      audioReconcileTimerRef.current = null;
    }
  }, []);

  const setActiveStreamTaskId = useCallback((taskId: string | null) => {
    const nextTaskId = normalizeStreamTaskId(taskId);
    if (nextTaskId === activeTaskIdRef.current) {
      return;
    }
    activeTaskIdRef.current = nextTaskId;
    setStreamTaskId(nextTaskId);
  }, []);

  const clearStreamingDraft = useCallback(() => {
    setStreamingDraft((previous) => {
      if (
        previous.threadId === null &&
        previous.content === "" &&
        previous.updatedAt === null
      ) {
        return previous;
      }
      return {
        threadId: null,
        content: "",
        updatedAt: null,
      };
    });
  }, []);

  const appendStreamingDraft = useCallback((threadId: number, delta: string) => {
    const chunk = String(delta ?? "");
    if (!chunk) return;

    setStreamingDraft((previous) => {
      if (previous.threadId !== threadId) {
        return {
          threadId,
          content: chunk,
          updatedAt: Date.now(),
        };
      }

      return {
        threadId,
        content: previous.content + chunk,
        updatedAt: Date.now(),
      };
    });
  }, []);

  const cancelScheduledRefresh = useCallback(() => {
    if (refreshTimeoutRef.current !== null) {
      window.clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
    if (scheduledRefreshRef.current.resolve) {
      scheduledRefreshRef.current.resolve([]);
    }
    scheduledRefreshRef.current = {
      threadId: null,
      promise: null,
      resolve: null,
      reject: null,
    };
  }, []);

  const clearCompletionState = useCallback(() => {
    setCompletionState((previous) => {
      if (
        !previous.isCompleting &&
        previous.activeTaskId === null &&
        previous.activeThreadId === null &&
        previous.startedAt === null
      ) {
        return previous;
      }
      if (previous.activeThreadId != null) {
        delete inFlightCompletionRef.current[previous.activeThreadId];
      }
      return {
        isCompleting: false,
        activeTaskId: null,
        activeThreadId: null,
        startedAt: null,
        requestState: null,
      };
    });
  }, []);

  const stopCompletionTrackingTimers = useCallback(() => {
    if (completionSlowTimeoutRef.current !== null) {
      window.clearTimeout(completionSlowTimeoutRef.current);
      completionSlowTimeoutRef.current = null;
    }
    if (completionHardTimeoutRef.current !== null) {
      window.clearTimeout(completionHardTimeoutRef.current);
      completionHardTimeoutRef.current = null;
    }
  }, []);

  const endCompletion = useCallback(() => {
    completionGenerationRef.current += 1;
    stopCompletionTrackingTimers();
    clearCompletionState();
  }, [clearCompletionState, stopCompletionTrackingTimers]);

  const disposeCompletionSession = useCallback(
    (sessionId?: string | null) => {
      if (
        sessionId &&
        completionSessionRef.current?.sessionId &&
        completionSessionRef.current.sessionId !== sessionId
      ) {
        return;
      }
      stopAudioReconcile();
      cancelScheduledRefresh();
      clearStreamingDraft();
      setActiveStreamTaskId(null);
      completionSessionRef.current = null;
    },
    [
      cancelScheduledRefresh,
      clearStreamingDraft,
      setActiveStreamTaskId,
      stopAudioReconcile,
    ]
  );

  const findAssociatedAssistantMessage = useCallback(
    (session: CompletionSession, candidates = messagesRef.current): ChatMessage | null => {
      const assistants = candidates.filter(
        (candidate) =>
          candidate.thread_id === session.threadId &&
          String(candidate.role ?? "").trim().toLowerCase() === "assistant"
      );
      if (!assistants.length) return null;

      if (session.turnId) {
        const byTurn = [...assistants]
          .reverse()
          .find(
            (candidate) =>
              candidate.turn_id === session.turnId &&
              candidate.id > session.baselineLatestAssistantId
          );
        if (byTurn) return byTurn;
      }

      if (session.assistantMatchedMessageId != null) {
        const byId = assistants.find(
          (candidate) => candidate.id === session.assistantMatchedMessageId
        );
        if (byId) return byId;
      }

      if (session.taskTerminalState != null) {
        const fallback = [...assistants]
          .reverse()
          .find(
            (candidate) =>
              candidate.id >
              Math.max(
                session.baselineLastUserMessageId,
                session.baselineLatestAssistantId
              )
          );
        if (fallback) return fallback;
      }

      return null;
    },
    []
  );

  const runSnapshotRefresh = useCallback(
    async (
      threadId: number,
      reason: string,
      options: RefreshOptions = {}
    ): Promise<ChatMessage[]> => {
      if (!Number.isFinite(threadId)) return [];
      const limit = options.limit ?? ACTIVE_SNAPSHOT_LIMIT;
      const nextToken = snapshotLaneRef.current.token + 1;
      snapshotLaneRef.current.controller?.abort();
      const controller = new AbortController();
      snapshotLaneRef.current = {
        controller,
        promise: null,
        threadId,
        token: nextToken,
      };

      if (!options.preserveError) {
        setError(null);
      }
      beginLoading();

      const promise = (async () => {
        try {
          const response = await api.get(`/chat/${threadId}/messages`, {
            params: { limit, offset: 0 },
            signal: controller.signal,
          });
          if (
            activeThreadRef.current !== threadId ||
            snapshotLaneRef.current.token !== nextToken
          ) {
            return [];
          }
          const parsed = parseMessagesResponse(response?.data);
          const normalizedPage = parsed
            ? parsed[0]
                .map((message) => normalizeMessage(message, threadId))
                .filter((message): message is ChatMessage => Boolean(message))
            : [];
          totalRef.current = parsed?.[1] ?? 0;
          snapshotMessagesRef.current = collapseAssistantTurnDuplicates(
            normalizedPage.sort(compareMessagesChronologically)
          );
          const snapshotIds = new Set(
            snapshotMessagesRef.current.map((message) => message.id)
          );
          paginationMessagesRef.current = paginationMessagesRef.current.filter(
            (message) => !snapshotIds.has(message.id)
          );
          rebuildVisibleState();
          return snapshotMessagesRef.current;
        } catch (error: any) {
          if (isAbortError(error)) {
            return [];
          }
          logOnce(`poll:messages:${reason}`, 10_000, () => {
            console.warn(
              `[useChat] Failed snapshot refresh for thread ${threadId}`,
              error
            );
          });
          setError(toUserFacingLoadMessagesError(error));
          throw error;
        } finally {
          if (snapshotLaneRef.current.token === nextToken) {
            snapshotLaneRef.current.controller = null;
            snapshotLaneRef.current.promise = null;
          }
          endLoadingCount();
        }
      })();

      snapshotLaneRef.current.promise = promise;
      return promise;
    },
    [beginLoading, endLoadingCount, rebuildVisibleState]
  );

  const scheduleRefresh = useCallback(
    (
      threadId: number,
      reason: string,
      options: RefreshOptions = {}
    ): Promise<ChatMessage[]> => {
      if (!Number.isFinite(threadId)) {
        return Promise.resolve([]);
      }

      const scheduled = scheduledRefreshRef.current;
      if (scheduled.threadId === threadId && scheduled.promise) {
        return scheduled.promise;
      }

      cancelScheduledRefresh();

      const promise = new Promise<ChatMessage[]>((resolve, reject) => {
        scheduledRefreshRef.current = {
          threadId,
          promise: null,
          resolve,
          reject,
        };

        refreshTimeoutRef.current = window.setTimeout(async () => {
          refreshTimeoutRef.current = null;
          try {
            const result = await runSnapshotRefresh(threadId, reason, options);
            scheduledRefreshRef.current.resolve?.(result);
          } catch (error) {
            scheduledRefreshRef.current.reject?.(error);
          } finally {
            scheduledRefreshRef.current = {
              threadId: null,
              promise: null,
              resolve: null,
              reject: null,
            };
          }
        }, DEBOUNCED_REFRESH_MS);
      });

      scheduledRefreshRef.current.promise = promise;
      return promise;
    },
    [cancelScheduledRefresh, runSnapshotRefresh]
  );

  const loadOlderMessages = useCallback(
    async (threadId: number, limit = ACTIVE_SNAPSHOT_LIMIT): Promise<ChatMessage[]> => {
      if (!Number.isFinite(threadId) || activeThreadRef.current !== threadId) {
        return [];
      }
      if (
        paginationLaneRef.current.promise &&
        paginationLaneRef.current.threadId === threadId
      ) {
        return paginationLaneRef.current.promise;
      }

      const nextToken = paginationLaneRef.current.token + 1;
      const controller = new AbortController();
      const offset =
        snapshotMessagesRef.current.length + paginationMessagesRef.current.length;
      paginationLaneRef.current = {
        controller,
        promise: null,
        threadId,
        token: nextToken,
      };
      beginLoading();
      setError(null);

      const promise = (async () => {
        try {
          const response = await api.get(`/chat/${threadId}/messages`, {
            params: { limit, offset },
            signal: controller.signal,
          });
          if (
            activeThreadRef.current !== threadId ||
            paginationLaneRef.current.token !== nextToken
          ) {
            return [];
          }
          const parsed = parseMessagesResponse(response?.data);
          const normalizedPage = parsed
            ? parsed[0]
                .map((message) => normalizeMessage(message, threadId))
                .filter((message): message is ChatMessage => Boolean(message))
            : [];
          totalRef.current = parsed?.[1] ?? totalRef.current;
          const snapshotIds = new Set(
            snapshotMessagesRef.current.map((message) => message.id)
          );
          const nextPagination = [...paginationMessagesRef.current];
          for (const message of normalizedPage) {
            if (snapshotIds.has(message.id)) continue;
            const existingIndex = nextPagination.findIndex(
              (candidate) => candidate.id === message.id
            );
            if (existingIndex < 0) {
              nextPagination.push(message);
              continue;
            }
            if (!sameMessage(nextPagination[existingIndex], message)) {
              nextPagination[existingIndex] = message;
            }
          }
          paginationMessagesRef.current = nextPagination.sort(
            compareMessagesChronologically
          );
          rebuildVisibleState();
          return normalizedPage;
        } catch (error: any) {
          if (isAbortError(error)) {
            return [];
          }
          logOnce("poll:messages:pagination", 10_000, () => {
            console.warn(
              `[useChat] Failed pagination refresh for thread ${threadId}`,
              error
            );
          });
          setError(toUserFacingLoadMessagesError(error));
          throw error;
        } finally {
          if (paginationLaneRef.current.token === nextToken) {
            paginationLaneRef.current.controller = null;
            paginationLaneRef.current.promise = null;
          }
          endLoadingCount();
        }
      })();

      paginationLaneRef.current.promise = promise;
      return promise;
    },
    [beginLoading, endLoadingCount, rebuildVisibleState]
  );

  const activateThread = useCallback(
    async (threadId: number | null) => {
      if (!Number.isFinite(threadId)) {
        activeThreadRef.current = null;
        clearLane(snapshotLaneRef);
        clearLane(paginationLaneRef);
        cancelScheduledRefresh();
        disposeCompletionSession();
        resetMessageState();
        endCompletion();
        return;
      }

      const numericThreadId = Number(threadId);
      if (
        activeThreadRef.current === numericThreadId &&
        snapshotMessagesRef.current.length
      ) {
        return;
      }

      activeThreadRef.current = numericThreadId;
      clearLane(snapshotLaneRef);
      clearLane(paginationLaneRef);
      cancelScheduledRefresh();
      disposeCompletionSession();
      resetMessageState();
      await runSnapshotRefresh(numericThreadId, "activate");
    },
    [
      clearLane,
      cancelScheduledRefresh,
      disposeCompletionSession,
      endCompletion,
      resetMessageState,
      runSnapshotRefresh,
    ]
  );

  const refreshSnapshot = useCallback(
    async (threadId: number, reason = "manual") => {
      if (!Number.isFinite(threadId)) return;
      const now = Date.now();
      const last = lastRefreshRef.current[threadId] ?? 0;
      if (now - last < 500) {
        if (process.env.NODE_ENV === "development") {
          console.debug(`[useChat] refreshSnapshot skipped (rate-limited)`, {
            threadId,
            reason,
          });
        }
        return;
      }
      lastRefreshRef.current[threadId] = now;
      try {
        await runSnapshotRefresh(threadId, reason);
        if (process.env.NODE_ENV === "development") {
          console.debug(`[useChat] refreshSnapshot executed`, {
            threadId,
            reason,
          });
        }
      } catch (err) {
        console.warn("[useChat] refreshSnapshot failed", err);
      }
    },
    [runSnapshotRefresh]
  );

  const appendMessage = useCallback(
    (threadId: number, raw: any) => {
      if (activeThreadRef.current !== threadId) return;
      const incoming = normalizeMessage(raw, threadId);
      if (!incoming || incoming.thread_id !== threadId) return;

      const snapshotIndex = snapshotMessagesRef.current.findIndex(
        (message) => message.id === incoming.id
      );
      if (snapshotIndex >= 0) {
        snapshotMessagesRef.current = upsertMessageIntoLane(
          snapshotMessagesRef.current,
          incoming
        );
      } else {
        const paginationIndex = paginationMessagesRef.current.findIndex(
          (message) => message.id === incoming.id
        );
        if (paginationIndex >= 0) {
          paginationMessagesRef.current = upsertMessageIntoLane(
            paginationMessagesRef.current,
            incoming
          );
        } else {
          snapshotMessagesRef.current = upsertMessageIntoLane(
            snapshotMessagesRef.current,
            incoming
          );
          totalRef.current = Math.max(totalRef.current, messagesRef.current.length + 1);
        }
      }

      rebuildVisibleState();
    },
    [rebuildVisibleState]
  );

  const sendMessage = useCallback(
    async (
      threadId: number,
      role: string,
      content: string,
      opts?: { attachments?: ChatAttachment[] }
    ) => {
      try {
        const payload: any = { role, content };
        if (opts?.attachments?.length) {
          payload.attachments = opts.attachments;
        }
        const response = await api.post(`/chat/${threadId}/messages`, payload);
        return response?.data;
      } catch {
        setError("Failed to send message");
        return { ok: false };
      }
    },
    []
  );

  const deleteMessage = useCallback(async (threadId: number, id: number) => {
    try {
      const response = await api.delete(`/chat/${threadId}/messages/${id}`);
      snapshotMessagesRef.current = snapshotMessagesRef.current.filter(
        (message) => message.id !== id
      );
      paginationMessagesRef.current = paginationMessagesRef.current.filter(
        (message) => message.id !== id
      );
      totalRef.current = Math.max(0, totalRef.current - 1);
      rebuildVisibleState();
      return response?.data;
    } catch {
      setError("Failed to delete message");
      return { ok: false };
    }
  }, [rebuildVisibleState]);

  const isCompletionInFlight = useCallback((threadId: number | null | undefined) => {
    if (threadId == null) return false;
    return Boolean(inFlightCompletionRef.current[threadId]);
  }, []);

  const setCompletionInFlight = useCallback((threadId: number, value: boolean) => {
    if (!Number.isFinite(threadId)) return;
    if (value) {
      inFlightCompletionRef.current[threadId] = true;
    } else {
      delete inFlightCompletionRef.current[threadId];
    }
  }, []);

  const startCompletion = useCallback(
    (threadId: number, taskId: string) => {
      const generation = completionGenerationRef.current + 1;
      completionGenerationRef.current = generation;
      setCompletionInFlight(threadId, true);
      setCompletionState((previous) => ({
        isCompleting: true,
        activeTaskId: taskId,
        activeThreadId: threadId,
        startedAt:
          previous.isCompleting && previous.activeThreadId === threadId
            ? previous.startedAt ?? Date.now()
            : Date.now(),
        requestState: CHAT_REQUEST_STATES.DISPATCHING,
      }));
      stopCompletionTrackingTimers();

      completionSlowTimeoutRef.current = window.setTimeout(() => {
        if (completionGenerationRef.current !== generation) return;
        console.warn(
          `[useChat] Completion still in progress after ${completionSlowPathMs}ms (slow-path)`
        );
        completionSlowTimeoutRef.current = null;
      }, completionSlowPathMs);

      completionHardTimeoutRef.current = window.setTimeout(() => {
        if (completionGenerationRef.current !== generation) return;
        console.warn(
          `[useChat] Completion hard-timeout reached (${completionHardTimeoutMs}ms), clearing state`
        );
        disposeCompletionSession(completionSessionRef.current?.sessionId ?? null);
        endCompletion();
      }, completionHardTimeoutMs);
    },
    [
      completionHardTimeoutMs,
      completionSlowPathMs,
      disposeCompletionSession,
      endCompletion,
      setCompletionInFlight,
      stopCompletionTrackingTimers,
    ]
  );

  const updateCompletionTaskId = useCallback((taskId: string | null) => {
    setCompletionState((previous) => {
      if (!previous.isCompleting) return previous;
      if (previous.activeTaskId === taskId) return previous;
      return { ...previous, activeTaskId: taskId };
    });
  }, []);

  const findCurrentSessionByTaskId = useCallback(
    (taskId: string | null, threadId?: number | null) => {
      if (!taskId) return null;
      const session = completionSessionRef.current;
      if (!session) return null;
      if (threadId != null && session.threadId !== threadId) return null;
      return session.taskIdAliases.has(taskId) ? session : null;
    },
    []
  );

  const scheduleAudioReconcile = useCallback(
    (sessionId: string) => {
      stopAudioReconcile();
      const tick = async () => {
        const session = completionSessionRef.current;
        if (!session || session.sessionId !== sessionId) return;
        if (
          session.audioReconcileStartedAt == null ||
          Date.now() - session.audioReconcileStartedAt > AUDIO_RECONCILE_MAX_MS
        ) {
          disposeCompletionSession(sessionId);
          return;
        }
        try {
          await runSnapshotRefresh(session.threadId, "audio-reconcile", {
            preserveError: true,
          });
        } catch {
          disposeCompletionSession(sessionId);
          return;
        }
        const current = completionSessionRef.current;
        if (!current || current.sessionId !== sessionId) return;
        const matched = findAssociatedAssistantMessage(current);
        if (!matched || matched.audio_status !== "pending") {
          disposeCompletionSession(sessionId);
          return;
        }
        audioReconcileTimerRef.current = window.setTimeout(
          tick,
          AUDIO_RECONCILE_POLL_MS
        );
      };

      const session = completionSessionRef.current;
      if (!session || session.sessionId !== sessionId) return;
      session.audioReconcileStartedAt = Date.now();
      audioReconcileTimerRef.current = window.setTimeout(
        tick,
        AUDIO_RECONCILE_POLL_MS
      );
    },
    [disposeCompletionSession, findAssociatedAssistantMessage, runSnapshotRefresh, stopAudioReconcile]
  );

  const ensureFinalSnapshot = useCallback(
    async (sessionId: string): Promise<boolean> => {
      const session = completionSessionRef.current;
      if (!session || session.sessionId !== sessionId) {
        return false;
      }
      if (session.finalSnapshotStatus === "done") {
        const matched = findAssociatedAssistantMessage(session);
        if (matched) {
          clearStreamingDraft();
        }
        return Boolean(matched);
      }
      if (session.finalSnapshotStatus === "running" && session.finalSnapshotPromise) {
        return session.finalSnapshotPromise;
      }
      if (session.finalSnapshotStatus === "failed") {
        return false;
      }

      session.finalSnapshotStatus = "running";
      const promise = (async () => {
        try {
          await scheduleRefresh(session.threadId, "completion-final", {
            preserveError: true,
          });
          const current = completionSessionRef.current;
          if (!current || current.sessionId !== sessionId) {
            return false;
          }
          const matched = findAssociatedAssistantMessage(current);
          if (!matched && current.taskTerminalState === "completed") {
            current.finalSnapshotStatus = "failed";
            current.finalSnapshotError = "Assistant response failed. Please retry.";
            disposeCompletionSession(sessionId);
            return false;
          }
          if (matched) {
            clearStreamingDraft();
          }
          current.finalSnapshotStatus = "done";
          current.finalSnapshotError = null;
          if (matched) {
            current.assistantMatchedMessageId = matched.id;
          }
          const pendingAudio = matched?.audio_status === "pending";
          if (pendingAudio) {
            scheduleAudioReconcile(sessionId);
          } else {
            disposeCompletionSession(sessionId);
          }
          return Boolean(matched);
        } catch (error: any) {
          const current = completionSessionRef.current;
          if (!current || current.sessionId !== sessionId) {
            return false;
          }
          if (isAbortError(error)) {
            disposeCompletionSession(sessionId);
            return false;
          }
          current.finalSnapshotStatus = "failed";
          current.finalSnapshotError =
            toUserFacingLoadMessagesError(error) ??
            "Unable to refresh messages right now.";
          disposeCompletionSession(sessionId);
          return false;
        } finally {
          const current = completionSessionRef.current;
          if (current && current.sessionId === sessionId) {
            current.finalSnapshotPromise = null;
          }
        }
      })();

      session.finalSnapshotPromise = promise;
      return promise;
    },
    [
      disposeCompletionSession,
      clearStreamingDraft,
      findAssociatedAssistantMessage,
      scheduleRefresh,
      scheduleAudioReconcile,
    ]
  );

  const startCompletionSession = useCallback(
    ({ threadId, taskId, turnId = null, reloadVersion }: CompletionSessionInput) => {
      if (!Number.isFinite(threadId)) return null;
      const normalizedTaskId = normalizeTaskId(taskId);
      if (!normalizedTaskId) return null;

      // Check if there's an existing session for the same thread that hasn't completed yet
      const existingSession = completionSessionRef.current;
      if (existingSession &&
          existingSession.threadId === threadId &&
          existingSession.taskTerminalState === null) {
        // If we're starting a new session for the same thread while another is active,
        // we should finalize the existing one first to prevent conflicts
        console.debug(`[useChat] Disposing active completion session for thread ${threadId} before starting new one`);
        disposeCompletionSession();
      }

      const sessionId = `${threadId}:${Date.now()}:${Math.random()
        .toString(36)
        .slice(2, 8)}`;
      // Only dispose if there was an active session for the same thread
      // The general dispose is still needed to clean up any existing session

      const session: CompletionSession = {
        sessionId,
        threadId,
        reloadVersion,
        taskId: normalizedTaskId,
        taskIdAliases: new Set([normalizedTaskId]),
        turnId,
        startedAt: Date.now(),
        baselineLastUserMessageId: getLastUserMessageId(messagesRef.current),
        baselineLatestAssistantId: getLastAssistantMessageId(messagesRef.current),
        taskTerminalState: null,
        finalSnapshotStatus: "idle",
        finalSnapshotError: null,
        finalSnapshotPromise: null,
        assistantMatchedMessageId: null,
        audioReconcileStartedAt: null,
        requestState: CHAT_REQUEST_STATES.DISPATCHING,
      };

      completionSessionRef.current = session;
      setActiveStreamTaskId(normalizedTaskId);

      void (async () => {
        try {
          await runSnapshotRefresh(threadId, "completion-start", {
            preserveError: true,
          });
        } catch {
          return;
        }
        const current = completionSessionRef.current;
        if (!current || current.sessionId !== sessionId) return;
        current.baselineLastUserMessageId = getLastUserMessageId(messagesRef.current);
        current.baselineLatestAssistantId = getLastAssistantMessageId(messagesRef.current);
        const matched = findAssociatedAssistantMessage(current);
        if (matched && current.turnId) {
          current.assistantMatchedMessageId = matched.id;
          endCompletion();
        }
      })();

      return sessionId;
    },
    [
      disposeCompletionSession,
      endCompletion,
      findAssociatedAssistantMessage,
      runSnapshotRefresh,
      setActiveStreamTaskId,
    ]
  );

  const reassociateCompletionSession = useCallback(
    ({
      threadId,
      provisionalTaskId,
      realTaskId,
      reloadVersion,
    }: ReassociateCompletionSessionInput) => {
      const current = completionSessionRef.current;
      const nextRealTaskId = normalizeTaskId(realTaskId);
      const nextProvisionalTaskId = normalizeTaskId(provisionalTaskId);
      if (!current || !nextRealTaskId || !nextProvisionalTaskId) return false;
      if (
        current.threadId !== threadId ||
        current.reloadVersion !== reloadVersion ||
        current.taskTerminalState != null
      ) {
        return false;
      }
      if (!current.taskIdAliases.has(nextProvisionalTaskId)) {
        return false;
      }
      current.taskId = nextRealTaskId;
      current.taskIdAliases.add(nextRealTaskId);
      current.taskIdAliases.add(nextProvisionalTaskId);
      setActiveStreamTaskId(nextRealTaskId);
      return true;
    },
    [setActiveStreamTaskId]
  );

  const updateCompletionSessionTurnId = useCallback(
    (taskId: string | null, turnId: string | null) => {
      const normalizedTaskId = normalizeTaskId(taskId);
      const normalizedTurnId = normalizeTurnId(turnId);
      if (!normalizedTaskId || !normalizedTurnId) return false;
      const current = findCurrentSessionByTaskId(normalizedTaskId);
      if (!current) return false;
      current.turnId = normalizedTurnId;
      const matched = findAssociatedAssistantMessage(current);
      if (matched) {
        current.assistantMatchedMessageId = matched.id;
        endCompletion();
        if (current.taskTerminalState != null) {
          void ensureFinalSnapshot(current.sessionId);
        }
      }
      return true;
    },
    [endCompletion, ensureFinalSnapshot, findAssociatedAssistantMessage, findCurrentSessionByTaskId]
  );

  const handleIncomingAssistantMessage = useCallback(
    (payload: any) => {
      const threadId = Number(
        payload?.thread_id ?? payload?.threadId ?? payload?.thread?.id
      );
      if (!Number.isFinite(threadId)) return false;

      appendMessage(threadId, payload);

      const message = normalizeMessage(payload, threadId);
      if (
        !message ||
        String(message.role ?? "").trim().toLowerCase() !== "assistant"
      ) {
        return false;
      }

      const current = completionSessionRef.current;
      if (!current || current.threadId !== threadId) {
        return false;
      }

      const messageTaskId = normalizeTaskId(payload?.task_id ?? payload?.taskId);
      const matchedByTask =
        Boolean(messageTaskId) && current.taskIdAliases.has(messageTaskId as string);
      const matchedByTurn =
        Boolean(current.turnId) && message.turn_id === current.turnId;

      if (!(matchedByTask || matchedByTurn)) {
        if (current.turnId && message.turn_id && message.turn_id !== current.turnId) {
          current.requestState = CHAT_REQUEST_STATES.ORPHANED;
        }
        return false;
      }

      current.assistantMatchedMessageId = message.id;
      clearStreamingDraft();
      endCompletion();
      if (current.taskTerminalState != null) {
        void ensureFinalSnapshot(current.sessionId);
      }
      return true;
    },
    [appendMessage, clearStreamingDraft, endCompletion, ensureFinalSnapshot]
  );

  const finalizeCompletionSession = useCallback(
    ({ taskId, terminalState }: FinalizeCompletionSessionInput) => {
      const normalizedTaskId = normalizeTaskId(taskId);
      if (!normalizedTaskId) return false;
      const current = findCurrentSessionByTaskId(normalizedTaskId);
      if (!current) return false;
      current.taskTerminalState = terminalState;
      endCompletion();
      void ensureFinalSnapshot(current.sessionId);
      return true;
    },
    [endCompletion, ensureFinalSnapshot, findCurrentSessionByTaskId]
  );

  const handleTaskStreamEvent = useCallback(
    (event: TaskStreamEvent) => {
      const currentTaskId = activeTaskIdRef.current;
      if (!currentTaskId) {
        return;
      }

      const eventTaskId = normalizeTaskId(
        event.task_id ?? event.taskId ?? currentTaskId
      );
      if (!eventTaskId || eventTaskId !== currentTaskId) {
        return;
      }

      const rawThreadId = Number(event.thread_id ?? event.threadId);
      const eventThreadId = Number.isFinite(rawThreadId) ? rawThreadId : null;
      const session = findCurrentSessionByTaskId(eventTaskId, eventThreadId);
      if (!session) {
        return;
      }

      updateCompletionTaskId(eventTaskId);

      const eventTurnId = normalizeTurnId(event.turn_id ?? event.turnId);
      if (eventTurnId) {
        updateCompletionSessionTurnId(eventTaskId, eventTurnId);
      }

      switch (event.type) {
        case "task.chunk": {
          const chunkDelta = normalizeTaskChunkDelta(
            event.delta ?? event.content ?? event.text ?? event.value
          );
          if (chunkDelta) {
            appendStreamingDraft(session.threadId, chunkDelta);
          }
          return;
        }
        case "task.running": {
          if (
            canTransitionRequestState(
              session.requestState,
              CHAT_REQUEST_STATES.STREAMING
            )
          ) {
            session.requestState = CHAT_REQUEST_STATES.STREAMING;
          }
          return;
        }
        case "task.completed": {
          if (findAssociatedAssistantMessage(session)) {
            clearStreamingDraft();
          }
          setActiveStreamTaskId(null);
          session.requestState = CHAT_REQUEST_STATES.COMPLETED;
          finalizeCompletionSession({
            taskId: eventTaskId,
            terminalState: "completed",
          });
          return;
        }
        case "task.failed": {
          clearStreamingDraft();
          setActiveStreamTaskId(null);
          session.requestState = CHAT_REQUEST_STATES.FAILED_RETRYABLE;
          finalizeCompletionSession({
            taskId: eventTaskId,
            terminalState: "failed",
          });
          return;
        }
        case "task.cancelled": {
          clearStreamingDraft();
          setActiveStreamTaskId(null);
          session.requestState = CHAT_REQUEST_STATES.CANCELLED;
          finalizeCompletionSession({
            taskId: eventTaskId,
            terminalState: "cancelled",
          });
          return;
        }
        case "completion.error": {
          clearStreamingDraft();
          setActiveStreamTaskId(null);
          session.requestState = CHAT_REQUEST_STATES.FAILED_FATAL;
          finalizeCompletionSession({
            taskId: eventTaskId,
            terminalState: "error",
          });
          return;
        }
        default:
          return;
      }
    },
    [
      appendStreamingDraft,
      clearStreamingDraft,
      finalizeCompletionSession,
      findAssociatedAssistantMessage,
      findCurrentSessionByTaskId,
      setActiveStreamTaskId,
      updateCompletionSessionTurnId,
      updateCompletionTaskId,
    ]
  );

  useTaskEvents(streamTaskId, handleTaskStreamEvent);

  useEffect(() => {
    return () => {
      clearLane(snapshotLaneRef);
      clearLane(paginationLaneRef);
      cancelScheduledRefresh();
      disposeCompletionSession();
      stopCompletionTrackingTimers();
    };
  }, [
    cancelScheduledRefresh,
    clearLane,
    disposeCompletionSession,
    stopCompletionTrackingTimers,
  ]);

  const loadMessages = useCallback(
    async (threadId: number, limit = 50, offset = 0, append = false) => {
      if (!append && offset === 0) {
        return runSnapshotRefresh(threadId, "legacy-load", { limit });
      }
      return loadOlderMessages(threadId, limit);
    },
    [loadOlderMessages, runSnapshotRefresh]
  );

  const shouldRefresh = useCallback(
    (threadId: number, currentMessageCount: number) => {
      const last = lastRefreshGuardRef.current;
      const now = Date.now();
      if (last.threadId !== threadId) return true;
      if (last.messageCount !== currentMessageCount) return true;
      if (now - last.timestamp < 500) return false;
      return true;
    },
    []
  );

  const markRefreshed = useCallback((threadId: number, messageCount: number) => {
    lastRefreshGuardRef.current = {
      threadId,
      messageCount,
      timestamp: Date.now(),
    };
  }, []);


  const noopRefreshSnapshot = (threadId?: number, reason?: string) => {
    console.warn("[useChat] refreshSnapshot fallback invoked", {
      threadId,
      reason,
    });
  };

  if (process.env.NODE_ENV === "development") {
    if (typeof refreshSnapshot !== "function") {
      console.error("[useChat] refreshSnapshot missing from return contract");
    }
  }

  return {
    messages,
    total,
    loading,
    error,
    hasMore,
    activateThread,
    loadOlderMessages,
    loadMessages,
    appendMessage,
    sendMessage,
    deleteMessage,
    refreshSnapshot: refreshSnapshot ?? noopRefreshSnapshot,
    completionState,
    streamingDraft,
    startCompletion,
    endCompletion,
    updateCompletionTaskId,
    startCompletionSession,
    reassociateCompletionSession,
    updateCompletionSessionTurnId,
    finalizeCompletionSession,
    handleIncomingAssistantMessage,
    isCompletionInFlight,
    setCompletionInFlight,
    shouldRefresh,
    markRefreshed,
  };
}

export default useChat;
