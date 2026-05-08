/**
 * useLiveEvents - shared SSE hook backed by a per-tab singleton hub.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import type { LiveEvent } from "@/lib/events/types";
import {
  getDesktopRuntimeAuthConfig,
  getRuntimeConfigHydrationFailureKind,
  getRuntimeConfigSync,
  getRuntimeConfigVersion,
  getRuntimeConfigHydrationState,
  isTauriRuntime,
  resolveSseEndpoint,
  subscribeRuntimeConfigState,
} from "@/lib/runtimeConfig";
import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";
import { SessionSpine } from "@/state/session/SessionSpine";
import {
  LiveEventsHubEvent,
  getLiveEventsHubStatus,
  subscribeLiveEventsHub,
  subscribeLiveEventsHubStatus,
  type LiveEventsHubStatus,
} from "@/lib/liveEventsHub";
import {
  LIVE_EVENT_CONNECTION_STATES,
  LiveEventConnectionState,
} from "@/contracts/runtimeTokens";
import {
  getAuthToken,
  getDevApiKey,
  readRuntimeApiKey,
} from "@/lib/api";
import {
  resolveRuntimeAuthSource,
  type RuntimeAuthSource,
} from "@/lib/runtimeAuth";
import {
  getRuntimeAuthVersion,
  subscribeRuntimeAuthState,
} from "@/lib/runtimeAuth";

const LAST_EVENT_DEBOUNCE_MS = 50;
const CONNECTED_DEBOUNCE_MS = 200;

export type { LiveEvent } from "@/lib/events/types";

export type ConnectionStatus = LiveEventConnectionState;

export interface UseLiveEventsResult {
  connected: boolean;
  connectionStatus: ConnectionStatus;
  statusUpdatedAt: number | null;
  lastEvent: LiveEvent | null;
  diagnostics: LiveEventsDiagnostics;
  subscribe: (eventType: string, handler: (event: LiveEvent) => void) => () => void;
}

export type LiveEventsDiagnostics = {
  endpoint: string | null;
  connectionState: ConnectionStatus;
  lastEventAt: number | null;
  lastPingAt: number | null;
  statusUpdatedAt: number | null;
  lastHttpStatus: number | null;
  transportErrorClass: string | null;
  authSource: RuntimeAuthSource;
  apiKeyPresent: boolean;
  hydrationState: "pending" | "ready" | "failed";
  nativeCommandStatus: string | null;
  reconnectAttempts: number;
  retryMs: number;
  subscribers: number;
  readyState: 0 | 1 | 2;
  lastErrorAt: number | null;
  lastEventId: string | null;
};

function resolveLiveEventsAuthSource(): RuntimeAuthSource {
  const hydrationState = getRuntimeConfigHydrationState();
  if (hydrationState === "pending") {
    return "unknown";
  }
  const desktopAuthConfig = getDesktopRuntimeAuthConfig();
  const runtimeDesktopKeyPresent = Boolean(
    desktopAuthConfig?.apiKeyPresent || readRuntimeApiKey()
  );
  const devKeyPresent = Boolean(getDevApiKey().trim());
  const bearerPresent = Boolean(getAuthToken());
  return resolveRuntimeAuthSource({
    isTauriRuntime: isTauriRuntime(),
    runtimeDesktopKeyPresent,
    devKeyPresent,
    bearerPresent,
    desktopAuthConfigKnown: Boolean(desktopAuthConfig),
  });
}

export function useLiveEvents(options: { passive?: boolean } = {}): UseLiveEventsResult {
  const { passive = false } = options;
  const auth = useAuthState();
  const runtimeAuthVersion = useSyncExternalStore(
    subscribeRuntimeAuthState,
    getRuntimeAuthVersion,
    getRuntimeAuthVersion
  );
  const runtimeConfigVersion = useSyncExternalStore(
    subscribeRuntimeConfigState,
    getRuntimeConfigVersion,
    getRuntimeConfigVersion
  );
  const runtimeConfigHydrationState = useSyncExternalStore(
    subscribeRuntimeConfigState,
    getRuntimeConfigHydrationState,
    getRuntimeConfigHydrationState
  );
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    LIVE_EVENT_CONNECTION_STATES.DISCONNECTED
  );
  const [statusUpdatedAt, setStatusUpdatedAt] = useState<number>(() => Date.now());
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const [hubStatus, setHubStatus] = useState<LiveEventsHubStatus>(
    () => getLiveEventsHubStatus()
  );
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

  const streamUrl = useMemo(
    () => resolveSseEndpoint(getRuntimeConfigSync()),
    [runtimeConfigVersion]
  );

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
      const activeSpine = SessionSpine.getRegisteredSpine();
      if (activeSpine && !activeSpine.shouldAcceptLiveEvent(event.type, event.data)) {
        return;
      }
      if (isSameEvent(lastEventRef.current, event)) {
        return;
      }
      lastEventRef.current = event;
      if (!passive) {
        scheduleLastEventUpdate(event);
      }
      const listeners = listenersRef.current.get(event.type);
      if (!listeners) {
        return;
      }
      listeners.forEach((listener) => {
        try {
          listener(event);
        } catch (error) {
          console.error(`[useLiveEvents] listener for ${event.type} failed`, error);
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

    if (runtimeConfigHydrationState === "pending") {
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
        connectedTimerRef.current = null;
      }
      pendingConnectedRef.current = null;
      connectedRef.current = false;
      setConnected(false);
      setConnectionStatus(LIVE_EVENT_CONNECTION_STATES.CONNECTING);
      setStatusUpdatedAt(Date.now());
      return;
    }

    if (runtimeConfigHydrationState === "failed") {
      if (connectedTimerRef.current) {
        clearTimeout(connectedTimerRef.current);
        connectedTimerRef.current = null;
      }
      pendingConnectedRef.current = null;
      connectedRef.current = false;
      setConnected(false);
      setConnectionStatus(LIVE_EVENT_CONNECTION_STATES.DISCONNECTED);
      setStatusUpdatedAt(Date.now());
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
      setConnectionStatus(LIVE_EVENT_CONNECTION_STATES.DISCONNECTED);
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
    const apiKeyPresent = Boolean(
      getDesktopRuntimeAuthConfig()?.apiKeyPresent ||
        readRuntimeApiKey() ||
        getDevApiKey().trim()
    );

    let cancelled = false;
    const unsubscribeStatus = subscribeLiveEventsHubStatus((status) => {
      if (cancelled || isUnmountedRef.current) return;
      setHubStatus(status);
      setConnectionStatus((prev) => {
        if (prev === status.connectionStatus) return prev;
        setStatusUpdatedAt(Date.now());
        return status.connectionStatus;
      });
      updateConnected(
        status.connectionStatus === LIVE_EVENT_CONNECTION_STATES.CONNECTED &&
          status.readyState === 1
      );
    });

    const unsubscribeEvents = subscribeLiveEventsHub(
      {
        url: streamUrl,
        headers,
        withCredentials: authInit.credentials === "include",
        authSource: resolveLiveEventsAuthSource(),
        apiKeyPresent,
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
    runtimeAuthVersion,
    runtimeConfigHydrationState,
    streamUrl,
    updateConnected,
  ]);

  const diagnostics = useMemo<LiveEventsDiagnostics>(
    () => ({
      endpoint: hubStatus.endpoint ?? streamUrl,
      connectionState: connectionStatus,
      lastEventAt: hubStatus.lastEventAt,
      lastPingAt: hubStatus.lastPingAt,
      statusUpdatedAt,
      lastHttpStatus: hubStatus.lastHttpStatus,
      transportErrorClass: hubStatus.transportErrorClass,
      authSource: hubStatus.authSource,
      apiKeyPresent: hubStatus.apiKeyPresent,
      hydrationState: runtimeConfigHydrationState,
      nativeCommandStatus:
        runtimeConfigHydrationState === "failed"
          ? getRuntimeConfigHydrationFailureKind() ?? "failed"
          : runtimeConfigHydrationState,
      reconnectAttempts: hubStatus.connectAttempt,
      retryMs: hubStatus.retryMs,
      subscribers: hubStatus.subscribers,
      readyState: hubStatus.readyState,
      lastErrorAt: hubStatus.lastErrorAt,
      lastEventId: hubStatus.lastEventId,
    }),
    [
      connectionStatus,
      hubStatus.apiKeyPresent,
      hubStatus.authSource,
      hubStatus.connectAttempt,
      hubStatus.endpoint,
      hubStatus.lastErrorAt,
      hubStatus.lastEventAt,
      hubStatus.lastEventId,
      hubStatus.lastHttpStatus,
      hubStatus.lastPingAt,
      hubStatus.readyState,
      hubStatus.retryMs,
      hubStatus.subscribers,
      hubStatus.transportErrorClass,
      statusUpdatedAt,
      runtimeConfigHydrationState,
      streamUrl,
    ]
  );

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
    diagnostics,
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
