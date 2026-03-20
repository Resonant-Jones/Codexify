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

import api from "@/lib/api";
import { logOnce } from "@/lib/logging/logOnce";

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
  pollDelayMs: number;
  audioReconcileStartedAt: number | null;
};

const DEFAULT_COMPLETION_SLOW_PATH_MS = 15_000;
const DEFAULT_COMPLETION_HARD_TIMEOUT_MS = 300_000;
const ACTIVE_SNAPSHOT_LIMIT = 100;
const COMPLETION_POLL_MIN_MS = 1_500;
const COMPLETION_POLL_MAX_MS = 5_000;
const AUDIO_RECONCILE_POLL_MS = 5_000;
const AUDIO_RECONCILE_MAX_MS = 45_000;
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
    return null;
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

const normalizeMessage = (
  raw: any,
  fallbackThreadId?: number
): ChatMessage | null => {
  if (!raw) return null;
  const base = raw.message && typeof raw.message === "object" ? raw.message : raw;
  const threadId = Number(base.thread_id ?? base.threadId ?? fallbackThreadId);
  const id = Number(base.id ?? base.message_id ?? base.messageId);
  const role = String(base.role ?? "").trim();
  const content =
    typeof base.content === "string" ? base.content : String(base.content ?? "");
  const createdAtRaw = base.created_at ?? base.createdAt;
  const createdAt = createdAtRaw ? String(createdAtRaw) : "";
  const attachments = normalizeAttachments(raw);
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
  for (const message of messages) {
    if (!isAssistantWithTurnId(message)) {
      next.push(message);
      continue;
    }
    const turnId = message.turn_id as string;
    if (seenTurns.has(turnId)) continue;
    seenTurns.add(turnId);
    next.push(message);
  }
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
  const [completionState, setCompletionState] = useState<CompletionState>({
    isCompleting: false,
    activeTaskId: null,
    activeThreadId: null,
    startedAt: null,
  });

  const activeThreadRef = useRef<number | null>(null);
  const snapshotMessagesRef = useRef<ChatMessage[]>([]);
  const paginationMessagesRef = useRef<ChatMessage[]>([]);
  const totalRef = useRef(0);
  const messagesRef = useRef<ChatMessage[]>([]);
  const lastRefreshRef = useRef<{ threadId: number; messageCount: number; timestamp: number }>({
    threadId: 0,
    messageCount: 0,
    timestamp: 0,
  });
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
  const completionPollTimerRef = useRef<number | null>(null);
  const audioReconcileTimerRef = useRef<number | null>(null);
  const completionSlowTimeoutRef = useRef<number | null>(null);
  const completionHardTimeoutRef = useRef<number | null>(null);
  const inFlightCompletionRef = useRef<Record<number, boolean>>({});
  const completionGenerationRef = useRef(0);
  const loadingCountRef = useRef(0);

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

  const stopCompletionPoll = useCallback(() => {
    if (completionPollTimerRef.current !== null) {
      window.clearTimeout(completionPollTimerRef.current);
      completionPollTimerRef.current = null;
    }
  }, []);

  const stopAudioReconcile = useCallback(() => {
    if (audioReconcileTimerRef.current !== null) {
      window.clearTimeout(audioReconcileTimerRef.current);
      audioReconcileTimerRef.current = null;
    }
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
      stopCompletionPoll();
      stopAudioReconcile();
      completionSessionRef.current = null;
    },
    [stopAudioReconcile, stopCompletionPoll]
  );

  const findAssociatedAssistantMessage = useCallback(
    (session: CompletionSession, candidates = messagesRef.current): ChatMessage | null => {
      const assistants = candidates.filter(
        (candidate) =>
          candidate.thread_id === session.threadId &&
          String(candidate.role ?? "").trim().toLowerCase() === "assistant"
      );
      if (!assistants.length) return null;

      if (session.assistantMatchedMessageId != null) {
        const byId = assistants.find(
          (candidate) => candidate.id === session.assistantMatchedMessageId
        );
        if (byId) return byId;
      }

      if (session.turnId) {
        const byTurn = assistants.find(
          (candidate) =>
            candidate.turn_id === session.turnId &&
            candidate.id > session.baselineLatestAssistantId
        );
        if (byTurn) return byTurn;
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
      options: { limit?: number; preserveError?: boolean } = {}
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
      disposeCompletionSession();
      resetMessageState();
      await runSnapshotRefresh(numericThreadId, "activate");
    },
    [
      clearLane,
      disposeCompletionSession,
      endCompletion,
      resetMessageState,
      runSnapshotRefresh,
    ]
  );

  const refreshSnapshot = useCallback(
    async (threadId: number, reason = "manual") => {
      return runSnapshotRefresh(threadId, reason);
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
        return Boolean(findAssociatedAssistantMessage(session));
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
          await runSnapshotRefresh(session.threadId, "completion-final", {
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
      findAssociatedAssistantMessage,
      runSnapshotRefresh,
      scheduleAudioReconcile,
    ]
  );

  const scheduleCompletionPoll = useCallback(
    (sessionId: string, delayMs: number) => {
      stopCompletionPoll();
      completionPollTimerRef.current = window.setTimeout(async () => {
        completionPollTimerRef.current = null;
        const session = completionSessionRef.current;
        if (!session || session.sessionId !== sessionId) return;
        if (session.taskTerminalState != null) return;
        if (Date.now() - session.startedAt > completionHardTimeoutMs) {
          disposeCompletionSession(sessionId);
          endCompletion();
          return;
        }
        try {
          await runSnapshotRefresh(session.threadId, "completion-poll", {
            preserveError: true,
          });
        } catch {
          disposeCompletionSession(sessionId);
          endCompletion();
          return;
        }
        const current = completionSessionRef.current;
        if (!current || current.sessionId !== sessionId) return;
        const matched = findAssociatedAssistantMessage(current);
        if (matched && current.turnId) {
          current.assistantMatchedMessageId = matched.id;
          endCompletion();
          return;
        }
        current.pollDelayMs = Math.min(
          Math.max(delayMs, COMPLETION_POLL_MIN_MS) + 500,
          COMPLETION_POLL_MAX_MS
        );
        scheduleCompletionPoll(sessionId, current.pollDelayMs);
      }, delayMs);
    },
    [
      completionHardTimeoutMs,
      disposeCompletionSession,
      endCompletion,
      findAssociatedAssistantMessage,
      runSnapshotRefresh,
      stopCompletionPoll,
    ]
  );

  const startCompletionSession = useCallback(
    ({ threadId, taskId, turnId = null, reloadVersion }: CompletionSessionInput) => {
      if (!Number.isFinite(threadId)) return null;
      const normalizedTaskId = normalizeTaskId(taskId);
      if (!normalizedTaskId) return null;

      const sessionId = `${threadId}:${Date.now()}:${Math.random()
        .toString(36)
        .slice(2, 8)}`;
      disposeCompletionSession();

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
        pollDelayMs: COMPLETION_POLL_MIN_MS,
        audioReconcileStartedAt: null,
      };

      completionSessionRef.current = session;

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
          return;
        }
        scheduleCompletionPoll(sessionId, COMPLETION_POLL_MIN_MS);
      })();

      return sessionId;
    },
    [disposeCompletionSession, endCompletion, findAssociatedAssistantMessage, runSnapshotRefresh, scheduleCompletionPoll]
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
      return true;
    },
    []
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

      // Issue 1: Remove the fallback that matches only by position without task/turn verification
      // This prevents accepting assistant completion events by thread alone
      const matchedByFallback = false;

      if (!(matchedByTask || matchedByTurn)) {
        return false;
      }

      current.assistantMatchedMessageId = message.id;
      stopCompletionPoll();
      endCompletion();
      if (current.taskTerminalState != null) {
        void ensureFinalSnapshot(current.sessionId);
      }
      return true;
    },
    [appendMessage, endCompletion, ensureFinalSnapshot, stopCompletionPoll]
  );

  const finalizeCompletionSession = useCallback(
    ({ taskId, terminalState }: FinalizeCompletionSessionInput) => {
      const normalizedTaskId = normalizeTaskId(taskId);
      if (!normalizedTaskId) return false;
      const current = findCurrentSessionByTaskId(normalizedTaskId);
      if (!current) return false;
      current.taskTerminalState = terminalState;
      stopCompletionPoll();
      endCompletion();
      void ensureFinalSnapshot(current.sessionId);
      return true;
    },
    [endCompletion, ensureFinalSnapshot, findCurrentSessionByTaskId, stopCompletionPoll]
  );

  useEffect(() => {
    return () => {
      clearLane(snapshotLaneRef);
      clearLane(paginationLaneRef);
      disposeCompletionSession();
      stopCompletionTrackingTimers();
    };
  }, [clearLane, disposeCompletionSession, stopCompletionTrackingTimers]);

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
      const last = lastRefreshRef.current;
      const now = Date.now();
      if (last.threadId !== threadId) return true;
      if (last.messageCount !== currentMessageCount) return true;
      if (now - last.timestamp < 500) return false;
      return true;
    },
    []
  );

  const markRefreshed = useCallback((threadId: number, messageCount: number) => {
    lastRefreshRef.current = {
      threadId,
      messageCount,
      timestamp: Date.now(),
    };
  }, []);

  return {
    messages,
    total,
    loading,
    error,
    hasMore,
    activateThread,
    refreshSnapshot,
    loadOlderMessages,
    loadMessages,
    appendMessage,
    sendMessage,
    deleteMessage,
    completionState,
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
