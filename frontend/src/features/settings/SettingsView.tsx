import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/controls/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { ImagePlus } from "lucide-react";
import { useConnectors } from "@/features/connectors/useConnectors";
import { ConnectorCard } from "@/features/connectors/ConnectorCard";
import { MemoryBrowser } from "@/features/settings/diagnostics";
import ImprintReviewPanel from "@/features/settings/components/ImprintReviewPanel";
import PersonalFactsPanel from "@/features/settings/components/PersonalFactsPanel";
import SystemPromptInspector from "@/features/settings/components/SystemPromptInspector";
import SettingsPanelDock from "@/features/settings/components/SettingsPanelDock";
import SettingsPanelShell from "@/features/settings/components/SettingsPanelShell";
import SettingsSectionCard from "@/features/settings/components/SettingsSectionCard";
import {
  SETTINGS_DENSITY,
  getSettingsHeadingRowStyle,
} from "./settingsDensityContract";
import {
  ChatGPTImportModal,
  type MigrationStats,
} from "@/components/modals/ChatGPTImportModal";
import {
  getDesktopConnectionSettings,
  initRuntimeConfig,
  invokeTauriCommand,
  isTauriRuntime,
  openExternalUrl,
  resolveBackendUrl,
  saveDesktopConnectionSettings,
} from "@/lib/runtimeConfig";
import {
  default as api,
  clearRuntimeApiKey,
  getAuthToken,
  getDevApiKey,
  readRuntimeApiKey,
  refreshApiBaseUrl,
  setRuntimeApiKey,
} from "@/lib/api";
import { updatePersonaSettings } from "@/features/settings/api/persona";
import {
  SUPPORTED_PROFILE_ROUTE_LABELS,
  type RuntimeRouteCapabilityState,
} from "@/contracts/supportedProfileRoutes";
import { GuardianEventSource } from "@/lib/guardianEventSource";
import {
  ensureRuntimeRouteCapabilitiesLoaded,
  getRuntimeRouteCapabilityState,
  markRuntimeRouteUnavailableIfNotFound,
  useRuntimeRouteCapabilities,
} from "@/lib/runtimeRouteCapabilities";
import type { RuntimeConfig } from "@/lib/runtimeConfig";

type ImportRuntimeStatus =
  | "idle"
  | "queued"
  | "running"
  | "succeeded"
  | "failed";

type StoredChatGPTImportTask = {
  taskId: string;
  startedAt: number;
  status: ImportRuntimeStatus;
  detail: string;
  lastEventAt: number;
};

type SettingsTab =
  | "appearance"
  | "system"
  | "connectors"
  | "data"
  | "connection"
  | "personalFacts"
  | "diagnostics";

type SettingsTabDefinition = {
  value: SettingsTab;
  label: string;
  requiresDesktop?: boolean;
};

const SETTINGS_TAB_DEFINITIONS: SettingsTabDefinition[] = [
  { value: "appearance", label: "Appearance" },
  { value: "system", label: "Imprint" },
  { value: "connectors", label: "Connectors" },
  { value: "data", label: "Data" },
  { value: "connection", label: "Connection", requiresDesktop: true },
  { value: "personalFacts", label: "Personal Facts" },
  { value: "diagnostics", label: "Diagnostics" },
];

function getSettingsTabButtonId(tab: SettingsTab): string {
  return `settings-tab-${tab}`;
}

function getSettingsTabPanelId(tab: SettingsTab): string {
  return `settings-panel-${tab}`;
}

const SETTINGS_TAB_STORAGE_KEY = "cfy.settingsTab";

function normalizeSettingsTab(value: unknown): SettingsTab | null {
  if (typeof value !== "string") return null;
  const compact = value.trim().toLowerCase().replace(/[^a-z]/g, "");
  if (!compact) return null;
  if (compact === "appearance") return "appearance";
  if (compact === "system" || compact === "imprint") return "system";
  if (compact === "connectors") return "connectors";
  if (compact === "data") return "data";
  if (compact === "connection") return "connection";
  if (compact === "personalfacts") return "personalFacts";
  if (compact === "diagnostics") return "diagnostics";
  return null;
}

function readPersistedSettingsTab(): SettingsTab | null {
  if (typeof window === "undefined") return null;
  try {
    return normalizeSettingsTab(
      window.sessionStorage.getItem(SETTINGS_TAB_STORAGE_KEY)
    );
  } catch {
    return null;
  }
}

function persistSettingsTab(tab: SettingsTab): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(SETTINGS_TAB_STORAGE_KEY, tab);
  } catch {
    /* ignore */
  }
}

const CHATGPT_IMPORT_TASK_STORAGE_KEY = "codexify.chatgpt_import_task";

function isChatGPTImportPath(rawUrl: unknown): boolean {
  if (typeof rawUrl !== "string") return false;
  try {
    const parsed = new URL(rawUrl, "http://localhost");
    const path = parsed.pathname.replace(/\/+$/, "");
    return (
      path.endsWith("/upload-chatgpt-export") ||
      path.endsWith("/api/upload-chatgpt-export")
    );
  } catch {
    return false;
  }
}

function statusLabel(status: ImportRuntimeStatus): string {
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "succeeded") return "Succeeded";
  if (status === "failed") return "Failed";
  return "Idle";
}

function isTerminalStatus(status: ImportRuntimeStatus): boolean {
  return status === "succeeded" || status === "failed";
}

function formatElapsed(startedAt: number, now: number): string {
  if (!Number.isFinite(startedAt) || startedAt <= 0) return "0s";
  const elapsedSeconds = Math.max(0, Math.floor((now - startedAt) / 1000));
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  if (minutes <= 0) return `${seconds}s`;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

function extractTaskEventDetail(data: unknown, fallbackType: string): string {
  if (typeof data === "string") {
    const lines = data
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length > 0) {
      return lines[lines.length - 1];
    }
  }
  if (data && typeof data === "object") {
    const records: Array<Record<string, unknown>> = [data as Record<string, unknown>];
    const top = data as Record<string, unknown>;
    if (top.data && typeof top.data === "object") {
      records.push(top.data as Record<string, unknown>);
    }
    if (top.payload && typeof top.payload === "object") {
      records.push(top.payload as Record<string, unknown>);
    }
    for (const record of records) {
      const candidates = [
        record.message,
        record.detail,
        record.stage,
        record.status,
        record.state,
        record.error,
      ];
      for (const candidate of candidates) {
        if (typeof candidate === "string" && candidate.trim()) {
          return candidate.trim();
        }
      }
      if (typeof record.progress === "number") {
        return `Progress ${Math.max(0, Math.min(100, record.progress))}%`;
      }
    }
  }
  return fallbackType;
}

