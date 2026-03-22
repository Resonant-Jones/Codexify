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
  SquareStack,
  Zap,
  Volume2,
} from "lucide-react";
import { Thread } from "@/types/ui";
import { Composer } from "./components";
import type { ComposerSendOptions } from "./components/Composer";
import ChatView from "@/features/chat/ChatView";
import useChat from "@/features/chat/useChat";
import api, {
  buildChatCompletePath,
  clearInFlightCompletionTurnId,
  getInFlightCompletionTurnId,
} from "@/lib/api";
import { buildChatCompletionPayload } from "@/lib/chatClient";
import { isRagTraceUIEnabled } from "@/lib/devFlags";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import FrameCard from "@/components/surface/FrameCard";
import { setTrace } from "@/state/contextTrace";
import PromptCostIndicator from "./components/PromptCostIndicator";
import RAGTracePanel from "./panels/RAGTracePanel";
import SessionRail from "@/components/SessionRail/SessionRail";
import GuardianThreadApprovalRail from "@/features/chat/components/GuardianThreadApprovalRail";
import { getWrappedSessionTabId } from "@/state/session/hooks";
import type { SessionTab, TabId } from "@/state/session/types";
import type { RagTraceResponse } from "@/types/rag";
import { fetchSystemPromptSummary, type PromptCostStatus, type SystemPromptSummary } from "@/imprint/api";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import { logOnce } from "@/lib/logging/logOnce";
import { useLlmCatalog } from "@/features/chat/hooks/useLlmCatalog";
import { useInferenceRequestState } from "@/features/chat/hooks/useInferenceRequestState";
import {
  createIdleInferenceRequestState,
  DEFAULT_COMPOSER_INFERENCE_MODE,
  isActiveInferencePhase,
  type ComposerInferenceMode,
} from "@/types/inference";
import { setPreferredProviderSelection } from "@/lib/providerPref";
import { SystemProfiles } from "@/dcw-services/gc";


const DRAFT_KEY_PREFIX = "gc-draft:";
const TURN_LOCK_TOAST =
  "Keep typing. Send unlocks when the current reply finishes.";
const LLM_HEALTH_POLL_MS = 15000;
const THREAD_PROFILE_POLL_MS = 15000;
const NEW_THREAD_TITLE = "New Thread";

export function flattenChatEventPayload(data: unknown): Record<string, unknown> {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return {};
  }

  const payload = data as Record<string, unknown>;
  const nested = payload.data;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return {
      ...(nested as Record<string, unknown>),
      ...payload,
    };
  }

  return payload;
}

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
  rawError: string | null;
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

type VoiceCapabilities = {
  read_aloud_enabled: boolean;
  turn_based_enabled: boolean;
  supported_input_mime: string[];
  limits: { max_upload_bytes: number; max_duration_s: number } | null;
};

type VoiceCapabilitiesStatus = "loading" | "ready" | "error";

