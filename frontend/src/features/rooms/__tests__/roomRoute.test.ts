import { describe, expect, it } from "vitest";

import {
  buildHostedRoomPath,
  parseHostedRoomRoute,
} from "@/features/rooms/roomRoute";

describe("Hosted Room route", () => {
  it("parses a direct Room route", () => {
    expect(parseHostedRoomRoute("/rooms/room-owner-1")).toEqual({
      roomId: "room-owner-1",
    });
  });

  it("round-trips an opaque Room ID without treating it as a thread ID", () => {
    const roomId = "Room owner:alpha+beta";
    const path = buildHostedRoomPath(roomId);

    expect(path).toBe("/rooms/Room%20owner%3Aalpha%2Bbeta");
    expect(parseHostedRoomRoute(path)).toEqual({ roomId });
  });

  it.each([
    "/rooms",
    "/rooms/",
    "/rooms/room-1/messages",
    "/rooms/%E0%A4%A",
  ])("rejects malformed or empty Room paths: %s", (pathname) => {
    expect(parseHostedRoomRoute(pathname)).toBeNull();
  });

  it("rejects empty Room IDs when building paths", () => {
    expect(() => buildHostedRoomPath("   ")).toThrow(/non-empty opaque string/i);
  });
});