function normalizeTaskEventStatus(
  eventType: string,
  data: unknown
): ImportRuntimeStatus | null {
  const normalizedType = eventType.toLowerCase();
  const candidateSignals: string[] = [normalizedType];

  if (typeof data === "string") {
    const trimmed = data.trim().toLowerCase();
    if (trimmed) {
      candidateSignals.push(trimmed);
    }
  } else if (data && typeof data === "object") {
    const records: Array<Record<string, unknown>> = [data as Record<string, unknown>];
    const top = data as Record<string, unknown>;
    if (top.data && typeof top.data === "object") {
      records.push(top.data as Record<string, unknown>);
    }
    if (top.payload && typeof top.payload === "object") {
      records.push(top.payload as Record<string, unknown>);
    }

    for (const record of records) {
      const maybeSignals = [
        record.type,
        record.event,
        record.status,
        record.state,
        record.stage,
      ];
      for (const signal of maybeSignals) {
        if (typeof signal === "string" && signal.trim()) {
          candidateSignals.push(signal.toLowerCase());
        }
      }
    }
  }

  const normalizedSignals = candidateSignals.join(" ");

  if (
    normalizedSignals.includes("failed") ||
    normalizedSignals.includes("cancel")
  ) {
    return "failed";
  }
  if (
    normalizedSignals.includes("completed") ||
    normalizedSignals.includes("succeeded") ||
    normalizedSignals.includes("done")
  ) {
    return "succeeded";
  }
  if (
    normalizedSignals.includes("running") ||
    normalizedSignals.includes("started") ||
    normalizedSignals.includes("progress")
  ) {
    return "running";
  }
  if (
    normalizedSignals.includes("queued") ||
    normalizedSignals.includes("created")
  ) {
    return "queued";
  }
  return null;
}

function getResponseErrorMessage(error: unknown): string | null {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as {
      data?: { detail?: unknown; error?: unknown };
    };
    if (
      typeof response.data?.detail === "string" &&
      response.data.detail.trim()
    ) {
      return response.data.detail;
    }
    if (
      typeof response.data?.error === "string" &&
      response.data.error.trim()
    ) {
      return response.data.error;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return null;
}

function readRouteThreadId(): number | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/chat\/(\d+)/);
  if (!match) return null;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

