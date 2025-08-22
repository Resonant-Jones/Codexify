import { useMemo, useState, useEffect } from "react";
import {
  Files, MessageSquare, Folder, ChevronRight, ChevronLeft,
  Image as ImageIcon, FileText
} from "lucide-react";

export type Project = { id: string; name: string };
export type Thread  = { id: string; projectId?: string | null; title: string; unread?: number };
export type Asset   = { id: string; threadId: string; kind: "doc" | "img"; name: string; ext?: string; src?: string };

type ContentMode = "overview" | "docs";

export default function RightRail({
  projects = [],
  threads = [],
  assets = [],
  selectedProjectId,
  selectedThreadId,
  onSelectProject,
  onSelectThread,
  onOpenProjects,
  open,
  onToggle
}: {
  projects?: Project[];
  threads?: Thread[];
  assets?: Asset[];
  selectedProjectId?: string | null;
  selectedThreadId?: string | null;
  onSelectProject: (id: string) => void;
  onSelectThread: (id: string) => void;
  onOpenProjects: () => void;
  open: boolean;
  onToggle: (next: boolean) => void;
}) {
  const [mode, setMode] = useState<ContentMode>("overview");

  useEffect(() => {
    setMode("overview");
  }, [selectedProjectId, selectedThreadId]);

  const frosted = useMemo(() => ({
    background: "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)",
    backdropFilter: "blur(12px) saturate(120%)",
    WebkitBackdropFilter: "blur(12px) saturate(120%)",
    borderColor: "var(--panel-border)",
    boxShadow: "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.25), 0 10px 22px rgba(0,0,0,0.25)"
  }), []);

  return (
    <aside
      className={`relative hidden lg:flex flex-col w-[320px] shrink-0 rounded-3xl border overflow-hidden ${open ? "" : "lg:hidden"}`}
      style={frosted}
      aria-label="WorkSpace rail"
    >
      <div className="relative flex items-center justify-between px-3 py-2">
        <div
          className="absolute left-0 right-0 top-0 h-px"
          style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)" }}
          aria-hidden="true"
        />
        <div
          className="absolute left-0 right-0 bottom-0 h-px"
          style={{ background: "linear-gradient(90deg, transparent, rgba(0,0,0,0.35), transparent)" }}
          aria-hidden="true"
        />
        <div className="text-xs font-semibold opacity-80" style={{ color: "var(--text)" }}>WorkSpace</div>
        <button className="rounded-lg px-2 py-1 hover:opacity-90" style={{ color: "var(--text)" }} onClick={() => onToggle(!open)} aria-label={open ? "Hide rail" : "Show rail"}>
          {open ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <div className="px-3 py-2 flex items-center gap-2 border-b" style={{ borderColor: "var(--panel-border)" }}>
        <TabButton active={mode === "overview"} onClick={() => setMode("overview")} icon={<Files size={14} />}>WorkSpace</TabButton>
        <TabButton active={false} onClick={() => onOpenProjects()} icon={<Folder size={14} />}>Projects</TabButton>
        <TabButton active={mode === "docs"} onClick={() => setMode("docs")} icon={<FileText size={14} />}>Docs</TabButton>
      </div>

      <RailBody
        projects={projects}
        threads={threads}
        assets={assets}
        selectedProjectId={selectedProjectId}
        selectedThreadId={selectedThreadId}
        mode={mode}
        onSelectProject={onSelectProject}
        onSelectThread={onSelectThread}
      />
    </aside>
  );
}

function TabButton({ active, onClick, children, icon }: {
  active: boolean; onClick: () => void; children: string; icon: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${active ? "bg-white/10" : "hover:bg-white/5"}`}
      style={{ color: "var(--text)" }}
    >
      {icon}{children}
    </button>
  );
}

function RailBody({
  projects, threads, assets, selectedProjectId, selectedThreadId, mode, onSelectProject, onSelectThread
}: {
  projects: Project[]; threads: Thread[]; assets: Asset[];
  selectedProjectId?: string | null; selectedThreadId?: string | null;
  mode: "overview" | "docs";
  onSelectProject: (id: string) => void; onSelectThread: (id: string) => void;
}) {
  const project = projects.find(p => p.id === selectedProjectId);
  const projectThreads = threads.filter(t => (selectedProjectId ? t.projectId === selectedProjectId : true));
  const thread = threads.find(t => t.id === selectedThreadId);

  return (
    <div className="flex-1 overflow-auto p-3 space-y-3">
      <Breadcrumb project={project?.name} thread={thread?.title}
        onBackProject={() => onSelectProject("")} onBackThread={() => onSelectThread("")} />

      {!thread && (
        <>
          <h4 className="text-xs uppercase opacity-70">Threads</h4>
          <div className="grid gap-2">
            {projectThreads.length ? projectThreads.map(t => (
              <button key={t.id} onClick={() => onSelectThread(t.id)}
                className="w-full text-left rounded-xl border px-3 py-2 hover:bg-white/5"
                style={{ borderColor: "var(--panel-border)" }}>
                <span className="inline-flex items-center gap-2">
                  <MessageSquare size={14} /><span className="truncate">{t.title}</span>
                </span>
                {t.unread ? <span className="ml-2 text-[10px] rounded-full px-1.5 bg-white/10">{t.unread}</span> : null}
              </button>
            )) : <EmptyState title="No threads yet" hint="Start a new conversation" />}
          </div>
        </>
      )}

      {thread && mode === "overview" && (
        <>
          <h4 className="text-xs uppercase opacity-70">Assets</h4>
          <div className="grid grid-cols-2 gap-2">
            {assets.filter(a => a.threadId === thread.id).map(a => (
              <div key={a.id} className="rounded-xl border p-2"
                style={{ borderColor: "var(--panel-border)", background: "var(--chip-bg)" }}>
                <div className="flex items-center gap-2">
                  {a.kind === "img" ? <ImageIcon size={14} /> : <Files size={14} />}
                  <span className="truncate text-sm">{a.name}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {thread && mode === "docs" && (
        <>
          <h4 className="text-xs uppercase opacity-70">Documents</h4>
          <div className="grid gap-2">
            {assets.filter(a => a.threadId === thread.id && a.kind === "doc").map(a => (
              <div key={a.id} className="rounded-xl border px-3 py-2"
                style={{ borderColor: "var(--panel-border)", background: "var(--chip-bg)" }}>
                <div className="flex items-center gap-2">
                  <FileText size={14} /><span className="truncate">{a.name}</span>
                </div>
              </div>
            ))}
            {!assets.some(a => a.threadId === thread.id && a.kind === "doc") && (
              <EmptyState title="No documents yet" hint="Upload or attach a file" />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Breadcrumb({ project, thread, onBackProject, onBackThread }: {
  project?: string; thread?: string; onBackProject: () => void; onBackThread: () => void;
}) {
  return (
    <div className="text-xs opacity-80 flex items-center gap-1">
      <span className="opacity-60">Projects</span>
      {project ? (
        <>
          <ChevronRight size={12} /><button className="underline-offset-2 hover:underline" onClick={onBackProject}>{project}</button>
        </>
      ) : null}
      {thread ? (
        <>
          <ChevronRight size={12} /><span>{thread}</span>
        </>
      ) : null}
    </div>
  );
}

function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border p-3 text-sm opacity-80" style={{ borderColor: "var(--panel-border)" }}>
      <div className="font-medium">{title}</div>
      {hint ? <div className="text-xs opacity-70 mt-1">{hint}</div> : null}
    </div>
  );
}
