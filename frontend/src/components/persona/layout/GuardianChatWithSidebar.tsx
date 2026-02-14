/**
 * GuardianChatWithSidebar — coordinates the chat surface and the sidebar, ensuring
 * each lives inside its own glass shell while sharing data feeds for threads/projects/messages.
 */
import React, { useMemo } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";
import GuardianChat from "@/features/chat/GuardianChat";
import SidebarRoot from "@/components/sidebar/SidebarRoot";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { Thread, Message } from "@/types/ui";
import api from "@/lib/api";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import useImprintZero from "@/imprint/useImprintZero";
import ImprintZeroToast from "@/imprint/ImprintZeroToast";
import { RedisSessionStateStore } from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";
import {
  DEFAULT_MODEL_ID,
  type SessionState,
  type TabId,
} from "@/state/session/types";

type PanelShellProps = React.PropsWithChildren<{
  className?: string;
  surfaceStyle?: React.CSSProperties;
  disabled?: boolean;
}>;

const sameThreadSnapshot = (a: Thread, b: Thread): boolean => {
  return a.id === b.id
    && a.title === b.title
    && a.lastMessage === b.lastMessage
    && (a.unread ?? 0) === (b.unread ?? 0)
    && (a.projectId ?? null) === (b.projectId ?? null)
    && (a.parentId ?? null) === (b.parentId ?? null)
    && (a.archivedAt ?? null) === (b.archivedAt ?? null);
};

const DEVICE_ID_STORAGE_KEY = "cfy.deviceId";

function getOrCreateDeviceId(): string {
  if (typeof window === "undefined") return "server-device";
  const existing = window.localStorage.getItem(DEVICE_ID_STORAGE_KEY);
  if (existing && existing.trim()) return existing.trim();
  const generated =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(DEVICE_ID_STORAGE_KEY, generated);
  return generated;
}


