/**
 * GuardianChat.tsx
 *
 * Hosts the Guardian chat surface and coordinates thread-level UI state,
 * including completion tracking and per-thread turn gating for the composer.
 */
import { useMemo, useState, useEffect, useCallback, useRef } from "react";
import { debounce } from "lodash-es";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ChevronRight,
  MoreVertical,
  Sparkles,
  Layers,
  SquareStack,
  Zap,
  Volume2,
} from "lucide-react";
import { Thread } from "@/types/ui";
import { Composer } from "./components";
import ChatView from "@/features/chat/ChatView";
import useChat from "@/features/chat/useChat";
import api, { buildChatCompletePath } from "@/lib/api";
import { buildChatCompletionPayload } from "@/lib/chatClient";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import FrameCard from "@/components/surface/FrameCard";
import { setTrace } from "@/state/contextTrace";
import PromptCostIndicator from "./components/PromptCostIndicator";
import TraceButton from "./components/TraceButton";
import SessionRail from "@/components/SessionRail/SessionRail";
import type { SessionTab, TabId } from "@/state/session/types";
import type { RagTraceResponse } from "@/types/rag";
import { fetchSystemPromptSummary, type PromptCostStatus, type SystemPromptSummary } from "@/imprint/api";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import { logOnce } from "@/lib/logging/logOnce";


const DRAFT_KEY_PREFIX = "gc-draft:";
const TURN_LOCK_TOAST = "One moment—finish the current reply first.";
const LLM_HEALTH_POLL_MS = 15000;
const THREAD_PROFILE_POLL_MS = 15000;
const NEW_THREAD_TITLE = "New Thread";

/**
 * RAG depth modes: Four lenses of consciousness.
 * - shallow: Breezy, fast, ephemeral awareness
 * - normal: Situational recall + semantic grounding
 * - deep: Rich memory pull + cross-thread resonance
 * - diagnostic: System introspection, sensors, trace-level visibility
 */
type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";
type PromptCostPopoverSection = "cost" | "providers";

type LlmHealthStatus = "unknown" | "online" | "offline" | "misconfigured";

type LlmHealthSnapshot = {
  ok: boolean | null;
  status: LlmHealthStatus;
  provider: string | null;
  model: string | null;
  error: string | null;
  checkedAt: number | null;
};

type ProfileMode = "local" | "cloud";

type SystemProfileOption = {
  id: string;
  name: string;
  mode: ProfileMode;
  providerOverride?: string | null;
  modelOverride?: string | null;
};

type ResolvedProfileState = {
  id: string;
  name: string;
  mode: ProfileMode;
  providerOverride: string | null;
  modelOverride: string | null;
};

const PROFILE_FALLBACK_OPTIONS: SystemProfileOption[] = [
  { id: "default", name: "Default", mode: "cloud" },
  { id: "cloud_mode", name: "Cloud Profile", mode: "cloud" },
  { id: "local_mode", name: "Local Mode", mode: "local" },
];

function profileModeFromValue(value: unknown): ProfileMode {
  return String(value ?? "").trim().toLowerCase() === "local"
    ? "local"
    : "cloud";
}

function normalizeProfileId(value: unknown): string {
  const cleaned = String(value ?? "").trim();
  return cleaned || "default";
}

function normalizeProfileName(value: unknown, profileId: string): string {
  const cleaned = String(value ?? "").trim();
  if (cleaned) return cleaned;
  return (
    profileId
      .replace(/[_-]+/g, " ")
      .trim()
      .replace(/\b\w/g, (ch) => ch.toUpperCase()) || "Profile"
  );
}

