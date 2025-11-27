import { useState, useMemo, useEffect, useRef } from "react";
import { Folder, MessageSquare, ArrowLeft, X } from "lucide-react";
import type { Project, Thread } from "./RightRail";

export default function ProjectsOverlay({
  open, onClose, projects = [], threads = [], onOpenThread
}: {
  open: boolean;
  onClose: () => void;
  projects?: Project[];
  threads?: Thread[];
  onOpenThread: (projectId: string, threadId: string) => void;
}) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);

  const [focusProjectId, setFocusProjectId] = useState<string | null>(null);
  const viewThreads = useMemo(
    () => threads.filter(t => t.projectId === focusProjectId),
    [threads, focusProjectId]
  );

  useEffect(() => {
    const prev = (document.activeElement as HTMLElement) || null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "Tab" && panelRef.current) {
        const focusables = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement;
        if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && active === first) {
          e.preventDefault();
          last.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    setTimeout(() => closeBtnRef.current?.focus(), 0);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onClose]);

  const glass = {
    background: "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)",
    backdropFilter: "blur(12px) saturate(120%)",
    WebkitBackdropFilter: "blur(12px) saturate(120%)",
    borderColor: "var(--panel-border)",
    boxShadow: "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.25), 0 10px 22px rgba(0,0,0,0.25)"
  } as const;

  if (!open) return null;

  return (
    <div className="absolute inset-0 z-[60]">
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="absolute inset-0 p-[3px] pointer-events-none">
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="projectsOverlayTitle"
          className="relative h-full w-full rounded-3xl border overflow-hidden pointer-events-auto"
          style={glass}
        >
          <div className="relative flex items-center justify-between px-4 py-3">
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
            <div className="flex items-center gap-2">
              {focusProjectId ? (
                <button
                  className="rounded-full p-1 hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                  onClick={() => setFocusProjectId(null)}
                  aria-label="Back"
                  style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
                >
                  <ArrowLeft size={16} />
                </button>
              ) : null}
              <div id="projectsOverlayTitle" className="text-sm font-semibold opacity-90" style={{ color: "var(--text)" }}>
                {focusProjectId ? "Threads" : "Projects"}
              </div>
            </div>
            <button
              ref={closeBtnRef}
              className="rounded-full p-1 hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              onClick={onClose}
              aria-label="Close"
              style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
            >
              <X size={16} />
            </button>
          </div>

          {!focusProjectId ? (
            <div className="p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map(p => (
                <button
                  key={p.id}
                  onClick={() => setFocusProjectId(p.id)}
                  className="rounded-2xl border px-4 py-3 text-left transition-colors"
                  style={{ borderColor: "var(--panel-border)", background: "var(--chip-bg)", color: "var(--text)" }}
                >
                  <div className="flex items-center gap-2">
                    <Folder size={16} />
                    <div className="font-medium truncate">{p.name}</div>
                  </div>
                  <div className="mt-1 text-xs opacity-70">
                    {threads.filter(t => t.projectId === p.id).length} thread(s)
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="p-4 grid gap-2">
              {viewThreads.length ? viewThreads.map(t => (
                <button
                  key={t.id}
                  onClick={() => onOpenThread(focusProjectId!, t.id)}
                  className="rounded-xl border px-3 py-2 text-left transition-colors"
                  style={{ borderColor: "var(--panel-border)", background: "var(--chip-bg)", color: "var(--text)" }}
                >
                  <div className="inline-flex items-center gap-2">
                    <MessageSquare size={14} />
                    <span className="truncate">{t.title}</span>
                  </div>
                </button>
              )) : (
                <div className="text-sm opacity-80 px-1">No threads yet.</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
