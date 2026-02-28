/**
 * useLiveEvents - shared SSE hook that enforces semantic-only state updates.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import { GUARDIAN_API_BASE } from "@/lib/env";
import { combineBaseAndPath } from "@/lib/urlJoin";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";

const EVENT_ENDPOINT = "/api/events";
const DEFAULT_EVENT_TYPES = [
  "ping",
  "message.created",
  "thread.updated",
  "thread.created",
  "thread.branch",
  "thread.archived",
  "thread.profile.switched",
  "connector.status",
  "connector.sync",
];

// Coalesce rapid SSE bursts into a single React update.
const LAST_EVENT_DEBOUNCE_MS = 50;
// Debounce connected state changes to prevent rapid flapping
const CONNECTED_DEBOUNCE_MS = 200;

export interface LiveEvent {
  id: string | null;
  type: string;
  data: unknown;
}

export type ConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface UseLiveEventsResult {
  connected: boolean;
  connectionStatus: ConnectionStatus;
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
export function useLiveEvents(options: { passive?: boolean } = {}): UseLiveEventsResult {
  const { passive = false } = options;
  const auth = useAuthState();
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const listenersRef = useRef<Map<string, Set<(event: LiveEvent) => void>>>(
    new Map()
  );
  const connectedRef = useRef(false);
  const lastEventRef = useRef<LiveEvent | null>(null);
  const isUnmountedRef = useRef(false);
  const pendingLastEventRef = useRef<LiveEvent | null>(null);
  const lastEventTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingConnectedRef = useRef<boolean | null>(null);
  const hasConnectedRef = useRef(false); // Track if we've ever successfully connected

  const streamUrl = useMemo(() => combineBaseAndPath(GUARDIAN_API_BASE, EVENT_ENDPOINT), []);

  const isSameEvent = useCallback((prev: LiveEvent | null, next: LiveEvent) => {
    if (!prev) return false;
    if (prev.id && next.id && prev.id === next.id) return true;
    if (prev.type !== next.type) return false;
    try {
      return JSON.stringify(prev.data) === JSON.stringify(next.data);
    } catch {
      return false;
    }
  }, []);

  // Debounced connected state update to prevent rapid flapping
  const flushConnected = useCallback(() => {
    if (isUnmountedRef.current) return;
    const next = pendingConnectedRef.current;
    if (next !== null && connectedRef.current !== next) {
      connectedRef.current = next;
      setConnected(next);
      // Update connection status based on whether we've ever connected
      if (next) {
        setConnectionStatus("connected");
        hasConnectedRef.current = true;
      } else {
        setConnectionStatus(hasConnectedRef.current ? "reconnecting" : "connecting");
      }
    }
    pendingConnectedRef.current = null;
  }, [isSameEvent]);

  const updateConnected = useCallback((next: boolean) => {
    if (isUnmountedRef.current) return;
    // If the value hasn't changed from current ref, no-op
    if (connectedRef.current === next && pendingConnectedRef.current === null) {
      return;
    }
    pendingConnectedRef.current = next;
    // Clear any pending timer
    if (connectedTimerRef.current) {
      clearTimeout(connectedTimerRef.current);
    }
    // Debounce the state update to prevent rapid flapping
    connectedTimerRef.current = setTimeout(() => {
      connectedTimerRef.current = null;
      flushConnected();
    }, CONNECTED_DEBOUNCE_MS);
  }, [flushConnected]);

  const flushLastEvent = useCallback(() => {
    if (isUnmountedRef.current) return;
    const payload = pendingLastEventRef.current;
    if (payload && !isSameEvent(lastEventRef.current, payload)) {
      setLastEvent(payload);
    }
  }, []);

  const scheduleLastEventUpdate = useCallback(
    (payload: LiveEvent) => {
      pendingLastEventRef.current = payload;
      if (lastEventTimerRef.current) {
        clearTimeout(lastEventTimerRef.current);
      }
      lastEventTimerRef.current = setTimeout(() => {
        lastEventTimerRef.current = null;
        flushLastEvent();
      }, LAST_EVENT_DEBOUNCE_MS);
    },
    [flushLastEvent]
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    if (!checkAuthGate(auth, "SSE connect")) {
      connectedRef.current = false;
      setConnected(false);
      return;
    }
    isUnmountedRef.current = false;

    // Build absolute URL + resume from server outbox
    const lastId = (() => {
      try { return Number(localStorage.getItem("cfy.events.lastId") || 0) || 0; } catch { return 0; }
    })();
    const url = `${streamUrl}?last_id=${lastId}`;

    // Only send an API key header when we actually have a key.
    // Sending an empty X-API-Key causes noisy 401s and prevents proxy-based auth injection.
    const authInit = buildAuthenticatedFetchInit({
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
    const headers = (authInit.headers as Record<string, string>) ?? {
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    };

    const eventSource = new GuardianEventSource(url, {
      headers,
      withCredentials: authInit.credentials === "include",
      onUnauthorized: () => {
        markAuthUnauthenticatedFrom401();
      },
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
      updateConnected(true);
      if (isSameEvent(lastEventRef.current, payload)) {
        return;
      }
      lastEventRef.current = payload;
      if (!passive) {
        scheduleLastEventUpdate(payload);
      }
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
      updateConnected(true);
      console.info(`[SSE] connected ${streamUrl}`);
    };

    const handleError = (_evt: Event) => {
      if (isCancelled) return;
      updateConnected(false);
    };

    eventSource.addEventListener("open", handleOpen as EventListener);
    eventSource.onerror = handleError;
    eventSource.onmessage = handleEvent;

    DEFAULT_EVENT_TYPES.forEach((eventName) => {
      eventSource.addEventListener(eventName, handleEvent as EventListener);
    });

    return () => {
      isCancelled = true;
      isUnmountedRef.current = true;
      // Clear debounce timers to prevent state updates after unmount
      if (lastEventTimerRef.current) {
        clearTimeout(lastEventTimerRef.current);
        lastEventTimerRef.current = null;
      }
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
        connectedTimerRef.current = null;
      }
      pendingLastEventRef.current = null;
      pendingConnectedRef.current = null;
      listenersRef.current.clear();
      DEFAULT_EVENT_TYPES.forEach((eventName) => {
        eventSource.removeEventListener(eventName, handleEvent as EventListener);
      });
      eventSource.removeEventListener("open", handleOpen as EventListener);
      eventSource.onmessage = null;
      eventSource.onerror = null;
      eventSource.close();
    };
    // Note: updateConnected and scheduleLastEventUpdate are intentionally omitted from deps
    // as they are stable refs and including them would cause unnecessary reconnections
  }, [
    auth.ready,
    auth.status,
    auth.token,
    passive,
    streamUrl,
    isSameEvent,
    scheduleLastEventUpdate,
    updateConnected,
  ]);

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

  return {
    connected,
    connectionStatus,
    lastEvent: passive ? lastEventRef.current : lastEvent,
    subscribe,
  };
}
