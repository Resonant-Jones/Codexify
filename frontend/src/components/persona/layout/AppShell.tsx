/**
 * TODO: TOKEN MIGRATION PLAN — Codexify UI Architecture
 *
 * Current state:
 *   - Inline CSS variables declared directly in AppShell serve as runtime design tokens.
 *   - Variables like `--bezel`, `--rim`, `--panel-bg`, etc., are effectively local tokens.
 *
 * Next phase:
 *   - Extract all static vars into `/src/theme/tokens.json`.
 *   - Create `/src/theme/index.ts` to import JSON and export `cssVars` for React + CSS injection.
 *   - Optional: Add Style Dictionary or a simple script to export Figma/Swift/React Native tokens.
 *
 * Goal:
 *   - Establish a universal token layer for Codexify and PulseOS.
 *   - Maintain parity across Web, Electron, and mobile builds.
 *
 * Notes:
 *   - Do NOT rename the existing CSS vars — their current names are the future token keys.
 *   - Migration should be trivial if naming consistency is preserved.
 */
import api from "@/lib/api";
import { Settings2 } from "lucide-react";
import React, { PropsWithChildren, useCallback, useEffect, useMemo, useState } from "react";

// Global font injection for Apple system font
if (typeof window !== "undefined") {
  document.documentElement.style.fontFamily =
    'SF Pro Display, SF Pro Icons, Apple System, BlinkMacSystemFont, ".SFNSDisplay-Regular", "Helvetica Neue", Helvetica, Arial, sans-serif';
}
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import GuardianChat from "@/features/chat/GuardianChat";
import DashboardView from "@/components/dashboard/DashboardView";
import SettingsView from "@/features/settings/SettingsView";
import PersonaStudioPage from "@/features/personaStudio/PersonaStudioPage";
import ErrorBoundary from "@/components/ErrorBoundary";
import DocumentsView from "@/components/documents/DocumentsView";
import GuardianChatWithSidebar from "@/components/persona/layout/GuardianChatWithSidebar";
import {
  MOBILE_MOTION,
  getMobileWorkspaceMotionState,
} from "@/components/persona/layout/mobileMotionContract";
import WorkspaceDrawer from "@/features/workspace/components/WorkspaceDrawer";
import { useBreakpoint } from "./useBreakpoint";
import { useShellViewportProfile } from "./shellBreakpointContract";
import { getMobileShellProfile } from "./mobileShellProfile";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import useRuntimeHealth from "@/hooks/useRuntimeHealth";
import { useViewportInsets } from "@/hooks/useViewportInsets";
import {
  describeProviderState,
  PROVIDER_RUNTIME_STATES,
  RUNTIME_HEALTH_FAILURE_KINDS,
  RUNTIME_HEALTH_STATUSES,
  type ProviderRuntimeState,
} from "@/contracts/runtimeTokens";
import { checkAuthGate, useAuthState } from "@/lib/authState";
import { ExtColors, GalleryItem, ThemeMode, Thread, Message } from "@/types/ui";
import { DocumentLike, type DocumentScope } from "@/types/documents";
import { SessionSpine } from "@/state/session/SessionSpine";
import { listCodexEntries, CodexEntrySummary } from "@/api/codex";
import ToastPortal from "@/components/ui/ToastPortal";
import useUploader from "@/hooks/useUploader";
import { useRenderableMediaSrc } from "@/hooks/useRenderableMediaSrc";
import ContextMenu from "@/components/ui/ContextMenu";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { ShareButton } from "@/components/ShareButton";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import { useRuntimeRouteCapability } from "@/lib/runtimeRouteCapabilities";
import {
  useWorkspaceState,
  type WorkspaceOpenRequest,
} from "@/features/workspace/state/useWorkspaceState";
import {
  useWorkspaceUiState,
  type WorkspaceDrawerTab,
} from "@/features/workspace/state/useWorkspaceUiState";
import { useWorkspaceLayoutMode } from "@/features/workspace/state/useWorkspaceLayoutMode";
import {
  createDocumentContextTile,
  type DocumentContextTile,
} from "@/lib/documentContext";
import {
  getMobileTopNavDockStyle,
  getMobileNavigationControlStyle,
  getMobileTopNavRailStyle,
} from "./mobileNavigationContract";
import {
  getWorkspaceAffordanceCopy,
  getWorkspaceAffordanceIcon,
  getWorkspaceAffordanceState,
  getWorkspaceAffordanceSurfaceStyle,
  WORKSPACE_AFFORDANCE,
} from "./workspaceAffordanceContract";
import { usePressFeedback } from "@/hooks/usePressFeedback";

// TEMPORARY: inject static design tokens until full migration is done.
import { injectCssVars } from "@/theme";
injectCssVars();
/* ──────────────────────────────────────────────────────────────────────────
   TUNING PRIMER (safe knobs)
   - Per-VIEW overrides: add CSS vars on the wrapper just after `{view === "…"`:
       --radius, --frame, --bezel, --rim, --gutter, --card-pad,
       --workspace-w, --min-h/--max-h, --min-w/--max-w
   - Per-CARD overrides: add vars on the *placement wrapper* (the <div> with
     `style={{ padding: "var(--board-edge)", … }}`) using:
       --w/--min-w/--max-w, --h/--min-h/--max-h, --flex
     Examples:
       • Fixed height:         {"--h":"560px","--flex":"0 0 auto"}
       • Responsive floor:     {"--min-h":"clamp(520px,70vh,900px)"}
       • Share space (2:1):    {"--flex":"2 1 0%"}  vs  {"--flex":"1 1 0%"}
       • Workspace width:      {"--w":"clamp(16rem,22vw,28rem)","--flex":"0 0 var(--w)"}
   - Keep aberration off on glass: <FrameCard liquidBezel shimmer tone="base"… aberration={0} />
   ────────────────────────────────────────────────────────────────────────── */
/* ─────────────────────────────────────────────────────────────────────────────
   🧠 SECTION: Theme Mode Type
   We use a simple type alias for the resolved theme mode,
   which will always be either "light" or "dark".
   ───────────────────────────────────────────────────────────────────────────── */
type Resolved = "light" | "dark";
type LayoutMode = "focus" | "zen";
type AppShellView =
  | "dashboard"
  | "documents"
  | "gallery"
  | "guardian"
  | "settings"
  | "personaStudio";
type WorkspaceShellView = "dashboard" | "documents" | "guardian";
type DocItem = DocumentLike & { ext: keyof ExtColors };
type AppShellProps = PropsWithChildren<{
  startupLocked?: boolean;
  startupOverlay?: React.ReactNode;
}>;
type PhonePressButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  isPhoneShell: boolean;
  square?: boolean;
};

function PhonePressButton({
  isPhoneShell,
  square = false,
  className,
  style,
  children,
  ...buttonProps
}: PhonePressButtonProps) {
  const pressFeedback = usePressFeedback({ enabled: isPhoneShell });

  return (
    <button
      {...buttonProps}
      {...pressFeedback.getPressFeedbackProps({
        className,
        style: {
          ...getMobileNavigationControlStyle(isPhoneShell, { square }),
          ...style,
        },
      })}
    >
      {children}
    </button>
  );
}

const APP_SHELL_VIEWS = [
  "dashboard",
  "documents",
  "gallery",
  "guardian",
  "settings",
  "personaStudio",
] as const satisfies readonly AppShellView[];

const APP_SHELL_VIEW_SET = new Set<AppShellView>(APP_SHELL_VIEWS);

function isAppShellView(value: string | null): value is AppShellView {
  return value != null && APP_SHELL_VIEW_SET.has(value as AppShellView);
}

function resolveViewFromPathname(pathname: string): AppShellView | null {
  if (pathname.startsWith("/persona-studio")) return "personaStudio";
  if (pathname.startsWith("/settings")) return "settings";
  if (pathname.startsWith("/gallery")) return "gallery";
  if (pathname.startsWith("/documents")) return "documents";
  if (pathname.startsWith("/dashboard")) return "dashboard";
  if (pathname.startsWith("/chat")) return "guardian";
  return null;
}

function resolvePathForView(view: AppShellView, threadId: number | null): string {
  switch (view) {
    case "guardian":
      return threadId != null ? `/chat/${threadId}` : "/chat";
    case "documents":
      return "/documents";
    case "gallery":
      return "/gallery";
    case "settings":
      return "/settings";
    case "personaStudio":
      return "/persona-studio";
    case "dashboard":
    default:
      return "/dashboard";
  }
}

function isWorkspaceShellView(view: AppShellView): view is WorkspaceShellView {
  return view === "dashboard" || view === "documents" || view === "guardian";
}

function normalizeDoc(raw: any, idx = 0): DocItem {
  const filename =
    typeof raw?.filename === "string" && raw.filename.trim()
      ? raw.filename.trim()
      : undefined;
  const title =
    raw?.title ||
    raw?.name ||
    (filename ? filename.replace(/\.[^./\\]+$/, "") : "") ||
    "Untitled";
  const extFromFilename = (() => {
    if (!filename) return undefined;
    const match = filename.toLowerCase().match(/\.([a-z0-9]+)$/i);
    return match?.[1];
  })();
  // Preserve any existing media URL so WorkspacePane can preview attachments.
  const srcUrl =
    (typeof raw?.src_url === "string" && raw.src_url) ||
    (typeof raw?.srcUrl === "string" && raw.srcUrl) ||
    (typeof raw?.src === "string" && raw.src) ||
    (typeof raw?.url === "string" && raw.url) ||
    undefined;
  const embeddingStatus =
    typeof raw?.embeddingStatus === "string"
      ? raw.embeddingStatus
      : typeof raw?.embedding_status === "string"
        ? raw.embedding_status
        : undefined;
  const embeddingError =
    typeof raw?.embeddingError === "string"
      ? raw.embeddingError
      : typeof raw?.embedding_error === "string"
        ? raw.embedding_error
        : undefined;
  const embeddingStartedAt =
    typeof raw?.embeddingStartedAt === "string"
      ? raw.embeddingStartedAt
      : typeof raw?.embedding_started_at === "string"
        ? raw.embedding_started_at
        : undefined;
  const embeddingCompletedAt =
    typeof raw?.embeddingCompletedAt === "string"
      ? raw.embeddingCompletedAt
      : typeof raw?.embedding_completed_at === "string"
        ? raw.embedding_completed_at
        : undefined;
  const projectIdRaw =
    raw?.projectId ??
    raw?.project_id ??
    raw?.project?.id ??
    undefined;
  const threadIdRaw =
    raw?.threadId ??
    raw?.thread_id ??
    raw?.thread?.id ??
    undefined;
  const projectId = Number(projectIdRaw);
  const threadId = Number(threadIdRaw);
  return {
    id: raw?.id || raw?.document_id || `${title}-${raw?.ext || "md"}-${idx}`,
    name: raw?.name || filename || title,
    title,
    ext: (
      raw?.ext ||
      raw?.extension ||
      raw?.format ||
      extFromFilename ||
      "md"
    ) as keyof ExtColors,
    type: raw?.type === "codex_entry" ? "codex_entry" : "file",
    content:
      typeof raw?.content === "string"
        ? raw.content
        : typeof raw?.parsed_text === "string"
          ? raw.parsed_text
          : typeof raw?.parsedText === "string"
            ? raw.parsedText
            : undefined,
    parsed_text:
      typeof raw?.parsed_text === "string"
        ? raw.parsed_text
        : typeof raw?.parsedText === "string"
          ? raw.parsedText
          : typeof raw?.content === "string"
            ? raw.content
            : undefined,
    parsedText:
      typeof raw?.parsedText === "string"
        ? raw.parsedText
        : typeof raw?.parsed_text === "string"
          ? raw.parsed_text
          : typeof raw?.content === "string"
            ? raw.content
            : undefined,
    mime_type:
      typeof raw?.mime_type === "string"
        ? raw.mime_type
        : typeof raw?.mimeType === "string"
          ? raw.mimeType
          : typeof raw?.content_type === "string"
            ? raw.content_type
            : undefined,
    mimeType:
      typeof raw?.mimeType === "string"
        ? raw.mimeType
        : typeof raw?.mime_type === "string"
          ? raw.mime_type
          : typeof raw?.content_type === "string"
            ? raw.content_type
            : undefined,
    mock: Boolean(raw?.mock),
    createdAt: raw?.createdAt || raw?.created_at,
    src_url: srcUrl,
    projectId: Number.isFinite(projectId) ? projectId : undefined,
    threadId: Number.isFinite(threadId) ? threadId : undefined,
    embeddingStatus,
    embeddingError,
    embeddingStartedAt,
    embeddingCompletedAt,
  };
}

function normalizeDocIdentity(doc: DocumentLike): string {
  const type = doc?.type === "codex_entry" ? "codex_entry" : "file";
  const id = typeof doc?.id === "string" ? doc.id.trim() : "";
  if (id) return `${type}:${id}`;
  const title = String(doc?.title || doc?.name || "untitled")
    .trim()
    .toLowerCase();
  const ext = String(doc?.ext || "").trim().toLowerCase();
  return `${type}:${title}:${ext}`;
}

function dedupeDocItems(items: DocItem[]): DocItem[] {
  const seen = new Set<string>();
  const deduped: DocItem[] = [];
  for (const doc of items) {
    const key = normalizeDocIdentity(doc);
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(doc);
  }
  return deduped;
}

