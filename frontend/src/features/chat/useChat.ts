/**
 * useChat - local chat state with semantic guards against no-op updates.
 */
import { useCallback, useEffect, useRef, useState } from "react";
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
    // Internal control-flow signals should never render in the chat surface.
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

/**
 * Safely extract messages from API response.
 * Handles both envelope format { ok, total, messages } and raw array format.
 * Returns [messages, total] or null if response is invalid.
 */
export const parseMessagesResponse = (data: any): [ChatMessage[], number] | null => {
  // Handle envelope format: { ok: true, messages: [...], total: number }
  if (data?.ok && Array.isArray(data.messages)) {
    return [data.messages, data.total ?? data.messages.length];
  }
  // Defensive fallback: raw array
  if (Array.isArray(data)) {
    return [data, data.length];
  }
  return null;
};

const normalizeSrcUrl = (src: any): string => {
  if (typeof src !== "string") return "";
  // Allow either absolute URLs or /media/... relative paths.
  return src.trim();
};

const normalizeAudioUrl = (value: unknown): string | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const normalizeAttachments = (raw: any): ChatAttachment[] => {
  const base = raw?.message && typeof raw.message === "object" ? raw.message : raw;

  // We accept a few possible shapes to stay resilient while backend evolves.
  const candidates: any[] = [];

  // Preferred: `attachments: [...]`
  if (Array.isArray(base?.attachments)) candidates.push(...base.attachments);

  // Legacy-ish: `images: [...]` or `documents: [...]`
  if (Array.isArray(base?.images)) candidates.push(...base.images.map((x: any) => ({ ...x, kind: "image" })));
  if (Array.isArray(base?.documents)) candidates.push(...base.documents.map((x: any) => ({ ...x, kind: "document" })));

  // Sometimes nested media envelope: `media: { images: [...], documents: [...] }`
  if (base?.media && typeof base.media === "object") {
    if (Array.isArray(base.media.images)) candidates.push(...base.media.images.map((x: any) => ({ ...x, kind: "image" })));
    if (Array.isArray(base.media.documents)) candidates.push(...base.media.documents.map((x: any) => ({ ...x, kind: "document" })));
  }

  const out: ChatAttachment[] = [];
  for (const c of candidates) {
    if (!c) continue;
    const kind: any = (c.kind || c.type || c.media_type || c.mime_type || "").toString().toLowerCase();
    const inferredKind: "image" | "document" =
      kind.includes("image") ? "image" : (kind === "document" || kind.includes("pdf") || kind.includes("text")) ? "document" : "image";

    const id = (c.id ?? c.media_id ?? c.uuid ?? "").toString();
    const src_url = normalizeSrcUrl(c.src_url ?? c.srcUrl ?? c.url ?? c.path);
    if (!id || !src_url) continue;

    out.push({
      id,
      kind: inferredKind,
      src_url,
      filename: typeof c.filename === "string" ? c.filename : undefined,
      mime_type: typeof c.mime_type === "string" ? c.mime_type : (typeof c.mimeType === "string" ? c.mimeType : undefined),
      filesize: Number.isFinite(Number(c.filesize)) ? Number(c.filesize) : (Number.isFinite(Number(c.size)) ? Number(c.size) : undefined),
      created_at: (c.created_at ?? c.createdAt) ? String(c.created_at ?? c.createdAt) : undefined,
    });
  }

  return out;
};

const UUID_V4ISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function normalizeTurnId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return UUID_V4ISH_RE.test(trimmed) ? trimmed.toLowerCase() : null;
}

function readTurnId(raw: any): string | null {
  const direct = normalizeTurnId(raw?.turn_id ?? raw?.turnId);
  if (direct) return direct;
  const base = raw?.message && typeof raw.message === "object" ? raw.message : raw;
  const metadataCandidate =
    base?.metadata ?? base?.extra_meta ?? base?.extraMeta;
  if (metadataCandidate && typeof metadataCandidate === "object") {
    const nested = metadataCandidate as Record<string, unknown>;
    return normalizeTurnId(nested.turn_id ?? nested.turnId);
  }
  return null;
}

