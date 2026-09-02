/**
 * The single portable Conversation window (V1 one-window rule).
 *
 * Renders through the global portal root so it survives SPA navigation.
 * It is a UI projection of the SAME Conversation_ID: closing, popping,
 * minimizing, or restoring never creates, deletes, moves, or rebinds the
 * underlying Conversation.  Dragging is presentation-only and clamped to
 * the usable viewport; coarse pointers get an anchored panel instead.
 */
import { MessageCircle, Minus, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import {
  fetchDirectMessageConversation,
  normalizeDirectMessageError,
  sendDirectMessage,
} from "@/lib/direct-messages";
import type { DirectMessageConversation } from "@/lib/direct-messages";

import { useDirectMessageTranscript } from "./useDirectMessageTranscript";
import type { PeopleMessagingState } from "./usePeopleMessagingState";

type FloatingConversationProps = {
  state: PeopleMessagingState;
};

type PortalTarget = HTMLElement | null;

function portalRoot(): PortalTarget {
  if (typeof document === "undefined") return null;
  return (
    document.getElementById("cfy-portal-root") ??
    document.getElementById("app") ??
    document.getElementById("root") ??
    document.body
  );
}

function profileLabel(conversation: DirectMessageConversation | null): string {
  // Caller-relative only: the backend projects `peer`; never guess from
  // participant order (which could render the caller's own name).
  const peer = conversation?.peer ?? null;
  if (!peer) return "Conversation";
  return peer.display_name?.trim() || peer.username || "Profile";
}

function originBreadcrumb(conversation: DirectMessageConversation | null): string {
  if (!conversation) return "";
  const projectId = conversation.origin.origin_project_id;
  const threadId = conversation.origin.origin_thread_id;
  if (projectId == null && threadId == null) return "General";
  if (threadId == null) return projectId != null ? `Project ${projectId}` : "General";
  return projectId != null ? `Project ${projectId} · Thread ${threadId}` : `Thread ${threadId}`;
}

export default function FloatingConversation({
  state,
}: FloatingConversationProps) {
  const conversationId = state.floatingConversationId;
  const [meta, setMeta] = useState<DirectMessageConversation | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const windowRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    offsetX: number;
    offsetY: number;
  } | null>(null);

  useEffect(() => {
    if (!conversationId) {
      setMeta(null);
      return;
    }
    const cached = state.conversationMetaById[conversationId] ?? null;
    if (cached) {
      setMeta(cached);
      return;
    }
    let cancelled = false;
    void fetchDirectMessageConversation(conversationId)
      .then((conversation) => {
        if (cancelled) return;
        setMeta(conversation);
        state.cacheConversationMeta(conversation);
      })
      .catch(() => {
        if (!cancelled) setMeta(null);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, state]);

  const clampOffset = useCallback((next: { x: number; y: number }) => {
    const element = windowRef.current;
    if (!element || typeof window === "undefined") return next;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const rect = element.getBoundingClientRect();
    const baseLeft = rect.left - next.x;
    const baseTop = rect.top - next.y;
    const margin = 8;
    return {
      x: Math.min(
        Math.max(next.x, margin - baseLeft),
        viewportWidth - margin - (baseLeft + rect.width)
      ),
      y: Math.min(
        Math.max(next.y, margin - baseTop),
        viewportHeight - margin - (baseTop + rect.height)
      ),
    };
  }, []);

  useEffect(() => {
    if (state.floatingMode !== "open") return;
    const handleResize = () => {
      setOffset((current) => clampOffset(current));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [state.floatingMode, clampOffset]);

  const draft = conversationId
    ? (state.draftsByConversationId[conversationId] ?? "")
    : "";
  const cachedMessages = conversationId
    ? (state.messagesByConversationId[conversationId] ?? [])
    : [];
  const loaded =
    conversationId != null &&
    state.loadedByConversationId[conversationId] === true;

  // The transcript hook must not be called conditionally; guard inputs.
  const activeConversationId = conversationId ?? "";
  const transcript = useDirectMessageTranscript(
    activeConversationId,
    conversationId ? cachedMessages : [],
    conversationId ? loaded : true,
    state.replaceMessages,
    state.markTranscriptLoaded
  );

  const handleSend = useCallback(async () => {
    if (!conversationId) return;
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setSendError(null);
    const key = state.getClientMessageKey(conversationId, body);
    try {
      const result = await sendDirectMessage(conversationId, body, key);
      state.acknowledgeClientMessage(conversationId, key);
      state.appendServerMessage(conversationId, result.message);
      state.setDraft(conversationId, "");
    } catch (error) {
      setSendError(normalizeDirectMessageError(error).message);
    } finally {
      setSending(false);
    }
  }, [conversationId, draft, sending, state]);

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (typeof window === "undefined") return;
      if (!window.matchMedia("(pointer: fine)").matches) return;
      if (event.button !== 0) return;
      event.preventDefault();
      dragRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        offsetX: offset.x,
        offsetY: offset.y,
      };
      (event.target as Element).setPointerCapture?.(event.pointerId);
    },
    [offset.x, offset.y]
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) return;
      const next = {
        x: drag.offsetX + (event.clientX - drag.startX),
        y: drag.offsetY + (event.clientY - drag.startY),
      };
      setOffset(clampOffset(next));
    },
    [clampOffset]
  );

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (dragRef.current?.pointerId !== event.pointerId) return;
      dragRef.current = null;
    },
    []
  );

  const target = portalRoot();
  if (!conversationId || state.floatingMode == null || !target) {
    return null;
  }

  const content =
    state.floatingMode === "minimized" ? (
      <div
        className="people-floating-pill"
        role="button"
        tabIndex={0}
        aria-label={`Restore conversation with ${profileLabel(meta)}`}
        data-testid="floating-conversation-pill"
        onClick={state.restoreFloating}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            state.restoreFloating();
          }
        }}
      >
        <span className="contacts-window-avatar" aria-hidden="true">
          {profileLabel(meta)
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0])
            .join("")
            .toUpperCase() || "?"}
        </span>
        <span className="people-floating-pill-copy">
          <span className="people-floating-pill-name">{profileLabel(meta)}</span>
          <span className="people-floating-pill-origin">
            {originBreadcrumb(meta)}
          </span>
        </span>
        <span className="people-floating-pill-actions">
          <button
            type="button"
            aria-label="Close conversation"
            onClick={(event) => {
              event.stopPropagation();
              state.closeFloating();
            }}
          >
            <X size={13} aria-hidden="true" />
          </button>
        </span>
      </div>
    ) : (
      <div
        ref={windowRef}
        className="people-floating-window"
        role="dialog"
        aria-label={`Floating conversation with ${profileLabel(meta)}`}
        data-testid="floating-conversation"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
      >
        <header
          className="people-floating-header"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          <div className="people-floating-identity">
            <span className="people-floating-title">{profileLabel(meta)}</span>
            {originBreadcrumb(meta) ? (
              <span className="people-floating-origin">
                ↳ {originBreadcrumb(meta)}
              </span>
            ) : null}
          </div>
          <div className="people-floating-actions">
            <button
              type="button"
              aria-label="Open in People"
              onClick={state.returnFloatingToPeople}
            >
              <MessageCircle size={14} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Minimize conversation"
              onClick={state.minimizeFloating}
            >
              <Minus size={14} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Close conversation"
              onClick={state.closeFloating}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div
          className="people-floating-transcript"
          role="log"
          aria-label="Message transcript"
        >
          {transcript.loading && transcript.messages.length === 0 ? (
            <p className="people-conversation-hint">Loading messages…</p>
          ) : transcript.messages.length === 0 ? (
            <p className="people-conversation-hint">No messages yet.</p>
          ) : (
            transcript.messages.map((message) => (
              <article key={message.message_id} className="people-message">
                <p className="people-message-body">{message.content.body}</p>
                <time className="people-message-time" dateTime={message.created_at}>
                  {new Date(message.created_at).toLocaleTimeString(undefined, {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
              </article>
            ))
          )}
        </div>

        <div className="people-floating-composer">
          <textarea
            aria-label="Message"
            placeholder="Write a message…"
            value={draft}
            onChange={(event) =>
              state.setDraft(conversationId, event.target.value)
            }
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
          />
          <button
            type="button"
            className="people-conversation-send"
            aria-label="Send message"
            disabled={sending || draft.trim().length === 0}
            onClick={() => void handleSend()}
          >
            <Send size={14} aria-hidden="true" />
            Send
          </button>
        </div>
        {sendError ? <p className="people-inbox-error">{sendError}</p> : null}
      </div>
    );

  return createPortal(content, target);
}
