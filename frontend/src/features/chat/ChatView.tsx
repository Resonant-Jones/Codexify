/**
 * ChatView - renders Guardian message history without owning fetch loops.
 */
import { AlertTriangle, ArrowDown, Inbox, Loader2 } from "lucide-react";
import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import ContextMenu from "@/components/ui/ContextMenu";
import { CHAT_LANE_INLINE_PADDING, CHAT_LANE_MAX_WIDTH } from "@/features/chat/chatLane";
import ChatBubble from "@/features/chat/components/ChatBubble";
import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";
import { useChatAutoScroll } from "@/features/chat/hooks/useChatAutoScroll";
import type {
  ChatMessage,
  CompletionState,
  StreamingDraft,
} from "@/features/chat/useChat";
import api from "@/lib/api";
import { CodexDraftCard } from "@/features/chat/components/CodexDraftCard";
import type { CodexDraft } from "@/api/codex";
import { cn } from "@/lib/utils";
import { parseDocumentContextContent } from "@/lib/documentContext";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
import { useViewportInsets } from "@/hooks/useViewportInsets";
import { resolveMessageLaneBottomPad } from "@/components/persona/layout/mobileBottomEdgeContract";
import {
  createIdleInferenceRequestState,
  isActiveInferencePhase,
  type InferenceRequestState,
} from "@/types/inference";

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";
type BubblePlayState =
  | "idle"
  | "playing"
  | "pending"
  | "unavailable"
  | "disabled";

type LazyAudioState = {
  status: "pending" | "ready" | "failed";
  audioUrl: string | null;
  audioError: string | null;
  provider: string | null;
  voice: string | null;
};

type ChatSurfaceState =
  | {
      kind: "loading";
      title: string;
      detail: string;
    }
  | {
      kind: "empty";
      title: string;
      detail: string;
    }
  | {
      kind: "error";
      title: string;
      detail: string;
    }
  | {
      kind: "unavailable";
      title: string;
      detail: string;
    };

