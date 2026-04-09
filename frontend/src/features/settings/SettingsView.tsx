import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/controls/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { ImagePlus } from "lucide-react";
import { useConnectors } from "@/features/connectors/useConnectors";
import { ConnectorCard } from "@/features/connectors/ConnectorCard";
import ImprintReviewPanel from "@/features/settings/components/ImprintReviewPanel";
import PersonaSettingsPanel from "@/features/settings/components/PersonaSettingsPanel";
import PersonalFactsPanel from "@/features/settings/components/PersonalFactsPanel";
import SettingsPanelShell from "@/features/settings/components/SettingsPanelShell";
import type { SettingsTab } from "@/features/settings/components/SettingsPanelDock";
import SystemPromptInspector from "@/features/settings/components/SystemPromptInspector";
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
  const [tab, setTab] = useState<SettingsTab>("appearance");
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

  return (
    <SettingsPanelShell
      activeTab={tab}
      desktopMode={desktopMode}
      onTabChange={setTab}
    >
      {tab === "system" && (
        <div className="space-y-[var(--shell-gap)]">
            <div
              className="space-y-2 rounded-[var(--tile-radius,19px)] border p-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
              }}
            >
              <div className="space-y-1">
                <div className="text-sm font-semibold">Local Preview</div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  These values are local preview context only. The backend proposal
                  truth is generated and reviewed in the Imprint workspace below.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <div className="text-sm font-medium">Guardian Nickname</div>
                  <Input value={name} onChange={(e) => setName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-medium">User Nickname</div>
                  <Input value={uName} onChange={(e) => setUName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <div className="text-sm font-medium">Occupation / Role</div>
                  <Input value={uRole} onChange={(e) => setURole(e.target.value)} className="h-9" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-sm font-medium">Preview Prompt</div>
                <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-medium">Notes</div>
                <Textarea value={memo} onChange={(e) => setMemo(e.target.value)} rows={4} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    onClick={handleSave}
                    className="rounded-[var(--tile-radius,19px)]"
                    disabled={systemPromptSaveStatus === "saving"}
                  >
                    {systemPromptSaveStatus === "saving" ? "Saving…" : "Save"}
                  </Button>
                  {systemPromptSaveMessage && systemPromptSaveStatus !== "saving" && (
                    <span
                      className="text-xs opacity-70"
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

            <section
              className="space-y-4 rounded-[var(--tile-radius,19px)] border p-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
              }}
              data-testid="imprint-workspace"
            >
              <div className="space-y-1">
                <div className="text-sm font-semibold">Imprint Workspace</div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  Generate Proposal uses the backend authority path. Review, edit,
                  and inspect the returned proposal through the mounted panels.
                </p>
              </div>
              <ImprintReviewPanel />
              <div className="grid gap-4 xl:grid-cols-2">
                <PersonaSettingsPanel />
                <SystemPromptInspector />
              </div>
            </section>
          </div>
        )}

      {tab === "appearance" && (
        <div className="space-y-[var(--shell-gap)]">
            <div className="space-y-2">
              <div className="text-sm font-semibold">Theme</div>
              <SegmentedThemeControl mode={mode} onChange={setMode} />
              <div className="text-xs opacity-80">Resolved: {resolved}</div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold">Wallpaper</div>
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
                <span className="text-xs opacity-70">{fileLabel}</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">Background Accents</div>
              <div className="text-xs opacity-80">Base color (used when no wallpaper)</div>
              <Input
                type="color"
                value={baseColor}
                onChange={(e) => setBaseColor(e.target.value)}
                aria-label="Base color"
                className="color-swatch"
              />
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">File Type Colors</div>
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-4 max-w-md">
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">PDF</span>
                  <Input id="color-pdf" type="color" value={extColors.pdf} onChange={(e) => setExtColors({ ...extColors, pdf: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">DOC</span>
                  <Input id="color-doc" type="color" value={extColors.doc} onChange={(e) => setExtColors({ ...extColors, doc: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">MD</span>
                  <Input id="color-md" type="color" value={extColors.md} onChange={(e) => setExtColors({ ...extColors, md: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">PNG</span>
                  <Input id="color-png" type="color" value={extColors.png} onChange={(e) => setExtColors({ ...extColors, png: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">SKETCH</span>
                  <Input id="color-sketch" type="color" value={extColors.sketch} onChange={(e) => setExtColors({ ...extColors, sketch: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">TXT</span>
                  <Input id="color-txt" type="color" value={extColors.txt} onChange={(e) => setExtColors({ ...extColors, txt: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">DOCX</span>
                  <Input id="color-docx" type="color" value={extColors.docx} onChange={(e) => setExtColors({ ...extColors, docx: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">JPEG</span>
                  <Input id="color-jpeg" type="color" value={extColors.jpeg} onChange={(e) => setExtColors({ ...extColors, jpeg: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">CODEX</span>
                  <Input id="color-codex" type="color" value={extColors.codex} onChange={(e) => setExtColors({ ...extColors, codex: e.target.value })} className="color-swatch" />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">Dashboard Layout</div>
              <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">Recent thread rows</div>
                    <div className="text-xs opacity-70">Controls the 2 × N grid for Recent Threads.</div>
                  </div>
                  <span className="text-xs font-semibold">
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

            <div className="flex flex-col items-center space-y-4">
              <div className="space-y-2 text-center">
                <div className="text-sm font-semibold">Depth</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
                </div>
              </div>
              <div className="space-y-2 text-center">
                <div className="text-sm font-semibold">Fade</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={fade} onChange={(e) => setFade(Number(e.target.value))} />
                </div>
              </div>
            </div>

          </div>
        )}

      {tab === "connectors" && (
        <div className="space-y-[var(--shell-gap)]">
            {runtimeCapabilitiesReady &&
              connectorsCapability === "unavailable" && (
                <div className="text-sm opacity-70">
                  Connectors are unavailable in this runtime profile.
                </div>
              )}
            {!runtimeCapabilitiesReady && (
              <div className="text-sm opacity-70">
                Checking connector availability…
              </div>
            )}
            {loading && <div className="text-sm opacity-70">Loading connectors…</div>}
            {error && <div className="text-sm text-red-500">{error}</div>}
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
                <div className="text-sm opacity-70">No connectors available</div>
              )
            )}
          </div>
        )}

      {tab === "data" && (
        <div className="space-y-[var(--shell-gap)]">
            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="text-sm font-semibold">
                    Migrate from ChatGPT
                  </div>
                  <p className="text-xs opacity-70 leading-relaxed">
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

              <div className="grid gap-2 sm:grid-cols-2">
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
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
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
                  <div className="mt-2 text-xs opacity-80">
                    Elapsed: {importElapsed}
                    {importLastEventAt > 0 ? " • Live updates active" : ""}
                  </div>
                  {importTaskId && (
                    <div className="mt-1 text-[11px] opacity-70 break-all">
                      Task ID: {importTaskId}
                    </div>
                  )}
                  <div className="mt-1 text-xs">{importDetail || "Import task running."}</div>
                  <div className="mt-2 text-xs opacity-70">
                    You can navigate away; this continues in the background.
                  </div>
                </div>
              )}

              {!shouldShowImportStatusPanel && isImportActive && (
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-3 text-xs flex items-center justify-between gap-3">
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
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide opacity-70">
                    Import Summary
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
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
                <p className="text-xs opacity-70 leading-relaxed">
                  Migration step skipped for this session. You can come back to
                  import any time.
                </p>
              )}
            </div>
          </div>
        )}

      {tab === "connection" && desktopMode && (
        <div className="space-y-[var(--shell-gap)]">
            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="text-sm font-semibold">Desktop Connection</div>
              <p className="text-xs opacity-70">
                Configure backend routing and the public base URL used for copied share links.
              </p>
              <div className="space-y-2">
                <label className="text-xs opacity-80">Backend Base URL</label>
                <Input
                  value={desktopBackendBaseUrl}
                  onChange={(event) => setDesktopBackendBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:8888"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs opacity-80">Share Public Base URL</label>
                <Input
                  value={desktopShareBaseUrl}
                  onChange={(event) => setDesktopShareBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:5173"
                />
              </div>
              {runtimeConfigSnapshot ? (
                <div
                  className="rounded-[14px] border px-3 py-2 text-[11px] opacity-80"
                  style={{
                    borderColor: "var(--panel-border)",
                    background:
                      "color-mix(in oklab, var(--panel-sheet) 92%, transparent)",
                  }}
                >
                  <div>Active backend: {runtimeConfigSnapshot.backendBaseUrl || "(not set)"}</div>
                  <div>Active API base: {runtimeConfigSnapshot.apiBaseUrl || "(not set)"}</div>
                  <div>Active events endpoint: {runtimeConfigSnapshot.sseUrl || "(not set)"}</div>
                </div>
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
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

            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="text-sm font-semibold">Local API Key (Secure Store)</div>
              <p className="text-xs opacity-70">
                Stored in macOS keychain for desktop local-safe auth.
              </p>
              <Input
                type="password"
                value={desktopApiKeyInput}
                onChange={(event) => setDesktopApiKeyInput(event.target.value)}
                placeholder="Enter Guardian API key"
              />
              <div className="flex flex-wrap items-center gap-2">
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
              <div className="text-xs text-emerald-300">{connectionMessage}</div>
            )}
            {connectionError && (
              <div className="text-xs text-red-400">{connectionError}</div>
            )}
          </div>
        )}

      {tab === "personalFacts" && (
        <div
          className="space-y-[var(--shell-gap)]"
          id="settings-panel-personalFacts"
          role="tabpanel"
          aria-labelledby="settings-tab-personalFacts"
          data-testid="settings-panel-personal-facts"
        >
            <PersonalFactsPanel />
        </div>
      )}

      <ChatGPTImportModal
        open={chatGPTModalOpen}
        onOpenChange={setChatGPTModalOpen}
        userName={userName}
        onImported={(stats) => {
          setMigrationStats(stats);
          setMigrationStepSkipped(false);
        }}
      />
    </SettingsPanelShell>
  );
}

export default SettingsView;
