import * as React from "react";
import { Search, Plus, ChevronDown, Folder, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import LayeredCard from "@/components/ui/LayeredCard";
import { DocChip } from "@/components/layout/WorkspacePane";
import { deleteProject, deleteThread } from "@/api";

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
}: Props) {
  const [tab, setTab] = React.useState<"threads"|"projects">("threads");
  const [q, setQ] = React.useState("");

  // derived lists
  const scopedThreads = React.useMemo(() => {
    const base = projectId === null
      ? threads.filter(t => !t.projectId)
      : projectId ? threads.filter(t => t.projectId === projectId) : threads;
    if (!q) return base;
    const s = q.toLowerCase();
    return base.filter(t => t.title.toLowerCase().includes(s) || (t.lastMessage ?? "").toLowerCase().includes(s));
  }, [threads, projectId, q]);

  const looseCount = React.useMemo(() => threads.filter(t => !t.projectId).length, [threads]);

  // header
  const scopeLabel =
    projectId === null ? "Loose"
    : projectId ? (projects.find(p => p.id === projectId)?.name ?? "Project")
    : "All";

  return (
    <div className="flex h-full w-full flex-col p-2 gap-2" style={{color:"var(--text)"}}>
      {/* Segmented tabs */}
      <div className="grid grid-cols-2 gap-1 rounded-xl border p-1" style={{borderColor:"var(--panel-border)", background:"var(--panel-bg)"}}>
        <button
          className={`rounded-lg py-1.5 text-sm ${tab==="threads" ? "font-semibold shadow" : "opacity-80"}`}
          style={tab==="threads" ? {background:"var(--chip-bg)"} : undefined}
          onClick={() => setTab("threads")}
        >Threads</button>
        <button
          className={`rounded-lg py-1.5 text-sm ${tab==="projects" ? "font-semibold shadow" : "opacity-80"}`}
          style={tab==="projects" ? {background:"var(--chip-bg)"} : undefined}
          onClick={() => setTab("projects")}
        >Projects</button>
      </div>

      {/* Search */}
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
    <div className="flex-1 min-h-0 overflow-auto space-y-2">
      {/* Loose pseudo-project as a BIG chip */}
      <DocChip
        label={`Loose threads${looseCount ? ` (${looseCount})` : ""}`}
        onClick={() => onPick(null)}
        active={currentId === null}
      />

      {/* All projects rendered as BIG chips */}
      {filtered.map((p) => (
        <DocChip
          key={p.id}
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
    <div className="flex-1 min-h-0 overflow-auto">
      <div className="flex items-center justify-between px-1 pb-2">
        <div className="inline-flex items-center gap-1 text-xs opacity-70">
          <ChevronDown className="h-3 w-3" /> <span>Scope:</span> <span className="font-medium">{scopeLabel}</span>
        </div>
        <Button size="icon" variant="ghost" className="rounded-xl" onClick={onNewChat}><Plus className="h-4 w-4" /></Button>
      </div>
      <div className="space-y-2">
        {threads.map((t) => (
          <LayeredCard className="w-full rounded-2xl p-[3px]" key={t.id}>
            <button
              onClick={() => onSelect(t.id)}
              className={`w-full text-left rounded-xl border px-3 py-2 transition ${t.id===activeId ? "ring-1" : ""}`}
              style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)", color: "var(--text)" }}
              title={t.lastMessage}
            >
              <div className="flex items-center justify-between">
                <div className="font-medium truncate">{t.title}</div>
                {t.unread > 0 && (
                  <span className="ml-2 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-green-600/90 text-white text-xs px-1">
                    {t.unread}
                  </span>
                )}
              </div>
              <div className="text-xs opacity-70 truncate">{t.lastMessage}</div>
            </button>
          </LayeredCard>
        ))}
      </div>
    </div>
  );
}
