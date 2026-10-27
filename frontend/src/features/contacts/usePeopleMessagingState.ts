/**
 * Bounded People-surface state owner.
 *
 * Lives at the globally mounted launcher seam (above `ContactsWindow`)
 * so closing the modal never destroys the portable conversation, and the
 * floating window survives SPA navigation.  This is NOT a general window
 * manager: exactly one Conversation may be floating/parked at a time.
 *
 * Server authority notes:
 * - drafts are SPA-session-local only (never persisted, never sent);
 * - the message cache only ever holds server-returned durable messages;
 * - closing the floating UI mutates UI state only — it never deletes,
 *   moves, or rebinds a Conversation.
 */
import { useCallback, useMemo, useRef, useState } from "react";

import type {
  DirectMessageConversation,
  DirectMessageEnvelope,
} from "@/lib/direct-messages";
import {
  fetchDirectMessageConversations,
  markDirectMessageConversationRead,
} from "@/lib/direct-messages";

import type { PeopleTab } from "./types";

export type FloatingMode = null | "open" | "minimized";

export type PeopleMessagingState = {
  peopleOpen: boolean;
  activeTab: PeopleTab;
  selectedRelationshipId: string | null;
  selectedConversationId: string | null;
  floatingConversationId: string | null;
  floatingMode: FloatingMode;
  draftsByConversationId: Record<string, string>;
  messagesByConversationId: Record<string, DirectMessageEnvelope[]>;
  loadedByConversationId: Record<string, boolean>;
  conversationMetaById: Record<string, DirectMessageConversation>;
  /**
   * Total unread messages across every cached Conversation, derived from
   * the caller-local read projection.  Every presentation surface reads
   * this one projection: the Inbox badges, the launcher badge, and the
   * floating window.  It is derived, never stored, and the peer can never
   * observe it.
   */
  unreadTotal: number;
  openPeople: () => void;
  closePeople: () => void;
  setTab: (tab: PeopleTab) => void;
  openRelationship: (relationshipId: string | null) => void;
  openConversation: (
    conversationId: string,
    meta?: DirectMessageConversation
  ) => void;
  closeConversation: () => void;
  popOutConversation: (
    conversationId: string,
    meta?: DirectMessageConversation
  ) => boolean;
  minimizeFloating: () => void;
  restoreFloating: () => void;
  closeFloating: () => void;
  returnFloatingToPeople: () => void;
  setDraft: (conversationId: string, draft: string) => void;
  getClientMessageKey: (conversationId: string, body: string) => string;
  acknowledgeClientMessage: (conversationId: string, key: string) => void;
  cacheConversationMeta: (conversation: DirectMessageConversation) => void;
  replaceMessages: (
    conversationId: string,
    messages: DirectMessageEnvelope[]
  ) => void;
  appendServerMessage: (
    conversationId: string,
    message: DirectMessageEnvelope
  ) => void;
  markTranscriptLoaded: (conversationId: string) => void;
  /**
   * Load the caller-local read projection — every Conversation the caller
   * participates in, with its recipient-local unread count — and cache it in
   * the shared projection every presentation surface reads.
   *
   * This is the ONLY read path for the conversation projection.  The Inbox,
   * the launcher badge, and the floating window all read the same cached
   * projection; there is no second projection and no notification store.
   * Resolves to the projected Conversations.
   */
  refreshUnreadProjection: () => Promise<DirectMessageConversation[]>;
  /**
   * Load the read projection at most once for this state owner.
   *
   * The launcher badge must be able to show the unread count without the
   * People window being open, and the People window is the only place the
   * Inbox is rendered.  Several surfaces can mount together, so the load is
   * guarded to happen once per owner rather than once per surface.
   */
  ensureUnreadProjection: () => Promise<void>;
  /**
   * Advance the caller's own recipient-local read cursor for one
   * Conversation, to the supplied read watermark.  Shared by every
   * presentation surface so the cursor advances through one path.
   */
  markConversationRead: (
    conversationId: string,
    watermarkMessageId: string | null,
  ) => Promise<boolean>;
};

