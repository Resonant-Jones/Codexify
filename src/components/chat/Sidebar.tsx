import * as React from "react";
import { Search, Plus, ChevronDown, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import PreviewTile from "@/components/ui/PreviewTile";
import { DocChip } from "@/components/layout/WorkspacePane";
// removed unused: deleteProject, deleteThread

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
 * - `LayeredCard` is used as a visual wrapper for threads to preserve the app's
 *   glass / layered aesthetic and consistent elevation. Avoid wrapping multiple
 *   cards in a single outer rounded container to prevent clipping of shadows/blur.
 *
 * Notes for future us:
 * - If thread lists grow very large, consider virtualization (e.g. react-window)
 *   to maintain snappy scroll performance.
 * - Avoid persisting large binary blobs or generated artifacts in this component.
 */

type Project = { id: string; name: string; color?: string; icon?: string };

type Message = { id: string; authorId: string; authorName: string; content: string; createdAt: number; status?: "sending"|"sent"|"delivered"|"read" };
type Thread = { id: string; title: string; lastMessage: string; unread: number; participants: Array<{id:string;name:string}>; messages: Message[]; projectId?: string | null };

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
}: Props) {
  // Persisted tab state: keeps user context across refreshes. Key: cfy.sidebarTab
  const [tab, setTab] = React.useState<"threads"|"projects">(() =>
    (typeof window === "undefined" ? "threads" : ((localStorage.getItem("cfy.sidebarTab") as any) || "threads"))
  );
  const [q, setQ] = React.useState("");

  // Local collapse state fallback if no handler passed
  const [collapsed, setCollapsed] = React.useState(false);
  const handleToggleCollapse = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setCollapsed(!collapsed);
    }
  };

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
  const scopedThreads = React.useMemo(() => {
    const base = projectId === null
      ? threads.filter(t => !t.projectId)
      : projectId ? threads.filter(t => t.projectId === projectId) : threads;
    if (!q) return base;
    const s = q.toLowerCase();
    return base.filter(t => t.title.toLowerCase().includes(s) || (t.lastMessage ?? "").toLowerCase().includes(s));
  }, [threads, projectId, q]);

  const looseCount = React.useMemo(() => threads.filter(t => !t.projectId).length, [threads]);

  // Accessible segmented control: role=tablist + keyboard navigation for a11y
  // header
  const scopeLabel =
    projectId === null ? "Loose"
    : projectId ? (projects.find(p => p.id === projectId)?.name ?? "Project")
    : "All";

  return (
    <div
      className="flex min-h-0 w-full flex-col p-[6px] gap-2"
      style={{
        color: "var(--text)",
        height: "var(--card-height)"
      }}
    >
      <div className="flex items-center gap-2">
        {/* Segmented tabs — accessible + sliding indicator */}
      <div
        role="tablist"
        aria-label="Sidebar tabs"
        className="relative inline-grid grid-cols-2 gap-1 rounded-xl border p-2 max-w-full flex-shrink-0" // added overflow protection
        style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)", minWidth: "240px" }} // increased minWidth for more horizontal space
      >
          {/* sliding indicator */}
          <div
            aria-hidden="true"
            className="absolute top-1 left-1 h-[calc(100%-0.5rem)] w-[calc(50%-0.5rem)] rounded-lg transition-transform duration-200 flex-grow"
            style={{
              background: "var(--chip-bg)",
              transform: tab === "threads" ? "translateX(0%)" : "translateX(100%)",
            }}
          />

          <button
            role="tab"
            aria-selected={tab === "threads"}
            tabIndex={tab === "threads" ? 0 : -1}
            onClick={() => setTab("threads")}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight" || e.key === "ArrowDown") setTab("projects");
              if (e.key === "ArrowLeft" || e.key === "ArrowUp") setTab("threads");
            }}
            className={`relative z-10 rounded-lg py-1.5 text-sm flex-grow ${tab === "threads" ? "font-semibold" : "opacity-80"}`} // added flex-grow
            style={tab === "threads" ? { color: "var(--text)" } : undefined}
          >
            Threads
          </button>

          <button
            role="tab"
            aria-selected={tab === "projects"}
            tabIndex={tab === "projects" ? 0 : -1}
            onClick={() => setTab("projects")}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight" || e.key === "ArrowDown") setTab("projects");
              if (e.key === "ArrowLeft" || e.key === "ArrowUp") setTab("threads");
            }}
            className={`relative z-10 rounded-lg py-1.5 text-sm flex-grow ${tab === "projects" ? "font-semibold" : "opacity-80"}`} // added flex-grow
            style={tab === "projects" ? { color: "var(--text)" } : undefined}
          >
            Projects
          </button>
        </div>
      </div>

      {/* Search */}
      {/* Search: client-side filter on title and last message. Consider debounce if input becomes noisy. */}
      <div className="relative">
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
          projects={projects}
          q={q}
          looseCount={looseCount}
          currentId={projectId}
          onPick={(id) => {
            onProjectChange?.(id);
            setTab("threads");
          }}
        />
      ) : (
        <ThreadsList
          threads={scopedThreads}
          activeId={activeId}
          scopeLabel={scopeLabel}
          onSelect={onSelect}
          onNewChat={onNewChat}
          creatingThread={creatingThread}
          onDeleteThread={onDeleteThread}
        />
      )}
    </div>
  );
}

