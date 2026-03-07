/**
 * ChatView - renders message history with scroll/stream coherence.
 */
import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useChat, parseMessagesResponse, CompletionState } from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";
import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";
import ContextMenu from "@/components/ui/ContextMenu";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useChatAutoScroll } from "@/features/chat/hooks/useChatAutoScroll";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import { logOnce } from "@/lib/logging/logOnce";
import {
  createIdleInferenceRequestState,
  isActiveInferencePhase,
  type InferenceRequestState,
} from "@/types/inference";

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";
type BubblePlayState = "idle" | "playing" | "unavailable" | "disabled";

type PollSession = {
  token: number;
  tid: number;
  reason: string;
  key: string;
  turnId: string | null;
  startedAt: number;
  lastUserMessageId: number;
  initialAssistantId: number;
  initialLatestMessageId: number;
};

type Voice404Classification = "message_not_found" | "route_missing" | "unknown";

const PAGE_SIZE = 100;
// Keep poll cadence moderate to avoid backend global rate-limit pressure.
const MESSAGE_POLL_MIN_MS = 1500;
const MESSAGE_POLL_MAX_MS = 5000;
const POLL_TIMEOUT_MS = 300_000; // 5 minutes slow-path ceiling
const COMPLETION_SETTLE_MS = 150;
const UUID_V4ISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function parseMessageId(raw: any): number {
  const value = Number(raw?.id ?? raw?.message_id ?? raw?.messageId);
  return Number.isFinite(value) ? value : 0;
}

function normalizeTurnId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return UUID_V4ISH_RE.test(trimmed) ? trimmed.toLowerCase() : null;
}

function readMessageTurnId(raw: any): string | null {
  const direct = normalizeTurnId(raw?.turn_id ?? raw?.turnId);
  if (direct) return direct;

  const metadataCandidate = raw?.metadata ?? raw?.extra_meta ?? raw?.extraMeta;
  if (metadataCandidate && typeof metadataCandidate === "object") {
    const nested = metadataCandidate as Record<string, unknown>;
    return normalizeTurnId(nested.turn_id ?? nested.turnId);
  }
  return null;
}

function getTrackedTurnId(threadId: number | null | undefined): string | null {
  const getter = (api as any)?.getInFlightCompletionTurnId;
  if (typeof getter !== "function") return null;
  return getter(threadId);
}

function clearTrackedTurnId(
  threadId: number | null | undefined,
  expectedTurnId?: string | null
): void {
  const clearer = (api as any)?.clearInFlightCompletionTurnId;
  if (typeof clearer !== "function") return;
  clearer(threadId, expectedTurnId);
}

function getLastUserMessageId(messages: Array<{ id: unknown; role?: string }>): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (String(msg?.role ?? "").trim().toLowerCase() !== "user") continue;
    const id = Number(msg?.id);
    if (Number.isFinite(id)) {
      return id;
    }
  }
  return 0;
}

function classifyVoice404Error(err: unknown): Voice404Classification {
  const status = Number((err as any)?.response?.status ?? 0);
  if (status !== 404) {
    return "unknown";
  }

  const detail = (err as any)?.response?.data?.detail;
  const normalized = (() => {
    if (typeof detail === "string") return detail.toLowerCase();
    if (detail && typeof detail === "object") {
      const bits = [
        (detail as any).error,
        (detail as any).reason,
        (detail as any).code,
        (detail as any).type,
        (detail as any).message,
      ]
        .filter(Boolean)
        .map((value) => String(value).toLowerCase());
      return bits.join(" ");
    }
    return "";
  })();

  if (
    normalized.includes("message_not_found") ||
    normalized.includes("message not found")
  ) {
    return "message_not_found";
  }
  if (normalized.includes("route_not_found")) {
    return "route_missing";
  }

  // Generic 404 from speak endpoint is treated as route-missing for this session.
  return "route_missing";
}