const DEFAULT_VOICE_CAPABILITIES: VoiceCapabilities = {
  read_aloud_enabled: false,
  turn_based_enabled: false,
  supported_input_mime: ["audio/wav", "audio/x-wav", "audio/webm", "audio/ogg"],
  limits: null,
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

function normalizeLlmHealthRawError(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function describeProviderSource(source: {
  kind?: string;
  label?: string;
  baseUrl?: string;
} | null | undefined): string | null {
  if (!source) return null;
  const label = String(source.label ?? "").trim();
  if (label) return label;
  const baseUrl = String(source.baseUrl ?? "").trim();
  if (!baseUrl) return null;
  try {
    return new URL(baseUrl).host || baseUrl;
  } catch {
    return baseUrl;
  }
}

function getModelMenuLabel(model: {
  alias?: string;
  displayLabel?: string;
  pickerLabel?: string;
  canonicalId: string;
}): string {
  return (
    String(
      model.alias ??
        model.displayLabel ??
        model.pickerLabel ??
        model.canonicalId
    ).trim() || model.canonicalId
  );
}

function getModelLabelKey(model: {
  alias?: string;
  displayLabel?: string;
  pickerLabel?: string;
  canonicalId: string;
}): string {
  return getModelMenuLabel(model).trim().toLowerCase();
}

function getModelDifferentiator(
  model: {
    canonicalId: string;
    namespace?: string;
    source?: string;
  },
  siblingModels: Array<{
    canonicalId: string;
    namespace?: string;
    source?: string;
  }>,
  providerSourceLabel: string | null
): string {
  const namespaces = new Set(
    siblingModels
      .map((entry) => String(entry.namespace ?? "").trim())
      .filter(Boolean)
  );
  if (namespaces.size > 1 && model.namespace) {
    return `Namespace ${model.namespace}`;
  }

  const sources = new Set(
    siblingModels
      .map((entry) => String(entry.source ?? providerSourceLabel ?? "").trim())
      .filter(Boolean)
  );
  const sourceLabel = String(model.source ?? providerSourceLabel ?? "").trim();
  if (sources.size > 1 && sourceLabel) {
    return `Source ${sourceLabel}`;
  }

  return model.canonicalId;
}

function isApplePlatform(): boolean {
  if (typeof navigator === "undefined") return false;
  const platform = String(
    (navigator as any).userAgentData?.platform ?? navigator.platform ?? ""
  ).toLowerCase();
  return (
    platform.includes("mac") ||
    platform.includes("iphone") ||
    platform.includes("ipad") ||
    platform.includes("ipod")
  );
}

function normalizeVoiceCapabilities(raw: any): VoiceCapabilities {
  const limitsRaw = raw?.limits;
  const maxUploadBytes = Number(limitsRaw?.max_upload_bytes);
  const maxDurationSeconds = Number(limitsRaw?.max_duration_s);
  const supportedInputMime = Array.isArray(raw?.supported_input_mime)
    ? raw.supported_input_mime
        .map((entry: unknown) => String(entry ?? "").trim().toLowerCase())
        .filter(Boolean)
    : DEFAULT_VOICE_CAPABILITIES.supported_input_mime;

  return {
    read_aloud_enabled: Boolean(raw?.read_aloud_enabled),
    turn_based_enabled: Boolean(raw?.turn_based_enabled),
    supported_input_mime: supportedInputMime.length
      ? supportedInputMime
      : DEFAULT_VOICE_CAPABILITIES.supported_input_mime,
    limits:
      Number.isFinite(maxUploadBytes) && Number.isFinite(maxDurationSeconds)
        ? {
            max_upload_bytes: Math.max(0, Math.floor(maxUploadBytes)),
            max_duration_s: Math.max(0, Math.floor(maxDurationSeconds)),
          }
        : null,
  };
}

function toUserFacingLlmHealthError(
  rawError: string | null,
  status: LlmHealthStatus
): string | null {
  if (!rawError) return null;
  const normalized = rawError.toLowerCase();

  if (/allow_cloud_providers\s*=\s*false/i.test(rawError)) {
    return "Cloud providers are disabled by configuration.";
  }
  if (
    normalized.includes("timeout") ||
    normalized.includes("timed out") ||
    normalized.includes("connecttimeout") ||
    normalized.includes("readtimeout")
  ) {
    return "Guardian cannot reach the model endpoint right now. Check connectivity and model service health.";
  }
  if (
    normalized.includes("connection refused") ||
    normalized.includes("econnrefused") ||
    normalized.includes("enotfound") ||
    normalized.includes("httpconnectionpool")
  ) {
    return "Guardian cannot connect to the configured model service. Start it or switch providers.";
  }
  if (
    status === "misconfigured" ||
    normalized.includes("misconfig") ||
    normalized.includes("invalid model") ||
    normalized.includes("unknown model")
  ) {
    return "Model configuration is invalid. Review provider/model settings.";
  }
  return "Guardian cannot reach the model endpoint. Check connectivity and model service availability.";
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
  workspaceOpen = false,
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
  activeProviderId = null,
  activeModelId = "default",
  activeInferenceMode = DEFAULT_COMPOSER_INFERENCE_MODE,
  activeDraft = "",
  onSessionTabActivate,
  onSessionTabClose,
  onSessionTabOpen,
  onSessionProviderChange,
  onSessionModelChange,
  onSessionInferenceModeChange,
  onSessionDraftChange,
}: {
  guardianName: string;
  userName: string;
  prefill?: string;
  onPrefillConsumed?: () => void;
  onWorkspaceToggle?: () => void;
  workspaceOpen?: boolean;
  activeThread: Thread;
  onSendMessage: (text: string) => Promise<void>;
  onThreadPersisted?: (
    threadId: number,
    title?: string,
    options?: { tabId?: TabId | null }
  ) => void;
  onNewChat: () => void;
  onBranchThread?: (threadId: number, options?: { title?: string }) => Promise<void> | void;
  onArchiveThread?: (threadId: number) => Promise<void> | void;
  onSidebarToggle?: () => void;
  isSidebarVisible?: boolean;
  onBack?: () => void;
  bare?: boolean;
  sessionTabs?: SessionTab[];
  activeSessionTabId?: TabId | null;
  activeProviderId?: string | null;
  activeModelId?: string;
  activeInferenceMode?: ComposerInferenceMode;
  activeDraft?: string;
  onSessionTabActivate?: (tabId: TabId) => void;
  onSessionTabClose?: (tabId: TabId) => void;
  onSessionTabOpen?: () => void;
  onSessionProviderChange?: (providerId: string | null) => void;
  onSessionModelChange?: (modelId: string) => void;
  onSessionInferenceModeChange?: (mode: ComposerInferenceMode) => void;
  onSessionDraftChange?: (text: string) => void;
}) {
  // RAG depth selector: User's control of perceptual awareness
  const [depth, setDepth] = useState<DepthMode>("normal");
  const [ragTraceOpen, setRagTraceOpen] = useState(false);

  const [externalPrefill, setExternalPrefill] = useState<string | undefined>(undefined);
  // Chat state management including completion tracking
  const {
    messages,
    loading: chatLoading,
    error: chatError,
    hasMore: chatHasMore,
    activateThread,
    refreshSnapshot,
    loadOlderMessages,
    completionState,
    startCompletion,
    endCompletion,
    updateCompletionTaskId,
    startCompletionSession,
    reassociateCompletionSession,
    updateCompletionSessionTurnId,
    finalizeCompletionSession,
    handleIncomingAssistantMessage,
    isCompletionInFlight,
    setCompletionInFlight,
  } = useChat();
  const inferenceRequest = useInferenceRequestState();
  const {
    providers: catalogProviders,
    getProviderById,
    getModelById,
    findProviderForModel,
  } = useLlmCatalog();
  const [turnLocks, setTurnLocks] = useState<Record<number, boolean>>({});
  const [pendingTurnLock, setPendingTurnLock] = useState(false);
  const lastCompletionThreadRef = useRef<number | null>(null);
  const lastCompletionDepthRef = useRef<Record<number, DepthMode>>({});
  const traceEndpointRef = useRef<Record<number, string>>({});
  const traceFetchInflightRef = useRef<Record<number, boolean>>({});
  const activeThreadRef = useRef<Thread>(activeThread);
  const effectiveThreadIdRef = useRef<number | null>(null);
  const activeSessionTabIdRef = useRef<TabId | null>(activeSessionTabId);
  const pendingFastRetryRef = useRef<{
    threadId: number;
    providerId: string | null;
    modelId: string | null;
  } | null>(null);
  const threadProfileRequestRef = useRef<{
    controller: AbortController | null;
    promise: Promise<SystemProfileOption | null> | null;
    threadId: number | null;
    token: number;
  }>({
    controller: null,
    promise: null,
    threadId: null,
    token: 0,
  });

  useEffect(() => {
    activeThreadRef.current = activeThread;
  }, [activeThread]);

  useEffect(() => {
    activeSessionTabIdRef.current = activeSessionTabId;
  }, [activeSessionTabId]);

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
  const [voiceCapabilities, setVoiceCapabilities] = useState<VoiceCapabilities>(
    DEFAULT_VOICE_CAPABILITIES
  );
  const [voiceCapabilitiesStatus, setVoiceCapabilitiesStatus] =
    useState<VoiceCapabilitiesStatus>("loading");
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
    rawError: null,
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
  const [providerMenuOpenSignal, setProviderMenuOpenSignal] = useState(0);
  const promptCostPopoverRef = useRef<HTMLDivElement | null>(null);
  const showToast = useCallback((message: string) => {
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:toast", { detail: { message, kind: "error" } })
      );
    } catch {}
  }, []);
  const voiceReadAloudEnabled = voiceCapabilities.read_aloud_enabled;
  const voiceTurnBasedEnabled = voiceCapabilities.turn_based_enabled;
  const voiceCapabilitiesFailed = voiceCapabilitiesStatus === "error";
  const supportedVoiceInputMime = voiceCapabilities.supported_input_mime;
  const voiceUploadAccept = useMemo(
    () => supportedVoiceInputMime.join(","),
    [supportedVoiceInputMime]
  );
  const voiceUploadLimitBytes = voiceCapabilities.limits?.max_upload_bytes ?? null;

  const selectedProvider = useMemo(() => {
    const explicitProvider = getProviderById(activeProviderId);
    if (explicitProvider) return explicitProvider;
    const providerFromModel = findProviderForModel(activeModelId);
    if (providerFromModel) return providerFromModel;
    return catalogProviders[0] ?? null;
  }, [
    activeModelId,
    activeProviderId,
    catalogProviders,
    findProviderForModel,
    getProviderById,
  ]);

  const selectedModel = useMemo(() => {
    if (selectedProvider?.models?.length) {
      return (
        selectedProvider.models.find((model) => model.id === activeModelId) ??
        selectedProvider.models[0] ??
        null
      );
    }
    return getModelById(activeModelId);
  }, [activeModelId, getModelById, selectedProvider]);

  const providerOptions = useMemo(
    () =>
      catalogProviders.map((provider) => ({
        value: provider.id,
        label: provider.displayName,
        description: provider.available
          ? [
              `${provider.models.length} models`,
              describeProviderSource(provider.source)
                ? `Source ${describeProviderSource(provider.source)}`
                : null,
            ]
              .filter(Boolean)
              .join(" · ")
          : provider.disabledReason || "Unavailable",
        disabled: !provider.available,
      })),
    [catalogProviders]
  );

  const modelOptions = useMemo(
    () => {
      const models = selectedProvider?.models ?? [];
      const providerSourceLabel = describeProviderSource(selectedProvider?.source);
      const modelsByLabel = new Map<string, typeof models>();

      for (const model of models) {
        const labelKey = getModelLabelKey(model);
        const siblings = modelsByLabel.get(labelKey);
        if (siblings) {
          siblings.push(model);
          continue;
        }
        modelsByLabel.set(labelKey, [model]);
      }

      return models.map((model) => {
        const label = getModelMenuLabel(model);
        const siblingModels = modelsByLabel.get(getModelLabelKey(model)) ?? [model];
        const description =
          siblingModels.length > 1
            ? getModelDifferentiator(model, siblingModels, providerSourceLabel)
            : undefined;

        return {
          value: model.id,
          label,
          description,
          meta:
            typeof model.contextWindow === "number"
              ? `${Math.round(model.contextWindow / 1000)}k`
              : null,
        };
      });
    },
    [selectedProvider]
  );

  const supportsManualInferenceMode = useMemo(() => {
    if (!selectedProvider || !selectedModel) return false;
    if (selectedProvider.id !== "local") return false;
    return Boolean(selectedModel.runtime?.reasoning?.mode) || /qwen|qwq/i.test(selectedModel.id);
  }, [selectedModel, selectedProvider]);

  const effectiveInferenceMode = supportsManualInferenceMode
    ? activeInferenceMode
    : DEFAULT_COMPOSER_INFERENCE_MODE;

  const inferenceModeOptions = useMemo(() => {
    const base = [
      {
        value: "default",
        label: "Auto",
        description: "Use the model's default runtime behavior.",
      },
    ];
    if (!supportsManualInferenceMode) return base;
    return [
      ...base,
      {
        value: "no_think",
        label: "Fast",
        description: "Prefer immediate responses without extended reasoning.",
      },
      {
        value: "think",
        label: "Think",
        description: "Allow a longer reasoning pass before output begins.",
      },
    ];
  }, [supportsManualInferenceMode]);

  useEffect(() => {
    if (selectedProvider && activeProviderId !== selectedProvider.id) {
      onSessionProviderChange?.(selectedProvider.id);
    }
  }, [activeProviderId, onSessionProviderChange, selectedProvider]);

  useEffect(() => {
    if (selectedModel && activeModelId !== selectedModel.id) {
      onSessionModelChange?.(selectedModel.id);
    }
  }, [activeModelId, onSessionModelChange, selectedModel]);

  useEffect(() => {
    if (
      !supportsManualInferenceMode &&
      activeInferenceMode !== DEFAULT_COMPOSER_INFERENCE_MODE
    ) {
      onSessionInferenceModeChange?.(DEFAULT_COMPOSER_INFERENCE_MODE);
    }
  }, [
    activeInferenceMode,
    onSessionInferenceModeChange,
    supportsManualInferenceMode,
  ]);

  useEffect(() => {
    if (!selectedProvider && !selectedModel) return;
    setPreferredProviderSelection({
      provider: selectedProvider?.id ?? null,
      model: selectedModel?.id ?? null,
    });
  }, [selectedModel?.id, selectedProvider?.id]);

  const refreshVoiceCapabilities = useCallback(async () => {
    try {
      const response = await api.get("/voice/capabilities");
      setVoiceCapabilities(normalizeVoiceCapabilities(response?.data));
      setVoiceCapabilitiesStatus("ready");
    } catch (error) {
      console.warn("[guardian] voice capabilities unavailable", error);
      setVoiceCapabilities(DEFAULT_VOICE_CAPABILITIES);
      setVoiceCapabilitiesStatus("error");
    }
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
      const rawError = normalizeLlmHealthRawError(data?.error);

      setLlmHealth({
        ok: typeof data?.ok === "boolean" ? data.ok : status === "online",
        status,
        provider: typeof data?.provider === "string" ? data.provider : null,
        model: typeof data?.model === "string" ? data.model : null,
        error: toUserFacingLlmHealthError(rawError, status),
        rawError,
        checkedAt: Date.now(),
      });
    } catch (err: any) {
      const rawError = normalizeLlmHealthRawError(err?.message) || "LLM health check failed";
      setLlmHealth({
        ok: null,
        status: "unknown",
        provider: null,
        model: null,
        error: toUserFacingLlmHealthError(rawError, "unknown"),
        rawError,
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
    llmHealth.rawError || ""
  );
  const llmStatusMessage =
    llmHealth.error
    || "Guardian cannot reach the model endpoint. Check connectivity and model service availability.";
  const applePlatform = useMemo(() => isApplePlatform(), []);
  const focusComposer = useCallback(() => {
    if (typeof document === "undefined") return;
    const composer = document.querySelector<HTMLTextAreaElement>('textarea[placeholder="Write a message…"]');
    composer?.focus();
  }, []);
  const handleTellGuardianWhatToDoInstead = useCallback(
    ({ suggestedPrompt }: { suggestedPrompt: string }) => {
      const normalizedPrompt = suggestedPrompt.trim() || "Guardian, do this instead: ";
      setExternalPrefill((current) => {
        const existing = (current ?? "").trim();
        if (!existing) return normalizedPrompt;
        if (existing.includes(normalizedPrompt)) {
          return current ?? existing;
        }
        return `${existing}\n${normalizedPrompt}`;
      });
      focusComposer();
    },
    [focusComposer]
  );
  const handleSessionTabOpenRequest = useCallback(() => {
    if (onSessionTabOpen) {
      onSessionTabOpen();
      return true;
    }
    onNewChat();
    return true;
  }, [onNewChat, onSessionTabOpen]);
  const handleSessionTabActivateRequest = useCallback(
    (tabId: TabId) => {
      if (!onSessionTabActivate) return false;
      onSessionTabActivate(tabId);
      return true;
    },
    [onSessionTabActivate]
  );
  const activateNextSessionTab = useCallback(() => {
    if (!onSessionTabActivate || !sessionTabs.length) return false;
    const nextTabId = getWrappedSessionTabId(
      sessionTabs,
      activeSessionTabId,
      1
    );
    if (!nextTabId || nextTabId === activeSessionTabId) return true;
    return handleSessionTabActivateRequest(nextTabId);
  }, [
    activeSessionTabId,
    handleSessionTabActivateRequest,
    onSessionTabActivate,
    sessionTabs,
  ]);
  const activatePreviousSessionTab = useCallback(() => {
    if (!onSessionTabActivate || !sessionTabs.length) return false;
    const previousTabId = getWrappedSessionTabId(
      sessionTabs,
      activeSessionTabId,
      -1
    );
    if (!previousTabId || previousTabId === activeSessionTabId) return true;
    return handleSessionTabActivateRequest(previousTabId);
  }, [
    activeSessionTabId,
    handleSessionTabActivateRequest,
    onSessionTabActivate,
    sessionTabs,
  ]);
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
      return Boolean(turnLocks[threadId]) || isCompletionInFlight(threadId);
    },
    [isCompletionInFlight, pendingTurnLock, turnLocks]
  );
  const notifyTurnLocked = () => {
    showToast(TURN_LOCK_TOAST);
  };
  const requestProviderSwitch = useCallback(
    () => {
      setPromptCostPopoverOpen(false);
      setProviderMenuOpenSignal((prev) => prev + 1);
      window.setTimeout(() => focusComposer(), 0);
    },
    [focusComposer]
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
  type CompletionOutcome = "ok" | "service_unavailable" | "failed" | "inflight";
  type CompletionRequestOptions = {
    providerId?: string | null;
    modelId?: string | null;
    reasoningMode?: ComposerInferenceMode;
  };

  const resolveCompletionSelection = useCallback(
    (options: CompletionRequestOptions = {}) => ({
      providerId: options.providerId ?? selectedProvider?.id ?? activeProviderId ?? null,
      modelId: options.modelId ?? selectedModel?.id ?? activeModelId ?? "default",
      reasoningMode: options.reasoningMode ?? effectiveInferenceMode,
    }),
    [
      activeModelId,
      activeProviderId,
      effectiveInferenceMode,
      selectedModel?.id,
      selectedProvider?.id,
    ]
  );

  const startInferenceForThread = useCallback(
    (threadId: number, options: CompletionRequestOptions = {}) => {
      const selection = resolveCompletionSelection(options);
      inferenceRequest.startRequest({
        threadId,
        providerId: selection.providerId,
        modelId: selection.modelId,
        mode: selection.reasoningMode,
      });
      return selection;
    },
    [inferenceRequest, resolveCompletionSelection]
  );

  // Helper: ask backend to complete the thread and then refresh
  const completeThread = async (
    tid: number,
    options: CompletionRequestOptions = {}
  ): Promise<CompletionOutcome> => {
    const selection = resolveCompletionSelection(options);
    const payload = buildChatCompletionPayload(depth, {
      providerId: selection.providerId,
      modelId: selection.modelId,
      reasoningMode: selection.reasoningMode,
    });
    const provisionalTaskId = `pending-${Date.now()}`;
    setCompletionInFlight(tid, true);
    startCompletion(tid, provisionalTaskId);
    try {
      const response = await api.post(buildChatCompletePath(tid), payload);
      console.log(`[guardian] Completing with depth=${depth}`);

      if (effectiveThreadIdRef.current === tid) {
        startCompletionSession({
          threadId: tid,
          taskId: provisionalTaskId,
          turnId: null,
          reloadVersion: chatReloadVersion,
        });
      }

      // Capture task_id for completion state tracking
      const taskId = response?.data?.task_id ?? provisionalTaskId;
      const responseDepth = (response?.data?.depth_mode as DepthMode | undefined) ?? depth;
      lastCompletionDepthRef.current[tid] = responseDepth;

      if (effectiveThreadIdRef.current === tid) {
        reassociateCompletionSession({
          threadId: tid,
          provisionalTaskId,
          realTaskId: taskId,
          reloadVersion: chatReloadVersion,
        });
      }

      if (taskId) {
        console.debug(`[guardian] Starting completion tracking: task=${taskId}`);
        updateCompletionTaskId(taskId);
        inferenceRequest.attachTask(taskId);
      }

      const turnId =
        typeof response?.data?.turn_id === "string" &&
        response.data.turn_id.trim().length > 0
          ? response.data.turn_id.trim()
          : getInFlightCompletionTurnId(tid);
      if (turnId && effectiveThreadIdRef.current === tid) {
        updateCompletionSessionTurnId(taskId, turnId);
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
      if (statusCode === 429) {
        logOnce("complete:turn-lock", 5_000, () => {
          console.warn("[guardian] completion hit turn-lock (429) — waiting for prior turn");
        });
        showToast("Finishing previous turn…");
        setCompletionInFlight(tid, true);
        if (!completionState.isCompleting || completionState.activeThreadId !== tid) {
          startCompletion(tid, `turn-lock-${tid}`);
        }
        return "inflight";
      }
      if (
        statusCode === 503 &&
        (reason.includes("completion_service_unavailable") ||
          reason.includes("queue_unavailable") ||
          reason.includes("turn_lock_unavailable"))
      ) {
        showToast("Completion service unavailable — check Docker/Redis.");
        endCompletion();
        inferenceRequest.markFailed(
          "Completion service unavailable",
          {
            detailText: "Guardian could not enqueue the response worker.",
          }
        );
        return "service_unavailable";
      }
      console.warn("[guardian] completion failed", err);
      endCompletion();
      inferenceRequest.markFailed(
        err?.response?.data?.detail ||
          err?.message ||
          "Guardian could not start the response.",
        {
          detailText: "Try again or switch to a faster mode.",
        }
      );
      return "failed";
    }
  };

  const retryWithoutThinkingAfterCancel = useCallback(
    (threadId: number, attempt = 0) => {
      const delayMs = 180 + attempt * 180;
      window.setTimeout(() => {
        const pending = pendingFastRetryRef.current;
        if (!pending || pending.threadId !== threadId) {
          return;
        }
        void (async () => {
          startInferenceForThread(threadId, {
            providerId: pending.providerId,
            modelId: pending.modelId,
            reasoningMode: "no_think",
          });
          const outcome = await completeThread(threadId, {
            providerId: pending.providerId,
            modelId: pending.modelId,
            reasoningMode: "no_think",
          });
          if (outcome === "inflight" && attempt < 3) {
            retryWithoutThinkingAfterCancel(threadId, attempt + 1);
            return;
          }
          pendingFastRetryRef.current = null;
          if (outcome !== "ok" && outcome !== "inflight") {
            setTurnLockForThread(threadId, false);
            showToast("Guardian could not continue in fast mode.");
          }
        })();
      }, delayMs);
    },
    [completeThread, setTurnLockForThread, showToast, startInferenceForThread]
  );

  const numericThreadId = useMemo(() => {
    const n = Number((activeThread as any)?.id);
    return Number.isFinite(n) ? (n as number) : null;
  }, [activeThread?.id]);

  // Update currentThreadId when numericThreadId changes
  useEffect(() => {
    setCurrentThreadId((prev) => (prev === numericThreadId ? prev : numericThreadId));
  }, [numericThreadId]);

  const effectiveThreadId = currentThreadId ?? numericThreadId ?? null;

  useEffect(() => {
    effectiveThreadIdRef.current = effectiveThreadId;
  }, [effectiveThreadId]);

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
      if (
        threadProfileRequestRef.current.promise &&
        threadProfileRequestRef.current.threadId === threadId
      ) {
        return threadProfileRequestRef.current.promise;
      }

      if (
        threadProfileRequestRef.current.threadId != null &&
        threadProfileRequestRef.current.threadId !== threadId
      ) {
        threadProfileRequestRef.current.controller?.abort();
      }

      const nextToken = threadProfileRequestRef.current.token + 1;
      const controller = new AbortController();
      threadProfileRequestRef.current = {
        controller,
        promise: null,
        threadId,
        token: nextToken,
      };

      const request = (async () => {
        try {
          const response = await api.get(`/chat/${threadId}/profile`, {
            signal: controller.signal,
          });
          if (
            effectiveThreadIdRef.current !== threadId ||
            threadProfileRequestRef.current.token !== nextToken
          ) {
            return null;
          }
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
          if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") {
            return null;
          }
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
      })();

      threadProfileRequestRef.current.promise = request;
      return request.finally(() => {
        if (threadProfileRequestRef.current.token === nextToken) {
          threadProfileRequestRef.current.controller = null;
          threadProfileRequestRef.current.promise = null;
        }
      });
    },
    [applyProfileFallback]
  );

  const switchThreadProfile = useCallback(
    async (threadId: number, profileId: string): Promise<boolean> => {
      setProfileSwitching(true);
      try {
        const result = await SystemProfiles.switch({
          thread_id: threadId,
          profile_id: profileId,
        });
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
      threadProfileRequestRef.current.controller?.abort();
      threadProfileRequestRef.current = {
        controller: null,
        promise: null,
        threadId: null,
        token: threadProfileRequestRef.current.token,
      };
      applyProfileFallback();
      return;
    }
    void refreshThreadProfile(effectiveThreadId);
  }, [applyProfileFallback, effectiveThreadId, refreshThreadProfile]);

  useEffect(() => {
    void activateThread(effectiveThreadId);
  }, [activateThread, effectiveThreadId]);

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

  useEffect(() => {
    if (typeof document === "undefined") return;
    const onDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing) return;

      const lowerKey = event.key.toLowerCase();
      const usesPrimaryCreateModifier = applePlatform
        ? event.metaKey && !event.ctrlKey
        : event.ctrlKey && !event.metaKey;
      if (
        usesPrimaryCreateModifier &&
        !event.altKey &&
        !event.shiftKey &&
        lowerKey === "t"
      ) {
        if (handleSessionTabOpenRequest()) {
          event.preventDefault();
        }
        return;
      }

      const wantsNextByCtrlTab =
        event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        !event.shiftKey &&
        event.key === "Tab";
      const wantsNextByPageDown =
        event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        !event.shiftKey &&
        event.key === "PageDown";
      const wantsNextByAppleArrow =
        applePlatform &&
        event.metaKey &&
        !event.ctrlKey &&
        event.altKey &&
        !event.shiftKey &&
        event.key === "ArrowRight";

      if (wantsNextByCtrlTab || wantsNextByPageDown || wantsNextByAppleArrow) {
        if (activateNextSessionTab()) {
          event.preventDefault();
        }
        return;
      }

      const wantsPreviousByCtrlShiftTab =
        event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        event.shiftKey &&
        event.key === "Tab";
      const wantsPreviousByPageUp =
        event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        !event.shiftKey &&
        event.key === "PageUp";
      const wantsPreviousByAppleArrow =
        applePlatform &&
        event.metaKey &&
        !event.ctrlKey &&
        event.altKey &&
        !event.shiftKey &&
        event.key === "ArrowLeft";

      if (
        wantsPreviousByCtrlShiftTab ||
        wantsPreviousByPageUp ||
        wantsPreviousByAppleArrow
      ) {
        if (activatePreviousSessionTab()) {
          event.preventDefault();
        }
      }
    };

    document.addEventListener("keydown", onDocumentKeyDown);
    return () => {
      document.removeEventListener("keydown", onDocumentKeyDown);
    };
  }, [
    activateNextSessionTab,
    activatePreviousSessionTab,
    applePlatform,
    handleSessionTabOpenRequest,
  ]);

  const handlePromptCostToggle = useCallback(() => {
    setPromptCostPopoverOpen((previous) => {
      const next = !previous;
      if (next) {
        void refreshPromptCostSummary(effectiveThreadId);
      }
      return next;
    });
  }, [effectiveThreadId, refreshPromptCostSummary]);

  useEffect(() => {
    return () => {
      triggerReload.cancel();
      threadProfileRequestRef.current.controller?.abort();
    };
  }, [triggerReload]);

  useEffect(() => {
    void refreshVoiceCapabilities();
  }, [effectiveThreadId, refreshVoiceCapabilities]);

  useEffect(() => {
    if (voiceReadAloudEnabled) return;
    if (!autoReadEnabled) return;
    setAutoReadEnabled(false);
  }, [autoReadEnabled, voiceReadAloudEnabled]);

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

  // Live event integration keeps the shared chat hook synchronized.
  useEffect(() => {
    const offThread = subscribe("thread.updated", (event) => {
      const payload = flattenChatEventPayload(event.data);
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
      const payload = flattenChatEventPayload(event.data);
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
      const payload = flattenChatEventPayload(event.data);
      const tid = Number(payload?.thread_id ?? payload?.threadId);
      const role = String(payload?.role ?? "").trim().toLowerCase();
      if (!Number.isFinite(tid) || role !== "assistant") return;
      const handled = handleIncomingAssistantMessage(payload);
      if (!handled) return;
      setTurnLockForThread(tid, false);
      clearInFlightCompletionTurnId(tid);
      void fetchTraceForThread(tid, "message-event");
      if (
        inferenceRequest.state.threadId === tid &&
        isActiveInferencePhase(inferenceRequest.state.phase)
      ) {
        inferenceRequest.markCompleted();
      }
    });
    const finalizeCompletionFromTaskEvent = (event: any) => {
      const payload = flattenChatEventPayload(event.data);
      const tid = Number(payload?.thread_id ?? payload?.threadId);
      if (!Number.isFinite(tid)) return;

      // Issue 1: Only accept events with explicit task_id/turn_id, not by thread alone
      const eventTaskId = String(payload?.task_id ?? payload?.taskId ?? "").trim();
      const eventTurnId = String(payload?.turn_id ?? payload?.turnId ?? "").trim();

      // Only proceed if both task_id and turn_id are present in the event payload
      // This prevents accepting assistant completion events by thread alone
      if (!eventTaskId || !eventTurnId) {
        console.debug(`[guardian] Ignoring completion event without explicit task_id or turn_id for thread ${tid}`);
        return;
      }

      updateCompletionSessionTurnId(eventTaskId, eventTurnId);

      const terminalState =
        event.type === "task.completed"
          ? "completed"
          : event.type === "task.cancelled"
            ? "cancelled"
            : event.type === "completion.error"
              ? "error"
              : "failed";

      const finalized = finalizeCompletionSession({
        taskId: eventTaskId,
        terminalState,
      });

      if (finalized) {
        clearInFlightCompletionTurnId(tid);
        setTurnLockForThread(tid, false);
      }
      if (event.type === "task.failed" || event.type === "completion.error") {
        inferenceRequest.markFailed(
          String(payload?.error || "Guardian could not finish the response."),
          {
            detailText: "Try again or switch to a faster mode.",
          }
        );
        pendingFastRetryRef.current = null;
        return;
      }
      if (event.type === "task.cancelled") {
        inferenceRequest.markCancelled();
        if (pendingFastRetryRef.current?.threadId === tid) {
          retryWithoutThinkingAfterCancel(tid);
        }
        return;
      }
      if (event.type === "task.completed") {
        pendingFastRetryRef.current = null;
        inferenceRequest.markCompleted();
      }
    };
    const offTaskCompleted = subscribe("task.completed", finalizeCompletionFromTaskEvent);
    const offTaskFailed = subscribe("task.failed", finalizeCompletionFromTaskEvent);
    const offTaskCancelled = subscribe("task.cancelled", finalizeCompletionFromTaskEvent);
    const offCompletionError = subscribe(
      "completion.error",
      finalizeCompletionFromTaskEvent
    );

    return () => {
      offMessage();
      offTaskCompleted();
      offTaskFailed();
      offTaskCancelled();
      offCompletionError();
    };
  }, [
    completionState.activeTaskId,
    fetchTraceForThread,
    finalizeCompletionSession,
    handleIncomingAssistantMessage,
    inferenceRequest,
    inferenceRequest.state.phase,
    inferenceRequest.state.taskId,
    inferenceRequest.state.threadId,
    setTurnLockForThread,
    retryWithoutThinkingAfterCancel,
    subscribe,
    updateCompletionSessionTurnId,
  ]);
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
  const handleThreadCreated = (
    threadId: number,
    title?: string,
    options?: { tabId?: TabId | null }
  ) => {
    const nextTitle = (title && title.trim().length > 0) ? title.trim() : NEW_THREAD_TITLE;
    const targetTabId = options?.tabId ?? null;
    const shouldPromoteVisibleThread =
      targetTabId == null || targetTabId === activeSessionTabIdRef.current;

    if (shouldPromoteVisibleThread) {
      setCurrentThreadId(threadId);
      setThreadTitle(nextTitle);
    }

    // Notify other panes that a new thread exists so sidebars can update immediately
    emitThreadsRefresh("create", { id: String(threadId), title: nextTitle });

    // Update URL to reflect the new thread
    if (shouldPromoteVisibleThread && typeof window !== "undefined") {
      window.history.replaceState({}, "", `/chat/${threadId}`);
    }
  };

  const ensureThreadIdForAttachments = useCallback(
    async (bodyText: string) => {
      if (effectiveThreadId != null) {
        return effectiveThreadId;
      }

      const normalizedUserId = userName || "default";
      const originTabId = activeSessionTabIdRef.current;
      const firstLine = bodyText.trim().split(/\n+/)[0] ?? "";
      const provisionalTitle = firstLine.slice(0, 60) || NEW_THREAD_TITLE;
      const metadata = originTabId
        ? { draft_tab_id: originTabId }
        : undefined;

      const resp = await api.post("/chat/threads", {
        title: provisionalTitle,
        user_id: normalizedUserId,
        metadata,
      });
      const payload = (resp && resp.data) || {};
      const newThreadId =
        payload.id ?? payload.thread?.id ?? payload.thread_id ?? payload.id_str;
      const numericThreadId = Number(newThreadId);
      if (!Number.isFinite(numericThreadId)) {
        throw new Error("Thread id missing from create thread response");
      }

      const derivedTitle = payload.thread?.title ?? provisionalTitle;
      handleThreadCreated(numericThreadId, derivedTitle, {
        tabId: originTabId,
      });
      onThreadPersisted?.(numericThreadId, derivedTitle, {
        tabId: originTabId,
      });
      return numericThreadId;
    },
    [effectiveThreadId, onThreadPersisted, userName]
  );

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
  const handleSendMessage = async (
    text: string,
    options?: ComposerSendOptions
  ) => {
    /**
     * Inject human consciousness into the thread's awareness stream.
     *
     * When no thread exists, this creates a new conversation consciousness
     * container and establishes the temporal message flow. The provisional
     * title becomes the thread's identity in the distributed awareness network.
     */
    const normalizedUserId = userName || "default";
    const originTabId = activeSessionTabIdRef.current;
    const targetThreadId = options?.threadIdOverride ?? effectiveThreadId;
    const requestedProfileId = resolveProfileIdFromCommand(text);
    const isProfileCommand =
      targetThreadId != null && Boolean(requestedProfileId);
    if (llmBackendUnavailable && !isProfileCommand) {
      const title =
        llmHealth.status === "misconfigured"
          ? "LLM backend misconfigured."
          : "LLM backend offline.";
      showToast(`${title} ${llmStatusMessage}`);
      void refreshLlmHealth();
      return;
    }
    if (targetThreadId != null && isTurnLocked(targetThreadId)) {
      notifyTurnLocked();
      return;
    }
    if (
      targetThreadId != null &&
      isCompletionInFlight(targetThreadId)
    ) {
      notifyTurnLocked();
      return;
    }
    if (targetThreadId != null && requestedProfileId) {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${targetThreadId}`);
      }
      try {
        await onSendMessage(text);
        const switched = await switchThreadProfile(
          targetThreadId,
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
          await api.post(`/chat/${targetThreadId}/messages`, {
            role: "assistant",
            content: `Profile switched to ${label}. Next completion will use this profile.`,
            user_id: normalizedUserId,
          });
          if (targetThreadId === effectiveThreadId) {
            await refreshSnapshot(targetThreadId, "profile-switch");
          }
        }
      } catch (error) {
        console.error("[guardian] profile switch command failed", error);
        showToast("Profile switch failed.");
        throw error;
      }
      return;
    }
    if (!targetThreadId) {
      const firstLine = text.trim().split(/\n+/)[0] ?? "";
      const provisionalTitle = firstLine.slice(0, 60) || NEW_THREAD_TITLE;
      let createdThreadId: number | null = null;
      setPendingTurnLock(true);
      try {
        const resp = await api.post("/chat/messages", {
          thread_id: null,
          draft_tab_id: originTabId ?? undefined,
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
        handleThreadCreated(numericNewId, derivedTitle, {
          tabId: originTabId,
        });
        await activateThread(numericNewId);
        onThreadPersisted?.(numericNewId, derivedTitle, {
          tabId: originTabId,
        });

        // Lock the new thread before requesting assistant completion.
        setTurnLockForThread(numericNewId, true);
        setPendingTurnLock(false);

        // Remove draft only after successful commit.
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${numericNewId}`);
        }

        // Complete the thread and refresh.
        startInferenceForThread(numericNewId);
        const completionOutcome = await completeThread(numericNewId);
        if (completionOutcome !== "ok" && completionOutcome !== "inflight") {
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
        sessionStorage.removeItem(`${DRAFT_KEY_PREFIX}${targetThreadId}`);
      }
      setTurnLockForThread(targetThreadId, true);
      // Thread exists, just send the message via parent callback
      try {
        if (targetThreadId !== effectiveThreadId) {
          await api.post(`/chat/${targetThreadId}/messages`, {
            role: "user",
            content: text,
            user_id: normalizedUserId,
          });
          emitThreadsRefresh("refresh", {
            reason: "message",
            id: String(targetThreadId),
          });
          setChatReloadVersion((v) => v + 1);
        } else {
          await onSendMessage(text);
          await refreshSnapshot(targetThreadId, "user-send");
        }

        // Fire-and-forget completion a beat later so the just-sent message is persisted
        startInferenceForThread(targetThreadId);
        setTimeout(() => {
          if (targetThreadId == null) return;
          void (async () => {
            const completionOutcome = await completeThread(targetThreadId);
            if (completionOutcome !== "ok" && completionOutcome !== "inflight") {
              setTurnLockForThread(targetThreadId, false);
              if (completionOutcome === "failed") {
                showToast("Assistant response failed.");
              }
            }
          })();
        }, 100);
      } catch (error) {
        setTurnLockForThread(targetThreadId, false);
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
  const ragTraceUiEnabled = isRagTraceUIEnabled();
  const depthOptions = (Object.keys(depthLabels) as DepthMode[]).map((mode) => ({
    value: mode,
    label: depthLabels[mode],
    description: depthDescriptions[mode],
  }));
  const composerInferenceState =
    effectiveThreadId != null &&
    inferenceRequest.state.threadId === effectiveThreadId
      ? inferenceRequest.state
      : createIdleInferenceRequestState();
  const handleCancelInference = () => {
    pendingFastRetryRef.current = null;
    void inferenceRequest.requestCancel();
  };
  const handleSwitchToNoThink = () => {
    if (effectiveThreadId == null) return;
    onSessionInferenceModeChange?.("no_think");
    const selection = resolveCompletionSelection({
      reasoningMode: "no_think",
    });
    pendingFastRetryRef.current = {
      threadId: effectiveThreadId,
      providerId: selection.providerId,
      modelId: selection.modelId,
    };
    void inferenceRequest.requestCancel().then((ok) => {
      if (!ok) {
        pendingFastRetryRef.current = null;
      }
    });
  };

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
            <PromptCostIndicator summary={promptCostSummary} variant="popover" />
          </div>
        ) : null}
      </div>
      <button
        type="button"
        className="icon-inline"
        aria-label={
          voiceReadAloudEnabled
            ? autoReadEnabled
              ? "Disable auto read aloud"
              : "Enable auto read aloud"
            : "Auto read aloud unavailable"
        }
        title={
          voiceReadAloudEnabled
            ? autoReadEnabled
              ? "Auto read aloud: On"
              : "Auto read aloud: Off"
            : "Read-aloud unavailable"
        }
        onClick={() => {
          if (!voiceReadAloudEnabled) return;
          setAutoReadEnabled((v) => !v);
        }}
        disabled={!voiceReadAloudEnabled}
        style={{
          borderRadius: "var(--radius-micro)",
          opacity: voiceReadAloudEnabled ? (autoReadEnabled ? 1 : 0.65) : 0.45,
        }}
      >
        <Volume2 className="h-5 w-5" />
      </button>
      <button
        type="button"
        className="icon-inline"
        aria-label="Toggle workspace"
        aria-pressed={workspaceOpen}
        onClick={onWorkspaceToggle}
        style={{
          borderRadius: "var(--radius-micro)",
          opacity: workspaceOpen ? 1 : 0.72,
          background: workspaceOpen
            ? "color-mix(in oklab, var(--panel-bg), var(--accent) 18%)"
            : "transparent",
        }}
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
              <div className="font-medium">Branch Thread</div>
              <div className="text-xs opacity-70">
                Create a new thread that inherits a summary/briefing and continue with a different model.
              </div>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              const pidRaw = window.prompt("Add to project id (blank to cancel)", "");
              if (pidRaw == null || pidRaw === "") return;
              const pid = Number(pidRaw);
              if (!Number.isFinite(pid)) return alert("Invalid project id");
              try {
                await api.patch(`/chat/${effectiveThreadId}`, { project_id: pid });
                emitThreadsRefresh("move", { id: String(effectiveThreadId), project_id: pid });
              } catch (e) {
                console.warn(e);
                alert("Add failed.");
              }
            }}
          >
            Add to Project…
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={async () => {
              if (effectiveThreadId == null) return alert("Thread is not persisted yet");
              const pidRaw = window.prompt("Move to project id (blank to cancel)", "");
              if (pidRaw == null || pidRaw === "") return;
              const pid = Number(pidRaw);
              if (!Number.isFinite(pid)) return alert("Invalid project id");
              try {
                await api.patch(`/chat/${effectiveThreadId}`, { project_id: pid });
                emitThreadsRefresh("move", { id: String(effectiveThreadId), project_id: pid });
              } catch (e) {
                console.warn(e);
                alert("Move failed.");
              }
            }}
          >
            Move to Project…
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
              const nextProfile = window.prompt("Switch to profile id", resolvedProfile.id || "default");
              const profileId = (nextProfile || "").trim();
              if (!profileId) return;
              await switchThreadProfile(effectiveThreadId, profileId);
            }}
          >
            Switch profile…
          </DropdownMenuItem>
          {ragTraceUiEnabled ? (
            <DropdownMenuItem
              onClick={() => {
                if (effectiveThreadId == null) {
                  alert("Thread is not persisted yet");
                  return;
                }
                setRagTraceOpen(true);
              }}
            >
              View RAG Trace
            </DropdownMenuItem>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );

  const body = (
    <div className="relative flex h-full w-full min-h-0 flex-col bg-transparent">
      {/* Single header rail */}
      <header className="shrink-0 z-20 px-4 py-2">
        <div
          className="relative flex items-center gap-2 px-1 py-2 flex-nowrap"
          style={{
            color: "var(--text)",
          }}
        >
          <div className="flex items-center gap-2 shrink-0">
            {onSidebarToggle && (
              <button
                type="button"
                className="icon-inline"
                aria-label={isSidebarVisible ? "Hide sidebar" : "Show sidebar"}
                onClick={onSidebarToggle}
                disabled={!onSidebarToggle}
                style={{
                  borderRadius: "999px",
                  border: "1px solid color-mix(in oklab, var(--panel-border) 78%, transparent)",
                  background:
                    "linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.03)), color-mix(in oklab, var(--panel-bg) 70%, transparent)",
                  boxShadow:
                    "inset 0 1px 0 rgba(255,255,255,0.18), 0 8px 18px rgba(0,0,0,0.08)",
                  padding: "0.5rem",
                }}
              >
                <ChevronRight
                  className={`h-5 w-5 transition-transform duration-200 ${
                    isSidebarVisible ? "rotate-180" : ""
                  }`}
                />
              </button>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <SessionRail
              tabs={sessionTabs}
              activeTabId={activeSessionTabId}
              isCloud={resolvedProfile.mode === "cloud" ? true : resolvedProfile.mode === "local" ? false : undefined}
              showTabs={sessionTabs.length > 1}
              onActivateTab={handleSessionTabActivateRequest}
              onCloseTab={(tabId) => onSessionTabClose?.(tabId)}
              onOpenTab={handleSessionTabOpenRequest}
            />
          </div>

          <div className="flex items-center gap-1 justify-end shrink-0">
            {headerActions}
          </div>
        </div>
      </header>

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
            key={effectiveThreadId}
            threadId={effectiveThreadId}
            guardianName={guardianName}
            messages={messages}
            loading={chatLoading}
            error={chatError}
            hasMore={chatHasMore}
            onLoadOlderMessages={() => loadOlderMessages(effectiveThreadId)}
            reloadVersion={chatReloadVersion}
            completionState={completionState}
            endCompletion={endCompletion}
            className="flex flex-col flex-1 min-h-0"
            bottomPadding={160}
            autoReadEnabled={autoReadEnabled}
            depthMode={depth}
            profileId={resolvedProfile.id}
            voiceReadAloudEnabled={voiceReadAloudEnabled}
            voiceCapabilitiesFailed={voiceCapabilitiesFailed}
            inferenceState={composerInferenceState}
            onCancelInference={handleCancelInference}
            onSwitchToFast={handleSwitchToNoThink}
          />
        ) : (
          <div
            className="flex flex-1 items-center justify-center px-[var(--card-pad)] text-sm opacity-70"
            style={{ color: "var(--muted)" }}
          >
            New thread ready. Start typing below.
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
          <GuardianThreadApprovalRail
            className="mb-3"
            onTellGuardianWhatToDoInstead={handleTellGuardianWhatToDoInstead}
            reloadSignal={chatReloadVersion}
            threadId={effectiveThreadId ?? undefined}
          />
          <Composer
            onSend={handleSendMessage}
            ensureThreadIdForAttachments={ensureThreadIdForAttachments}
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
            activeProviderId={selectedProvider?.id ?? activeProviderId}
            providerOptions={providerOptions}
            providerOpenSignal={providerMenuOpenSignal}
            onProviderChange={(providerId) => {
              const nextProvider =
                catalogProviders.find((provider) => provider.id === providerId) ?? null;
              onSessionProviderChange?.(providerId);
              const nextModelId = nextProvider?.models?.[0]?.id ?? null;
              if (
                nextProvider &&
                (!selectedModel ||
                  !nextProvider.models.some((model) => model.id === selectedModel.id)) &&
                nextModelId
              ) {
                onSessionModelChange?.(nextModelId);
              }
            }}
            activeModelId={selectedModel?.id ?? activeModelId}
            modelOptions={modelOptions}
            onModelChange={(modelId) => onSessionModelChange?.(modelId)}
            activeInferenceMode={effectiveInferenceMode}
            inferenceModeOptions={inferenceModeOptions}
            onInferenceModeChange={(mode) =>
              onSessionInferenceModeChange?.(mode)
            }
            depthMode={depth}
            depthOptions={depthOptions}
            onDepthModeChange={setDepth}
            onVoiceTurn={
              voiceTurnBasedEnabled
                ? () => {
                    if (effectiveThreadId == null) {
                      alert(
                        "Create or open a thread before starting a voice turn."
                      );
                      return;
                    }
                    voiceFileInputRef.current?.click();
                  }
                : undefined
            }
            voiceTurnLabel={voiceUploading ? "Processing voice…" : "Upload voice turn"}
          />
          {voiceTurnBasedEnabled ? (
            <input
              ref={voiceFileInputRef}
              type="file"
              accept={voiceUploadAccept}
              className="hidden"
              onChange={async (event) => {
                const file = event.target.files?.[0];
                event.currentTarget.value = "";
                if (!file) return;
                if (effectiveThreadId == null) {
                  alert("Create or open a thread before starting a voice turn.");
                  return;
                }
                const normalizedMime = String(file.type || "")
                  .trim()
                  .toLowerCase();
                if (
                  normalizedMime &&
                  supportedVoiceInputMime.length > 0 &&
                  !supportedVoiceInputMime.includes(normalizedMime)
                ) {
                  alert(`Unsupported audio type: ${normalizedMime}`);
                  return;
                }
                if (
                  voiceUploadLimitBytes != null &&
                  file.size > voiceUploadLimitBytes
                ) {
                  const limitMb = (voiceUploadLimitBytes / (1024 * 1024)).toFixed(1);
                  alert(`Audio file too large. Max ${limitMb} MB.`);
                  return;
                }
                setVoiceUploading(true);
                try {
                  const form = new FormData();
                  form.append("thread_id", String(effectiveThreadId));
                  form.append("audio_file", file);
                  form.append("tts_enabled", "true");
                  await api.post("/voice/turn", form, {
                    headers: { "Content-Type": "multipart/form-data" },
                    timeout: 180000,
                  });
                  await refreshSnapshot(effectiveThreadId, "voice-turn");
                } catch (error) {
                  console.warn("[guardian] voice turn failed", error);
                  alert("Voice turn failed. Check backend voice configuration.");
                } finally {
                  setVoiceUploading(false);
                }
              }}
            />
          ) : null}
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
        <RAGTracePanel
          open={ragTraceOpen}
          onOpenChange={setRagTraceOpen}
          threadId={effectiveThreadId}
        />
      </>
    );
  }

  return (
    <>
      <FrameCard
        className="flex-1 min-h-0 min-w-0 flex flex-col h-full"
        hoverPop
      >
        <div className="relative flex flex-col w-full h-full">
          {body}
        </div>
      </FrameCard>
      <RAGTracePanel
        open={ragTraceOpen}
        onOpenChange={setRagTraceOpen}
        threadId={effectiveThreadId}
      />
    </>
  );
}

export default GuardianChat;
