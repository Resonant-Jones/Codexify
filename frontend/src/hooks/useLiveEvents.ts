/**
 * useLiveEvents - shared SSE hook backed by a per-tab singleton hub.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { getRuntimeConfigSync, resolveSseEndpoint } from "@/lib/runtimeConfig";
import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";
import { SessionSpine } from "@/state/session/SessionSpine";
import {
  LiveEventsHubEvent,
  subscribeLiveEventsHub,
  subscribeLiveEventsHubStatus,
} from "@/lib/liveEventsHub";

const LAST_EVENT_DEBOUNCE_MS = 50;
const CONNECTED_DEBOUNCE_MS = 200;

export interface LiveEvent {
  id: string | null;
  type: string;
  data: unknown;
}

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export interface UseLiveEventsResult {
  connected: boolean;
  connectionStatus: ConnectionStatus;
  statusUpdatedAt: number | null;
  lastEvent: LiveEvent | null;
  subscribe: (eventType: string, handler: (event: LiveEvent) => void) => () => void;
}

export function useLiveEvents(options: { passive?: boolean } = {}): UseLiveEventsResult {
  const { passive = false } = options;
  const auth = useAuthState();
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [statusUpdatedAt, setStatusUpdatedAt] = useState<number>(() => Date.now());
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const listenersRef = useRef<Map<string, Set<(event: LiveEvent) => void>>>(
    new Map()
  );
  const isUnmountedRef = useRef(false);
  const connectedRef = useRef(false);
  const pendingConnectedRef = useRef<boolean | null>(null);
  const connectedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastEventRef = useRef<LiveEvent | null>(null);
  const pendingLastEventRef = useRef<LiveEvent | null>(null);
  const lastEventTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const streamUrl = useMemo(() => resolveSseEndpoint(getRuntimeConfigSync()), []);

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

  const flushConnected = useCallback(() => {
    if (isUnmountedRef.current) return;
    const next = pendingConnectedRef.current;
    if (next === null || connectedRef.current === next) {
      pendingConnectedRef.current = null;
      return;
    }
    connectedRef.current = next;
    pendingConnectedRef.current = null;
    setConnected(next);
  }, []);

  const updateConnected = useCallback(
    (next: boolean) => {
      if (isUnmountedRef.current) return;
      if (connectedRef.current === next && pendingConnectedRef.current === null) {
        return;
      }
      pendingConnectedRef.current = next;
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
      }
      connectedTimerRef.current = setTimeout(() => {
        connectedTimerRef.current = null;
        flushConnected();
      }, CONNECTED_DEBOUNCE_MS);
    },
    [flushConnected]
  );

  const flushLastEvent = useCallback(() => {
    if (isUnmountedRef.current) return;
    const payload = pendingLastEventRef.current;
    if (!payload || isSameEvent(lastEventRef.current, payload)) {
      return;
    }
    setLastEvent(payload);
  }, [isSameEvent]);

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

  const handleHubEvent = useCallback(
    (event: LiveEventsHubEvent) => {
      const payload: LiveEvent = {
        id: event.id || null,
        type: event.type || "message",
        data: event.data,
      };
      const activeSpine = SessionSpine.getRegisteredSpine();
      if (activeSpine && !activeSpine.shouldAcceptLiveEvent(payload.type, payload.data)) {
        return;
      }
      if (isSameEvent(lastEventRef.current, payload)) {
        return;
      }
      lastEventRef.current = payload;
      if (!passive) {
        scheduleLastEventUpdate(payload);
      }
      const listeners = listenersRef.current.get(payload.type);
      if (!listeners) {
        return;
      }
      listeners.forEach((listener) => {
        try {
          listener(payload);
        } catch (error) {
          console.error(`[useLiveEvents] listener for ${payload.type} failed`, error);
        }
      });
    },
    [isSameEvent, passive, scheduleLastEventUpdate]
  );

  useEffect(() => {
    isUnmountedRef.current = false;
    return () => {
      isUnmountedRef.current = true;
      if (lastEventTimerRef.current) {
        clearTimeout(lastEventTimerRef.current);
        lastEventTimerRef.current = null;
      }
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
        connectedTimerRef.current = null;
      }
      pendingConnectedRef.current = null;
      pendingLastEventRef.current = null;
      listenersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (!checkAuthGate(auth, "SSE connect")) {
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
        connectedTimerRef.current = null;
      }
      pendingConnectedRef.current = null;
      connectedRef.current = false;
      setConnected(false);
      setConnectionStatus("disconnected");
      setStatusUpdatedAt(Date.now());
      return;
    }

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

    let cancelled = false;
    const unsubscribeStatus = subscribeLiveEventsHubStatus((status) => {
      if (cancelled || isUnmountedRef.current) return;
      setConnectionStatus((prev) => {
        if (prev === status.connectionStatus) return prev;
        setStatusUpdatedAt(Date.now());
        return status.connectionStatus;
      });
      updateConnected(
        status.connectionStatus === "connected" && status.readyState === 1
      );
    });

    const unsubscribeEvents = subscribeLiveEventsHub(
      {
        url: streamUrl,
        headers,
        withCredentials: authInit.credentials === "include",
        onUnauthorized: () => {
          markAuthUnauthenticatedFrom401();
        },
      },
      (event) => {
        if (cancelled || isUnmountedRef.current) return;
        handleHubEvent(event);
      }
    );

    return () => {
      cancelled = true;
      unsubscribeEvents();
      unsubscribeStatus();
    };
  }, [
    auth.ready,
    auth.status,
    auth.token,
    handleHubEvent,
    streamUrl,
    updateConnected,
  ]);

  const subscribe = useCallback(
    (eventType: string, handler: (event: LiveEvent) => void) => {
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
    statusUpdatedAt,
    lastEvent: passive ? lastEventRef.current : lastEvent,
    subscribe,
  };
}

export function useLiveEventsStatus(): Pick<
  UseLiveEventsResult,
  "connected" | "connectionStatus" | "statusUpdatedAt"
> {
  const { connected, connectionStatus, statusUpdatedAt } = useLiveEvents({
    passive: true,
  });
  return { connected, connectionStatus, statusUpdatedAt };
}
