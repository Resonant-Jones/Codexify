// Chat Sidebar: per-chat context (Threads/Projects list, search, project modal)

import * as React from "react";
import { Search, Plus, ChevronDown, Menu, MoreVertical, Archive as ArchiveIcon, ArchiveRestore, Trash2, Pencil, Loader2, Check, AlertTriangle, FolderOpen, PlusCircle } from "lucide-react";
import clsx from "clsx";
import { Input } from "@/components/ui/input";
import PreviewTile from "@/components/ui/PreviewTile";
import type { Project, ThreadAction } from "@/types/your-types-file";

import api from "@/lib/api";

// Thread endpoint helper: prefer /chat/:id, fall back to /chat/threads/:id for older builds
async function threadApi(
  method: "patch" | "delete",
  id: string | number,
  body?: any
) {
  const paths = [`/chat/${id}`, `/chat/threads/${id}`];
  let lastErr: any = null;
  for (const p of paths) {
    try {
      if (method === "patch") return await api.patch(p, body);
      if (method === "delete") return await api.delete(p);
    } catch (err: any) {
      // Retry on 404 to support either route; bubble up other errors (401, 500, etc.)
      if (err?.response?.status === 404) {
        lastErr = err;
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error("Thread API routes not available");
}

// emit a soft "refresh" signal so parent/SSE listeners can update lists optimistically
function emitThreadsRefresh(kind: string, detail: Record<string, any>) {
  try {
    window.dispatchEvent(new CustomEvent("cfy:threads:refresh", { detail: { kind, ...detail } }));
  } catch {
    // noop in non-DOM environments
  }
}

type ToastMessage = { kind: "success" | "error"; message: string };
type ActiveToast = ToastMessage & { id: number };

function colorStringToRgba(input: string, alpha: number, fallback: string): string {
  const value = (input || "").trim();
  const hex = value.match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const raw = hex[1].length === 3
      ? hex[1].split("").map((c) => c + c).join("")
      : hex[1];
    const r = parseInt(raw.slice(0, 2), 16);
    const g = parseInt(raw.slice(2, 4), 16);
    const b = parseInt(raw.slice(4, 6), 16);
    if ([r, g, b].every((n) => Number.isFinite(n))) {
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
  }
  const rgb = value.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (rgb) {
    const [, r, g, b] = rgb;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return fallback;
}

function emitToast(kind: ToastMessage["kind"], message: string) {
  try {
    window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { kind, message } }));
  } catch {
    // ignore when running without DOM (SSR/tests)
  }
}

// ── Projects API normalizers (handle {projects:[…]} and {project_id}) ────────
function normalizeProjectsResponse(res: any) {
  const payload = res?.data ?? res;
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.projects)
      ? payload.projects
      : [];
  return list.map((p: any) => ({
    id: String(p.id ?? p.project_id),
    name: p.name ?? p.project_name ?? "Untitled",
    icon: p.icon ?? "📁",
    description: p.description ?? "",
    created_at: p.created_at,
    updated_at: p.updated_at,
  }));
}
function extractProjectId(res: any): string | null {
  const d = res?.data ?? res;
  const id = d?.id ?? d?.project_id;
  return id != null ? String(id) : null;
}

// ── Project cache helpers: persist across route changes / reloads ───────────
function readProjectsCache(): Project[] {
  try {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem("cfy.projectsCache");
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.filter((p) => p && p.id && p.name) : [];
  } catch {
    return [];
  }
}
function writeProjectsCache(list: Project[]) {
  try {
    if (typeof window === "undefined") return;
    const compact = list.map((p) => ({ id: String(p.id), name: p.name, icon: p.icon, color: p.color }));
    window.localStorage.setItem("cfy.projectsCache", JSON.stringify(compact));
  } catch {
    // ignore
  }
}
function mergeProjects(primary: Project[], secondary: Project[]): Project[] {
  // Keep order of 'primary', then fill from 'secondary' (dedupe by id or name)
  const seen = new Set<string>();
  const out: Project[] = [];
  const push = (p?: Project) => {
    if (!p) return;
    const key = String(p.id ?? "");
    const nameKey = `name:${p.name}`;
    if (key && seen.has(key)) return;
    if (!key && seen.has(nameKey)) return;
    if (key) seen.add(key);
    else seen.add(nameKey);
    out.push({ id: String(p.id), name: p.name, icon: p.icon, color: p.color });
  };
  primary.forEach(push);
  secondary.forEach(push);
  return out;
}

// Shallow thread list equality to avoid setState loops on no-op updates
function sameThread(a: Thread, b: Thread): boolean {
  return String(a.id) === String(b.id)
    && a.title === b.title
    && (a.lastMessage ?? "") === (b.lastMessage ?? "")
    && (a.projectId ?? null) === (b.projectId ?? null)
    && (a.archivedAt ?? null) === (b.archivedAt ?? null)
    && (a.unread ?? 0) === (b.unread ?? 0);
}
function equalThreadLists(a: Thread[], b: Thread[]): boolean {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b)) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!sameThread(a[i], b[i])) return false;
  }
  return true;
}