export default function GuardianChatWithSidebar({ guardianName, userName, prefill, onPrefillConsumed, onWorkspaceToggle }) {
  const [isSidebarVisible, setIsSidebarVisible] = React.useState(() => {
    if (typeof window === "undefined") return true;
    const stored = localStorage.getItem("cfy.sidebarVisible");
    return stored === null ? true : stored === "true";
  });
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false);
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = window.localStorage.getItem("cfy.lastProjectId");
    if (!stored || stored === "null") return null;
    return stored;
  });

  // Persist sidebar visibility preference
  React.useEffect(() => {
    try {
      localStorage.setItem("cfy.sidebarVisible", String(isSidebarVisible));
    } catch { /* ignore */ }
  }, [isSidebarVisible]);
  const [showWorkspacePanel, setShowWorkspacePanel] = React.useState(false);
  const [isDesktopLayout, setIsDesktopLayout] = React.useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
    return window.matchMedia("(min-width: 1024px)").matches;
  });
  const [threads, setThreads] = React.useState<Thread[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [threadsLoaded, setThreadsLoaded] = React.useState(false);
  const [sessionSpine, setSessionSpine] = React.useState<SessionSpine | null>(null);
  const [sessionState, setSessionState] = React.useState<SessionState | null>(null);
  const [sessionReady, setSessionReady] = React.useState(false);
  const { subscribe } = useLiveEvents({ passive: true });
  const { wallpaperUrl } = useWallpaperUrl();
  const imprintZero = useImprintZero();

  const resolveRouteThreadId = React.useCallback((): string | null => {
    if (typeof window === "undefined") return null;
    const match = window.location.pathname.match(/\/chat\/(\d+)/);
    if (match && match[1]) return match[1];
    return null;
  }, []);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    let mounted = true;
    const store = new RedisSessionStateStore();
    const spine = new SessionSpine({
      userId: (userName || "default").trim() || "default",
      deviceId: getOrCreateDeviceId(),
      store,
      defaultModelId: DEFAULT_MODEL_ID,
    });

    const unsubscribe = spine.subscribe((next) => {
      if (!mounted) return;
      setSessionState(next);
    });

    setSessionSpine(spine);
    void spine
      .hydrate({
        threadId: resolveRouteThreadId() ?? undefined,
        modelId: DEFAULT_MODEL_ID,
      })
      .finally(() => {
        if (mounted) setSessionReady(true);
      });

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, [resolveRouteThreadId, userName]);

  const activeSessionTab = React.useMemo(() => {
    if (!sessionState) return null;
    return (
      sessionState.tabs.find((tab) => tab.tabId === sessionState.activeTabId) ??
      null
    );
  }, [sessionState]);
  const activeSessionTabId = activeSessionTab?.tabId ?? null;
  const activeSessionModelId = activeSessionTab?.modelId ?? DEFAULT_MODEL_ID;
  const activeSessionDraft =
    activeSessionTabId && sessionState?.drafts
      ? sessionState.drafts[activeSessionTabId] ?? ""
      : "";

  React.useEffect(() => {
    if (!sessionReady || !activeSessionTab) return;
    const targetThreadId = activeSessionTab.threadId ?? null;
    if (targetThreadId === activeId) return;
    setActiveId(targetThreadId);
    if (typeof window !== "undefined") {
      if (targetThreadId) {
        window.history.pushState({}, "", `/chat/${targetThreadId}`);
      } else {
        window.history.pushState({}, "", "/chat");
      }
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }, [activeId, activeSessionTab, sessionReady]);

  React.useEffect(() => {
    if (!sessionReady || !sessionSpine || !activeSessionTabId) return;
    if (!activeId) return;
    const activeThread = threads.find((thread) => thread.id === activeId);
    sessionSpine.tabSetThread(
      activeSessionTabId,
      activeId,
      activeThread?.title || undefined
    );
  }, [activeId, activeSessionTabId, sessionReady, sessionSpine, threads]);
  // Workspace panel toggle event listener
  React.useEffect(() => {
    const onToggleWorkspace = () => {
      setShowWorkspacePanel(prev => !prev);
    };
    window.addEventListener('cfy:workspace:toggleWorkspacePanel', onToggleWorkspace);
    return () => window.removeEventListener('cfy:workspace:toggleWorkspacePanel', onToggleWorkspace);
  }, []);

  React.useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    const mq = window.matchMedia("(min-width: 1024px)");
    const handleChange = (event?: MediaQueryListEvent) => {
      if (event && typeof event.matches === "boolean") {
        setIsDesktopLayout(event.matches);
        return;
      }
      setIsDesktopLayout(mq.matches);
    };
    handleChange();
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", handleChange);
      return () => {
        mq.removeEventListener("change", handleChange);
      };
    }
    if (typeof mq.addListener === "function") {
      mq.addListener(handleChange);
      return () => {
        mq.removeListener(handleChange);
      };
    }
    return undefined;
  }, []);

  const isSidebarOpen = isDesktopLayout ? isSidebarVisible : isMobileSidebarOpen;
  const isMobileOverlayActive = !isDesktopLayout && isSidebarOpen;

  // Portal target: mount inside the themed app shell so the overlay inherits
  // the same CSS variables and theme context as the rest of the UI.
  const portalTarget = React.useMemo(() => {
    if (typeof document === "undefined") return null;
    return (
      document.getElementById("cfy-portal-root") ??
      document.getElementById("app") ??
      document.getElementById("root") ??
      document.body ??
      document.documentElement
    );
  }, []);


  const setSidebarOpen = React.useCallback(
    (next: boolean) => {
      if (isDesktopLayout) {
        setIsSidebarVisible(next);
      } else {
        setIsMobileSidebarOpen(next);
      }
    },
    [isDesktopLayout]
  );

  const closeSidebar = React.useCallback(() => {
    setSidebarOpen(false);
  }, [setSidebarOpen]);

  const toggleSidebar = React.useCallback(() => {
    setSidebarOpen(!isSidebarOpen);
  }, [isSidebarOpen, setSidebarOpen]);

  React.useEffect(() => {
    if (isDesktopLayout && isMobileSidebarOpen) {
      setIsMobileSidebarOpen(false);
    }
  }, [isDesktopLayout, isMobileSidebarOpen]);

  React.useEffect(() => {
    if (!isMobileOverlayActive || typeof document === "undefined") return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileOverlayActive]);

  React.useEffect(() => {
    if (!isMobileOverlayActive || typeof window === "undefined") return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMobileOverlayActive, setSidebarOpen]);

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
      const metadata = raw.metadata ?? raw.meta ?? null;
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
        metadata: metadata,
      };
    },
    [guardianName, userName]
  );

  const handleNewChat = React.useCallback(async () => {
    try {
      const res = await api.post("/chat/threads", {
        title: "New Chat",
        user_id: userName || "default",
        projectId: null, // TODO: future project linkage
        personaId: null, // placeholder for persona tracking
        tags: [],        // placeholder for codex linkages
      });
      const payload = res?.data?.thread ?? {};
      const id = res?.data?.id ?? payload?.id;

      if (id == null) return null;

      const idStr = String(id);
      const mapped = mapThreadRecord({ id, title: payload?.title ?? "New Chat", lastMessage: "" });

      if (!mapped) return null;

      setThreads((prev) => [mapped, ...prev]);
      setActiveId(idStr);

      // Navigate
      if (typeof window !== "undefined") {
        window.history.pushState({}, "", `/chat/${idStr}`);
        // Dispatch refresh for sidebar
        window.dispatchEvent(new CustomEvent("cfy:threads:refresh", {
          detail: { kind: "create", id: idStr }
        }));
      }

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

  const handleSessionTabOpen = React.useCallback(() => {
    if (!sessionSpine) {
      void handleNewChat();
      return;
    }
    const current = threads.find((thread) => thread.id === activeId);
    sessionSpine.tabOpen(activeId ?? undefined, current?.title);
  }, [activeId, handleNewChat, sessionSpine, threads]);

  const handleSessionTabActivate = React.useCallback((tabId: TabId) => {
    sessionSpine?.tabActivate(tabId);
  }, [sessionSpine]);

  const handleSessionTabClose = React.useCallback((tabId: TabId) => {
    sessionSpine?.tabClose(tabId);
  }, [sessionSpine]);

  const handleSessionModelChange = React.useCallback((modelId: string) => {
    if (!sessionSpine || !activeSessionTabId) return;
    sessionSpine.tabSetModel(activeSessionTabId, modelId);
  }, [activeSessionTabId, sessionSpine]);

  const handleSessionDraftChange = React.useCallback((text: string) => {
    if (!sessionSpine || !activeSessionTabId) return;
    sessionSpine.tabSetDraft(activeSessionTabId, text);
  }, [activeSessionTabId, sessionSpine]);

  // Heuristic prompt detector
  function isLikelyPrompt(text: string): boolean {
    if (!text) return false;
    const v = text.trim();
    if (!v) return false;
    const head = v.slice(0, 48).toLowerCase();
    if (v.startsWith("/") || /^generate\b/i.test(v)) return true;
    if (v.startsWith("[image-derived]")) return true;
    const patterns = [
      "a photo of",
      "cinematic lighting",
      "bokeh",
      "portrait of",
      "octane render",
      "ultra-detailed",
      "dslr",
      "35mm",
      "highly detailed",
    ];
    return patterns.some((p) => head.includes(p));
  }

  async function embedPrompt(text: string, source: string) {
    try {
      const resp = await fetch('/embed', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, tags: ['prompt'], metadata: { source } }),
      });
      if (!resp.ok) {
        throw new Error(`embed failed: ${resp.status}`);
      }
      // Also append to local prompt cache for prompt library UI
      try {
        const key = 'cfy.prompts';
        const raw = localStorage.getItem(key);
        const arr = raw ? JSON.parse(raw) : [];
        const next = [{ text, ts: Date.now() }, ...Array.isArray(arr) ? arr : []].slice(0, 200);
        localStorage.setItem(key, JSON.stringify(next));
      } catch {}
      try {
        window.dispatchEvent(new CustomEvent('cfy:toast', { detail: { kind: 'success', message: 'Saved to Prompt Library' } }));
      } catch {}
    } catch (err) {
      console.warn('[prompt] embed failed', err);
      try {
        window.dispatchEvent(new CustomEvent('cfy:toast', { detail: { kind: 'error', message: 'Prompt embedding failed' } }));
      } catch {}
    }
  }

  // ----- Thread loader (hoisted early to avoid TDZ) -----
  const loadThreads = React.useCallback(async () => {
    try {
      const res = await api.get("/chat/threads");
      const data = res?.data;
      const rawList = Array.isArray(data?.threads)
        ? data.threads
        : Array.isArray(data)
        ? data
        : [];

      // If empty, create new chat
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

      // Only set activeId if we don't have one, or if the URL dictates it
      setActiveId((prev) => {
        const routeId = resolveRouteThreadId();
        if (routeId && visible.some((t) => t.id === routeId)) {
          return routeId;
        }
        // If we have a previous ID and it's still in the list, KEEP IT
        if (prev && visible.some((t) => t.id === prev)) {
          return prev;
        }
        // Otherwise default to first
        return visible[0] ? visible[0].id : null;
      });
    } catch (err) {
      console.warn("[guardian] failed to load threads", err);
      // Only create new chat if we really have nothing
      if (threads.length === 0) {
        await handleNewChat();
      }
    } finally {
      setThreadsLoaded(true);
    }
  }, [handleNewChat, mapThreadRecord, resolveRouteThreadId]); // Remove threads dependency to avoid loops

  React.useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onThreadsRefresh = (event: Event) => {
      const detail = (event as CustomEvent)?.detail ?? {};
      const kind = detail?.kind ?? detail?.type;
      if (kind !== "refresh" && kind !== "import") return;
      void loadThreads();
    };
    window.addEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
    return () => window.removeEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
  }, [loadThreads]);

  // Initial load only
  React.useEffect(() => {
    void loadThreads();
  }, [loadThreads]);

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
        // No need to reload all threads
      } catch (err) {
        console.warn("[guardian] failed to branch thread", err);
      }
    },
    [mapThreadRecord]
  );

  const handleArchiveThread = React.useCallback(
    async (threadId: number) => {
      try {
        await api.patch(`/chat/${threadId}`, { archived: true });
        const idStr = String(threadId);
        setThreads((prev) => {
          const filtered = prev.filter((t) => t.id !== idStr);
          if (filtered.length === prev.length) {
            return prev;
          }
          // If we archived the active thread, switch to another
          if (activeId === idStr) {
             const next = filtered[0]?.id ?? null;
             setActiveId(next);
             if (next && typeof window !== "undefined") {
                window.history.pushState({}, "", `/chat/${next}`);
             }
          }
          return filtered;
        });
      } catch (err) {
        console.warn("[guardian] failed to archive thread", err);
      }
    },
    [activeId]
  );

  const handleSelectThread = React.useCallback((id: string) => {
    setActiveId(id);
    if (sessionSpine && activeSessionTabId) {
      const selected = threads.find((thread) => thread.id === id);
      sessionSpine.tabSetThread(activeSessionTabId, id, selected?.title);
    }
    if (typeof window !== "undefined") {
      window.history.pushState({}, "", `/chat/${id}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }, [activeSessionTabId, sessionSpine, threads]);


  // Guarantee at least one thread exists and is active (on mount or when threads/activeId changes)
  React.useEffect(() => {
    if (!threadsLoaded) return;
    if (!threads || threads.length === 0) {
      // If no threads or no active thread after load, create one and set active
      void handleNewChat();
      return;
    }
    if (!activeId) {
      setActiveId(threads[0]?.id ?? null);
    }
  }, [threadsLoaded, threads.length, activeId, handleNewChat]); // Depend on length, not array identity

  React.useEffect(() => {
    const onPopstate = () => {
      const routeId = resolveRouteThreadId();
      if (!routeId) return;
      setActiveId((prev) => (prev === routeId ? prev : routeId));
      if (threadsLoaded && !threads.some((t) => t.id === routeId)) {
        void loadThreads();
      }
    };
    if (typeof window !== "undefined") {
      window.addEventListener("popstate", onPopstate);
      return () => window.removeEventListener("popstate", onPopstate);
    }
  }, [loadThreads, resolveRouteThreadId, threads, threadsLoaded]);

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
    const userMsg: Message = {
      id: userMsgId,
      authorId: "me",
      authorName: userName,
      content: text,
      createdAt: Date.now(),
      status: "sending",
    };

    // Optimistic local update and title refinement for first message
    setThreads((prev) =>
      prev.map((t) => {
        if (t.id !== threadKey) return t;
        let newTitle = t.title;
        if (
          (t.title === "New Chat" || t.title === "Untitled Chat") &&
          (!t.messages || t.messages.length === 0)
        ) {
          const words = text.trim().split(/\s+/);
          const head = words.slice(0, 6).join(" ");
          newTitle = head.length > 0 ? head + (words.length > 6 ? "…" : "") : "New Chat";
        }
        return {
          ...t,
          messages: [...t.messages, userMsg],
          lastMessage: text,
          title: newTitle,
        };
      })
    );

    if (!Number.isFinite(numericThreadId)) return;

    try {
      // Optionally update the thread title on the server if this is the first message
      const thread = threads.find((t) => t.id === threadKey);
      if (
        thread &&
        (thread.title === "New Chat" || thread.title === "Untitled Chat") &&
        (!thread.messages || thread.messages.length === 0)
      ) {
        const words = text.trim().split(/\s+/);
        const head = words.slice(0, 6).join(" ");
        const newTitle = head.length > 0 ? head + (words.length > 6 ? "…" : "") : "New Chat";
        await api.patch(`/chat/threads/${numericThreadId}`, { title: newTitle });
      }

      await api.post(`/chat/${numericThreadId}/messages`, {
        role: "user",
        content: text,
        metadata: isLikelyPrompt(text) ? { type: "prompt" } : undefined,
      });

      if (isLikelyPrompt(text)) {
        void embedPrompt(text, "chat");
      }

      // Gated graph hook
      const ENABLE_NEO_GRAPH = false;
      if (ENABLE_NEO_GRAPH) {
        try {
          await api.post("/neo/graph-message", {
            role: "user",
            content: text,
            threadId: numericThreadId,
            userName,
            guardianName,
            source: "chat",
            tags: isLikelyPrompt(text) ? ["prompt"] : [],
          });
        } catch (err) {
          console.warn("[guardian] failed to graph user message", err);
        }
      }

      // Mark our optimistic message as sent
      setThreads((prev) =>
        prev.map((t) =>
          t.id === threadKey
            ? {
                ...t,
                messages: t.messages.map((m) =>
                  m.id === userMsgId ? { ...m, status: "sent" } : m
                ),
              }
            : t
        )
      );
    } catch (err) {
      console.warn("[guardian] failed to persist user message", err);
      // Surface per-thread turn lock errors as a friendly retry prompt.
      const status = (err as any)?.response?.status;
      const errorCode = (err as any)?.response?.data?.error;
      const message =
        status === 429 || errorCode === "turn_in_flight"
          ? "One moment—finish the current reply first."
          : "Failed to send message.";
      throw new Error(message);
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
          // If we have no threads, we might need to load them
          void loadThreads();
          return prev;
        }
        const idx = prev.findIndex((t) => t.id === threadId);
        if (idx === -1) {
          // New thread we don't know about? Load to be safe, or ignore
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
        const shouldMove = idx > 0;
        if (!shouldMove && sameThreadSnapshot(target, updated)) {
          return prev;
        }
        const next = prev.slice();
        next.splice(idx, 1);
        next.unshift(updated);
        return next;
      });
    });

    const offThreadUpdated = subscribe("thread.updated", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] thread.updated", payload);
      // Update local state instead of full reload
      const threadPayload = payload?.thread ?? payload;
      const tid = threadPayload?.id ?? threadPayload?.thread_id ?? payload?.thread_id;
      if (!tid) return;
      const idStr = String(tid);
      setThreads((prev) => {
        let touched = false;
        const next = prev.map((t) => {
          if (t.id !== idStr) return t;
          const updated = {
            ...t,
            title: threadPayload?.title ?? t.title,
            projectId: threadPayload?.project_id ?? threadPayload?.projectId ?? t.projectId,
            archivedAt: threadPayload?.archived_at ?? threadPayload?.archivedAt ?? t.archivedAt,
          };
          if (!sameThreadSnapshot(t, updated)) {
            touched = true;
          }
          return updated;
        });
        return touched ? next : prev;
      });
    });

    const offThreadCreated = subscribe("thread.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] thread.created", payload);
      // Insert new thread at top
      const mapped = mapThreadRecord(payload);
      if (mapped) {
          setThreads(prev => {
              if (prev.some(t => t.id === mapped.id)) return prev;
              return [mapped, ...prev];
          });
      } else {
          void loadThreads();
      }
    });

    const offThreadBranched = subscribe("thread.branch", (event) => {
      const payload = (event.data as any)?.child ?? event.data;
      console.info("[live] thread.branch", payload);
      const mapped = mapThreadRecord(payload);
      if (mapped) {
          setThreads((prev) => {
            if (prev.some((t) => t.id === mapped.id)) return prev;
            return [mapped, ...prev];
          });
      } else {
          void loadThreads();
      }
    });

    const offThreadArchived = subscribe("thread.archived", (event) => {
      const payload = (event.data as any)?.thread ?? event.data;
      console.info("[live] thread.archived", payload);
      const tid = payload?.id;
      if (tid) {
          setThreads((prev) => {
            const next = prev.filter((t) => t.id !== String(tid));
            return next.length === prev.length ? prev : next;
          });
      } else {
          void loadThreads();
      }
    });

    return () => {
      offMessage();
      offThreadUpdated();
      offThreadCreated();
      offThreadBranched();
      offThreadArchived();
    };
  }, [subscribe, loadThreads, activeId, mapThreadRecord]);

  const sidebarSurfaceStyle = useMemo(
    () => ({
      background: "var(--panel-bg)",
      borderRight: "1px solid var(--panel-border)",
    }),
    []
  );
  const chatSurfaceStyle = useMemo(
    () => ({
      background: "var(--panel-bg)",
    }),
    []
  );

  const chatDisabled = !isDesktopLayout && isSidebarOpen;

  const sidebarWrapperClass = "relative flex h-full min-h-0 shrink-0 basis-[clamp(300px,24vw,360px)]";
  const stopDrawerEvent = React.useCallback((event: React.SyntheticEvent) => {
    event.stopPropagation();
  }, []);

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
        className={clsx("flex flex-col h-full w-full min-h-0 box-border", className)}
        hoverPop={!disabled}
        ariaLabel={disabled ? "panel disabled" : undefined}
        style={{
          borderRadius: "var(--card-radius)",
          border: "1px solid var(--panel-border)",
          ...panelStyle,
        }}
      >
        {children}
      </FrameCard>
    );
  };

  const mobileOverlay = isMobileOverlayActive && portalTarget
    ? createPortal(
        <div
          data-testid="mobile-sidebar-overlay"
          style={{ position: "fixed", inset: 0, zIndex: 10000 }}
        >
          <div
            data-testid="mobile-sidebar-scrim"
            style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.45)" }}
            role="button"
            tabIndex={0}
            onClick={closeSidebar}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                closeSidebar();
              }
            }}
          />
          <aside
            data-testid="mobile-sidebar-drawer"
            className="h-full overflow-hidden"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              width: "min(360px, 90vw)",
              zIndex: 10001,
            }}
            onPointerDown={stopDrawerEvent}
            onClick={stopDrawerEvent}
          >
            <div className="relative h-full w-full min-h-0 min-w-0 box-border">
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
                  <SidebarRoot
                    threads={threads}
                    activeId={activeId}
                    onSelect={handleSelectThread}
                    onNewChat={handleNewChatImmediate}
                    projectId={selectedProjectId}
                    onProjectChange={setSelectedProjectId}
                  />
                </PanelShell>
              </div>
            </div>
          </aside>
        </div>,
        portalTarget
      )
    : null;

  return (
    <>
      {mobileOverlay}
      <div
        className="relative grid h-full w-full max-w-[1500px] min-h-0 overflow-hidden box-border items-stretch mx-auto"
        style={{
          gridTemplateColumns: isDesktopLayout && isSidebarOpen
            ? "clamp(300px, 24vw, 360px) minmax(0, 1fr)"
            : "1fr",
          gap: "8px",
          padding: "0px",
          boxSizing: "border-box",
          transition: "grid-template-columns 0.2s ease-out",
        }}
      >
        {imprintZero.proposal && (
          <ImprintZeroToast
            proposal={imprintZero.proposal}
            onAccept={(override) => imprintZero.accept(override)}
            onReject={() => imprintZero.reject()}
            onEditAccept={(text) => imprintZero.accept(text)}
          />
        )}

        {/* Sidebar */}
        {isSidebarOpen && isDesktopLayout && (
          <div
            className={clsx("h-full w-full min-h-0 overflow-hidden box-border", sidebarWrapperClass)}
            style={{ gridColumn: "1", gridRow: "1" }}
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
                <SidebarRoot
                  threads={threads}
                  activeId={activeId}
                  onSelect={handleSelectThread}
                  onNewChat={handleNewChatImmediate}
                  projectId={selectedProjectId}
                  onProjectChange={setSelectedProjectId}
                />
              </PanelShell>
            </div>
          </div>
        )}
        {/* Chat Panel */}
        <div
          className="flex h-full w-full min-h-0 overflow-hidden flex-col box-border"
          style={{
            gridColumn: isDesktopLayout && isSidebarOpen ? "2" : "1",
            gridRow: "1",
          }}
        >
          <PanelShell
            className="h-full w-full min-h-0 overflow-hidden box-border rounded-[var(--card-radius)]"
            surfaceStyle={chatSurfaceStyle}
            disabled={chatDisabled}
          >
            <div className="flex h-full min-h-0 overflow-hidden flex-col">
              <PromptLibraryPortal />
              {(imprintZero.status?.system_prompt_meta?.warnings?.length || 0) > 0 && (
                <div
                  className="mx-4 mt-3 rounded-lg border px-3 py-2 text-xs"
                  style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
                >
                  {(imprintZero.status?.system_prompt_meta?.warnings || []).join(" ")}
                </div>
              )}
              {showWorkspacePanel && (
                <div className="absolute inset-0 z-[110] pointer-events-auto">
                  <div className="absolute right-0 top-0 h-full w-[min(420px,90vw)] bg-black/50 backdrop-blur-md border-l border-white/10 shadow-2xl overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
                      <div className="text-sm font-semibold text-white">Workspace</div>
                      <button onClick={() => setShowWorkspacePanel(false)} className="text-white/70 hover:text-white">×</button>
                    </div>
                    <div className="p-4 text-white text-xs overflow-auto h-[calc(100%-42px)]">
                      <p>Workspace tools coming soon…</p>
                      <p>Prompt Library, Notes, File Viewer, Context Inspector, etc.</p>
                    </div>
                  </div>
                </div>
              )}
              <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
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
                  isSidebarVisible={isSidebarOpen}
                  sessionTabs={sessionState?.tabs ?? []}
                  activeSessionTabId={sessionState?.activeTabId ?? null}
                  activeModelId={activeSessionModelId}
                  activeDraft={activeSessionDraft}
                  onSessionTabActivate={handleSessionTabActivate}
                  onSessionTabClose={handleSessionTabClose}
                  onSessionTabOpen={handleSessionTabOpen}
                  onSessionModelChange={handleSessionModelChange}
                  onSessionDraftChange={handleSessionDraftChange}
                  onBack={() => {
                    setActiveId(null);
                    if (sessionSpine && activeSessionTabId) {
                      sessionSpine.tabSetThread(activeSessionTabId, undefined, "New Chat");
                    }
                    if (typeof window !== "undefined") {
                      window.history.pushState({}, "", "/guardian");
                    }
                  }}
                  bare
                />
              </div>
            </div>
          </PanelShell>
        </div>
      </div>
    </>
  );
}

// Inline Prompt Library popover mounted within chat panel
function PromptLibraryPortal() {
  const [open, setOpen] = React.useState(false);
  const [items, setItems] = React.useState<Array<{ text: string; ts?: number; title?: string; category?: string; tags?: string[]; pinned?: boolean }>>([]);
  const [query, setQuery] = React.useState("");

  React.useEffect(() => {
    const onToggle = () => {
      try {
        const raw = localStorage.getItem('cfy.prompts');
        const arr = raw ? JSON.parse(raw) : [];
        if (Array.isArray(arr)) setItems(arr);
      } catch {}
      setOpen(true);
    };
    window.addEventListener('cfy:workspace:togglePromptLibrary', onToggle);
    return () => window.removeEventListener('cfy:workspace:togglePromptLibrary', onToggle);
  }, []);

  function persist(next: typeof items) {
    setItems(next);
    try { localStorage.setItem('cfy.prompts', JSON.stringify(next)); } catch {}
  }

  function togglePin(idx: number) {
    const next = items.slice();
    next[idx] = { ...next[idx], pinned: !next[idx]?.pinned };
    persist(next);
  }

  function editItem(idx: number) {
    const cur = items[idx];
    const title = window.prompt('Title', cur.title || '') ?? cur.title;
    const category = window.prompt('Category', cur.category || '') ?? cur.category;
    const tagsRaw = window.prompt('Tags (comma-separated)', (cur.tags || []).join(', ')) ?? (cur.tags || []).join(',');
    const text = window.prompt('Prompt text', cur.text) ?? cur.text;
    const next = items.slice();
    next[idx] = { ...cur, title: title || undefined, category: category || undefined, tags: (tagsRaw || '').split(',').map(s => s.trim()).filter(Boolean), text };
    persist(next);
  }

  function removeItem(idx: number) {
    const next = items.slice();
    next.splice(idx, 1);
    persist(next);
  }

  function exportJSON() {
    try {
      const txt = JSON.stringify(items, null, 2);
      navigator.clipboard?.writeText(txt);
      window.dispatchEvent(new CustomEvent('cfy:toast', { detail: { message: 'Prompt library copied to clipboard' } }));
    } catch {}
  }

  async function importJSON() {
    const txt = window.prompt('Paste prompt library JSON');
    if (!txt) return;
    try {
      const arr = JSON.parse(txt);
      if (Array.isArray(arr)) persist(arr);
    } catch {
      alert('Invalid JSON');
    }
  }

  if (!open) return null;
  const filtered = items.filter(it => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const hay = [it.text, it.title, it.category, ...(it.tags || [])].filter(Boolean).join(' ').toLowerCase();
    return hay.includes(q);
  });
  const pinned = filtered.filter(i => i.pinned);
  const unpinned = filtered.filter(i => !i.pinned);
  const categories = Array.from(new Set(unpinned.map(i => i.category).filter(Boolean))) as string[];
  return (
    <div className="absolute inset-0 z-[120] pointer-events-none" aria-hidden={!open}>
      <div className="absolute bottom-20 right-6 w-[min(520px,96vw)] max-h-[50vh] overflow-hidden rounded-[var(--card-radius)] border pointer-events-auto"
           style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", boxShadow: "0 14px 34px rgba(0,0,0,0.35)" }}>
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>Prompt Library</div>
          <div className="flex items-center gap-2">
            <input
              type="search"
              placeholder="Search prompts…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-7 rounded-md px-2 text-xs border"
              style={{ background: "transparent", color: "var(--text)", borderColor: "var(--panel-border)" }}
            />
            <button type="button" className="text-xs underline" onClick={exportJSON}>Export</button>
            <button type="button" className="text-xs underline" onClick={importJSON}>Import</button>
            <button type="button" className="icon-inline" aria-label="Close" onClick={() => setOpen(false)}>×</button>
          </div>
        </div>
        <div className="max-h-[40vh] overflow-auto" style={{ borderColor: "var(--panel-border)" }}>
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-xs opacity-70" style={{ color: "var(--muted)" }}>No prompts yet. Send some prompts to build your library.</div>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--panel-border)" }}>
              {pinned.length > 0 && (
                <div>
                  <div className="px-3 py-1 text-[11px] uppercase opacity-70" style={{ color: "var(--muted)" }}>Pinned</div>
                  {pinned.map((it, idx) => (
                    <PromptRow key={`pinned-${idx}`} it={it} idx={idx} onUse={(t) => { window.dispatchEvent(new CustomEvent('cfy:composer:prefill', { detail: { text: t } })); setOpen(false); }} onPin={togglePin} onEdit={editItem} onRemove={removeItem} />
                  ))}
                </div>
              )}
              {categories.length > 0 && categories.map((cat) => (
                <div key={cat || 'uncat'}>
                  <div className="px-3 py-1 text-[11px] uppercase opacity-70" style={{ color: "var(--muted)" }}>{cat || 'Uncategorized'}</div>
                  {unpinned.filter(i => (i.category || '') === cat).map((it, idx) => (
                    <PromptRow key={`${cat}-${idx}`} it={it} idx={items.indexOf(it)} onUse={(t) => { window.dispatchEvent(new CustomEvent('cfy:composer:prefill', { detail: { text: t } })); setOpen(false); }} onPin={togglePin} onEdit={editItem} onRemove={removeItem} />
                  ))}
                </div>
              ))}
              {categories.length === 0 && unpinned.length > 0 && (
                <div>
                  {unpinned.map((it, idx) => (
                    <PromptRow key={`plain-${idx}`} it={it} idx={items.indexOf(it)} onUse={(t) => { window.dispatchEvent(new CustomEvent('cfy:composer:prefill', { detail: { text: t } })); setOpen(false); }} onPin={togglePin} onEdit={editItem} onRemove={removeItem} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PromptRow({ it, idx, onUse, onPin, onEdit, onRemove }: { it: { text: string; ts?: number; title?: string; category?: string; tags?: string[]; pinned?: boolean }; idx: number; onUse: (t: string) => void; onPin: (idx: number) => void; onEdit: (idx: number) => void; onRemove: (idx: number) => void; }) {
  return (
    <div className="px-3 py-2 text-sm hover:bg-white/5 select-text">
      <div className="flex items-start gap-2">
        <button type="button" className="text-xs underline shrink-0" onClick={() => onPin(idx)}>{it.pinned ? 'Unpin' : 'Pin'}</button>
        <div className="flex-1 cursor-pointer" title="Double‑click to use" onDoubleClick={() => onUse(it.text)}>
          {it.title && <div className="font-semibold truncate" style={{ color: "var(--text)" }}>{it.title}</div>}
          <div className="truncate" style={{ color: "var(--text)" }}>{it.text}</div>
          <div className="text-[10px] opacity-60 flex items-center gap-2" style={{ color: "var(--muted)" }}>
            {it.category && <span>#{it.category}</span>}
            {(it.tags && it.tags.length > 0) && <span>{it.tags.map(t => `#${t}`).join(' ')}</span>}
            {it.ts && <span>{new Date(it.ts).toLocaleString()}</span>}
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <button type="button" className="text-xs underline" onClick={() => onEdit(idx)}>Edit</button>
          <button type="button" className="text-xs underline" onClick={() => onRemove(idx)}>Remove</button>
        </div>
      </div>
    </div>
  );
}
