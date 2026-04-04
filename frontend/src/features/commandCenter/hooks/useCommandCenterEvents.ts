import * as React from "react";

import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import {
  getRuntimeConfigSync,
  resolveSseEndpoint,
} from "@/lib/runtimeConfig";

import {
  aggregateCommandCenterEvents,
  normalizeCommandCenterEvent,
} from "@/features/commandCenter/commandCenterRunAggregation";

import type {
  CommandCenterApproval,
  CommandCenterConnectionState,
  CommandCenterEvent,
  CommandCenterRun,
} from "@/features/commandCenter/types";

const EVENT_BUFFER_LIMIT = 500;

type UseCommandCenterEventsOptions = {
  enabled: boolean;
};

type UseCommandCenterEventsResult = {
  approvals: CommandCenterApproval[];
  connectionDetail: string | null;
  connectionState: CommandCenterConnectionState;
  events: CommandCenterEvent[];
  lastEventAt: number | null;
  runs: CommandCenterRun[];
  unauthorized: boolean;
};

function appendBoundedEvent(
  previous: CommandCenterEvent[],
  next: CommandCenterEvent
): CommandCenterEvent[] {
  const appended = [...previous, next];
  if (appended.length <= EVENT_BUFFER_LIMIT) return appended;
  return appended.slice(appended.length - EVENT_BUFFER_LIMIT);
}

function tapMessageEvents(
  source: GuardianEventSource,
  onMessage: (event: MessageEvent<string>) => void
): () => void {
  const originalDispatchEvent = source.dispatchEvent.bind(source);
  (source as any).dispatchEvent = (event: Event) => {
    if (event instanceof MessageEvent) {
      onMessage(event as MessageEvent<string>);
    }
    return originalDispatchEvent(event);
  };
  return () => {
    (source as any).dispatchEvent = originalDispatchEvent;
  };
}

function closeSource(ref: React.MutableRefObject<GuardianEventSource | null>): void {
  ref.current?.close();
  ref.current = null;
}

export function useCommandCenterEvents(
  options: UseCommandCenterEventsOptions
): UseCommandCenterEventsResult {
  const { enabled } = options;
  const auth = useAuthState();
  const [events, setEvents] = React.useState<CommandCenterEvent[]>([]);
  const [connectionState, setConnectionState] =
    React.useState<CommandCenterConnectionState>("closed");
  const [lastEventAt, setLastEventAt] = React.useState<number | null>(null);
  const [unauthorized, setUnauthorized] = React.useState(false);
  const [connectionDetail, setConnectionDetail] = React.useState<string | null>(
    null
  );
  const sourceRef = React.useRef<GuardianEventSource | null>(null);

  React.useEffect(() => {
    if (!enabled) {
      closeSource(sourceRef);
      setConnectionState("closed");
      setConnectionDetail("Command Center not enabled.");
      setUnauthorized(false);
      return;
    }

    if (!checkAuthGate(auth, "command center SSE")) {
      closeSource(sourceRef);
      setConnectionState("closed");
      const blocked = auth.ready && auth.status !== "authenticated";
      setUnauthorized(blocked);
      setConnectionDetail(blocked ? "Unauthorized" : "Waiting for authentication");
      return;
    }

    const authInit = buildAuthenticatedFetchInit({
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
    const headers = ((authInit.headers as Record<string, string>) ?? {}) as Record<
      string,
      string
    >;
    const source = new GuardianEventSource(
      resolveSseEndpoint(getRuntimeConfigSync()),
      {
        autoReconnect: true,
        headers,
        retryInterval: 3000,
        withCredentials: authInit.credentials === "include",
        onUnauthorized: () => {
          markAuthUnauthenticatedFrom401();
        },
      }
    );

    closeSource(sourceRef);
    sourceRef.current = source;
    setConnectionState("connecting");
    setConnectionDetail("Connecting to live events...");
    setUnauthorized(false);

    const restoreDispatch = tapMessageEvents(source, (message) => {
      const normalized = normalizeCommandCenterEvent(message);
      setEvents((previous) => appendBoundedEvent(previous, normalized));
      setLastEventAt(normalized.receivedAt);
    });

    const handleOpen = () => {
      setConnectionState("open");
      setConnectionDetail(null);
      setUnauthorized(false);
    };

    const handleError = () => {
      setConnectionState("error");
      setConnectionDetail("Disconnected from live events.");
    };

    const handleUnauthorized = () => {
      setConnectionState("closed");
      setConnectionDetail("Unauthorized");
      setUnauthorized(true);
    };

    source.addEventListener("open", handleOpen as EventListener);
    source.addEventListener("error", handleError as EventListener);
    source.addEventListener("unauthorized", handleUnauthorized as EventListener);

    return () => {
      restoreDispatch();
      source.removeEventListener("open", handleOpen as EventListener);
      source.removeEventListener("error", handleError as EventListener);
      source.removeEventListener(
        "unauthorized",
        handleUnauthorized as EventListener
      );
      if (sourceRef.current === source) {
        closeSource(sourceRef);
      } else {
        source.close();
      }
    };
  }, [auth.ready, auth.status, auth.token, enabled]);

  const derived = React.useMemo(
    () => aggregateCommandCenterEvents(events),
    [events]
  );

  return {
    approvals: derived.approvals,
    connectionDetail,
    connectionState,
    events,
    lastEventAt,
    runs: derived.runs,
    unauthorized,
  };
}

export default useCommandCenterEvents;
