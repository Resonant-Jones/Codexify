// src/guardian/threadHelpers.ts
import { Dispatch, SetStateAction } from "react";

export type Participant = { id: string; name: string };
export type Thread = {
  id: string;
  title: string;
  lastMessage: string;
  unread: number;
  participants: Participant[];
  messages: any[];
};

/**
 * Pure factory that returns a new Thread object.
 * This is useful if callers want to create the thread object and
 * manipulate or inspect it before inserting into state.
 */
export function makeNewThread(userName: string, guardianName: string): Thread {
  const id = `t_${Date.now()}`;
  return {
    id,
    title: "New Chat",
    lastMessage: "",
    unread: 0,
    participants: [
      { id: "me", name: userName },
      { id: "bot", name: guardianName },
    ],
    messages: [],
  };
}

/**
 * Convenience helper that inserts a new thread into React state and sets it active.
 * Keeps backward-compatibility with previous createNewThread(setThreads, setActiveId, userName, guardianName)
 */
export function createNewThread(
  setThreads: Dispatch<SetStateAction<Thread[]>>,
  setActiveId: (id: string) => void,
  userName: string,
  guardianName: string
) {
  const thread = makeNewThread(userName, guardianName);
  setThreads((prev) => [thread, ...prev]);
  setActiveId(thread.id);
}