function normalizeMessageTimestamp(raw: unknown): number | null {
  if (typeof raw === "number") {
    return Number.isFinite(raw) ? raw : null;
  }
  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    const parsed = Date.parse(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function normalizeVoiceField(value: unknown): string | null {
  const normalized = String(value ?? "").trim();
  return normalized ? normalized : null;
}

function buildVoiceSelectionKey(
  provider: string | null | undefined,
  voice: string | null | undefined
): string | null {
  const normalizedProvider = normalizeVoiceField(provider);
  const normalizedVoice = normalizeVoiceField(voice);
  if (!normalizedProvider || !normalizedVoice) return null;
  return `${normalizedProvider}::${normalizedVoice}`;
}

function isUnavailableChatError(error: string | null): boolean {
  if (!error) return false;
  const normalized = error.toLowerCase();
  return (
    normalized.includes("temporarily unavailable") ||
    normalized.includes("not authorized") ||
    normalized.includes("thread not found") ||
    normalized.includes("forbidden") ||
    normalized.includes("unavailable in this posture") ||
    normalized.includes("unavailable in this runtime")
  );
}

function buildChatSurfaceState(args: {
  loading: boolean;
  error: string | null;
  hasMessages: boolean;
}): ChatSurfaceState | null {
  if (args.hasMessages) {
    return null;
  }

  if (args.loading) {
    return {
      kind: "loading",
      title: "Loading Guardian chat",
      detail: "Fetching the thread history.",
    };
  }

  if (args.error) {
    if (isUnavailableChatError(args.error)) {
      return {
        kind: "unavailable",
        title: "Chat unavailable",
        detail: args.error,
      };
    }
    return {
      kind: "error",
      title: "Failed to load messages",
      detail: args.error,
    };
  }

  return {
    kind: "empty",
    title: "No messages yet",
    detail: "This thread is ready. Start the conversation below.",
  };
}

function getVoiceSpeakErrorMessage(error: unknown): string {
  const response = error as {
    response?: { data?: { detail?: unknown } | unknown; status?: number };
    message?: string;
  };
  const detail = response?.response?.data;
  if (detail && typeof detail === "object") {
    const candidate = (detail as { detail?: unknown }).detail;
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
    if (candidate != null) {
      return String(candidate);
    }
  }
  if (typeof response?.message === "string" && response.message.trim()) {
    return response.message;
  }
  return error instanceof Error && error.message ? error.message : "Audio unavailable";
}

function ChatSurfaceStateCard({ state }: { state: ChatSurfaceState }) {
  const icon =
    state.kind === "loading" ? (
      <Loader2 className="h-4 w-4 shrink-0 animate-spin" aria-hidden="true" />
    ) : state.kind === "empty" ? (
      <Inbox className="h-4 w-4 shrink-0" aria-hidden="true" />
    ) : (
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
    );

  const toneColor =
    state.kind === "loading" || state.kind === "empty"
      ? "var(--muted)"
      : "rgb(248 113 113)";

  return (
    <div className="w-full flex justify-start" data-testid="chat-surface-state">
      <div
        className="max-w-[min(34rem,calc(100%-1rem))] min-w-0 rounded-[22px] border px-4 py-3 shadow-sm"
        role="status"
        aria-live="polite"
        style={{
          background:
            "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 82%, transparent)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <div className="flex items-center gap-2 text-sm font-medium">
          <span style={{ color: toneColor }}>{icon}</span>
          <span>{state.title}</span>
        </div>
        <div className="mt-1 text-sm leading-6" style={{ color: "var(--muted)" }}>
          {state.detail}
        </div>
      </div>
    </div>
  );
}

export function ChatView({
  threadId,
  guardianName,
  messages,
  loading,
  error,
  hasMore,
  onLoadOlderMessages,
  reloadVersion: _reloadVersion = 0,
  completionState,
  endCompletion: _endCompletion,
  className,
  bottomPadding = 0,
  autoReadEnabled = false,
  voiceReadAloudEnabled = false,
  voiceProvider = null,
  voiceSelectedVoice = null,
  voiceDefaultVoice = null,
  voiceCapabilitiesFailed: _voiceCapabilitiesFailed = false,
  depthMode: _depthMode = "normal",
  profileId: _profileId = null,
  inferenceState = createIdleInferenceRequestState(),
  streamingDraft = null,
  onCancelInference,
  onSwitchToFast,
  codexDraft = null,
  onCodexDraftSave,
  onCodexDraftDownload,
  onCodexDraftDismiss,
}: {
  threadId: number;
  guardianName?: string;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onLoadOlderMessages?: () => Promise<unknown> | unknown;
  reloadVersion?: number;
  completionState: CompletionState;
  endCompletion: () => void;
  className?: string;
  bottomPadding?: number;
  autoReadEnabled?: boolean;
  voiceReadAloudEnabled?: boolean;
  voiceProvider?: string | null;
  voiceSelectedVoice?: string | null;
  voiceDefaultVoice?: string | null;
  voiceCapabilitiesFailed?: boolean;
  depthMode?: DepthMode;
  profileId?: string | null;
  inferenceState?: InferenceRequestState;
  streamingDraft?: StreamingDraft | null;
  onCancelInference?: () => void;
  onSwitchToFast?: () => void;
  codexDraft?: CodexDraft | null;
  onCodexDraftSave?: (draft: CodexDraft) => void | Promise<void>;
  onCodexDraftDownload?: (draft: CodexDraft) => void;
  onCodexDraftDismiss?: () => void;
}) {
  const { containerRef, endRef } = useChatAutoScroll(messages.length);
  const initialScrollRef = useRef(true);
  const initialScrollAppliedRef = useRef(false);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<number | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number; text: string } | null>(null);
  const [voiceUnavailableMessageIds, setVoiceUnavailableMessageIds] = useState<
    Record<number, true>
  >({});
  const voiceUnavailableMessageIdsRef = useRef<Record<number, true>>({});
  const [voiceRouteMissing, setVoiceRouteMissing] = useState(false);
  const voiceRouteMissingRef = useRef(false);
  const [lazyAudioStates, setLazyAudioStates] = useState<
    Record<number, LazyAudioState>
  >({});
  const lastAutoReadMessageIdRef = useRef<number | null>(null);
  const autoReadPrimedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const conversationLaneRef = useRef<HTMLDivElement | null>(null);
  const mobileShellProfile = useMobileShellProfile();
  const viewportInsets = useViewportInsets(mobileShellProfile.active);
  const shouldStickToLatestRef = useRef(true);

  const currentVoiceSelectionKey = buildVoiceSelectionKey(
    voiceProvider,
    voiceSelectedVoice
  );
  const voiceSelectionKeyRef = useRef<string | null>(currentVoiceSelectionKey);

  useEffect(() => {
    voiceSelectionKeyRef.current = currentVoiceSelectionKey;
  }, [currentVoiceSelectionKey]);

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
  const streamingDraftText =
    streamingDraft && streamingDraft.threadId === threadId
      ? streamingDraft.content
      : "";
  const showStreamingDraft = Boolean(streamingDraftText.trim());
  const surfaceState = buildChatSurfaceState({
    loading,
    error,
    hasMessages: messages.length > 0,
  });
  const viewportLayoutSignature = useMemo(
    () =>
      [
        messages.length,
        loading ? "loading" : "idle",
        error ?? "",
        hasMore ? "more" : "none",
        showCompletionIndicator ? "completion" : "steady",
        showStreamingDraft ? "draft" : "no-draft",
      ].join("|"),
    [
      error,
      hasMore,
      loading,
      messages.length,
      showCompletionIndicator,
      showStreamingDraft,
    ]
  );

  const showToast = useCallback((message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message } }));
    } catch {
      // no-op
    }
  }, []);

  const isVoiceUnavailable = useCallback((messageId: number): boolean => {
    return Boolean(voiceUnavailableMessageIdsRef.current[messageId]);
  }, []);

  const markVoiceUnavailable = useCallback((messageId: number) => {
    if (voiceUnavailableMessageIdsRef.current[messageId]) {
      return;
    }
    voiceUnavailableMessageIdsRef.current = {
      ...voiceUnavailableMessageIdsRef.current,
      [messageId]: true,
    };
    setVoiceUnavailableMessageIds(voiceUnavailableMessageIdsRef.current);
  }, []);

  const clearVoiceUnavailable = useCallback((messageId: number) => {
    if (!voiceUnavailableMessageIdsRef.current[messageId]) {
      return;
    }
    const next = { ...voiceUnavailableMessageIdsRef.current };
    delete next[messageId];
    voiceUnavailableMessageIdsRef.current = next;
    setVoiceUnavailableMessageIds(next);
  }, []);

  const measureChatViewport = useCallback(() => {
    const el = containerRef.current;
    if (!el) {
      setHasOverflow(false);
      setShowJumpToLatest(false);
      return;
    }

    const viewportHeight = el.clientHeight;
    const overflowing = viewportHeight > 0 && el.scrollHeight > viewportHeight + 1;
    const distanceFromBottom = Math.max(
      0,
      el.scrollHeight - viewportHeight - el.scrollTop
    );
    shouldStickToLatestRef.current = distanceFromBottom <= 120;
    const shouldShowJump = overflowing && distanceFromBottom > viewportHeight;

    setHasOverflow(overflowing);
    setShowJumpToLatest(shouldShowJump);
  }, [containerRef]);

  const handleJumpToLatest = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;

    el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight);
    shouldStickToLatestRef.current = true;
    measureChatViewport();
    el.dispatchEvent(new Event("scroll", { bubbles: true }));
  }, [containerRef, measureChatViewport]);

  useEffect(() => {
    initialScrollRef.current = true;
    initialScrollAppliedRef.current = false;
    autoReadPrimedRef.current = false;
    lastAutoReadMessageIdRef.current = null;
    shouldStickToLatestRef.current = true;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);
    voiceUnavailableMessageIdsRef.current = {};
    setVoiceUnavailableMessageIds({});
    voiceRouteMissingRef.current = false;
    setVoiceRouteMissing(false);
    setLazyAudioStates({});
    setHasOverflow(false);
    setShowJumpToLatest(false);
  }, [threadId]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);
    voiceUnavailableMessageIdsRef.current = {};
    setVoiceUnavailableMessageIds({});
    setLazyAudioStates({});
  }, [currentVoiceSelectionKey]);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  useLayoutEffect(() => {
    if (!initialScrollAppliedRef.current) return;
    measureChatViewport();
  }, [measureChatViewport, viewportLayoutSignature]);

  useLayoutEffect(() => {
    if (!initialScrollAppliedRef.current) return;
    const el = containerRef.current;
    if (!el) return;

    if (shouldStickToLatestRef.current) {
      el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight);
    }
    measureChatViewport();
  }, [
    bottomPadding,
    containerRef,
    measureChatViewport,
    viewportInsets.keyboardInset,
    viewportInsets.visualViewportHeight,
  ]);

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
              initialScrollAppliedRef.current = true;
              measureChatViewport();
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
      initialScrollAppliedRef.current = true;
      measureChatViewport();
    }
  }, [containerRef, measureChatViewport, messages.length, threadId]);

  useEffect(() => {
    const el = containerRef.current;
    const lane = conversationLaneRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(() => {
      if (!initialScrollAppliedRef.current) return;
      measureChatViewport();
    });
    observer.observe(el);
    if (lane) {
      observer.observe(lane);
    }
    return () => observer.disconnect();
  }, [containerRef, conversationLaneRef, measureChatViewport]);

  const playMessageAudio = useCallback(
    async (
      messageId: number,
      audioUrl: string | null | undefined,
      options?: { manual?: boolean; unavailableMessage?: string }
    ) => {
      const manual = Boolean(options?.manual);
      if (!voiceReadAloudEnabled || voiceRouteMissingRef.current) {
        if (manual) {
          showToast("Voice disabled");
        }
        return;
      }
      if (isVoiceUnavailable(messageId) || !audioUrl) {
        if (manual) {
          showToast(options?.unavailableMessage || "Audio unavailable");
        }
        return;
      }

      try {
        const resolvedSrc =
          typeof audioUrl === "string" && audioUrl.startsWith("http")
            ? audioUrl
            : String(audioUrl || "").startsWith("/")
              ? String(audioUrl)
              : `/${String(audioUrl || "")}`;

        if (audioRef.current) {
          audioRef.current.pause();
        }

        const audio = new Audio(resolvedSrc);
        audioRef.current = audio;
        setPlayingMessageId(messageId);
        audio.onended = () =>
          setPlayingMessageId((previous) =>
            previous === messageId ? null : previous
          );
        audio.onerror = () =>
          setPlayingMessageId((previous) =>
            previous === messageId ? null : previous
          );
        await audio.play();
      } catch (error) {
        console.warn("[chat] playMessageAudio failed", error);
        markVoiceUnavailable(messageId);
        if (manual) {
          showToast(options?.unavailableMessage || "Audio unavailable");
        }
        setPlayingMessageId((previous) =>
          previous === messageId ? null : previous
        );
      }
    },
    [isVoiceUnavailable, markVoiceUnavailable, showToast, voiceReadAloudEnabled]
  );

  const resolveMessageAudioState = useCallback(
    (message: ChatMessage) => {
      const messageId = Number(message.id);
      const override = Number.isFinite(messageId)
        ? lazyAudioStates[messageId]
        : undefined;
      const messageAudioProvider =
        normalizeVoiceField(override?.provider) ??
        normalizeVoiceField(message.audio_provider);
      const messageAudioVoice =
        normalizeVoiceField(override?.voice) ?? normalizeVoiceField(message.audio_voice);
      const messageAudioStatus =
        override?.status ?? (message.audio_status ?? "unavailable");
      const messageAudioUrl =
        override?.audioUrl ??
        (typeof message.audio_url === "string" && message.audio_url.trim()
          ? message.audio_url
          : null);
      const messageAudioError =
        override?.audioError ??
        (typeof message.audio_error === "string" && message.audio_error.trim()
          ? message.audio_error
          : null);
      const messageVoiceKey = buildVoiceSelectionKey(
        messageAudioProvider,
        messageAudioVoice
      );
      const matchesSelectedVoice =
        !currentVoiceSelectionKey ||
        (messageVoiceKey
          ? messageVoiceKey === currentVoiceSelectionKey
          : normalizeVoiceField(voiceSelectedVoice) ===
            normalizeVoiceField(voiceDefaultVoice));
      const resolvedStatus = matchesSelectedVoice
        ? messageAudioStatus
        : "unavailable";
      return {
        messageId,
        status: resolvedStatus,
        url: matchesSelectedVoice ? messageAudioUrl : null,
        error: matchesSelectedVoice ? messageAudioError : null,
      };
    },
    [currentVoiceSelectionKey, lazyAudioStates, voiceDefaultVoice, voiceSelectedVoice]
  );

  const requestAndPlayMessageAudio = useCallback(
    async (message: ChatMessage) => {
      const { messageId } = resolveMessageAudioState(message);
      if (!Number.isFinite(messageId)) {
        return;
      }
      if (!voiceReadAloudEnabled || voiceRouteMissingRef.current) {
        showToast("Voice disabled");
        return;
      }

      clearVoiceUnavailable(messageId);
      setLazyAudioStates((previous) => ({
        ...previous,
        [messageId]: {
          status: "pending",
          audioUrl: null,
          audioError: null,
          provider: normalizeVoiceField(voiceProvider),
          voice: normalizeVoiceField(voiceSelectedVoice),
        },
      }));

      const requestedSelectionKey = buildVoiceSelectionKey(
        voiceProvider,
        voiceSelectedVoice
      );

      try {
        const payload: Record<string, unknown> = {
          force_regenerate: false,
        };
        const normalizedVoiceProvider = normalizeVoiceField(voiceProvider);
        const normalizedVoice = normalizeVoiceField(voiceSelectedVoice);
        if (normalizedVoiceProvider) {
          payload.provider = normalizedVoiceProvider;
        }
        if (normalizedVoice) {
          payload.voice = normalizedVoice;
        }
        const response = await api.post(
          `/voice/messages/${messageId}/speak`,
          payload
        );
        const audioAsset = (response?.data as {
          audio_asset?: { stream_url?: unknown; src_url?: unknown };
        })?.audio_asset;
        const audioUrl =
          typeof audioAsset?.stream_url === "string" &&
          audioAsset.stream_url.trim()
            ? audioAsset.stream_url.trim()
            : typeof audioAsset?.src_url === "string" &&
                audioAsset.src_url.trim()
              ? audioAsset.src_url.trim()
              : null;
        if (!audioUrl) {
          throw new Error("Audio unavailable");
        }

        setLazyAudioStates((previous) => ({
          ...previous,
          [messageId]: {
            status: "ready",
            audioUrl,
            audioError: null,
            provider: normalizeVoiceField(voiceProvider),
            voice: normalizeVoiceField(voiceSelectedVoice),
          },
        }));

        if (requestedSelectionKey !== voiceSelectionKeyRef.current) {
          return;
        }

        await playMessageAudio(messageId, audioUrl, {
          manual: true,
          unavailableMessage: "Audio unavailable",
        });
      } catch (error) {
        const errorMessage = getVoiceSpeakErrorMessage(error);
        setLazyAudioStates((previous) => ({
          ...previous,
          [messageId]: {
            status: "failed",
            audioUrl: null,
            audioError: errorMessage,
            provider: normalizeVoiceField(voiceProvider),
            voice: normalizeVoiceField(voiceSelectedVoice),
          },
        }));
        showToast(errorMessage);
      }
    },
    [
      clearVoiceUnavailable,
      playMessageAudio,
      resolveMessageAudioState,
      showToast,
      voiceProvider,
      voiceSelectedVoice,
      voiceReadAloudEnabled,
    ]
  );

  const handlePlayClick = useCallback(
    (message: ChatMessage) => {
      const audioState = resolveMessageAudioState(message);
      const { messageId, status, url } = audioState;
      if (!Number.isFinite(messageId)) return;
      if (!voiceReadAloudEnabled || voiceRouteMissingRef.current) {
        showToast("Voice disabled");
        return;
      }
      if (status === "pending") {
        showToast("Audio is still generating");
        return;
      }
      if (
        isVoiceUnavailable(messageId) ||
        status !== "ready" ||
        !url
      ) {
        void requestAndPlayMessageAudio(message);
        return;
      }

      void playMessageAudio(messageId, url, {
        manual: true,
        unavailableMessage: audioState.error || "Audio unavailable",
      });
    },
    [
      isVoiceUnavailable,
      playMessageAudio,
      requestAndPlayMessageAudio,
      resolveMessageAudioState,
      showToast,
      voiceReadAloudEnabled,
    ]
  );

  useEffect(() => {
    if (!voiceReadAloudEnabled || !autoReadEnabled) return;
    autoReadPrimedRef.current = true;
    const assistants = messages.filter(
      (message) => message.role !== "user" && Number.isFinite(Number(message.id))
    );
    const latest = assistants.length > 0 ? assistants[assistants.length - 1] : null;
    if (!latest) return;
    const latestId = Number(latest.id);
    if (!Number.isFinite(latestId)) return;
    lastAutoReadMessageIdRef.current = latestId;
  }, [autoReadEnabled, messages, voiceReadAloudEnabled]);

  const onScroll = useCallback(async () => {
    const el = containerRef.current;
    if (!el) return;

    measureChatViewport();

    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(`chat-scroll-${threadId}`, String(el.scrollTop));
      } catch {
        // no-op
      }
    }

    if (loading || !hasMore || !onLoadOlderMessages) return;
    if (el.scrollTop === 0) {
      const previousHeight = el.scrollHeight;
      await onLoadOlderMessages();
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop =
            containerRef.current.scrollHeight - previousHeight;
          measureChatViewport();
        }
      });
    }
  }, [containerRef, hasMore, loading, measureChatViewport, onLoadOlderMessages, threadId]);

  const savePrompt = useCallback((text: string) => {
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
      const parsed = raw ? JSON.parse(raw) : [];
      const next = [item, ...(Array.isArray(parsed) ? parsed : [])];
      localStorage.setItem("cfy.prompts", JSON.stringify(next));
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { message: "Saved to Prompt Library" },
        })
      );
    } catch {
      // no-op
    }
  }, []);

  const shouldMask = hasOverflow && bottomPadding > 0;
  // Mobile bottom-edge contract: when keyboard is open on phone, the composer
  // anchors the bottom and the message lane should not add extra padding.
  const isPhoneClass = mobileShellProfile.active;
  const effectiveBottomPad = resolveMessageLaneBottomPad(
    isPhoneClass,
    viewportInsets.isKeyboardOpen,
    bottomPadding ?? 0
  );
  const scrollStyle: React.CSSProperties = useMemo(
    () => ({
      "--chat-safe-area-bottom": mobileShellProfile.chat.composer.bottomSafeArea,
      paddingBottom: `calc(${effectiveBottomPad}px + var(--chat-safe-area-bottom, 0px))`,
      ...(shouldMask
        ? {
            maskImage:
              "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black 0%, black calc(100% - 80px), transparent 100%)",
          }
        : {}),
    }),
    [effectiveBottomPad, mobileShellProfile.chat.composer.bottomSafeArea, shouldMask]
  );

  return (
    <div className={cn("relative flex min-h-0 min-w-0 flex-col h-full", className)}>
      <div
        ref={containerRef}
        onScroll={() => {
          void onScroll();
        }}
        data-testid="chat-container"
        data-debug-scroll
        className="flex-1 min-h-0 min-w-0 flex flex-col overflow-y-auto overflow-x-hidden overscroll-contain"
        style={{
          ...scrollStyle,
          paddingInline: CHAT_LANE_INLINE_PADDING,
          overflowAnchor: "none",
        }}
      >
        <div
          ref={conversationLaneRef}
          data-testid="chat-conversation-lane"
          className="mx-auto w-full min-w-0 max-w-full md:max-w-[888px] space-y-4"
          style={{ maxWidth: CHAT_LANE_MAX_WIDTH }}
        >
          {surfaceState ? <ChatSurfaceStateCard state={surfaceState} /> : null}
          {messages.map((message, index) => {
            const audioState = resolveMessageAudioState(message);
            const messageId = audioState.messageId;
            const canPlay = message.role !== "user" && Number.isFinite(messageId);
            const messageAudioStatus = audioState.status;
            const messageAudioUrl = audioState.url;
            const showPlay =
              canPlay && voiceReadAloudEnabled && !voiceRouteMissing;
            const messageVoiceUnavailable = Boolean(
              Number.isFinite(messageId) && voiceUnavailableMessageIds[messageId]
            );
            const playState: BubblePlayState = !showPlay
              ? "idle"
              : messageAudioStatus === "pending"
                ? "pending"
                : messageAudioStatus === "failed" ||
                    messageAudioStatus === "unavailable" ||
                    (messageAudioStatus === "ready" && !messageAudioUrl) ||
                    messageVoiceUnavailable
                  ? "unavailable"
                  : playingMessageId === messageId &&
                      messageAudioStatus === "ready" &&
                      Boolean(messageAudioUrl)
                    ? "playing"
                    : "idle";

            return (
                <div
                  data-testid="chat-message"
                  key={message.id ?? `${message.role}-${message.created_at ?? index}`}
                  className="max-w-full"
                  onContextMenu={(event) => {
                    event.preventDefault();
                    const content = parseDocumentContextContent(
                      String(message.content ?? "")
                    ).text;
                    if (!content.trim()) return;
                    setMenu({ x: event.clientX, y: event.clientY, text: content });
                  }}
                >
                <ChatBubble
                  message={{
                    id: String(message.id ?? `${message.role}-${message.created_at ?? index}`),
                    authorId: message.role === "user" ? "me" : "bot",
                    authorName:
                      message.role === "user" ? "You" : guardianName || "Guardian",
                    content: message.content ?? "",
                    createdAt: normalizeMessageTimestamp(message.created_at),
                    attachments: message.attachments?.map((attachment) => ({
                      id: attachment.id,
                      kind: attachment.kind,
                      src: attachment.src_url,
                      name: attachment.filename,
                    })),
                    execution: message.execution,
                  }}
                  isGuardian={message.role !== "user"}
                  showPlay={showPlay}
                  playing={playState === "playing"}
                  playState={playState}
                  isPhoneShell={mobileShellProfile.active}
                  onPlay={() => {
                    if (!Number.isFinite(messageId)) return;
                    handlePlayClick(message);
                  }}
                />
              </div>
            );
          })}

          {codexDraft && onCodexDraftSave && onCodexDraftDownload && onCodexDraftDismiss ? (
            <CodexDraftCard
              draft={codexDraft}
              onSave={onCodexDraftSave}
              onDownload={onCodexDraftDownload}
              onDismiss={onCodexDraftDismiss}
            />
          ) : null}

          {showStreamingDraft ? (
            <div
              className="w-full flex justify-start min-w-0"
              data-testid="chat-streaming-draft"
            >
              <div className="max-w-[min(34rem,calc(100%-1rem))] min-w-0 opacity-90">
                <ChatBubble
                  message={{
                    id: `${threadId}-streaming-draft`,
                    authorId: "bot",
                    authorName: guardianName || "Guardian",
                    content: streamingDraftText,
                    createdAt: streamingDraft?.updatedAt ?? null,
                  }}
                  isGuardian
                  isPhoneShell={mobileShellProfile.active}
                />
              </div>
            </div>
          ) : null}

          {showCompletionIndicator ? (
            <div
              className="w-full flex justify-start"
              data-testid="chat-completing-indicator"
            >
              <div
                className="max-w-[min(34rem,calc(100%-1rem))] min-w-0 rounded-[22px] px-4 py-3 shadow-sm"
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
          ) : null}

          {loading && messages.length > 0 ? (
            <div className="min-w-0 text-xs opacity-70" data-testid="chat-loading">
              Loading...
            </div>
          ) : null}
          {error && messages.length > 0 ? (
            <div className="min-w-0 text-xs text-red-500" data-testid="chat-error">
              {error}
            </div>
          ) : null}
          <div ref={endRef} />
        </div>
      </div>

      {showJumpToLatest ? (
        <div
          className="pointer-events-none absolute inset-x-0 z-30 flex justify-center px-4"
          style={{ bottom: "calc(1rem + var(--chat-safe-area-bottom, 0px))" }}
        >
          <button
            type="button"
            data-testid="jump-to-latest-button"
            aria-label="Jump to latest turn"
            title="Jump to latest turn"
            onClick={handleJumpToLatest}
            className="icon-inline pointer-events-auto inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium shadow-2xl backdrop-blur-xl transition-transform duration-150 hover:-translate-y-0.5"
            style={{
              borderColor: "var(--panel-border)",
              background:
                "color-mix(in oklab, var(--panel-bg) 88%, rgba(255,255,255,0.12))",
              color: "var(--text)",
            }}
          >
            <ArrowDown className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Latest</span>
          </button>
        </div>
      ) : null}

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          onClose={() => setMenu(null)}
          items={[
            {
              label: "Save to Prompt Library",
              onClick: () => savePrompt(menu.text),
            },
          ]}
        />
      ) : null}
    </div>
  );
}

export default ChatView;
