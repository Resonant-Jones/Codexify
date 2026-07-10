import { describe, it, expect } from "vitest";
import { normalizeDocumentCollaborationEvent } from "../collaborationEvents";

describe("normalizeDocumentCollaborationEvent", () => {
  // ── Content updates ──────────────────────────────────────────────────────

  it("normalizes a direct content update to content.update", () => {
    const input = { type: "update", content: "Direct content", user_id: "user2" };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("content.update");
    if (event.kind !== "content.update") return;
    expect(event.content).toBe("Direct content");
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("normalizes a payload content update to content.update", () => {
    const input = {
      type: "update",
      payload: { content: "Remote change" },
      user_id: "user2",
    };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("content.update");
    if (event.kind !== "content.update") return;
    expect(event.content).toBe("Remote change");
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("normalizes a payload content update without a user_id", () => {
    const input = { type: "update", payload: { content: "no author" } };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("content.update");
    if (event.kind !== "content.update") return;
    expect(event.content).toBe("no author");
    expect(event.userId).toBeUndefined();
  });

  // ── Presence ─────────────────────────────────────────────────────────────

  it("normalizes direct presence.join with active user IDs", () => {
    const input = {
      type: "presence.join",
      user_id: "user2",
      active_users: ["user1", "user2"],
    };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("presence.join");
    if (event.kind !== "presence.join") return;
    expect(event.activeUserIds).toEqual(["user1", "user2"]);
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("normalizes direct presence.leave with active user IDs", () => {
    const input = {
      type: "presence.leave",
      user_id: "user2",
      active_users: ["user1"],
    };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("presence.leave");
    if (event.kind !== "presence.leave") return;
    expect(event.activeUserIds).toEqual(["user1"]);
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  // ── Typing (direct) ──────────────────────────────────────────────────────

  it("normalizes direct typing.start", () => {
    const input = { type: "typing.start", user_id: "user2" };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("typing.start");
    if (event.kind !== "typing.start") return;
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("normalizes direct typing.stop", () => {
    const input = { type: "typing.stop", user_id: "user2" };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("typing.stop");
    if (event.kind !== "typing.stop") return;
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  // ── Typing (wrapped envelope) ────────────────────────────────────────────

  it("normalizes wrapped typing.start as typing.start", () => {
    const input = {
      type: "update",
      payload: { type: "typing.start", user_id: "user2" },
      user_id: "user2",
    };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("typing.start");
    if (event.kind !== "typing.start") return;
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("normalizes wrapped typing.stop as typing.stop", () => {
    const input = {
      type: "update",
      payload: { type: "typing.stop", user_id: "user2" },
      user_id: "user2",
    };
    const event = normalizeDocumentCollaborationEvent(input);

    expect(event.kind).toBe("typing.stop");
    if (event.kind !== "typing.stop") return;
    expect(event.userId).toBe("user2");
    expect(event.raw).toBe(input);
  });

  it("does not normalize wrapped typing as a content update", () => {
    const event = normalizeDocumentCollaborationEvent({
      type: "update",
      payload: { type: "typing.start", user_id: "user2" },
      user_id: "user2",
    });

    expect(event.kind).not.toBe("content.update");
    expect(event.kind).toBe("typing.start");
  });

  // ── Malformed / unknown shapes ───────────────────────────────────────────

  it("normalizes malformed messages to unknown", () => {
    expect(normalizeDocumentCollaborationEvent(null).kind).toBe("unknown");
    expect(normalizeDocumentCollaborationEvent(undefined).kind).toBe("unknown");
    expect(normalizeDocumentCollaborationEvent(42).kind).toBe("unknown");
    expect(normalizeDocumentCollaborationEvent("update").kind).toBe("unknown");
    expect(normalizeDocumentCollaborationEvent({}).kind).toBe("unknown");
    expect(
      normalizeDocumentCollaborationEvent({ type: "bogus" }).kind
    ).toBe("unknown");
  });

  it("normalizes a message without a recognizable type to unknown", () => {
    const input = { type: "typing.indeterminate", user_id: "user2" };
    const event = normalizeDocumentCollaborationEvent(input);
    expect(event.kind).toBe("unknown");
  });

  it("normalizes direct typing without user_id to unknown", () => {
    const input = { type: "typing.start" };
    const event = normalizeDocumentCollaborationEvent(input);
    expect(event.kind).toBe("unknown");
  });

  it("normalizes wrapped typing without user_id to unknown", () => {
    const input = { type: "update", payload: { type: "typing.start" } };
    const event = normalizeDocumentCollaborationEvent(input);
    expect(event.kind).toBe("unknown");
  });

  it("does not mutate the input object", () => {
    const input = {
      type: "update",
      payload: { type: "typing.start", user_id: "user2" },
      user_id: "user2",
    };
    const snapshot = JSON.parse(JSON.stringify(input));

    normalizeDocumentCollaborationEvent(input);

    expect(input).toEqual(snapshot);
  });
});
