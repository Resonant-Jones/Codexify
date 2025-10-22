/**
 * GuardianChatWithSidebar — coordinates the chat surface and the sidebar, ensuring
 * each lives inside its own glass shell while sharing data feeds for threads/projects/messages.
 */
import React, { useMemo } from "react";
import clsx from "clsx";
import GuardianChat from "@/features/chat/GuardianChat";
import Sidebar from "@/components/chat/Sidebar";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { Thread, Message } from "@/types/ui";
import api from "@/lib/api";
import { GuardianAPI } from "@/lib/guardianApi";
import { useBreakpoint } from "./useBreakpoint";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";

type PanelShellProps = React.PropsWithChildren<{
  className?: string;
  surfaceStyle?: React.CSSProperties;
  disabled?: boolean;
}>;


export default function GuardianChatWithSidebar({ guardianName, userName, prefill, onPrefillConsumed, onWorkspaceToggle }) {
  const [isSidebarVisible, setIsSidebarVisible] = React.useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false);
  const bp = useBreakpoint();
  const [threads, setThreads] = React.useState<Thread[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const { subscribe } = useLiveEvents();
  const { wallpaperUrl } = useWallpaperUrl();

  const isDesktopLayout = bp === "lg" || bp === "xl" || bp === "2xl";
  const isSidebarOpen = isDesktopLayout ? isSidebarVisible : isMobileSidebarOpen;

  const toggleSidebar = React.useCallback(() => {
    if (isDesktopLayout) {
      setIsSidebarVisible((prev) => !prev);
    } else {
      setIsMobileSidebarOpen((prev) => !prev);
    }
  }, [isDesktopLayout]);

  React.useEffect(() => {
    if (isDesktopLayout && isMobileSidebarOpen) {
      setIsMobileSidebarOpen(false);
    }
  }, [isDesktopLayout, isMobileSidebarOpen]);

  const mapThreadRecord = React.useCallback(
    (raw: any): Thread | null => {
      if (!raw) return null;
      const rawId = raw.id ?? raw.thread_id ?? raw.threadId;
      if (rawId == null) return null;
      const title = raw.title ?? raw.summary ?? "Untitled Chat";
      const last = raw.lastMessage ?? raw.last_message ?? "";
      const projectVal = raw.project_id ?? raw.projectId ?? null;
      const parentVal = raw.parent_id ?? raw.parentId ?? null;
      const archivedVal = raw.archived_at ?? raw.archivedAt ?? null;
      return {
        id: String(rawId),
        title,
        lastMessage: last || "",
        unread: 0,
        participants: [
          { id: "me", name: userName || "You" },
          { id: "bot", name: guardianName || "Guardian" },
        ],
        messages: [],
        projectId: projectVal != null ? String(projectVal) : null,
        parentId: parentVal != null ? String(parentVal) : null,
        archivedAt: archivedVal ? String(archivedVal) : null,
      };
    },
    [guardianName, userName]
  );

  const handleNewChat = React.useCallback(async () => {
    try {
      const res = await api.post("/chat/threads", {
        title: "New Chat",
        user_id: userName || "default",
        projectId: null, // placeholder for future project linkage
        personaId: null, // placeholder for persona tracking
        tags: [],        // placeholder for codex linkages
      });
      const payload = res?.data?.thread ?? {};
      const id = res?.data?.id ?? payload?.id;
      if (id == null) return null;
      const mapped = mapThreadRecord({ id, title: payload?.title ?? "New Chat", lastMessage: "" });
      if (!mapped) return null;
      setThreads((prev) => [mapped, ...prev]);
      setActiveId(mapped.id);
      return mapped;
    } catch (err) {
      console.warn("[guardian] failed to create thread", err);
      // If API fails, create a synthetic thread as fallback
      const fallback: Thread = {
        id: "temp",
        title: "New Chat",
        lastMessage: "",
        unread: 0,
        participants: [
          { id: "me", name: userName || "You" },
          { id: "bot", name: guardianName || "Guardian" },
        ],
        messages: [],
      };
      setThreads((prev) => [fallback, ...prev]);
      setActiveId("temp");
      return fallback;
    }
  }, [mapThreadRecord, userName, guardianName]);

  // ----- Thread loader (hoisted early to avoid TDZ) -----
  const loadThreads = React.useCallback(async () => {
    try {
      const res = await GuardianAPI.get("/chat/threads");
      const rawList = Array.isArray(res?.threads)
        ? res.threads
        : Array.isArray(res)
        ? res
        : [];
      if (!rawList.length) {
        await handleNewChat();
        return;
      }
      const mapped = rawList.map(mapThreadRecord).filter(Boolean);
      // Deduplicate by thread id
      const dedupedMap = new Map<string, Thread>();
      for (const thread of mapped) {
        if (thread && thread.id) dedupedMap.set(thread.id, thread);
      }
      const visible = Array.from(dedupedMap.values()).filter((t) => !t.archivedAt);
      setThreads(visible);
      setActiveId((prev) => {
        if (prev && visible.some((t) => t.id === prev)) {
          return prev;
        }
        return visible[0] ? visible[0].id : null;
      });
    } catch (err) {
      console.warn("[guardian] failed to load threads", err);
      await handleNewChat();
    }
  }, [handleNewChat, mapThreadRecord]);

  const handleBranchThread = React.useCallback(
    async (threadId: number, options?: { title?: string }) => {
      try {
        const payload = options?.title && options.title.trim().length
          ? { title: options.title.trim() }
          : {};
        const res = await api.post(`/chat/${threadId}/branch`, payload);
        const child = res?.data;
        const mapped = mapThreadRecord(child);
        if (!mapped || mapped.archivedAt) {
          return;
        }
        setThreads((prev) => {
          const filtered = prev.filter((t) => t.id !== mapped.id);
          return [mapped, ...filtered];
        });
        setActiveId(mapped.id);
        void loadThreads();
      } catch (err) {
        console.warn("[guardian] failed to branch thread", err);
      }
    },
    [mapThreadRecord, loadThreads]
  );

  const handleArchiveThread = React.useCallback(
    async (threadId: number) => {
      try {
        await api.patch(`/api/chat/${threadId}`, { archived: true });
        const idStr = String(threadId);
        setThreads((prev) => {
          const filtered = prev.filter((t) => t.id !== idStr);
          if (filtered.length === prev.length) {
            return prev;
          }
          setActiveId((current) => {
            if (current === idStr) {
              return filtered[0]?.id ?? null;
            }
            return current;
          });
          return filtered;
        });
        void loadThreads();
      } catch (err) {
        console.warn("[guardian] failed to archive thread", err);
      }
    },
    [loadThreads]
  );


  // Ensure at least one thread exists and is active, always.
  React.useEffect(() => {
    if (!threadId && !loading) {
      createThread(); // or whatever your function is called
    }
  }, [threadId, loading]); // <-- be careful to include a static dependency array

  // Guarantee at least one thread exists and is active (on mount or when threads/activeId changes)
  React.useEffect(() => {
    if ((!threads || threads.length === 0) || !activeId) {
      // If no threads or no active thread, create one and set active
      handleNewChat();
    }
  }, [threads, activeId, handleNewChat]);

  const activeThread = React.useMemo(() => {
    // Always return a usable thread object for GuardianChat
    let found = threads.find((t) => t.id === activeId) || null;
    if (found) return found;
    if (threads.length > 0) return threads[0];
    // Fallback to a synthetic blank thread
    return {
      id: "temp",
      title: "New Chat",
      lastMessage: "",
      unread: 0,
      participants: [
        { id: "me", name: userName || "You" },
        { id: "bot", name: guardianName || "Guardian" },
      ],
      messages: [],
    };
  }, [threads, activeId, userName, guardianName]);

  const handleNewChatImmediate = () => {
    void handleNewChat();
  };

  const handleSendMessage = async (text: string) => {
    if (!activeId) return;
    const threadKey = activeId;
    const numericThreadId = Number(threadKey);
    const userMsgId = String(Math.random());
    const userMsg: Message = { id: userMsgId, authorId: "me", authorName: userName, content: text, createdAt: Date.now(), status: "sending" };

    // Update thread title if it's the first user message
    setThreads((prev) =>
      prev.map((t) => {
        if (t.id === threadKey) {
          let newTitle = t.title;
          if (
            // Only update if "New Chat" and no messages yet (or only system messages)
            (t.title === "New Chat" || t.title === "Untitled Chat") &&
            (!t.messages || t.messages.length === 0)
          ) {
            // Use first ~6 words of the message
            const trimmed = text.trim().split(/\s+/).slice(0, 6).join(" ");
            newTitle = trimmed.length > 0 ? trimmed + (text.trim().split(/\s+/).length > 6 ? "…" : "") : "New Chat";
          }
          return { ...t, messages: [...t.messages, userMsg], lastMessage: text, title: newTitle };
        }
        return t;
      })
    );

    // If first message, update the thread title server-side as well
    (async () => {
      if (!Number.isFinite(numericThreadId)) return;
      try {
        // Fetch thread to see if it needs updating
        const thread = threads.find((t) => t.id === threadKey);
        if (
          thread &&
          (thread.title === "New Chat" || thread.title === "Untitled Chat") &&
          (!thread.messages || thread.messages.length === 0)
        ) {
          // Update title on server
          const trimmed = text.trim().split(/\s+/).slice(0, 6).join(" ");
          const newTitle = trimmed.length > 0 ? trimmed + (text.trim().split(/\s+/).length > 6 ? "…" : "") : "New Chat";
          await api.patch(`/chat/threads/${numericThreadId}`, { title: newTitle });
        }
        await api.post(`/chat/${numericThreadId}/messages`, { role: "user", content: text });
        try {
          await api.post("/neo/graph-message", {
            role: "user",
            content: text,
            threadId: numericThreadId,
            userName,
            guardianName,
            source: "chat",
          });
        } catch (err) {
          console.warn("[guardian] failed to graph user message", err);
        }
        setThreads((prev) =>
          prev.map((t) =>
            t.id === threadKey
              ? {
                  ...t,
                  messages: t.messages.map((m) => (m.id === userMsgId ? { ...m, status: "sent" } : m)),
                }
              : t
          )
        );
      } catch (err) {
        console.warn("[guardian] failed to persist user message", err);
      }
    })();

    const botMsgId = String(Math.random());
    const botBase: Message = { id: botMsgId, authorId: "bot", authorName: guardianName, content: "", createdAt: Date.now(), status: "delivered" };
    setThreads((prev) =>
      prev.map((t) => (t.id === threadKey ? { ...t, messages: [...t.messages, botBase] } : t))
    );

    const provider = "groq";
    const model = (import.meta as any).env?.VITE_DEFAULT_MODEL as string | undefined;

    let acc = "";
    let gotFirstToken = false;
    let finalized = false;
    let assistantPersisted = false;
    let fallbackTimer: ReturnType<typeof setTimeout>;

    const persistAssistant = async (content: string) => {
      if (assistantPersisted) return;
      if (!Number.isFinite(numericThreadId)) return;
      if (!content || !content.trim()) return;
      assistantPersisted = true;
      try {
        await api.post(`/chat/${numericThreadId}/messages`, { role: "assistant", content });
        try {
          await api.post("/neo/graph-message", {
            role: "assistant",
            content,
            threadId: numericThreadId,
            userName,
            guardianName,
            source: "chat",
          });
        } catch (err) {
          console.warn("[guardian] failed to graph assistant message", err);
        }
      } catch (err) {
        console.warn("[guardian] failed to persist assistant message", err);
      }
    };

    const finalizeAssistant = (content: string, fallbackLast?: string) => {
      if (finalized) return;
      finalized = true;
      if (fallbackTimer) clearTimeout(fallbackTimer);
      const display = content ?? "";
      const last = display || fallbackLast || text;
      setThreads((prev) =>
        prev.map((t) =>
          t.id === threadKey
            ? {
                ...t,
                messages: t.messages.map((m) => (m.id === botMsgId ? { ...m, content: display } : m)),
                lastMessage: last,
              }
            : t
        )
      );
      void persistAssistant(display);
    };

    fallbackTimer = setTimeout(async () => {
      if (gotFirstToken) return;
      try {
        const res = await GuardianAPI.chat({ prompt: text, provider, model });
        const finalText = (res as any)?.text ?? "";
        finalizeAssistant(finalText, text);
      } catch (e) {
        const errText = e instanceof Error ? e.message : String(e);
        finalizeAssistant(errText, text);
      }
    }, 2500);

    try {
      const stop = GuardianAPI.chatStream(
        { prompt: text, provider, model },
        (chunk: string) => {
          if (!gotFirstToken) {
            gotFirstToken = true;
            clearTimeout(fallbackTimer);
          }
          acc += chunk;
          setThreads((prev) =>
            prev.map((t) =>
              t.id === threadKey
                ? {
                    ...t,
                    messages: t.messages.map((m) => (m.id === botMsgId ? { ...m, content: acc } : m)),
                    lastMessage: acc || text,
                  }
                : t
            )
          );
        },
        (err?: unknown) => {
          if (!gotFirstToken && !acc.trim()) {
            if (err) console.warn("[guardian] stream ended without tokens", err);
            return;
          }
          finalizeAssistant(acc, text);
        }
      );
      void stop;
    } catch (e) {
      const errText = e instanceof Error ? e.message : String(e);
      finalizeAssistant(errText, text);
    }
  };

  // Mark active thread as read when it gains focus
  React.useEffect(() => {
    if (!activeId) return;
    setThreads((prev) => prev.map((t) => (t.id === activeId ? { ...t, unread: 0 } : t)));
  }, [activeId]);

  // React to live events to keep thread list fresh
  React.useEffect(() => {
    const offMessage = subscribe("message.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] message.created", payload);
      const rawId = payload?.thread_id ?? payload?.threadId ?? payload?.id;
      if (rawId == null) {
        return;
      }
      const threadId = String(rawId);
      const content =
        typeof payload?.content === "string"
          ? payload.content
          : typeof payload?.message === "string"
          ? payload.message
          : "";
      setThreads((prev) => {
        if (!prev.length) {
          void loadThreads();
          return prev;
        }
        const idx = prev.findIndex((t) => t.id === threadId);
        if (idx === -1) {
          void loadThreads();
          return prev;
        }
        const target = prev[idx];
        const unread = threadId === activeId ? 0 : (target.unread ?? 0) + 1;
        const updated: Thread = {
          ...target,
          lastMessage: content || target.lastMessage,
          unread,
        };
        const next = prev.slice();
        next.splice(idx, 1);
        next.unshift(updated);
        return next;
      });
    });

    const offThreadUpdated = subscribe("thread.updated", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] thread.updated", payload);
      void loadThreads();
    });

    const offThreadCreated = subscribe("thread.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] thread.created", payload);
      void loadThreads();
    });

    const offThreadBranched = subscribe("thread.branch", (event) => {
      const payload = (event.data as any)?.child ?? event.data;
      console.info("[live] thread.branch", payload);
      void loadThreads();
    });

    const offThreadArchived = subscribe("thread.archived", (event) => {
      const payload = (event.data as any)?.thread ?? event.data;
      console.info("[live] thread.archived", payload);
      void loadThreads();
    });

    return () => {
      offMessage();
      offThreadUpdated();
      offThreadCreated();
      offThreadBranched();
      offThreadArchived();
    };
  }, [subscribe, loadThreads, activeId]);

  const sidebarSurfaceStyle = useMemo(
    () => ({
      ["--panel-bg" as any]: "color-mix(in oklab, var(--panel-bg) 98%, rgba(8,12,20,0.96))",
      ["--panel-border" as any]: "color-mix(in oklab, var(--panel-border) 85%, transparent)",
    }),
    []
  );
  const chatSurfaceStyle = useMemo(
    () => ({
      ["--panel-bg" as any]: "color-mix(in oklab, var(--panel-bg) 98%, rgba(8,12,20,0.96))",
      ["--panel-border" as any]: "color-mix(in oklab, var(--panel-border) 85%, transparent)",
    }),
    []
  );

  const chatDisabled = !isDesktopLayout && isSidebarOpen;

  const sidebarWrapperClass = isDesktopLayout
    ? "relative flex h-full min-h-0 shrink-0 basis-[clamp(300px,24vw,360px)]"
    : "absolute inset-0 z-30 flex h-full w-full";

  const PanelShell: React.FC<PanelShellProps> = ({ className, surfaceStyle, disabled, children }) => {
    const panelStyle: React.CSSProperties = {
      opacity: disabled ? 0.35 : 1,
      pointerEvents: disabled ? "none" : undefined,
      ...(surfaceStyle ?? {}),
    };
    return (
      <FrameCard
        fill
        refractiveFallback
        shimmerMode="subtle"
        liquidBezelWidth={3}
        className={clsx("flex flex-col h-full w-full box-border", className)}
        hoverPop={!disabled}
        ariaLabel={disabled ? "panel disabled" : undefined}
        style={panelStyle}
      >
        {children}
      </FrameCard>
    );
  };

  return (
    <div className="flex h-full w-full box-border overflow-hidden">
      <div
        className="relative grid h-full w-[calc(100%-12px)] max-w-[1500px] box-border items-stretch mx-auto overflow-hidden"
        style={{
          gridTemplateColumns: "clamp(300px, 24vw, 360px) 6px minmax(0, 1fr)",
          gap: "0px",
          padding: "6px",
          boxSizing: "border-box",
        }}
      >
        {/* Sidebar */}
        {isSidebarOpen && (
          <>
            {!isDesktopLayout && (
              <button
                type="button"
                aria-label="Hide sidebar"
                className="absolute inset-0 z-20 bg-black/45"
                onClick={toggleSidebar}
              />
            )}
            <div
              className={clsx(
                "h-full w-full overflow-hidden box-border",
                sidebarWrapperClass && isDesktopLayout ? undefined : undefined
              )}
              style={{
                gridColumn: "1",
                gridRow: "1",
                zIndex: isDesktopLayout ? undefined : 30,
                position: isDesktopLayout ? "relative" : "absolute",
                inset: !isDesktopLayout ? 0 : undefined,
              }}
            >
              <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--card-radius)] pointer-events-none">
                <RefractiveGlassCard
                  wallpaperUrl={wallpaperUrl}
                  className="h-full w-full rounded-[var(--card-radius)]"
                  style={{ background: "transparent", border: "none" }}
                  intensity={0.006}
                  aberration={0}
                />
              </div>
              <div
                data-layer="panel-shell"
                className="flex h-full w-full min-h-0 min-w-0 flex-col box-border"
              >
                <PanelShell surfaceStyle={sidebarSurfaceStyle}>
                  <Sidebar
                    threads={threads}
                    activeId={activeId}
                    onSelect={setActiveId}
                    onNewChat={handleNewChatImmediate}
                  />
                </PanelShell>
              </div>
            </div>
            {/* Vertical Divider */}
            <div
              style={{
                gridColumn: "2",
                gridRow: "1",
                background: "var(--panel-border,rgba(80,80,120,0.14))",
                width: "6px",
                minWidth: "6px",
                maxWidth: "6px",
                height: "100%",
                alignSelf: "stretch",
                pointerEvents: "none",
              }}
            />
          </>
        )}
        {/* Chat Panel */}
        <div
          className="h-full w-full overflow-hidden box-border"
          style={{
            gridColumn: isSidebarOpen ? 3 : "1 / span 3",
            gridRow: "1",
          }}
        >
          <PanelShell
            className="h-full w-full overflow-hidden box-border"
            surfaceStyle={chatSurfaceStyle}
            disabled={chatDisabled}
          >
            <GuardianChat
              guardianName={guardianName}
              userName={userName}
              prefill={prefill}
              onPrefillConsumed={onPrefillConsumed}
              onWorkspaceToggle={onWorkspaceToggle}
              activeThread={activeThread}
              onSendMessage={handleSendMessage}
              onNewChat={handleNewChatImmediate}
              onBranchThread={handleBranchThread}
              onArchiveThread={handleArchiveThread}
              onSidebarToggle={toggleSidebar}
              bare
            />
          </PanelShell>
        </div>
      </div>
    </div>
  );
}
