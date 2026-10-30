import { describe, expect, it } from "vitest";

import {
  buildConversationNavigationEntries,
  buildConversationPreviewText,
  collectConversationAttachmentLabels,
  deriveConversationSections,
  resolveConversationEntrySections,
  type ConversationSection,
} from "@/features/chat/conversationNavigation";
import type { ChatMessage } from "@/features/chat/useChat";

function buildMessage(
  id: number,
  role: string,
  overrides: Partial<ChatMessage> = {}
): ChatMessage {
  return {
    id,
    thread_id: 7,
    role,
    content: `message ${id}`,
    created_at: `2026-03-13T00:00:${String(id % 60).padStart(2, "0")}.000Z`,
    ...overrides,
  };
}

describe("conversationNavigation section derivation", () => {
  it("anchors each user-authored section to stable message identity", () => {
    const sections = deriveConversationSections([
      buildMessage(11, "user", { content: "first question" }),
      buildMessage(12, "assistant", { content: "first answer" }),
      buildMessage(21, "user", { content: "second question" }),
      buildMessage(22, "assistant", { content: "second answer" }),
    ]);

    expect(sections).toHaveLength(2);
    expect(sections[0].anchorMessageId).toBe("11");
    expect(sections[0].anchorRole).toBe("user");
    expect(sections[1].anchorMessageId).toBe("21");
    expect(sections[0].id).not.toBe(sections[1].id);
  });

  it("does not use array indexes as durable navigation identity", () => {
    const messages = [
      buildMessage(11, "user"),
      buildMessage(12, "assistant"),
      buildMessage(13, "user"),
    ];

    const before = deriveConversationSections(messages);
    // Prepending older history must not renumber the existing sections.
    const after = deriveConversationSections([
      buildMessage(9, "user"),
      ...messages,
    ]);

    expect(after[1].id).toBe(before[0].id);
    expect(after[2].id).toBe(before[1].id);
    expect(after[1].anchorMessageId).toBe("11");
  });

  it("keeps consecutive user messages as separate sections", () => {
    const sections = deriveConversationSections([
      buildMessage(1, "user", { content: "one" }),
      buildMessage(2, "user", { content: "two" }),
    ]);

    expect(sections).toHaveLength(2);
    expect(sections[0].preview).toBe("one");
    expect(sections[1].preview).toBe("two");
    expect(sections[0].replyPreview).toBeNull();
    expect(sections[1].replyPreview).toBeNull();
  });

  it("projects a following assistant message into the open section", () => {
    const sections = deriveConversationSections([
      buildMessage(1, "user", { content: "question" }),
      buildMessage(2, "assistant", { content: "answer" }),
    ]);

    expect(sections).toHaveLength(1);
    expect(sections[0].replyPreview).toBe("answer");
    expect(sections[0].messageCount).toBe(2);
  });

  it("anchors a loaded window that begins with an assistant message without inventing a user turn", () => {
    const sections = deriveConversationSections([
      buildMessage(31, "assistant", { content: "earlier answer" }),
      buildMessage(32, "user", { content: "later question" }),
    ]);

    expect(sections).toHaveLength(2);
    expect(sections[0].anchorRole).toBe("assistant");
    expect(sections[0].anchorMessageId).toBe("31");
    expect(sections[0].replyPreview).toBeNull();
    expect(sections[1].anchorRole).toBe("user");
    expect(sections[1].anchorMessageId).toBe("32");
  });

  it("does not create sections for tool events or other non-user turns", () => {
    const sections = deriveConversationSections([
      buildMessage(1, "user", { content: "question" }),
      buildMessage(2, "tool", { content: "tool output" }),
      buildMessage(3, "system", { content: "system notice" }),
    ]);

    expect(sections).toHaveLength(1);
    expect(sections[0].preview).toBe("question");
    expect(sections[0].replyPreview).toBeNull();
    expect(sections[0].messageCount).toBe(1);
  });

  it("returns no sections for an empty transcript", () => {
    expect(deriveConversationSections([])).toEqual([]);
  });
});

