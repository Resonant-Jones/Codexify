import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  checkAuthGate,
  markAuthUnauthenticatedFrom401,
  useAuthState,
} from "@/lib/authState";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import { resolveApiUrl } from "@/lib/runtimeConfig";

import type {
  CommandCenterConnectionState,
  CommandCenterRun,
  CommandCenterTaskEvent,
} from "@/features/commandCenter/types";

const TASK_EVENT_LIMIT = 200;

type RunDetailDrawerProps = {
  run: CommandCenterRun | null;
  onClose: () => void;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function parseTaskJson(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    return asRecord(JSON.parse(trimmed));
  } catch {
    return null;
  }
}

function summarizeTaskEvent(
  raw: string,
  json: Record<string, unknown> | null,
  eventType: string | null
): string {
  const summary = firstString(
    json?.summary,
    json?.message,
    json?.error,
    json?.status
  );
  if (summary) return summary;
  const trimmed = raw.trim();
  if (trimmed) {
    return trimmed.length > 160 ? `${trimmed.slice(0, 157)}...` : trimmed;
  }
  return eventType ?? "Task event";
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

function appendTaskEvent(
  previous: CommandCenterTaskEvent[],
  next: CommandCenterTaskEvent
): CommandCenterTaskEvent[] {
  const appended = [...previous, next];
  if (appended.length <= TASK_EVENT_LIMIT) return appended;
  return appended.slice(appended.length - TASK_EVENT_LIMIT);
}

function connectionStyle(state: CommandCenterConnectionState): React.CSSProperties {
  switch (state) {
    case "open":
      return {
        background: "rgba(34, 197, 94, 0.12)",
        borderColor: "rgba(34, 197, 94, 0.35)",
      };
    case "connecting":
      return {
        background: "rgba(59, 130, 246, 0.12)",
        borderColor: "rgba(59, 130, 246, 0.35)",
      };
    case "error":
      return {
        background: "rgba(239, 68, 68, 0.12)",
        borderColor: "rgba(239, 68, 68, 0.35)",
      };
    default:
      return {
        background: "rgba(148, 163, 184, 0.12)",
        borderColor: "rgba(148, 163, 184, 0.28)",
      };
  }
}

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

export default function RunDetailDrawer({
  run,
  onClose,
}: RunDetailDrawerProps) {
  const auth = useAuthState();
  const [taskEvents, setTaskEvents] = React.useState<CommandCenterTaskEvent[]>([]);
  const [connectionState, setConnectionState] =
    React.useState<CommandCenterConnectionState>("closed");
  const [connectionDetail, setConnectionDetail] = React.useState<string | null>(
    null
  );
  const [lastEventAt, setLastEventAt] = React.useState<number | null>(null);
  const [showRawJson, setShowRawJson] = React.useState(false);
  const sourceRef = React.useRef<GuardianEventSource | null>(null);
  const open = Boolean(run);

  React.useEffect(() => {
    const source = sourceRef.current;
    return () => {
      source?.close();
    };
  }, []);

  React.useEffect(() => {
    setShowRawJson(false);
  }, [run?.key]);

  React.useEffect(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setTaskEvents([]);
    setLastEventAt(null);
    setConnectionState("closed");
    setConnectionDetail(null);

    if (!open || !run?.taskId) {
      return;
    }

    if (!checkAuthGate(auth, "command center task SSE")) {
      const blocked = auth.ready && auth.status !== "authenticated";
      setConnectionState("closed");
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
      resolveApiUrl(`/api/tasks/${encodeURIComponent(run.taskId)}/events`),
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
    sourceRef.current = source;
    setConnectionState("connecting");
    setConnectionDetail("Connecting to task stream...");

    const restoreDispatch = tapMessageEvents(source, (message) => {
      const raw = typeof message.data === "string" ? message.data : String(message.data ?? "");
      const json = parseTaskJson(raw);
      const nextEvent: CommandCenterTaskEvent = {
        eventId: firstString(message.lastEventId),
        eventType: firstString(message.type) ?? "message",
        json,
        raw,
        receivedAt: Date.now(),
        summary: summarizeTaskEvent(raw, json, firstString(message.type)),
      };
      setTaskEvents((previous) => appendTaskEvent(previous, nextEvent));
      setLastEventAt(nextEvent.receivedAt);
    });

    const handleOpen = () => {
      setConnectionState("open");
      setConnectionDetail(null);
    };
    const handleError = () => {
      setConnectionState("error");
      setConnectionDetail("Task event stream disconnected.");
    };
    const handleUnauthorized = () => {
      setConnectionState("closed");
      setConnectionDetail("Unauthorized");
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
      source.close();
      if (sourceRef.current === source) {
        sourceRef.current = null;
      }
    };
  }, [auth.ready, auth.status, auth.token, open, run?.key, run?.taskId]);

  return (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
    >
      <SheetContent
        side="right"
        className="w-[min(42rem,100vw)] overflow-y-auto border-l"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
        }}
      >
        {run ? (
          <>
            <SheetHeader className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <SheetTitle className="text-base" style={{ color: "var(--text)" }}>
                  Run Detail
                </SheetTitle>
                <Badge
                  className="border"
                  style={{
                    ...connectionStyle(connectionState),
                    color: "var(--text)",
                  }}
                >
                  {connectionState}
                </Badge>
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                Last task event: {formatTimestamp(lastEventAt)}
              </div>
              {connectionDetail ? (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {connectionDetail}
                </div>
              ) : null}
            </SheetHeader>

            <div className="space-y-4 p-4">
              <Card
                className="bezel-none rounded-xl border"
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                  borderColor: "var(--panel-border)",
                }}
              >
                <CardContent className="space-y-3 p-4">
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    Identifiers
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs" style={{ color: "var(--muted)" }}>
                    <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Grouping key: {run.key}
                    </span>
                    <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Task: {run.taskId ?? "—"}
                    </span>
                    <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
                      Run: {run.runId ?? "—"}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    Task Event Stream
                  </div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    Live updates from /api/tasks/{"{task_id}"}/events
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRawJson((current) => !current)}
                >
                  {showRawJson ? "Hide Raw JSON" : "Raw JSON"}
                </Button>
              </div>

              {!run.taskId ? (
                <Card
                  className="bezel-none rounded-xl border"
                  style={{
                    background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    borderColor: "var(--panel-border)",
                  }}
                >
                  <CardContent className="p-4 text-sm" style={{ color: "var(--muted)" }}>
                    No task event stream available for this run.
                  </CardContent>
                </Card>
              ) : taskEvents.length === 0 ? (
                <Card
                  className="bezel-none rounded-xl border"
                  style={{
                    background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    borderColor: "var(--panel-border)",
                  }}
                >
                  <CardContent className="p-4 text-sm" style={{ color: "var(--muted)" }}>
                    Waiting for task events...
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {taskEvents
                    .slice()
                    .reverse()
                    .map((event) => (
                      <Card
                        key={`${event.eventId ?? event.receivedAt}:${event.eventType ?? "message"}`}
                        className="bezel-none rounded-xl border"
                        style={{
                          background:
                            "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                          borderColor: "var(--panel-border)",
                        }}
                      >
                        <CardContent className="space-y-2 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-xs font-medium" style={{ color: "var(--text)" }}>
                              {event.eventType ?? "message"}
                            </div>
                            <div className="text-xs" style={{ color: "var(--muted)" }}>
                              {formatTimestamp(event.receivedAt)}
                            </div>
                          </div>
                          <div className="text-sm" style={{ color: "var(--text)" }}>
                            {event.summary}
                          </div>
                          {showRawJson ? (
                            <pre
                              className="overflow-x-auto rounded-lg border p-3 text-xs"
                              style={{
                                borderColor: "var(--panel-border)",
                                background: "rgba(0, 0, 0, 0.14)",
                                color: "var(--text)",
                              }}
                            >
                              {event.json ? JSON.stringify(event.json, null, 2) : event.raw}
                            </pre>
                          ) : null}
                        </CardContent>
                      </Card>
                    ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
