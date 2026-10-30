/**
 * conversationNavigation - pure projection of the loaded transcript into
 * navigable conversation sections.
 *
 * This module deliberately has no React or DOM dependency so the grouping
 * rules can be exercised without a renderer.
 *
 * Boundary rules encoded here:
 * - The projection only covers messages that are already loaded and supplied
 *   to the transcript. It never implies server-side history that was not
 *   supplied.
 * - Sections are anchored to stable message identity. Array positions are
 *   never used as durable navigation identity.
 * - A section groups the rendered message order. It does not assert
 *   request-attempt linkage or completion status (see ADR-003).
 * - Tool events, hidden context, and streaming drafts are not navigable
 *   destinations.
 */
import type { ChatAttachment, ChatMessage } from "@/features/chat/useChat";
import { parseDocumentContextContent } from "@/lib/documentContext";

/** Maximum length of a section preview, in characters. */
export const CONVERSATION_SECTION_PREVIEW_LIMIT = 180;

export type ConversationSectionRole = "user" | "assistant";

export type ConversationSection = {
  /** Stable identity for the section. Derived from message identity. */
  id: string;
  /** Stable message identity of the anchor this section navigates to. */
  anchorMessageId: string;
  /** Role of the message that opened the section. */
  anchorRole: ConversationSectionRole;
  /** Display-safe plain-text preview of the anchored message. */
  preview: string;
  /** Display-safe attachment labels attached to the anchored message. */
  attachmentLabels: string[];
  /**
   * Display-safe plain-text preview of the assistant message that followed the
   * anchor, when the loaded window contains one. This is a rendered-order
   * observation only; it carries no completion or attempt semantics.
   */
  replyPreview: string | null;
  /** Number of loaded messages projected into this section. */
  messageCount: number;
};

export type ConversationNavigationEntryKind = "section" | "range";

export type ConversationNavigationEntry = {
  /** Stable identity for the rail entry. */
  id: string;
  kind: ConversationNavigationEntryKind;
  /** Section identities reachable from this entry, in chronological order. */
  sectionIds: string[];
  /** Index of the first section covered by this entry. */
  startIndex: number;
  /** Index of the last section covered by this entry. */
  endIndex: number;
  /** Human readable label for the entry. */
  label: string;
};

function normalizeRole(role: unknown): ConversationSectionRole | null {
  const normalized = String(role ?? "").trim().toLowerCase();
  if (normalized === "user") return "user";
  if (normalized === "assistant") return "assistant";
  return null;
}

function normalizeMessageId(message: ChatMessage): string {
  const raw = message?.id;
  if (typeof raw === "number" && Number.isFinite(raw)) return String(raw);
  const text = String(raw ?? "").trim();
  return text;
}

/**
 * Build a display-safe plain-text preview for a message body.
 *
 * Document-context markers are stripped through the shared parser so hidden
 * context payloads never leak into the preview. Only plain text survives.
 */
export function buildConversationPreviewText(
  content: unknown,
  limit: number = CONVERSATION_SECTION_PREVIEW_LIMIT
): string {
  const raw = typeof content === "string" ? content : "";
  const { text } = parseDocumentContextContent(raw);
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  const cut = Math.max(0, limit - 1);
  return `${normalized.slice(0, cut).trimEnd()}…`;
}

/**
 * Collect display-safe attachment labels. Only labels are surfaced; no image
 * source, remote reference, or executable content is carried forward.
 */
export function collectConversationAttachmentLabels(
  attachments: ChatAttachment[] | undefined
): string[] {
  if (!Array.isArray(attachments)) return [];
  const labels: string[] = [];
  for (const attachment of attachments) {
    const filename = String(attachment?.filename ?? "").trim();
    if (filename) {
      labels.push(filename);
      continue;
    }
    const kind = String(attachment?.kind ?? "").trim();
    if (kind) labels.push(kind);
  }
  return labels;
}

function buildSectionIdentity(
  anchorMessageId: string,
  used: Set<string>
): string {
  const base = anchorMessageId
    ? `conversation-section-${anchorMessageId}`
    : "conversation-section-unidentified";
  if (!used.has(base)) {
    used.add(base);
    return base;
  }
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) suffix += 1;
  const identity = `${base}-${suffix}`;
  used.add(identity);
  return identity;
}

