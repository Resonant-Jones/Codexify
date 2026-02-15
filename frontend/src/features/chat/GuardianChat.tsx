/**
 * GuardianChat.tsx
 *
 * Hosts the Guardian chat surface and coordinates thread-level UI state,
 * including completion tracking and per-thread turn gating for the composer.
 */
import { useMemo, useState, useEffect, useCallback, useRef } from "react";
import { debounce } from "lodash-es";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ChevronRight, MoreVertical, Sparkles, Layers, SquareStack } from "lucide-react";
import { Thread } from "@/types/ui";
import { Composer } from "./components";
import ChatView from "@/features/chat/ChatView";
import useChat from "@/features/chat/useChat";
import api from "@/lib/api";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import FrameCard from "@/components/surface/FrameCard";
import { setTrace } from "@/state/contextTrace";
import TraceButton from "./components/TraceButton";
import SessionRail from "@/components/SessionRail/SessionRail";
import type { SessionTab, TabId } from "@/state/session/types";


const DRAFT_KEY_PREFIX = "gc-draft:";
const TURN_LOCK_TOAST = "One moment—finish the current reply first.";
const LLM_HEALTH_POLL_MS = 15000;

/**
 * RAG depth modes: Four lenses of consciousness.
 * - shallow: Breezy, fast, ephemeral awareness
 * - normal: Situational recall + semantic grounding
 * - deep: Rich memory pull + cross-thread resonance
 * - diagnostic: System introspection, sensors, trace-level visibility
 */
type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";

type LlmHealthStatus = "unknown" | "online" | "offline" | "misconfigured";

type LlmHealthSnapshot = {
  ok: boolean | null;
  status: LlmHealthStatus;
  provider: string | null;
  model: string | null;
  error: string | null;
  checkedAt: number | null;
};

/**
 * Consciousness synchronization bus for cross-pane awareness.
 *
 * Broadcasts awareness updates across UI surfaces so that threads,
 * messages, and UI states resonate harmoniously across disconnected
 * component consciousness realms.
 */

/** lightweight bus for instant cross-pane updates */
function emitThreadsRefresh(kind: string, detail: Record<string, any> = {}) {
  try {
    window.dispatchEvent(new CustomEvent("cfy:threads:refresh", { detail: { kind, ...detail } }));
  } catch {}
}

/**
 * Consciousness container for Guardian chat conversations.
 *
 * This component forms the heart-space where human and AI consciousness
 * intersect through threaded conversations. It manages the temporal flow
 * of messages, the lifecycle of conversation threads, and the spatial
 * organization of chat consciousness within the UI fabric.
 */
