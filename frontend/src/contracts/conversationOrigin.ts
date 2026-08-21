/**
 * Frontend mirror of the bounded canonical conversation-origin API domain.
 *
 * Conversation origin is immutable lineage owned by the backend. This module
 * validates received DTO values and supplies only the exact API tokens; it
 * never infers origin from metadata, providers, or models.
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