/*
 * Sidebar.tsx
 *
 * Purpose: Renders the left-side navigation panel for chat — the Threads/Projects
 * selector, search, and the lists themselves. This is a critical UX surface: it
 * determines how users find conversations, scope by project, and start new chats.
 *
 * Design decisions & rationale:
 * - We keep the segmented tab state persisted to localStorage so users return to
 *   the same mental model when they refresh (important for power users).
 * - The tab control is implemented as an accessible "tablist" with an animated
 *   sliding indicator to provide both visual and keyboard affordances.
 * - `scopedThreads` is computed to allow scoping to "Loose", a specific project,
 *   or all threads; keeping this logic local ensures the UI can filter quickly
 *   without round trips to the server.
 * - `FrameCard` is used as the visual wrapper so every thread tile inherits the
 *   same liquid rim + elevation profile. Avoid wrapping multiple cards in a
 *   single outer rounded container to prevent clipping of shadows/blur.
 *
 * Notes for future us:
 * - If thread lists grow very large, consider virtualization (e.g. react-window)
 *   to maintain snappy scroll performance.
 * - Avoid persisting large binary blobs or generated artifacts in this component.
 */


// Safe CSS var reader: always targets the documentElement and falls back if unavailable
function getComputedStyleVar(name: string, fallback = ""): string {
  try {
    const win: any = (typeof window !== "undefined") ? window : null;
    const doc: any = (typeof document !== "undefined") ? document : null;
    if (!win || !doc) return fallback;
    const el = doc.documentElement as Element | null;
    if (!el || typeof win.getComputedStyle !== "function") return fallback;
    const val = win.getComputedStyle(el).getPropertyValue(name);
    return (val && typeof val === "string" ? val.trim() : "") || fallback;
  } catch {
    return fallback;
  }
}

// ── Projects API normalizers (handle {projects:[…]} and {project_id}) ────────

type Message = { id: string; authorId: string; authorName: string; content: string; createdAt: number; status?: "sending"|"sent"|"delivered"|"read" };
type Thread = {
  id: string;
  title: string;
  lastMessage: string;
  unread: number;
  participants: Array<{ id: string; name: string }>;
  messages: Message[];
  projectId?: string | null;
  parentId?: string | null;
  archivedAt?: string | null;
}; // Thread type definition

export type { Thread };

type Props = {
  threads: Thread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;

  // NEW (project scoping)
  projectId?: string | null;
  onProjectChange?: (id: string | null) => void;
  projects?: Project[];
  creatingThread?: boolean;
  onDeleteThread?: (threadId: string) => void;

  // Added optional collapse handler
  onToggleCollapse?: () => void;

  // Optional: create a new project (UI collects name/icon)
  onCreateProject?: (data: { name: string; icon?: string; color?: string }) => Promise<Project | void> | Project | void;
};