describe("conversationNavigation preview text", () => {
  it("uses display-safe text and strips hidden document context", () => {
    const content = [
      "<!-- cfy-doc-tile:eyJpZCI6IjEiLCJ0aXRsZSI6IkRpc2guIn0= -->",
      "Visible question text",
      "<!-- cfy-doc-content:start:eyJpZCI6IjEifQ== -->",
      "hidden document body",
      "<!-- cfy-doc-content:end:eyJpZCI6IjEifQ== -->",
    ].join("\n");

    const preview = buildConversationPreviewText(content);

    expect(preview).toContain("Visible question text");
    expect(preview).not.toContain("hidden document body");
    expect(preview).not.toContain("cfy-doc-tile");
  });

  it("collapses whitespace and bounds the preview length", () => {
    const preview = buildConversationPreviewText("a\n\n  b   c", 180);
    expect(preview).toBe("a b c");

    const long = buildConversationPreviewText("x".repeat(400));
    expect(long.length).toBeLessThanOrEqual(180);
    expect(long.endsWith("…")).toBe(true);
  });

  it("collects attachment labels only", () => {
    const labels = collectConversationAttachmentLabels([
      { id: "a", kind: "image", src_url: "https://example.test/a.png", filename: "photo.png" },
      { id: "b", kind: "document", src_url: "https://example.test/b.pdf" },
    ]);

    expect(labels).toEqual(["photo.png", "document"]);
    expect(labels.join(" ")).not.toContain("example.test");
  });
});

describe("conversationNavigation density grouping", () => {
  function buildSections(count: number): ConversationSection[] {
    return Array.from({ length: count }, (_unused, index) => ({
      id: `conversation-section-${index + 1}`,
      anchorMessageId: String(index + 1),
      anchorRole: "user" as const,
      preview: `turn ${index + 1}`,
      attachmentLabels: [],
      replyPreview: null,
      messageCount: 1,
    }));
  }

  it("keeps one entry per section when the history fits", () => {
    const sections = buildSections(5);
    const entries = buildConversationNavigationEntries(sections, 20);

    expect(entries).toHaveLength(5);
    expect(entries.every((entry) => entry.kind === "section")).toBe(true);
  });

  it("coalesces a dense history into ranges that never exceed the mark budget", () => {
    const sections = buildSections(240);
    const entries = buildConversationNavigationEntries(sections, 40);

    expect(entries.length).toBeLessThanOrEqual(40);
    expect(entries.length).toBeGreaterThan(1);
    expect(entries.some((entry) => entry.kind === "range")).toBe(true);
  });

  it("keeps every loaded destination reachable and in chronological order", () => {
    const sections = buildSections(240);
    const entries = buildConversationNavigationEntries(sections, 40);

    const reachable = entries.flatMap((entry) => entry.sectionIds);
    expect(reachable).toHaveLength(sections.length);
    expect(new Set(reachable).size).toBe(sections.length);
    expect(reachable).toEqual(sections.map((section) => section.id));
  });

  it("resolves the exact destinations behind a range entry", () => {
    const sections = buildSections(240);
    const entries = buildConversationNavigationEntries(sections, 40);
    const range = entries.find((entry) => entry.kind === "range");
    expect(range).toBeDefined();

    const byId = new Map(sections.map((section) => [section.id, section]));
    const resolved = resolveConversationEntrySections(range!, byId);

    expect(resolved.length).toBe(range!.sectionIds.length);
    expect(resolved[0].id).toBe(range!.sectionIds[0]);
    expect(resolved[resolved.length - 1].id).toBe(
      range!.sectionIds[range!.sectionIds.length - 1]
    );
  });

  it("produces no entries for an empty projection", () => {
    expect(buildConversationNavigationEntries([], 20)).toEqual([]);
  });
});
