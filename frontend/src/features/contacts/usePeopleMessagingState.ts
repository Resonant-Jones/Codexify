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
      setConversationMetaById((current) => ({
        ...current,
        [conversation.conversation_id]: conversation,
      }));
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
    ]
  );
}
