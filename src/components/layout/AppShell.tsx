import React, { useMemo } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { RefractiveGlassCard } from "../ui/RefractiveGlassCard";

/**
 * AppShell
 * - Adds a consistent 3px outer buffer so foreground never touches viewport edges
 * - Rounds all outer corners for the whole app frame
 * - Keeps your existing Header + Sidebar structure intact
 * - Optional wallpaper background (reads `cfy.wallpaper` from localStorage)
 */

type Props = {
  children: React.ReactNode;
};

export const AppShell: React.FC<Props> = ({ children }) => {
  // Read a user-selected wallpaper URL if present (set elsewhere in the app)
  const wallpaper = useMemo(() => {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem("cfy.wallpaper");
    } catch {
      return null;
    }
  }, []);

  const backgroundStyle = wallpaper
    ? { backgroundImage: `url(${wallpaper})`, backgroundSize: "cover", backgroundPosition: "center" }
    : undefined;

  return (
    // 3px buffer around everything, shows the background peeking at the corners
    <div className="h-screen w-screen p-[3px]" style={backgroundStyle}>
      {/* Foreground app frame with rounded corners */}
      <div className="h-full w-full flex rounded-2xl overflow-hidden bg-bg text-fg">
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col">
          <Header />
          {/* Main content area; frost only on Dashboard */}
          <main className="flex-1 min-w-0 overflow-auto p-4">
            <div className="mx-auto w-full max-w-7xl">
              {(() => {
                const isDashboard =
                  typeof window !== "undefined" && /dashboard/i.test(window.location.pathname);
                if (!isDashboard) return <div className="p-4">{children}</div>;
                return (
                  <RefractiveGlassCard wallpaperUrl={wallpaper}>
                    <div className="p-4">{children}</div>
                  </RefractiveGlassCard>
                );
              })()}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};
