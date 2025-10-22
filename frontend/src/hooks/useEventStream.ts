import { useCallback, useEffect, useRef, useState } from "react";
import { EventSourcePolyfill } from "event-source-polyfill";
import { buildEventUrl } from "../lib/eventUrl";
import { ENV } from "../lib/env";

type OnEvent = (ev: MessageEvent) => void;

export function useEventStream(opts?: {
  onEvent?: OnEvent;
  onConnectChange?: (connected: boolean) => void;
}) {
  const { onEvent, onConnectChange } = opts ?? {};
  const [connected, setConnected] = useState(false);
  const lastIdRef = useRef<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef<number>(1000); // backoff
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleReconnect = useCallback(
    (connectFn: () => void) => {
      const delay = Math.min(retryRef.current, 30000);
      retryRef.current = Math.min(retryRef.current * 1.8, 30000);
      timeoutRef.current = setTimeout(connectFn, delay);
    },
    []
  );

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const url = new URL(buildEventUrl(null), window.location.origin);
    if (lastIdRef.current) url.searchParams.set("last_id", lastIdRef.current);

    // Send dev key when available; Vite proxy still adds its own header in dev.
    const es = new EventSourcePolyfill(url.toString(), {
      withCredentials: false,
      headers: ENV.uiKey ? { "X-API-Key": ENV.uiKey } : undefined,
    });
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      onConnectChange?.(true);
      retryRef.current = 1000;
    };

    es.onmessage = (ev) => {
      if (ev.lastEventId) lastIdRef.current = ev.lastEventId;
      onEvent?.(ev);
    };

    es.onerror = () => {
      setConnected(false);
      onConnectChange?.(false);
      es.close();
      scheduleReconnect(connect);
    };
  }, [onConnectChange, onEvent, scheduleReconnect]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [connect]);

  return { connected };
}
