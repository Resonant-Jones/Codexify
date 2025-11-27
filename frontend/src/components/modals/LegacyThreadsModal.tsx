import React from "react";

type LegacyThread = {
  id: string;
  title: string;
  summary?: string;
};

export function LegacyThreadsModal({ onClose, onFork }: { onClose: () => void; onFork: (threadId?: string) => void }) {
  const [threads] = React.useState<LegacyThread[]>([
    { id: "t1", title: "Research: Prompt Engineering", summary: "Notes and iterations on prompt patterns" },
    { id: "t2", title: "Design: Dashboard Concepts", summary: "Explorations of layout and interactions" },
    { id: "t3", title: "Analysis: Model Comparisons", summary: "Comparing responses across providers" },
  ]);
  const [activeId, setActiveId] = React.useState<string | null>(threads[0]?.id ?? null);
  const active = React.useMemo(() => threads.find((t) => t.id === activeId) || null, [threads, activeId]);

  return (
    <div className="flex flex-col h-full" style={{ color: "var(--text)" }}>
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "var(--panel-border)" }}>
        <h2 className="text-base font-semibold">Legacy Threads</h2>
        <button type="button" className="icon-inline" aria-label="Close" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-0 flex-1 min-h-0">
        <div className="border-r overflow-auto" style={{ borderColor: "var(--panel-border)" }}>
          <ul className="divide-y" style={{ borderColor: "var(--panel-border)" }}>
            {threads.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => setActiveId(t.id)}
                  className="w-full text-left px-4 py-3 hover:bg-white/5"
                  data-active={activeId === t.id}
                >
                  <div className="text-sm font-medium truncate">{t.title}</div>
                  {t.summary && <div className="text-xs opacity-70 truncate">{t.summary}</div>}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="md:col-span-2 min-h-0 overflow-auto">
          {active ? (
            <div className="p-4 space-y-3">
              <div className="text-sm opacity-80">Thread ID: {active.id}</div>
              <div className="rounded-xl border p-4 text-sm" style={{ borderColor: "var(--panel-border)" }}>
                Placeholder conversation tree/viewer goes here. Render messages and branching.
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  className="px-3 py-1.5 rounded-full border"
                  style={{ borderColor: "var(--panel-border)" }}
                  onClick={() => onFork(active.id)}
                >
                  Fork to new thread
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 text-sm opacity-70">Select a legacy thread to preview.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default LegacyThreadsModal;
