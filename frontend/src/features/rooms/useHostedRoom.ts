import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchHostedRoomDetail,
  fetchHostedRoomMessages,
  isHostedRoomUnavailableError,
  postHostedRoomHumanMessage,
} from "@/features/rooms/api";
import type {
  HostedRoomDetail,
  HostedRoomMessage,
} from "@/features/rooms/types";

export type HostedRoomLoadState =
  | "loading"
  | "ready"
  | "unavailable"
  | "error";

export type UseHostedRoomResult = {
  room: HostedRoomDetail | null;
  messages: HostedRoomMessage[];
  loadState: HostedRoomLoadState;
  loadError: string | null;
  postError: string | null;
  isPosting: boolean;
  postHumanMessage: (content: string) => Promise<void>;
  reload: () => Promise<void>;
};

export function useHostedRoom(roomId: string): UseHostedRoomResult {
  const [room, setRoom] = useState<HostedRoomDetail | null>(null);
  const [messages, setMessages] = useState<HostedRoomMessage[]>([]);
  const [loadState, setLoadState] = useState<HostedRoomLoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [postError, setPostError] = useState<string | null>(null);
  const [isPosting, setIsPosting] = useState(false);
  const loadSequenceRef = useRef(0);
  const postingRef = useRef(false);

  const load = useCallback(async () => {
    const loadSequence = ++loadSequenceRef.current;
    setLoadState("loading");
    setLoadError(null);
    setPostError(null);

    try {
      const detail = await fetchHostedRoomDetail(roomId);
      if (loadSequence !== loadSequenceRef.current) return;

      setRoom(detail);
      if (detail.status === "closed") {
        setMessages([]);
        setLoadState("ready");
        return;
      }

      const transcript = await fetchHostedRoomMessages(roomId);
      if (loadSequence !== loadSequenceRef.current) return;
      setMessages(transcript);
      setLoadState("ready");
    } catch (error) {
      if (loadSequence !== loadSequenceRef.current) return;
      setRoom(null);
      setMessages([]);
      if (isHostedRoomUnavailableError(error)) {
        setLoadState("unavailable");
        setLoadError("Room unavailable");
      } else {
        setLoadState("error");
        setLoadError("Room could not be loaded. Try again.");
      }
    }
  }, [roomId]);

  useEffect(() => {
    void load();
    return () => {
      loadSequenceRef.current += 1;
    };
  }, [load]);

  const postHumanMessage = useCallback(
    async (content: string) => {
      const normalizedContent = content.trim();
      if (!normalizedContent) return;
      if (!room || room.status === "closed") {
        throw new Error("This Room is closed.");
      }
      if (postingRef.current) {
        throw new Error("A Room message is already being sent.");
      }

      postingRef.current = true;
      setIsPosting(true);
      setPostError(null);

      try {
        await postHostedRoomHumanMessage(room.id, normalizedContent);
        try {
          const transcript = await fetchHostedRoomMessages(room.id);
          setMessages(transcript);
        } catch {
          setPostError(
            "Message saved, but the transcript could not refresh. Reload the Room."
          );
        }
      } catch {
        setPostError("Message was not sent. Check the connection and try again.");
        throw new Error("Message was not sent. Check the connection and try again.");
      } finally {
        postingRef.current = false;
        setIsPosting(false);
      }
    },
    [room]
  );

  return {
    room,
    messages,
    loadState,
    loadError,
    postError,
    isPosting,
    postHumanMessage,
    reload: load,
  };
}

export default useHostedRoom;