function normalizeProfileOption(
  raw: any,
  fallbackId?: string
): SystemProfileOption | null {
  if (!raw || typeof raw !== "object") return null;
  const id = normalizeProfileId(raw.id ?? raw.profile_id ?? fallbackId ?? "default");
  return {
    id,
    name: normalizeProfileName(raw.name, id),
    mode: profileModeFromValue(raw.mode ?? raw.provider_override),
    providerOverride:
      raw.provider_override != null ? String(raw.provider_override) : null,
    modelOverride:
      raw.model_override != null ? String(raw.model_override) : null,
  };
}

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
  onThreadPersisted,
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
  onThreadPersisted?: (threadId: number, title?: string) => void;
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
  const lastCompletionDepthRef = useRef<Record<number, DepthMode>>({});
  const traceEndpointRef = useRef<Record<number, string>>({});
  const traceFetchInflightRef = useRef<Record<number, boolean>>({});
  const activeThreadRef = useRef<Thread>(activeThread);

  useEffect(() => {
    activeThreadRef.current = activeThread;
  }, [activeThread]);

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
  const [threadTitle, setThreadTitle] = useState<string>(activeThread?.title ?? NEW_THREAD_TITLE);
  const voiceFileInputRef = useRef<HTMLInputElement | null>(null);
  const [voiceUploading, setVoiceUploading] = useState(false);
  const [autoReadEnabled, setAutoReadEnabled] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem("cfy.voice.autoRead") === "1";
    } catch {
      return false;
    }
  });
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
  const [availableProfiles, setAvailableProfiles] = useState<SystemProfileOption[]>(PROFILE_FALLBACK_OPTIONS);
  const [resolvedProfile, setResolvedProfile] = useState<ResolvedProfileState>({
    id: "default",
    name: "Default",
    mode: "cloud",
    providerOverride: null,
    modelOverride: null,
  });
  const [profileSwitching, setProfileSwitching] = useState(false);
  const [promptCostSummary, setPromptCostSummary] = useState<SystemPromptSummary | null>(null);
  const [promptCostPopoverOpen, setPromptCostPopoverOpen] = useState(false);
  const [promptCostPopoverSection, setPromptCostPopoverSection] =
    useState<PromptCostPopoverSection>("cost");
  const [providerMenuOpenSignal, setProviderMenuOpenSignal] = useState(0);
  const promptCostPopoverRef = useRef<HTMLDivElement | null>(null);
  const showToast = useCallback((message: string) => {
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:toast", { detail: { message, kind: "error" } })
      );
    } catch {}
  }, []);
  const resolveProfileIdFromCommand = useCallback(
    (text: string): string | null => {
      const normalized = text.trim().toLowerCase();
      if (!normalized) return null;
      if (!/\b(switch|activate|use|set)\b/.test(normalized)) return null;

      const localIntent = /\b(local|offline)\b/.test(normalized);
      const cloudIntent = /\b(cloud|online|remote)\b/.test(normalized);
      const defaultIntent = /\b(default)\b/.test(normalized);
      if (!localIntent && !cloudIntent && !defaultIntent) return null;

      const options = availableProfiles.length
        ? availableProfiles
        : PROFILE_FALLBACK_OPTIONS;

      if (localIntent) {
        const local =
          options.find((profile) => profile.mode === "local") ||
          options.find((profile) =>
            /\blocal|offline\b/i.test(profile.id + " " + profile.name)
          );
        return local?.id || "local_mode";
      }

      if (defaultIntent) {
        const defaultProfile = options.find((profile) => profile.id === "default");
        if (defaultProfile) return defaultProfile.id;
      }

      if (cloudIntent || defaultIntent) {
        const cloud =
          options.find((profile) => profile.mode === "cloud") ||
          options.find((profile) =>
            /\bcloud|remote\b/i.test(profile.id + " " + profile.name)
          );
        return cloud?.id || "default";
      }
      return null;
    },
    [availableProfiles]
  );
  const refreshLlmHealth = useCallback(async (options: { throwOnError?: boolean } = {}) => {
    try {
      const res = await api.get("/health/llm");
      const data = res?.data ?? {};
      const rawStatus = String(data?.status ?? "").trim().toLowerCase();
      const status: LlmHealthStatus =
        rawStatus === "online" || rawStatus === "offline" || rawStatus === "misconfigured"
          ? rawStatus
          : data?.ok
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
      logOnce("poll:health-llm", 10_000, () => {
        console.warn("[guardian] LLM health check failed", err);
      });
      if (options.throwOnError) {
        throw err;
      }
    }
  }, []);
  usePollWithBackoff(() => refreshLlmHealth({ throwOnError: true }), {
    intervalMs: LLM_HEALTH_POLL_MS,
    maxBackoffMs: 60_000,
    enabled: true,
    onErrorKey: "poll:health-llm",
    logTtlMs: 10_000,
  });
  const llmBackendUnavailable =
    llmHealth.status === "offline" || llmHealth.status === "misconfigured";
  const cloudProvidersDisabled = /ALLOW_CLOUD_PROVIDERS\s*=\s*false/i.test(
    llmHealth.error || ""
  );
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
  const requestProviderSwitch = useCallback(
    (options?: { openPopover?: boolean }) => {
      if (sessionTabs.length <= 0) {
        showToast("Provider selector unavailable in this view.");
        return;
      }
      if (options?.openPopover) {
        setPromptCostPopoverSection("providers");
        setPromptCostPopoverOpen(true);
      }
      setProviderMenuOpenSignal((prev) => prev + 1);
    },
    [sessionTabs.length, showToast]
  );
  const getDepthForThread = useCallback(
    (threadId: number): DepthMode =>
      lastCompletionDepthRef.current[threadId] ?? depth,
    [depth]
  );
  const fetchTraceForThread = useCallback(
    async (threadId: number, reason = "assistant-message") => {
      if (!Number.isFinite(threadId)) return;
      if (traceFetchInflightRef.current[threadId]) return;

      const endpoint =
        traceEndpointRef.current[threadId] ??
        `/api/chat/debug/rag-trace/${threadId}/latest`;

      traceFetchInflightRef.current[threadId] = true;
      try {
        const response = await api.get<RagTraceResponse>(endpoint);
        const payload = response?.data ?? null;
        if (!payload) return;

        const semantic = Array.isArray(payload?.documents)
          ? payload.documents
              .filter((doc): doc is RagTraceResponse["documents"][number] => {
                return Boolean(doc) && typeof doc === "object";
              })
              .map((doc) => ({
                text: doc.snippet || doc.title || "(untitled document)",
                score:
                  typeof doc.score === "number" && Number.isFinite(doc.score)
                    ? doc.score
                    : undefined,
                metadata: {
                  id: doc.id,
                  title: doc.title,
                },
              }))
          : [];

        const memory = Array.isArray(payload?.graph)
          ? payload.graph
              .filter((node) => Boolean(node) && typeof node === "object")
              .map((node) => ({
                text: node.text || "(graph node)",
                metadata: {
                  node_id: node.node_id,
                  kind: node.kind,
                },
              }))
          : [];

        setTrace({
          semantic,
          memory,
          depth: getDepthForThread(threadId),
          threadId,
        });
        console.debug(
          `[guardian] RAG trace refreshed for thread ${threadId} (${reason})`
        );
      } catch (error) {
        console.debug(
          `[guardian] RAG trace fetch failed for thread ${threadId} (${reason})`,
          error
        );
      } finally {
        traceFetchInflightRef.current[threadId] = false;
      }
    },
    [getDepthForThread]
  );
  type CompletionOutcome = "ok" | "service_unavailable" | "failed";
  // Helper: ask backend to complete the thread and then refresh
  const completeThread = async (tid: number): Promise<CompletionOutcome> => {
    const payload = buildChatCompletionPayload(depth, activeModelId || "default");
    try {
      const response = await api.post(buildChatCompletePath(tid), payload);
      console.log(`[guardian] Completing with depth=${depth}`);

      // Capture task_id for completion state tracking
      const taskId = response?.data?.task_id;
      const responseDepth = (response?.data?.depth_mode as DepthMode | undefined) ?? depth;
      lastCompletionDepthRef.current[tid] = responseDepth;

      if (taskId) {
        console.debug(`[guardian] Starting completion tracking: task=${taskId}`);
        startCompletion(tid, taskId);
      }

      const traceUrlRaw = response?.data?.trace_url;
      if (typeof traceUrlRaw === "string" && traceUrlRaw.trim().length > 0) {
        traceEndpointRef.current[tid] = traceUrlRaw;
      } else {
        delete traceEndpointRef.current[tid];
      }
      return "ok";
    } catch (err: any) {
      const statusCode = Number(err?.response?.status || 0);
      const detail = err?.response?.data?.detail;
      const reason =
        detail && typeof detail === "object"
          ? String(detail?.error || detail?.reason || "")
          : String(detail || "");
      if (
        statusCode === 503 &&
        (reason.includes("completion_service_unavailable") ||
          reason.includes("queue_unavailable") ||
          reason.includes("turn_lock_unavailable"))
      ) {
        showToast("Completion service unavailable — check Docker/Redis.");
        return "service_unavailable";
      }
      console.warn("[guardian] completion failed", err);
      return "failed";
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
    setCurrentThreadId((prev) => (prev === numericThreadId ? prev : numericThreadId));
  }, [numericThreadId]);

  const effectiveThreadId = currentThreadId ?? numericThreadId ?? null;

  const refreshPromptCostSummary = useCallback(async (threadId: number | null) => {
    try {
      const params = threadId != null ? { thread_id: threadId } : undefined;
      const data = await fetchSystemPromptSummary(params);
      setPromptCostSummary(data ?? null);
    } catch (error) {
      console.debug("[guardian] prompt cost summary refresh failed", error);
      setPromptCostSummary(null);
    }
  }, []);

  const applyProfileFallback = useCallback(() => {
    const fallbackThread = activeThreadRef.current as any;
    const fallbackId = normalizeProfileId(
      fallbackThread?.activeProfileId ??
        fallbackThread?.active_profile_id ??
        "default"
    );
    const fallbackMode = profileModeFromValue(
      fallbackThread?.profileMode ??
        fallbackThread?.providerOverride ??
        fallbackThread?.provider_override
    );
    setAvailableProfiles(PROFILE_FALLBACK_OPTIONS);
    setResolvedProfile({
      id: fallbackId,
      name: normalizeProfileName(fallbackThread?.profileName, fallbackId),
      mode: fallbackMode,
      providerOverride:
        fallbackThread?.providerOverride ??
        fallbackThread?.provider_override ??
        null,
      modelOverride:
        fallbackThread?.modelOverride ??
        fallbackThread?.model_override ??
        null,
    });
  }, []);

  const refreshThreadProfile = useCallback(
    async (
      threadId: number,
      options: { throwOnError?: boolean } = {}
    ) => {
      try {
        const response = await api.get(`/chat/${threadId}/profile`);
        const data = response?.data ?? {};
        const profileRaw = data?.profile ?? null;
        const profilesRaw = Array.isArray(data?.profiles) ? data.profiles : [];

        const parsedProfiles = profilesRaw
          .map((entry: any) => normalizeProfileOption(entry))
          .filter(Boolean) as SystemProfileOption[];

        if (parsedProfiles.length > 0) {
          setAvailableProfiles(parsedProfiles);
        } else {
          setAvailableProfiles(PROFILE_FALLBACK_OPTIONS);
        }

        const parsedProfile = normalizeProfileOption(profileRaw);
        if (parsedProfile) {
          setResolvedProfile({
            id: parsedProfile.id,
            name: parsedProfile.name,
            mode: parsedProfile.mode,
            providerOverride: parsedProfile.providerOverride || null,
            modelOverride: parsedProfile.modelOverride || null,
          });
          return parsedProfile;
        }
      } catch (err: any) {
        logOnce("poll:chat-profile", 10_000, () => {
          console.warn(
            `[guardian] profile refresh failed for thread ${threadId}`,
            err
          );
        });
        applyProfileFallback();
        if (options.throwOnError) {
          throw err;
        }
        return null;
      }

      applyProfileFallback();
      return null;
    },
    [applyProfileFallback]
  );

  const switchThreadProfile = useCallback(
    async (threadId: number, profileId: string): Promise<boolean> => {
      setProfileSwitching(true);
      try {
        const response = await api.post("/tools/execute", {
          name: "guardian.profile.switch",
          args: { thread_id: threadId, profile_id: profileId },
        });
        const result = response?.data?.result;
        if (result && result.ok === false) {
          const detail =
            typeof result.error === "string"
              ? result.error
              : "Profile switch failed";
          throw new Error(detail);
        }
        await refreshThreadProfile(threadId);
        emitThreadsRefresh("refresh", {
          reason: "profile-switch",
          id: String(threadId),
          profile_id: profileId,
        });
        return true;
      } catch (err: any) {
        const message =
          err?.message || "Unable to switch profile. Please try again.";
        showToast(message);
        return false;
      } finally {
        setProfileSwitching(false);
      }
    },
    [refreshThreadProfile, showToast]
  );

  useEffect(() => {
    if (effectiveThreadId == null) {
      applyProfileFallback();
      return;
    }
    void refreshThreadProfile(effectiveThreadId);
  }, [applyProfileFallback, effectiveThreadId, refreshThreadProfile]);

  usePollWithBackoff(
    async () => {
      if (effectiveThreadId == null) return;
      await refreshThreadProfile(effectiveThreadId, { throwOnError: true });
    },
    {
      intervalMs: THREAD_PROFILE_POLL_MS,
      maxBackoffMs: 60_000,
      enabled: effectiveThreadId != null,
      onErrorKey: "poll:chat-profile",
      logTtlMs: 10_000,
    }
  );

  useEffect(() => {
    setPromptCostPopoverOpen(false);
    setPromptCostPopoverSection("cost");
  }, [effectiveThreadId]);

  useEffect(() => {
    if (!promptCostPopoverOpen || typeof document === "undefined") return;
    const onDocumentPointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (promptCostPopoverRef.current?.contains(target)) return;
      setPromptCostPopoverOpen(false);
    };
    const onDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPromptCostPopoverOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocumentPointerDown);
    document.addEventListener("keydown", onDocumentKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocumentPointerDown);
      document.removeEventListener("keydown", onDocumentKeyDown);
    };
  }, [promptCostPopoverOpen]);

  const handlePromptCostToggle = useCallback(() => {
    setPromptCostPopoverSection("cost");
    setPromptCostPopoverOpen((previous) => {
      const next = !previous;
      if (next) {
        void refreshPromptCostSummary(effectiveThreadId);
      }
      return next;
    });
  }, [effectiveThreadId, refreshPromptCostSummary]);

  useEffect(() => () => triggerReload.cancel(), [triggerReload]);

  useEffect(() => {
    try {
      window.localStorage.setItem("cfy.voice.autoRead", autoReadEnabled ? "1" : "0");
    } catch {}
  }, [autoReadEnabled]);

  // Keep local thread title in sync with upstream threads when relevant
  useEffect(() => {
    const parsedId = Number(activeThread?.id);
    if (Number.isFinite(parsedId)) {
      if (currentThreadId == null || currentThreadId === parsedId) {
        setThreadTitle(activeThread?.title ?? NEW_THREAD_TITLE);
      }
    } else if (currentThreadId == null) {
      setThreadTitle(activeThread?.title ?? NEW_THREAD_TITLE);
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

    const offProfileSwitched = subscribe("thread.profile.switched", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const incomingId = Number(payload?.thread_id ?? payload?.threadId);
      if (
        Number.isFinite(incomingId) &&
        effectiveThreadId != null &&
        incomingId === effectiveThreadId
      ) {
        void refreshThreadProfile(incomingId);
      }
    });

    return () => {
      offThread();
      offProfileSwitched();
    };
  }, [effectiveThreadId, refreshThreadProfile, subscribe]);
  useEffect(() => {
    const offMessage = subscribe("message.created", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const tid = Number(payload?.thread_id ?? payload?.threadId);
      const role = String(payload?.role ?? "").trim().toLowerCase();
      if (!Number.isFinite(tid) || role !== "assistant") return;
      setTurnLockForThread(tid, false);
      void fetchTraceForThread(tid, "message-event");
    });

    return () => {
      offMessage();
    };
  }, [fetchTraceForThread, setTurnLockForThread, subscribe]);
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

    const nextTitle = (title && title.trim().length > 0) ? title.trim() : NEW_THREAD_TITLE;
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
    const suggestion = `${threadTitle || NEW_THREAD_TITLE} (branch)`;
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
    const requestedProfileId = resolveProfileIdFromCommand(text);
    const isProfileCommand =
      effectiveThreadId != null && Boolean(requestedProfileId);
    if (llmBackendUnavailable && !isProfileCommand) {
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
    if (effectiveThreadId != null && requestedProfileId) {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${effectiveThreadId}`);
      }
      try {
        await onSendMessage(text);
        const switched = await switchThreadProfile(
          effectiveThreadId,
          requestedProfileId
        );
        if (switched) {
          const selected =
            availableProfiles.find(
              (profile) => profile.id === requestedProfileId
            ) ||
            PROFILE_FALLBACK_OPTIONS.find(
              (profile) => profile.id === requestedProfileId
            );
          const label = selected?.name || requestedProfileId;
          await api.post(`/chat/${effectiveThreadId}/messages`, {
            role: "assistant",
            content: `Profile switched to ${label}. Next completion will use this profile.`,
            user_id: normalizedUserId,
          });
          triggerReload();
        }
      } catch (error) {
        console.error("[guardian] profile switch command failed", error);
        showToast("Profile switch failed.");
        throw error;
      }
      return;
    }
    if (!effectiveThreadId) {
      const firstLine = text.trim().split(/\n+/)[0] ?? "";
      const provisionalTitle = firstLine.slice(0, 60) || NEW_THREAD_TITLE;
      let createdThreadId: number | null = null;
      setPendingTurnLock(true);
      try {
        const resp = await api.post("/chat/messages", {
          thread_id: null,
          draft_tab_id: activeSessionTabId ?? undefined,
          role: "user",
          content: text,
          user_id: normalizedUserId,
          title: provisionalTitle,
        });
        const th = (resp && resp.data) || {};
        const newThreadId =
          th.thread_id ?? th.thread?.id ?? th.message?.thread_id ?? th.id ?? th.id_str;
        const numericNewId = Number(newThreadId);
        if (!Number.isFinite(numericNewId)) {
          console.warn("Unexpected create-on-send response:", th);
          throw new Error("Thread id missing from response");
        }
        createdThreadId = numericNewId;
        const derivedTitle = th.thread?.title ?? provisionalTitle;
        handleThreadCreated(numericNewId, derivedTitle);
        onThreadPersisted?.(numericNewId, derivedTitle);

        // Lock the new thread before requesting assistant completion.
        setTurnLockForThread(numericNewId, true);
        setPendingTurnLock(false);

        // Remove draft only after successful commit.
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${numericNewId}`);
        }

        // Complete the thread and refresh.
        const completionOutcome = await completeThread(numericNewId);
        if (completionOutcome !== "ok") {
          setTurnLockForThread(numericNewId, false);
          if (completionOutcome === "failed") {
            throw new Error("Assistant response failed.");
          }
          return;
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
            const completionOutcome = await completeThread(effectiveThreadId);
            if (completionOutcome !== "ok") {
              setTurnLockForThread(effectiveThreadId, false);
              if (completionOutcome === "failed") {
                showToast("Assistant response failed.");
              }
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

  const promptCostStatus: PromptCostStatus =
    promptCostSummary?.threshold?.status ?? "unknown";
  const showPromptCostDot =
    promptCostStatus === "warn" || promptCostStatus === "hard";

  const headerActions = (
    <div className="flex items-center gap-1">
      <div
        ref={promptCostPopoverRef}
        className="relative"
        data-testid="prompt-cost-popover-anchor"
      >
        <button
          type="button"
          className="icon-inline relative"
          aria-label="Prompt cost details"
          aria-expanded={promptCostPopoverOpen}
          aria-controls="prompt-cost-popover"
          onClick={handlePromptCostToggle}
          style={{ borderRadius: "var(--radius-micro)" }}
          data-testid="prompt-cost-trigger"
        >
          <Zap className="h-5 w-5" />
          {showPromptCostDot ? (
            <span
              className={`absolute right-[0.1rem] top-[0.1rem] h-1.5 w-1.5 rounded-full ${
                promptCostStatus === "hard" ? "bg-rose-400" : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
          ) : null}
        </button>
        {promptCostPopoverOpen ? (
          <div
            id="prompt-cost-popover"
            role="dialog"
            aria-label="Prompt cost"
            data-testid="prompt-cost-popover"
            className="absolute right-0 top-[calc(100%+0.4rem)] z-30 min-w-[16rem] rounded-lg border px-3 py-2 shadow-xl"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--panel-sheet)",
              color: "var(--text)",
            }}
          >
            <div
              className="mb-2 inline-flex items-center gap-1 rounded-full border p-1 text-[11px]"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <button
                type="button"
                className="rounded-full px-2 py-0.5 transition"
                data-state={promptCostPopoverSection === "cost" ? "active" : "inactive"}
                style={{
                  background:
                    promptCostPopoverSection === "cost"
                      ? "color-mix(in oklab, var(--panel-bg), var(--accent) 22%)"
                      : "transparent",
                }}
                onClick={() => setPromptCostPopoverSection("cost")}
              >
                Cost
              </button>
              <button
                type="button"
                className="rounded-full px-2 py-0.5 transition"
                data-state={
                  promptCostPopoverSection === "providers" ? "active" : "inactive"
                }
                style={{
                  background:
                    promptCostPopoverSection === "providers"
                      ? "color-mix(in oklab, var(--panel-bg), var(--accent) 22%)"
                      : "transparent",
                }}
                onClick={() => setPromptCostPopoverSection("providers")}
              >
                Providers
              </button>
            </div>
            {promptCostPopoverSection === "providers" ? (
              <div
                className="space-y-2 text-xs"
                data-testid="prompt-cost-providers-panel"
              >
                <div className="font-medium">Providers</div>
                <div className="opacity-85">
                  Open the provider picker from the session rail.
                </div>
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => requestProviderSwitch()}
                  data-testid="prompt-cost-open-provider"
                >
                  Open provider picker
                </button>
                {cloudProvidersDisabled ? (
                  <div className="opacity-80">Cloud providers disabled by config.</div>
                ) : null}
              </div>
            ) : (
              <PromptCostIndicator summary={promptCostSummary} variant="popover" />
            )}
          </div>
        ) : null}
      </div>
      <TraceButton threadId={effectiveThreadId} />
      <button
        type="button"
        className="icon-inline"
        aria-label={autoReadEnabled ? "Disable auto read aloud" : "Enable auto read aloud"}
        title={autoReadEnabled ? "Auto read aloud: On" : "Auto read aloud: Off"}
        onClick={() => setAutoReadEnabled((v) => !v)}
        style={{ borderRadius: "var(--radius-micro)", opacity: autoReadEnabled ? 1 : 0.65 }}
      >
        <Volume2 className="h-5 w-5" />
      </button>

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
                setThreadTitle(NEW_THREAD_TITLE);
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
                setThreadTitle(NEW_THREAD_TITLE);
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
        className="shrink-0 z-20 px-4 py-3"
      >
        <div
          className="relative flex items-center justify-between gap-2 rounded-full border px-3 py-2"
          style={{
            borderColor: "var(--panel-border)",
            background:
              "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 88%, transparent)",
            color: "var(--text)",
            boxShadow:
              "inset 0 1px 0 rgba(255,255,255,0.18), 0 8px 18px rgba(0,0,0,0.10)",
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
        </div>
      </header>

      {sessionTabs.length > 0 && (
        <SessionRail
          tabs={sessionTabs}
          activeTabId={activeSessionTabId}
          activeModelId={activeModelId || "default"}
          activeProfileId={resolvedProfile.id}
          activeProfileName={resolvedProfile.name}
          activeProfileMode={resolvedProfile.mode}
          profiles={availableProfiles}
          profileSwitching={profileSwitching}
          providerMenuOpenSignal={providerMenuOpenSignal}
          providerPickerOpenSignal={providerMenuOpenSignal}
          cloudProvidersDisabled={cloudProvidersDisabled}
          showTabs={sessionTabs.length > 1}
          onActivateTab={(tabId) => onSessionTabActivate?.(tabId)}
          onCloseTab={(tabId) => onSessionTabClose?.(tabId)}
          onOpenTab={() => (onSessionTabOpen ? onSessionTabOpen() : onNewChat())}
          onSetModel={(modelId) => onSessionModelChange?.(modelId)}
          onSetProfile={(profileId) => {
            if (effectiveThreadId == null) {
              showToast("Thread is not persisted yet.");
              return;
            }
            void switchThreadProfile(effectiveThreadId, profileId);
          }}
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
              title="Open provider selector"
              onClick={requestProviderSwitch}
            >
              Switch provider
            </button>
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
          {cloudProvidersDisabled ? (
            <div className="mt-1 opacity-80">Cloud providers disabled by config.</div>
          ) : null}
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
            autoReadEnabled={autoReadEnabled}
            depthMode={depth}
            profileId={resolvedProfile.id}
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
          {/* Bottom controls bar (aligned to bottom edge) */}
          <div className="mt-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {/* Voice mode indicator (icon-only, label via tooltip) */}
              <button
                type="button"
                className="icon-inline"
                aria-label="Turn-based voice"
                title="Turn-based voice"
                style={{ borderRadius: "var(--radius-micro)", opacity: 0.8 }}
                onClick={() => {
                  // purely informational affordance for now
                  console.debug("[guardian] turn-based voice affordance clicked");
                }}
              >
                <Volume2 className="h-4 w-4" />
              </button>

              {/* RAG Depth Selector (icon-only) */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="icon-inline"
                    aria-label="RAG depth selector"
                    title={`RAG Depth: ${depthLabels[depth]} — ${depthDescriptions[depth]}`}
                    style={{ borderRadius: "var(--radius-micro)" }}
                  >
                    <Layers className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="top"
                  align="start"
                  sideOffset={10}
                  collisionPadding={12}
                  className="z-[9999] min-w-[16rem] rounded-lg border p-1 shadow-xl"
                  style={{
                    borderColor: "var(--panel-border)",
                    background: "var(--panel-sheet)",
                    color: "var(--text)",
                  }}
                >
                  <div
                    className="px-2 py-1.5 text-xs font-semibold"
                    style={{ color: "var(--muted)", opacity: 0.85 }}
                  >
                    RAG Depth
                  </div>
                  {(["shallow", "normal", "deep", "diagnostic"] as DepthMode[]).map((d) => (
                    <DropdownMenuItem
                      key={d}
                      onClick={() => {
                        setDepth(d);
                        console.log(`[guardian] Depth changed to: ${d}`);
                      }}
                      className={
                        "cursor-pointer rounded-md px-2 py-2 focus:outline-none" +
                        (depth === d ? " bg-accent" : "")
                      }
                      style={{
                        background:
                          depth === d
                            ? "color-mix(in oklab, var(--panel-bg), var(--accent) 22%)"
                            : "transparent",
                      }}
                    >
                      <div className="flex flex-col flex-1 min-h-0">
                        <div className="font-medium">{depthLabels[d]}</div>
                        <div className="text-xs" style={{ color: "var(--muted)", opacity: 0.9 }}>
                          {depthDescriptions[d]}
                        </div>
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-md border px-2 py-1 text-xs hover:opacity-90 disabled:opacity-50"
                style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
                disabled={voiceUploading}
                onClick={() => {
                  if (effectiveThreadId == null) {
                    alert("Create or open a thread before starting a voice turn.");
                    return;
                  }
                  voiceFileInputRef.current?.click();
                }}
              >
                {voiceUploading ? "Processing…" : "Upload Voice Turn"}
              </button>

              <input
                ref={voiceFileInputRef}
                type="file"
                accept="audio/wav,audio/*"
                className="hidden"
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  event.currentTarget.value = "";
                  if (!file) return;
                  if (effectiveThreadId == null) {
                    alert("Create or open a thread before starting a voice turn.");
                    return;
                  }
                  setVoiceUploading(true);
                  try {
                    const form = new FormData();
                    form.append("thread_id", String(effectiveThreadId));
                    form.append("audio_file", file);
                    form.append("tts_enabled", "true");
                    await api.post("/api/voice/turn", form, {
                      headers: { "Content-Type": "multipart/form-data" },
                      timeout: 180000,
                    });
                    triggerReload();
                  } catch (error) {
                    console.warn("[guardian] voice turn failed", error);
                    alert("Voice turn failed. Check backend voice configuration.");
                  } finally {
                    setVoiceUploading(false);
                  }
                }}
              />
            </div>
          </div>
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
