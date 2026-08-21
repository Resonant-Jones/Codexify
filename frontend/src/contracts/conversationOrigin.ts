/**
 * Frontend mirror of the bounded canonical conversation-origin API domain.
 *
 * Conversation origin is immutable lineage owned by
 * guardian/conversation_origin.py. This read/query-only frontend mirror
 * validates received DTO values and supplies only exact API tokens; it never
 * assigns or infers origin from metadata, providers, or models.
 */
export const CONVERSATION_ORIGIN_SYSTEMS = [
  "codexify",
  "openai",
  "anthropic",
] as const;

export type ConversationOriginSystem =
  (typeof CONVERSATION_ORIGIN_SYSTEMS)[number];

const CANONICAL_ORIGIN_SYSTEMS = new Set<string>(CONVERSATION_ORIGIN_SYSTEMS);

/** Return an exact canonical origin token, or fail closed for an unknown DTO value. */
export function parseConversationOriginSystem(
  value: unknown
): ConversationOriginSystem | null {
  if (typeof value !== "string" || !CANONICAL_ORIGIN_SYSTEMS.has(value)) {
    return null;
  }
  return value as ConversationOriginSystem;
}