const normalizeMessage = (raw: any, fallbackThreadId?: number): ChatMessage | null => {
  if (!raw) return null;
  const base = raw.message && typeof raw.message === "object" ? raw.message : raw;
  const threadId = Number(base.thread_id ?? base.threadId ?? fallbackThreadId);
  const id = Number(base.id ?? base.message_id ?? base.messageId);
  const role = String(base.role ?? "").trim();
  const content = typeof base.content === "string" ? base.content : String(base.content ?? "");
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
  // Drop true no-op messages, but allow attachment-only messages (uploads).
  const hasText = !!content.trim();
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
    const aa = aAtt[i];
    const bb = bAtt[i];
    if (
      aa.id !== bb.id ||
      aa.kind !== bb.kind ||
      aa.src_url !== bb.src_url ||
      (aa.filename || "") !== (bb.filename || "") ||
      (aa.mime_type || "") !== (bb.mime_type || "") ||
      (aa.filesize ?? null) !== (bb.filesize ?? null)
    ) {
      return false;
    }
  }

  return a.id === b.id
    && a.thread_id === b.thread_id
    && a.role === b.role
    && a.content === b.content
    && (a.created_at || "") === (b.created_at || "")
    && (a.turn_id || null) === (b.turn_id || null)
    && (a.audio_status || null) === (b.audio_status || null)
    && (a.audio_url || null) === (b.audio_url || null)
    && (a.audio_mime_type || null) === (b.audio_mime_type || null)
    && (a.audio_duration_ms ?? null) === (b.audio_duration_ms ?? null)
    && (a.audio_error || null) === (b.audio_error || null);
};

const equalMessageLists = (a: ChatMessage[], b: ChatMessage[]): boolean => {
  if (a === b) return true;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (!sameMessage(a[i], b[i])) return false;
  }
  return true;
};

function isAssistantWithTurnId(message: ChatMessage): boolean {
  return (
    String(message.role || "").trim().toLowerCase() === "assistant" &&
    Boolean(message.turn_id)
  );
}

