/**
 * Server-authoritative transcript loading for one Conversation.
 *
 * The backend pages ascending with a `before_id` cursor; this walks pages
 * (bounded) so the newest durable messages are present, and keeps the
 * cache in the People state owner so the floating window and the modal
 * never hold conflicting copies.
 *
 * Reopening a conversation **refreshes** it.  The cache is a rendering
 * convenience, not a guarantee: a message that arrived while the recipient
 * was elsewhere must appear in the transcript before it can be marked read,
 * and the read watermark is the last message actually shown.  The People
 * modal and the floating window can hold the same conversation at once, so
 * concurrent activations share one in-flight fetch rather than issuing two.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchDirectMessageMessages } from "@/lib/direct-messages";
import type { DirectMessageEnvelope } from "@/lib/direct-messages";

const MAX_PAGES = 10;
const PAGE_SIZE = 200;

/**
 * In-flight transcript fetches, keyed by conversation id.
 *
 * The People modal and the floating window can both hold one conversation;
 * without this they would each page the whole transcript.  A shared promise
 * keeps one fetch per conversation, and it outlives any single consumer so
 * one view unmounting cannot cancel the other view's fetch.
 */
const inFlightTranscripts = new Map<string, Promise<DirectMessageEnvelope[]>>();

async function loadTranscript(
  conversationId: string,
): Promise<DirectMessageEnvelope[]> {
  const collected: DirectMessageEnvelope[] = [];
  let beforeId: string | null = null;
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const pageMessages = await fetchDirectMessageMessages(conversationId, {
      limit: PAGE_SIZE,
      beforeId,
    });
    if (pageMessages.length === 0) break;
    // Pages arrive ascending; prepend older pages before newer ones.
    collected.unshift(...pageMessages);
    if (pageMessages.length < PAGE_SIZE) break;
    beforeId = pageMessages[0].message_id;
  }
  return collected;
}

function fetchTranscriptOnce(
  conversationId: string,
): Promise<DirectMessageEnvelope[]> {
  const existing = inFlightTranscripts.get(conversationId);
  if (existing) return existing;
  const pending = loadTranscript(conversationId).finally(() => {
    if (inFlightTranscripts.get(conversationId) === pending) {
      inFlightTranscripts.delete(conversationId);
    }
  });
  inFlightTranscripts.set(conversationId, pending);
  return pending;
}

export type TranscriptState = {
  messages: DirectMessageEnvelope[];
  loading: boolean;
  error: string | null;
  reload: () => void;
};

export function useDirectMessageTranscript(
  conversationId: string,
  cachedMessages: DirectMessageEnvelope[],
  loaded: boolean,
  replaceMessages: (conversationId: string, messages: DirectMessageEnvelope[]) => void,
  markTranscriptLoaded: (conversationId: string) => void
): TranscriptState {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);

  /**
   * Which (conversation, reload) this consumer has already attempted.
   *
   * The effect re-runs whenever the shared cache changes, so without this a
   * completed load would immediately trigger another one.  A fresh consumer
   * (a reopen) starts with an empty ref and therefore refreshes.
   */
  const attempted = useRef<string | null>(null);

  useEffect(() => {
    // The floating window mounts this hook even with no conversation.
    if (!conversationId) return;

    const attemptKey = `${conversationId}:${reloadToken}`;
    if (attempted.current === attemptKey) return;
    attempted.current = attemptKey;

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const collected = await fetchTranscriptOnce(conversationId);
        // The shared cache is written even if this consumer unmounted: the
        // state owner outlives it, and a sibling consumer may still be
        // waiting on the same fetch.
        replaceMessages(conversationId, collected);
        markTranscriptLoaded(conversationId);
      } catch (loadError) {
        // A failed refresh leaves the previously cached transcript in place
        // and never marks unseen messages read.
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load messages"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [conversationId, loaded, reloadToken, replaceMessages, markTranscriptLoaded]);

  return { messages: cachedMessages, loading, error, reload };
}