export function ChatView({
  threadId,
  guardianName,
  reloadVersion = 0,
  completionState,
  endCompletion,
  className,
  bottomPadding = 0,
  autoReadEnabled = false,
  voiceReadAloudEnabled = false,
  voiceCapabilitiesFailed = false,
  depthMode = "normal",
  profileId = null,
  inferenceState = createIdleInferenceRequestState(),
  onCancelInference,
  onSwitchToFast,
}: {
  threadId: number;
  guardianName?: string;
  reloadVersion?: number;
  completionState: CompletionState;
  endCompletion: () => void;
  className?: string;
  bottomPadding?: number;
  autoReadEnabled?: boolean;
  voiceReadAloudEnabled?: boolean;
  voiceCapabilitiesFailed?: boolean;
  depthMode?: DepthMode;
  profileId?: string | null;
  inferenceState?: InferenceRequestState;
  onCancelInference?: () => void;
  onSwitchToFast?: () => void;
}) {
  const {
    messages,
    loadMessages,
    appendMessage,
    loading,
    error,
    hasMore,
    shouldRefresh,
    markRefreshed,
  } = useChat();
  const { containerRef, endRef } = useChatAutoScroll(messages.length);
  const initialScrollRef = useRef(true);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<number | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number; text: string } | null>(null);
  const [voiceUnavailableMessageIds, setVoiceUnavailableMessageIds] = useState<
    Record<number, true>
  >({});
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const [voiceRouteMissing, setVoiceRouteMissing] = useState(false);
  const lastAutoReadMessageIdRef = useRef<number | null>(null);
  const autoReadPrimedRef = useRef(false);
  const { subscribe } = useLiveEvents({ passive: true });
  const pollTokenRef = useRef(0);
  const activePollKeyRef = useRef<string | null>(null);
  const [pollSession, setPollSession] = useState<PollSession | null>(null);
  const pollSessionRef = useRef<PollSession | null>(null);
  const lastMessageIdRef = useRef(0);
  const lastAssistantIdRef = useRef(0);
  const lastPolledUserIdRef = useRef(0);
  const lastReloadVersionRef = useRef(reloadVersion);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeThreadRef = useRef(threadId);
  const completionStateRef = useRef(completionState);
  const endCompletionRef = useRef(endCompletion);
  const loadMessagesRef = useRef(loadMessages);
  const shouldRefreshRef = useRef(shouldRefresh);
  const markRefreshedRef = useRef(markRefreshed);
  const messagesRef = useRef(messages);
  const completionFinalizeTimerRef = useRef<number | null>(null);
  const inFlightCompletionByThreadRef = useRef<Map<number, string>>(new Map());
  const activeTurnIdRef = useRef<string | null>(null);
  const completionFinalizePendingRef = useRef<Set<number>>(new Set());
  const lastCompletingThreadIdRef = useRef<number | null>(null);
  const liveSubscriptionCleanupRef = useRef<(() => void) | null>(null);
  const voiceUnavailableMessageIdsRef = useRef<Record<number, true>>({});
  const voiceRouteMissingRef = useRef(false);
  const logTimestampsRef = useRef<Map<string, number>>(new Map());

  const profileKey = profileId ?? "none";
  const resolvedDepthMode: DepthMode = depthMode ?? "normal";
  const isCompletingForThread =
    completionState.isCompleting && completionState.activeThreadId === threadId;
  const activeInferenceState = useMemo(() => {
    if (inferenceState.threadId === threadId) {
      return inferenceState;
    }
    if (!isCompletingForThread) {
      return createIdleInferenceRequestState();
    }
    const timestamp = Date.now();
    return {
      ...createIdleInferenceRequestState(),
      phase: "thinking" as const,
      threadId,
      startedAt: timestamp,
      updatedAt: timestamp,
    };
  }, [inferenceState, isCompletingForThread, threadId]);
  const showCompletionIndicator =
    isCompletingForThread || isActiveInferencePhase(activeInferenceState.phase);

  const debugLog = useCallback((key: string, message: string, ttlMs = 1000) => {
    const now = Date.now();
    const previous = logTimestampsRef.current.get(key) ?? 0;
    if (now - previous < ttlMs) return;
    logTimestampsRef.current.set(key, now);
    console.debug(message);
  }, []);

  const showToast = useCallback((message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message } }));
    } catch {
      // no-op
    }
  }, []);

  const buildPollKey = useCallback(
    (tid: number, lastUserMessageId: number): string =>
      `${tid}:${Math.max(0, lastUserMessageId)}:${resolvedDepthMode}:${profileKey}`,
    [profileKey, resolvedDepthMode]
  );

  const isVoiceUnavailable = useCallback((messageId: number): boolean => {
    return Boolean(voiceUnavailableMessageIdsRef.current[messageId]);
  }, []);

  const markVoiceUnavailable = useCallback(
    (messageId: number) => {
      if (voiceUnavailableMessageIdsRef.current[messageId]) {
        return;
      }
      voiceUnavailableMessageIdsRef.current = {
        ...voiceUnavailableMessageIdsRef.current,
        [messageId]: true,
      };
      setVoiceUnavailableMessageIds(voiceUnavailableMessageIdsRef.current);
      debugLog(
        `voice:unavailable:${messageId}`,
        `[chat:voice] marked message ${messageId} unavailable`,
        5000
      );
    },
    [debugLog]
  );

  const disableVoiceRoute = useCallback(() => {
    if (voiceRouteMissingRef.current) return;
    voiceRouteMissingRef.current = true;
    setVoiceRouteMissing(true);
    debugLog(
      "voice:route-missing",
      "[chat:voice] route missing detected, disabling auto-read for session",
      5000
    );
  }, [debugLog]);

  const stopPolling = useCallback((expectedKey?: string) => {
    if (expectedKey && activePollKeyRef.current !== expectedKey) return;
    pollTokenRef.current += 1;
    activePollKeyRef.current = null;
    setPollSession((prev) => (prev ? null : prev));
  }, []);

  const stopPollingWithReason = useCallback(
    (reason: string, expectedKey?: string) => {
      debugLog(`poll:stop:${reason}`, `[chat:poll] stop reason=${reason}`, 500);
      stopPolling(expectedKey);
    },
    [debugLog, stopPolling]
  );

  const clearCompletionAfterFailure = useCallback(
    (tid: number, reason: string, toastMessage?: string) => {
      if (!Number.isFinite(tid)) return;

      if (completionFinalizeTimerRef.current !== null) {
        window.clearTimeout(completionFinalizeTimerRef.current);
        completionFinalizeTimerRef.current = null;
      }
      completionFinalizePendingRef.current.delete(tid);

      const activeKey = activePollKeyRef.current;
      if (activeKey && activeKey.startsWith(`${tid}:`)) {
        stopPollingWithReason(reason, activeKey);
      }

      inFlightCompletionByThreadRef.current.delete(tid);

      const completionTurnId = activeTurnIdRef.current ?? getTrackedTurnId(tid);
      if (completionTurnId) {
        clearTrackedTurnId(tid, completionTurnId);
        if (activeThreadRef.current === tid) {
          setActiveTurnId((prev) => (prev === completionTurnId ? null : prev));
        }
      } else if (activeThreadRef.current === tid) {
        setActiveTurnId(null);
      }

      if (toastMessage && activeThreadRef.current === tid) {
        showToast(toastMessage);
      }

      endCompletionRef.current();
    },
    [showToast, stopPollingWithReason]
  );

  const startPolling = useCallback(
    (tid: number, reason: string, lastUserMessageId: number) => {
      if (!Number.isFinite(tid)) return;
      const normalizedUserId = Number.isFinite(lastUserMessageId)
        ? Math.max(0, lastUserMessageId)
        : 0;
      const turnId = activeTurnIdRef.current;
      const key = buildPollKey(tid, normalizedUserId);
      if (activePollKeyRef.current === key) {
        debugLog(
          `poll:skip:${key}`,
          `[chat:poll] skip duplicate poll session key=${key}`,
          1000
        );
        return;
      }

      const token = pollTokenRef.current + 1;
      pollTokenRef.current = token;
      activePollKeyRef.current = key;
      setPollSession({
        token,
        tid,
        reason,
        key,
        turnId,
        startedAt: Date.now(),
        lastUserMessageId: normalizedUserId,
        initialAssistantId: lastAssistantIdRef.current,
        initialLatestMessageId: lastMessageIdRef.current,
      });
      debugLog(`poll:start:${key}`, `[chat:poll] start reason=${reason} key=${key}`, 500);
    },
    [buildPollKey, debugLog]
  );

  const ingestIncoming = useCallback(
    (payload: any) => {
      if (!payload) return;
      const tid = Number(payload.thread_id ?? payload.threadId ?? payload.thread?.id);
      if (!Number.isFinite(tid) || tid !== threadId) return;

      const messageRole = String(payload?.role ?? "").trim().toLowerCase();
      const incomingTurnId = readMessageTurnId(payload);
      const incomingMessageId = parseMessageId(payload);
      if (messageRole === "assistant" && incomingTurnId) {
        const existingForTurn = messagesRef.current.find((msg) => {
          if (String(msg.role ?? "").trim().toLowerCase() !== "assistant") return false;
          return readMessageTurnId(msg) === incomingTurnId;
        });
        if (
          existingForTurn &&
          Number(existingForTurn.id) !== incomingMessageId
        ) {
          debugLog(
            `completion:duplicate-turn:${incomingTurnId}`,
            `[chat:completion] dropped duplicate assistant message turn_id=${incomingTurnId}`,
            5000
          );
          return;
        }
      }

      appendMessage(threadId, payload);
    },
    [appendMessage, debugLog, threadId]
  );

  const pollOnce = useCallback(async () => {
    const session = pollSessionRef.current;
    if (!session) return;
    if (activePollKeyRef.current !== session.key) return;
    if (pollTokenRef.current !== session.token) return;

    if (Date.now() - session.startedAt >= POLL_TIMEOUT_MS) {
      logOnce("poll:messages:timeout", 10_000, () => {
        console.info(`[chat] polling timed out (${session.reason})`);
      });
      showToast("Still working; refresh or retry.");
      stopPolling(session.key);
      return;
    }

    try {
      const res = await api.get(`/chat/${session.tid}/messages`, {
        params: { limit: PAGE_SIZE, offset: 0 },
      });
      if (pollTokenRef.current !== session.token) return;
      if (activePollKeyRef.current !== session.key) return;

      const parsed = parseMessagesResponse(res?.data);
      if (!parsed) return;
      const [page] = parsed;
      console.debug(`[chat:poll] Parsed ${page.length} messages for thread ${session.tid}`);

      let maxId = lastMessageIdRef.current;
      let maxAssistantId = session.initialAssistantId;
      const expectedTurnId = session.turnId ?? activeTurnIdRef.current;
      let matchingTurnAssistantId = 0;
      const newMessages: any[] = [];

      for (const msg of page) {
        const id = parseMessageId(msg);
        if (!Number.isFinite(id)) continue;
        if (id > maxId) {
          maxId = id;
        }
        if (msg?.role && msg.role !== "user" && id > maxAssistantId) {
          maxAssistantId = id;
        }
        const messageRole = String(msg?.role ?? "").trim().toLowerCase();
        if (
          expectedTurnId &&
          messageRole === "assistant" &&
          (() => {
            const messageTurnId = readMessageTurnId(msg);
            if (messageTurnId) {
              return messageTurnId === expectedTurnId;
            }
            return id > session.lastUserMessageId;
          })() &&
          id > matchingTurnAssistantId
        ) {
          matchingTurnAssistantId = id;
        }
        if (id > lastMessageIdRef.current) {
          newMessages.push(msg);
        }
      }

      if (newMessages.length) {
        console.debug(
          `[chat:poll] Found ${newMessages.length} new messages for thread ${session.tid}`
        );
        newMessages
          .sort((a, b) => parseMessageId(a) - parseMessageId(b))
          .forEach((msg) => ingestIncoming(msg));
      }

      if (maxId > lastMessageIdRef.current) {
        lastMessageIdRef.current = maxId;
      }
      if (maxAssistantId > lastAssistantIdRef.current) {
        lastAssistantIdRef.current = maxAssistantId;
      }

      if (expectedTurnId && matchingTurnAssistantId > 0) {
        if (inFlightCompletionByThreadRef.current.has(session.tid)) {
          inFlightCompletionByThreadRef.current.delete(session.tid);
          endCompletionRef.current();
        }
        clearTrackedTurnId(session.tid, expectedTurnId);
        if (activeThreadRef.current === session.tid) {
          setActiveTurnId((prev) =>
            prev === expectedTurnId ? null : prev
          );
        }
        stopPollingWithReason("assistant-turn-arrived", session.key);
        return;
      }

      const assistantReplyArrived =
        maxAssistantId > session.initialAssistantId &&
        maxAssistantId > session.lastUserMessageId;
      if (assistantReplyArrived && activePollKeyRef.current === session.key) {
        stopPollingWithReason("assistant-reply-arrived", session.key);
      }
    } catch (err) {
      logOnce("poll:messages", 10_000, () => {
        console.warn("[chat] polling failed", err);
      });
      throw err;
    }
  }, [ingestIncoming, stopPollingWithReason]);

  usePollWithBackoff(pollOnce, {
    enabled: Boolean(pollSession && activePollKeyRef.current === pollSession.key),
    intervalMs: MESSAGE_POLL_MIN_MS,
    maxBackoffMs: MESSAGE_POLL_MAX_MS,
    onErrorKey: "poll:messages",
    logTtlMs: 10_000,
  });

  useEffect(() => {
    activeThreadRef.current = threadId;
  }, [threadId]);

  useEffect(() => {
    completionStateRef.current = completionState;
    if (completionState.isCompleting && completionState.activeThreadId != null) {
      lastCompletingThreadIdRef.current = completionState.activeThreadId;
      const marker =
        completionState.activeTaskId ??
        `thread-${completionState.activeThreadId}`;
      inFlightCompletionByThreadRef.current.set(
        completionState.activeThreadId,
        marker
      );
      const currentTurnId = getTrackedTurnId(
        completionState.activeThreadId
      );
      if (currentTurnId !== activeTurnIdRef.current) {
        setActiveTurnId(currentTurnId);
      }
      return;
    }
    if (!completionState.isCompleting) {
      const completingThreadId = lastCompletingThreadIdRef.current;
      if (completingThreadId != null) {
        clearTrackedTurnId(completingThreadId, activeTurnIdRef.current);
      }
      lastCompletingThreadIdRef.current = null;
      setActiveTurnId(null);
      inFlightCompletionByThreadRef.current.clear();
      completionFinalizePendingRef.current.clear();
    }
  }, [completionState, threadId]);

  useEffect(() => {
    endCompletionRef.current = endCompletion;
  }, [endCompletion]);

  useEffect(() => {
    const clearCompletionOnFailure = (eventType: string, event: any) => {
      const payload = (event?.data as any)?.data ?? event?.data ?? {};
      const tid = Number(payload?.thread_id ?? payload?.threadId ?? payload?.thread?.id);
      if (!Number.isFinite(tid) || tid !== activeThreadRef.current) return;

      const snapshot = completionStateRef.current;
      if (!snapshot.isCompleting || snapshot.activeThreadId !== tid) return;

      const eventTaskIdRaw = payload?.task_id ?? payload?.taskId;
      const eventTaskId =
        typeof eventTaskIdRaw === "string" && eventTaskIdRaw.trim().length > 0
          ? eventTaskIdRaw.trim()
          : null;
      if (
        snapshot.activeTaskId &&
        eventTaskId &&
        snapshot.activeTaskId !== eventTaskId
      ) {
        return;
      }

      if (completionFinalizeTimerRef.current !== null) {
        window.clearTimeout(completionFinalizeTimerRef.current);
        completionFinalizeTimerRef.current = null;
      }
      completionFinalizePendingRef.current.delete(tid);
      inFlightCompletionByThreadRef.current.delete(tid);
      const completionTurnId = activeTurnIdRef.current ?? getTrackedTurnId(tid);
      if (completionTurnId) {
        clearTrackedTurnId(tid, completionTurnId);
        setActiveTurnId((prev) =>
          prev === completionTurnId ? null : prev
        );
      }
      const activeKey = activePollKeyRef.current;
      if (activeKey && activeKey.startsWith(`${tid}:`)) {
        stopPollingWithReason(`worker-${eventType}`, activeKey);
      }
      endCompletionRef.current();
    };

    const offTaskFailed = subscribe("task.failed", (event) => {
      clearCompletionOnFailure("task.failed", event);
    });
    const offTaskCancelled = subscribe("task.cancelled", (event) => {
      clearCompletionOnFailure("task.cancelled", event);
    });
    const offCompletionError = subscribe("completion.error", (event) => {
      clearCompletionOnFailure("completion.error", event);
    });
    const offTaskCompleted = subscribe("task.completed", (event) => {
      const payload = (event?.data as any)?.data ?? event?.data ?? {};
      const messageId = parseMessageId(payload);
      if (messageId > 0) return;
      clearCompletionOnFailure("task.completed_missing_message", event);
    });

    return () => {
      offTaskFailed();
      offTaskCancelled();
      offCompletionError();
      offTaskCompleted();
    };
  }, [stopPollingWithReason, subscribe]);


  useEffect(() => {
    loadMessagesRef.current = loadMessages;
  }, [loadMessages]);

  useEffect(() => {
    shouldRefreshRef.current = shouldRefresh;
  }, [shouldRefresh]);

  useEffect(() => {
    markRefreshedRef.current = markRefreshed;
  }, [markRefreshed]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    activeTurnIdRef.current = activeTurnId;
  }, [activeTurnId]);

  useEffect(() => {
    pollSessionRef.current = pollSession;
  }, [pollSession]);

  useEffect(() => {
    stopPolling();
    initialScrollRef.current = true;
    autoReadPrimedRef.current = false;
    lastAutoReadMessageIdRef.current = null;
    lastPolledUserIdRef.current = 0;
    lastMessageIdRef.current = 0;
    lastAssistantIdRef.current = 0;
    inFlightCompletionByThreadRef.current.clear();
    completionFinalizePendingRef.current.clear();
    setActiveTurnId(getTrackedTurnId(threadId));
    const completionSnapshot = completionStateRef.current;
    if (
      completionSnapshot.isCompleting &&
      completionSnapshot.activeThreadId === threadId
    ) {
      const marker = completionSnapshot.activeTaskId ?? `thread-${threadId}`;
      inFlightCompletionByThreadRef.current.set(threadId, marker);
    }

    if (completionFinalizeTimerRef.current !== null) {
      window.clearTimeout(completionFinalizeTimerRef.current);
      completionFinalizeTimerRef.current = null;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);

    voiceUnavailableMessageIdsRef.current = {};
    setVoiceUnavailableMessageIds({});
    voiceRouteMissingRef.current = false;
    setVoiceRouteMissing(false);

    loadMessages(threadId, PAGE_SIZE, 0, false);
  }, [loadMessages, stopPolling, threadId]);

  useEffect(() => {
    if (!isCompletingForThread) return;
    if (reloadVersion === lastReloadVersionRef.current) return;
    lastReloadVersionRef.current = reloadVersion;
    startPolling(threadId, "completion", getLastUserMessageId(messagesRef.current));
  }, [isCompletingForThread, reloadVersion, startPolling, threadId]);

  useEffect(() => {
    if (!isCompletingForThread) return;
    const active = pollSessionRef.current;
    if (!active || active.tid !== threadId) return;
    const nextKey = buildPollKey(threadId, active.lastUserMessageId);
    if (nextKey !== active.key) {
      startPolling(threadId, "poll-context-change", active.lastUserMessageId);
    }
  }, [
    activeTurnId,
    buildPollKey,
    isCompletingForThread,
    profileKey,
    resolvedDepthMode,
    startPolling,
    threadId,
  ]);

  useEffect(() => {
    liveSubscriptionCleanupRef.current?.();

    const onMessageCreated = (event: any) => {
      const payload = (event.data as any)?.data ?? event.data;
      const messageRole = String(payload?.role ?? "").trim().toLowerCase();
      const tid = Number(payload?.thread_id ?? payload?.threadId ?? payload?.thread?.id);
      const messageId = parseMessageId(payload);
      const expectedTurnId = activeTurnIdRef.current;
      const observedTurnId = readMessageTurnId(payload);

      ingestIncoming(payload);

      if (!Number.isFinite(tid) || messageRole !== "assistant") {
        return;
      }
      if (
        expectedTurnId &&
        observedTurnId &&
        observedTurnId !== expectedTurnId
      ) {
        return;
      }
      if (messageId > lastAssistantIdRef.current) {
        lastAssistantIdRef.current = messageId;
      }
      if (tid !== activeThreadRef.current) {
        return;
      }

      const completionSnapshot = completionStateRef.current;
      const hasInFlight = inFlightCompletionByThreadRef.current.has(tid);
      if (
        !completionSnapshot.isCompleting ||
        completionSnapshot.activeThreadId !== tid ||
        !hasInFlight
      ) {
        return;
      }

      if (completionFinalizePendingRef.current.has(tid)) {
        return;
      }
      completionFinalizePendingRef.current.add(tid);

      if (completionFinalizeTimerRef.current !== null) {
        window.clearTimeout(completionFinalizeTimerRef.current);
      }

      completionFinalizeTimerRef.current = window.setTimeout(() => {
        completionFinalizeTimerRef.current = null;
        completionFinalizePendingRef.current.delete(tid);

        if (activeThreadRef.current !== tid) {
          return;
        }
        if (!inFlightCompletionByThreadRef.current.has(tid)) {
          return;
        }

        inFlightCompletionByThreadRef.current.delete(tid);
        const completionTurnId =
          activeTurnIdRef.current ?? getTrackedTurnId(tid);
        if (completionTurnId) {
          clearTrackedTurnId(tid, completionTurnId);
          setActiveTurnId((prev) =>
            prev === completionTurnId ? null : prev
          );
        }
        endCompletionRef.current();

        const messageCount = messagesRef.current.length;
        if (shouldRefreshRef.current(tid, messageCount)) {
          void loadMessagesRef.current(tid, 50, 0, false);
          markRefreshedRef.current(tid, messageCount + 1);
        }

        const activeKey = activePollKeyRef.current;
        if (activeKey && activeKey.startsWith(`${tid}:`)) {
          stopPolling(activeKey);
        }
      }, COMPLETION_SETTLE_MS);
    };

    const offMessageCreated = subscribe("message.created", onMessageCreated);
    const onTerminalTaskEvent = (
      event: any,
      eventType: "task.failed" | "task.cancelled" | "completion.error"
    ) => {
      const payload = (event.data as any)?.data ?? event.data;
      const completionSnapshot = completionStateRef.current;
      if (!completionSnapshot.isCompleting) return;

      const tid = Number(
        payload?.thread_id ??
          payload?.threadId ??
          completionSnapshot.activeThreadId
      );
      if (!Number.isFinite(tid)) return;
      if (completionSnapshot.activeThreadId !== tid) return;

      const incomingTaskId = String(
        payload?.task_id ?? payload?.taskId ?? ""
      ).trim();
      if (
        completionSnapshot.activeTaskId &&
        incomingTaskId &&
        incomingTaskId !== completionSnapshot.activeTaskId
      ) {
        return;
      }

      const shouldToast =
        eventType === "task.failed" || eventType === "completion.error";
      clearCompletionAfterFailure(
        tid,
        eventType,
        shouldToast ? "Assistant response failed. Please retry." : undefined
      );
    };
    const onTaskFailed = (event: any) => onTerminalTaskEvent(event, "task.failed");
    const onTaskCancelled = (event: any) =>
      onTerminalTaskEvent(event, "task.cancelled");
    const onCompletionError = (event: any) =>
      onTerminalTaskEvent(event, "completion.error");
    const onTaskCompleted = (event: any) => {
      const payload = (event.data as any)?.data ?? event.data;
      const completionSnapshot = completionStateRef.current;
      if (!completionSnapshot.isCompleting) return;

      const tid = Number(
        payload?.thread_id ??
          payload?.threadId ??
          completionSnapshot.activeThreadId
      );
      if (!Number.isFinite(tid)) return;
      if (completionSnapshot.activeThreadId !== tid) return;

      const incomingTaskId = String(
        payload?.task_id ?? payload?.taskId ?? ""
      ).trim();
      if (
        completionSnapshot.activeTaskId &&
        incomingTaskId &&
        incomingTaskId !== completionSnapshot.activeTaskId
      ) {
        return;
      }

      const messageId = Number(payload?.message_id ?? payload?.messageId);
      if (Number.isFinite(messageId) && messageId > 0) {
        return;
      }

      clearCompletionAfterFailure(
        tid,
        "task.completed:missing-message",
        "Assistant response failed. Please retry."
      );
    };
    const offTaskFailed = subscribe("task.failed", onTaskFailed);
    const offTaskCancelled = subscribe("task.cancelled", onTaskCancelled);
    const offCompletionError = subscribe("completion.error", onCompletionError);
    const offTaskCompleted = subscribe("task.completed", onTaskCompleted);
    const onLocal = (evt: Event) => {
      const detail = (evt as CustomEvent).detail || {};
      ingestIncoming(detail.message ?? detail);
    };
    window.addEventListener("cfy:chat:message", onLocal as EventListener);

    const cleanup = () => {
      offMessageCreated();
      offTaskFailed();
      offTaskCancelled();
      offCompletionError();
      offTaskCompleted();
      window.removeEventListener("cfy:chat:message", onLocal as EventListener);
    };
    liveSubscriptionCleanupRef.current = cleanup;

    return () => {
      cleanup();
      if (liveSubscriptionCleanupRef.current === cleanup) {
        liveSubscriptionCleanupRef.current = null;
      }
    };
  }, [clearCompletionAfterFailure, ingestIncoming, stopPolling, subscribe, threadId]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const overflowing = el.scrollHeight > el.clientHeight + 1;
    setHasOverflow(overflowing);
  }, [containerRef, messages.length]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (initialScrollRef.current && typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem(`chat-scroll-${threadId}`);
        if (saved) {
          requestAnimationFrame(() => {
            if (containerRef.current) {
              containerRef.current.scrollTop = parseInt(saved, 10);
            }
          });
          initialScrollRef.current = false;
          return;
        }
      } catch {
        // no-op
      }
    }

    if (initialScrollRef.current) {
      el.scrollTop = el.scrollHeight;
      initialScrollRef.current = false;
    }
  }, [containerRef, messages.length, threadId]);

  useEffect(() => {
    let maxId = 0;
    let maxAssistantId = 0;
    for (const msg of messages) {
      const id = Number(msg.id);
      if (!Number.isFinite(id)) continue;
      if (id > maxId) {
        maxId = id;
      }
      if (msg.role && msg.role !== "user" && id > maxAssistantId) {
        maxAssistantId = id;
      }
    }
    if (maxId > lastMessageIdRef.current) {
      lastMessageIdRef.current = maxId;
    }
    if (maxAssistantId > lastAssistantIdRef.current) {
      lastAssistantIdRef.current = maxAssistantId;
    }
  }, [messages]);

  useEffect(() => {
    if (!isCompletingForThread) return;
    const lastUserMessageId = getLastUserMessageId(messages);
    if (!Number.isFinite(lastUserMessageId) || lastUserMessageId <= 0) return;
    if (lastUserMessageId <= lastPolledUserIdRef.current) return;
    lastPolledUserIdRef.current = lastUserMessageId;
    startPolling(threadId, "user-message", lastUserMessageId);
  }, [isCompletingForThread, messages, startPolling, threadId]);

  useEffect(() => {
    if (isCompletingForThread) return;
    const activeKey = activePollKeyRef.current;
    if (activeKey && activeKey.startsWith(`${threadId}:`)) {
      stopPollingWithReason("completion-inactive", activeKey);
    }
    const trackedTurnId = getTrackedTurnId(threadId);
    if (trackedTurnId) {
      clearTrackedTurnId(threadId, trackedTurnId);
    }
    if (activeTurnIdRef.current && completionStateRef.current.activeThreadId !== threadId) {
      setActiveTurnId(null);
    }
  }, [isCompletingForThread, stopPollingWithReason, threadId]);

  useEffect(
    () => () => {
      liveSubscriptionCleanupRef.current?.();
      stopPolling();
      if (completionFinalizeTimerRef.current !== null) {
        window.clearTimeout(completionFinalizeTimerRef.current);
        completionFinalizeTimerRef.current = null;
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    },
    [stopPolling]
  );

  const playMessageAudio = useCallback(
    async (messageId: number, options?: { manual?: boolean }) => {
      const manual = Boolean(options?.manual);
      if (!voiceReadAloudEnabled) {
        if (manual) {
          showToast("Voice disabled");
        }
        return;
      }
      if (voiceRouteMissingRef.current) {
        if (manual) {
          showToast("Voice disabled");
        }
        return;
      }
      if (isVoiceUnavailable(messageId)) {
        if (manual) {
          showToast("Audio unavailable");
        }
        return;
      }

      try {
        const res = await api.post(`/voice/messages/${messageId}/speak`, {
          force_regenerate: false,
        });
        const src = res?.data?.audio_asset?.src_url;
        if (!src) return;

        const resolvedSrc =
          typeof src === "string" && src.startsWith("http")
            ? src
            : String(src || "").startsWith("/")
              ? String(src)
              : `/${String(src || "")}`;

        if (audioRef.current) {
          audioRef.current.pause();
        }

        const audio = new Audio(resolvedSrc);
        audioRef.current = audio;
        setPlayingMessageId(messageId);
        audio.onended = () =>
          setPlayingMessageId((prev) => (prev === messageId ? null : prev));
        audio.onerror = () =>
          setPlayingMessageId((prev) => (prev === messageId ? null : prev));
        await audio.play();
      } catch (err) {
        const classification = classifyVoice404Error(err);
        if (classification === "message_not_found") {
          markVoiceUnavailable(messageId);
          if (manual) {
            showToast("Audio unavailable");
          }
        } else if (classification === "route_missing" && voiceCapabilitiesFailed) {
          disableVoiceRoute();
          if (manual) {
            showToast("Voice disabled");
          }
        } else {
          console.warn("[chat] playMessageAudio failed", err);
        }
        setPlayingMessageId((prev) => (prev === messageId ? null : prev));
      }
    },
    [
      disableVoiceRoute,
      isVoiceUnavailable,
      markVoiceUnavailable,
      showToast,
      voiceCapabilitiesFailed,
      voiceReadAloudEnabled,
    ]
  );

  const handlePlayClick = useCallback(
    (messageId: number) => {
      if (!voiceReadAloudEnabled) {
        showToast("Voice disabled");
        return;
      }
      if (voiceRouteMissingRef.current) {
        showToast("Voice disabled");
        return;
      }
      if (isVoiceUnavailable(messageId)) {
        showToast("Audio unavailable");
        return;
      }
      void playMessageAudio(messageId, { manual: true });
    },
    [isVoiceUnavailable, playMessageAudio, showToast, voiceReadAloudEnabled]
  );

  useEffect(() => {
    if (!voiceReadAloudEnabled) return;
    if (!autoReadEnabled) return;
    if (voiceRouteMissingRef.current) return;

    const assistants = messages.filter(
      (msg) => msg.role !== "user" && Number.isFinite(Number(msg.id))
    );
    const latest = assistants.length > 0 ? assistants[assistants.length - 1] : null;
    if (!latest) return;

    if (!autoReadPrimedRef.current) {
      autoReadPrimedRef.current = true;
      lastAutoReadMessageIdRef.current = Number(latest.id);
      return;
    }

    const latestId = Number(latest.id);
    if (!Number.isFinite(latestId)) return;
    if (lastAutoReadMessageIdRef.current === latestId) return;

    lastAutoReadMessageIdRef.current = latestId;
    if (isVoiceUnavailable(latestId)) {
      return;
    }
    void playMessageAudio(latestId);
  }, [
    autoReadEnabled,
    isVoiceUnavailable,
    messages,
    playMessageAudio,
    voiceReadAloudEnabled,
    voiceRouteMissing,
  ]);

  const onScroll = async () => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(`chat-scroll-${threadId}`, String(el.scrollTop));
      } catch {
        // no-op
      }
    }

    if (loading || !hasMore) return;
    if (el.scrollTop === 0) {
      const prevHeight = el.scrollHeight;
      await loadMessages(threadId, PAGE_SIZE, messages.length, true);
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight - prevHeight;
        }
      });
    }
  };

  const savePrompt = (text: string) => {
    const title = window.prompt("Optional title", "");
    const category = window.prompt("Optional category", "");
    const tagsRaw = window.prompt("Optional tags (comma-separated)", "");
    const pin = window.confirm("Pin this prompt to top?");
    const item = {
      text,
      ts: Date.now(),
      source: "manual",
      title: title || undefined,
      category: category || undefined,
      tags: (tagsRaw || "")
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      pinned: pin || false,
    };
    try {
      const raw = localStorage.getItem("cfy.prompts");
      const arr = raw ? JSON.parse(raw) : [];
      const next = [item, ...(Array.isArray(arr) ? arr : [])];
      localStorage.setItem("cfy.prompts", JSON.stringify(next));
      window.dispatchEvent(
        new CustomEvent("cfy:toast", { detail: { message: "Saved to Prompt Library" } })
      );
    } catch {
      // no-op
    }
  };

  const shouldMask = hasOverflow && bottomPadding > 0;
  const scrollStyle: React.CSSProperties = useMemo(
    () => ({
      paddingBottom: bottomPadding ?? 0,
      ...(shouldMask
        ? {
            maskImage:
              "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
          }
        : {}),
    }),
    [bottomPadding, shouldMask]
  );

  return (
    <div className={cn("flex flex-col h-full min-h-0", className)}>
      <div
        ref={containerRef}
        onScroll={onScroll}
        data-testid="chat-container"
        data-debug-scroll
        className="flex-1 min-h-0 flex flex-col overflow-y-auto overscroll-contain px-4 space-y-4"
        style={scrollStyle}
      >
        {messages.map((m, index) => {
          const messageId = Number(m.id);
          const canPlay = m.role !== "user" && Number.isFinite(messageId);
          const showPlay =
            canPlay && voiceReadAloudEnabled && !voiceRouteMissing;
          const messageVoiceUnavailable = Boolean(
            Number.isFinite(messageId) && voiceUnavailableMessageIds[messageId]
          );
          const playState: BubblePlayState = !showPlay
            ? "idle"
            : messageVoiceUnavailable
                ? "unavailable"
                : playingMessageId === messageId
                  ? "playing"
                  : "idle";

          return (
            <div
              data-testid="chat-message"
              key={m.id ?? `${m.role}-${m.created_at ?? index}`}
              className="max-w-full"
              onContextMenu={(event) => {
                event.preventDefault();
                const content = String(m.content ?? "");
                if (!content.trim()) return;
                setMenu({ x: event.clientX, y: event.clientY, text: content });
              }}
            >
              <ChatBubble
                message={{
                  id: String(m.id ?? `${m.role}-${m.created_at ?? index}`),
                  authorId: m.role === "user" ? "me" : "bot",
                  authorName: m.role === "user" ? "You" : guardianName || "Guardian",
                  content: m.content ?? "",
                  createdAt:
                    typeof m.created_at === "number"
                      ? m.created_at
                      : typeof m.created_at === "string"
                        ? Date.parse(m.created_at)
                        : Date.now(),
                  attachments: m.attachments?.map((att) => ({
                    id: att.id,
                    kind: att.kind,
                    src: att.src_url,
                    name: att.filename,
                  })),
                }}
                isGuardian={m.role !== "user"}
                showPlay={showPlay}
                playing={playState === "playing"}
                playState={playState}
                onPlay={() => {
                  if (!Number.isFinite(messageId)) return;
                  handlePlayClick(messageId);
                }}
              />
            </div>
          );
        })}

        {showCompletionIndicator && (
          <div className="mx-4 mb-2 flex max-w-full justify-start" data-testid="chat-completing-indicator">
            <div
              className="max-w-[min(34rem,calc(100%-1rem))] rounded-[22px] px-4 py-3 shadow-sm"
              style={{
                background:
                  "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 82%, transparent)",
                color: "var(--text)",
              }}
            >
              <InferenceStatusBanner
                state={activeInferenceState}
                onCancel={onCancelInference}
                onSwitchToFast={onSwitchToFast}
              />
            </div>
          </div>
        )}

        {loading && (
          <div className="text-xs opacity-70" data-testid="chat-loading">
            Loading...
          </div>
        )}
        {error && (
          <div className="text-xs text-red-500" data-testid="chat-error">
            {error}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {menu && (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          onClose={() => setMenu(null)}
          items={[{ label: "Save to Prompt Library", onClick: () => savePrompt(menu.text) }]}
        />
      )}
    </div>
  );
}

export default ChatView;