export function SettingsView({
  mode,
  setMode,
  guardianName,
  setGuardianName,
  userName,
  setUserName,
  role,
  setRole,
  notes,
  setNotes,
  baseColor,
  setBaseColor,
  depth,
  setDepth,
  fade,
  setFade,
  resolved,
  systemPrompt,
  setSystemPrompt,
  wallpaper,
  setWallpaper,
  extColors,
  setExtColors,
  dashboardThreadRows,
  setDashboardThreadRows,
}: {
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  guardianName: string;
  setGuardianName: (s: string) => void;
  userName: string;
  setUserName: (s: string) => void;
  role: string;
  setRole: (s: string) => void;
  notes: string;
  setNotes: (s: string) => void;
  baseColor: string;
  setBaseColor: (s: string) => void;
  depth: number;
  setDepth: (n: number) => void;
  fade: number;
  setFade: (n: number) => void;
  resolved: "light" | "dark";
  systemPrompt: string;
  setSystemPrompt: (s: string) => void;
  wallpaper: string | null;
  setWallpaper: (s: string | null) => void;
  extColors: ExtColors;
  setExtColors: (m: ExtColors) => void;
  dashboardThreadRows: number;
  setDashboardThreadRows: (n: number) => void;
}) {
  const desktopMode = isTauriRuntime();
  const [tab, setTab] = useState<SettingsTab>(() => {
    const storedTab = readPersistedSettingsTab();
    if (storedTab === "connection" && !desktopMode) {
      return "appearance";
    }
    return storedTab ?? "appearance";
  });
  const tabButtonRefs = useRef<Record<SettingsTab, HTMLButtonElement | null>>({
    appearance: null,
    system: null,
    connectors: null,
    data: null,
    connection: null,
    personalFacts: null,
    diagnostics: null,
  });
  const settingsScrollContainerRef = useRef<HTMLElement | null>(null);
  const tabScrollPositionsRef = useRef<Partial<Record<SettingsTab, number>>>({});
  const [chatGPTModalOpen, setChatGPTModalOpen] = useState(false);
  const [migrationStepSkipped, setMigrationStepSkipped] = useState(false);
  const [migrationStats, setMigrationStats] = useState<MigrationStats | null>(
    null
  );
  const [name, setName] = useState(guardianName);
  const [uName, setUName] = useState(userName);
  const [uRole, setURole] = useState(role);
  const [prompt, setPrompt] = useState(systemPrompt);
  const [memo, setMemo] = useState(notes);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(() =>
    readRouteThreadId()
  );
  const [desktopBackendBaseUrl, setDesktopBackendBaseUrl] = useState("");
  const [desktopShareBaseUrl, setDesktopShareBaseUrl] = useState("");
  const [desktopApiKeyInput, setDesktopApiKeyInput] = useState("");
  const [runtimeConfigSnapshot, setRuntimeConfigSnapshot] =
    useState<RuntimeConfig | null>(null);
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [importTaskId, setImportTaskId] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<ImportRuntimeStatus>("idle");
  const [importDetail, setImportDetail] = useState("");
  const [importStartedAt, setImportStartedAt] = useState(0);
  const [importLastEventAt, setImportLastEventAt] = useState(0);
  const [importPanelHidden, setImportPanelHidden] = useState(false);
  const [importNow, setImportNow] = useState(() => Date.now());
  const importPendingStartedAtRef = useRef(0);
  const importTaskStreamRef = useRef<GuardianEventSource | null>(null);
  const isImportActive = importStatus === "queued" || importStatus === "running";
  const isImportTerminal = isTerminalStatus(importStatus);
  const shouldShowImportStatusPanel = importStatus !== "idle" && !importPanelHidden;
  const importElapsed = formatElapsed(importStartedAt, importNow);
  const [systemPromptSaveStatus, setSystemPromptSaveStatus] = useState<
    "idle" | "saving" | "success" | "warning" | "error"
  >("idle");
  const [systemPromptSaveMessage, setSystemPromptSaveMessage] = useState<
    string | null
  >(null);
  const [systemPromptSaveError, setSystemPromptSaveError] = useState<string | null>(
    null
  );
  const [systemPromptSyncRetryNeeded, setSystemPromptSyncRetryNeeded] =
    useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const syncActiveThreadId = () => {
      setActiveThreadId(readRouteThreadId());
    };
    const history = window.history;
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    const emitRouteChange = () => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    };

    history.pushState = function (
      ...args: Parameters<History["pushState"]>
    ) {
      const result = originalPushState.apply(history, args);
      emitRouteChange();
      return result;
    };

    history.replaceState = function (
      ...args: Parameters<History["replaceState"]>
    ) {
      const result = originalReplaceState.apply(history, args);
      emitRouteChange();
      return result;
    };

    syncActiveThreadId();
    window.addEventListener("popstate", syncActiveThreadId);
    window.addEventListener(
      "cfy:threads:refresh",
      syncActiveThreadId as EventListener
    );

    return () => {
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
      window.removeEventListener("popstate", syncActiveThreadId);
      window.removeEventListener(
        "cfy:threads:refresh",
        syncActiveThreadId as EventListener
      );
    };
  }, []);
  const [lastSavedPersonaId, setLastSavedPersonaId] = useState<number | null>(
    null
  );
  const {
    ready: runtimeCapabilitiesReady,
    states: runtimeRouteStates,
  } = useRuntimeRouteCapabilities([
    SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT,
    SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS,
  ]);
  const imprintCapability =
    runtimeRouteStates[SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT] ?? "unknown";
  const connectorsCapability =
    runtimeRouteStates[SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS] ?? "unknown";

  function resetImportStatus() {
    setImportTaskId(null);
    setImportStatus("idle");
    setImportDetail("");
    setImportStartedAt(0);
    setImportLastEventAt(0);
    setImportPanelHidden(false);
    importPendingStartedAtRef.current = 0;
    importTaskStreamRef.current?.close();
    importTaskStreamRef.current = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
    }
  }

  function handleImportPanelAction() {
    if (isImportTerminal) {
      resetImportStatus();
      return;
    }
    setImportPanelHidden(true);
  }
  useEffect(() => setName(guardianName), [guardianName]);
  useEffect(() => setUName(userName), [userName]);
  useEffect(() => setURole(role), [role]);
  useEffect(() => setPrompt(systemPrompt), [systemPrompt]);
  useEffect(() => setMemo(notes), [notes]);
  useEffect(() => {
    setSystemPromptSaveStatus("idle");
    setSystemPromptSaveMessage(null);
    setSystemPromptSaveError(null);
  }, [memo, name, prompt, uName, uRole]);
  useEffect(() => {
    persistSettingsTab(tab);
  }, [tab]);
  useEffect(() => {
    if (!desktopMode) return;
    const settings = getDesktopConnectionSettings();
    setDesktopBackendBaseUrl(settings.backendBaseUrl);
    setDesktopShareBaseUrl(settings.sharePublicBaseUrl);
    setDesktopApiKeyInput(readRuntimeApiKey() ?? "");
    void initRuntimeConfig({ force: true }).then((config) => {
      setRuntimeConfigSnapshot(config);
    });
  }, [desktopMode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as Partial<StoredChatGPTImportTask>;
      const storedTaskId =
        typeof parsed.taskId === "string" ? parsed.taskId.trim() : "";
      if (!storedTaskId) {
        window.localStorage.removeItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
        return;
      }
      const startedAt =
        typeof parsed.startedAt === "number" && Number.isFinite(parsed.startedAt)
          ? parsed.startedAt
          : Date.now();
      const status =
        parsed.status === "queued" ||
        parsed.status === "running" ||
        parsed.status === "succeeded" ||
        parsed.status === "failed"
          ? parsed.status
          : "running";
      setImportTaskId(storedTaskId);
      setImportStatus(status);
      setImportStartedAt(startedAt);
      setImportDetail(
        typeof parsed.detail === "string" && parsed.detail.trim()
          ? parsed.detail
          : "Reattached to background import task."
      );
      setImportLastEventAt(
        typeof parsed.lastEventAt === "number" && Number.isFinite(parsed.lastEventAt)
          ? parsed.lastEventAt
          : startedAt
      );
      setImportPanelHidden(false);
    } catch {
      window.localStorage.removeItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!importTaskId) return;
    const snapshot: StoredChatGPTImportTask = {
      taskId: importTaskId,
      startedAt: importStartedAt || Date.now(),
      status: importStatus,
      detail: importDetail,
      lastEventAt: importLastEventAt || Date.now(),
    };
    window.localStorage.setItem(
      CHATGPT_IMPORT_TASK_STORAGE_KEY,
      JSON.stringify(snapshot)
    );
  }, [
    importTaskId,
    importStartedAt,
    importStatus,
    importDetail,
    importLastEventAt,
  ]);

  useEffect(() => {
    if (importStatus === "idle") return;
    const timer = window.setInterval(() => {
      setImportNow(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [importStatus]);

  useEffect(() => {
    if (!importTaskId || isImportTerminal) {
      importTaskStreamRef.current?.close();
      importTaskStreamRef.current = null;
      return;
    }

    const apiKey = readRuntimeApiKey() || getDevApiKey();
    const authToken = getAuthToken();
    const headers: Record<string, string> = {};
    if (authToken) {
      headers.Authorization = `Bearer ${authToken}`;
    } else if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const stream = new GuardianEventSource(
      `/api/tasks/${encodeURIComponent(importTaskId)}/events`,
      {
        headers,
        withCredentials: true,
        autoReconnect: true,
        retryInterval: 3000,
      }
    );

    importTaskStreamRef.current?.close();
    importTaskStreamRef.current = stream;

    const handleTaskEvent = (event: Event) => {
      const message = event as MessageEvent<string>;
      let payload: unknown = message.data;
      if (typeof payload === "string") {
        const trimmed = payload.trim();
        if (!trimmed) return;
        try {
          payload = JSON.parse(trimmed);
        } catch {
          payload = trimmed;
        }
      }

      const nextStatus = normalizeTaskEventStatus(message.type, payload);
      const fallbackDetail =
        message.type === "message"
          ? "Import event received."
          : message.type.replace("task.", "").replace(/\./g, " ");
      const detail = extractTaskEventDetail(payload, fallbackDetail);
      const now = Date.now();

      setImportLastEventAt(now);
      setImportDetail(detail);
      if (nextStatus) {
        setImportStatus(nextStatus);
        if (isTerminalStatus(nextStatus)) {
          stream.close();
          if (importTaskStreamRef.current === stream) {
            importTaskStreamRef.current = null;
          }
        }
      }
    };

    stream.onopen = () => {
      const now = Date.now();
      setImportLastEventAt(now);
      setImportStatus((current) =>
        current === "queued" ? "running" : current
      );
      setImportDetail((current) =>
        current || "Import task connected. Waiting for updates..."
      );
    };

    stream.onerror = () => {
      const now = Date.now();
      setImportLastEventAt(now);
      setImportStatus((current) =>
        current === "queued" ? "running" : current
      );
      setImportDetail((current) =>
        current || "Import is still running. Waiting for next update..."
      );
    };

    const eventTypes = [
      "message",
      "task.created",
      "task.queued",
      "task.running",
      "task.started",
      "task.progress",
      "task.completed",
      "task.failed",
      "task.cancelled",
    ];

    for (const eventType of eventTypes) {
      stream.addEventListener(eventType, handleTaskEvent);
    }

    return () => {
      for (const eventType of eventTypes) {
        stream.removeEventListener(eventType, handleTaskEvent);
      }
      stream.close();
      if (importTaskStreamRef.current === stream) {
        importTaskStreamRef.current = null;
      }
    };
  }, [importTaskId, isImportTerminal]);

  useEffect(() => {
    const requestInterceptorId = api.interceptors.request.use((config: any) => {
      if (!isChatGPTImportPath(config?.url)) return config;
      const startedAt = Date.now();
      importPendingStartedAtRef.current = startedAt;
      setImportPanelHidden(false);
      setImportStartedAt(startedAt);
      setImportLastEventAt(startedAt);
      setImportStatus("queued");
      setImportDetail("Import started. Preparing background task...");
      setMigrationStepSkipped(false);
      return config;
    });

    const responseInterceptorId = api.interceptors.response.use(
      (response: any) => {
        if (!isChatGPTImportPath(response?.config?.url)) {
          return response;
        }

        const now = Date.now();
        const startedAt = importPendingStartedAtRef.current || now;
        importPendingStartedAtRef.current = 0;

        const rawTaskId =
          response?.data?.task_id ??
          response?.data?.taskId ??
          response?.headers?.["x-task-id"] ??
          response?.headers?.["X-Task-Id"];
        const taskId =
          typeof rawTaskId === "string" ? rawTaskId.trim() : String(rawTaskId || "");

        if (taskId) {
          setImportTaskId(taskId);
          setImportStartedAt(startedAt);
          setImportLastEventAt(now);
          setImportStatus("queued");
          setImportDetail("Import queued. Live progress is now attached.");
          return response;
        }

        const threads = Number(response?.data?.threads_imported ?? 0);
        const messages = Number(response?.data?.messages_imported ?? 0);
        setImportTaskId(null);
        setImportStartedAt(startedAt);
        setImportLastEventAt(now);
        setImportStatus("succeeded");
        setImportDetail(
          `Import completed. Imported ${threads} thread${
            threads === 1 ? "" : "s"
          } and ${messages} message${messages === 1 ? "" : "s"}.`
        );
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
        }
        return response;
      },
      (error: any) => {
        if (!isChatGPTImportPath(error?.config?.url)) {
          return Promise.reject(error);
        }

        const now = Date.now();
        const startedAt = importPendingStartedAtRef.current || now;
        importPendingStartedAtRef.current = 0;
        const detail =
          error?.response?.data?.detail ??
          error?.response?.data?.error ??
          error?.message ??
          "ChatGPT import failed.";

        setImportTaskId(null);
        setImportStartedAt(startedAt);
        setImportLastEventAt(now);
        setImportStatus("failed");
        setImportDetail(String(detail));
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(CHATGPT_IMPORT_TASK_STORAGE_KEY);
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.request.eject(requestInterceptorId);
      api.interceptors.response.eject(responseInterceptorId);
    };
  }, []);

  useEffect(() => {
    return () => {
      importTaskStreamRef.current?.close();
      importTaskStreamRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (tab === "connection" && !desktopMode) {
      setTab("appearance");
    }
  }, [desktopMode, tab]);

  async function handleSave() {
    const localDirty =
      name !== guardianName ||
      uName !== userName ||
      uRole !== role ||
      memo !== notes ||
      prompt !== systemPrompt;
    const userId = (uName || userName || "default").trim() || "default";
    const personaId = lastSavedPersonaId;
    console.log("[SystemPrompt] Save clicked", {
      value: prompt,
      length: prompt?.length,
      dirty: localDirty,
      userId,
      personaId,
    });
    setGuardianName(name);
    setUserName(uName);
    setRole(uRole);
    setNotes(memo);
    setSystemPrompt(prompt);

    const shouldAttemptPersonaSync =
      prompt !== systemPrompt || systemPromptSyncRetryNeeded;

    if (!localDirty && !shouldAttemptPersonaSync) {
      setSystemPromptSaveStatus("success");
      setSystemPromptSaveMessage("Saved locally.");
      return;
    }

    const projectId =
      typeof window !== "undefined"
        ? Number(window.localStorage.getItem("cfy.lastProjectId"))
        : NaN;
    const payload = {
      text: prompt,
      persona_prompt: prompt,
      system_prompt: prompt,
      projectId: Number.isFinite(projectId) ? projectId : undefined,
    };
    console.log("[SystemPrompt] Persist payload", payload);

    setSystemPromptSaveStatus("saving");
    setSystemPromptSaveMessage(null);
    setSystemPromptSaveError(null);
    if (!shouldAttemptPersonaSync) {
      setSystemPromptSaveStatus("success");
      setSystemPromptSaveMessage("Saved locally.");
      return;
    }

    await ensureRuntimeRouteCapabilitiesLoaded();
    const resolvedImprintCapability: RuntimeRouteCapabilityState =
      getRuntimeRouteCapabilityState(SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT);

    if (resolvedImprintCapability === "unavailable") {
      setSystemPromptSyncRetryNeeded(false);
      setSystemPromptSaveStatus("warning");
      setSystemPromptSaveMessage(
        "Saved locally. Not synced to runtime persona layer in this profile."
      );
      return;
    }

    try {
      const response = await updatePersonaSettings(payload);
      console.log("[SystemPrompt] Save response", response);
      setLastSavedPersonaId(response.id);
      setSystemPromptSyncRetryNeeded(false);
      setSystemPromptSaveStatus("success");
      setSystemPromptSaveMessage(
        "Saved locally and synced to runtime persona layer."
      );
    } catch (error) {
      console.error("[SystemPrompt] Save failed", error);
      if (
        markRuntimeRouteUnavailableIfNotFound(
          SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT,
          error
        )
      ) {
        setSystemPromptSyncRetryNeeded(false);
        setSystemPromptSaveStatus("warning");
        setSystemPromptSaveMessage(
          "Saved locally. Not synced to runtime persona layer in this profile."
        );
        return;
      }

      setSystemPromptSyncRetryNeeded(true);
      setSystemPromptSaveStatus("warning");
      setSystemPromptSaveMessage("Saved locally. Persona sync failed.");
      setSystemPromptSaveError(
        getResponseErrorMessage(error) ?? "Persona sync failed."
      );
    }
  }

  const [fileLabel, setFileLabel] = useState<string>("");
  const [, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);
  function triggerFile() {
    fileRef.current?.click();
  }
  function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setUploading(true);
    setFileLabel(f.name);
    const rd = new FileReader();
    rd.onload = () => {
      const url = String(rd.result || "");
      setWallpaper(url);
      if (typeof window !== "undefined") {
        localStorage.setItem("cfy.wallpaper", url);
        // Mark that the user has uploaded a file at least once
        localStorage.setItem("cfy.hasUserUpload", "true");
      }
      setUploading(false);
    };
    rd.onerror = () => setUploading(false);
    rd.readAsDataURL(f);
  }
  function clearWallpaper() {
    setWallpaper(null);
    setFileLabel("");
    if (typeof window !== "undefined") localStorage.removeItem("cfy.wallpaper");
    if (fileRef.current) fileRef.current.value = "";
  }

  const migrationComplete =
    migrationStepSkipped || migrationStats !== null || importStatus === "succeeded";

  async function handleSaveConnectionSettings() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await saveDesktopConnectionSettings({
        backendBaseUrl: desktopBackendBaseUrl,
        sharePublicBaseUrl: desktopShareBaseUrl,
      });
      const config = await initRuntimeConfig({ force: true });
      refreshApiBaseUrl();
      setRuntimeConfigSnapshot(config);
      setConnectionMessage("Connection settings saved.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to save connection settings."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleSaveDesktopApiKey() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await invokeTauriCommand("desktop_set_api_key", {
        apiKey: desktopApiKeyInput,
      });
      setRuntimeApiKey(desktopApiKeyInput);
      setConnectionMessage("Desktop API key saved to secure keychain.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to save desktop API key."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleClearDesktopApiKey() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await invokeTauriCommand("desktop_clear_api_key");
      setDesktopApiKeyInput("");
      clearRuntimeApiKey();
      setConnectionMessage("Desktop API key cleared.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to clear desktop API key."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleTestConnection() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      const config = await initRuntimeConfig({ force: true });
      refreshApiBaseUrl();
      setRuntimeConfigSnapshot(config);
      const response = await fetch(resolveBackendUrl("/ping", config));
      if (!response.ok) {
        throw new Error(`Backend ping failed (${response.status})`);
      }
      setConnectionMessage("Connection test passed.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Connection test failed."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleDownloadExport() {
    if (typeof window === "undefined") return;
    const exportUrl = resolveBackendUrl("/exports/chatgpt.zip");
    if (desktopMode) {
      const opened = await openExternalUrl(exportUrl);
      if (opened) return;
    }
    window.location.href = exportUrl;
  }

  const connectorsEnabled =
    tab === "connectors" &&
    runtimeCapabilitiesReady &&
    connectorsCapability !== "unavailable";
  const {
    connectors,
    updateConnector,
    loading,
    error,
    authorizeOAuth,
    testConnector,
    syncConnector,
  } = useConnectors({ enabled: connectorsEnabled });

  const visibleTabs = SETTINGS_TAB_DEFINITIONS.filter(
    (definition) => !definition.requiresDesktop || desktopMode
  );

  useLayoutEffect(() => {
    const scrollContainer = settingsScrollContainerRef.current;
    if (!scrollContainer) return;
    scrollContainer.scrollTop = tabScrollPositionsRef.current[tab] ?? 0;
  }, [tab]);

  useEffect(() => {
    const scrollContainer = settingsScrollContainerRef.current;
    if (!scrollContainer) return;

    const rememberScrollPosition = () => {
      tabScrollPositionsRef.current[tab] = scrollContainer.scrollTop;
    };

    rememberScrollPosition();
    scrollContainer.addEventListener("scroll", rememberScrollPosition, {
      passive: true,
    });

    return () => {
      scrollContainer.removeEventListener("scroll", rememberScrollPosition);
    };
  }, [tab]);

  function handleTabChange(nextTab: SettingsTab) {
    const scrollContainer = settingsScrollContainerRef.current;
    if (scrollContainer) {
      tabScrollPositionsRef.current[tab] = scrollContainer.scrollTop;
      scrollContainer.scrollTop = tabScrollPositionsRef.current[nextTab] ?? 0;
    }
    setTab(nextTab);
  }

  function activateTab(nextTab: SettingsTab) {
    handleTabChange(nextTab);
    tabButtonRefs.current[nextTab]?.focus();
  }

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    currentTab: SettingsTab
  ) {
    const navigationTabs = visibleTabs.map((definition) => definition.value);
    const currentIndex = navigationTabs.indexOf(currentTab);
    if (currentIndex < 0 || navigationTabs.length === 0) return;

    let nextIndex = currentIndex;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (currentIndex + 1) % navigationTabs.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = (currentIndex - 1 + navigationTabs.length) % navigationTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = navigationTabs.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    activateTab(navigationTabs[nextIndex]);
  }

  function renderTabButton(definition: SettingsTabDefinition) {
    const selected = tab === definition.value;
    const tabButtonId = getSettingsTabButtonId(definition.value);
    const tabPanelId = getSettingsTabPanelId(definition.value);

    return (
      <Button
        ref={(node) => {
          tabButtonRefs.current[definition.value] = node;
        }}
        key={definition.value}
        type="button"
        role="tab"
        id={tabButtonId}
        aria-controls={tabPanelId}
        aria-selected={selected}
        tabIndex={selected ? 0 : -1}
        variant={selected ? "default" : "ghost"}
        size="sm"
        className="rounded-[var(--tile-radius,19px)]"
        onClick={() => activateTab(definition.value)}
        onKeyDown={(event) => handleTabKeyDown(event, definition.value)}
      >
        {definition.label}
      </Button>
    );
  }

  return (
    <div className="w-full" style={{ color: "var(--text)" }}>
      <SettingsPanelShell>
        <div className="flex h-full min-h-0 flex-col gap-[var(--shell-gap)]">
          <SettingsPanelDock>
            {visibleTabs.map(renderTabButton)}
          </SettingsPanelDock>

          <div
            ref={settingsScrollContainerRef}
            data-testid="settings-panel-scroll-body"
            className="flex min-h-0 flex-1 flex-col gap-[var(--shell-gap)] overflow-x-visible overflow-y-auto"
          >
            {tab === "system" && (
          <SettingsSectionCard
            data-testid="settings-system-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("system")}
            aria-labelledby={getSettingsTabButtonId("system")}
            className="space-y-[var(--shell-gap)]"
          >
            <div
              className="space-y-[var(--radius-micro)] rounded-[var(--tile-radius,19px)] border p-[var(--card-pad)]"
              style={{
                borderColor: "var(--panel-border)",
                background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
              }}
            >
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Local Preview</div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  These values are local preview context only. The backend proposal
                  truth is generated and reviewed in the Imprint workspace below.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-[var(--radius-micro)] sm:grid-cols-2">
                <div className="space-y-[calc(var(--radius-micro)/2)]">
                  <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>Guardian Nickname</div>
                  <Input value={name} onChange={(e) => setName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-[calc(var(--radius-micro)/2)]">
                  <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>User Nickname</div>
                  <Input value={uName} onChange={(e) => setUName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-[calc(var(--radius-micro)/2)] sm:col-span-2">
                  <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>Occupation / Role</div>
                  <Input value={uRole} onChange={(e) => setURole(e.target.value)} className="h-9" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
              </div>
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>Preview Prompt</div>
                <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>Notes</div>
                <Textarea value={memo} onChange={(e) => setMemo(e.target.value)} rows={4} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="flex flex-col gap-[calc(var(--radius-micro)/2)]">
                <div className="flex items-center gap-[calc(var(--radius-micro)/2)]">
                  <Button
                    type="button"
                    onClick={handleSave}
                    className="rounded-[var(--tile-radius,19px)]"
                    disabled={systemPromptSaveStatus === "saving"}
                  >
                    {systemPromptSaveStatus === "saving" ? "Saving…" : "Save"}
                  </Button>
                  {systemPromptSaveMessage &&
                    systemPromptSaveStatus !== "saving" && (
                      <span
                        className="text-xs"
                        style={{
                          color:
                            systemPromptSaveStatus === "error"
                              ? "var(--error, #ef4444)"
                              : "var(--muted)",
                        }}
                      >
                        {systemPromptSaveMessage}
                      </span>
                    )}
                </div>
                {systemPromptSaveError && (
                  <div className="text-xs" style={{ color: "var(--error, #ef4444)" }}>
                    {systemPromptSaveError}
                  </div>
                )}
              </div>
            </div>

            <SettingsSectionCard
              data-testid="imprint-workspace"
              className="space-y-[var(--shell-gap)]"
            >
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Imprint Workspace</div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  Generate Proposal uses the backend authority path. Review, edit,
                  and inspect the returned proposal through the mounted panels.
                </p>
              </div>
              <ImprintReviewPanel />
              <div className="grid gap-[var(--shell-gap)] xl:grid-cols-2">
                <PersonalFactsPanel />
                <SystemPromptInspector />
              </div>
            </SettingsSectionCard>
          </SettingsSectionCard>
        )}

        {tab === "appearance" && (
          <SettingsSectionCard
            data-testid="settings-appearance-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("appearance")}
            aria-labelledby={getSettingsTabButtonId("appearance")}
            className="space-y-[var(--shell-gap)]"
          >
            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div style={SETTINGS_DENSITY.sectionTitle}>Theme</div>
              <SegmentedThemeControl mode={mode} onChange={setMode} />
              <div className="text-xs" style={{ color: "var(--muted)" }}>Resolved: {resolved}</div>
            </div>

            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div style={SETTINGS_DENSITY.sectionTitle}>Wallpaper</div>
              <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
                <Button type="button" variant="ghost" size="sm" className="rounded-[var(--tile-radius,19px)] flex items-center gap-2" onClick={triggerFile}>
                  <ImagePlus className="h-4 w-4" />
                  Choose Image
                </Button>
                {wallpaper && (
                  <Button type="button" variant="ghost" className="rounded-[var(--tile-radius,19px)]" onClick={clearWallpaper}>
                    Clear
                  </Button>
                )}
                <span className="text-xs" style={{ color: "var(--muted)" }}>{fileLabel}</span>
              </div>
            </div>

            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div style={SETTINGS_DENSITY.sectionTitle}>Background Accents</div>
              <p className="text-xs" style={{ color: "var(--muted)" }}>Base color (used when no wallpaper)</p>
              <Input
                type="color"
                value={baseColor}
                onChange={(e) => setBaseColor(e.target.value)}
                aria-label="Base color"
                className="color-swatch"
              />
            </div>

            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div style={SETTINGS_DENSITY.sectionTitle}>File Type Colors</div>
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-[var(--shell-gap)] max-w-md">
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>PDF</span>
                  <Input id="color-pdf" type="color" value={extColors.pdf} onChange={(e) => setExtColors({ ...extColors, pdf: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>DOC</span>
                  <Input id="color-doc" type="color" value={extColors.doc} onChange={(e) => setExtColors({ ...extColors, doc: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>MD</span>
                  <Input id="color-md" type="color" value={extColors.md} onChange={(e) => setExtColors({ ...extColors, md: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>PNG</span>
                  <Input id="color-png" type="color" value={extColors.png} onChange={(e) => setExtColors({ ...extColors, png: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>SKETCH</span>
                  <Input id="color-sketch" type="color" value={extColors.sketch} onChange={(e) => setExtColors({ ...extColors, sketch: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>TXT</span>
                  <Input id="color-txt" type="color" value={extColors.txt} onChange={(e) => setExtColors({ ...extColors, txt: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>DOCX</span>
                  <Input id="color-docx" type="color" value={extColors.docx} onChange={(e) => setExtColors({ ...extColors, docx: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>JPEG</span>
                  <Input id="color-jpeg" type="color" value={extColors.jpeg} onChange={(e) => setExtColors({ ...extColors, jpeg: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-[calc(var(--radius-micro)/2)]">
                  <span className="text-xs" style={SETTINGS_DENSITY.sectionDescription}>CODEX</span>
                  <Input id="color-codex" type="color" value={extColors.codex} onChange={(e) => setExtColors({ ...extColors, codex: e.target.value })} className="color-swatch" />
                </div>
              </div>
            </div>

            <div className="space-y-[calc(var(--radius-micro)/2)]">
              <div style={SETTINGS_DENSITY.sectionTitle}>Dashboard Layout</div>
              <div className="space-y-[var(--radius-micro)] rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]">
                <div className="flex flex-wrap items-center justify-between gap-[var(--radius-micro)]">
                  <div className="space-y-[calc(var(--radius-micro)/4)]">
                    <div className="text-sm font-medium" style={SETTINGS_DENSITY.sectionTitle}>Recent thread rows</div>
                    <p className="text-xs" style={{ color: "var(--muted)" }}>Controls the 2 × N grid for Recent Threads.</p>
                  </div>
                  <span className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                    {dashboardThreadRows} {dashboardThreadRows === 1 ? "row" : "rows"}
                  </span>
                </div>
                <Input
                  type="range"
                  min={1}
                  max={4}
                  step={1}
                  value={dashboardThreadRows}
                  onChange={(e) => setDashboardThreadRows(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <div className="flex flex-col items-center gap-[var(--shell-gap)]">
              <div className="space-y-[calc(var(--radius-micro)/2)] text-center">
                <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Depth</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
                </div>
              </div>
              <div className="space-y-[calc(var(--radius-micro)/2)] text-center">
                <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Fade</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={fade} onChange={(e) => setFade(Number(e.target.value))} />
                </div>
              </div>
            </div>

          </SettingsSectionCard>
        )}

        {tab === "connectors" && (
          <SettingsSectionCard
            data-testid="settings-connectors-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("connectors")}
            aria-labelledby={getSettingsTabButtonId("connectors")}
            className="space-y-[var(--shell-gap)]"
          >
            {runtimeCapabilitiesReady &&
              connectorsCapability === "unavailable" && (
                <div className="text-sm" style={{ color: "var(--muted)" }}>
                  Connectors are unavailable in this runtime profile.
                </div>
              )}
            {!runtimeCapabilitiesReady && (
              <div className="text-sm" style={{ color: "var(--muted)" }}>
                Checking connector availability…
              </div>
            )}
            {loading && <div className="text-sm" style={{ color: "var(--muted)" }}>Loading connectors…</div>}
            {error && <div className="text-sm" style={{ color: "var(--danger-text)" }}>{error}</div>}
            {runtimeCapabilitiesReady &&
            connectorsCapability !== "unavailable" &&
            Array.isArray(connectors) &&
            connectors.length > 0 ? (
              connectors.map((connector) => (
                <ConnectorCard
                  key={connector.id}
                  connector={connector}
                  onUpdate={updateConnector}
                  onAuthorize={authorizeOAuth}
                  onTest={testConnector}
                  onSync={syncConnector}
                />
              ))
            ) : (
              runtimeCapabilitiesReady &&
              connectorsCapability !== "unavailable" &&
              !loading &&
              !error && (
                <div className="text-sm" style={{ color: "var(--muted)" }}>No connectors available</div>
              )
            )}
          </SettingsSectionCard>
        )}

        {tab === "data" && (
          <SettingsSectionCard
            data-testid="settings-data-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("data")}
            aria-labelledby={getSettingsTabButtonId("data")}
            className="space-y-[var(--shell-gap)]"
          >
            <div className="space-y-[var(--radius-micro)] rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]">
              <div className="flex items-start justify-between gap-[var(--radius-micro)]">
                <div className="space-y-[calc(var(--radius-micro)/2)]">
                  <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>
                    Migrate from ChatGPT
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                    Import your ChatGPT export. Codexify will preserve project
                    grouping and remove tool-output noise from the user-visible
                    transcript.
                  </p>
                </div>
                <div
                  className="shrink-0 rounded-full border px-2 py-1 text-[11px] font-medium"
                  style={{
                    borderColor: migrationComplete
                      ? "rgba(34, 197, 94, 0.35)"
                      : "var(--panel-border)",
                    color: migrationComplete
                      ? "rgb(134, 239, 172)"
                      : "var(--muted)",
                  }}
                >
                  {migrationComplete ? "Complete" : "Optional"}
                </div>
              </div>

              <div className="grid gap-[var(--radius-micro)] sm:grid-cols-2">
                <Button
                  type="button"
                  onClick={() => {
                    setImportPanelHidden(false);
                    setChatGPTModalOpen(true);
                  }}
                  disabled={isImportActive}
                  className="rounded-[var(--tile-radius,19px)] w-full"
                >
                  {isImportActive ? "Import in progress..." : "Import ChatGPT history"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleDownloadExport}
                  className="rounded-[var(--tile-radius,19px)] w-full"
                >
                  Download Codexify ZIP export
                </Button>
              </div>

              {shouldShowImportStatusPanel && (
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[calc(var(--card-pad)*0.75)]">
                  <div className="flex items-center justify-between gap-[var(--radius-micro)]">
                    <div className="flex items-center gap-[calc(var(--radius-micro)/2)]">
                      {isImportActive && (
                        <span className="inline-block h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      )}
                      <span
                        className="rounded-full border px-2 py-0.5 text-[11px] font-medium"
                        style={{
                          borderColor:
                            importStatus === "failed"
                              ? "rgba(248, 113, 113, 0.4)"
                              : importStatus === "succeeded"
                                ? "rgba(34, 197, 94, 0.4)"
                                : "rgba(125, 211, 252, 0.4)",
                          color:
                            importStatus === "failed"
                              ? "rgb(254, 202, 202)"
                              : importStatus === "succeeded"
                                ? "rgb(134, 239, 172)"
                                : "rgb(186, 230, 253)",
                        }}
                      >
                        {statusLabel(importStatus)}
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleImportPanelAction}
                      className="rounded-[var(--tile-radius,19px)]"
                    >
                      {isImportTerminal ? "Dismiss" : "Hide"}
                    </Button>
                  </div>
                  <div className="mt-[calc(var(--radius-micro)/2)] text-xs" style={{ color: "var(--muted)" }}>
                    Elapsed: {importElapsed}
                    {importLastEventAt > 0 ? " • Live updates active" : ""}
                  </div>
                  {importTaskId && (
                    <div className="mt-[calc(var(--radius-micro)/4)] text-[11px] break-all" style={{ color: "var(--muted)" }}>
                      Task ID: {importTaskId}
                    </div>
                  )}
                  <div className="mt-[calc(var(--radius-micro)/4)] text-xs">{importDetail || "Import task running."}</div>
                  <div className="mt-[calc(var(--radius-micro)/2)] text-xs" style={{ color: "var(--muted)" }}>
                    You can navigate away; this continues in the background.
                  </div>
                </div>
              )}

              {!shouldShowImportStatusPanel && isImportActive && (
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[calc(var(--card-pad)*0.75)] text-xs flex items-center justify-between gap-[var(--radius-micro)]">
                  <span>Import is running in the background.</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setImportPanelHidden(false)}
                    className="rounded-[var(--tile-radius,19px)]"
                  >
                    Show status
                  </Button>
                </div>
              )}

              {!migrationComplete && (
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setMigrationStepSkipped(true)}
                    className="rounded-[var(--tile-radius,19px)]"
                  >
                    Skip
                  </Button>
                </div>
              )}

              {migrationStats && (
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[calc(var(--card-pad)*0.75)]">
                  <div className="text-xs font-semibold uppercase tracking-wide" style={SETTINGS_DENSITY.metaLabel}>
                    Import Summary
                  </div>
                  <div className="mt-[calc(var(--radius-micro)/2)] grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    <div>Threads imported</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.threads_imported ?? 0}
                    </div>
                    <div>Messages imported</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.messages_imported ?? 0}
                    </div>
                    <div>Projects created</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.projects_created ?? 0}
                    </div>
                    <div>Projects reused</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.projects_reused ?? 0}
                    </div>
                    <div>Messages filtered</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.messages_filtered ?? 0}
                    </div>
                  </div>
                </div>
              )}

              {migrationStepSkipped && !migrationStats && (
                <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                  Migration step skipped for this session. You can come back to
                  import any time.
                </p>
              )}
            </div>

            <ChatGPTImportModal
              open={chatGPTModalOpen}
              onOpenChange={setChatGPTModalOpen}
              userName={userName}
              onImported={(stats) => {
                setMigrationStats(stats);
                setMigrationStepSkipped(false);
              }}
            />
          </SettingsSectionCard>
        )}

        {tab === "connection" && desktopMode && (
          <SettingsSectionCard
            data-testid="settings-connection-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("connection")}
            aria-labelledby={getSettingsTabButtonId("connection")}
            className="space-y-[var(--shell-gap)]"
          >
            <div className="space-y-[var(--radius-micro)] rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]">
              <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Desktop Connection</div>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Configure backend routing and the public base URL used for copied share links.
              </p>
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <label className="text-xs" style={{ color: "var(--muted)" }}>Backend Base URL</label>
                <Input
                  value={desktopBackendBaseUrl}
                  onChange={(event) => setDesktopBackendBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:8888"
                />
              </div>
              <div className="space-y-[calc(var(--radius-micro)/2)]">
                <label className="text-xs" style={{ color: "var(--muted)" }}>Share Public Base URL</label>
                <Input
                  value={desktopShareBaseUrl}
                  onChange={(event) => setDesktopShareBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:5173"
                />
              </div>
              {runtimeConfigSnapshot ? (
                <div
                  className="rounded-[14px] border px-3 py-2 text-[11px]"
                  style={{
                    borderColor: "var(--panel-border)",
                    background:
                      "color-mix(in oklab, var(--panel-sheet) 92%, transparent)",
                    color: "var(--muted)",
                  }}
                >
                  <div>Active backend: {runtimeConfigSnapshot.backendBaseUrl || "(not set)"}</div>
                  <div>Active API base: {runtimeConfigSnapshot.apiBaseUrl || "(not set)"}</div>
                  <div>Active events endpoint: {runtimeConfigSnapshot.sseUrl || "(not set)"}</div>
                </div>
              ) : null}
              <div className="flex flex-wrap items-center gap-[var(--radius-micro)]">
                <Button
                  type="button"
                  onClick={handleSaveConnectionSettings}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Save Connection
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleTestConnection}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Test Connection
                </Button>
              </div>
            </div>

            <div className="space-y-[var(--radius-micro)] rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]">
              <div className="text-sm font-semibold" style={SETTINGS_DENSITY.sectionTitle}>Local API Key (Secure Store)</div>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Stored in macOS keychain for desktop local-safe auth.
              </p>
              <Input
                type="password"
                value={desktopApiKeyInput}
                onChange={(event) => setDesktopApiKeyInput(event.target.value)}
                placeholder="Enter Guardian API key"
              />
              <div className="flex flex-wrap items-center gap-[var(--radius-micro)]">
                <Button
                  type="button"
                  onClick={handleSaveDesktopApiKey}
                  disabled={connectionBusy || !desktopApiKeyInput.trim()}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Save API Key
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleClearDesktopApiKey}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Clear API Key
                </Button>
              </div>
            </div>

            {connectionMessage && (
              <div className="text-xs" style={{ color: "rgb(134, 239, 172)" }}>{connectionMessage}</div>
            )}
            {connectionError && (
              <div className="text-xs" style={{ color: "var(--danger-text)" }}>{connectionError}</div>
            )}
          </SettingsSectionCard>
        )}

        {tab === "personalFacts" && (
          <SettingsSectionCard
            data-testid="settings-panel-personal-facts"
            role="tabpanel"
            id={getSettingsTabPanelId("personalFacts")}
            aria-labelledby={getSettingsTabButtonId("personalFacts")}
            className="space-y-4"
          >
            <PersonalFactsPanel />
          </SettingsSectionCard>
        )}

        {tab === "diagnostics" && (
          <SettingsSectionCard
            data-testid="settings-diagnostics-surface"
            role="tabpanel"
            id={getSettingsTabPanelId("diagnostics")}
            aria-labelledby={getSettingsTabButtonId("diagnostics")}
            className="space-y-4"
          >
            <MemoryBrowser activeThreadId={activeThreadId} />
          </SettingsSectionCard>
        )}
          </div>
        </div>
      </SettingsPanelShell>
    </div>
  );
}

export default SettingsView;
