export type HostedRoomRoute = {
  roomId: string;
};

function isUsableRoomId(roomId: string): boolean {
  return roomId.length > 0 && roomId.trim().length > 0;
}

export function parseHostedRoomRoute(pathname: string): HostedRoomRoute | null {
  const match = pathname.match(/^\/rooms\/([^/]+)\/?$/);
  if (!match) return null;

  try {
    const roomId = decodeURIComponent(match[1]);
    return isUsableRoomId(roomId) ? { roomId } : null;
  } catch {
    return null;
  }
}

export function buildHostedRoomPath(roomId: string): string {
  if (!isUsableRoomId(roomId)) {
    throw new Error("Room ID must be a non-empty opaque string");
  }
  return `/rooms/${encodeURIComponent(roomId)}`;
}