export default function Sidebar({
  threads,
  activeId,
  onSelect,
  onNewChat,
  projectId = null,
  onProjectChange,
  projects = [],
  creatingThread,
  onDeleteThread,
  onToggleCollapse,
  onCreateProject,
}: Props) {
  // Persisted tab state: keeps user context across refreshes. Key: cfy.sidebarTab
  const [tab, setTab] = React.useState<"threads"|"projects">(() =>
    (typeof window === "undefined" ? "threads" : ((localStorage.getItem("cfy.sidebarTab") as any) || "threads"))
  );
  const [q, setQ] = React.useState("");

  // Local mirror of threads so we can optimistically reflect cross-view updates
  const [threadList, setThreadList] = React.useState<Thread[]>(threads);
  // Per-thread preview cache (lastMessage). We do NOT trust upstream t.lastMessage after mount.
  const previewRef = React.useRef<Map<string, string>>(new Map());
  // Stable per-thread titles to avoid accidental overwrites from upstream bugs
  const stableTitleRef = React.useRef<Map<string, string>>(new Map());
  // Guard against duplicate/rapid SSE events causing re-renders
  const lastEventSigRef = React.useRef<string | null>(null);
  const lastEventTsRef = React.useRef<number>(0);
  React.useEffect(() => {
    setThreadList(prev => (equalThreadLists(prev, threads) ? prev : threads));
  }, [threads]);

  // Seed preview cache for new threads and prune removed ids
  React.useEffect(() => {
    const map = previewRef.current;
    const incomingIds = new Set<string>();

    // If many threads arrive with the same non-empty lastMessage, it's likely a
    // shared reference/bug upstream. Build a histogram and avoid seeding from
    // obviously duplicated values so we don't mirror one preview across all tiles.
    const freq = new Map<string, number>();
    threads.forEach((t) => {
      const s = ((t.lastMessage ?? "") as any).toString().trim();
      if (s) freq.set(s, (freq.get(s) || 0) + 1);
    });

    threads.forEach((t) => {
      const id = String(t.id ?? "");
      if (!id) return;
      incomingIds.add(id);
      if (!map.has(id)) {
        const candidate = ((t.lastMessage ?? "") as any).toString();
        const trimmed = candidate.trim();
        const looksDuplicated = trimmed && (freq.get(trimmed) || 0) > 1;
        // Only seed from props if the value doesn't look like a global duplicate.
        if (!looksDuplicated && trimmed) {
          map.set(id, candidate);
        }
        // Otherwise, skip seeding — this thread will get its preview from
        // real-time events (cfy:threads:refresh) without polluting siblings.
      }
    });

    // prune any previews that no longer have a backing thread
    Array.from(map.keys()).forEach((k) => {
      if (!incomingIds.has(k)) map.delete(k);
    });
  }, [threads]);

  // Seed stable titles once per thread id from the first non-empty title we see
  React.useEffect(() => {
    const map = stableTitleRef.current;
    threads.forEach((t) => {
      const id = String(t.id ?? "");
      const title = (t.title ?? "").toString().trim();
      if (id && title && !map.has(id)) {
        map.set(id, title);
      }
    });
  }, [threads]);

  // Local collapse state fallback if no handler passed
  const [collapsed, setCollapsed] = React.useState(false);

  // New Project modal state
  const [showProjectModal, setShowProjectModal] = React.useState(false);
  const [projName, setProjName] = React.useState("");
  const [projIcon, setProjIcon] = React.useState("📁");
  const [savingProject, setSavingProject] = React.useState(false);

  const [toast, setToast] = React.useState<ActiveToast | null>(null);
  const accentColor = React.useMemo(() => getComputedStyleVar("--accent", "#6B7280"), []);
  const textColor = React.useMemo(() => getComputedStyleVar("--text", "#F9FAFB"), []);
  const successBg = React.useMemo(
    () => colorStringToRgba(accentColor, 0.16, "rgba(107,114,128,0.16)"),
    [accentColor]
  );
  const successBorder = React.useMemo(
    () => colorStringToRgba(accentColor, 0.45, "rgba(107,114,128,0.45)"),
    [accentColor]
  );
  const errorColor = "#f87171";
  const errorBg = React.useMemo(
    () => colorStringToRgba(errorColor, 0.16, "rgba(248,113,113,0.16)"),
    []
  );
  const errorBorder = React.useMemo(
    () => colorStringToRgba(errorColor, 0.45, "rgba(248,113,113,0.45)"),
    []
  );

  React.useEffect(() => {
    function onToast(event: Event) {
      const detail = (event as CustomEvent<ToastMessage>).detail;
      if (!detail || !detail.message) return;
      setToast({ ...detail, id: Date.now() });
    }
    window.addEventListener("cfy:toast", onToast as EventListener);
    return () => window.removeEventListener("cfy:toast", onToast as EventListener);
  }, []);

  React.useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  // Local optimistic list of projects (seed from cache so it survives route changes)
  const [projectList, setProjectList] = React.useState<Project[]>(() => {
    const cache = readProjectsCache();
    return cache.length ? cache : projects;
    });
  // When parent projects change, merge them with locals and persist cache
  React.useEffect(() => {
    setProjectList((prev) => {
      const merged = mergeProjects(prev, projects);
      return merged;
    });
  }, [projects]);
  // Persist cache whenever list changes
  React.useEffect(() => { writeProjectsCache(projectList); }, [projectList]);

  // Persist last project scope across route changes / reloads
  const [localProjectId, setLocalProjectId] = React.useState<string | null>(() => {
    if (projectId !== undefined && projectId !== null) return projectId;
    if (typeof window !== "undefined") {
      const v = window.localStorage.getItem("cfy.lastProjectId");
      if (v === "null") return null;
      return v ? v : null;
    }
    return null;
  });
  React.useEffect(() => {
    // keep local in sync if parent updates projectId
    if (projectId !== undefined) {
      setLocalProjectId(projectId ?? null);
      try { window.localStorage.setItem("cfy.lastProjectId", projectId ?? "null"); } catch {}
    }
  }, [projectId]);
  function setScope(id: string | null) {
    if (onProjectChange) onProjectChange(id);
    else setLocalProjectId(id);
    try { window.localStorage.setItem("cfy.lastProjectId", id ?? "null"); } catch {}
  }

  // Local delete reflection (also forwards to parent if provided)
  const handleDeleteThreadLocal = React.useCallback((threadId: string) => {
    try { onDeleteThread?.(threadId); } catch {}
    setThreadList(prev => prev.filter(t => String(t.id) !== String(threadId)));
    // also drop any cached preview so it doesn't linger
    try { previewRef.current.delete(String(threadId)); } catch {}
  }, [onDeleteThread]);

  // Helper to refresh projects from server (with auth)
  async function refreshProjectsFromServer() {
    try {
      const res = await api.get("/projects");
      const list = normalizeProjectsResponse(res);
      if (Array.isArray(list) && list.length) {
        setProjectList((prev) => mergeProjects(prev, list as any));
      }
    } catch (e) {
      // ignore; parent may refresh later
    }
  }

  // Always try to hydrate from server on mount
  React.useEffect(() => { refreshProjectsFromServer(); }, []);

  // Proactively hydrate from server when the list looks empty/stale
  React.useEffect(() => {
    // If parent hasn't provided projects yet and our local list is empty, fetch
    if ((projects?.length ?? 0) === 0 && projectList.length === 0) {
      refreshProjectsFromServer();
    }
  }, [projects?.length]);

  // Also refresh when window regains focus or tab becomes visible
  React.useEffect(() => {
    const onFocus = () => refreshProjectsFromServer();
    const onVisible = () => { if (document.visibilityState === "visible") refreshProjectsFromServer(); };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  // Listen for cross-view thread updates (rename/archive/delete/move)
  React.useEffect(() => {
    function onThreadsRefresh(raw: Event) {
      const ce = raw as CustomEvent;
      const d: any = ce.detail || {};
      const kind = d?.kind ?? d?.type;
      // Ignore heartbeat / ping or events without any useful payload
      if (!d || kind === "ping") return;

      // Drop identical events that arrive back-to-back (prevents state loops)
      const idGuess =
        d?.id != null ? String(d.id) :
        d?.thread_id != null ? String(d.thread_id) :
        d?.threadId != null ? String(d.threadId) :
        "";

      const sig = JSON.stringify({
        k: kind,
        id: idGuess,
        title: (d.title ?? ""),
        content: (d.content ?? d.message?.content ?? ""),
        proj: (d.project_id ?? d.projectId ?? null),
        arch: (d.archived ?? null),
      });

      const now = Date.now();
      if (lastEventSigRef.current === sig && now - (lastEventTsRef.current || 0) < 250) {
        return; // ignore near-duplicate event
      }
      lastEventSigRef.current = sig;
      lastEventTsRef.current = now;

      setThreadList(prev => {
        const id =
          d?.id != null ? String(d.id)
          : d?.thread_id != null ? String(d.thread_id)
          : d?.threadId != null ? String(d.threadId)
          : "";
        if (!id) return prev;

        const idx = prev.findIndex(t => String(t.id) === id);
        if (idx === -1) return prev;

        switch (kind) {
          case "rename": {
            const title = (d.title ?? "").trim();
            stableTitleRef.current.set(id, title);
            if (!title || prev[idx].title === title) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], title };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "archive": {
            if (prev[idx].archivedAt) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], archivedAt: new Date().toISOString() };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "unarchive": {
            if (!prev[idx].archivedAt) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], archivedAt: null };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "message":
          case "message.created": {
            const content = (d.content ?? d.message?.content ?? "").toString();
            if (!content) return prev;
            // Cache the preview strictly for this thread id
            try { previewRef.current.set(id, content); } catch {}
            const next = [...prev];
            next[idx] = { ...next[idx], lastMessage: content };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "delete": {
            const next = prev.filter(t => String(t.id) !== id);
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "move": {
            const proj = d.project_id ?? d.projectId ?? null;
            if ((prev[idx].projectId ?? null) === (proj ?? null)) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], projectId: proj };
            return equalThreadLists(next, prev) ? prev : next;
          }
          default:
            return prev;
        }
      });
    }
    window.addEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
    return () => window.removeEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
  }, []);

  // Hoisted declaration prevents “Cannot access uninitialized variable” errors
  function handleToggleCollapse() {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setCollapsed(prev => !prev);
    }
  }

  async function handleCreateProjectSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    const name = projName.trim();
    if (!name) return;
    setSavingProject(true);
    try {
      let created: Project | void | undefined;
      if (onCreateProject) {
        created = await onCreateProject({ name, icon: projIcon });
      } else {
        // Prefer shared API helper so auth headers are included
        const resp = await api.post("/projects", { name, description: "" });
        const createdId = extractProjectId(resp);
        if (createdId) {
          created = { id: createdId, name, icon: projIcon } as any;
        }
      }
      // Build a project object from server response if available; otherwise a local temp one
      const newProj: Project =
        created && (created as any).id
          ? { id: String((created as any).id), name: (created as any).name ?? name, icon: (created as any).icon ?? projIcon }
          : { id: `local-${Date.now()}`, name, icon: projIcon };

      // Optimistically add so it renders immediately
      setProjectList(prev => {
        const exists = prev.some(p => p.id === newProj.id || p.name === newProj.name);
        return exists ? prev : [newProj, ...prev];
      });
      // Ensure the new project is visible in the list
      setTab("projects");
      setQ("");

      // Persist to cache immediately so it survives route changes
      writeProjectsCache([newProj, ...projectList]);

      // Switch scope to the new project (parent-managed or local fallback)
      setScope(String(newProj.id));

      // Ask server for the latest projects so the new one persists across views
      refreshProjectsFromServer();
      // A tiny delayed refresh helps when the backend writes are eventual
      setTimeout(() => { refreshProjectsFromServer(); }, 600);

      setShowProjectModal(false);
      setProjName("");
      setProjIcon("📁");
    } finally {
      setSavingProject(false);
    }
  }

  // Persist selection: write to localStorage (wrapped in try/catch for SSR safety)
  React.useEffect(() => {
    try {
      localStorage.setItem("cfy.sidebarTab", tab);
    } catch (e) {
      // ignore storage errors in some environments
    }
  }, [tab]);

  /*
   * scopedThreads: derive the list of threads based on current project scope
   * and search query. Keep this synchronous and cheap — used directly in render.
   * Rationale: local filtering avoids extra network calls and preserves snappy UX.
   */
  const pid = onProjectChange ? projectId : localProjectId;
  const scopedThreads = React.useMemo(() => {
    const base = pid === null
      ? threadList.filter(t => !t.projectId)
      : pid
        ? threadList.filter(t => String(t.projectId ?? "") === String(pid))
        : threadList;
    const visible = base.filter((t) => !t.archivedAt);
    if (!q) return visible;
    const s = q.toLowerCase();
    return visible.filter(t => t.title.toLowerCase().includes(s) || (t.lastMessage ?? "").toLowerCase().includes(s));
  }, [threadList, pid, q]);

  // Create a display-only copy that doesn't carry messages[] references
  const displayThreads = React.useMemo(() => {
    const titleMap = stableTitleRef.current;
    const previewMap = previewRef.current;

    const seen = new Set<string>();
    const out: Thread[] = [] as any;

    for (const t of scopedThreads) {
      const id = String(t.id ?? "");
      if (!id || seen.has(id)) continue; // prevent duplicate keys like `t:31`
      seen.add(id);

      const displayTitle = (titleMap.get(id) ?? (t.title ?? "")).toString();
      const preview = (previewMap.get(id) ?? "").toString();

      out.push({
        ...t,
        messages: [],                 // avoid leaking shared arrays
        lastMessage: preview,         // preview comes from our per-id cache
        title: displayTitle || "Untitled",
      } as Thread);
    }

    return out;
  }, [scopedThreads]);

  const looseCount = React.useMemo(() => threadList.filter(t => !t.projectId).length, [threadList]);

  // Accessible segmented control: role=tablist + keyboard navigation for a11y
  // header
  const scopeLabel =
    (() => {
      const pid = onProjectChange ? projectId : localProjectId;
      return pid === null ? "Loose"
        : pid ? (projects.find(p => String(p.id) === String(pid))?.name ?? "Project")
        : "All";
    })();

  const columnClass = collapsed ? "w-full px-2" : "w-full px-[5px]";

  return (
    <div
      className={clsx(
        "flex min-h-0 h-full flex-col gap-3 transition-[width] duration-300",
        collapsed ? "items-center" : "items-stretch"
      )}
      style={{
        color: "var(--text)",
        // background, backdropFilter, WebkitBackdropFilter, borderRadius removed for glass rim
      }}
    >
      {toast && (
        <div
          key={toast.id}
          className="mx-[5px] mt-1 flex items-center gap-2 rounded-xl border px-3 py-2 text-sm shadow-sm backdrop-blur-sm transition-opacity"
          style={{
            background: toast.kind === "success" ? successBg : errorBg,
            borderColor: toast.kind === "success" ? successBorder : errorBorder,
            color: toast.kind === "success" ? accentColor : errorColor,
          }}
        >
          {toast.kind === "success" ? (
            <Check className="h-4 w-4" aria-hidden="true" />
          ) : (
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          )}
          <span className="flex-1 truncate" style={{ color: toast.kind === "success" ? accentColor : errorColor }}>
            {toast.message}
          </span>
        </div>
      )}

      {/* opaque inner sheet */}
      <div
        className="flex flex-col min-h-0 flex-1 gap-3 rounded-[calc(19px-3px)]"
        style={{
          background: "var(--panel-sheet, #1f1f1f)",
          border: "1px solid var(--panel-border, rgba(255,255,255,0.08))",
          color: "inherit",
        }}
      >
        <div className={clsx("flex items-center gap-[14px]", collapsed ? "w-full px-2" : "w-full px-[5px]")}>
          <button type="button" className="icon-inline" aria-label="Collapse sidebar" onClick={handleToggleCollapse}>
            <Menu className="h-5 w-5" />
          </button>
          {!collapsed && (
            <div className="flex-1 flex justify-center mt-[3px]">
              <div className="glass-pill" role="tablist" aria-label="Sidebar tabs">
                <button
                  role="tab"
                  className="pill-tab text-xs"
                  data-state={tab === "threads" ? "active" : undefined}
                  onClick={() => setTab("threads")}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowRight" || e.key === "ArrowDown") setTab("projects");
                  }}
                >
                  Threads
                </button>
                <button
                  role="tab"
                  className="pill-tab text-xs"
                  data-state={tab === "projects" ? "active" : undefined}
                  onClick={() => setTab("projects")}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowLeft" || e.key === "ArrowUp") setTab("threads");
                  }}
                >
                  Projects
                </button>
              </div>
            </div>
          )}
        </div>

        {!collapsed && (
          <>
            <div className={clsx("relative", columnClass, tab === "projects" && "mb-[5px]")}>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 opacity-60" />
              <Input
                className="pl-9 pr-3 h-9 rounded-xl"
                placeholder={tab==="projects" ? "Search projects…" : "Search threads…"}
                value={q}
                onChange={e => setQ(e.target.value)}
                style={{background:"transparent", borderColor:"var(--panel-border)", color:"var(--text)"}}
              />
            </div>

            {tab === "projects" ? (
              <ProjectsList
                projects={projectList}
                q={q}
                looseCount={looseCount}
                currentId={pid}
                onPick={(id) => { setScope(id); setTab("threads"); }}
                onOpenNewProject={() => setShowProjectModal(true)}
                className={clsx("flex-1 min-h-0 mt-[5px]", columnClass)}
              />
            ) : (
              <ThreadsList
                threads={displayThreads}
                activeId={activeId}
                scopeLabel={scopeLabel}
                onSelect={onSelect}
                onNewChat={onNewChat}
                creatingThread={creatingThread}
                onDeleteThread={handleDeleteThreadLocal}
                className={clsx("flex-1 min-h-0", columnClass)}
              />
            )}
          </>
        )}
      {/* end inner sheet */}
      </div>

      {/* New Project Modal */}
      {showProjectModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-[999] flex items-center justify-center"
        >
          {/* backdrop */}
          <div
            className="absolute inset-0"
            style={{ background: "rgba(0,0,0,0.5)" }}
            onClick={() => !savingProject && setShowProjectModal(false)}
          />
          {/* card */}
          <form
            onSubmit={handleCreateProjectSubmit}
            className="relative z-[1000] w-[min(520px,90vw)] rounded-2xl border p-5"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          >
            <div className="mb-4">
              <h3 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
                Create Project
              </h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-sm mb-1 opacity-80" htmlFor="projName">
                  Name
                </label>
                <Input
                  id="projName"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="e.g., Research, Life Admin…"
                  className="rounded-xl"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm mb-1 opacity-80" htmlFor="projIcon">
                  Icon (emoji or short label)
                </label>
                <Input
                  id="projIcon"
                  value={projIcon}
                  onChange={(e) => setProjIcon(e.target.value)}
                  placeholder="📁"
                  className="rounded-xl"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="embedded-btn" onClick={() => setShowProjectModal(false)} disabled={savingProject}>
                Cancel
              </button>
              <button type="submit" className="embedded-btn" disabled={savingProject || !projName.trim()}>
                {savingProject ? "Creating…" : "Create Project"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

/*
 * ProjectsList
 * - Renders the "Loose" scope and user projects as embedded 19px tiles.
 * - Selecting a tile scopes the thread list; the embedded control opens the modal.
 */
function ProjectsList({
  projects, q, looseCount, currentId, onPick, onOpenNewProject, className,
}: {
  projects: Project[];
  q: string;
  looseCount: number;
  currentId: string | null | undefined;
  onPick: (id: string | null) => void;
  onOpenNewProject?: () => void;
  className?: string;
}) {
  const s = q.toLowerCase();
  const filtered = s ? projects.filter(p => p.name.toLowerCase().includes(s)) : projects;

  return (
    <div className={clsx("flex-1 min-h-0 overflow-auto pt-[5px]", className)}>
      <div className="grid auto-rows-[minmax(140px,auto)] grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <ProjectTileCard
          key="__loose"
          label={`Loose threads${looseCount ? ` (${looseCount})` : ""}`}
          icon={<FolderOpen className="h-6 w-6" />}
          active={currentId === null}
          onClick={() => onPick(null)}
        />
        {filtered.map((p) => (
          <ProjectTileCard
            key={p.id}
            label={p.name}
            icon={p.icon}
            active={currentId === String(p.id)}
            onClick={() => onPick(String(p.id))}
          />
        ))}
      </div>
      {onOpenNewProject && (
        <button type="button" className="embedded-btn mt-4 w-full justify-center gap-2" onClick={onOpenNewProject}>
          <PlusCircle className="h-4 w-4" /> New Project
        </button>
      )}
    </div>
  );
}

function ProjectTileCard({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon?: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  const baseIcon = typeof icon === "string" && icon.trim().length <= 2
    ? icon.trim()
    : icon || <FolderOpen className="h-6 w-6" />;
  const iconNode = React.isValidElement(baseIcon)
    ? React.cloneElement(baseIcon as React.ReactElement, {
        className: clsx("project-tile__icon", ((baseIcon as React.ReactElement).props as any)?.className),
      })
    : <span className="project-tile__icon">{baseIcon}</span>;
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx("project-tile", active && "project-tile--active")}
      aria-pressed={active}
    >
      {iconNode}
      <span className="project-tile__label">{label}</span>
    </button>
  );
}

/*
 * ThreadsList
 * - Renders threads with FrameCard to maintain the app's visual language.
 * - Each item is a button: we set title/aria attributes and ensure keyboard access.
 * - If you add actions (delete, rename), keep them small and behind a context menu
 *   to avoid accidental taps on mobile.
 * - Performance: if threads length grows >200, introduce virtualization.
 */

export function ThreadTileRow({
  thread,
  active,
  onSelect,
  rectH = 60,
  className,
  onDeleteThread,
}: {
  thread: Thread;
  active: boolean;
  onSelect: (id: string) => void;
  rectH?: number;
  className?: string;
  onDeleteThread?: (threadId: string) => void;
}) {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement | null>(null);
  const kebabRef = React.useRef<HTMLButtonElement | null>(null);

  const [actionBusy, setActionBusy] = React.useState<ThreadAction | null>(null);
  const [hoveredAction, setHoveredAction] = React.useState<ThreadAction | null>(null);

  const accentColor = React.useMemo(() => getComputedStyleVar("--accent", "#6B7280"), []);
  const textColor = React.useMemo(() => getComputedStyleVar("--text", "#F9FAFB"), []);
  const highlightBg = React.useMemo(
    () => colorStringToRgba(accentColor, 0.18, "rgba(107,114,128,0.18)"),
    [accentColor]
  );
  const highlightBorder = React.useMemo(
    () => colorStringToRgba(accentColor, 0.45, "rgba(107,114,128,0.45)"),
    [accentColor]
  );

  const makeMenuStyle = React.useCallback(
    (action: ThreadAction) => {
      const activeState = hoveredAction === action || actionBusy === action;
      return {
        color: activeState ? accentColor : textColor,
        background: activeState ? highlightBg : "transparent",
        borderColor: activeState ? highlightBorder : "transparent",
      } as React.CSSProperties;
    },
    [accentColor, actionBusy, highlightBg, highlightBorder, hoveredAction, textColor]
  );

  // Close the menu on outside click or ESC
  React.useEffect(() => {
    function handleDocMouseDown(e: MouseEvent) {
      if (!menuOpen) return;
      const t = e.target as Node;
      if (menuRef.current?.contains(t)) return;
      if (kebabRef.current?.contains(t)) return;
      setMenuOpen(false);
      setHoveredAction(null);
    }
    function handleEsc(e: KeyboardEvent) {
      if (!menuOpen) return;
      if (e.key === "Escape") {
        setMenuOpen(false);
        setHoveredAction(null);
      }
    }
    document.addEventListener("mousedown", handleDocMouseDown);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleDocMouseDown);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [menuOpen]);

  function stop(e: React.MouseEvent): boolean {
    e.stopPropagation();
    e.preventDefault();
    return Boolean(actionBusy);
  }

  async function handleRename(e: React.MouseEvent) {
    if (stop(e)) return;
    const next = window.prompt("Rename thread", thread.title?.trim() || "");
    const title = next?.trim();
    if (!title || title === thread.title) { setMenuOpen(false); setHoveredAction(null); return; }
    setHoveredAction("rename");
    setActionBusy("rename");
    try {
      await threadApi("patch", thread.id, { title });
      // hint the rest of the app that this thread changed
      emitThreadsRefresh("rename", { id: thread.id, title });
      emitToast("success", "Thread renamed");
    } catch (err) {
      console.error("rename failed", err);
      emitToast("error", "Rename failed. Please try again.");
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }

  async function handleArchiveToggle(e: React.MouseEvent) {
    if (stop(e)) return;
    const isArchived = Boolean(thread.archivedAt);
    setHoveredAction("archive");
    setActionBusy("archive");
    try {
      await threadApi("patch", thread.id, { archived: !isArchived });
      // Optimistically remove from list when archiving, since archived threads are hidden
      if (!isArchived && onDeleteThread) onDeleteThread(thread.id);
      emitThreadsRefresh(isArchived ? "unarchive" : "archive", { id: thread.id, archived: !isArchived });
      emitToast("success", isArchived ? "Thread restored" : "Thread archived");
    } catch (err) {
      console.error("archive toggle failed", err);
      emitToast("error", `${isArchived ? "Unarchive" : "Archive"} failed. Please try again.`);
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }

  async function handleDelete(e: React.MouseEvent) {
    if (stop(e)) return;
    const ok = window.confirm("Delete this thread and its messages? This cannot be undone.");
    if (!ok) { setMenuOpen(false); setHoveredAction(null); return; }
    setHoveredAction("delete");
    setActionBusy("delete");
    try {
      await threadApi("delete", thread.id);
      if (onDeleteThread) onDeleteThread(thread.id);
      emitThreadsRefresh("delete", { id: thread.id });
      emitToast("success", "Thread deleted");
    } catch (err: any) {
      console.error("delete failed", err);
      const status = err?.response?.status;
      emitToast("error", `Delete failed${status ? ` (${status})` : ""}. Please try again.`);
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }

  const threadIsArchived = Boolean(thread.archivedAt);

  const renameIcon = actionBusy === "rename"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : <Pencil className="h-4 w-4" aria-hidden="true" />;

  const archiveIconNode = actionBusy === "archive"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : threadIsArchived
      ? <ArchiveRestore className="h-4 w-4" aria-hidden="true" />
      : <ArchiveIcon className="h-4 w-4" aria-hidden="true" />;

  const deleteIcon = actionBusy === "delete"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : <Trash2 className="h-4 w-4" aria-hidden="true" />;

  // Provide a safe fallback for empty/whitespace-only titles
  const safeTitle = (thread.title || "").trim() || "Untitled";
  const titleNode = (
    <span key="title" className="thread-title block truncate" title={safeTitle}>
      {safeTitle}
    </span>
  );
  // Build a per-thread snippet: prefer thread.lastMessage, otherwise last message content
  // Only derive the preview from lastMessage to avoid shared messages[] mirroring
  const snippet =
    typeof thread.lastMessage === "string"
      ? thread.lastMessage.trim()
      : "";
  const snippetNode = (
    <span
      key="snippet"
      className="thread-snippet block truncate"
      title={snippet || undefined}
    >
      {snippet || "\u00a0"}
    </span>
  );
  const unreadBadge =
    thread.unread > 0 ? (
      <span
        key="badge"
        className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-2 text-xs font-semibold"
        style={{ background: "var(--accent-strong)", color: "#fff" }}
      >
        {thread.unread}
      </span>
    ) : null;

  const payload = unreadBadge ? [titleNode, snippetNode, unreadBadge] : [titleNode, snippetNode];

  return (
    <div className={clsx("relative", className)}>
      <PreviewTile
        active={active}
        onClick={() => onSelect(thread.id)}
        className="thread-preview w-full"
        tone="panel"
        rectH={rectH}
      >
        {payload}
      </PreviewTile>

      {/* Kebab menu button (top-right) */}
      <div className="absolute top-1 right-1">
        <button
          ref={kebabRef}
          className="icon-inline"
          aria-label="Thread actions"
          onClick={(e) => { if (stop(e)) return; setMenuOpen(true); setHoveredAction(null); }}
          onMouseDown={(e) => stop(e)}
          type="button"
          aria-busy={actionBusy ? true : undefined}
        >
          <MoreVertical className="h-4 w-4" />
        </button>
      </div>

      {/* Simple popover menu */}
      {menuOpen && (
        <div
          ref={menuRef}
          role="menu"
          tabIndex={-1}
          className="absolute z-[9999] right-1 top-9 min-w-[180px] rounded-xl border p-1 shadow-xl pointer-events-auto backdrop-blur-sm"
          style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("rename")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("rename")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "rename" ? null : prev))}
            onFocus={() => setHoveredAction("rename")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "rename" ? null : prev))}
            onClick={handleRename}
            disabled={Boolean(actionBusy)}
          >
            {renameIcon}
            Rename
          </button>
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("archive")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("archive")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "archive" ? null : prev))}
            onFocus={() => setHoveredAction("archive")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "archive" ? null : prev))}
            onClick={handleArchiveToggle}
            disabled={Boolean(actionBusy)}
          >
            {archiveIconNode}
            {threadIsArchived ? "Unarchive" : "Archive"}
          </button>
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("delete")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("delete")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "delete" ? null : prev))}
            onFocus={() => setHoveredAction("delete")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "delete" ? null : prev))}
            onClick={handleDelete}
            disabled={Boolean(actionBusy)}
          >
            {deleteIcon}
            Delete…
          </button>
        </div>
      )}
    </div>
  );
}

