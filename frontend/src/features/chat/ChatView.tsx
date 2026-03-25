/**
 * ChatView - renders Guardian message history without owning fetch loops.
 */
import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  ChatMessage,
  CompletionState,
} from "@/features/chat/useChat";
import ChatBubble from "@/features/chat/components/ChatBubble";
import InferenceStatusBanner from "@/features/chat/components/InferenceStatusBanner";
import ContextMenu from "@/components/ui/ContextMenu";
import { cn } from "@/lib/utils";
import { useChatAutoScroll } from "@/features/chat/hooks/useChatAutoScroll";
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
  voiceCapabilitiesFailed: _voiceCapabilitiesFailed = false,
  depthMode: _depthMode = "normal",
  profileId: _profileId = null,
  inferenceState = createIdleInferenceRequestState(),
  onCancelInference,
  onSwitchToFast,
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
  voiceCapabilitiesFailed?: boolean;
  depthMode?: DepthMode;
  profileId?: string | null;
  inferenceState?: InferenceRequestState;
  onCancelInference?: () => void;
  onSwitchToFast?: () => void;
}) {
  const { containerRef, endRef } = useChatAutoScroll(messages.length);
  const initialScrollRef = useRef(true);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<number | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number; text: string } | null>(null);
  const [voiceUnavailableMessageIds, setVoiceUnavailableMessageIds] = useState<
    Record<number, true>
  >({});
  const voiceUnavailableMessageIdsRef = useRef<Record<number, true>>({});
  const [voiceRouteMissing, setVoiceRouteMissing] = useState(false);
  const voiceRouteMissingRef = useRef(false);
  const lastAutoReadMessageIdRef = useRef<number | null>(null);
  const autoReadPrimedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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

  useEffect(() => {
    initialScrollRef.current = true;
    autoReadPrimedRef.current = false;
    lastAutoReadMessageIdRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);
    voiceUnavailableMessageIdsRef.current = {};
    setVoiceUnavailableMessageIds({});
    voiceRouteMissingRef.current = false;
    setVoiceRouteMissing(false);
  }, [threadId]);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

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

  const handlePlayClick = useCallback(
    (message: ChatMessage) => {
      const messageId = Number(message.id);
      const messageAudioUrl =
        typeof message.audio_url === "string" && message.audio_url.trim()
          ? message.audio_url
          : null;
      if (!voiceReadAloudEnabled || voiceRouteMissingRef.current) {
        showToast("Voice disabled");
        return;
      }
      if (!Number.isFinite(messageId)) return;
      if (message.audio_status === "pending") {
        showToast("Audio is still generating");
        return;
      }
      if (message.audio_status === "failed") {
        showToast(message.audio_error || "Audio unavailable");
        return;
      }
      if (
        isVoiceUnavailable(messageId) ||
        message.audio_status !== "ready" ||
        !messageAudioUrl
      ) {
        showToast("Audio unavailable");
        return;
      }

      void playMessageAudio(messageId, messageAudioUrl, {
        manual: true,
        unavailableMessage: message.audio_error || "Audio unavailable",
      });
    },
    [isVoiceUnavailable, playMessageAudio, showToast, voiceReadAloudEnabled]
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
        }
      });
    }
  }, [containerRef, hasMore, loading, onLoadOlderMessages, threadId]);

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
        onScroll={() => {
          void onScroll();
        }}
        data-testid="chat-container"
        data-debug-scroll
        className="flex-1 min-h-0 flex flex-col overflow-y-auto overscroll-contain px-4 space-y-4"
        style={scrollStyle}
      >
        {messages.map((message, index) => {
          const messageId = Number(message.id);
          const canPlay = message.role !== "user" && Number.isFinite(messageId);
          const messageAudioStatus = message.audio_status;
          const messageAudioUrl =
            typeof message.audio_url === "string" && message.audio_url.trim()
              ? message.audio_url
              : null;
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
                const content = String(message.content ?? "");
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
                }}
                isGuardian={message.role !== "user"}
                showPlay={showPlay}
                playing={playState === "playing"}
                playState={playState}
                onPlay={() => {
                  if (!Number.isFinite(messageId)) return;
                  handlePlayClick(message);
                }}
              />
            </div>
          );
        })}

        {showCompletionIndicator ? (
          <div
            className="mx-4 mb-2 flex max-w-full justify-start"
            data-testid="chat-completing-indicator"
          >
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
        ) : null}

        {loading ? (
          <div className="text-xs opacity-70" data-testid="chat-loading">
            Loading...
          </div>
        ) : null}
        {error ? (
          <div className="text-xs text-red-500" data-testid="chat-error">
            {error}
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

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
