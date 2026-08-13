import api from "@/lib/api";

import type {
  HostedRoomDetail,
  HostedRoomMessage,
} from "@/features/rooms/types";

function hostedRoomPath(roomId: string, suffix = ""): string {
  return `/api/hosted-rooms/${encodeURIComponent(roomId)}${suffix}`;
}

export async function fetchHostedRoomDetail(
  roomId: string
): Promise<HostedRoomDetail> {
  const response = await api.get<HostedRoomDetail>(hostedRoomPath(roomId));
  return response.data;
}

export async function fetchHostedRoomMessages(
  roomId: string
): Promise<HostedRoomMessage[]> {
  const response = await api.get<HostedRoomMessage[]>(
    hostedRoomPath(roomId, "/messages")
  );
  return response.data;
}

export async function postHostedRoomHumanMessage(
  roomId: string,
  content: string
): Promise<HostedRoomMessage> {
  const response = await api.post<HostedRoomMessage>(
    hostedRoomPath(roomId, "/messages"),
    { content }
  );
  return response.data;
}

export function isHostedRoomUnavailableError(error: unknown): boolean {
  const status = Number(
    (error as { response?: { status?: unknown } } | null)?.response?.status ?? 0
  );
  return status === 403 || status === 404 || status === 405 || status === 501;
}
