/**
 * Conversation view inside People: durable transcript + composer.
 *
 * Messages are server-authoritative: rendering comes from the backend's
 * chronological read, sends use the existing endpoint, and replayed
 * (idempotent) responses dedupe by the server-returned Message_ID.
 */
import { ArrowLeft, ExternalLink, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  fetchDirectMessageConversation,
  normalizeDirectMessageError,
  sendDirectMessage,
} from "@/lib/direct-messages";
import type { DirectMessageConversation } from "@/lib/direct-messages";

import { useDirectMessageTranscript } from "./useDirectMessageTranscript";
import type { PeopleMessagingState } from "./usePeopleMessagingState";

type DirectConversationProps = {
  conversationId: string;
  state: PeopleMessagingState;
  projectLabels: Map<number, string>;
  onBack: () => void;
};

function originBreadcrumb(
  conversation: DirectMessageConversation | null,
  labels: Map<number, string>
): string {
  if (!conversation) return "";
  const projectId = conversation.origin.origin_project_id;
  const threadId = conversation.origin.origin_thread_id;
  if (projectId == null && threadId == null) return "General";
  const project = projectId == null ? null : (labels.get(projectId) ?? "Project");
  if (threadId == null) return project ?? "General";
  return project ? `${project} · Thread ${threadId}` : `Thread ${threadId}`;
}

function placementLabel(
  conversation: DirectMessageConversation | null,
  labels: Map<number, string>
): string {
  if (!conversation) return "";
  const projectId = conversation.placement.project_id;
  if (projectId == null) return "Unscoped";
  return labels.get(projectId) ?? "Project";
}

export default function DirectConversation({
  conversationId,
  state,
  projectLabels,
  onBack,
}: DirectConversationProps) {
  const [meta, setMeta] = useState<DirectMessageConversation | null>(
    state.conversationMetaById[conversationId] ?? null
  );
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => {
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

  const draft = state.draftsByConversationId[conversationId] ?? "";
  const cachedMessages = state.messagesByConversationId[conversationId] ?? [];
  const loaded = state.loadedByConversationId[conversationId] === true;
  const transcript = useDirectMessageTranscript(
    conversationId,
    cachedMessages,
    loaded,
    state.replaceMessages,
    state.markTranscriptLoaded
  );

  const isFloating = state.floatingConversationId === conversationId;
  const anotherIsFloating =
    state.floatingConversationId !== null &&
    state.floatingConversationId !== conversationId;

  const handleSend = useCallback(async () => {
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setSendError(null);
    try {
      const key = crypto.randomUUID();
      const result = await sendDirectMessage(conversationId, body, key);
      state.appendServerMessage(conversationId, result.message);
      state.setDraft(conversationId, "");
    } catch (error) {
      setSendError(normalizeDirectMessageError(error).message);
    } finally {
      setSending(false);
    }
  }, [conversationId, draft, sending, state]);

  const handlePopOut = useCallback(() => {
    state.popOutConversation(conversationId, meta ?? undefined);
  }, [conversationId, meta, state]);

  return (
    <section
      className="people-conversation"
      aria-label="Direct conversation"
      data-testid="direct-conversation"
    >
      <header className="people-conversation-header">
        <button
          type="button"
          className="people-back"
          aria-label="Back to conversations with this person"
          onClick={onBack}
        >
          <ArrowLeft size={15} aria-hidden="true" />
          Person
        </button>
        <div className="people-conversation-header-actions">
          {meta ? (
            <span className="people-conversation-breadcrumb">
              ↳ {originBreadcrumb(meta, projectLabels)} · placed in{" "}
              {placementLabel(meta, projectLabels)}
            </span>
          ) : null}
          <button
            type="button"
            className="people-conversation-popout"
            aria-label="Pop out conversation"
            title={
              anotherIsFloating
                ? "Close the floating conversation first"
                : "Pop this conversation out"
            }
            disabled={anotherIsFloating}
            onClick={handlePopOut}
          >
            <ExternalLink size={14} aria-hidden="true" />
            Pop Out
          </button>
        </div>
      </header>

      {isFloating ? (
        <div className="people-conversation-floating-note">
          <p>This conversation is open in the floating window.</p>
          <button
            type="button"
            className="people-conversation-return"
            onClick={state.returnFloatingToPeople}
          >
            Return it here
          </button>
        </div>
      ) : null}

      <div
        className="people-conversation-transcript"
        role="log"
        aria-label="Message transcript"
        data-testid="conversation-transcript"
      >
        {transcript.loading && transcript.messages.length === 0 ? (
          <p className="people-conversation-hint">Loading messages…</p>
        ) : transcript.error && transcript.messages.length === 0 ? (
          <p className="people-conversation-hint">{transcript.error}</p>
        ) : transcript.messages.length === 0 ? (
          <p className="people-conversation-hint">
            No messages yet. Say hello.
          </p>
        ) : (
          transcript.messages.map((message) => (
            <article
              key={message.message_id}
              className="people-message"
              data-testid="direct-message"
            >
              <p className="people-message-body">{message.content.body}</p>
              <time
                className="people-message-time"
                dateTime={message.created_at}
              >
                {new Date(message.created_at).toLocaleTimeString(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </article>
          ))
        )}
      </div>

      {!isFloating ? (
        <div className="people-conversation-composer">
          <textarea
            aria-label="Message"
            placeholder="Write a message…"
            value={draft}
            onChange={(event) => state.setDraft(conversationId, event.target.value)}
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
      ) : null}
      {sendError ? <p className="people-inbox-error">{sendError}</p> : null}
    </section>
  );
}
