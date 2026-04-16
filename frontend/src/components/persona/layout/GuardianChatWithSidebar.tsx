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
import { Thread, Message, type ThreadConfig } from "@/types/ui";
import { DocumentLike } from "@/types/documents";
import api from "@/lib/api";
import { fetchChatThread, moveChatThread } from "@/lib/api";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import WorkspacePane from "@/features/workspace/WorkspacePane";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import useImprintZero from "@/imprint/useImprintZero";
import ImprintZeroToast from "@/imprint/ImprintZeroToast";
import PromptCostIndicator from "@/features/chat/components/PromptCostIndicator";
import {
  InMemorySessionStateStore,
  RedisSessionStateStore,
} from "@/state/session/SessionStateStore";
import { SessionSpine } from "@/state/session/SessionSpine";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import { useRuntimeRouteCapabilities } from "@/lib/runtimeRouteCapabilities";
import {
  useSessionActiveDraft,
  useSessionActiveInferenceMode,
  useSessionActiveProviderId,
  useSessionActiveModelId,
  useSessionActiveTab,
  useSessionRailSlice,
} from "@/state/session/hooks";
import {
  DEFAULT_INFERENCE_MODE,
  DEFAULT_MODEL_ID,
  type TabId,
} from "@/state/session/types";
import {
  DEFAULT_COMPOSER_INFERENCE_MODE,
  type ComposerInferenceMode,
} from "@/types/inference";
import { getPreferredProviderSelection } from "@/lib/providerPref";
import {
  checkAuthGate,
  requireAuthReady,
  useAuthState,
} from "@/lib/authState";
import type { ProviderRuntimeState } from "@/contracts/runtimeTokens";
import type { DocumentContextTile } from "@/lib/documentContext";
import { useShellViewportProfile } from "./shellBreakpointContract";
import { getMobileShellProfile } from "./mobileShellProfile";

type PanelShellProps = React.PropsWithChildren<{
  className?: string;
  surfaceStyle?: React.CSSProperties;
  disabled?: boolean;
}>;

function PanelShell({ className, surfaceStyle, disabled, children }: PanelShellProps) {
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
}

const sameThreadSnapshot = (a: Thread, b: Thread): boolean => {
  const sameThreadConfig = (
    left: ThreadConfig | null | undefined,
    right: ThreadConfig | null | undefined
  ): boolean => {
    return (left?.providerId ?? null) === (right?.providerId ?? null)
      && (left?.modelId ?? null) === (right?.modelId ?? null)
      && (left?.inferenceMode ?? null) === (right?.inferenceMode ?? null)
      && (left?.retrievalSource ?? null) === (right?.retrievalSource ?? null)
      && (left?.personaId ?? null) === (right?.personaId ?? null);
  };

  return a.id === b.id
    && a.title === b.title
    && a.lastMessage === b.lastMessage
    && (a.unread ?? 0) === (b.unread ?? 0)
    && (a.projectId ?? null) === (b.projectId ?? null)
    && (a.projectName ?? null) === (b.projectName ?? null)
    && (a.lastInteractionAt ?? null) === (b.lastInteractionAt ?? null)
    && (a.parentId ?? null) === (b.parentId ?? null)
    && (a.archivedAt ?? null) === (b.archivedAt ?? null)
    && (a.activeProfileId ?? null) === (b.activeProfileId ?? null)
    && (a.providerOverride ?? null) === (b.providerOverride ?? null)
    && (a.modelOverride ?? null) === (b.modelOverride ?? null)
    && sameThreadConfig(a.threadConfig, b.threadConfig);
};

function normalizeThreadConfig(raw: unknown): ThreadConfig | null {
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      return normalizeThreadConfig(parsed);
    } catch {
      return null;
    }
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }

  const payload = raw as Record<string, unknown>;
  const providerId = String(
    payload.providerId ?? payload.provider_id ?? payload.provider ?? ""
  ).trim();
  const modelId = String(
    payload.modelId ?? payload.model_id ?? payload.model ?? ""
  ).trim();
  const inferenceMode = String(
    payload.inferenceMode ??
      payload.inference_mode ??
      payload.reasoningMode ??
      payload.reasoning_mode ??
      ""
  )
    .trim()
    .toLowerCase();
  if (!providerId || !modelId || !inferenceMode) {
    return null;
  }

  const retrievalSource = String(
    payload.retrievalSource ??
      payload.retrieval_source ??
      payload.sourceMode ??
      payload.source_mode ??
      "project"
  )
    .trim()
    .toLowerCase();
  const personaRaw = payload.personaId ?? payload.persona_id ?? null;
  const personaId =
    personaRaw == null ? null : String(personaRaw).trim() || null;

  return {
    providerId,
    modelId,
    inferenceMode,
    retrievalSource:
      retrievalSource === "personal_knowledge"
        ? "personal_knowledge"
        : "project",
    personaId,
  };
}

const DEVICE_ID_STORAGE_KEY = "cfy.deviceId";
const THREAD_PAGE_SIZE = 50;
const NEW_THREAD_TITLE = "New Thread";

