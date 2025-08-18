import React from "react";

export const Header: React.FC = () => {
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
          <button className="btn" onClick={toggleTheme} aria-label="Toggle theme">
            Toggle Theme
          </button>
        </div>
      </div>
    </header>
  );
};