/**
 * Project the rendered message order into navigable sections.
 *
 * A user-authored message opens a section. Assistant messages that follow are
 * projected into the open section. When the loaded window begins with an
 * assistant message, that message opens its own section rather than inventing
 * a missing user turn. Messages that are neither user nor assistant authored
 * (tool events and other non-user turns) never become destinations.
 */
export function deriveConversationSections(
  messages: ChatMessage[]
): ConversationSection[] {
  if (!Array.isArray(messages) || messages.length === 0) return [];

  const sections: ConversationSection[] = [];
  const usedIdentities = new Set<string>();
  let openSection: ConversationSection | null = null;

  for (const message of messages) {
    if (!message) continue;
    const role = normalizeRole(message.role);
    if (role === null) continue;

    if (role === "user") {
      const anchorMessageId = normalizeMessageId(message);
      const identity = buildSectionIdentity(anchorMessageId, usedIdentities);
      openSection = {
        id: identity,
        anchorMessageId,
        anchorRole: "user",
        preview: buildConversationPreviewText(message.content),
        attachmentLabels: collectConversationAttachmentLabels(message.attachments),
        replyPreview: null,
        messageCount: 1,
      };
      sections.push(openSection);
      continue;
    }

    if (openSection === null) {
      // The loaded window starts with an assistant message. Anchor the section
      // on that message instead of inventing a missing user turn.
      const anchorMessageId = normalizeMessageId(message);
      const identity = buildSectionIdentity(anchorMessageId, usedIdentities);
      openSection = {
        id: identity,
        anchorMessageId,
        anchorRole: "assistant",
        preview: buildConversationPreviewText(message.content),
        attachmentLabels: collectConversationAttachmentLabels(message.attachments),
        replyPreview: null,
        messageCount: 1,
      };
      sections.push(openSection);
      continue;
    }

    openSection.messageCount += 1;
    if (openSection.replyPreview === null) {
      const replyPreview = buildConversationPreviewText(message.content);
      if (replyPreview) openSection.replyPreview = replyPreview;
    }
  }

  return sections;
}

/**
 * Coalesce sections into rail entries that fit the available rail height.
 *
 * A dense history must not become hundreds of overlapping interactive targets.
 * When the section count exceeds the available marks, contiguous sections are
 * grouped into a range. The range still exposes every exact destination so no
 * loaded section becomes unreachable.
 */
export function buildConversationNavigationEntries(
  sections: ConversationSection[],
  maxMarks: number
): ConversationNavigationEntry[] {
  if (!Array.isArray(sections) || sections.length === 0) return [];

  const limit = Math.max(1, Math.floor(Number(maxMarks) || 0) || 1);

  if (sections.length <= limit) {
    return sections.map((section, index) => ({
      id: `conversation-nav-${section.id}`,
      kind: "section" as const,
      sectionIds: [section.id],
      startIndex: index,
      endIndex: index,
      label: `Turn ${index + 1}`,
    }));
  }

  // The mark budget bounds the number of independent rail entries, not the
  // size of each range. Use the full budget so every range stays as small as
  // the budget allows and no two hit areas overlap.
  const groupCount = limit;
  const groupSize = Math.ceil(sections.length / groupCount);
  const entries: ConversationNavigationEntry[] = [];

  for (let start = 0; start < sections.length; start += groupSize) {
    const chunk = sections.slice(start, start + groupSize);
    if (chunk.length === 0) continue;
    const isSingle = chunk.length === 1;
    entries.push({
      id: `conversation-nav-range-${chunk[0].id}`,
      kind: isSingle ? "section" : "range",
      sectionIds: chunk.map((section) => section.id),
      startIndex: start,
      endIndex: start + chunk.length - 1,
      label: isSingle
        ? `Turn ${start + 1}`
        : `Turns ${start + 1}–${start + chunk.length}`,
    });
  }

  return entries;
}

/**
 * Resolve the destination sections covered by a rail entry.
 */
export function resolveConversationEntrySections(
  entry: ConversationNavigationEntry,
  sectionsById: Map<string, ConversationSection>
): ConversationSection[] {
  const resolved: ConversationSection[] = [];
  for (const sectionId of entry.sectionIds) {
    const section = sectionsById.get(sectionId);
    if (section) resolved.push(section);
  }
  return resolved;
}
