/**
 * Share Sheet — person-aware routing for Thread/Document shares.
 *
 * Orchestrates two existing authority-bearing contracts without adding
 * authority of its own:
 *   1. the tokenized read-only share-link contract (POST /api/share);
 *   2. the direct-message Relationship → Conversation contract.
 *
 * Truth rules enforced here:
 * - Opening/closing the sheet creates nothing (no token, no Relationship,
 *   no Conversation, no Message).
 * - Exactly one share token per submission attempt; the generated URL is
 *   preserved across all downstream retry states.
 * - An existing Conversation's origin/placement are never touched.
 * - A new Conversation captures canonical Project/Thread origin only when
 *   the shell provides it — never guessed from labels or DOM text.
 * - A share URL is token-authorized for anyone who holds it; sending it in
 *   a Conversation does NOT make it recipient-exclusive.  The UI copy says
 *   so.
 */
import { Check, Copy, Link2, Loader2, Search, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { RuntimeRouteCapabilityState } from "@/contracts/supportedProfileRoutes";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import {
  createDirectMessageConversation,
  fetchRelationshipConversations,
  fetchThreadProjectScope,
  peerPresentationLabel,
  resolveDirectMessageRelationship,
  searchDirectMessageProfiles,
  sendDirectMessage,
  type DirectMessageConversation,
  type DirectMessageRelationship,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";
import { resolveSharePublicUrl } from "@/lib/runtimeConfig";
import {
  copyTextWithFallback,
  createShareLink,
  type CopyMethod,
  type CreateShareResult,
} from "@/lib/share-links";

import "./ShareSheet.css";

export type ShareSheetProps = {
  targetType: "thread" | "document";
  targetId: number;
  open: boolean;
  onClose: () => void;
  /** Capability posture for `direct_messages`; Send to Person requires
   *  "available" and must fire zero DM requests otherwise. */
  capabilityState: RuntimeRouteCapabilityState;
  /** Existing shell-owned People state; when absent Send to Person is
   *  hidden (standalone mounts keep Copy Link only). */
  peopleState: PeopleMessagingState | null;
  /** Canonical shell thread scope used ONLY as a new-Conversation origin.
   *  Never used to rebind an existing Conversation. */
  sourceThreadId?: number | null;
  /** Canonical project scope (project-only surfaces; optional). */
  sourceProjectId?: number | null;
};

type Stage = "actions" | "person" | "conversations" | "result";

type SendPhase =
  | "idle"
  | "resolving"
  | "ready"
  | "creating_link"
  | "link_failed"
  | "creating_conversation"
  | "conversation_failed"
  | "sending"
  | "send_failed"
  | "complete";

type SendFlow = {
  phase: SendPhase;
  profile: DirectMessageSocialProfile | null;
  relationship: DirectMessageRelationship | null;
  conversations: DirectMessageConversation[];
  /** Existing destination Conversation_ID, or null for "New Conversation". */
  choice: string | null;
  choiceIsNew: boolean;
  /** Conversation created by this submission (reused on retries). */
  createdConversationId: string | null;
  link: CreateShareResult | null;
  linkUrl: string | null;
  clientMessageKey: string | null;
  error: string | null;
  sentMessageBody: string | null;
};

const INITIAL_FLOW: SendFlow = {
  phase: "idle",
  profile: null,
  relationship: null,
  conversations: [],
  choice: null,
  choiceIsNew: false,
  createdConversationId: null,
  link: null,
  linkUrl: null,
  clientMessageKey: null,
  error: null,
  sentMessageBody: null,
};

function portalRoot(): HTMLElement | null {
  if (typeof document === "undefined") return null;
  return (
    document.getElementById("cfy-portal-root") ??
    document.getElementById("app") ??
    document.getElementById("root") ??
    document.body
  );
}

export default function ShareSheet({
  targetType,
  targetId,
  open,
  onClose,
  capabilityState,
  peopleState,
  sourceThreadId = null,
  sourceProjectId = null,
}: ShareSheetProps) {
  const [stage, setStage] = useState<Stage>("actions");
  const [copyState, setCopyState] = useState<{
    phase: "idle" | "copying" | "copied" | "failed";
    url: string | null;
    message: string | null;
  }>({ phase: "idle", url: null, message: null });
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DirectMessageSocialProfile[]>(
    []
  );
  const [flow, setFlow] = useState<SendFlow>(INITIAL_FLOW);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const messagingEnabled = capabilityState === "available" && peopleState != null;

  // Reset transient state when the sheet opens.
  useEffect(() => {
    if (!open) return;
    setStage("actions");
    setCopyState({ phase: "idle", url: null, message: null });
    setSearchQuery("");
    setSearchResults([]);
    setFlow(INITIAL_FLOW);
  }, [open]);

  useEffect(() => {
    if (!open || typeof window === "undefined") return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  const close = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleCopyLink = useCallback(async () => {
    setCopyState({ phase: "copying", url: null, message: null });
    try {
      const result = await createShareLink(targetType, targetId);
      const fullUrl = resolveSharePublicUrl(String(result.url || ""));
      const method: CopyMethod = await copyTextWithFallback(fullUrl);
      setCopyState({
        phase: "copied",
        url: fullUrl,
        message:
          method === "clipboard" || method === "execCommand"
            ? "Share link copied."
            : method === "prompt"
              ? "Share link ready to copy:"
              : "Share link created:",
      });
    } catch (error) {
      setCopyState({
        phase: "failed",
        url: null,
        message: error instanceof Error ? error.message : "Failed to create share link",
      });
    }
  }, [targetType, targetId]);

  const runSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      setSearchResults(await searchDirectMessageProfiles(trimmed));
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleQueryChange = useCallback(
    (value: string) => {
      setSearchQuery(value);
      if (searchTimer.current) window.clearTimeout(searchTimer.current);
      searchTimer.current = window.setTimeout(() => {
        void runSearch(value);
      }, 250);
    },
    [runSearch]
  );

  const selectProfile = useCallback(
    async (profile: DirectMessageSocialProfile) => {
      setFlow({ ...INITIAL_FLOW, phase: "resolving", profile });
      setStage("conversations");
      try {
        const relationship = await resolveDirectMessageRelationship(
          profile.node_id,
          profile.profile_id
        );
        const conversations = await fetchRelationshipConversations(
          relationship.relationship_id
        );
        setFlow({
          ...INITIAL_FLOW,
          phase: "ready",
          profile,
          relationship,
          conversations,
          choice: null,
          choiceIsNew: false,
        });
      } catch (error) {
        setFlow({
          ...INITIAL_FLOW,
          phase: "link_failed",
          profile,
          error:
            error instanceof Error
              ? error.message
              : "Could not resolve this person's Relationship.",
        });
      }
    },
    []
  );

  const computeOrigin = useCallback(async () => {
    if (sourceThreadId != null) {
      const projectId = await fetchThreadProjectScope(sourceThreadId);
      if (projectId != null) {
        return {
          origin_project_id: projectId,
          origin_thread_id: sourceThreadId,
        };
      }
      return {};
    }
    if (sourceProjectId != null) {
      return { origin_project_id: sourceProjectId, origin_thread_id: null };
    }
    return {};
  }, [sourceThreadId, sourceProjectId]);

  /**
   * Runs the composite operation for one destination choice.
   * - Creates the share link at most once per submission (per choice).
   * - Sends the same URL with one stable client message key, so retries
   *   replay idempotently on the backend.
   */
  const submitChoice = useCallback(
    async (choice: string | null, choiceIsNew: boolean) => {
      if (!peopleState || !flow.relationship) return;
      const relationshipId = flow.relationship.relationship_id;

      let conversationId = choice;
      let createdConversationId = flow.createdConversationId;
      setFlow((current) => ({
        ...current,
        choice,
        choiceIsNew,
        error: null,
        phase:
          choiceIsNew && !createdConversationId
            ? "creating_conversation"
            : "creating_link",
      }));

      try {
        if (choiceIsNew) {
          if (createdConversationId != null) {
            // Retry path: never re-create the already-created Conversation.
            conversationId = createdConversationId;
          } else {
            const origin = await computeOrigin();
            const conversation = await createDirectMessageConversation(
              relationshipId,
              origin
            );
            conversationId = conversation.conversation_id;
            createdConversationId = conversation.conversation_id;
            peopleState.cacheConversationMeta(conversation);
            setFlow((current) => ({
              ...current,
              createdConversationId,
            }));
          }
        }
      } catch (error) {
        setFlow((current) => ({
          ...current,
          phase: "conversation_failed",
          error:
            error instanceof Error
              ? error.message
              : "Could not create the Conversation.",
        }));
        return;
      }

      // Share-link creation: exactly once per submission attempt.
      let link = flow.link;
      if (!link) {
        setFlow((current) => ({
          ...current,
          phase: "creating_link",
          error: null,
        }));
        try {
          link = await createShareLink(targetType, targetId);
          setFlow((current) => ({
            ...current,
            link,
            linkUrl: resolveSharePublicUrl(String(link?.url || "")),
          }));
        } catch (error) {
          setFlow((current) => ({
            ...current,
            phase: "link_failed",
            error:
              error instanceof Error
                ? error.message
                : "Failed to create share link",
          }));
          return;
        }
      }
      if (!link || conversationId == null) return;
      const fullUrl = resolveSharePublicUrl(String(link.url || ""));

      const key = flow.clientMessageKey ?? crypto.randomUUID();
      setFlow((current) => ({
        ...current,
        phase: "sending",
        error: null,
        clientMessageKey: key,
      }));
      try {
        await sendDirectMessage(conversationId, fullUrl, key);
        setFlow((current) => ({
          ...current,
          phase: "complete",
          sentMessageBody: fullUrl,
        }));
        setStage("result");
        peopleState.openConversation(conversationId, undefined);
        peopleState.openPeople();
      } catch (error) {
        setFlow((current) => ({
          ...current,
          phase: "send_failed",
          error:
            error instanceof Error
              ? error.message
              : "The message was not sent.",
        }));
        setStage("result");
      }
    },
    [
      computeOrigin,
      flow.clientMessageKey,
      flow.createdConversationId,
      flow.link,
      flow.relationship,
      peopleState,
      targetId,
      targetType,
    ]
  );

  if (!open) return null;
  const target = portalRoot();
  if (!target) return null;

  const sourceLabel = targetType === "thread" ? "Thread" : "Document";
  const showRetrySend = flow.phase === "send_failed" && flow.linkUrl != null;
  const showRetryLink =
    flow.phase === "link_failed" &&
    (flow.choice != null || flow.createdConversationId != null);
  const showRetryConversation = flow.phase === "conversation_failed";

  return createPortal(
    <div className="share-sheet-overlay" role="presentation">
      <div
        className="share-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Share"
        data-testid="share-sheet"
        onClick={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <header className="share-sheet-header">
          <div>
            <h2 className="share-sheet-title">Share {sourceLabel}</h2>
            <p className="share-sheet-subcopy">
              Where do you want this to go?
            </p>
          </div>
          <button
            type="button"
            className="share-sheet-close"
            aria-label="Close Share"
            onClick={close}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </header>

        {stage === "actions" ? (
          <div className="share-sheet-actions">
            <button
              type="button"
              className="share-sheet-action"
              data-testid="share-action-copy"
              disabled={copyState.phase === "copying"}
              onClick={() => void handleCopyLink()}
            >
              <Link2 size={15} aria-hidden="true" />
              <span>
                <strong>Copy Link</strong>
                <small>Create a secure share link and copy it.</small>
              </span>
            </button>

            {messagingEnabled ? (
              <button
                type="button"
                className="share-sheet-action"
                data-testid="share-action-send-person"
                onClick={() => {
                  setStage("person");
                  setSearchQuery("");
                  setSearchResults([]);
                }}
              >
                <Send size={15} aria-hidden="true" />
                <span>
                  <strong>Send to Person</strong>
                  <small>
                    Creates a secure share link and sends it in this
                    conversation. Anyone with the link can view it.
                  </small>
                </span>
              </button>
            ) : (
              <div
                className="share-sheet-action share-sheet-action-disabled"
                data-testid="share-action-send-person-unavailable"
                aria-disabled="true"
              >
                <Send size={15} aria-hidden="true" />
                <span>
                  <strong>Send to Person</strong>
                  <small>
                    Direct messages are unavailable in this profile.
                  </small>
                </span>
              </div>
            )}

            {copyState.phase === "copying" ? (
              <p className="share-sheet-status">
                <Loader2 size={13} className="spin" aria-hidden="true" />
                Creating share link…
              </p>
            ) : null}
            {copyState.phase === "copied" ? (
              <p className="share-sheet-status share-sheet-status-ok" data-testid="copy-success">
                <Check size={13} aria-hidden="true" />
                {copyState.message}{" "}
                <span className="share-sheet-url">{copyState.url}</span>
              </p>
            ) : null}
            {copyState.phase === "failed" ? (
              <p className="share-sheet-status share-sheet-status-error">
                {copyState.message}
              </p>
            ) : null}
          </div>
        ) : null}

        {stage === "person" ? (
          <div className="share-sheet-person">
            <label
              className="share-sheet-search"
              aria-label="Search for a person"
            >
              <Search size={13} aria-hidden="true" />
              <input
                type="search"
                value={searchQuery}
                placeholder="Search by Codexify username"
                aria-label="Search profiles by username"
                onChange={(event) => handleQueryChange(event.target.value)}
              />
            </label>
            {searching ? <p className="share-sheet-status">Searching…</p> : null}
            {!searching && searchQuery.trim() && searchResults.length === 0 ? (
              <p className="share-sheet-status">
                No profiles match that username.
              </p>
            ) : null}
            <div className="share-sheet-results" role="list">
              {searchResults.map((profile) => (
                <button
                  key={`${profile.node_id}:${profile.profile_id}`}
                  type="button"
                  className="share-sheet-result"
                  data-testid="share-person-result"
                  onClick={() => void selectProfile(profile)}
                >
                  <span>{peerPresentationLabel(profile)}</span>
                  {profile.username ? (
                    <span className="share-sheet-username">
                      @{profile.username}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="share-sheet-back"
              onClick={() => setStage("actions")}
            >
              Back
            </button>
          </div>
        ) : null}

        {stage === "conversations" ? (
          <div className="share-sheet-conversations">
            {flow.phase === "resolving" ? (
              <p className="share-sheet-status">
                <Loader2 size={13} className="spin" aria-hidden="true" />
                Resolving {peerPresentationLabel(flow.profile)}…
              </p>
            ) : (
              <>
                <p className="share-sheet-subcopy">
                  Send this share link to{" "}
                  <strong>{peerPresentationLabel(flow.profile)}</strong> in:
                </p>
                <div className="share-sheet-choices" role="radiogroup" aria-label="Destination conversation">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={flow.choiceIsNew}
                    className="share-sheet-choice"
                    data-testid="share-choice-new"
                    onClick={() => setFlow((c) => ({ ...c, choice: null, choiceIsNew: true }))}
                  >
                    <strong>New Conversation</strong>
                    <small>
                      Created under your existing Relationship with this
                      person.
                    </small>
                  </button>
                  {flow.conversations.map((conversation) => (
                    <button
                      key={conversation.conversation_id}
                      type="button"
                      role="radio"
                      aria-checked={
                        !flow.choiceIsNew &&
                        flow.choice === conversation.conversation_id
                      }
                      className="share-sheet-choice"
                      data-testid={`share-choice-${conversation.conversation_id}`}
                      onClick={() =>
                        setFlow((c) => ({
                          ...c,
                          choice: conversation.conversation_id,
                          choiceIsNew: false,
                        }))
                      }
                    >
                      <strong>
                        Conversation · {new Date(conversation.created_at).toLocaleDateString()}
                      </strong>
                      <small>
                        Existing conversation — its origin and placement are
                        never changed.
                      </small>
                    </button>
                  ))}
                </div>
                <p className="share-sheet-privacy">
                  A share link is secure but not exclusive: anyone with the
                  link can view the shared content. Sending it here keeps the
                  conversation private.
                </p>
                <button
                  type="button"
                  className="share-sheet-primary"
                  data-testid="share-submit"
                  disabled={
                    flow.choiceIsNew ? false : flow.choice == null
                  }
                  onClick={() =>
                    void submitChoice(flow.choice, flow.choiceIsNew)
                  }
                >
                  Send share link
                </button>
                <button
                  type="button"
                  className="share-sheet-back"
                  onClick={() => setStage("person")}
                >
                  Back
                </button>
              </>
            )}
          </div>
        ) : null}

        {stage === "result" || showRetrySend || showRetryLink || showRetryConversation ? (
          <div className="share-sheet-result" data-testid="share-result">
            {flow.phase === "complete" ? (
              <p className="share-sheet-status share-sheet-status-ok">
                <Check size={13} aria-hidden="true" />
                Share link sent in the conversation.
              </p>
            ) : null}
            {showRetrySend ? (
              <>
                <p className="share-sheet-status share-sheet-status-error">
                  Share link created, but the message was not sent.
                </p>
                <button
                  type="button"
                  className="share-sheet-primary"
                  data-testid="share-retry-send"
                  onClick={() =>
                    void submitChoice(flow.choice, flow.choiceIsNew)
                  }
                >
                  Retry Send
                </button>
              </>
            ) : null}
            {showRetryLink ? (
              <>
                <p className="share-sheet-status share-sheet-status-error">
                  Share link creation failed. {flow.error}
                </p>
                <button
                  type="button"
                  className="share-sheet-primary"
                  data-testid="share-retry-link"
                  onClick={() =>
                    void submitChoice(flow.choice, flow.choiceIsNew)
                  }
                >
                  Retry Link
                </button>
              </>
            ) : null}
            {showRetryConversation ? (
              <>
                <p className="share-sheet-status share-sheet-status-error">
                  Conversation creation failed.
                </p>
                <button
                  type="button"
                  className="share-sheet-primary"
                  data-testid="share-retry-conversation"
                  onClick={() =>
                    void submitChoice(flow.choice, flow.choiceIsNew)
                  }
                >
                  Retry Conversation
                </button>
              </>
            ) : null}
            {flow.linkUrl ? (
              <div
                className="share-sheet-created-link"
                data-testid="share-created-link"
              >
                <span>Share link created:</span>
                <code className="share-sheet-url">{flow.linkUrl}</code>
                <button
                  type="button"
                  className="share-sheet-copy"
                  data-testid="share-copy-link"
                  onClick={() => void copyTextWithFallback(flow.linkUrl ?? "")}
                >
                  <Copy size={12} aria-hidden="true" />
                  Copy Link
                </button>
              </div>
            ) : null}
            <button
              type="button"
              className="share-sheet-back"
              onClick={close}
            >
              Close
            </button>
          </div>
        ) : null}
      </div>
    </div>,
    target
  );
}
