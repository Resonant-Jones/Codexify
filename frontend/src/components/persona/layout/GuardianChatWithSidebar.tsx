/**
 * GuardianChatWithSidebar — coordinates the chat surface and the sidebar, ensuring
 * each lives inside its own glass shell while sharing data feeds for threads/projects/messages.
 */
import React, { useMemo } from "react";
import clsx from "clsx";
import GuardianChat from "@/features/chat/GuardianChat";
import SidebarRoot from "@/components/sidebar/SidebarRoot";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { Thread, Message } from "@/types/ui";
import api from "@/lib/api";
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
  const [showWorkspacePanel, setShowWorkspacePanel] = React.useState(false);
  const bp = useBreakpoint();
  const [threads, setThreads] = React.useState<Thread[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const { subscribe } = useLiveEvents();
  const { wallpaperUrl } = useWallpaperUrl();
  // Workspace panel toggle event listener
  React.useEffect(() => {
    const onToggleWorkspace = () => {
      setShowWorkspacePanel(prev => !prev);
    };
    window.addEventListener('cfy:workspace:toggleWorkspacePanel', onToggleWorkspace);
    return () => window.removeEventListener('cfy:workspace:toggleWorkspacePanel', onToggleWorkspace);
  }, []);

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
      await fetch('/embed', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, tags: ['prompt'], metadata: { source } }),
      });
      // Also append to local prompt cache for prompt library UI
      try {
        const key = 'cfy.prompts';
        const raw = localStorage.getItem(key);
        const arr = raw ? JSON.parse(raw) : [];
        const next = [{ text, ts: Date.now() }, ...Array.isArray(arr) ? arr : []].slice(0, 200);
        localStorage.setItem(key, JSON.stringify(next));
      } catch {}
    } catch (err) {
      console.warn('[prompt] embed failed', err);
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
        await api.patch(`/chat/${threadId}`, { archived: true });
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

      // Best-effort graph hook; safe to fail until the route exists
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
      className="relative grid h-full w-full max-w-[1500px] box-border items-stretch mx-auto overflow-hidden"
      style={{
        gridTemplateColumns: "clamp(300px, 24vw, 360px) minmax(0, 1fr)",
        gap: "8px",
        padding: "0px",
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
                  <SidebarRoot
                    threads={threads}
                    activeId={activeId}
                    onSelect={setActiveId}
                    onNewChat={handleNewChatImmediate}
                  />
                </PanelShell>
              </div>
            </div>
          </>
        )}
        {/* Chat Panel */}
        <div
          className="h-full w-full overflow-hidden box-border"
          style={{
            gridColumn: isSidebarOpen ? 2 : "1 / span 2",
            gridRow: "1",
          }}
        >
          <PanelShell
            className="h-full w-full overflow-hidden box-border"
            surfaceStyle={chatSurfaceStyle}
            disabled={chatDisabled}
          >
            <PromptLibraryPortal />
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
      <div className="absolute bottom-20 right-6 w-[min(520px,96vw)] max-h-[50vh] overflow-hidden rounded-2xl border pointer-events-auto"
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