function readStoredGeneralProjectId(): number | null {
  if (typeof window === "undefined") return null;
  const candidates = [
    window.localStorage.getItem("cfy.generalProjectId"),
    window.localStorage.getItem("cfy.defaultProjectId"),
  ];
  for (const raw of candidates) {
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return null;
}

function isDraftTitle(value: string | null | undefined): boolean {
  const normalized = (value ?? "").trim();
  return normalized === "New Thread" || normalized === "New Chat" || normalized === "Untitled Chat";
}

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

type GuardianChatWithSidebarProps = {
  guardianName: string;
  userName: string;
  userProfession?: string;
  prefill?: string;
  onPrefillConsumed?: () => void;
  pendingDocumentTiles?: DocumentContextTile[];
  onPendingDocumentTilesConsumed?: () => void;
  onWorkspaceToggle?: () => void;
  workspaceOpen?: boolean;
  activeWorkspaceDoc?: DocumentLike | null;
  onWorkspaceClose?: () => void;
  onWorkspaceOpenInThread?: (doc: DocumentLike | null) => void;
  providerRuntimeState?: ProviderRuntimeState | null;
};

export default function GuardianChatWithSidebar({
  guardianName,
  userName,
  userProfession = "",
  prefill,
  onPrefillConsumed,
  pendingDocumentTiles,
  onPendingDocumentTilesConsumed,
  onWorkspaceToggle,
  workspaceOpen = false,
  activeWorkspaceDoc = null,
  onWorkspaceClose,
  onWorkspaceOpenInThread,
  providerRuntimeState = null,
}: GuardianChatWithSidebarProps) {
  const auth = useAuthState();
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

  const [selectedProjectName, setSelectedProjectName] = React.useState<string | null>(null);

  const handleSelectedProjectChange = React.useCallback((id: string | null, name: string | null) => {
    setSelectedProjectId(id);
    setSelectedProjectName(name);
  }, []);

  // Persist sidebar visibility preference
  React.useEffect(() => {
    try {
      localStorage.setItem("cfy.sidebarVisible", String(isSidebarVisible));
    } catch { /* ignore */ }
  }, [isSidebarVisible]);
  const shellViewportProfile = useShellViewportProfile();
  const mobileShellProfile = useMemo(
    () => getMobileShellProfile(shellViewportProfile),
    [shellViewportProfile]
  );
  const isPhoneShell = mobileShellProfile.active;
  const isDesktopLayout = shellViewportProfile.sidebarArrangement === "split";
  const [threads, setThreads] = React.useState<Thread[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [threadsLoaded, setThreadsLoaded] = React.useState(false);
  const [threadsHasMore, setThreadsHasMore] = React.useState(true);
  const [threadsLoadingMore, setThreadsLoadingMore] = React.useState(false);
  const [sessionSpine, setSessionSpine] = React.useState<SessionSpine | null>(null);
  const [sessionReady, setSessionReady] = React.useState(false);
  const sessionHydratedRef = React.useRef(false);
  const paginationRef = React.useRef({ offset: 0, hasMore: true, loading: false });
  const threadsRef = React.useRef<Thread[]>([]);
  const { subscribe } = useLiveEvents({ passive: true });
  const { wallpaperUrl } = useWallpaperUrl();
  const {
    ready: routeCapabilitiesReady,
    states: routeCapabilityStates,
  } = useRuntimeRouteCapabilities([
    SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT,
    SUPPORTED_PROFILE_ROUTE_LABELS.UI_SESSION,
  ]);
  const imprintCapability =
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] ?? "unknown";
  const uiSessionCapability =
    routeCapabilityStates[SUPPORTED_PROFILE_ROUTE_LABELS.UI_SESSION] ??
    "unknown";
  const imprintZero = useImprintZero({
    enabled: routeCapabilitiesReady && imprintCapability !== "unavailable",
  });

  const resolveRouteThreadId = React.useCallback((): string | null => {
    if (typeof window === "undefined") return null;
    const match = window.location.pathname.match(/\/chat\/(\d+)/);
    if (match && match[1]) return match[1];
    return null;
  }, []);

  React.useEffect(() => {
    threadsRef.current = threads;
  }, [threads]);

  React.useEffect(() => {
    if (!routeCapabilitiesReady) {
      setSessionSpine(null);
      sessionHydratedRef.current = false;
      return;
    }
    if (typeof window === "undefined") return;
    const store =
      uiSessionCapability === "unavailable"
        ? new InMemorySessionStateStore()
        : new RedisSessionStateStore();
    const preferredSelection = getPreferredProviderSelection();
    const spine = new SessionSpine({
      userId: (userName || "default").trim() || "default",
      deviceId: getOrCreateDeviceId(),
      store,
      defaultProviderId: preferredSelection?.provider ?? null,
      defaultModelId: DEFAULT_MODEL_ID,
      defaultInferenceMode: DEFAULT_INFERENCE_MODE,
      canHydrate: () => requireAuthReady("session hydrate"),
      canPersist: () => requireAuthReady("session persist"),
    });

    setSessionSpine(spine);
    sessionHydratedRef.current = false;
  }, [routeCapabilitiesReady, uiSessionCapability, userName]);

  React.useEffect(() => {
    if (!sessionSpine) return;
    let cancelled = false;

    if (!auth.ready) {
      setSessionReady(false);
      sessionHydratedRef.current = false;
      return () => {
        cancelled = true;
      };
    }

    if (auth.status !== "authenticated") {
      setSessionReady(true);
      sessionHydratedRef.current = false;
      return () => {
        cancelled = true;
      };
    }

    if (sessionHydratedRef.current) {
      setSessionReady(true);
      return () => {
        cancelled = true;
      };
    }

    sessionHydratedRef.current = true;
    setSessionReady(false);
    void sessionSpine
      .hydrate({
        threadId: resolveRouteThreadId() ?? undefined,
        providerId: getPreferredProviderSelection()?.provider ?? null,
        modelId: DEFAULT_MODEL_ID,
        inferenceMode: DEFAULT_INFERENCE_MODE,
      })
      .finally(() => {
        if (!cancelled) setSessionReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, [auth.ready, auth.status, resolveRouteThreadId, sessionSpine]);
  const sessionRail = useSessionRailSlice(sessionSpine);
  const activeSessionTab = useSessionActiveTab(sessionSpine);
  const activeSessionTabId = sessionRail.activeTabId;
  const activeSessionProviderId = useSessionActiveProviderId(sessionSpine);
  const activeSessionModelId = useSessionActiveModelId(
    sessionSpine,
    DEFAULT_MODEL_ID
  );
  const activeSessionInferenceMode = useSessionActiveInferenceMode(
    sessionSpine,
    DEFAULT_COMPOSER_INFERENCE_MODE
  );
  const lastSessionSyncTabIdRef = React.useRef<TabId | null>(null);
  const activeSessionDraftSeed = useSessionActiveDraft(sessionSpine);
  const selectedProjectFilter = React.useMemo(() => {
    if (!selectedProjectId) return null;
    const parsed = Number(selectedProjectId);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [selectedProjectId]);
  const lastProjectScopeRef = React.useRef<string | null>(selectedProjectId ?? null);

  React.useEffect(() => {
    const nextScope = selectedProjectId ?? null;
    const prevScope = lastProjectScopeRef.current;
    lastProjectScopeRef.current = nextScope;

    const generalProjectId = readStoredGeneralProjectId();
    const isGeneralScope =
      nextScope == null
        || (generalProjectId != null && nextScope === String(generalProjectId));
    const wasGeneralScope =
      prevScope == null
        || (generalProjectId != null && prevScope === String(generalProjectId));

    if (!isGeneralScope || wasGeneralScope) return;

    if (activeId !== null) {
      setActiveId(null);
    }
    if (sessionSpine && activeSessionTabId) {
      sessionSpine.tabSetThread(activeSessionTabId, undefined, NEW_THREAD_TITLE);
    }
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/chat");
    }
  }, [activeId, activeSessionTabId, selectedProjectId, sessionSpine]);

  // Sync URL with session tab - only push when route differs to avoid loop.
  // Guard against stale session thread ids that no longer exist in the loaded list.
  React.useEffect(() => {
    if (!sessionReady || !activeSessionTab) return;
    const targetThreadId = activeSessionTab.threadId ?? null;
    const currentRouteThreadId = resolveRouteThreadId();
    const targetMissingFromThreads =
      targetThreadId != null &&
      threadsLoaded &&
      !threads.some((thread) => thread.id === targetThreadId);
    const shouldClearMissingTarget =
      selectedProjectFilter == null &&
      !threadsHasMore &&
      !threadsLoadingMore;

    if (targetMissingFromThreads) {
      if (!shouldClearMissingTarget) {
        // Keep session linkage intact: filtered/paginated lists can omit a valid thread.
        return;
      }
      if (activeId !== null) {
        setActiveId(null);
      }
      if (sessionSpine && activeSessionTabId) {
        // Clear stale thread linkage once so tab state stops forcing an invalid route id.
        sessionSpine.tabSetThread(activeSessionTabId, undefined, undefined);
      }
      if (currentRouteThreadId !== null && typeof window !== "undefined") {
        window.history.replaceState({}, "", "/chat");
      }
      return;
    }

    if (targetThreadId === activeId) return;
    setActiveId(targetThreadId);
    // Only push state if the route actually differs from target
    if (currentRouteThreadId !== targetThreadId && typeof window !== "undefined") {
      const newPath = targetThreadId ? `/chat/${targetThreadId}` : "/chat";
      window.history.replaceState({}, "", newPath);
    }
  }, [
    activeId,
    activeSessionTab,
    activeSessionTabId,
    resolveRouteThreadId,
    sessionReady,
    sessionSpine,
    selectedProjectFilter,
    threads,
    threadsHasMore,
    threadsLoaded,
    threadsLoadingMore,
  ]);

  // Sync sessionSpine with active thread - only depends on primitives needed to initiate side effect
  React.useEffect(() => {
    if (!sessionReady || !sessionSpine || !activeSessionTabId) return;
    const sessionTabChanged = lastSessionSyncTabIdRef.current !== activeSessionTabId;
    lastSessionSyncTabIdRef.current = activeSessionTabId;
    if (!activeId) return;
    if (
      sessionTabChanged &&
      (activeSessionTab?.threadId ?? null) !== activeId
    ) {
      return;
    }
    const activeThread = threads.find((thread) => thread.id === activeId);
    sessionSpine.tabSetThread(
      activeSessionTabId,
      activeId,
      activeThread?.title || undefined
    );
  }, [
    activeId,
    activeSessionTab?.threadId,
    activeSessionTabId,
    sessionReady,
    sessionSpine,
    threads,
  ]);
  const isSidebarOpen = isDesktopLayout ? isSidebarVisible : isMobileSidebarOpen;
  const isMobileOverlayActive = !isDesktopLayout && isSidebarOpen;
  const guardianLayoutMode = mobileShellProfile.guardian.singleLane
    ? "single_lane"
    : isDesktopLayout
      ? "split"
      : "collapsed_drawer";

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
      const projectNameVal = raw.project_name ?? raw.projectName ?? null;
      const lastInteractionAtVal =
        raw.last_interaction_at ?? raw.lastInteractionAt ?? null;
      const parentVal = raw.parent_id ?? raw.parentId ?? null;
      const archivedVal = raw.archived_at ?? raw.archivedAt ?? null;
      const activeProfileVal =
        raw.active_profile_id ?? raw.activeProfileId ?? null;
      const providerOverrideVal =
        raw.provider_override ?? raw.providerOverride ?? null;
      const modelOverrideVal = raw.model_override ?? raw.modelOverride ?? null;
      const threadConfig = normalizeThreadConfig(
        raw.thread_config ?? raw.threadConfig ?? null
      );
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
        projectName: projectNameVal != null ? String(projectNameVal) : null,
        lastInteractionAt:
          lastInteractionAtVal != null ? String(lastInteractionAtVal) : null,
        parentId: parentVal != null ? String(parentVal) : null,
        archivedAt: archivedVal ? String(archivedVal) : null,
        activeProfileId:
          activeProfileVal != null ? String(activeProfileVal) : null,
        providerOverride:
          providerOverrideVal != null ? String(providerOverrideVal) : null,
        modelOverride:
          modelOverrideVal != null ? String(modelOverrideVal) : null,
        threadConfig,
        metadata: metadata,
      };
    },
    [guardianName, userName]
  );

  const handleNewChat = React.useCallback(async () => {
    setActiveId(null);
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/chat");
    }
    if (sessionSpine) {
      sessionSpine.tabOpen(undefined, NEW_THREAD_TITLE);
    }
    return null;
  }, [sessionSpine]);

  const handleSessionTabOpen = React.useCallback(() => {
    if (!sessionSpine) {
      void handleNewChat();
      return;
    }
    setActiveId(null);
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/chat");
    }
    sessionSpine.tabOpen(undefined, NEW_THREAD_TITLE);
  }, [handleNewChat, sessionSpine]);

  const handleSessionTabActivate = React.useCallback((tabId: TabId) => {
    const nextTab = sessionRail.tabs.find((tab) => tab.tabId === tabId) ?? null;
    const nextThreadId = nextTab?.threadId ?? null;
    setActiveId(nextThreadId);
    if (typeof window !== "undefined") {
      const nextPath = nextThreadId ? `/chat/${nextThreadId}` : "/chat";
      window.history.replaceState({}, "", nextPath);
    }
    sessionSpine?.tabActivate(tabId);
    // Sync sidebar project selection to the activated tab's thread project.
    const tabProjectId = nextTab?.projectId ?? null;
    setSelectedProjectId(tabProjectId);
    setSelectedProjectName(tabProjectId != null ? (nextTab?.projectName ?? null) : null);
  }, [sessionRail.tabs, sessionSpine]);

  const handleSessionTabClose = React.useCallback((tabId: TabId) => {
    sessionSpine?.tabClose(tabId);
  }, [sessionSpine]);

  const handleSessionModelChange = React.useCallback((modelId: string) => {
    if (!sessionSpine || !activeSessionTabId) return;
    sessionSpine.tabSetModel(activeSessionTabId, modelId);
  }, [activeSessionTabId, sessionSpine]);

  const handleSessionProviderChange = React.useCallback((providerId: string | null) => {
    if (!sessionSpine || !activeSessionTabId) return;
    sessionSpine.tabSetProvider(activeSessionTabId, providerId);
  }, [activeSessionTabId, sessionSpine]);

  const handleSessionInferenceModeChange = React.useCallback(
    (mode: ComposerInferenceMode) => {
      if (!sessionSpine || !activeSessionTabId) return;
      sessionSpine.tabSetInferenceMode(activeSessionTabId, mode);
    },
    [activeSessionTabId, sessionSpine]
  );

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
      console.debug('[prompt] embed unavailable — optional enrichment skipped', err);
    }
  }

  const mergeThreadsPage = React.useCallback(
    (existing: Thread[], incoming: Thread[], reset: boolean): Thread[] => {
      const next = reset ? [] : existing.map((thread) => ({ ...thread }));
      const indexById = new Map<string, number>();
      for (let i = 0; i < next.length; i += 1) {
        const id = String(next[i]?.id ?? "");
        if (!id || indexById.has(id)) continue;
        indexById.set(id, i);
      }
      for (const thread of incoming) {
        const id = String(thread.id ?? "");
        if (!id) continue;
        const existingIndex = indexById.get(id);
        if (existingIndex != null) {
          next[existingIndex] = thread;
          continue;
        }
        indexById.set(id, next.length);
        next.push(thread);
      }
      return next;
    },
    []
  );

  // ----- Thread loader (hoisted early to avoid TDZ) -----
  const loadThreads = React.useCallback(async ({ reset = false }: { reset?: boolean } = {}) => {
    if (!checkAuthGate(auth, "threads load")) {
      return;
    }
    if (!reset && (paginationRef.current.loading || !paginationRef.current.hasMore)) {
      return;
    }
    const offset = reset ? 0 : paginationRef.current.offset;
    paginationRef.current.loading = true;
    setThreadsLoadingMore(true);
    try {
      const generalProjectId = readStoredGeneralProjectId();
      const projectFilter =
        selectedProjectFilter != null
          && !(generalProjectId != null && selectedProjectFilter === generalProjectId)
          ? selectedProjectFilter
          : null;
      const res = await api.get("/chat/threads", {
        params: {
          limit: THREAD_PAGE_SIZE,
          offset,
          ...(projectFilter != null ? { project_id: projectFilter } : {}),
        },
      });
      const data = res?.data;
      const rawList = Array.isArray(data?.threads)
        ? data.threads
        : Array.isArray(data)
        ? data
        : [];

      const mapped = rawList.map(mapThreadRecord).filter(Boolean);
      // Deduplicate by thread id
      const dedupedMap = new Map<string, Thread>();
      for (const thread of mapped) {
        if (thread && thread.id) dedupedMap.set(thread.id, thread);
      }
      const visible = Array.from(dedupedMap.values()).filter((t) => !t.archivedAt);
      const existingThreads = reset ? [] : threadsRef.current;
      const merged = mergeThreadsPage(existingThreads, visible, reset);
      threadsRef.current = merged;
      setThreads(merged);

      const rawCount = rawList.length;
      const nextOffsetFromBackend = Number(data?.next_offset);
      const computedNextOffset =
        Number.isFinite(nextOffsetFromBackend) && nextOffsetFromBackend > offset
          ? nextOffsetFromBackend
          : offset + rawCount;
      const backendHasMore =
        typeof data?.has_more === "boolean"
          ? data.has_more
          : rawCount >= THREAD_PAGE_SIZE;
      const hasMore = rawCount > 0 && backendHasMore;
      paginationRef.current.offset = computedNextOffset;
      paginationRef.current.hasMore = hasMore;
      setThreadsHasMore(hasMore);
    } catch (err) {
      console.warn("[guardian] failed to load threads", err);
      // Preserve last-known list when refresh fails; avoid transient UI data loss.
    } finally {
      paginationRef.current.loading = false;
      setThreadsLoadingMore(false);
      setThreadsLoaded(true);
    }
  }, [auth, mapThreadRecord, mergeThreadsPage, selectedProjectFilter]);

  const handleDeleteThreadStateSync = React.useCallback(
    (threadId: string) => {
      const normalizedId = String(threadId ?? "").trim();
      if (!normalizedId) return;

      const current = threadsRef.current;
      const removedIndex = current.findIndex(
        (thread) => thread.id === normalizedId
      );
      if (removedIndex === -1) return;

      const remaining = current.filter((thread) => thread.id !== normalizedId);
      threadsRef.current = remaining;
      setThreads(remaining);

      const activeThreadDeleted = activeId === normalizedId;
      const activeTabThreadDeleted =
        (activeSessionTab?.threadId ?? null) === normalizedId;
      if (!activeThreadDeleted && !activeTabThreadDeleted) {
        return;
      }

      const fallbackThread =
        remaining[removedIndex] ??
        remaining[Math.max(0, removedIndex - 1)] ??
        null;
      const nextActiveId = fallbackThread?.id ?? null;
      const nextActiveTitle = fallbackThread?.title ?? NEW_THREAD_TITLE;

      setActiveId(nextActiveId);
      if (sessionSpine && activeSessionTabId) {
        sessionSpine.tabSetThread(
          activeSessionTabId,
          nextActiveId ?? undefined,
          nextActiveTitle
        );
        sessionSpine.cancelActiveCompletion({
          threadId: normalizedId,
          restoreDraft: false,
        });
      }
      if (typeof window !== "undefined") {
        window.history.replaceState(
          {},
          "",
          nextActiveId ? `/chat/${nextActiveId}` : "/chat"
        );
      }
    },
    [activeId, activeSessionTab?.threadId, activeSessionTabId, sessionSpine]
  );

  const handleBeforeDeleteThread = React.useCallback(
    (threadId: string): string | null => {
      const normalizedId = String(threadId ?? "").trim();
      if (!normalizedId || !sessionSpine) return null;
      const activeCompletionThreadId =
        sessionSpine.getActiveCompletion()?.threadId ?? null;
      if (
        activeCompletionThreadId !== normalizedId ||
        !sessionSpine.isComposerBlocked()
      ) {
        return null;
      }
      sessionSpine.cancelActiveCompletion({
        threadId: normalizedId,
        restoreDraft: false,
      });
      if (!sessionSpine.isComposerBlocked()) {
        return null;
      }
      return "Finish or cancel the current assistant reply before deleting this thread.";
    },
    [sessionSpine]
  );

  const handleDeleteThread = React.useCallback(
    async (threadId: string) => {
      handleDeleteThreadStateSync(threadId);
    },
    [handleDeleteThreadStateSync]
  );

  React.useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onThreadsRefresh = (event: Event) => {
      const detail = (event as CustomEvent)?.detail ?? {};
      const kind = detail?.kind ?? detail?.type;
      if (kind === "delete") {
        const deletedThreadId = detail?.id ?? detail?.thread_id ?? detail?.threadId;
        if (deletedThreadId != null) {
          handleDeleteThreadStateSync(String(deletedThreadId));
        }
        return;
      }
      if (kind !== "refresh" && kind !== "import" && kind !== "create") return;
      void loadThreads({ reset: true });
    };
    window.addEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
    return () => window.removeEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
  }, [handleDeleteThreadStateSync, loadThreads]);

  React.useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onDraftThreadRequested = () => {
      void handleNewChat();
    };
    window.addEventListener("cfy:chat:new-draft", onDraftThreadRequested as EventListener);
    return () =>
      window.removeEventListener("cfy:chat:new-draft", onDraftThreadRequested as EventListener);
  }, [handleNewChat]);

  // Initial load only
  React.useEffect(() => {
    void loadThreads({ reset: true });
  }, [loadThreads]);

  const handleBranchThread = React.useCallback(
    async (threadId: number, options?: { title?: string }) => {
      if (!checkAuthGate(auth, "threads branch")) return;
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
    [auth, mapThreadRecord]
  );

  const handleArchiveThread = React.useCallback(
    async (threadId: number) => {
      if (!checkAuthGate(auth, "threads archive")) return;
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
    [activeId, auth]
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


  // Never auto-select on list refresh. If selected thread disappears, clear it.
  React.useEffect(() => {
    if (!threadsLoaded) return;
    if (!activeId) return;
    if (threads.some((thread) => thread.id === activeId)) return;
    setActiveId(null);
  }, [
    threadsLoaded,
    activeId,
    threads,
  ]);

  React.useEffect(() => {
    const onPopstate = () => {
      const routeId = resolveRouteThreadId();
      if (!routeId) {
        setActiveId(null);
        return;
      }
      setActiveId((prev) => (prev === routeId ? prev : routeId));
      if (threadsLoaded && !threads.some((t) => t.id === routeId)) {
        void loadThreads({ reset: true });
      }
    };
    if (typeof window !== "undefined") {
      window.addEventListener("popstate", onPopstate);
      return () => window.removeEventListener("popstate", onPopstate);
    }
  }, [loadThreads, resolveRouteThreadId, threads, threadsLoaded]);

  const loadMoreThreads = React.useCallback(async () => {
    if (!threadsHasMore || threadsLoadingMore) {
      return;
    }
    await loadThreads({ reset: false });
  }, [loadThreads, threadsHasMore, threadsLoadingMore]);

  const activeThread = React.useMemo(() => {
    let found = threads.find((t) => t.id === activeId) || null;
    if (found) return found;
    return {
      id: "temp",
      title: NEW_THREAD_TITLE,
      lastMessage: "",
      unread: 0,
      participants: [
        { id: "me", name: userName || "You" },
        { id: "bot", name: guardianName || "Guardian" },
      ],
      messages: [],
      projectId: selectedProjectId,
      projectName: selectedProjectName,
      lastInteractionAt: null,
    };
  }, [threads, activeId, userName, guardianName, selectedProjectId, selectedProjectName]);

  const handleNewChatImmediate = () => {
    void handleNewChat();
  };

  const handleSendMessage = async (
    text: string,
    options?: { threadIdOverride?: number }
  ) => {
    if (!activeId) return;
    const threadKey = activeId;
    const numericThreadId = Number(threadKey);
    const userMsgId = String(Math.random());
    const contextProjectIdRaw =
      selectedProjectId != null ? Number(selectedProjectId) : null;
    const contextProjectId = Number.isFinite(contextProjectIdRaw)
      ? contextProjectIdRaw
      : null;
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
        return {
          ...t,
          messages: [...t.messages, userMsg],
          lastInteractionAt: new Date().toISOString(),
        };
      })
    );

    if (!Number.isFinite(numericThreadId)) return;

    try {
      // Persist the message and then refresh the authoritative thread snapshot.
      await api.post(`/chat/${numericThreadId}/messages`, {
        role: "user",
        content: text,
        metadata: isLikelyPrompt(text) ? { type: "prompt" } : undefined,
        project_id: contextProjectId ?? undefined,
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

      const refreshed = await fetchChatThread(numericThreadId);
      const authoritativeThread = refreshed?.thread;
      if (authoritativeThread) {
        const mapped = mapThreadRecord(authoritativeThread);
        if (mapped) {
          setThreads((prev) =>
            prev.map((thread) =>
              thread.id === mapped.id
                ? {
                    ...mapped,
                    messages: thread.messages,
                  }
                : thread
            )
          );
        }
      }
    } catch (err) {
      console.warn("[guardian] failed to persist user message", err);
      const status = (err as any)?.response?.status;
      const payload = (err as any)?.response?.data ?? {};
      const errorCode = String(payload?.error ?? payload?.code ?? "")
        .trim()
        .toLowerCase();
      const detail = String(payload?.detail ?? payload?.message ?? "")
        .trim()
        .toLowerCase();
      const retryAfterRaw = Number(
        payload?.retry_after
          ?? (err as any)?.response?.headers?.["retry-after"]
          ?? 0
      );
      const retryAfterSeconds = Number.isFinite(retryAfterRaw)
        ? Math.max(0, Math.ceil(retryAfterRaw))
        : 0;

      // Surface per-thread turn lock errors as a friendly retry prompt.
      const isTurnInFlight =
        errorCode === "turn_in_flight"
        || detail.includes("turn_in_flight")
        || detail.includes("assistant is responding");

      const message = isTurnInFlight
        ? "One moment—finish the current reply first."
        : status === 429
          ? retryAfterSeconds > 0
            ? `Too many requests right now. Try again in ${retryAfterSeconds}s.`
            : "Too many requests right now. Please wait a moment and retry."
          : "Failed to send message.";
      throw new Error(message);
    }
  };

  const handleDraftThreadPersisted = React.useCallback(
    (
      threadId: number,
      title?: string,
      options?: { tabId?: TabId | null }
    ) => {
      const idStr = String(threadId);
      const nextTitle = (title || "").trim() || NEW_THREAD_TITLE;
      const targetTabId = options?.tabId ?? activeSessionTabId;
      const shouldPromoteVisibleTab =
        !targetTabId || targetTabId === activeSessionTabId;
      if (shouldPromoteVisibleTab) {
        setActiveId(idStr);
      }
      setThreads((prev) => {
        const existing = prev.find((thread) => thread.id === idStr);
        if (existing) {
          return prev.map((thread) =>
            thread.id === idStr ? { ...thread, title: nextTitle } : thread
          );
        }
        const synthetic: Thread = {
          id: idStr,
          title: nextTitle,
          lastMessage: "",
          unread: 0,
          participants: [
            { id: "me", name: userName || "You" },
            { id: "bot", name: guardianName || "Guardian" },
          ],
          messages: [],
        };
        return [synthetic, ...prev];
      });
      if (sessionSpine && targetTabId) {
        sessionSpine.tabSetThread(targetTabId, idStr, nextTitle);
      }
      if (shouldPromoteVisibleTab && typeof window !== "undefined") {
        window.history.replaceState({}, "", `/chat/${idStr}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("cfy:threads:refresh", {
            detail: { kind: "create", id: idStr },
          })
        );
      }
    },
    [activeSessionTabId, guardianName, sessionSpine, userName]
  );

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
          void loadThreads({ reset: true });
          return prev;
        }
        const idx = prev.findIndex((t) => t.id === threadId);
        if (idx === -1) {
          // New thread we don't know about? Load to be safe, or ignore
          void loadThreads({ reset: true });
          return prev;
        }
        const target = prev[idx];
        const unread = threadId === activeId ? 0 : (target.unread ?? 0) + 1;
        const updated: Thread = {
          ...target,
          lastMessage: content || target.lastMessage,
          lastInteractionAt: new Date().toISOString(),
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
            projectName:
              threadPayload?.project_name ?? threadPayload?.projectName ?? t.projectName,
            lastInteractionAt:
              threadPayload?.last_interaction_at ?? threadPayload?.lastInteractionAt ?? t.lastInteractionAt,
            archivedAt: threadPayload?.archived_at ?? threadPayload?.archivedAt ?? t.archivedAt,
            threadConfig: normalizeThreadConfig(
              threadPayload?.thread_config ??
                threadPayload?.threadConfig ??
                t.threadConfig
            ),
          };
          if (!sameThreadSnapshot(t, updated)) {
            touched = true;
          }
          return updated;
        });
        return touched ? next : prev;
      });
    });

    const offThreadMoved = subscribe("thread.moved", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      console.info("[live] thread.moved", payload);
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
            projectId:
              threadPayload?.project_id ?? threadPayload?.projectId ?? t.projectId,
            projectName:
              threadPayload?.project_name ?? threadPayload?.projectName ?? t.projectName,
            lastInteractionAt:
              threadPayload?.last_interaction_at ?? threadPayload?.lastInteractionAt ?? t.lastInteractionAt,
          };
          if (!sameThreadSnapshot(t, updated)) {
            touched = true;
          }
          return updated;
        });
        return touched ? next : prev;
      });
    });

    const offProfileSwitched = subscribe("thread.profile.switched", (event) => {
      const payload = (event.data as any)?.data ?? event.data;
      const tid = payload?.thread_id ?? payload?.threadId;
      if (!tid) return;
      const idStr = String(tid);
      const activeProfileId =
        payload?.active_profile_id ?? payload?.activeProfileId ?? null;
      const providerOverride =
        payload?.provider_override ?? payload?.providerOverride ?? null;
      const modelOverride =
        payload?.model_override ?? payload?.modelOverride ?? null;
      setThreads((prev) =>
        prev.map((thread) =>
          thread.id !== idStr
            ? thread
            : {
                ...thread,
                activeProfileId:
                  activeProfileId != null ? String(activeProfileId) : null,
                providerOverride:
                  providerOverride != null ? String(providerOverride) : null,
                modelOverride:
                  modelOverride != null ? String(modelOverride) : null,
              }
        )
      );
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
          void loadThreads({ reset: true });
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
          void loadThreads({ reset: true });
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
          void loadThreads({ reset: true });
      }
    });

    return () => {
      offMessage();
      offThreadUpdated();
      offThreadMoved();
      offProfileSwitched();
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
  const showWorkspacePreview = workspaceOpen && activeWorkspaceDoc != null;

  const sidebarWrapperClass = "relative flex h-full min-h-0 shrink-0 basis-[clamp(300px,24vw,360px)]";
  const stopDrawerEvent = React.useCallback((event: React.SyntheticEvent) => {
    event.stopPropagation();
  }, []);

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
              width: mobileShellProfile.guardian.drawerWidth,
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
                    projectName={selectedProjectName}
                    onProjectChange={handleSelectedProjectChange}
                    hasMoreThreads={threadsHasMore}
                    loadingMoreThreads={threadsLoadingMore}
                    onLoadMoreThreads={loadMoreThreads}
                    onBeforeDeleteThread={handleBeforeDeleteThread}
                    onDeleteThread={handleDeleteThread}
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
        className={clsx(
          "relative h-full w-full min-h-0 overflow-hidden box-border items-stretch mx-auto",
          isPhoneShell ? "flex flex-col" : "grid"
        )}
        data-guardian-layout={guardianLayoutMode}
        data-shell-profile={mobileShellProfile.shellMode}
        style={{
          maxWidth: mobileShellProfile.guardian.frameMaxWidth,
          gridTemplateColumns:
            !isPhoneShell && isDesktopLayout && isSidebarOpen
              ? "clamp(300px, 24vw, 360px) minmax(0, 1fr)"
              : "1fr",
          gap: "var(--gutter)",
          padding: "0px",
          boxSizing: "border-box",
          transition: isPhoneShell
            ? undefined
            : "grid-template-columns 0.2s ease-out",
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
                  projectName={selectedProjectName}
                  onProjectChange={handleSelectedProjectChange}
                  hasMoreThreads={threadsHasMore}
                  loadingMoreThreads={threadsLoadingMore}
                  onLoadMoreThreads={loadMoreThreads}
                  onBeforeDeleteThread={handleBeforeDeleteThread}
                  onDeleteThread={handleDeleteThread}
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
              <PromptCostIndicator summary={imprintZero.status?.system_prompt_meta} />
              {auth.ready && auth.status === "unauthenticated" && (
                <div
                  className="mx-4 mt-3 rounded-lg border px-3 py-2 text-xs"
                  style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
                >
                  Authentication required. Please sign in or set a dev key.
                </div>
              )}
              {showWorkspacePreview && (
                <div className="absolute inset-0 z-[110] pointer-events-auto">
                  <div className="absolute right-0 top-0 h-full w-[min(420px,90vw)] bg-black/50 backdrop-blur-md border-l border-white/10 shadow-2xl overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
                      <div className="text-sm font-semibold text-white">Workspace</div>
                      <button
                        onClick={onWorkspaceClose}
                        className="text-white/70 hover:text-white"
                      >
                        ×
                      </button>
                    </div>
                    <div className="h-[calc(100%-42px)] overflow-auto">
                      <WorkspacePane
                        activeDoc={activeWorkspaceDoc}
                        onOpenInThread={onWorkspaceOpenInThread}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden flex flex-col">
              <GuardianChat
                guardianName={guardianName}
                userName={userName}
                userProfession={userProfession}
                prefill={prefill}
                onPrefillConsumed={onPrefillConsumed}
                pendingDocumentTiles={pendingDocumentTiles}
                onPendingDocumentTilesConsumed={onPendingDocumentTilesConsumed}
                onWorkspaceToggle={onWorkspaceToggle}
                workspaceOpen={workspaceOpen}
                providerRuntimeState={providerRuntimeState}
                activeThread={activeThread}
                  workspaceProjectId={selectedProjectId}
                  onSendMessage={handleSendMessage}
                  onThreadPersisted={handleDraftThreadPersisted}
                  onNewChat={handleNewChatImmediate}
                  onBranchThread={handleBranchThread}
                  onArchiveThread={handleArchiveThread}
                  onSidebarToggle={toggleSidebar}
                  isSidebarVisible={isSidebarOpen}
                  sessionTabs={sessionRail.tabs}
                  activeSessionTabId={activeSessionTabId}
                  activeProviderId={activeSessionProviderId}
                  activeModelId={activeSessionModelId}
                  activeInferenceMode={activeSessionInferenceMode}
                  activeDraft={activeSessionDraftSeed}
                  onSessionTabActivate={handleSessionTabActivate}
                  onSessionTabClose={handleSessionTabClose}
                  onSessionTabOpen={handleSessionTabOpen}
                  onSessionProviderChange={handleSessionProviderChange}
                  onSessionModelChange={handleSessionModelChange}
                  onSessionInferenceModeChange={
                    handleSessionInferenceModeChange
                  }
                  onSessionDraftChange={handleSessionDraftChange}
                  onBack={() => {
                    setActiveId(null);
                    if (sessionSpine && activeSessionTabId) {
                      sessionSpine.tabSetThread(activeSessionTabId, undefined, NEW_THREAD_TITLE);
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
