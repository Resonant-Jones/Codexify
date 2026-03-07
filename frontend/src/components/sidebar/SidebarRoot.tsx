import * as React from "react";
import clsx from "clsx";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import ThreadList from "./ThreadList";
import ProjectList from "./ProjectList";
import CreateProjectModal from "./CreateProjectModal";
import useSidebarThreads from "./useSidebarThreads";
import useProjectsCache from "./useProjectsCache";
import { useLegacyThreads } from "@/contexts/LegacyThreadsContext";
import api from "@/lib/api";

type ToastMessage = { kind: "success" | "error"; message: string };
type ActiveToast = ToastMessage & { id: number };

type Props = {
  threads: Thread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  projectId?: string | null;
  onProjectChange?: (id: string | null) => void;
  projects?: Project[];
  creatingThread?: boolean;
  hasMoreThreads?: boolean;
  loadingMoreThreads?: boolean;
  onLoadMoreThreads?: () => void | Promise<void>;
  onDeleteThread?: (threadId: string) => void;
  onCreateProject?: (data: { name: string; icon?: string; color?: string }) => Promise<Project | void> | Project | void;
};

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

const SIDEBAR_RAIL = "px-3";

export default function SidebarRoot({
  threads,
  activeId,
  onSelect,
  onNewChat,
  projectId = null,
  onProjectChange,
  projects = [],
  creatingThread,
  hasMoreThreads = false,
  loadingMoreThreads = false,
  onLoadMoreThreads,
  onDeleteThread,
  onCreateProject,
}: Props) {
  const [tab, setTab] = React.useState<"threads" | "projects">(() =>
    (typeof window === "undefined" ? "threads" : ((localStorage.getItem("cfy.sidebarTab") as any) || "threads"))
  );
  const [q, setQ] = React.useState("");
  const { enabled: legacyEnabled, open: openLegacy } = useLegacyThreads();
  const [toast, setToast] = React.useState<ActiveToast | null>(null);
  const [showProjectModal, setShowProjectModal] = React.useState(false);
  const [savingProject, setSavingProject] = React.useState(false);
  const [projectModalError, setProjectModalError] = React.useState<string | null>(null);

  const {
    threads: sidebarThreads,
    displayThreads,
    scopeLabel: hookScopeLabel,
    currentProjectId,
    setScope,
    renameThread,
    toggleArchiveThread,
    deleteThread,
  } = useSidebarThreads({ initialThreads: threads, projectId, onProjectChange });

  const {
    projectList,
    setProjectList,
    refreshProjectsFromServer,
  } = useProjectsCache({ initialProjects: projects, threadsForLooseCount: sidebarThreads });

  const scopeLabel = React.useMemo(() => {
    if (currentProjectId === null) return "General";
    if (currentProjectId) {
      const proj = projectList.find((p) => String(p.id) === String(currentProjectId));
      return proj?.name ?? hookScopeLabel;
    }
    return hookScopeLabel;
  }, [currentProjectId, hookScopeLabel, projectList]);

  React.useEffect(() => {
    if (currentProjectId !== null) return;
    const defaultProject = projectList.find((project) =>
      isDefaultProjectAlias(project?.name)
    );
    if (!defaultProject?.id) return;
    setScope(String(defaultProject.id));
  }, [currentProjectId, projectList, setScope]);

  const columnClass = clsx("w-full", SIDEBAR_RAIL);

  const accentColor = React.useMemo(() => getComputedStyleVar("--accent", "#6B7280"), []);
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

  React.useEffect(() => {
    try {
      localStorage.setItem("cfy.sidebarTab", tab);
    } catch {
      /* ignore */
    }
  }, [tab]);

  const filteredThreads = React.useMemo(() => {
    if (!q) return displayThreads;
    const s = q.toLowerCase();
    return displayThreads.filter(
      (t) => t.title.toLowerCase().includes(s) || (t.lastMessage ?? "").toLowerCase().includes(s)
    );
  }, [displayThreads, q]);

  const handleDelete = React.useCallback(
    async (id: string) => {
      await deleteThread(id);
      try {
        onDeleteThread?.(id);
      } catch {
        /* ignore */
      }
    },
    [deleteThread, onDeleteThread]
  );

  const handleArchiveToggle = React.useCallback(
    async (id: string, archived: boolean) => {
      await toggleArchiveThread(id, archived);
      if (archived) {
        try {
          onDeleteThread?.(id);
        } catch {
          /* ignore */
        }
      }
    },
    [onDeleteThread, toggleArchiveThread]
  );

  const handleCreateProject = React.useCallback(
    async (data: { name: string; icon?: string; color?: string }) => {
      const name = data.name.trim();
      if (!name) {
        setProjectModalError("Project name is required.");
        return;
      }
      setSavingProject(true);
      setProjectModalError(null);
      try {
        let created: Project | void | undefined;
        if (onCreateProject) {
          created = await onCreateProject(data);
        } else {
          const icon = data.icon?.trim() || "📁";
          const resp = await api.post("/api/projects", { name, icon, description: "" });
          const payload = resp?.data ?? {};
          const createdId = payload?.id ?? payload?.project_id;
          if (createdId) {
            created = { id: String(createdId), name, icon };
          }
        }
        const newProj: Project =
          created && (created as any).id
            ? { id: String((created as any).id), name: (created as any).name ?? name, icon: (created as any).icon ?? data.icon }
            : { id: `local-${Date.now()}`, name, icon: data.icon?.trim() || "📁" };

        setProjectList((prev) => {
          const exists = prev.some((p) => p.id === newProj.id || p.name === newProj.name);
          return exists ? prev : [newProj, ...prev];
        });

        setTab("projects");
        setQ("");
        setScope(String(newProj.id));
        setShowProjectModal(false);
        await refreshProjectsFromServer();
        setTimeout(() => { void refreshProjectsFromServer(); }, 600);
      } catch (err: any) {
        const message =
          err?.response?.data?.message
          || err?.response?.data?.detail
          || err?.message
          || "Failed to create project.";
        setProjectModalError(message);
      } finally {
        setSavingProject(false);
      }
    },
    [onCreateProject, refreshProjectsFromServer, setScope, setProjectList]
  );

  return (
    <div
      className={clsx(
        "flex min-h-0 h-full flex-col gap-3 transition-[width] duration-300",
        "items-stretch"
      )}
      style={{ color: "var(--text)" }}
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
          <span className="flex-1 truncate" style={{ color: toast.kind === "success" ? accentColor : errorColor }}>
            {toast.message}
          </span>
        </div>
      )}

      <div
        className="flex flex-col min-h-0 flex-1 gap-3 rounded-[var(--card-radius)]"
        style={{
          background: "var(--panel-sheet, #1f1f1f)",
          border: "1px solid transparent",
          color: "inherit",
          overflow: "hidden",
        }}
      >
        <div className={clsx("flex items-center gap-[14px] w-full", SIDEBAR_RAIL)}>
          <div className="flex-1 flex justify-center mt-[3px]">
            <div className="glass-pill" role="tablist" aria-label="Sidebar tabs">
              <button
                role="tab"
                className="pill-tab text-xs"
                data-testid="sidebar-threads-tab"
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
                data-testid="sidebar-projects-tab"
                data-state={tab === "projects" ? "active" : undefined}
                onClick={() => setTab("projects")}
                onKeyDown={(e) => {
                  if (e.key === "ArrowLeft" || e.key === "ArrowUp") setTab("threads");
                }}
              >
                Projects
              </button>
            </div>
            {legacyEnabled && (
              <button
                type="button"
                className="pill-tab text-xs ml-2"
                onClick={openLegacy}
                title="Browse legacy conversation trees"
              >
                Legacy
              </button>
            )}
          </div>
        </div>

        <div className={clsx(columnClass, tab === "projects" && "mb-[5px]")}>
          <div className="relative">
            <div
              data-testid="sidebar-search-icon"
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 opacity-60"
              aria-hidden="true"
            >
              <Search className="h-4 w-4" />
            </div>
            <Input
              data-testid="sidebar-search-input"
              className="h-10 w-full rounded-xl pl-10 pr-3 bg-[var(--chip-bg)] border border-white/10"
              placeholder={tab === "projects" ? "Search projects…" : "Search threads…"}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              style={{ color: "var(--text)" }}
            />
          </div>
        </div>

        {tab === "projects" ? (
          <ProjectList
            projects={projectList}
            search={q}
            currentId={currentProjectId}
            onPick={(id) => { setScope(id); setTab("threads"); }}
            onOpenNewProject={() => {
              setProjectModalError(null);
              setShowProjectModal(true);
            }}
            className={clsx("flex-1 min-h-0 mt-[5px]", columnClass)}
          />
        ) : (
          <ThreadList
            threads={filteredThreads}
            activeId={activeId}
            scopeLabel={scopeLabel}
            onSelect={onSelect}
            onNewChat={onNewChat}
            creatingThread={creatingThread}
            hasMore={hasMoreThreads}
            isLoadingMore={loadingMoreThreads}
            onLoadMore={onLoadMoreThreads}
            onRename={renameThread}
            onArchiveToggle={handleArchiveToggle}
            onDelete={handleDelete}
            className={clsx("flex-1 min-h-0", columnClass)}
          />
        )}
      </div>

      <CreateProjectModal
        open={showProjectModal}
        onClose={() => {
          if (savingProject) return;
          setShowProjectModal(false);
          setProjectModalError(null);
        }}
        onCreateProject={handleCreateProject}
        isSaving={savingProject}
        error={projectModalError}
      />
    </div>
  );
}
