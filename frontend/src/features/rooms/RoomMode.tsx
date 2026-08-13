import { DoorOpen, LockKeyhole, Users } from "lucide-react";
import React, { useMemo } from "react";

import FrameCard from "@/components/surface/FrameCard";
import { Button } from "@/components/ui/button";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
import ChatView from "@/features/chat/ChatView";
import type {
  ChatMessage,
  CompletionState,
} from "@/features/chat/useChat";
import { Composer } from "@/features/guardian/components/Composer";
import useHostedRoom from "@/features/rooms/useHostedRoom";

const IDLE_COMPLETION_STATE: CompletionState = {
  isCompleting: false,
  activeTaskId: null,
  activeThreadId: null,
  startedAt: null,
  requestState: null,
};

type RoomModeProps = {
  roomId: string;
  onLeave: () => void;
};

function RoomStateCard({
  title,
  detail,
  onLeave,
  onRetry,
}: {
  title: string;
  detail: string;
  onLeave: () => void;
  onRetry?: () => void;
}) {
  return (
    <FrameCard
      fill
      refractiveFallback
      shimmerMode="subtle"
      className="flex min-h-0 w-full flex-col items-center justify-center gap-[var(--shell-gap)] overflow-hidden text-center"
      data-testid="room-mode-state"
    >
      <div className="max-w-md space-y-2 px-[var(--card-pad)]">
        <h1 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
          {title}
        </h1>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          {detail}
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {onRetry ? (
          <Button type="button" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
        <Button type="button" variant="outline" onClick={onLeave}>
          Return to Guardian
        </Button>
      </div>
    </FrameCard>
  );
}

export default function RoomMode({ roomId, onLeave }: RoomModeProps) {
  const {
    room,
    messages,
    loadState,
    loadError,
    postError,
    isPosting,
    postHumanMessage,
    reload,
  } = useHostedRoom(roomId);
  const mobileShellProfile = useMobileShellProfile();

  const chatMessages = useMemo<ChatMessage[]>(() => {
    if (!room) return [];
    return messages.map((message) => ({
      id: message.id,
      thread_id: room.backing_thread_id,
      role: message.role,
      content: message.content,
      created_at: message.created_at,
      sender: message.sender,
    }));
  }, [messages, room]);

  if (loadState === "loading") {
    return (
      <RoomStateCard
        title="Loading Room"
        detail="Fetching the authorized Room and its canonical conversation."
        onLeave={onLeave}
      />
    );
  }

  if (loadState === "unavailable") {
    return (
      <RoomStateCard
        title="Room unavailable"
        detail="This Room cannot be opened in the current account or runtime posture."
        onLeave={onLeave}
      />
    );
  }

  if (loadState === "error" || !room) {
    return (
      <RoomStateCard
        title="Room could not be loaded"
        detail={loadError ?? "Try again or return to Guardian."}
        onLeave={onLeave}
        onRetry={() => void reload()}
      />
    );
  }

  const activeParticipants = room.participants.filter(
    (participant) => participant.state === "active"
  );
  const roomClosed = room.status === "closed";

  return (
    <div
      className="h-full w-full min-h-0 min-w-0"
      data-active-view="room"
      data-view-family="room"
      data-room-id={room.id}
    >
      <FrameCard
        fill
        refractiveFallback
        shimmerMode="subtle"
        className="flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden p-0"
        ariaLabel={`Shared Room: ${room.title}`}
        data-testid="room-mode"
      >
        <header
          className="flex shrink-0 flex-wrap items-start justify-between gap-[var(--shell-gap)] border-b px-[var(--card-pad)] py-[var(--card-pad)]"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.12em]"
                style={{
                  borderColor: "var(--chip-border)",
                  background: "var(--chip-bg)",
                  color: "var(--muted)",
                }}
              >
                {roomClosed ? (
                  <LockKeyhole className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <Users className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {roomClosed ? "Closed Room" : "Shared Room"}
              </span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                Owner view
              </span>
            </div>
            <div className="min-w-0">
              <h1
                className="break-words text-xl font-semibold tracking-[-0.02em] sm:text-2xl"
                style={{ color: "var(--text)" }}
              >
                {room.title}
              </h1>
              <p
                className="mt-1 break-words text-sm leading-5"
                style={{ color: "var(--muted)" }}
                aria-label="Active Room participants"
              >
                {activeParticipants.length > 0
                  ? activeParticipants
                      .map((participant) => participant.display_name)
                      .join(" · ")
                  : "No active participants"}
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            className="min-h-11 shrink-0 gap-2"
            onClick={onLeave}
            aria-label="Leave Room and return to Guardian"
          >
            <DoorOpen className="h-4 w-4" aria-hidden="true" />
            <span>Leave Room</span>
          </Button>
        </header>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {roomClosed ? (
            <div
              className="flex min-h-0 flex-1 items-center justify-center px-[var(--card-pad)] text-center"
              role="status"
            >
              <div className="max-w-md space-y-2">
                <p className="font-medium" style={{ color: "var(--text)" }}>
                  This Room is closed
                </p>
                <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
                  New messages are disabled. The current owner API does not expose
                  the transcript after Room closure.
                </p>
              </div>
            </div>
          ) : (
            <ChatView
              threadId={room.backing_thread_id}
              guardianName="Guardian"
              messages={chatMessages}
              loading={false}
              error={null}
              hasMore={false}
              completionState={IDLE_COMPLETION_STATE}
              endCompletion={() => undefined}
              showHumanAuthorNames
              className="min-h-0 flex-1"
            />
          )}
        </div>

        <div
          className="shrink-0 border-t px-[var(--card-pad)] py-[var(--card-pad)]"
          style={{ borderColor: "var(--panel-border)" }}
        >
          {postError ? (
            <div
              className="mb-2 rounded-[var(--radius-micro)] border px-3 py-2 text-sm"
              role="alert"
              style={{
                borderColor: "var(--danger-border, var(--panel-border))",
                background: "var(--danger-surface, var(--panel-bg))",
                color: "var(--danger-text, var(--text))",
              }}
            >
              {postError}
            </div>
          ) : null}
          <div
            data-room-composer="human-message-only"
          >
            <style>{`
              [data-room-composer="human-message-only"] [data-testid="composer-controls-strip"] {
                display: none;
              }
            `}</style>
            <Composer
              onSend={async (content, options) => {
                if (options?.slashIntent || options?.executionMode === "coding") {
                  throw new Error(
                    "Commands and Coding Loop dispatch are unavailable in Room Mode."
                  );
                }
                await postHumanMessage(content);
              }}
              threadId={room.backing_thread_id}
              draftScopeKey={`hosted-room:${room.id}`}
              isSending={isPosting || roomClosed}
              compactMobile={mobileShellProfile.active}
            />
          </div>
        </div>
      </FrameCard>
    </div>
  );
}
