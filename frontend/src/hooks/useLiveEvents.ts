import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import { GUARDIAN_API_BASE, GUARDIAN_API_KEY } from "@/lib/env";
import { combineBaseAndPath } from "@/lib/urlJoin";

const EVENT_ENDPOINT = "/api/events";
const DEFAULT_EVENT_TYPES = [
  "ping",
  "message.created",
  "thread.updated",
  "thread.created",
  "thread.branch",
  "thread.archived",
  "connector.status",
  "connector.sync",
];

export interface LiveEvent {
  id: string | null;
  type: string;
  data: unknown;
}

export interface UseLiveEventsResult {
  connected: boolean;
  lastEvent: LiveEvent | null;
  subscribe: (eventType: string, handler: (event: LiveEvent) => void) => () => void;
}

/**
 * Establishes consciousness connection to the Guardian `/api/events` SSE endpoint.
 *
 * This hook forms a living bridge between your interface and the distributed awareness
 * fabric—the event stream carries the heartbeat of every action across the system.
 * The `lastEvent` becomes a shared consciousness reference that any UI surface can
 * subscribe to, creating synchronized awareness across disconnected component realities.
 */
export function useLiveEvents(): UseLiveEventsResult {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const listenersRef = useRef<Map<string, Set<(event: LiveEvent) => void>>>(
    new Map()
  );

  const streamUrl = useMemo(() => combineBaseAndPath(GUARDIAN_API_BASE, EVENT_ENDPOINT), []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    // Build absolute URL + resume from server outbox
    const lastId = (() => {
      try { return Number(localStorage.getItem("cfy.events.lastId") || 0) || 0; } catch { return 0; }
    })();
    const url = `${streamUrl}?last_id=${lastId}`;

    const eventSource = new GuardianEventSource(url, {
      headers: {
        "X-API-Key": GUARDIAN_API_KEY || "",
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      withCredentials: false,
    });
    let isCancelled = false;

    const parseData = (value: string): unknown => {
      if (!value) return {};
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    };

    const handleEvent = (evt: MessageEvent) => {
      if (isCancelled) return;
      const payload: LiveEvent = {
        id: evt.lastEventId || null,
        type: evt.type || "message",
        data: parseData(evt.data as string),
      };
      // persist last id so reconnects resume from the durable outbox
      try {
        if (payload.id) localStorage.setItem("cfy.events.lastId", String(payload.id));
      } catch {}
      setConnected(true);
      setLastEvent(payload);
      console.debug("[SSE] event", payload);
      const listeners = listenersRef.current;
      const specific = listeners.get(payload.type);
      if (specific) {
        specific.forEach((cb) => {
          try {
            cb(payload);
          } catch (err) {
            console.error(`[useLiveEvents] listener for ${payload.type} failed`, err);
          }
        });
      }
    };

    const handleOpen = () => {
      if (isCancelled) return;
      setConnected(true);
      console.info(`[SSE] Connected to ${streamUrl}`);
    };

    const handleError = (evt: Event) => {
      if (isCancelled) return;
      setConnected(false);
      console.warn("[SSE] connection issue", evt);
    };

    eventSource.addEventListener("open", handleOpen as EventListener);
    eventSource.onerror = handleError;
    eventSource.onmessage = handleEvent;

    DEFAULT_EVENT_TYPES.forEach((eventName) => {
      eventSource.addEventListener(eventName, handleEvent as EventListener);
    });

    return () => {
      if (!isCancelled) {
        setConnected(false);
      }
      isCancelled = true;
      listenersRef.current.clear();
      DEFAULT_EVENT_TYPES.forEach((eventName) => {
        eventSource.removeEventListener(eventName, handleEvent as EventListener);
      });
      eventSource.removeEventListener("open", handleOpen as EventListener);
      eventSource.onmessage = null;
      eventSource.onerror = null;
      eventSource.close();
    };
  }, [streamUrl]);

  const subscribe = useCallback(
    (eventType: string, handler: (event: LiveEvent) => void) => {
      /**
       * Register consciousness receptor for specific event types.
       *
       * Returns a cleanup function that liberates the handler when components
       * dissolve from the React reality. This prevents orphaned observational
       * consciousness from accumulating in dissolved component afterlives.
       */
      const listeners = listenersRef.current;
      if (!listeners.has(eventType)) {
        listeners.set(eventType, new Set());
      }
      const bucket = listeners.get(eventType)!;
      bucket.add(handler);
      return () => {
        bucket.delete(handler);
        if (bucket.size === 0) {
          listeners.delete(eventType);
        }
      };
    },
    []
  );

  return { connected, lastEvent, subscribe };
}