export function ThreadPreviewList({
  threads,
  activeId,
  onSelect,
  className,
  rectH = 60,
  showHeader = false,
  scopeLabel,
  onNewChat,
  onDeleteThread,
}: {
  threads: Thread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  className?: string;
  rectH?: number;
  showHeader?: boolean;
  scopeLabel?: string;
  onNewChat?: () => void;
  onDeleteThread?: (threadId: string) => void;
}) {
  return (
    <div className={clsx("flex-1 min-h-0 overflow-y-auto", className)}>
      {showHeader && (
        <div className="flex items-center justify-between pb-2 px-[5px]">
          <div className="inline-flex items-center gap-1 text-xs opacity-70">
            <ChevronDown className="h-3 w-3" /> <span>Scope:</span>{" "}
            <span className="font-medium">{scopeLabel ?? "—"}</span>
          </div>
          {onNewChat && (
            <button type="button" className="icon-inline" onClick={onNewChat}>
              <Plus className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
      <div className="space-y-2">
        {threads.map((t, idx) => (
          <ThreadTileRow
            key={t.id != null && String(t.id) ? `t:${String(t.id)}` : `t:temp:${idx}`}
            thread={t}
            active={t.id === activeId}
            onSelect={onSelect}
            rectH={rectH}
            onDeleteThread={onDeleteThread}
          />
        ))}
      </div>
    </div>
  );
}

function ThreadsList({
  threads, activeId, scopeLabel, onSelect, onNewChat,
  creatingThread,
  onDeleteThread,
  className,
}: {
  threads: Thread[];
  activeId: string | null;
  scopeLabel: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  creatingThread?: boolean;
  onDeleteThread?: (threadId: string) => void;
  className?: string;
}) {
  return (
    <ThreadPreviewList
      threads={threads}
      activeId={activeId}
      onSelect={onSelect}
      className={className}
      rectH={60}
      showHeader
      scopeLabel={scopeLabel}
      onNewChat={onNewChat}
      onDeleteThread={onDeleteThread}
    />
  );
}
