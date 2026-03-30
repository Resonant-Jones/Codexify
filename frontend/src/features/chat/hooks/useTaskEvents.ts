import { useEffect, useRef } from "react";

import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveApiUrl } from "@/lib/runtimeConfig";

export type TaskStreamEvent = {
  type: string;
  id: string | null;
  [key: string]: unknown;
};

type TaskEventHandler = (event: TaskStreamEvent) => void;

const INITIAL_BACKOFF_MS = 500;
const MAX_BACKOFF_MS = 5000;

function isAbortError(error: unknown): boolean {
  const name = String(
    (error as { name?: unknown } | null | undefined)?.name ?? ""
  ).trim();
  return name === "AbortError";
}

function parseTaskEventChunk(chunk: string): TaskStreamEvent | null {
  if (!chunk.trim() || chunk.startsWith(":")) {
    return null;
  }

  let eventType = "message";
  let eventId: string | null = null;
  const dataLines: string[] = [];

  for (const line of chunk.split("\n")) {
    if (!line || line.startsWith(":")) {
      continue;
    }

    const separatorIndex = line.indexOf(":");
    const field =
      separatorIndex >= 0 ? line.slice(0, separatorIndex) : line.trim();
    const value =
      separatorIndex >= 0 ? line.slice(separatorIndex + 1).trimStart() : "";

    switch (field) {
      case "event":
        if (value) eventType = value;
        break;
      case "id":
        eventId = value || null;
        break;
      case "data":
        dataLines.push(value);
        break;
      default:
        break;
    }
  }

  if (!dataLines.length) {
    return null;
  }

  try {
    const parsed = JSON.parse(dataLines.join("\n"));
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return {
        ...(parsed as Record<string, unknown>),
        type: eventType,
        id: eventId,
      };
    }
    return {
      type: eventType,
      id: eventId,
      value: parsed,
    };
  } catch {
    return null;
  }
}

function drainBuffer(
  buffer: string,
  onEvent: (event: TaskStreamEvent) => void
): string {
  let working = buffer.replace(/\r\n?/g, "\n");
  let separatorIndex = working.indexOf("\n\n");

  while (separatorIndex !== -1) {
    const chunk = working.slice(0, separatorIndex);
    working = working.slice(separatorIndex + 2);
    const parsed = parseTaskEventChunk(chunk);
    if (parsed) {
      onEvent(parsed);
    }
    separatorIndex = working.indexOf("\n\n");
  }

  return working;
}

export function useTaskEvents(
  taskId: string | null,
  onEvent: TaskEventHandler
) {
  const abortRef = useRef<AbortController | null>(null);
  const retryRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!taskId) return;

    let isActive = true;
    let isAuthTerminalError = false;
    let backoff = INITIAL_BACKOFF_MS;
    let lastEventId: string | null = null;

    const clearRetryTimeout = () => {
      if (retryTimeoutRef.current == null) {
        return;
      }
      window.clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    };

    const connect = async () => {
      while (isActive) {
        try {
          const controller = new AbortController();
          abortRef.current?.abort();
          abortRef.current = controller;

          const headers: Record<string, string> = {
            Accept: "text/event-stream",
          };
          if (lastEventId) {
            headers["Last-Event-ID"] = lastEventId;
          }

          const url = resolveApiUrl(
            `/api/tasks/${encodeURIComponent(taskId)}/events`
          );

          const response = await fetch(
            url,
            buildAuthenticatedFetchInit(
              {
                signal: controller.signal,
                headers,
                cache: "no-store",
              },
              { forceApiKey: false }
            )
          );

          if (response.status === 401 || response.status === 403) {
            console.warn(
              `[task-events] stream unauthorized (${response.status}); stopping reconnect`
            );
            isAuthTerminalError = true;
            clearRetryTimeout();
            return;
          }

          if (!response.ok) {
            throw new Error(
              `Task event stream failed with status ${response.status}`
            );
          }

          if (!response.body) {
            throw new Error("No stream body");
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          retryRef.current = 0;
          backoff = INITIAL_BACKOFF_MS;

          while (isActive) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            buffer = drainBuffer(buffer, (event) => {
              if (event.id) {
                lastEventId = event.id;
              }
              onEventRef.current(event);
            });
          }

          buffer += decoder.decode();
          drainBuffer(buffer, (event) => {
            if (event.id) {
              lastEventId = event.id;
            }
            onEventRef.current(event);
          });
        } catch (error) {
          if (!isActive || isAuthTerminalError || isAbortError(error)) {
            break;
          }

          console.warn("[task-events] stream disconnected", error);

          await new Promise<void>((resolve) => {
            clearRetryTimeout();
            retryTimeoutRef.current = window.setTimeout(() => {
              retryTimeoutRef.current = null;
              resolve();
            }, backoff);
          });
          if (!isActive || isAuthTerminalError) {
            break;
          }
          backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
          retryRef.current += 1;
        }
      }
    };

    void connect();

    return () => {
      isActive = false;
      clearRetryTimeout();
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [taskId]);
}

export default useTaskEvents;