function unwrapDocumentArray(value: any): any[] {
  const unwrap = (candidate: any): any => {
    if (!candidate || typeof candidate !== "object") return candidate;
    return (
      (candidate as any).documents ??
      (candidate as any).items ??
      (candidate as any).data ??
      (candidate as any).results ??
      candidate
    );
  };
  const candidate1 = Array.isArray(value) ? value : unwrap(value);
  const candidate2 = Array.isArray(candidate1) ? candidate1 : unwrap(candidate1);
  return Array.isArray(candidate2) ? candidate2 : [];
}

function routeThreadIdFromPath(pathname: string): number | null {
  const match = pathname.match(/^\/chat\/(\d+)/);
  if (!match) return null;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

function readRouteThreadId(): number | null {
  if (typeof window === "undefined") return null;
  return routeThreadIdFromPath(window.location.pathname);
}

function normalizeGallerySrc(value: unknown): string {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  return normalizeMediaUrl(trimmed);
}

function isTransientFailedGalleryItem(raw: any): boolean {
  const candidate = raw?.src ?? raw?.src_url ?? raw?.srcUrl ?? raw?.url;
  return (
    Boolean(raw?.mock) &&
    typeof candidate === "string" &&
    candidate.trim().toLowerCase().startsWith("data:")
  );
}

function normalizeGalleryItem(raw: any): GalleryItem | null {
  if (isTransientFailedGalleryItem(raw)) return null;
  const src = normalizeGallerySrc(
    raw?.src ?? raw?.src_url ?? raw?.srcUrl ?? raw?.url
  );
  if (!src) return null;
  const prompt =
    typeof raw?.prompt === "string" && raw.prompt.trim()
      ? raw.prompt.trim()
      : "Untitled image";
  return {
    src,
    prompt,
    mock: Boolean(raw?.mock),
  };
}

function AppShellGalleryImage({
  src,
  alt,
}: {
  src: string;
  alt: string;
}) {
  const renderableSrc = useRenderableMediaSrc(src);
  const [hasLoadError, setHasLoadError] = useState(false);

  useEffect(() => {
    setHasLoadError(false);
  }, [renderableSrc.src]);

  const showImage =
    renderableSrc.status === "ready" &&
    !!renderableSrc.src &&
    !hasLoadError;

  if (!showImage) {
    return (
      <div className="absolute inset-0 grid place-items-center text-xs opacity-70">
        {renderableSrc.status === "loading" ? "Loading image" : "Image unavailable"}
      </div>
    );
  }

  return (
    <img
      src={renderableSrc.src}
      alt={alt}
      className="absolute inset-0 h-full w-full object-cover"
      onError={() => setHasLoadError(true)}
    />
  );
}

function normalizeInterceptPath(url: unknown): string {
  if (typeof url !== "string" || !url.trim()) return "";
  try {
    const base =
      typeof window !== "undefined" ? window.location.origin : "http://localhost";
    return new URL(url, base).pathname;
  } catch {
    return url;
  }
}

function parseRequestPayload(data: unknown): Record<string, unknown> {
  if (!data) return {};
  if (typeof data === "string") {
    try {
      const parsed = JSON.parse(data);
      return parsed && typeof parsed === "object"
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  if (typeof data === "object") {
    return data as Record<string, unknown>;
  }
  return {};
}

function normalizeShellToken(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function extractCompletionThreadId(pathname: string): string | null {
  const match = pathname.match(/\/chat\/([^/]+)\/complete$/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function extractMessageThreadId(pathname: string): string | null {
  const match = pathname.match(/\/chat\/([^/]+)\/messages$/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function extractCancelTaskId(pathname: string): string | null {
  const match = pathname.match(/\/tasks\/([^/]+)\/cancel$/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function isCreateMessagePath(pathname: string): boolean {
  return pathname.endsWith("/chat/messages");
}

function normalizeProjectName(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function isDefaultProjectAlias(value: unknown): boolean {
  const normalized = normalizeProjectName(value);
  return normalized === "general" || normalized === "loose threads";
}

async function createProjectApi(payload: { name: string; icon: string }) {
  const paths = ["/api/projects", "/projects"];
  let lastErr: any = null;
  for (const path of paths) {
    try {
      return await api.post(path, payload);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        lastErr = err;
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error("Project create route unavailable");
}

function findDefaultProjectId(projects: any[]): number | null {
  if (!Array.isArray(projects)) return null;
  const match = projects.find((project) => isDefaultProjectAlias(project?.name));
  const rawId = match?.id ?? match?.project_id ?? null;
  const parsed = Number(rawId);
  return Number.isFinite(parsed) ? parsed : null;
}

/* ─────────────────────────────────────────────────────────────────────────────
   🧠 SECTION: Theme Preference Handling
   This function takes in any value and ensures it matches one of our accepted
   theme modes: "light", "dark", or "system". If not, we default to "system".
   ───────────────────────────────────────────────────────────────────────────── */
function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

function hexToRgbChannels(input: string): { r: number; g: number; b: number } | null {
  if (!input) return null;
  const value = input.trim();
  const match = value.match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!match) return null;
  let hex = match[1];
  if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
  const num = Number.parseInt(hex, 16);
  if (Number.isNaN(num)) return null;
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function relativeLuminanceFromHex(color: string): number {
  const rgb = hexToRgbChannels(color);
  if (!rgb) return 0;
  const srgb = (c: number) => {
    const channel = c / 255;
    return channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  };
  const R = srgb(rgb.r);
  const G = srgb(rgb.g);
  const B = srgb(rgb.b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function getReadableTextColor(base: string): string {
  const luminance = relativeLuminanceFromHex(base);
  return luminance > 0.55 ? "var(--text-on-accent)" : "var(--icon)";
}

/* ─────────────────────────────────────────────────────────────────────────────
   🗝️ SECTION: Persistent Session Logic
   These helpers let us store a temporary theme override in localStorage,
   lasting until midnight. This is useful for one-day theme changes that
   shouldn't persist forever.
   ───────────────────────────────────────────────────────────────────────────── */
const SESSION_KEY = "cfy.sessionTheme"
const SESSION_UNTIL = "cfy.sessionThemeUntil"

// Returns the timestamp for the next local midnight.
function nextLocalMidnight() {
  const d = new Date()
  d.setHours(24, 0, 0, 0)
  return d.getTime()
}

// Checks if there's a valid theme override for this session in storage.
function readSessionOverride(): Resolved | null {
  if (typeof window === "undefined") return null
  try {
    const untilRaw = window.localStorage.getItem(SESSION_UNTIL)
    if (!untilRaw) return null
    const until = Number(untilRaw)
    // If expired, remove and ignore.
    if (!Number.isFinite(until) || Date.now() > until) {
      window.localStorage.removeItem(SESSION_KEY)
      window.localStorage.removeItem(SESSION_UNTIL)
      return null
    }
    const v = window.localStorage.getItem(SESSION_KEY)
    return v === "dark" || v === "light" ? v : null
  } catch {
    return null
  }
}

// Writes a session theme override, or clears it if null.
function writeSessionOverride(v: Resolved | null) {
  if (typeof window === "undefined") return
  if (v == null) {
    window.localStorage.removeItem(SESSION_KEY)
    window.localStorage.removeItem(SESSION_UNTIL)
  } else {
    window.localStorage.setItem(SESSION_KEY, v)
    window.localStorage.setItem(SESSION_UNTIL, String(nextLocalMidnight()))
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   🎨 SECTION: AppShell Main Function
   This is the root shell for the app, handling theme, persistent state,
   background visuals, modular design tokens, and view routing.
   ───────────────────────────────────────────────────────────────────────────── */
export default function AppShell({
  startupLocked = false,
  startupOverlay = null,
}: AppShellProps) {
  const auth = useAuthState();
  const shellContentRef = React.useRef<HTMLDivElement | null>(null);
  const { lastEvent } = useLiveEvents();
  const runtimeHealth = useRuntimeHealth();
  const {
    ready: codexCapabilityReady,
    state: codexCapability,
  } = useRuntimeRouteCapability(SUPPORTED_PROFILE_ROUTE_LABELS.CODEX);
  const [guardianSurfaceEpoch, setGuardianSurfaceEpoch] = useState(0);
  const [sessionComposerBlocked, setSessionComposerBlocked] = useState<boolean>(
    () => SessionSpine.getRegisteredSpine()?.isComposerBlocked() ?? false
  );
  const lastCanceledCompletionIdRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    return SessionSpine.subscribeActiveSpine((spine) => {
      const activeCompletion = spine?.getActiveCompletion() ?? null;
      setSessionComposerBlocked(spine?.isComposerBlocked() ?? false);
      if (
        activeCompletion?.status === "canceled" &&
        activeCompletion.completionId !== lastCanceledCompletionIdRef.current
      ) {
        lastCanceledCompletionIdRef.current = activeCompletion.completionId;
        setGuardianSurfaceEpoch((previous) => previous + 1);
      }
    });
  }, []);

  React.useEffect(() => {
    if (!lastEvent) return;
    SessionSpine.getRegisteredSpine()?.consumeAcceptedLiveEvent(lastEvent);
  }, [lastEvent]);

  React.useEffect(() => {
    const requestInterceptorId = api.interceptors.request.use((config) => {
      const spine = SessionSpine.getRegisteredSpine();
      if (!spine) return config;

      const method = String(config?.method ?? "get").toLowerCase();
      if (method !== "post") return config;

      const pathname = normalizeInterceptPath(config?.url);
      const payload = parseRequestPayload(config?.data);
      const messageThreadId = extractMessageThreadId(pathname);

      if (isCreateMessagePath(pathname) || messageThreadId) {
        const submittedDraft = normalizeShellToken(payload.content);
        if (submittedDraft) {
          const draftTabId =
            normalizeShellToken(payload.draft_tab_id ?? payload.draftTabId) ??
            spine.findTabIdForThread(messageThreadId) ??
            spine.getActiveTabId();
          spine.rememberSubmittedDraft(submittedDraft, {
            tabId: draftTabId ?? undefined,
            threadId: messageThreadId,
          });
        }
      }

      const completionThreadId = extractCompletionThreadId(pathname);
      if (completionThreadId) {
        const tabId =
          spine.findTabIdForThread(completionThreadId) ?? spine.getActiveTabId();
        const turnId = normalizeShellToken(
          payload.turn_id ?? payload.turnId ?? (config as any)?.__cfyCompletionTurnId
        );
        spine.startCompletion({
          tabId: tabId ?? undefined,
          threadId: completionThreadId,
          turnId,
        });
      }

      const cancelTaskId = extractCancelTaskId(pathname);
      if (cancelTaskId) {
        spine.cancelActiveCompletion({ taskId: cancelTaskId });
      }

      return config;
    });

    const responseInterceptorId = api.interceptors.response.use(
      (response) => {
        const spine = SessionSpine.getRegisteredSpine();
        if (!spine) return response;

        const pathname = normalizeInterceptPath(response?.config?.url);
        const completionThreadId = extractCompletionThreadId(pathname);
        if (completionThreadId) {
          spine.attachCompletionIdentity({
            threadId: completionThreadId,
            taskId: normalizeShellToken(response?.data?.task_id ?? response?.data?.taskId),
            turnId: normalizeShellToken(
              response?.data?.turn_id ??
                response?.data?.turnId ??
                (response?.config as any)?.__cfyCompletionTurnId
            ),
          });
        }

        return response;
      },
      (error) => {
        const spine = SessionSpine.getRegisteredSpine();
        if (spine) {
          const pathname = normalizeInterceptPath(error?.config?.url);
          const completionThreadId = extractCompletionThreadId(pathname);
          if (completionThreadId) {
            spine.failActiveCompletion({
              threadId: completionThreadId,
              taskId: normalizeShellToken(
                error?.response?.data?.task_id ?? error?.response?.data?.taskId
              ),
              turnId: normalizeShellToken(
                error?.response?.data?.turn_id ??
                  error?.response?.data?.turnId ??
                  (error?.config as any)?.__cfyCompletionTurnId
              ),
              errorText: normalizeShellToken(
                error?.response?.data?.detail ??
                  error?.response?.data?.message ??
                  error?.message
              ),
            });
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.request.eject(requestInterceptorId);
      api.interceptors.response.eject(responseInterceptorId);
    };
  }, []);

  React.useEffect(() => {
    const node = shellContentRef.current as (HTMLDivElement & { inert?: boolean }) | null;
    if (!node) return;
    if (startupLocked) {
      node.setAttribute("inert", "");
      return;
    }
    node.removeAttribute("inert");
  }, [startupLocked]);
  // Surface continuation summaries as toasts (PCX_CONTINUE_002)
  React.useEffect(() => {
    const handler = (e: Event) => {
      try {
        const ce = e as CustomEvent;
        const summary = ce?.detail?.summary ?? ce?.detail?.stateSummary ?? "";
        window.dispatchEvent(new CustomEvent("cfy:toast", {
          detail: { message: summary, title: "🧭 New Child Thread", duration: 12000 }
        }));
      } catch {}
    };
    window.addEventListener("cfy:continuationToast", handler as any);
    return () => window.removeEventListener("cfy:continuationToast", handler as any);
  }, []);
  /* ─────────────────────────────────────────────────────────────────────────────
     🧠 Theme Mode Logic
     - `mode`: The user's chosen theme mode (light, dark, or system)
     - `systemPrefersDark`: Tracks the OS-level dark mode preference
     - `sessionOverride`: A one-day override for the theme
     We keep all three in sync and resolve to either "light" or "dark" for rendering.
     ───────────────────────────────────────────────────────────────────────────── */
  const [mode, setMode] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const raw = window.localStorage.getItem("cfy.themeMode");
    return coerceMode(raw);
  });
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [sessionOverride, setSessionOverride] = useState<Resolved | null>(() => readSessionOverride());

  /* ─────────────────────────────────────────────────────────────────────────────
     🧠 Layout Mode State (Focus vs Zen)
     - `layoutMode`: Controls page padding via --page-pad CSS variable
     - Persists to localStorage for seamless user experience
     ───────────────────────────────────────────────────────────────────────────── */
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() => {
    if (typeof window === "undefined") return "focus";
    const raw = window.localStorage.getItem("cfy.layoutMode");
    return raw === "zen" ? "zen" : "focus";
  });

  // Persist layoutMode to localStorage when it changes
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cfy.layoutMode", layoutMode);
  }, [layoutMode]);

  // Listen for OS-level theme changes and storage updates
  useEffect(() => {
    if (typeof window === "undefined") return
    const mm = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => setSystemPrefersDark(mm.matches)
    if (mm.addEventListener) mm.addEventListener("change", handler)
    else mm.addListener(handler)
    return () => {
      if (mm.removeEventListener) mm.removeEventListener("change", handler)
      else mm.removeListener(handler)
    }
  }, [])
  useEffect(() => {
    if (typeof window === "undefined") return
    // Handle theme/session changes from other tabs/windows
    const onStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEY || e.key === SESSION_UNTIL) setSessionOverride(readSessionOverride())
      if (e.key === "cfy.themeMode") setMode(coerceMode(window.localStorage.getItem("cfy.themeMode")))
    }
    window.addEventListener("storage", onStorage)
    // Periodically check if the session override expired
    const t = window.setInterval(() => setSessionOverride(readSessionOverride()), 60_000)
    return () => {
      window.removeEventListener("storage", onStorage)
      window.clearInterval(t)
    }
  }, [])

  // Decide the final theme mode for this session
  const resolved: Resolved = useMemo(() => {
    if (sessionOverride) return sessionOverride;
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return systemPrefersDark ? "dark" : "light";
  }, [mode, systemPrefersDark, sessionOverride]);

  // Actually apply the theme class to the <html> element
  useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.classList.toggle("dark", resolved === "dark")
  }, [resolved])

  // Save user theme mode to localStorage when changed
  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem("cfy.themeMode", mode)
  }, [mode])

  /* ─────────────────────────────────────────────────────────────────────────────
     🗂️ Persistent User and App State
     These state variables track user names, role, notes, and system prompt.
     We sync them with localStorage so they persist across reloads.
     ───────────────────────────────────────────────────────────────────────────── */
  const [guardianName, setGuardianName] = useState<string>(() => (typeof window === "undefined" ? "Guardian" : localStorage.getItem("cfy.assistantName") || "Guardian"));
  const [userName, setUserName] = useState<string>(() => (typeof window === "undefined" ? "You" : localStorage.getItem("cfy.userName") || "You"));
  const [role, setRole] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.role") || ""));
  const [notes, setNotes] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.notes") || ""));
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.assistantName", guardianName); }, [guardianName]);
  const [systemPrompt, setSystemPrompt] = useState<string>(() => (typeof window === "undefined" ? "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity." : localStorage.getItem("cfy.systemPrompt") || "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity."));
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.userName", userName);
      localStorage.setItem("cfy.role", role);
      localStorage.setItem("cfy.notes", notes);
      localStorage.setItem("cfy.systemPrompt", systemPrompt);
    }
  }, [userName, role, notes, systemPrompt]);

  /* ─────────────────────────────────────────────────────────────────────────────
     🚦 SECTION: View Routing and UI Rendering
     - `view`: Tracks which main screen (dashboard, documents, etc.) is active.
     - `workspaceOpen`: Controls visibility of the workspace sidebar/pane.
     - `wallpaper`: Optional image for the background.
     - We persist the last view and wallpaper for a seamless return experience.
     ───────────────────────────────────────────────────────────────────────────── */
  const [view, setView] = useState<AppShellView>(() => {
    if (typeof window !== "undefined") {
      const routeView = resolveViewFromPathname(window.location.pathname);
      if (routeView) return routeView;

      const storedView = window.localStorage.getItem("cfy.lastView");
      if (isAppShellView(storedView)) {
        return storedView;
      }
    }

    return "dashboard";
  });
  const workspaceShellEnabled = isWorkspaceShellView(view);
  const workspaceRouteContext: WorkspaceShellView = workspaceShellEnabled
    ? view
    : "dashboard";
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [projectModalSaving, setProjectModalSaving] = useState(false);
  const [projectModalName, setProjectModalName] = useState("");
  const [projectModalIcon, setProjectModalIcon] = useState("📁");
  const [projectModalError, setProjectModalError] = useState<string | null>(null);

  const openCreateProjectModal = React.useCallback(() => {
    setProjectModalError(null);
    setProjectModalName("");
    setProjectModalIcon("📁");
    setProjectModalOpen(true);
  }, []);

  const closeCreateProjectModal = React.useCallback(() => {
    if (projectModalSaving) return;
    setProjectModalOpen(false);
  }, [projectModalSaving]);

  React.useEffect(() => {
    if (!projectModalOpen) {
      setProjectModalName("");
      setProjectModalIcon("📁");
      setProjectModalError(null);
    }
  }, [projectModalOpen]);

  React.useEffect(() => {
    if (projectModalOpen && view !== "dashboard") {
      setProjectModalOpen(false);
    }
  }, [view, projectModalOpen]);

  const handleProjectSubmit = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedName = projectModalName.trim();
      if (!trimmedName) {
        setProjectModalError("Project name is required.");
        return;
      }
      setProjectModalSaving(true);
      setProjectModalError(null);
      const iconValue = projectModalIcon.trim() || "📁";
      try {
        const response = await createProjectApi({
          name: trimmedName,
          icon: iconValue,
        });
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:projects:refresh", {
              detail: {
                id: response?.data?.id ?? response?.data?.project_id ?? null,
                name: trimmedName,
                icon: iconValue,
              },
            })
          );
        } catch {
          // Ignore DOM errors for non-browser environments
        }
        setProjectModalOpen(false);
      } catch (err: any) {
        const message =
          err?.response?.data?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to create project.";
        setProjectModalError(message);
      } finally {
        setProjectModalSaving(false);
      }
    },
    [projectModalIcon, projectModalName]
  );
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view); }, [view]);
  // Sync the main view with the browser URL so direct links and back/forward
  // navigation keep the shell view in lockstep with the pathname.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncRouteState = () => {
      setActiveRouteThreadId(readRouteThreadId());
      const routeView = resolveViewFromPathname(window.location.pathname);
      if (routeView) {
        setView(routeView);
      }
    };

    syncRouteState();
    window.addEventListener("popstate", syncRouteState);
    window.addEventListener("cfy:threads:refresh", syncRouteState as EventListener);
    return () => {
      window.removeEventListener("popstate", syncRouteState);
      window.removeEventListener("cfy:threads:refresh", syncRouteState as EventListener);
    };
  }, []);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop" : localStorage.getItem("cfy.wallpaper")));

  /* ─────────────────────────────────────────────────────────────────────────────
     📄 SECTION: Document and Gallery State
     - `documents`: List of available document items, with types and colors.
     - `gallery`: List of images for the gallery view.
     - `activeDoc`: Which document is open in the workspace.
     - Workspace open/close state now flows through the shared invocation hook.
     ───────────────────────────────────────────────────────────────────────────── */
  const defaultDocs: DocItem[] = [
    normalizeDoc({ id: "mock-covenant", name: "Covenant", ext: "pdf", mock: true }),
    normalizeDoc({ id: "mock-roadmap", name: "Roadmap", ext: "md", mock: true }),
    normalizeDoc({ id: "mock-vision", name: "Vision", ext: "txt", mock: true }),
    normalizeDoc({ id: "mock-design", name: "Design", ext: "sketch", mock: true }),
  ];
  const readCachedDocuments = (): DocItem[] | null => {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem("cfy.documents");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return null;
      return parsed.map((d: any, idx: number) => normalizeDoc(d, idx)) as DocItem[];
    } catch {
      return null;
    }
  };
  const [documents, setDocuments] = useState<DocItem[]>(() => {
    const cached = readCachedDocuments();
    if (cached) return cached;
    return typeof window === "undefined" ? defaultDocs : defaultDocs;
  });
  const [activeRouteThreadId, setActiveRouteThreadId] = useState<number | null>(
    () => readRouteThreadId()
  );
  const [generalProjectId, setGeneralProjectId] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem("cfy.generalProjectId");
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  });
  const hasFetchedGeneralProjectRef = React.useRef(false);
  const [activeThreadProjectId, setActiveThreadProjectId] = useState<number | null>(null);
  const [documentScope, setDocumentScope] = useState<DocumentScope>(
    () => (readRouteThreadId() != null ? "thread" : "project")
  );
  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const syncRouteThread = () => {
      setActiveRouteThreadId(readRouteThreadId());
    };
    syncRouteThread();
    window.addEventListener("popstate", syncRouteThread);
    window.addEventListener("cfy:threads:refresh", syncRouteThread as EventListener);
    return () => {
      window.removeEventListener("popstate", syncRouteThread);
      window.removeEventListener(
        "cfy:threads:refresh",
        syncRouteThread as EventListener
      );
    };
  }, []);
  useEffect(() => {
    setDocumentScope(activeRouteThreadId != null ? "thread" : "project");
  }, [activeRouteThreadId]);
  const navigateToView = useCallback(
    (nextView: AppShellView) => {
      setView(nextView);
      if (typeof window === "undefined") return;

      const nextPath = resolvePathForView(nextView, activeRouteThreadId);
      if (window.location.pathname !== nextPath) {
        window.history.pushState({}, "", nextPath);
      }
      window.dispatchEvent(new PopStateEvent("popstate"));
    },
    [activeRouteThreadId]
  );
  const openSettings = useCallback(() => navigateToView("settings"), [navigateToView]);
  const [documentsSource, setDocumentsSource] = useState<"default" | "cache" | "backend">(() => {
    if (typeof window === "undefined") return "default";
    return readCachedDocuments() ? "cache" : "default";
  });
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (documentsSource === "default") return;
    const cacheable = documents.filter((d) => !d.mock);
    try {
      localStorage.setItem("cfy.documents", JSON.stringify(cacheable));
    } catch {}
  }, [documents, documentsSource]);
  useEffect(() => {
    if (typeof window === "undefined" || generalProjectId == null) return;
    try {
      window.localStorage.setItem("cfy.generalProjectId", String(generalProjectId));
      window.localStorage.setItem("cfy.defaultProjectId", String(generalProjectId));
    } catch {}
  }, [generalProjectId]);

  useEffect(() => {
    let cancelled = false;
    if (startupLocked) {
      return () => {
        cancelled = true;
      };
    }
    if (generalProjectId != null) {
      return () => {
        cancelled = true;
      };
    }
    if (hasFetchedGeneralProjectRef.current) {
      return () => {
        cancelled = true;
      };
    }
    if (!checkAuthGate(auth, "projects list load")) {
      return () => {
        cancelled = true;
      };
    }
    hasFetchedGeneralProjectRef.current = true;
    (async () => {
      try {
        const response = await api.get("/api/projects");
        if (cancelled) return;
        const payload = response?.data ?? response;
        const list = Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.projects)
          ? payload.projects
          : [];
        const defaultProject = findDefaultProjectId(list);
        if (defaultProject != null) {
          setGeneralProjectId(defaultProject);
        }
      } catch (err) {
        if (cancelled) return;
        console.warn("[projects] failed to resolve default project", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth, generalProjectId, startupLocked]);
  useEffect(() => {
    let cancelled = false;
    if (startupLocked) {
      setActiveThreadProjectId(null);
      return () => {
        cancelled = true;
      };
    }
    if (!activeRouteThreadId) {
      setActiveThreadProjectId(null);
      return () => {
        cancelled = true;
      };
    }
    if (!checkAuthGate(auth, "thread project load")) {
      setActiveThreadProjectId(null);
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const response = await api.get("/chat/threads");
        const payload = response?.data ?? response;
        const threads = Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.threads)
          ? payload.threads
          : [];
        const hit = threads.find(
          (thread: any) => Number(thread?.id) === activeRouteThreadId
        );
        const projectRaw = hit?.project_id ?? hit?.projectId ?? null;
        const parsed = Number(projectRaw);
        if (cancelled) return;
        setActiveThreadProjectId(Number.isFinite(parsed) ? parsed : null);
      } catch (err) {
        if (cancelled) return;
        setActiveThreadProjectId(null);
        console.warn("[documents] failed to resolve thread project", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeRouteThreadId, auth, startupLocked]);
  const effectiveDocumentsProjectId = useMemo<number | null>(
    () => activeThreadProjectId ?? generalProjectId,
    [activeThreadProjectId, generalProjectId]
  );
  useEffect(() => {
    let cancelled = false;
    if (startupLocked) {
      return () => {
        cancelled = true;
      };
    }
    if (!checkAuthGate(auth, "documents list load")) {
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const params: Record<string, number> = { limit: 100 };
        if (effectiveDocumentsProjectId != null) {
          params.project_id = effectiveDocumentsProjectId;
        }
        const res = await api.get("/media/documents", { params });
        const docs = unwrapDocumentArray(res?.data);
        if (cancelled) return;
        const normalized = dedupeDocItems(
          docs.map((d: any, idx: number) => normalizeDoc(d, idx))
        );
        setDocuments(normalized);
        setDocumentsSource("backend");
      } catch (err) {
        if (cancelled) return;
        console.warn("[documents] failed to load backend documents", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth, effectiveDocumentsProjectId, startupLocked]);
  const [codexEntries, setCodexEntries] = useState<CodexEntrySummary[]>([]);
  useEffect(() => {
    let cancelled = false;
    if (startupLocked) {
      return () => {
        cancelled = true;
      };
    }
    if (!codexCapabilityReady) {
      return () => {
        cancelled = true;
      };
    }
    if (codexCapability === "unavailable") {
      setCodexEntries([]);
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const entries = await listCodexEntries();
        if (!cancelled) setCodexEntries(entries);
      } catch (err) {
        console.warn("[codex] failed to load entries", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [codexCapability, codexCapabilityReady, startupLocked]);
  const codexDocs = useMemo<DocItem[]>(() => {
    if (!Array.isArray(codexEntries)) return [];
    return codexEntries.map((e, idx) => ({
      id: e?.id || `codex-${idx}`,
      name: e?.title || "Untitled Codex Entry",
      title: e?.title || "Untitled Codex Entry",
      ext: ((e?.ext || "codex") as keyof ExtColors),
      type: "codex_entry" as const,
      createdAt: e?.created_at,
      mock: false,
    }));
  }, [codexEntries]);
  const scopedProjectDocuments = useMemo<DocItem[]>(() => {
    if (documentScope !== "thread" || activeRouteThreadId == null) {
      return documents;
    }
    return documents.filter((doc) => {
      const threadRaw = (doc as any).threadId ?? (doc as any).thread_id;
      const threadValue = Number(threadRaw);
      return Number.isFinite(threadValue) && threadValue === activeRouteThreadId;
    });
  }, [activeRouteThreadId, documents, documentScope]);
  const allDocuments = useMemo<DocItem[]>(
    () => dedupeDocItems([...codexDocs, ...scopedProjectDocuments]),
    [codexDocs, scopedProjectDocuments]
  );
  const [baseColor, setBaseColor] = useState<string>(() => (typeof window === "undefined" ? "#6B7280" : localStorage.getItem("cfy.baseColor") || "#6B7280"));
  // Utility: parse a number from unknown input, fall back & clamp to [0,1]
  function safeNumber(val: unknown, fallback: number): number {
    const n = Number(val);
    return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : fallback;
  }
  const [depth, setDepth] = useState<number>(() => {
    if (typeof window === "undefined") return 0.6;
    return safeNumber(localStorage.getItem("cfy.depth"), 0.6);
  });
  const [fade, setFade] = useState<number>(() => {
    if (typeof window === "undefined") return 0.4;
    return safeNumber(localStorage.getItem("cfy.fade"), 0.4);
  });
  const [dashboardThreadRows, setDashboardThreadRows] = useState<number>(() => {
    if (typeof window === "undefined") return 2;
    const raw = Number(window.localStorage.getItem("cfy.dashboard.threadRows"));
    if (!Number.isFinite(raw)) return 2;
    return Math.max(1, Math.min(4, Math.round(raw)));
  });
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.baseColor", baseColor);
      localStorage.setItem("cfy.depth", String(depth));
      localStorage.setItem("cfy.fade", String(fade));
    }
  }, [baseColor, depth, fade]);
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("cfy.dashboard.threadRows", String(dashboardThreadRows));
    }
  }, [dashboardThreadRows]);

  /* ─────────────────────────────────────────────────────────────────────────────
     🌈 SECTION: Color Helpers and Gradient Generators
     These little functions help convert between color formats and generate
     lightened/darkened versions for backgrounds and gradients.
     ───────────────────────────────────────────────────────────────────────────── */
  function hexToRgb(hex: string) {
    const n = hex.replace("#", "");
    const v = n.length === 3 ? n.split("").map((c) => c + c).join("") : n;
    const num = parseInt(v, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }
  function rgbToHsl(r: number, g: number, b: number) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0; const l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }
    return { h: h * 360, s: s * 100, l: l * 100 };
  }
  function hslToHex(h: number, s: number, l: number) {
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    let r = 0, g = 0, b = 0;
    if (0 <= h && h < 60) { r = c; g = x; }
    else if (60 <= h && h < 120) { r = x; g = c; }
    else if (120 <= h && h < 180) { g = c; b = x; }
    else if (180 <= h && h < 240) { g = x; b = c; }
    else if (240 <= h && h < 300) { r = x; b = c; }
    else { r = c; b = x; }
    const to255 = (v: number) => Math.round((v + m) * 255);
    const out = (n: number) => n.toString(16).padStart(2, "0");
    return `#${out(to255(r))}${out(to255(g))}${out(to255(b))}`;
  }
  function lighten(hex: string, amount: number) {
    const { r, g, b } = hexToRgb(hex);
    const { h, s, l } = rgbToHsl(r, g, b);
    const nl = Math.min(100, l + amount * 100);
    return hslToHex(h, s, nl);
  }
  function darken(hex: string, amount: number) {
    const { r, g, b } = hexToRgb(hex);
    const { h, s, l } = rgbToHsl(r, g, b);
    const nl = Math.max(0, l - amount * 100);
    return hslToHex(h, s, nl);
  }

  /* ─────────────────────────────────────────────────────────────────────────────
     🖼️ SECTION: App-wide Visual Background Handling
     - If no wallpaper is set, we use a smooth color gradient based on the base color.
     - If wallpaper is set, we overlay a subtle gradient to help the theme (light/dark)
       be visually obvious, regardless of the wallpaper image.
     ───────────────────────────────────────────────────────────────────────────── */
  const accent = baseColor;
  const accentWeak = baseColor;
  const accentStrong = baseColor;
  const accentContrast = getReadableTextColor(accentStrong);
  const bgStyleNoWallpaper = (() => {
    const start = lighten(baseColor, fade * 0.6);
    const end = darken(baseColor, depth * 0.8);
    return { background: `linear-gradient(to bottom, ${start}, ${end})` } as React.CSSProperties;
  })();
  const backgroundStyle: React.CSSProperties = (() => {
    if (!wallpaper) return bgStyleNoWallpaper;
    // Overlay gradient with alpha to bias the scene per theme
    const clamp = (n: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, n));
    const f = clamp(fade);
    const d = clamp(depth);
    let start = "rgba(255,255,255,0.0)";
    let end = "rgba(255,255,255,0.0)";
    if (resolved === "dark") {
      // dark: emphasize depth (heavier overlay), minimal fade
      start = `rgba(0,0,0,${(d * 0.7).toFixed(3)})`;
      end = `rgba(0,0,0,${(f * 0.35).toFixed(3)})`;
    } else {
      // light: emphasize fade (brighter wash), low depth
      start = `rgba(255,255,255,${(f * 0.5).toFixed(3)})`;
      end = `rgba(255,255,255,${(d * 0.25).toFixed(3)})`;
    }
    return {
      backgroundImage: `linear-gradient(135deg, ${start}, ${end}), url(${wallpaper})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
    } as React.CSSProperties;
  })();
  const panelSheet = resolved === "dark" ? "#1b1b1d" : "#f1ede8";
  const panelBg = panelSheet;
  const chipBg = resolved === "dark" ? "#262629" : "#e9e4dc";
  // Global: soften panel border
  const panelBorder = resolved === "dark" ? "rgba(255,255,255,0.10)" : "rgba(17,24,39,0.08)";
  const panelSheetBorder = resolved === "dark" ? "rgba(255,255,255,0.18)" : "rgba(17,24,39,0.14)";
  const textColor = resolved === "dark" ? "#ffffff" : "#111827";
  const mutedColor = resolved === "dark" ? "rgba(255,255,255,0.88)" : "#374151";
  const subtleTextColor =
    resolved === "dark" ? "rgba(255,255,255,0.72)" : "#6b7280";
  const iconMutedColor =
    resolved === "dark" ? "rgba(255,255,255,0.76)" : "#4b5563";
  const surfaceHover =
    resolved === "dark" ? "rgba(255,255,255,0.08)" : "rgba(17,24,39,0.06)";
  const surfaceSoft =
    resolved === "dark" ? "rgba(255,255,255,0.04)" : "rgba(17,24,39,0.04)";
  const chipBorder =
    resolved === "dark" ? "rgba(255,255,255,0.16)" : "rgba(17,24,39,0.10)";
  const textOnAccent = resolved === "dark" ? "#f9fafb" : "#111827";
  const infoSurface =
    resolved === "dark" ? "rgba(96,165,250,0.18)" : "#dbeafe";
  const infoText = resolved === "dark" ? "#bfdbfe" : "#1d4ed8";
  const tagSurface =
    resolved === "dark" ? "rgba(192,132,252,0.18)" : "#f3e8ff";
  const tagText = resolved === "dark" ? "#e9d5ff" : "#7e22ce";
  const dangerSurface =
    resolved === "dark" ? "rgba(248,113,113,0.16)" : "#fef2f2";
  const dangerBorder =
    resolved === "dark" ? "rgba(248,113,113,0.32)" : "#fecaca";
  const dangerText = resolved === "dark" ? "#fecaca" : "#991b1b";
  // Local-only: translucent bezel for Dashboard cards
  const panelBezel = resolved === "dark" ? "rgba(255,255,255,0.14)" : "rgba(17,24,39,0.12)";
  const panelBorderStrong = resolved === "dark" ? "rgba(255,255,255,0.22)" : "rgba(17,24,39,0.16)";
  const shellViewportProfile = useShellViewportProfile();
  const mobileShellProfile = useMemo(
    () => getMobileShellProfile(shellViewportProfile),
    [shellViewportProfile]
  );
  const isPhoneShell = mobileShellProfile.active;
  const viewportInsets = useViewportInsets(isPhoneShell);
  const mobileTopNavDockStyle = useMemo<React.CSSProperties>(
    () => getMobileTopNavDockStyle(mobileShellProfile),
    [mobileShellProfile]
  );
  const mobileTopNavRailStyle = useMemo<React.CSSProperties>(
    () => getMobileTopNavRailStyle(mobileShellProfile),
    [mobileShellProfile]
  );

  /* ─────────────────────────────────────────────────────────────────────────────
     🏗️ SECTION: Modular Design Token Setup
     All main layout, color, and sizing tokens are set here, so the UI can
     consistently use them for spacing, shapes, and color across views.
     ───────────────────────────────────────────────────────────────────────────── */
  const styleVars = {
    /* === GENERAL LAYOUT TOKENS === */
    "--radius-micro": "8px",                 // chips, inputs, pills
    "--radius-tile": "20px",                  // cards, tiles, panels
    "--card-radius": "20px",    // pointer used by components (explicit for clarity)
    "--shell-viewport-height": `${viewportInsets.visualViewportHeight}px`,
    "--shell-layout-viewport-height": `${viewportInsets.layoutViewportHeight}px`,
    "--shell-keyboard-inset": `${viewportInsets.keyboardInset}px`,
    "--edge-chrome": shellViewportProfile.shellEdgeChrome,                     // Outer padding (PWA safe zone)
    "--shell-gap": shellViewportProfile.shellGap,                      // Gap between cards or columns
    "--pill-pad-y": isPhoneShell ? shellViewportProfile.shellCardPad : "11px", // Vertical padding for the navigation pill dock (controls thickness)
    "--viewport-radius": shellViewportProfile.viewportRadius,                // Rounding for main window
    "--tile-radius": "var(--radius-tile)",      // Default internal card rounding
    "--page-gutter-top": shellViewportProfile.shellPageGutterTop,                // Fixed gutter under the pill dock
    "--page-pad": shellViewportProfile.viewportClass === "desktop" ? (layoutMode === "zen" ? "48px" : "0px") : "0px",  // Layout mode: zen (12px) or focus (0px)
    /* === CARD GEOMETRY === */
    "--card-pad": shellViewportProfile.shellCardPad,                       // Internal card padding
    "--frame": "3px",                         // Outer frame thickness
    // --bezel: Visual margin between the refractive glass and the opaque content surface.
    // Changing this variable tunes the glass thickness everywhere.
    "--bezel": "var(--bezel, 6px)",             // Bezel (margin) between glass and content (default 6px)
    "--rim": "3px",                           // Inner rim spacing

    /* === TILE / CHIP / ELEMENT SIZING === */
    "--project-tile-size": "72px",              // Project tile square size
    "--doc-chip-height": "48px",                // Height of document chips
    "--image-tile-size": "180px",               // Square preview image size

    /* === GRID CONTROL === */
    "--image-grid-gap": "var(--shell-gap)",     // Gap between images
    "--image-grid-cols": "auto-fit",            // Can be set to fixed or responsive

    /* === DIMENSION CONSTRAINTS === */
    "--min-h": shellViewportProfile.contentMinHeight,    // Viewport vertical floor
    "--card-height": shellViewportProfile.viewportClass === "desktop" ? "clamp(480px, 70vh, 800px)" : "auto", // Centralized card height

    /* === COLORS & SURFACE === */
    "--panel-bg": panelBg,
    "--panel-sheet": panelSheet,
    "--panel-sheet-border": panelSheetBorder,
    "--panel-border-strong": panelBorderStrong,
    "--chip-bg": chipBg,
    "--chip-border": chipBorder,
    "--panel-border": panelBorder,
    "--panel-bezel": panelBezel,
    "--text": textColor,
    "--muted": mutedColor,
    "--text-subtle": subtleTextColor,
    "--icon": textColor,
    "--icon-muted": iconMutedColor,
    "--surface-hover": surfaceHover,
    "--surface-soft": surfaceSoft,
    "--text-on-accent": textOnAccent,
    "--info-surface": infoSurface,
    "--info-text": infoText,
    "--tag-surface": tagSurface,
    "--tag-text": tagText,
    "--danger-surface": dangerSurface,
    "--danger-border": dangerBorder,
    "--danger-text": dangerText,
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,
    "--pill-active-text": accentContrast,

    /* === SEMANTIC FALLBACKS (legacy) === */
    "--radius": "var(--tile-radius)",           // Used in old components
    "--board-edge": "var(--edge-chrome)",       // Used in spacing wrappers
    "--gutter": "var(--shell-gap)",             // Used in layout
    // --bezel is also set at the main viewport for live tuning of glass thickness
  } as React.CSSProperties;


  /* ─────────────────────────────────────────────────────────────────────────────
     🎨 SECTION: Extension Colors and Gallery Defaults
     - We provide default colors for file extensions and allow user overrides.
     - Gallery images are seeded with a few examples but can be customized.
     ───────────────────────────────────────────────────────────────────────────── */
  const DEFAULT_EXT_COLORS: ExtColors = {
    pdf:   "#E23B3B", // red
    doc:   "#0EA5E9", // cyan-blue
    md:    "#6B7280", // slate gray
    png:   "#06B6D4", // teal
    sketch:"#F59E0B", // amber
    txt:   "#8B5CF6", // violet
    docx:  "#2563EB", // blue
    jpeg:  "#D946EF", // fuchsia
    codex: "#22C55E", // green for Codex entries
  };
  const [extColors, setExtColors] = useState<ExtColors>(() => {
    // Merge any saved colors with explicit defaults, so new keys get sensible values
    if (typeof window === "undefined") return DEFAULT_EXT_COLORS;
    try {
      const raw = localStorage.getItem("cfy.extColors");
      const saved = raw ? JSON.parse(raw) : {};
      return { ...DEFAULT_EXT_COLORS, ...saved } as ExtColors;
    } catch {
      return DEFAULT_EXT_COLORS;
    }
  });
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.extColors", JSON.stringify(extColors)); }, [extColors]);
  const [gallery, setGallery] = useState<GalleryItem[]>(() => {
    const def: GalleryItem[] = [
      { src: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop", prompt: "vibrant color gradient, smooth texture, abstract art, minimalist, 4k", mock: true },
      { src: "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=600&auto=format&fit=crop", prompt: "dramatic light, deep shadows, cinematic, moody, purple and blue tones", mock: true },
      { src: "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?q=80&w=600&auto=format&fit=crop", prompt: "ethereal smoke, liquid metal, iridescent, holographic, studio lighting, 8k", mock: true },
      { src: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=600&auto=format&fit=crop", prompt: "soft gradient, warm horizon fade, subtle grain, minimal", mock: true },
    ];
    if (typeof window === "undefined") return def;
    try {
      const raw = localStorage.getItem("cfy.gallery");
      if (!raw) {
        localStorage.setItem("cfy.gallery", JSON.stringify(def));
        return def;
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return def;
      return parsed
        .map((item) => normalizeGalleryItem(item))
        .filter((item): item is GalleryItem => !!item);
    } catch { return def; }
  });
  useEffect(() => {
    if (typeof window === "undefined") return;
    // Keep a compact copy in storage; trim on quota errors to avoid crashes when large data URLs are present.
    const compact = (gallery || []).filter((g) => g && g.src).slice(0, 200);
    try {
      localStorage.setItem("cfy.gallery", JSON.stringify(compact));
    } catch (err) {
      console.warn("[gallery] failed to persist gallery; trimming cache", err);
      try {
        localStorage.setItem("cfy.gallery", JSON.stringify(compact.slice(0, 50)));
      } catch {}
    }
  }, [gallery]);

  // Ingestion API toggle (Labs)
  const [ingestionEnabled, setIngestionEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("cfy.ingest.enabled") === "true";
  });
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.ingest.enabled", String(ingestionEnabled));
    }
  }, [ingestionEnabled]);

  // Clear mocks when any user upload occurs (e.g., wallpaper) or flag set
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hasUpload = !!localStorage.getItem("cfy.hasUserUpload");
    if (hasUpload || !!wallpaper) {
      const filteredGallery = gallery.filter((g) => !g.mock);
      if (filteredGallery.length !== gallery.length) setGallery(filteredGallery);
      const filteredDocs = documents.filter((d) => !d.mock);
      if (filteredDocs.length !== documents.length) setDocuments(filteredDocs);
    }
  }, [wallpaper]);

  // Listen for upload flag updates from other tabs
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "cfy.hasUserUpload" && e.newValue) {
        const filteredGallery = gallery.filter((g) => !g.mock);
        if (filteredGallery.length !== gallery.length) setGallery(filteredGallery);
        const filteredDocs = documents.filter((d) => !d.mock);
        if (filteredDocs.length !== documents.length) setDocuments(filteredDocs);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [gallery, documents]);

  const deleteDocument = useCallback((doc: DocumentLike) => {
    if (doc.type === "codex_entry") return;
    const keepDoc = (d: DocItem) =>
      d.type === "codex_entry" ||
      (d.id !== doc.id && !(d.title === doc.title && d.ext === doc.ext));
    setDocuments((prev) => prev.filter(keepDoc));
  }, []);
  const deleteGalleryItem = useCallback((src: string) => {
    const targetSrc = normalizeGallerySrc(src);
    if (!targetSrc) return;
    setGallery((prev) =>
      prev.filter((g) => normalizeGallerySrc(g.src) !== targetSrc)
    );
  }, []);

  // Provide delete undo for documents
  useEffect(() => {
    const onDel = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const doc = detail.doc ? normalizeDoc(detail.doc) : null;
      if (!doc) return;
      const removed = documents.find(
        (x) =>
          x.id === doc.id ||
          ((x.title === doc.title || x.name === doc.name) && x.ext === doc.ext)
      );
      if (!removed) return;
      try {
        window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: "Document deleted", actionLabel: "Undo", onAction: () => {
          setDocuments((prev) => [removed, ...prev]);
        }}}));
      } catch {}
    };
    window.addEventListener("cfy:documents:delete", onDel as EventListener);
    return () => window.removeEventListener("cfy:documents:delete", onDel as EventListener);
  }, [documents]);

  // Hook documents add from DocumentsView uploader
  useEffect(() => {
    const onAdd = (e: Event) => {
      const items = (e as CustomEvent).detail?.items || [];
      if (!Array.isArray(items) || items.length === 0) return;
      setDocumentsSource((prev) => (prev === "default" ? "cache" : prev));
      setDocuments((prev) =>
        dedupeDocItems([
          ...items.map((item: any, idx: number) => normalizeDoc(item, idx)),
          ...prev,
        ])
      );
    };
    window.addEventListener("cfy:documents:add", onAdd as EventListener);
    return () => window.removeEventListener("cfy:documents:add", onAdd as EventListener);
  }, []);

  // Hook gallery add from chat/uploader
  useEffect(() => {
    const onAdd = (e: Event) => {
      const items = (e as CustomEvent).detail?.items || [];
      if (!Array.isArray(items) || items.length === 0) return;
      const normalizedItems = items
        .map((item: any) => normalizeGalleryItem(item))
        .filter((item): item is GalleryItem => !!item);
      if (normalizedItems.length === 0) return;
      setGallery((prev) => {
        const seen = new Set<string>();
        const merged = [...normalizedItems, ...prev].filter((g: any) => {
          const key = g?.src || g?.id;
          if (!key) return false;
          const sk = String(key);
          if (seen.has(sk)) return false;
          seen.add(sk);
          return true;
        });
        return merged;
      });
    };
    window.addEventListener("cfy:gallery:add", onAdd as EventListener);
    return () => window.removeEventListener("cfy:gallery:add", onAdd as EventListener);
  }, []);

  // Gallery uploader
  const galleryUploader = useUploader({
    tag: "upload",
    projectId: generalProjectId ?? undefined,
    onImages: (items) =>
      setGallery((prev) => {
        const normalizedItems = items
          .map((item: any) => normalizeGalleryItem(item))
          .filter((item): item is GalleryItem => !!item);
        if (normalizedItems.length === 0) return prev;
        const seen = new Set<string>();
        const merged = [...normalizedItems, ...prev].filter((g: any) => {
          const key = g?.src || g?.id;
          if (!key) return false;
          const sk = String(key);
          if (seen.has(sk)) return false;
          seen.add(sk);
          return true;
        });
        return merged;
      }),
    onDocuments: (items) =>
      setDocuments((prev) => [
        ...(items || []).map((item: any, idx: number) => normalizeDoc(item, idx)),
        ...prev,
      ]),
    onAnyUpload: () => {},
  });
  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  const [pendingComposerDocumentTiles, setPendingComposerDocumentTiles] = useState<
    DocumentContextTile[]
  >([]);
  const {
    isOpen: workspaceDrawerOpen,
    activeTab: workspaceDrawerTab,
    setActiveTab: setWorkspaceDrawerTab,
    open: openWorkspaceDrawer,
    close: closeWorkspaceDrawerUi,
  } = useWorkspaceUiState({
    routeContext: workspaceRouteContext,
  });
  const {
    paneRatio: workspacePaneRatio,
    minPaneRatio: minWorkspacePaneRatio,
    maxPaneRatio: maxWorkspacePaneRatio,
    primaryPaneRatio,
    workspacePaneBasis,
    primaryPaneBasis,
    primaryPaneMinWidth,
    workspacePaneMinWidth,
    layoutMode: workspaceLayoutMode,
    isWorkspaceDominant,
    ratioBucket: workspaceRatioBucket,
    setLayoutMode: setWorkspaceLayoutMode,
  } = useWorkspaceLayoutMode({
    isOpen: workspaceDrawerOpen,
    activeThreadId: activeRouteThreadId,
  });
  const handleWorkspaceDrawerTabChange = useCallback(
    (tab: WorkspaceDrawerTab) => {
      setWorkspaceDrawerTab(tab);
    },
    [setWorkspaceDrawerTab]
  );
  const handleWorkspaceOpenRequest = useCallback(
    (request: WorkspaceOpenRequest) => {
      const doc = normalizeDoc(request.doc);
      setDocumentsSource((prev) => (prev === "default" ? "cache" : prev));
      setDocuments((prev) => dedupeDocItems([doc, ...prev]));
      navigateToView(request.targetView === "guardian" ? "guardian" : "documents");
      if (
        mobileShellProfile.workspace.autoOpenOnDocumentRequest ||
        workspaceDrawerOpen
      ) {
        openWorkspaceDrawer("inspector");
        return;
      }
      setWorkspaceDrawerTab("inspector");
      closeWorkspaceDrawerUi();
    },
    [
      closeWorkspaceDrawerUi,
      mobileShellProfile.workspace.autoOpenOnDocumentRequest,
      navigateToView,
      openWorkspaceDrawer,
      setWorkspaceDrawerTab,
      workspaceDrawerOpen,
    ]
  );
  const { closeWorkspace: closeLegacyWorkspace } = useWorkspaceState({
    normalizeDocument: (doc) => normalizeDoc(doc),
    onOpenRequest: handleWorkspaceOpenRequest,
  });
  const closeWorkspaceDrawer = useCallback(() => {
    closeWorkspaceDrawerUi();
    closeLegacyWorkspace();
  }, [closeLegacyWorkspace, closeWorkspaceDrawerUi]);
  const toggleWorkspaceDrawer = useCallback(() => {
    if (workspaceDrawerOpen) {
      closeWorkspaceDrawer();
      return;
    }
    openWorkspaceDrawer();
  }, [closeWorkspaceDrawer, openWorkspaceDrawer, workspaceDrawerOpen]);
  const [workspaceDrawerMotionPhase, setWorkspaceDrawerMotionPhase] = useState<
    "closed" | "open" | "closing"
  >(workspaceDrawerOpen ? "open" : "closed");
  useEffect(() => {
    if (!isPhoneShell) {
      setWorkspaceDrawerMotionPhase(workspaceDrawerOpen ? "open" : "closed");
      return;
    }

    if (workspaceDrawerOpen) {
      setWorkspaceDrawerMotionPhase("open");
      return;
    }

    setWorkspaceDrawerMotionPhase((current) =>
      current === "open" ? "closing" : current
    );

    const timer = window.setTimeout(() => {
      setWorkspaceDrawerMotionPhase("closed");
    }, MOBILE_MOTION.workspaceSheetExitMs);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isPhoneShell, workspaceDrawerOpen]);
  const [galleryMenu, setGalleryMenu] = useState<{ x: number; y: number; src?: string } | null>(null);
  const [visionBusySrc, setVisionBusySrc] = useState<string | null>(null);
  const [showImgGenGallery, setShowImgGenGallery] = useState(false);
  const [showImgGenDashboard, setShowImgGenDashboard] = useState(false);
  const galleryItemsToRender = useMemo(() => {
    const realGallery = gallery.filter((item) => !item.mock);
    return realGallery.length > 0 ? realGallery : gallery;
  }, [gallery]);

  // Lightweight local vision captioner: analyze colors and aspect ratio
  async function localDescribeImage(src: string): Promise<string> {
    return new Promise((resolve) => {
      try {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
          const w = img.width, h = img.height;
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");
          if (!ctx) return resolve("An image.");
          const max = 160;
          const scale = Math.min(1, max / Math.max(w, h));
          canvas.width = Math.max(1, Math.floor(w * scale));
          canvas.height = Math.max(1, Math.floor(h * scale));
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
          let r = 0, g = 0, b = 0;
          const step = 4 * Math.max(1, Math.floor((canvas.width * canvas.height) / 4000));
          let count = 0;
          for (let i = 0; i < data.length; i += step) {
            r += data[i]; g += data[i + 1]; b += data[i + 2]; count++;
          }
          r = Math.round(r / Math.max(1, count));
          g = Math.round(g / Math.max(1, count));
          b = Math.round(b / Math.max(1, count));
          const aspect = (w >= h ? `${(w / h).toFixed(2)}:1` : `1:${(h / w).toFixed(2)}`);
          const hex = `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
          resolve(`A ${w}×${h} image (aspect ${aspect}) with dominant color ${hex}. Describe key elements and style succinctly.`);
        };
        img.onerror = () => resolve("An image (unable to analyze). Describe its content.");
        img.src = src;
      } catch {
        resolve("An image. Describe its content.");
      }
    });
  }

  async function generatePromptForImage(src: string) {
    setVisionBusySrc(src);
    const endpoint = (import.meta as any).env?.VITE_VISION_ENDPOINT as string | undefined;
    let prompt: string | null = null;
    let mode: "remote" | "local" = "local";
    try {
      if (endpoint) {
        mode = "remote";
        let payload: any = {};
        if (src.startsWith("data:")) {
          payload.imageBase64 = src.split(",")[1] || "";
        } else {
          payload.url = src;
        }
        const r = await fetch(endpoint, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
        if (r.ok) {
          const j = await r.json().catch(() => ({}));
          const t = j.prompt || j.caption || j.text || null;
          if (t && typeof t === "string") prompt = t;
        }
      }
    } catch {
      // fall through to local
    }
    if (!prompt) {
      mode = "local";
      prompt = await localDescribeImage(src);
    }
    // Prefill Guardian chat with image-derived tag
    setPrefill(`[image-derived][${mode}] ${prompt}`);
    navigateToView("guardian");
    try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: "Image prompt generated" } })); } catch {}
    setVisionBusySrc(null);
  }
  const openDocInThread = useCallback((doc: DocumentLike) => {
    const normalizedDoc = normalizeDoc(doc);
    const tile = createDocumentContextTile(normalizedDoc, normalizedDoc.content || normalizedDoc.parsed_text || normalizedDoc.parsedText);
    if (!tile) return;
    setPendingComposerDocumentTiles((previous) => {
      const next = [...previous];
      if (!next.some((item) => item.id === tile.id)) {
        next.push(tile);
      }
      return next;
    });
    navigateToView("guardian");
  }, [navigateToView]);
  const createThreadFromDashboard = useCallback(() => {
    if (!checkAuthGate(auth, "threads create")) {
      return;
    }
    setPrefill(undefined);
    closeWorkspaceDrawer();
    navigateToView("guardian");
    if (typeof window !== "undefined") {
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:chat:new-draft", {
            detail: { source: "dashboard" },
          })
        );
      } catch (eventErr) {
        console.warn("[dashboard] draft-thread event failed", eventErr);
      }
    }
  }, [auth, closeWorkspaceDrawer, navigateToView]);
  // Use an active wallpaper for refractive glass; fall back to first gallery image if none chosen yet
  const activeWallpaper = useMemo(() => {
    return wallpaper ?? (gallery && gallery.length > 0 ? gallery[0].src : "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop");
  }, [wallpaper, gallery]);

  const bp = useBreakpoint();

  // Helper to jump to Guardian chat with a prefilled prompt
  function openChatWithPrompt(p: string) { setPrefill(p); navigateToView("guardian"); }

  // Responsive layout helper for Settings view
  const settingsLayout = useMemo(() => {
    // Keep the settings card compact, but give it enough width to breathe.
    if (bp === "sm" || bp === "md") {
      return { maxWidth: "none" };
    }
    // On larger screens, let the shell expand modestly without becoming a takeover.
    return { maxWidth: "min(46rem, calc(100vw - 2rem))" };
  }, [bp]);

  const galleryGridStyle = useMemo(
    () =>
      ({
        "--image-grid-cols": bp === "sm" || bp === "md" ? "2" : "4",
        "--image-grid-gap": "calc(var(--shell-gap) / 2)",
        display: "grid",
        width: "100%",
        minWidth: 0,
        minHeight: 0,
        boxSizing: "border-box",
        gap: "var(--image-grid-gap)",
        gridTemplateColumns: "repeat(var(--image-grid-cols), minmax(0, 1fr))",
        gridAutoRows: "max-content",
        gridAutoFlow: "row",
        alignItems: "start",
        alignContent: "start",
        justifyContent: "stretch",
        flex: "1 1 0%",
        overflow: "auto",
        paddingRight: "1px",
      }) as React.CSSProperties,
    [bp],
  );
  const showWorkspaceDrawer =
    workspaceShellEnabled &&
    (workspaceDrawerOpen || (isPhoneShell && workspaceDrawerMotionPhase === "closing"));
  const workspaceDrawerMotionState = isPhoneShell
    ? getMobileWorkspaceMotionState(
        isPhoneShell,
        workspaceDrawerOpen || workspaceDrawerMotionPhase === "closing",
        workspaceLayoutMode
      )
    : workspaceDrawerOpen
      ? "open"
      : "collapsed";
  const workspacePrimaryPaneStyle: React.CSSProperties = showWorkspaceDrawer
    ? isPhoneShell
      ? {
          flex: "1 1 0%",
          minWidth: 0,
          minHeight: 0,
        }
      : {
          flexBasis: primaryPaneBasis,
          flexGrow: primaryPaneRatio,
          flexShrink: 1,
          minWidth: primaryPaneMinWidth,
          minHeight: 0,
        }
    : {
        flex: "1 1 0%",
        minWidth: 0,
        minHeight: 0,
      };
  const workspaceDrawerPaneStyle: React.CSSProperties = isPhoneShell
    ? {
        padding: "var(--board-edge)",
        flex: "0 0 auto",
        width: mobileShellProfile.workspace.drawerWidth,
        minWidth: mobileShellProfile.workspace.drawerWidth,
        height: "100%",
        minHeight: "100%",
        maxHeight: "100%",
        alignSelf: "stretch",
        borderRadius: "var(--card-radius)",
        boxShadow:
          workspaceLayoutMode === "workspace_focus"
            ? "0 0 0 1px color-mix(in oklab, var(--panel-border-strong) 72%, transparent)"
            : undefined,
      }
    : {
        padding: "var(--board-edge)",
        flexBasis: workspacePaneBasis,
        flexGrow: workspacePaneRatio,
        flexShrink: 1,
        minWidth: workspacePaneMinWidth,
        minHeight: "0",
        maxHeight: "100%",
        borderRadius: "var(--card-radius)",
        boxShadow:
          workspaceLayoutMode === "workspace_focus"
            ? "0 0 0 1px color-mix(in oklab, var(--panel-border-strong) 72%, transparent)"
            : undefined,
      };
  const workspaceSplitSurfaceProps = workspaceShellEnabled
    ? {
        "data-testid": "workspace-layout-surface",
        "data-workspace-layout-mode": workspaceLayoutMode,
        "data-workspace-ratio-bucket": workspaceRatioBucket,
        "data-workspace-dominant": isWorkspaceDominant ? "true" : "false",
        "data-workspace-pane-ratio": workspacePaneRatio.toFixed(2),
        "data-workspace-pane-ratio-min": minWorkspacePaneRatio.toFixed(2),
        "data-workspace-pane-ratio-max": maxWorkspacePaneRatio.toFixed(2),
        "data-shell-viewport-class": shellViewportProfile.viewportClass,
        "data-shell-workspace-arrangement": shellViewportProfile.workspaceArrangement,
      }
    : {};
  const sharedWorkspaceDrawer = showWorkspaceDrawer ? (
    isPhoneShell ? (
      <div
        data-testid="workspace-drawer-overlay"
        data-overlay-mode="mobile"
        data-workspace-motion-state={workspaceDrawerMotionState}
        data-workspace-motion-phase={workspaceDrawerMotionPhase}
        className="absolute inset-0 z-20 flex items-stretch justify-end bg-black/35 backdrop-blur-sm"
      >
        <button
          type="button"
          aria-label="Close workspace drawer"
          className="absolute inset-0 border-0 bg-transparent p-0"
          onClick={closeWorkspaceDrawer}
        />
        <div
          data-testid="workspace-drawer-pane"
          data-overlay="true"
          data-pane-basis={mobileShellProfile.workspace.drawerWidth}
          data-pane-min-width="0px"
          data-shell-workspace-arrangement={shellViewportProfile.workspaceArrangement}
          className="relative z-10 h-full min-h-0 min-w-0 overflow-visible rounded-[var(--radius)]"
          style={workspaceDrawerPaneStyle}
          onClick={(event) => event.stopPropagation()}
          onPointerDown={(event) => event.stopPropagation()}
        >
          <WorkspaceDrawer
            routeContext={workspaceRouteContext}
            isOpen={workspaceDrawerOpen}
            activeTab={workspaceDrawerTab}
            layoutMode={workspaceLayoutMode}
            paneRatio={workspacePaneRatio}
            minPaneRatio={minWorkspacePaneRatio}
            maxPaneRatio={maxWorkspacePaneRatio}
            onOpenChange={(nextOpen) => {
              if (nextOpen) {
                openWorkspaceDrawer();
                return;
              }
              closeWorkspaceDrawer();
            }}
            onActiveTabChange={handleWorkspaceDrawerTabChange}
            onLayoutModeChange={setWorkspaceLayoutMode}
            projectId={effectiveDocumentsProjectId}
          />
        </div>
      </div>
    ) : (
      <div
        data-testid="workspace-drawer-pane"
        data-pane-basis={workspacePaneBasis}
        data-pane-min-width={workspacePaneMinWidth}
        data-shell-workspace-arrangement={shellViewportProfile.workspaceArrangement}
        className="min-h-0 min-w-0 overflow-visible rounded-[var(--radius)]"
        style={workspaceDrawerPaneStyle}
      >
        <WorkspaceDrawer
          routeContext={workspaceRouteContext}
          isOpen={workspaceDrawerOpen}
          activeTab={workspaceDrawerTab}
          layoutMode={workspaceLayoutMode}
          paneRatio={workspacePaneRatio}
          minPaneRatio={minWorkspacePaneRatio}
          maxPaneRatio={maxWorkspacePaneRatio}
          onOpenChange={(nextOpen) => {
            if (nextOpen) {
              openWorkspaceDrawer();
              return;
            }
            closeWorkspaceDrawer();
          }}
          onActiveTabChange={handleWorkspaceDrawerTabChange}
          onLayoutModeChange={setWorkspaceLayoutMode}
          projectId={effectiveDocumentsProjectId}
        />
      </div>
    )
  ) : null;
  const workspaceShellLaneClassName = isPhoneShell
    ? "flex h-full min-h-0 w-full flex-col gap-[var(--gutter)]"
    : "flex h-full min-h-0 w-full items-stretch gap-[var(--gutter)]";

  const runtimeDegraded =
    runtimeHealth.status === RUNTIME_HEALTH_STATUSES.DEGRADED;
  const runtimeFailureKind = runtimeHealth.failureKind ?? "unknown";
  const runtimeDetail =
    typeof process !== "undefined" &&
    process.env &&
    process.env.NODE_ENV !== "production" &&
    runtimeFailureKind === RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY
      ? runtimeHealth.llmDetail
      : null;

  const providerRuntimeState: ProviderRuntimeState =
    runtimeHealth.backendReachable === false
      ? PROVIDER_RUNTIME_STATES.OFFLINE
      : PROVIDER_RUNTIME_STATES.DEGRADED;

  const runtimePresentation = describeProviderState(providerRuntimeState);

  const showRuntimeBanner =
    runtimeDegraded &&
    runtimeFailureKind !== RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING;
  const runtimeLastHealthy = runtimeHealth.lastSuccessAt
    ? new Date(runtimeHealth.lastSuccessAt).toLocaleString()
    : "never";
  const workspaceAffordanceState = getWorkspaceAffordanceState({
    isPhoneShell,
    isOpen: workspaceDrawerOpen,
    isClosing: workspaceDrawerMotionPhase === "closing",
  });
  const workspaceSummonCopy = getWorkspaceAffordanceCopy(workspaceAffordanceState);
  const WorkspaceAffordanceGlyph = getWorkspaceAffordanceIcon(
    workspaceAffordanceState
  );
  const workspaceDrawerToggle = workspaceShellEnabled ? (
    <PhonePressButton
      type="button"
      isPhoneShell={isPhoneShell}
      className="pill-tab shrink-0 whitespace-nowrap"
      style={getWorkspaceAffordanceSurfaceStyle(
        isPhoneShell,
        workspaceAffordanceState
      )}
      data-state={workspaceAffordanceState === "open" ? "active" : "inactive"}
      data-workspace-affordance-state={workspaceAffordanceState}
      data-testid="workspace-drawer-toggle"
      aria-pressed={workspaceAffordanceState === "open"}
      aria-label={
        isPhoneShell
          ? workspaceSummonCopy.ariaLabel
          : "Toggle workspace drawer"
      }
      title={
        isPhoneShell
          ? workspaceSummonCopy.title
          : workspaceDrawerOpen
            ? "Close workspace drawer"
            : "Open workspace drawer"
      }
      onClick={toggleWorkspaceDrawer}
    >
      {isPhoneShell ? (
        <span
          className="inline-flex items-center"
          style={{ gap: WORKSPACE_AFFORDANCE.labelGap }}
        >
          <WorkspaceAffordanceGlyph
            className={WORKSPACE_AFFORDANCE.iconClassName}
            aria-hidden="true"
          />
          <span>{workspaceSummonCopy.label}</span>
        </span>
      ) : (
        "Workspace"
      )}
    </PhonePressButton>
  ) : null;
  const settingsUtilityAction = (
    <PhonePressButton
      type="button"
      isPhoneShell={isPhoneShell}
      className="pill-tab h-9 w-9 shrink-0 p-0"
      square
      data-state={view === "settings" ? "active" : "inactive"}
      data-testid="settings-utility-toggle"
      aria-label="Settings"
      title="Settings"
      onClick={openSettings}
    >
      <Settings2 className="h-4 w-4" aria-hidden="true" />
    </PhonePressButton>
  );
  const shareUtilityAction = activeRouteThreadId != null ? (
    <ShareButton
      targetType="thread"
      targetId={activeRouteThreadId}
      className="pill-tab shrink-0 whitespace-nowrap"
      dataState="inactive"
      isPhoneShell={isPhoneShell}
      style={{
        borderRadius: 999,
        border: "1px solid var(--chip-border)",
        background: "var(--chip-bg)",
        color: "var(--text)",
        fontSize: "0.78rem",
        fontWeight: 500,
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.22), 0 3px 10px rgba(0,0,0,0.18)",
      }}
    />
  ) : null;
  const desktopHeaderUtilityActions = (
    <>
      {settingsUtilityAction}
      {workspaceDrawerToggle}
      {shareUtilityAction}
    </>
  );
  const mobileHeaderUtilityActions = (
    <>
      {workspaceDrawerToggle}
      {settingsUtilityAction}
      {shareUtilityAction}
    </>
  );

  /* ─────────────────────────────────────────────────────────────────────────────
     🎭 SECTION: Dynamic Background Dramatic Effects
     When no wallpaper is set, we dramatically adjust background depth/fade
     based on the current theme for a more expressive look.
     ───────────────────────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (wallpaper) return; // wallpaper drives the look instead
    if (resolved === "dark") {
      setDepth(0.92);
      setFade(0.1);
    } else {
      setDepth(0.1);
      setFade(0.9);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolved, wallpaper]);

  /* ─────────────────────────────────────────────────────────────────────────────
     🚪 SECTION: Main AppShell Render
     The outermost wrappers set up the background, safe area, and design tokens.
     Inside, we render the navigation menu and the main content area, which
     switches between views like Guardian, Dashboard, Gallery, Documents, and Settings.
     ───────────────────────────────────────────────────────────────────────────── */
  return (
    <div
      className="flex h-screen w-screen flex-col min-h-0 bg-transparent box-border overflow-hidden"
      style={{
        /* baseline viewport guardrails */
        minWidth: shellViewportProfile.shellMinWidth,
        height: isPhoneShell ? "var(--shell-viewport-height, 100vh)" : undefined,
        minHeight: isPhoneShell
          ? "var(--shell-viewport-height, 100vh)"
          : shellViewportProfile.shellMinHeight,
        padding: "var(--edge-chrome)",
        alignItems: "center",
        color: "var(--text)",
        colorScheme: resolved,

        /* ✨ glossy‑glass overrides */
        "--tile-blur": "22px",                       // stronger backdrop blur
        "--bezel": "6px",                            // bezel (glass margin) can be tuned here
        "--lip-w": "6px",                            // deeper inner lip
        "--depth-scale": "1.35",                     // bolder drop‑shadow scale
        "--panel-bezel": "rgba(255,255,255,0.28)",   // brighter edge sparkle
        "--panel-bg": "rgba(17,24,39,0.72)",         // translucent dark fill

        /* merge global scene tokens & gradient/wallpaper */
        ...backgroundStyle,
        ...styleVars,

        // Apple system font at root layout level
        fontFamily:
          'SF Pro Display, SF Pro Icons, Apple System, BlinkMacSystemFont, ".SFNSDisplay-Regular", "Helvetica Neue", Helvetica, Arial, sans-serif',
      } as React.CSSProperties}
      aria-busy={startupLocked}
    >
      {/*
        --bezel: Visual margin between the refractive glass and the opaque content surface.
        Changing --bezel allows live tuning of the glass thickness throughout the UI without code edits.
      */}
      <div
        ref={shellContentRef}
        className="relative h-full w-full isolate flex flex-col flex-1 min-h-0 overflow-hidden"
        aria-hidden={startupLocked}
      >
      {/* Global outer glass skin */}
      <div className="absolute inset-0 -z-10 pointer-events-none rounded-[var(--viewport-radius)] overflow-hidden">
        <RefractiveGlassCard
          wallpaperUrl={activeWallpaper}
          className="w-full h-full rounded-[var(--viewport-radius)]"
          style={{ background: "transparent", border: "none" }}
          intensity={0.008}
          aberration={0}
        />
      </div>
      <div
        className={`relative h-full w-full isolate flex flex-col flex-1 min-h-0 overflow-hidden py-[var(--edge-chrome)] mx-auto ${resolved === "dark" ? "dark" : ""}`}
        style={{
          ...backgroundStyle,
          ...styleVars,
          borderRadius: "var(--viewport-radius)",
          paddingLeft: "var(--edge-chrome)",
          paddingRight: "var(--edge-chrome)",
          boxSizing: "border-box",
          color: "var(--text)",
          colorScheme: resolved,
        }}
        data-shell-profile={mobileShellProfile.shellMode}
      >
      <div id="cfy-portal-root" />
      {/* {view === "dashboard" && (
        <RefractiveGlassCard
          wallpaperUrl={activeWallpaper}
          className="w-full h-full rounded-[var(--radius)]"
          style={{ background: "transparent", border: "none" }}
          intensity={0.008}
          aberration={0}
        />
      )} */}
      {/* Glass Pill Menu Bar + Header Actions */}
      <div
        data-testid="app-shell-top-chrome"
        className={`relative z-10 w-full ${isPhoneShell ? "flex flex-col gap-[var(--shell-gap)]" : "grid items-start"}`}
        style={
          isPhoneShell
            ? undefined
            : {
                gridTemplateColumns: "auto minmax(var(--shell-gap), 1fr) auto",
              }
        }
      >
        <div
          data-testid="app-shell-nav-anchor"
          className="min-w-0 shrink-0"
          style={
            isPhoneShell
              ? undefined
              : {
                  gridColumn: "1",
                  justifySelf: "start",
                }
          }
        >
          <div
            className="glass-pill isolate relative inline-flex w-fit max-w-full min-w-0"
            data-testid="app-shell-top-nav"
            data-shell-nav-mode={
              mobileShellProfile.topNav.scrollable ? "scroll_rail" : "docked"
            }
            style={mobileTopNavDockStyle}
          >
            {/* glass backdrop */}
            <div className="absolute inset-0 -z-10 overflow-hidden rounded-full pointer-events-none">
              <RefractiveGlassCard
                wallpaperUrl={activeWallpaper}
                className="w-full h-full rounded-full"
                style={{ background: "transparent", border: "none" }}
                intensity={0.006}
                aberration={0.006}
              />
            </div>

            <div
              className="inline-flex min-w-0 items-center"
              style={mobileTopNavRailStyle}
            >
              {/* brand badge — doubles as layout mode toggle */}
              <PhonePressButton
                type="button"
                isPhoneShell={isPhoneShell}
                className="pill-tab brand-tab shrink-0 whitespace-nowrap"
                style={{ color: "var(--text-on-accent)" }}
                title={
                  layoutMode === "zen"
                    ? "Zen layout — click to switch to Focus"
                    : "Focus layout — click to switch to Zen"
                }
                onClick={() =>
                  setLayoutMode((prev) => (prev === "focus" ? "zen" : "focus"))
                }
              >
                Codexify
              </PhonePressButton>

              {/* beta release indicator — persistent across navigation */}
              <span
                className="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase whitespace-nowrap"
                style={{
                  background: "var(--accent)",
                  color: "var(--text-on-accent)",
                  opacity: 0.85,
                  letterSpacing: "0.05em",
                }}
                title="Beta release — feedback welcome"
              >
                Beta
              </span>

              {/* nav tabs */}
              <PhonePressButton
                isPhoneShell={isPhoneShell}
                className="pill-tab shrink-0 whitespace-nowrap"
                data-state={view === "guardian" ? "active" : "inactive"}
                onClick={() => navigateToView("guardian")}
              >
                Guardian
              </PhonePressButton>
              <PhonePressButton
                isPhoneShell={isPhoneShell}
                className="pill-tab shrink-0 whitespace-nowrap"
                data-state={view === "dashboard" ? "active" : "inactive"}
                onClick={() => navigateToView("dashboard")}
              >
                Dashboard
              </PhonePressButton>
              <PhonePressButton
                isPhoneShell={isPhoneShell}
                className="pill-tab shrink-0 whitespace-nowrap"
                data-state={view === "documents" ? "active" : "inactive"}
                onClick={() => navigateToView("documents")}
              >
                Documents
              </PhonePressButton>
              <PhonePressButton
                isPhoneShell={isPhoneShell}
                className="pill-tab shrink-0 whitespace-nowrap"
                data-state={view === "gallery" ? "active" : "inactive"}
                onClick={() => navigateToView("gallery")}
              >
                Gallery
              </PhonePressButton>
              <PhonePressButton
                isPhoneShell={isPhoneShell}
                className="pill-tab shrink-0 whitespace-nowrap"
                data-state={view === "personaStudio" ? "active" : "inactive"}
                onClick={() => navigateToView("personaStudio")}
              >
                Persona Studio
              </PhonePressButton>
            </div>
          </div>
        </div>
        <div
          data-testid="app-shell-utility-cluster"
          className={`flex shrink-0 items-center ${isPhoneShell ? "gap-[var(--pill-gap)]" : "gap-2"}`}
          style={
            isPhoneShell
              ? undefined
              : {
                  gridColumn: "3",
                  justifySelf: "end",
                }
          }
        >
          {isPhoneShell ? mobileHeaderUtilityActions : desktopHeaderUtilityActions}
        </div>
      </div>

      {showRuntimeBanner && (
        <div className="relative z-10 w-full mt-3">
          <div
            className="flex w-full flex-col gap-1 rounded-[14px] border px-4 py-2 text-xs sm:text-sm"
            style={{
              borderColor: "var(--panel-border)",
              background:
                "color-mix(in oklab, var(--panel-bg) 90%, transparent)",
              color: "var(--text)",
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold tracking-wide">
                {runtimePresentation.title}
              </span>
              <span className="opacity-80">failure: {runtimeFailureKind}</span>
              <span className="opacity-70">
                last healthy: {runtimeLastHealthy}
              </span>
            </div>
            {runtimeDetail ? (
              <div className="text-[11px] opacity-75" style={{ color: "var(--muted)" }}>
                {runtimePresentation.detail} — detail: {runtimeDetail}
              </div>
            ) : (
              <div className="text-[11px] opacity-75" style={{ color: "var(--muted)" }}>
                {runtimePresentation.detail}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────────
          📺 SECTION: Main Content Area
          The main workspace area. Depending on the selected view, we show:
          - Guardian chat + workspace
          - Dashboard
          - Gallery
          - Documents
          - Settings
         ───────────────────────────────────────────────────────────────────────────── */}
      <div className="relative z-10 isolate flex flex-col flex-1 min-h-0 overflow-hidden items-stretch">
        <div
          className="flex-1 h-full min-h-0 flex overflow-hidden"
          style={{
            paddingTop: "var(--page-gutter-top)",   // always-on gutter under the pill dock
            paddingRight: "var(--page-pad)",        // mode-dependent
            paddingBottom: "var(--page-pad)",       // mode-dependent
            paddingLeft: "var(--page-pad)",         // mode-dependent
          }}
        >
          {startupLocked && (
            <FrameCard
              fill
              refractiveFallback
              shimmerMode="subtle"
              className="flex h-full w-full min-h-0 overflow-hidden"
            >
              <div
                className="h-full w-full rounded-[var(--card-radius)] border"
                aria-hidden="true"
                style={{
                  borderColor: "var(--panel-border)",
                  background:
                    "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                }}
              />
            </FrameCard>
          )}
          {!startupLocked && view === "documents" && (
            <div
              className="isolate"
              data-active-view="documents"
              data-active-view-contract="left-center-right"
              data-thread-rail="present"
              data-view-family="documents"
              style={{
                "--radius": "var(--card-radius)",
                "--frame": "1px",
                "--bezel": "var(--bezel, 6px)",
                "--rim": "1px",
                "--gutter": "var(--shell-gap)",
                "--card-pad": shellViewportProfile.shellCardPad,
                "--min-h": shellViewportProfile.contentMinHeight,
                borderRadius: "var(--card-radius)",
              } as React.CSSProperties}
            >
              <div
                className={workspaceShellLaneClassName}
                {...workspaceSplitSurfaceProps}
              >
                {/* LIST COLUMN (left) */}
                <div
                  data-testid="workspace-primary-pane"
                  data-pane-basis={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneBasis
                      : "100.00%"
                  }
                  data-pane-min-width={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneMinWidth
                      : "0px"
                  }
                  className="min-w-0 min-h-0 overflow-visible rounded-[var(--radius)]"
                  style={{
                    padding: "var(--board-edge)",
                    width: "var(--w, auto)",
                    maxWidth: "var(--max-w, none)",
                    minWidth: "var(--min-w, 0)",
                    height: "var(--h, auto)",
                    minHeight: "var(--min-h, 0)",
                    maxHeight: "var(--max-h, none)",
                    ["--min-h"]: shellViewportProfile.contentMinHeight,
                    borderRadius: "var(--card-radius)",
                    ...workspacePrimaryPaneStyle,
                  }}
                >
                  <FrameCard
                    fill
                    refractiveFallback
                    shimmerMode="subtle"
                    className="h-full w-full min-h-0 flex flex-col overflow-hidden"
                  >
                    <DocumentsView
                      documents={allDocuments}
                      extColors={extColors}
                      onOpenInThread={openDocInThread}
                      onDeleteDocument={deleteDocument}
                      defaultProjectId={generalProjectId}
                      documentScope={documentScope}
                      onDocumentScopeChange={setDocumentScope}
                      threadScopeEnabled={activeRouteThreadId != null}
                    />
                  </FrameCard>
                </div>
                {sharedWorkspaceDrawer}
              </div>
            </div>
          )}
          {!startupLocked && view === "gallery" && (
            <>
              <FrameCard
                fill
                refractiveFallback
                shimmerMode="subtle"
                className="flex h-full w-full min-h-0 flex-col overflow-hidden"
              >
                <div className="flex h-full min-h-0 flex-col p-[var(--card-pad)]">
                  <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>Gallery</div>
                  <div
                    className="min-h-0"
                    style={galleryGridStyle}
                    onDrop={galleryUploader.onDrop}
                    onDragOver={galleryUploader.onDragOver}
                  >
                    {galleryItemsToRender.map((g, i) => {
                      const resolvedSrc = normalizeGallerySrc(g.src) || g.src;
                      return (
                      <div
                        key={g.src || i}
                        className="relative w-full min-w-0 overflow-hidden rounded-[var(--radius)] border"
                        style={{
                          aspectRatio: "1 / 1",
                          boxSizing: "border-box",
                          background: "var(--panel-bg)",
                          borderColor: "var(--panel-border)",
                          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)",
                        }}
                        onContextMenu={(e) => { e.preventDefault(); setGalleryMenu({ x: e.clientX, y: e.clientY, src: resolvedSrc }); }}
                      >
                        <AppShellGalleryImage src={resolvedSrc} alt={g.prompt} />
                        {visionBusySrc === resolvedSrc && (
                          <div className="absolute inset-0 grid place-items-center bg-black/40">
                            <div className="h-6 w-6 rounded-full border-2 border-white/70 border-t-transparent animate-spin" />
                          </div>
                        )}
                        {g.mock && (
                          <span
                            className="absolute left-2 top-2 z-10 rounded-full px-2 py-1 text-[10px] border"
                            style={{
                              background:
                                "color-mix(in oklab, var(--chip-bg) 86%, transparent)",
                              color: "var(--text)",
                              borderColor: "var(--chip-border)",
                            }}
                          >
                            Mock
                          </span>
                        )}
                      </div>
                      );
                    })}
                  </div>
                  <div className="flex items-center justify-between gap-2 pt-3 text-xs opacity-80">
                    <div>Drag & drop images or documents here, or</div>
                    <button type="button" className="underline" onClick={galleryUploader.pick}>Choose files</button>
                    <button type="button" className="underline ml-2" onClick={() => setShowImgGenGallery(true)}>Generate Image</button>
                  </div>
                </div>
              </FrameCard>
              <ImageGenModal open={showImgGenGallery} onOpenChange={setShowImgGenGallery} />
            </>
          )}
          {!startupLocked && view === "guardian" && (
            <div
              className="h-full w-full isolate"
              data-active-view="guardian"
              data-active-view-contract="left-center-right"
              data-thread-rail="present"
              data-view-family="guardian"
              style={{ "--gutter": "var(--shell-gap)" } as React.CSSProperties}
            >
              <div
                className={workspaceShellLaneClassName}
                {...workspaceSplitSurfaceProps}
              >
                <div
                  data-testid="workspace-primary-pane"
                  data-pane-basis={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneBasis
                      : "100.00%"
                  }
                  data-pane-min-width={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneMinWidth
                      : "0px"
                  }
                  className="min-h-0 min-w-0"
                  style={workspacePrimaryPaneStyle}
                >
                  <div
                    className="flex h-full w-full min-h-0 isolate flex-col"
                    aria-busy={sessionComposerBlocked}
                    data-composer-blocked={
                      sessionComposerBlocked ? "true" : "false"
                    }
                    style={{
                      "--frame": "1px",
                      "--bezel": "var(--bezel, 6px)",
                      "--rim": "1px",
                    } as React.CSSProperties}
                  >
                    <ErrorBoundary>
                      <GuardianChatWithSidebar
                        key={`guardian-surface-${guardianSurfaceEpoch}`}
                        guardianName={guardianName}
                        userName={userName}
                        prefill={prefill}
                        onPrefillConsumed={() => setPrefill(undefined)}
                        pendingDocumentTiles={pendingComposerDocumentTiles}
                        onPendingDocumentTilesConsumed={() =>
                          setPendingComposerDocumentTiles([])
                        }
                        onWorkspaceToggle={toggleWorkspaceDrawer}
                        workspaceOpen={workspaceDrawerOpen}
                        activeWorkspaceDoc={null}
                        onWorkspaceClose={closeWorkspaceDrawer}
                      />
                    </ErrorBoundary>
                  </div>
                </div>
                {sharedWorkspaceDrawer}
              </div>
            </div>
          )}
          {!startupLocked && view === "dashboard" && (
            <div
              className="h-full w-full isolate"
              data-active-view="dashboard"
              data-active-view-contract="center-right"
              data-thread-rail="absent"
              data-view-family="dashboard"
              style={{ "--gutter": "var(--shell-gap)" } as React.CSSProperties}
            >
              <div
                className={workspaceShellLaneClassName}
                {...workspaceSplitSurfaceProps}
              >
                <div
                  data-testid="workspace-primary-pane"
                  data-pane-basis={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneBasis
                      : "100.00%"
                  }
                  data-pane-min-width={
                    showWorkspaceDrawer && !isPhoneShell
                      ? primaryPaneMinWidth
                      : "0px"
                  }
                  className="min-h-0 min-w-0"
                  style={workspacePrimaryPaneStyle}
                >
                  <DashboardView
                    extColors={extColors}
                    gallery={gallery}
                    onImagePrompt={openChatWithPrompt}
                    onRequestNewProject={openCreateProjectModal}
                    onRequestNewThread={createThreadFromDashboard}
                    onNavigateDocuments={() => navigateToView("documents")}
                    onNavigateGallery={() => navigateToView("gallery")}
                    threadGridRows={dashboardThreadRows}
                  />
                </div>
                {sharedWorkspaceDrawer}
              </div>
            </div>
          )}
          {!startupLocked && view === "settings" && (
            <FrameCard
              refractiveFallback
              shimmerMode="subtle"
              className="mx-auto w-full min-h-0 max-h-full flex flex-col overflow-hidden"
              data-testid="settings-framecard"
              style={settingsLayout}
            >
              <div className="w-full min-h-0 max-h-full overflow-auto p-0" data-testid="settings-scroll-body">
                <ErrorBoundary>
                  <SettingsView
                    mode={mode}
                    setMode={setMode}
                    guardianName={guardianName}
                    setGuardianName={setGuardianName}
                    userName={userName}
                    setUserName={setUserName}
                    role={role}
                    setRole={setRole}
                    notes={notes}
                    setNotes={setNotes}
                    baseColor={baseColor}
                    setBaseColor={setBaseColor}
                    depth={depth}
                    setDepth={setDepth}
                    fade={fade}
                    setFade={setFade}
                    resolved={resolved}
                    systemPrompt={systemPrompt}
                    setSystemPrompt={setSystemPrompt}
                    wallpaper={wallpaper}
                    setWallpaper={setWallpaper}
                    extColors={extColors}
                    setExtColors={setExtColors}
                    dashboardThreadRows={dashboardThreadRows}
                    setDashboardThreadRows={setDashboardThreadRows}
                    ingestionEnabled={ingestionEnabled}
                    setIngestionEnabled={setIngestionEnabled}
                  />
                </ErrorBoundary>
              </div>
            </FrameCard>
          )}
          {!startupLocked && view === "personaStudio" && (
            <div
              className="h-full w-full isolate"
              data-active-view="personaStudio"
              data-active-view-contract="left-center-right"
              data-thread-rail="absent"
              data-view-family="personaStudio"
            >
              <FrameCard
                refractiveFallback
                shimmerMode="subtle"
                className="flex h-full w-full min-h-0 flex-col overflow-hidden"
                data-testid="persona-studio-framecard"
              >
                <PersonaStudioPage />
              </FrameCard>
            </div>
          )}
        </div>
      </div>
      </div>
      </div>
      {startupOverlay && <div className="absolute inset-0 z-[1400]">{startupOverlay}</div>}
      {projectModalOpen && (
        <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closeCreateProjectModal}
          />
          <form
            onSubmit={handleProjectSubmit}
            className="relative z-[1201] w-[min(480px,90vw)] rounded-[var(--card-radius)] border p-6 flex flex-col gap-4 shadow-xl"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          >
            <div>
              <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
                Create Project
              </h2>
              <p className="text-sm mt-1 opacity-70" style={{ color: "var(--muted)" }}>
                Name your project and optionally pick an icon for quick recognition.
              </p>
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="projectName" style={{ color: "var(--text)" }}>
                  Project name
                </label>
                <Input
                  id="projectName"
                  value={projectModalName}
                  onChange={(event) => setProjectModalName(event.target.value)}
                  placeholder="e.g., Research, Launch Prep…"
                  className="rounded-[var(--tile-radius)]"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                  disabled={projectModalSaving}
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="projectIcon" style={{ color: "var(--text)" }}>
                  Icon (optional)
                </label>
                <Input
                  id="projectIcon"
                  value={projectModalIcon}
                  onChange={(event) => setProjectModalIcon(event.target.value)}
                  placeholder="📁"
                  className="rounded-[var(--tile-radius)]"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                  disabled={projectModalSaving}
                />
              </div>
              {projectModalError && (
                <div className="text-sm font-medium text-red-400">
                  {projectModalError}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={closeCreateProjectModal}
                disabled={projectModalSaving}
                className="rounded-full px-4"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="rounded-full px-4"
                disabled={projectModalSaving}
              >
                {projectModalSaving ? "Creating…" : "Create Project"}
              </Button>
            </div>
          </form>
        </div>
      )}
      <ToastPortal />
      {galleryMenu && (
        <ContextMenu
          x={galleryMenu.x}
          y={galleryMenu.y}
          onClose={() => setGalleryMenu(null)}
          items={[
            ...(galleryMenu.src ? [{ label: "Generate Prompt", onClick: () => generatePromptForImage(galleryMenu.src!) }] : []),
            ...(galleryMenu.src ? [{ label: "Delete", onClick: () => {
              const src = galleryMenu.src!;
              const removed = gallery.find(
                (g) => normalizeGallerySrc(g.src) === normalizeGallerySrc(src)
              );
              deleteGalleryItem(src);
              try {
                window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: "Image deleted", actionLabel: "Undo", onAction: () => {
                  if (removed) setGallery((prev) => [removed, ...prev]);
                }}}));
              } catch {}
            }}] : []),
          ]}
        />
      )}
    </div>
  );
}