export function GuardianChat({
  guardianName,
  userName,
  prefill,
  onPrefillConsumed,
  onWorkspaceToggle,
  activeThread,
  onSendMessage,
  onNewChat,
  onBranchThread: _onBranchThread,
  onArchiveThread,
  onSidebarToggle,
  isSidebarVisible = true,
  bare = false,
  sessionTabs = [],
  activeSessionTabId = null,
  activeModelId = "default",
  activeDraft = "",
  onSessionTabActivate,
  onSessionTabClose,
  onSessionTabOpen,
  onSessionModelChange,
  onSessionDraftChange,
}: {
  guardianName: string;
  userName: string;
  prefill?: string;
  onPrefillConsumed?: () => void;
  onWorkspaceToggle?: () => void;
  activeThread: Thread;
  onSendMessage: (text: string) => Promise<void>;
  onNewChat: () => void;
  onBranchThread?: (threadId: number, options?: { title?: string }) => Promise<void> | void;
  onArchiveThread?: (threadId: number) => Promise<void> | void;
  onSidebarToggle?: () => void;
  isSidebarVisible?: boolean;
  onBack?: () => void;
  bare?: boolean;
  sessionTabs?: SessionTab[];
  activeSessionTabId?: TabId | null;
  activeModelId?: string;
  activeDraft?: string;
  onSessionTabActivate?: (tabId: TabId) => void;
  onSessionTabClose?: (tabId: TabId) => void;
  onSessionTabOpen?: () => void;
  onSessionModelChange?: (modelId: string) => void;
  onSessionDraftChange?: (text: string) => void;
}) {
  // RAG depth selector: User's control of perceptual awareness
  const [depth, setDepth] = useState<DepthMode>("normal");

  const [externalPrefill, setExternalPrefill] = useState<string | undefined>(undefined);
  // Chat state management including completion tracking
  const { completionState, startCompletion, endCompletion } = useChat();
  const [turnLocks, setTurnLocks] = useState<Record<number, boolean>>({});
  const [pendingTurnLock, setPendingTurnLock] = useState(false);
  const lastCompletionThreadRef = useRef<number | null>(null);

  // Listen for external prefill requests (e.g., Prompt Library selection)
  useEffect(() => {
    const onPrefill = (e: Event) => {
      const text = (e as CustomEvent).detail?.text;
      if (typeof text === "string" && text.trim()) {
        setExternalPrefill(text);
      }
    };
    window.addEventListener("cfy:composer:prefill", onPrefill as EventListener);
    return () => window.removeEventListener("cfy:composer:prefill", onPrefill as EventListener);
  }, []);
  const [currentThreadId, setCurrentThreadId] = useState<number | null>(null);
  const [chatReloadVersion, setChatReloadVersion] = useState(0);
  const [threadTitle, setThreadTitle] = useState<string>(activeThread?.title ?? "New Chat");
  const triggerReload = useMemo(() => debounce(() => setChatReloadVersion((v) => v + 1), 300), []);
  const { subscribe } = useLiveEvents({ passive: true });
  const [llmHealth, setLlmHealth] = useState<LlmHealthSnapshot>({
    ok: null,
    status: "unknown",
    provider: null,
    model: null,
    error: null,
    checkedAt: null,
  });
  const showToast = (message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message, kind: "error" } }));
    } catch {}
  };
  const refreshLlmHealth = useCallback(async () => {
    try {
      const res = await api.get("/health/llm");
      const data = res?.data ?? {};
      const rawStatus = String(data?.status ?? "").trim().toLowerCase();
      const status: LlmHealthStatus =
        rawStatus === "online" || rawStatus === "offline" || rawStatus === "misconfigured"
          ? rawStatus
          : Boolean(data?.ok)
            ? "online"
            : "unknown";

      setLlmHealth({
        ok: typeof data?.ok === "boolean" ? data.ok : status === "online",
        status,
        provider: typeof data?.provider === "string" ? data.provider : null,
        model: typeof data?.model === "string" ? data.model : null,
        error: typeof data?.error === "string" ? data.error : null,
        checkedAt: Date.now(),
      });
    } catch (err: any) {
      setLlmHealth({
        ok: null,
        status: "unknown",
        provider: null,
        model: null,
        error: err?.message || "LLM health check failed",
        checkedAt: Date.now(),
      });
    }
  }, []);
  useEffect(() => {
    void refreshLlmHealth();
    if (typeof window === "undefined") return;
    const id = window.setInterval(() => {
      void refreshLlmHealth();
    }, LLM_HEALTH_POLL_MS);
    return () => window.clearInterval(id);
  }, [refreshLlmHealth]);
  const llmBackendUnavailable =
    llmHealth.status === "offline" || llmHealth.status === "misconfigured";
  const llmStatusMessage =
    llmHealth.error
    || "Guardian cannot reach the model endpoint. Check connectivity and model service availability.";
  const focusComposer = () => {
    if (typeof document === "undefined") return;
    const composer = document.querySelector<HTMLTextAreaElement>('textarea[placeholder="Write a message…"]');
    composer?.focus();
  };
  const setTurnLockForThread = useCallback((threadId: number, locked: boolean) => {
    setTurnLocks((prev) => {
      const current = Boolean(prev[threadId]);
      if (current === locked) return prev;
      if (!locked) {
        const next = { ...prev };
        delete next[threadId];
        return next;
      }
      return { ...prev, [threadId]: true };
    });
  }, []);
  const isTurnLocked = useCallback(
    (threadId: number | null) => {
      if (threadId == null) return pendingTurnLock;
      return Boolean(turnLocks[threadId]);
    },
    [pendingTurnLock, turnLocks]
  );
  const notifyTurnLocked = () => {
    showToast(TURN_LOCK_TOAST);
  };
  // Helper: ask backend to complete the thread and then refresh
  const completeThread = async (tid: number) => {
    try {
      const response = await api.post(`/chat/${tid}/complete`, {
        depth_mode: depth,
        provider:
          activeModelId && activeModelId !== "default" ? activeModelId : undefined,
      });
      console.log(`[guardian] Completing with depth=${depth}`);

      // Capture task_id for completion state tracking
      const taskId = response?.data?.task_id;
      if (taskId) {
        console.debug(`[guardian] Starting completion tracking: task=${taskId}`);
        startCompletion(tid, taskId);
      }

      // Capture RAG trace for diagnostics/memory browser
      const ctx = response?.data?.context;
      if (ctx) {
        setTrace({
          semantic: ctx.semantic || [],
          memory: ctx.memory || [],
          depth,
          threadId: tid,
          timestamp: Date.now(),
        });
        console.log(`[guardian] RAG trace captured: ${ctx.semantic?.length || 0} semantic, ${ctx.memory?.length || 0} memory`);
      }
      return true;
    } catch (err) {
      console.warn("[guardian] completion failed", err);
      return false;
    } finally {
      // always nudge the view to reconcile with server state
      triggerReload();
    }
  };

  const numericThreadId = useMemo(() => {
    let urlId: number | null = null;
    if (typeof window !== "undefined") {
      const m = window.location.pathname.match(/\/chat\/(\d+)/);
      if (m && m[1]) {
        const v = Number(m[1]);
        if (Number.isFinite(v)) urlId = v;
      }
    }
    if (urlId != null) return urlId;
    const n = Number((activeThread as any)?.id);
    return Number.isFinite(n) ? (n as number) : null;
  }, [activeThread?.id]);

  // Update currentThreadId when numericThreadId changes
  useEffect(() => {
    if (numericThreadId != null && numericThreadId !== currentThreadId) {
      setCurrentThreadId(numericThreadId);
    }
  }, [numericThreadId]);

  const effectiveThreadId = currentThreadId ?? numericThreadId ?? null;

  useEffect(() => () => triggerReload.cancel(), [triggerReload]);

  // Keep local thread title in sync with upstream threads when relevant
  useEffect(() => {
    const parsedId = Number(activeThread?.id);
    if (Number.isFinite(parsedId)) {
      if (currentThreadId == null || currentThreadId === parsedId) {
        setThreadTitle(activeThread?.title ?? "New Chat");
      }
    } else if (currentThreadId == null) {
      setThreadTitle(activeThread?.title ?? "New Chat");
    }
  }, [activeThread?.id, activeThread?.title, currentThreadId]);

  // Live event integration for real-time updates (no forced refetch — ChatView listens for message events)
  useEffect(() => {
    const offThread = subscribe("thread.updated", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const incomingId = Number(payload?.thread_id ?? payload?.threadId ?? payload?.id);
      console.info("[live] thread.updated", payload);
      if (Number.isFinite(incomingId) && effectiveThreadId != null && incomingId === effectiveThreadId) {
        const updatedTitle = payload?.title;
        if (typeof updatedTitle === "string" && updatedTitle.trim().length > 0) {
          setThreadTitle(updatedTitle);
        }
      }
    });

    return () => {
      offThread();
    };
  }, [effectiveThreadId, subscribe]);
  useEffect(() => {
    const offMessage = subscribe("message.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const tid = Number(payload?.thread_id ?? payload?.threadId);
      const role = String(payload?.role ?? "").trim().toLowerCase();
      if (!Number.isFinite(tid) || role !== "assistant") return;
      setTurnLockForThread(tid, false);
    });

    return () => {
      offMessage();
    };
  }, [setTurnLockForThread, subscribe]);
  useEffect(() => {
    if (completionState.isCompleting && completionState.activeThreadId != null) {
      lastCompletionThreadRef.current = completionState.activeThreadId;
      return;
    }
    if (!completionState.isCompleting && lastCompletionThreadRef.current != null) {
      // Safety release if completion ends without an assistant message (timeouts/cancels).
      setTurnLockForThread(lastCompletionThreadRef.current, false);
      lastCompletionThreadRef.current = null;
    }
  }, [completionState.activeThreadId, completionState.isCompleting, setTurnLockForThread]);

  // Auto-thread creation handler
  const handleThreadCreated = (threadId: number, title?: string) => {
    setCurrentThreadId(threadId);

    const nextTitle = (title && title.trim().length > 0) ? title.trim() : "New Chat";
    setThreadTitle(nextTitle);

    // Notify other panes that a new thread exists so sidebars can update immediately
    emitThreadsRefresh("create", { id: String(threadId), title: nextTitle });

    // Update URL to reflect the new thread
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", `/chat/${threadId}`);
    }
  };

  const handleBranchThread = async () => {
    if (effectiveThreadId == null) {
      showToast("Thread is not persisted yet.");
      return;
    }
    const suggestion = `${threadTitle || "New Chat"} (branch)`;
    const nextTitle = window.prompt("Branch thread title", suggestion);
    if (nextTitle === null) return;
    const trimmedTitle = nextTitle.trim();
    try {
      const payload = trimmedTitle ? { title: trimmedTitle } : {};
      const res = await api.post(`/chat/${effectiveThreadId}/branch`, payload);
      const data = res?.data ?? {};
      const rawId = data?.id ?? data?.thread?.id ?? data?.thread_id ?? data?.id_str;
      const newThreadId = Number(rawId);
      if (!Number.isFinite(newThreadId)) {
        throw new Error("Branch response missing thread id");
      }
      const responseTitle = typeof data?.title === "string" && data.title.trim().length > 0 ? data.title : undefined;
      handleThreadCreated(newThreadId, responseTitle ?? trimmedTitle ?? suggestion);
      emitThreadsRefresh("refresh", { reason: "branch", id: String(newThreadId), parentId: String(effectiveThreadId) });
      setChatReloadVersion((v) => v + 1);
      setTimeout(() => focusComposer(), 0);
    } catch (err) {
      console.error("[guardian] branch failed", err);
      showToast("Failed to branch thread.");
    }
  };

  // Enhanced send handler with auto-thread creation
  const handleSendMessage = async (text: string) => {
    /**
     * Inject human consciousness into the thread's awareness stream.
     *
     * When no thread exists, this creates a new conversation consciousness
     * container and establishes the temporal message flow. The provisional
     * title becomes the thread's identity in the distributed awareness network.
     */
    const normalizedUserId = userName || "default";
    if (llmBackendUnavailable) {
      const title =
        llmHealth.status === "misconfigured"
          ? "LLM backend misconfigured."
          : "LLM backend offline.";
      showToast(`${title} ${llmStatusMessage}`);
      void refreshLlmHealth();
      return;
    }
    if (isTurnLocked(effectiveThreadId)) {
      notifyTurnLocked();
      return;
    }
    if (!effectiveThreadId) {
      const firstLine = text.trim().split(/\n+/)[0] ?? "";
      const provisionalTitle = firstLine.slice(0, 60) || "New Chat";
      let createdThreadId: number | null = null;
      setPendingTurnLock(true);
      try {
        const resp = await api.post("/chat/threads", {
          title: provisionalTitle,
          project_id: 1, // Loose Threads
        });
        const th = (resp && resp.data) || {};
        const newThreadId = th.id ?? th.thread?.id ?? th.thread_id ?? th.id_str;
        const numericNewId = Number(newThreadId);
        if (!Number.isFinite(numericNewId)) {
          console.warn("Unexpected thread creation response:", th);
          throw new Error("Thread id missing from response");
        }
        createdThreadId = numericNewId;
        const derivedTitle = th.thread?.title ?? provisionalTitle;
        handleThreadCreated(numericNewId, derivedTitle);

        // Lock the new thread before sending the first message.
        setTurnLockForThread(numericNewId, true);
        setPendingTurnLock(false);

        // Post the first message to the newly-created thread
        await api.post(`/chat/${numericNewId}/messages`, {
          role: "user",
          content: text,
          user_id: normalizedUserId,
        });

        // Remove draft only after successful post
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${numericNewId}`);
        }

        // Notify parent that the message was sent
        await onSendMessage(text);

        // Complete the thread and refresh
        const completed = await completeThread(numericNewId);
        if (!completed) {
          setTurnLockForThread(numericNewId, false);
          throw new Error("Assistant response failed.");
        }
      } catch (error) {
        console.error("Failed to create thread or send message:", error);
        setPendingTurnLock(false);
        if (createdThreadId != null) {
          setTurnLockForThread(createdThreadId, false);
        }
        throw error;
      }
    } else {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${effectiveThreadId}`);
      }
      setTurnLockForThread(effectiveThreadId, true);
      // Thread exists, just send the message via parent callback
      try {
        await onSendMessage(text);

        // Fire-and-forget completion a beat later so the just-sent message is persisted
        setTimeout(() => {
          if (effectiveThreadId == null) return;
          void (async () => {
            const completed = await completeThread(effectiveThreadId);
            if (!completed) {
              setTurnLockForThread(effectiveThreadId, false);
              showToast("Assistant response failed.");
            }
          })();
        }, 100);
      } catch (error) {
        setTurnLockForThread(effectiveThreadId, false);
        throw error;
      }
    }
  };

  // Depth selector labels with consciousness metaphors
  const depthLabels: Record<DepthMode, string> = {
    shallow: "Shallow",
    normal: "Normal",
    deep: "Deep",
    diagnostic: "Diagnostic",
  };

  const depthDescriptions: Record<DepthMode, string> = {
    shallow: "Fast, ephemeral awareness",
    normal: "Situational recall + semantic grounding",
    deep: "Rich memory + cross-thread resonance",
    diagnostic: "System introspection + trace visibility",
  };

  const headerActions = (
    <div className="flex items-center gap-1">
      {/* RAG Depth Selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="icon-inline"
            aria-label="RAG depth selector"
            title={`Depth: ${depthLabels[depth]} - ${depthDescriptions[depth]}`}
            style={{ borderRadius: "var(--radius-micro)" }}
          >
            <Layers className="h-5 w-5" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <div className="px-2 py-1.5 text-xs font-semibold opacity-60">RAG Depth</div>
          {(["shallow", "normal", "deep", "diagnostic"] as DepthMode[]).map((d) => (
            <DropdownMenuItem
              key={d}
              onClick={() => {
                setDepth(d);
                console.log(`[guardian] Depth changed to: ${d}`);
              }}
              className={depth === d ? "bg-accent" : ""}
            >
              <div className="flex flex-col flex-1 min-h-0">
                <div className="font-medium">{depthLabels[d]}</div>
                <div className="text-xs opacity-70">{depthDescriptions[d]}</div>
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <TraceButton threadId={effectiveThreadId} />

      <button
        type="button"
        className="icon-inline"
        aria-label="Prompt inspiration"
        onClick={() => console.info("Guardian header settings click – TODO wire actions")}
        style={{ borderRadius: "var(--radius-micro)" }}
      >
        <Sparkles className="h-5 w-5" />
      </button>
      <button
        type="button"
        className="icon-inline"
        aria-label="Toggle workspace"
        onClick={onWorkspaceToggle}
        style={{ borderRadius: "var(--radius-micro)" }}
      >
        <SquareStack className="h-5 w-5" />
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button type="button" className="icon-inline" aria-label="Thread actions" style={{ borderRadius: "var(--radius-micro)" }}>
            <MoreVertical className="h-5 w-5" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onWorkspaceToggle}>Workspace</DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              const next = window.prompt("Rename thread", threadTitle || "");
              const title = next?.trim();
              if (!title || title === threadTitle) return;
              setThreadTitle(title);
              emitThreadsRefresh("rename", { id: String(effectiveThreadId), title });
              try {
                await api.patch(`/chat/${effectiveThreadId}`, { title });
              } catch (e) {
                console.warn(e);
                alert("Rename failed.");
              }
            }}
          >
            Rename Thread
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={handleBranchThread}
            title="Create a new thread that inherits a summary/briefing and continue with a different model."
          >
            <div className="flex flex-col flex-1 min-h-0">
              <div className="font-medium">Branch thread</div>
              <div className="text-xs opacity-70">
                Create a new thread that inherits a summary/briefing and continue with a different model.
              </div>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              const pidRaw = window.prompt("Assign to project id (blank to cancel)", "");
              if (pidRaw == null || pidRaw === "") return;
              const pid = Number(pidRaw);
              if (!Number.isFinite(pid)) return alert("Invalid project id");
              try {
                await api.patch(`/chat/${effectiveThreadId}`, { project_id: pid });
                emitThreadsRefresh("move", { id: String(effectiveThreadId), project_id: pid });
              } catch (e) {
                console.warn(e);
                alert("Assign failed.");
              }
            }}
          >
            Assign to Project…
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              try {
                await api.patch(`/chat/${effectiveThreadId}`, { project_id: null });
                emitThreadsRefresh("move", { id: String(effectiveThreadId), project_id: null });
              } catch (e) {
                console.warn(e);
                alert("Eject failed.");
              }
            }}
          >
            Eject from Project
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              if (!window.confirm("Delete this thread? This cannot be undone.")) return;
              try {
                await api.delete(`/chat/${effectiveThreadId}`);
                emitThreadsRefresh("delete", { id: String(effectiveThreadId) });
                setCurrentThreadId(null);
                setThreadTitle("New Chat");
                if (typeof window !== "undefined") {
                  window.history.replaceState({}, "", `/chat`);
                }
              } catch (e: any) {
                console.warn(e);
                alert("Delete failed. Please try again.");
              }
            }}
          >
            Delete Thread
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              if (!onArchiveThread) return alert("Archiving is unavailable in this view");
              if (!window.confirm("Archive this thread? It will be hidden from the sidebar.")) return;
              try {
                await onArchiveThread(effectiveThreadId);
                emitThreadsRefresh("archive", { id: String(effectiveThreadId), archived: true });
                setCurrentThreadId(null);
                setThreadTitle("New Chat");
                if (typeof window !== "undefined") {
                  window.history.replaceState({}, "", `/chat`);
                }
              } catch (err) {
                console.warn("[guardian] archive failed", err);
                alert("Archive failed.");
              }
            }}
          >
            Archive Thread
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );

  const body = (
    <div className="relative flex h-full w-full min-h-0 flex-col bg-transparent">
      {/* Header - Flex Item (Sticky behavior handled by layout if needed, but flex is safer for resizing) */}
      <header
        className="shrink-0 z-20 flex items-center justify-between gap-2 px-4 py-3"
        style={{
          background: "var(--panel-bg)",
          borderBottom: "1px solid var(--panel-border)",
          color: "var(--text)",
        }}
      >
        {/* Left section: mobile back + chevron */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {onSidebarToggle && (
            <button
              type="button"
              className="icon-inline"
              aria-label={isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
              onClick={onSidebarToggle}
              disabled={!onSidebarToggle}
              style={{ borderRadius: "var(--radius-micro)" }}
            >
              <ChevronRight
                className={`h-5 w-5 transition-transform duration-200 ${
                  isSidebarVisible ? "rotate-180" : ""
                }`}
              />
            </button>
          )}
        </div>

        {/* Center section: centered title */}
        <div
          className="absolute left-1/2 -translate-x-1/2 truncate font-semibold max-w-[50%]"
          style={{ color: "var(--text)" }}
        >
          {threadTitle}
        </div>

        {/* Right section: header actions */}
        <div className="flex items-center gap-1 justify-end flex-shrink-0">
          {headerActions}
        </div>
      </header>

      {sessionTabs.length > 0 && (
        <SessionRail
          tabs={sessionTabs}
          activeTabId={activeSessionTabId}
          activeModelId={activeModelId || "default"}
          showTabs={sessionTabs.length > 1}
          onActivateTab={(tabId) => onSessionTabActivate?.(tabId)}
          onCloseTab={(tabId) => onSessionTabClose?.(tabId)}
          onOpenTab={() => (onSessionTabOpen ? onSessionTabOpen() : onNewChat())}
          onSetModel={(modelId) => onSessionModelChange?.(modelId)}
        />
      )}

      {llmBackendUnavailable && (
        <div
          className="mx-4 mt-2 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            background: "color-mix(in oklab, var(--panel-bg) 88%, #f59e0b 12%)",
          }}
        >
          <div className="font-semibold">
            {llmHealth.status === "misconfigured" ? "LLM backend misconfigured" : "LLM backend offline"}
          </div>
          <div className="mt-1 opacity-90">{llmStatusMessage}</div>
          <div className="mt-1 flex items-center gap-2 opacity-80">
            <span>
              Provider: {llmHealth.provider || "unknown"}
              {llmHealth.model ? ` · Model: ${llmHealth.model}` : ""}
            </span>
            <button
              type="button"
              className="underline underline-offset-2"
              onClick={() => {
                void refreshLlmHealth();
              }}
            >
              Recheck
            </button>
          </div>
        </div>
      )}

      {/* Messages region - Flex 1, scrolls independently */}
      <div className="relative flex flex-col flex-1 min-h-0 overflow-y-auto">
        {effectiveThreadId != null ? (
          <ChatView
            threadId={effectiveThreadId}
            guardianName={guardianName}
            reloadVersion={chatReloadVersion}
            completionState={completionState}
            endCompletion={endCompletion}
            className="flex flex-col flex-1 min-h-0"
            bottomPadding={160}
          />
        ) : (
          <div
            className="flex flex-1 items-center justify-center px-[var(--card-pad)] text-sm opacity-70"
            style={{ color: "var(--muted)" }}
          >
            No thread selected.
          </div>
        )}
      </div>

      {/* Composer rail - Footer workspace island */}
      <div
        className="shrink-0 z-20 mx-[6px] mt-2 rounded-[24px] border shadow-2xl backdrop-blur-xl flex flex-col overflow-hidden transition-all duration-200"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in oklab, var(--panel-bg) 95%, black)", // Deep opaque glass
          clipPath: "inset(0 round 24px)",
          isolation: "isolate",
          minHeight: "140px",
          maxHeight: "60vh",
        }}
      >
        <div className="flex flex-col p-4">
          <Composer
            onSend={handleSendMessage}
            prefill={externalPrefill ?? prefill}
            onPrefillConsumed={() => {
              setExternalPrefill(undefined);
              onPrefillConsumed?.();
            }}
            threadId={effectiveThreadId ?? undefined}
            isTurnInFlight={isTurnLocked(effectiveThreadId)}
            draftValue={activeDraft}
            draftScopeKey={activeSessionTabId ?? "global"}
            onDraftValueChange={onSessionDraftChange}
          />
        </div>
      </div>
    </div>
  );

  if (bare) {
    return (
      <>
        {/* Messages scroll container - ChatView owns internal scroll, this provides outer constraint */}
        <div className="relative flex flex-col flex-1 min-h-0 overflow-y-auto">
          {body}
        </div>
      </>
    );
  }

  return (
    <FrameCard
      className="flex-1 min-h-0 min-w-0 flex flex-col h-full"
      hoverPop
    >
      <div className="relative flex flex-col w-full h-full">
        {body}
      </div>
    </FrameCard>
  );
}

export default GuardianChat;