function findAssistantTurnDuplicateIndex(
  messages: ChatMessage[],
  incoming: ChatMessage
): number {
  if (!isAssistantWithTurnId(incoming)) return -1;
  return messages.findIndex((candidate) => {
    if (!isAssistantWithTurnId(candidate)) return false;
    return candidate.turn_id === incoming.turn_id;
  });
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

export type CompletionState = {
  isCompleting: boolean;
  activeTaskId: string | null;
  activeThreadId: number | null;
  startedAt: number | null;
};

type UseChatOptions = {
  completionSlowPathMs?: number;
  completionHardTimeoutMs?: number;
};

const DEFAULT_COMPLETION_SLOW_PATH_MS = 15_000;
const DEFAULT_COMPLETION_HARD_TIMEOUT_MS = 300_000;

function coercePositiveDurationMs(value: unknown, fallback: number): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
  return Math.round(numeric);
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
  const lastRefreshRef = useRef<{ threadId: number; messageCount: number; timestamp: number }>({
    threadId: 0,
    messageCount: 0,
    timestamp: 0,
  });
  const completionSlowTimeoutRef = useRef<number | null>(null);
  const completionHardTimeoutRef = useRef<number | null>(null);
  const inFlightCompletionRef = useRef<Record<number, boolean>>({});
  const completionGenerationRef = useRef(0);

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

  const clearCompletionState = useCallback(() => {
    setCompletionState((prev) => {
      if (
        !prev.isCompleting &&
        prev.activeTaskId === null &&
        prev.activeThreadId === null &&
        prev.startedAt === null
      ) {
        return prev;
      }
      if (prev.activeThreadId != null) {
        setCompletionInFlight(prev.activeThreadId, false);
      }
      return {
        isCompleting: false,
        activeTaskId: null,
        activeThreadId: null,
        startedAt: null,
      };
    });
  }, [setCompletionInFlight]);

  const loadMessages = useCallback(async (threadId: number, limit = 50, offset = 0, append = false) => {
    activeThreadRef.current = threadId;
    setLoading(true);
    setError(null);
    if (!append || offset === 0) {
      setMessages((prev) => (prev.length ? [] : prev));
      setHasMore((prev) => (prev ? prev : true));
    }
    try {
      const res = await api.get(`/chat/${threadId}/messages`, { params: { limit, offset } });
      if (activeThreadRef.current !== threadId) {
        return;
      }
      const parsed = parseMessagesResponse(res?.data);
      if (parsed) {
        const [page, tot] = parsed;
        const normalizedPage = page
          .map((message) => normalizeMessage(message, threadId))
          .filter((message): message is ChatMessage => Boolean(message));
        console.debug(`[useChat] Loaded ${page.length} messages for thread ${threadId} (total: ${tot})`);
        setTotal((prev) => (prev === tot ? prev : tot));
        const nextHasMore = offset + page.length < tot;
        setHasMore((prev) => (prev === nextHasMore ? prev : nextHasMore));
        setMessages((prev) => {
          const merged = append
            ? mergeMessagePages(prev, normalizedPage)
            : normalizedPage;
          const next = collapseAssistantTurnDuplicates(merged);
          return equalMessageLists(prev, next) ? prev : next;
        });
      } else {
        setMessages((prev) => (prev.length ? [] : prev));
        setTotal((prev) => (prev === 0 ? prev : 0));
        setHasMore((prev) => (prev === false ? prev : false));
      }
    } catch (e: any) {
      logOnce("poll:messages", 10_000, () => {
        console.warn(`[useChat] Failed to load messages for thread ${threadId}`, e);
      });
      setError(toUserFacingLoadMessagesError(e));
      setMessages((prev) => (prev.length ? [] : prev));
      setTotal((prev) => (prev === 0 ? prev : 0));
      setHasMore((prev) => (prev === false ? prev : false));
    } finally {
      setLoading(false);
    }
  }, []);

  const appendMessage = useCallback((threadId: number, raw: any) => {
    const incoming = normalizeMessage(raw, threadId);
    if (!incoming || incoming.thread_id !== threadId) return;
    setMessages((prev) => {
      const turnDuplicateIdx = findAssistantTurnDuplicateIndex(prev, incoming);
      if (
        turnDuplicateIdx >= 0 &&
        prev[turnDuplicateIdx] &&
        prev[turnDuplicateIdx].id !== incoming.id
      ) {
        return prev;
      }

      const idx = prev.findIndex((msg) => msg.id === incoming.id);
      if (idx >= 0) {
        const existing = prev[idx];
        const merged = {
          ...existing,
          ...incoming,
          created_at: incoming.created_at || existing.created_at,
        };
        if (sameMessage(existing, merged)) return prev;
        const next = [...prev];
        next[idx] = merged;
        return next;
      }
      const next = collapseAssistantTurnDuplicates([...prev, incoming]);
      if (next.length === prev.length) {
        return prev;
      }
      setTotal((prevTotal) => prevTotal + 1);
      return next;
    });
  }, []);

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
          // Backend may ignore this until wired, but frontend can start calling it.
          payload.attachments = opts.attachments;
        }
        const res = await api.post(`/chat/${threadId}/messages`, payload);
        return res?.data;
      } catch (e) {
        setError("Failed to send message");
        return { ok: false };
      }
    },
    []
  );

  const deleteMessage = useCallback(async (threadId: number, id: number) => {
    try {
      const res = await api.delete(`/chat/${threadId}/messages/${id}`);
      return res?.data;
    } catch (e) {
      setError("Failed to delete message");
      return { ok: false };
    }
  }, []);

  const startCompletion = useCallback((threadId: number, taskId: string) => {
    const generation = completionGenerationRef.current + 1;
    completionGenerationRef.current = generation;
    setCompletionInFlight(threadId, true);
    setCompletionState((prev) => {
      const startedAt =
        prev.isCompleting && prev.activeThreadId === threadId
          ? prev.startedAt ?? Date.now()
          : Date.now();
      return {
        isCompleting: true,
        activeTaskId: taskId,
        activeThreadId: threadId,
        startedAt,
      };
    });
    console.debug(`[useChat] Started completion tracking: thread=${threadId}, task=${taskId}`);

    // Clear any existing timeouts
    if (completionSlowTimeoutRef.current !== null) {
      window.clearTimeout(completionSlowTimeoutRef.current);
    }
    if (completionHardTimeoutRef.current !== null) {
      window.clearTimeout(completionHardTimeoutRef.current);
    }

    // Hint timeout: after a short delay, stay in slow-path but keep completion active
    completionSlowTimeoutRef.current = window.setTimeout(() => {
      if (completionGenerationRef.current !== generation) return;
      console.warn(
        `[useChat] Completion still in progress after ${completionSlowPathMs}ms (slow-path)`
      );
      completionSlowTimeoutRef.current = null;
    }, completionSlowPathMs);

    // Hard timeout: keep the UI in sync with the longer poll ceiling for slow local runs.
    completionHardTimeoutRef.current = window.setTimeout(() => {
      if (completionGenerationRef.current !== generation) return;
      console.warn(
        `[useChat] Completion hard-timeout reached (${completionHardTimeoutMs}ms), clearing state`
      );
      completionHardTimeoutRef.current = null;
      clearCompletionState();
    }, completionHardTimeoutMs);
  }, [
    clearCompletionState,
    completionHardTimeoutMs,
    completionSlowPathMs,
    setCompletionInFlight,
  ]);

  const endCompletion = useCallback(() => {
    completionGenerationRef.current += 1;

    if (completionSlowTimeoutRef.current !== null) {
      window.clearTimeout(completionSlowTimeoutRef.current);
      completionSlowTimeoutRef.current = null;
    }
    if (completionHardTimeoutRef.current !== null) {
      window.clearTimeout(completionHardTimeoutRef.current);
      completionHardTimeoutRef.current = null;
    }
    if (completionState.activeThreadId != null) {
      setCompletionInFlight(completionState.activeThreadId, false);
    }
    console.debug(`[useChat] Ended completion tracking`);
    clearCompletionState();
  }, [clearCompletionState, completionState.activeThreadId, setCompletionInFlight]);

  const updateCompletionTaskId = useCallback((taskId: string | null) => {
    setCompletionState((prev) => {
      if (!prev.isCompleting) return prev;
      if (prev.activeTaskId === taskId) return prev;
      return { ...prev, activeTaskId: taskId };
    });
  }, []);

  useEffect(
    () => () => {
      completionGenerationRef.current += 1;
      if (completionSlowTimeoutRef.current !== null) {
        window.clearTimeout(completionSlowTimeoutRef.current);
        completionSlowTimeoutRef.current = null;
      }
      if (completionHardTimeoutRef.current !== null) {
        window.clearTimeout(completionHardTimeoutRef.current);
        completionHardTimeoutRef.current = null;
      }
    },
    []
  );

  const shouldRefresh = useCallback(
    (threadId: number, currentMessageCount: number) => {
      const last = lastRefreshRef.current;
      const now = Date.now();

      // Different thread - always refresh
      if (last.threadId !== threadId) return true;

      // Message count changed - refresh
      if (last.messageCount !== currentMessageCount) return true;

      // Debounce: Don't refresh if last refresh was < 500ms ago
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

  const refreshSnapshot = useCallback(
    async (threadId: number, reason?: string) => {
      if (!Number.isFinite(threadId)) return;
      try {
        await loadMessages(threadId, 50, 0, false);
        if (process.env.NODE_ENV === "development") {
          console.debug(
            `[useChat] refreshSnapshot(${threadId})`,
            reason ?? "no-reason"
          );
        }
      } catch (err) {
        console.warn("[useChat] refreshSnapshot failed", err);
      }
    },
    [loadMessages]
  );

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
    loadMessages,
    appendMessage,
    sendMessage,
    deleteMessage,
    refreshSnapshot: refreshSnapshot ?? noopRefreshSnapshot,
    completionState,
    startCompletion,
    endCompletion,
    updateCompletionTaskId,
    isCompletionInFlight,
    setCompletionInFlight,
    shouldRefresh,
    markRefreshed,
  };
}

