import React from "react";
import { useLiveEvents } from "../../hooks/useLiveEvents";
import { SparklesIcon } from "@heroicons/react/24/solid";

export const Header: React.FC = () => {
  const { connected } = useLiveEvents();
  const toggleTheme = () => {
    const html = document.documentElement;
    const next = html.classList.toggle("dark");
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {}
  };

  React.useEffect(() => {
    try {
      const saved = localStorage.getItem("theme");
      if (saved === "dark") document.documentElement.classList.add("dark");
      if (saved === "light") document.documentElement.classList.remove("dark");
    } catch {}
  }, []);

  return (
    <header className="sticky top-0 z-10 border-b border-white/10 bg-[var(--color-surface)]/80 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-surface)]/60">
      <div className="h-12 px-4 flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="h-6 w-6 rounded-md bg-[var(--color-primary)]" />
          <span className="font-semibold">Codexify</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1 text-sm ${
              connected ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                connected
                  ? "bg-emerald-400 animate-pulse"
                  : "bg-rose-400"
              }`}
            />
            <span>
              Live updates: {connected ? "Connected" : "Disconnected"}
            </span>
          </div>
          <button className="btn" onClick={toggleTheme} aria-label="Toggle theme">
            Toggle Theme
          </button>
          <button
            className="btn btn-ghost"
            onClick={() =>
              window.dispatchEvent(
                new CustomEvent("cfy:workspace:toggleWorkspacePanel")
              )
            }
            aria-label="Toggle Workspace"
          >
            <SparklesIcon className="h-5 w-5 text-yellow-400" />
          </button>
        </div>
      </div>
    </header>
  );
};