export function usePeopleMessagingState(): PeopleMessagingState {
  const pendingSendByConversationId = useRef<
    Record<string, { body: string; key: string }>
  >({});
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<PeopleTab>("inbox");
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<
    string | null
  >(null);
  const [selectedConversationId, setSelectedConversationId] = useState<
    string | null
  >(null);
  const [floatingConversationId, setFloatingConversationId] = useState<
    string | null
  >(null);
  const [floatingMode, setFloatingMode] = useState<FloatingMode>(null);
  const [draftsByConversationId, setDraftsByConversationId] = useState<
    Record<string, string>
  >({});
  const [messagesByConversationId, setMessagesByConversationId] = useState<
    Record<string, DirectMessageEnvelope[]>
  >({});
  const [loadedByConversationId, setLoadedByConversationId] = useState<
    Record<string, boolean>
  >({});
  const [conversationMetaById, setConversationMetaById] = useState<
    Record<string, DirectMessageConversation>
  >({});

  const openPeople = useCallback(() => setPeopleOpen(true), []);
  const closePeople = useCallback(() => setPeopleOpen(false), []);
  const setTab = useCallback((tab: PeopleTab) => setActiveTab(tab), []);

  const openRelationship = useCallback((relationshipId: string | null) => {
    setSelectedRelationshipId(relationshipId);
    setSelectedConversationId(null);
  }, []);

  const cacheConversationMeta = useCallback(
    (conversation: DirectMessageConversation) => {
      // A malformed projection must never crash the surface that received
      // it: a truncated response is not a reason to take the People window
      // down.
      if (!conversation || !conversation.conversation_id) return;
      setConversationMetaById((current) => {
        const existing = current[conversation.conversation_id];
        // Keep the existing entry when the server returned the same
        // conversation.  Replacing it with an equal-but-new object changes
        // this map's identity, which replaces the whole People state object,
        // which recreates any callback that depends on it — and a callback
        // that re-fetches the conversation projection would then fetch,
        // cache, replace, and fetch again.
        if (
          existing &&
          existing.unread_count === conversation.unread_count &&
          existing.latest_activity_at === conversation.latest_activity_at
        ) {
          return current;
        }
        return {
          ...current,
          [conversation.conversation_id]: conversation,
        };
      });
    },
    []
  );

  const openConversation = useCallback(
    (conversationId: string, meta?: DirectMessageConversation) => {
      if (meta) cacheConversationMeta(meta);
      setSelectedConversationId(conversationId);
    },
    [cacheConversationMeta]
  );

  const closeConversation = useCallback(() => {
    setSelectedConversationId(null);
  }, []);

  const popOutConversation = useCallback(
    (
      conversationId: string,
      meta?: DirectMessageConversation
    ): boolean => {
      if (meta) cacheConversationMeta(meta);
      // One-window V1 rule: never silently replace an active portable
      // conversation.  The caller disables the action instead.
      if (
        floatingConversationId !== null &&
        floatingConversationId !== conversationId
      ) {
        return false;
      }
      setFloatingConversationId(conversationId);
      setFloatingMode("open");
      return true;
    },
    [cacheConversationMeta, floatingConversationId]
  );

  const minimizeFloating = useCallback(() => setFloatingMode("minimized"), []);
  const restoreFloating = useCallback(() => setFloatingMode("open"), []);

  const closeFloating = useCallback(() => {
    setFloatingConversationId(null);
    setFloatingMode(null);
  }, []);

  const returnFloatingToPeople = useCallback(() => {
    const conversationId = floatingConversationId;
    if (!conversationId) return;
    setFloatingConversationId(null);
    setFloatingMode(null);
    setSelectedConversationId(conversationId);
    setActiveTab("inbox");
    setPeopleOpen(true);
  }, [floatingConversationId]);

  const setDraft = useCallback((conversationId: string, draft: string) => {
    setDraftsByConversationId((current) => ({
      ...current,
      [conversationId]: draft,
    }));
  }, []);

  const getClientMessageKey = useCallback(
    (conversationId: string, body: string): string => {
      const pending = pendingSendByConversationId.current[conversationId];
      if (pending?.body === body) return pending.key;
      const key = crypto.randomUUID();
      pendingSendByConversationId.current[conversationId] = { body, key };
      return key;
    },
    []
  );

  const acknowledgeClientMessage = useCallback(
    (conversationId: string, key: string) => {
      if (pendingSendByConversationId.current[conversationId]?.key === key) {
        delete pendingSendByConversationId.current[conversationId];
      }
    },
    []
  );

  const replaceMessages = useCallback(
    (conversationId: string, messages: DirectMessageEnvelope[]) => {
      setMessagesByConversationId((current) => ({
        ...current,
        [conversationId]: messages,
      }));
    },
    []
  );

  const appendServerMessage = useCallback(
    (conversationId: string, message: DirectMessageEnvelope) => {
      setMessagesByConversationId((current) => {
        const existing = current[conversationId] ?? [];
        // Idempotent replay returns the original message: never render a
        // duplicate when the server-returned id is already cached.
        if (existing.some((item) => item.message_id === message.message_id)) {
          return current;
        }
        return { ...current, [conversationId]: [...existing, message] };
      });
    },
    []
  );

  const markTranscriptLoaded = useCallback((conversationId: string) => {
    setLoadedByConversationId((current) => ({
      ...current,
      [conversationId]: true,
    }));
  }, []);

  /**
   * Load the caller-local read projection and cache it.
   *
   * Every surface that shows an unread count reads this one cached
   * projection.  The Inbox uses the returned rows for its own list; the
   * launcher and the floating window read the cached copy.
   */
  const refreshUnreadProjection = useCallback(async (): Promise<
    DirectMessageConversation[]
  > => {
    const rows = await fetchDirectMessageConversations();
    rows.forEach((row) => cacheConversationMeta(row));
    return rows;
  }, [cacheConversationMeta]);

  /**
   * Load the read projection at most once for this state owner.
   *
   * A failed load is not recorded as done, so a later surface may retry it.
   */
  const projectionRequested = useRef(false);
  const ensureUnreadProjection = useCallback(async (): Promise<void> => {
    if (projectionRequested.current) return;
    projectionRequested.current = true;
    try {
      await refreshUnreadProjection();
    } catch {
      projectionRequested.current = false;
    }
  }, [refreshUnreadProjection]);

  /**
   * The read watermark this session has already recorded, per Conversation.
   *
   * This is an idempotency guard, NOT an authority: the server cursor is the
   * authority, and it only ever moves forward.  The guard exists so that two
   * presentation surfaces holding one Conversation (the Inbox and the floating
   * window) post one watermark once, and so a surface that re-renders does not
   * re-post a watermark it already recorded.  A failed read is never recorded
   * here, so it stays retryable.
   */
  const recordedReadWatermarks = useRef<Map<string, string>>(new Map());

  /**
   * In-flight read attempts, keyed by Conversation and watermark.
   *
   * Two surfaces can hold one Conversation at once; without this they would
   * post the same watermark twice.
   */
  const inFlightReadAttempts = useRef<Map<string, Promise<boolean>>>(new Map());

  /**
   * Mark one Conversation read for the caller, and advance the caller's own
   * recipient-local cursor to the supplied read watermark.
   *
   * This lives in the People state owner so that **every** presentation
   * surface advances the cursor through one shared path: the Inbox, the
   * launcher, and the floating window.  The mutation is the reader's own
   * explicit action, it advances only the caller's cursor, and the peer can
   * never observe it — it is not a read receipt.
   *
   * The watermark is the last message the caller actually saw.  The cursor
   * advances to exactly that message and never past it, so a message that
   * arrived after the transcript was fetched is not marked read without ever
   * having been shown.
   *
   * Resolves to whether the read is recorded.  A failed read stays
   * *retryable*: the watermark is remembered only once the mutation has
   * actually succeeded, so the next open retries it.
   */
  const markConversationRead = useCallback(
    async (
      conversationId: string,
      watermarkMessageId: string | null,
    ): Promise<boolean> => {
      if (
        watermarkMessageId !== null &&
        recordedReadWatermarks.current.get(conversationId) === watermarkMessageId
      ) {
        // Already recorded in this session.  The server cursor only moves
        // forward, so re-posting the same watermark cannot change anything.
        return true;
      }

      const attemptKey = `${conversationId}:${watermarkMessageId ?? "<none>"}`;
      const inFlight = inFlightReadAttempts.current.get(attemptKey);
      if (inFlight) return inFlight;

      const attempt = (async () => {
        try {
          const conversation = await markDirectMessageConversationRead(
            conversationId,
            watermarkMessageId,
          );
          if (watermarkMessageId !== null) {
            recordedReadWatermarks.current.set(conversationId, watermarkMessageId);
          }
          cacheConversationMeta(conversation);
          return true;
        } catch {
          // A failed read must never break the visible surface, and must never
          // be mistaken for a recorded read.
          return false;
        } finally {
          inFlightReadAttempts.current.delete(attemptKey);
        }
      })();

      inFlightReadAttempts.current.set(attemptKey, attempt);
      return attempt;
    },
    [cacheConversationMeta],
  );

  /**
   * The caller's total unread count, derived from the cached read
   * projection.  Every surface renders from this one derived value.
   */
  const unreadTotal = useMemo(
    () =>
      Object.values(conversationMetaById).reduce(
        (total, conversation) =>
          total + Math.max(0, Number(conversation.unread_count ?? 0) || 0),
        0,
      ),
    [conversationMetaById],
  );

  return useMemo(
    () => ({
      peopleOpen,
      activeTab,
      selectedRelationshipId,
      selectedConversationId,
      floatingConversationId,
      floatingMode,
      draftsByConversationId,
      messagesByConversationId,
      loadedByConversationId,
      conversationMetaById,
      unreadTotal,
      openPeople,
      closePeople,
      setTab,
      openRelationship,
      openConversation,
      closeConversation,
      popOutConversation,
      minimizeFloating,
      restoreFloating,
      closeFloating,
      returnFloatingToPeople,
      setDraft,
      getClientMessageKey,
      acknowledgeClientMessage,
      cacheConversationMeta,
      replaceMessages,
      appendServerMessage,
      markTranscriptLoaded,
      refreshUnreadProjection,
      ensureUnreadProjection,
      markConversationRead,
    }),
    [
      peopleOpen,
      activeTab,
      selectedRelationshipId,
      selectedConversationId,
      floatingConversationId,
      floatingMode,
      draftsByConversationId,
      messagesByConversationId,
      loadedByConversationId,
      conversationMetaById,
      unreadTotal,
      openPeople,
      closePeople,
      setTab,
      openRelationship,
      openConversation,
      closeConversation,
      popOutConversation,
      minimizeFloating,
      restoreFloating,
      closeFloating,
      returnFloatingToPeople,
      setDraft,
      getClientMessageKey,
      acknowledgeClientMessage,
      cacheConversationMeta,
      replaceMessages,
      appendServerMessage,
      markTranscriptLoaded,
      refreshUnreadProjection,
      ensureUnreadProjection,
      markConversationRead,
    ]
  );
}