export default useChat;

function mergeMessagePages(prev: ChatMessage[], page: ChatMessage[]): ChatMessage[] {
  if (!page.length) return prev;
  const next = [...prev];
  // Deduplicate by id so SSE inserts do not re-add fetched messages.
  const indexById = new Map<number, number>();
  const assistantTurnIndex = new Map<string, number>();
  next.forEach((msg, idx) => {
    indexById.set(msg.id, idx);
    if (isAssistantWithTurnId(msg) && msg.turn_id) {
      if (!assistantTurnIndex.has(msg.turn_id)) {
        assistantTurnIndex.set(msg.turn_id, idx);
      }
    }
  });
  page.forEach((msg) => {
    if (isAssistantWithTurnId(msg) && msg.turn_id) {
      const turnIdx = assistantTurnIndex.get(msg.turn_id);
      if (turnIdx != null && next[turnIdx]?.id !== msg.id) {
        return;
      }
    }
    const existingIdx = indexById.get(msg.id);
    if (existingIdx == null) {
      indexById.set(msg.id, next.length);
      next.push(msg);
      if (isAssistantWithTurnId(msg) && msg.turn_id) {
        assistantTurnIndex.set(msg.turn_id, next.length - 1);
      }
      return;
    }
    const existing = next[existingIdx];
    if (!sameMessage(existing, msg)) {
      next[existingIdx] = msg;
      if (isAssistantWithTurnId(msg) && msg.turn_id) {
        assistantTurnIndex.set(msg.turn_id, existingIdx);
      }
    }
  });
  return collapseAssistantTurnDuplicates(next);
}