/*
 * ProjectsList
 * - Renders the project chips and a "Loose threads" pseudo-project.
 * - Clicking a project sets the scope; New Project is a client-side affordance.
 * - Keep DocChip usage consistent with workspace styling for visual alignment.
 */
function ProjectsList({
  projects, q, looseCount, currentId, onPick,
}: {
  projects: Project[];
  q: string;
  looseCount: number;
  currentId: string | null | undefined;
  onPick: (id: string | null) => void;
}) {
  const s = q.toLowerCase();
  const filtered = s ? projects.filter(p => p.name.toLowerCase().includes(s)) : projects;

  return (
    <div className="flex-1 min-h-0 overflow-auto space-y-2 px-[6px]">
      {/* Loose pseudo-project as a BIG doc chip */}
      <DocChip
        className="w-full"
        label={`Loose threads${looseCount ? ` (${looseCount})` : ""}`}
        onClick={() => onPick(null)}
        active={currentId === null}
      />

      {/* All projects rendered as BIG doc chips */}
      {filtered.map((p) => (
        <DocChip
          key={p.id}
          className="w-full"
          label={p.name}
          onClick={() => onPick(p.id)}
          active={currentId === p.id}
        />
      ))}

      {/* New Project */}
      <Button size="sm" className="w-full rounded-xl mt-2" variant="ghost" onClick={() => onPick(null)}>
        <Plus className="h-4 w-4 mr-1" /> New Project
      </Button>
    </div>
  );
}

/*
 * ThreadsList
 * - Renders threads as LayeredCard items to maintain the app's visual language.
 * - Each item is a button: we set title/aria attributes and ensure keyboard access.
 * - If you add actions (delete, rename), keep them small and behind a context menu
 *   to avoid accidental taps on mobile.
 * - Performance: if threads length grows >200, introduce virtualization.
 */
function ThreadsList({
  threads, activeId, scopeLabel, onSelect, onNewChat,
  creatingThread,
  onDeleteThread,
}: {
  threads: Thread[];
  activeId: string | null;
  scopeLabel: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  creatingThread?: boolean;
  onDeleteThread?: (threadId: string) => void;
}) {
  return (
    <div className="flex-1 min-h-0 overflow-auto px-[6px]">
      <div className="flex items-center justify-between px-1 pb-2">
        <div className="inline-flex items-center gap-1 text-xs opacity-70">
          <ChevronDown className="h-3 w-3" /> <span>Scope:</span> <span className="font-medium">{scopeLabel}</span>
        </div>
        <Button size="icon" variant="ghost" className="rounded-xl" onClick={onNewChat}><Plus className="h-4 w-4" /></Button>
      </div>
      <div className="space-y-2">
        {threads.map((t) => (
          <PreviewTile key={t.id} tone="panel" active={t.id===activeId} onClick={() => onSelect(t.id)} className="w-full">
            <div className="flex items-center justify-between gap-2" title={t.lastMessage}>
              <div className="min-w-0">
                <div className="font-medium truncate">{t.title}</div>
                <div className="text-xs opacity-70 truncate">{t.lastMessage || " "}</div>
              </div>
              {t.unread > 0 && (
                <span className="ml-2 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-2 text-xs font-semibold" style={{ background: "var(--accent-strong)", color: "#fff" }}>
                  {t.unread}
                </span>
              )}
            </div>
          </PreviewTile>
        ))}
      </div>
    </div>
  );
}
