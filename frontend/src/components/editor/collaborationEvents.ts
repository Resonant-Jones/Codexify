/**
 * Document collaboration event normalizer.
 *
 * Translates raw WebSocket messages from the `/api/collab/ws/{documentId}`
 * channel into a single, exhaustive discriminated union so the
 * `useDocumentCollaboration` hook never needs to re-implement direct-vs-wrapped
 * envelope parsing inline.
 *
 * The backend `ws_collab` handler is known to wrap some non-`update` messages
 * (notably typing) inside an `{ type: "update", payload: ... }` envelope. This
 * normalizer treats wrapped typing events as typing, never as content updates.
 *
 * Contract:
 *  - Pure: does not mutate its input, does not import React, and performs no
 *    I/O, scheduling, or state mutation.
 *  - Total: any input shape is mapped to exactly one union member; malformed
 *    or unrecognized shapes collapse to `{ kind: "unknown", raw }`.
 */

export type NormalizedDocumentCollaborationEvent =
  | {
      kind: "content.update";
      content: string;
      userId?: string;
      raw: unknown;
    }
  | {
      kind: "presence.join";
      activeUserIds: string[];
      userId?: string;
      raw: unknown;
    }
  | {
      kind: "presence.leave";
      activeUserIds: string[];
      userId?: string;
      raw: unknown;
    }
  | {
      kind: "typing.start";
      userId: string;
      raw: unknown;
    }
  | {
      kind: "typing.stop";
      userId: string;
      raw: unknown;
    }
  | {
      kind: "cursor.position";
      userId: string;
      position: number;
      raw: unknown;
    }
  | {
      kind: "unknown";
      raw: unknown;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function isFiniteNonNegativeNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

export function normalizeDocumentCollaborationEvent(
  message: unknown
): NormalizedDocumentCollaborationEvent {
  if (!isRecord(message)) {
    return { kind: "unknown", raw: message };
  }

  const type = typeof message.type === "string" ? message.type : undefined;

  // Wrapped envelope: `{ type: "update", payload: { ... } }`. The backend
  // `ws_collab` handler may re-wrap non-update messages this way. Typing is
  // checked before content so wrapped typing never masquerades as an update.
  if (type === "update" && isRecord(message.payload)) {
    const payload = message.payload;
    const payloadType =
      typeof payload.type === "string" ? payload.type : undefined;

    if (payloadType === "typing.start" || payloadType === "typing.stop") {
      if (typeof payload.user_id === "string") {
        return { kind: payloadType, userId: payload.user_id, raw: message };
      }
      return { kind: "unknown", raw: message };
    }

    if (payloadType === "cursor.position") {
      if (
        typeof payload.user_id === "string" &&
        isFiniteNonNegativeNumber(payload.position)
      ) {
        return {
          kind: "cursor.position",
          userId: payload.user_id,
          position: payload.position,
          raw: message,
        };
      }
      return { kind: "unknown", raw: message };
    }

    if (typeof payload.content === "string") {
      return {
        kind: "content.update",
        content: payload.content,
        userId: optionalString(message.user_id),
        raw: message,
      };
    }
  }

  // Direct update without a payload wrapper: `{ type: "update", content, user_id }`.
  if (type === "update") {
    if (typeof message.content === "string") {
      return {
        kind: "content.update",
        content: message.content,
        userId: optionalString(message.user_id),
        raw: message,
      };
    }
  }

  // Presence: join/leave carry the authoritative active-user list.
  if (type === "presence.join" || type === "presence.leave") {
    if (isStringArray(message.active_users)) {
      return {
        kind: type,
        activeUserIds: message.active_users,
        userId: optionalString(message.user_id),
        raw: message,
      };
    }
  }

  // Direct (unwrapped) typing events.
  if (type === "typing.start" || type === "typing.stop") {
    if (typeof message.user_id === "string") {
      return { kind: type, userId: message.user_id, raw: message };
    }
    return { kind: "unknown", raw: message };
  }

  // Direct (unwrapped) cursor events.
  if (type === "cursor.position") {
    if (
      typeof message.user_id === "string" &&
      isFiniteNonNegativeNumber(message.position)
    ) {
      return {
        kind: "cursor.position",
        userId: message.user_id,
        position: message.position,
        raw: message,
      };
    }
    return { kind: "unknown", raw: message };
  }

  return { kind: "unknown", raw: message };
}
