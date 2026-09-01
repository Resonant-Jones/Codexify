/**
 * Server-authoritative transcript loading for one Conversation.
 *
 * The backend pages ascending with a `before_id` cursor; this walks pages
 * (bounded) so the newest durable messages are present, and keeps the
 * cache in the People state owner so the floating window and the modal
 * never hold conflicting copies.
 */
import { useCallback, useEffect, useState } from "react";

import { fetchDirectMessageMessages } from "@/lib/direct-messages";
import type { DirectMessageEnvelope } from "@/lib/direct-messages";

const MAX_PAGES = 10;
const PAGE_SIZE = 200;

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

  useEffect(() => {
    if (loaded) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const collected: DirectMessageEnvelope[] = [];
        let beforeId: string | null = null;
        for (let page = 0; page < MAX_PAGES; page += 1) {
          const pageMessages = await fetchDirectMessageMessages(conversationId, {
            limit: PAGE_SIZE,
            beforeId,
          });
          if (cancelled) return;
          if (pageMessages.length === 0) break;
          // Pages arrive ascending; prepend older pages before newer ones.
          collected.unshift(...pageMessages);
          if (pageMessages.length < PAGE_SIZE) break;
          beforeId = pageMessages[0].message_id;
        }
        if (!cancelled) {
          replaceMessages(conversationId, collected);
          markTranscriptLoaded(conversationId);
        }
      } catch (loadError) {
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
  }, [
    conversationId,
    loaded,
    reloadToken,
    replaceMessages,
    markTranscriptLoaded,
  ]);

  return { messages: cachedMessages, loading, error, reload };
}
