import { useEffect, useRef } from "react";
import { useLiveEvents } from "@/hooks/useLiveEvents";

type OnEvent = (ev: MessageEvent) => void;

/**
 * Legacy compatibility wrapper over the singleton live-events hub.
 * This prevents opening a second EventSource in parallel with useLiveEvents.
 */
export function useEventStream(opts?: {
  onEvent?: OnEvent;
  onConnectChange?: (connected: boolean) => void;
}) {
  const { onEvent, onConnectChange } = opts ?? {};
  const { connected, lastEvent } = useLiveEvents();
  const onEventRef = useRef<OnEvent | undefined>(onEvent);
  const onConnectChangeRef = useRef<typeof onConnectChange>(onConnectChange);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    onConnectChangeRef.current = onConnectChange;
  }, [onConnectChange]);

  useEffect(() => {
    onConnectChangeRef.current?.(connected);
  }, [connected]);

  useEffect(() => {
    if (!lastEvent || !onEventRef.current) return;
    const payload =
      typeof lastEvent.data === "string"
        ? lastEvent.data
        : JSON.stringify(lastEvent.data ?? {});
    const synthetic = new MessageEvent(lastEvent.type || "message", {
      data: payload,
      lastEventId: lastEvent.id ?? "",
    });
    onEventRef.current(synthetic);
  }, [lastEvent]);

  return { connected };
}
