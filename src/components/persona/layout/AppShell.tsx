import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import ReactiveGlassCard from "@/components/surface/ReactiveGlassCard";
import GuardianChat from "@/features/chat/GuardianChat";
import WorkspacePane from "@/features/workspace/WorkspacePane";
import DashboardView from "@/features/dashboard/DashboardView";
import SettingsView from "@/features/settings/SettingsView";
import { ExtColors, GalleryItem, ThemeMode } from "@/types/ui";

type Resolved = "light" | "dark";

function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

const SESSION_KEY = "cfy.sessionTheme"
const SESSION_UNTIL = "cfy.sessionThemeUntil"

function nextLocalMidnight() {
  const d = new Date()
  d.setHours(24, 0, 0, 0)
  return d.getTime()
}

function readSessionOverride(): Resolved | null {
  if (typeof window === "undefined") return null
  try {
    const untilRaw = window.localStorage.getItem(SESSION_UNTIL)
    if (!untilRaw) return null
    const until = Number(untilRaw)
    if (!Number.isFinite(until) || Date.now() > until) {
      window.localStorage.removeItem(SESSION_KEY)
      window.localStorage.removeItem(SESSION_UNTIL)
      return null
    }
    const v = window.localStorage.getItem(SESSION_KEY)
    return v === "dark" || v === "light" ? v : null
  } catch {
    return null
  }
}

function writeSessionOverride(v: Resolved | null) {
  if (typeof window === "undefined") return
  if (v == null) {
    window.localStorage.removeItem(SESSION_KEY)
    window.localStorage.removeItem(SESSION_UNTIL)
  } else {
    window.localStorage.setItem(SESSION_KEY, v)
    window.localStorage.setItem(SESSION_UNTIL, String(nextLocalMidnight()))
  }
}

export function AppShell({}: PropsWithChildren) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const raw = window.localStorage.getItem("cfy.themeMode");
    return coerceMode(raw);
  });
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [sessionOverride, setSessionOverride] = useState<Resolved | null>(() => readSessionOverride());

  useEffect(() => {
    if (typeof window === "undefined") return
    const mm = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => setSystemPrefersDark(mm.matches)
    if (mm.addEventListener) mm.addEventListener("change", handler)
    else mm.addListener(handler)
    return () => {
      if (mm.removeEventListener) mm.removeEventListener("change", handler)
      else mm.removeListener(handler)
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    const onStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEY || e.key === SESSION_UNTIL) setSessionOverride(readSessionOverride())
      if (e.key === "cfy.themeMode") setMode(coerceMode(window.localStorage.getItem("cfy.themeMode")))
    }
    window.addEventListener("storage", onStorage)
    const t = window.setInterval(() => setSessionOverride(readSessionOverride()), 60_000)
    return () => {
      window.removeEventListener("storage", onStorage)
      window.clearInterval(t)
    }
  }, [])

  const resolved: Resolved = useMemo(() => {
    if (sessionOverride) return sessionOverride;
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return systemPrefersDark ? "dark" : "light";
  }, [mode, systemPrefersDark, sessionOverride]);

  useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.classList.toggle("dark", resolved === "dark")
  }, [resolved])

  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem("cfy.themeMode", mode)
  }, [mode])

  // App state and style vars for wallpaper/gradient and tokens
  const [guardianName, setGuardianName] = useState<string>(() => (typeof window === "undefined" ? "Guardian" : localStorage.getItem("cfy.assistantName") || "Guardian"));
  const [userName, setUserName] = useState<string>(() => (typeof window === "undefined" ? "You" : localStorage.getItem("cfy.userName") || "You"));
  const [role, setRole] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.role") || ""));
  const [notes, setNotes] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.notes") || ""));
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.assistantName", guardianName); }, [guardianName]);
  const [systemPrompt, setSystemPrompt] = useState<string>(() => (typeof window === "undefined" ? "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity." : localStorage.getItem("cfy.systemPrompt") || "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity."));
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.userName", userName);
      localStorage.setItem("cfy.role", role);
      localStorage.setItem("cfy.notes", notes);
      localStorage.setItem("cfy.systemPrompt", systemPrompt);
    }
  }, [userName, role, notes, systemPrompt]);

  const [view, setView] = useState<"dashboard" | "guardian" | "settings">(() => (typeof window === "undefined" ? "guardian" : ((localStorage.getItem("cfy.lastView") as any) || "guardian")));
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view); }, [view]);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("cfy.wallpaper")));
  const [baseColor, setBaseColor] = useState<string>(() => (typeof window === "undefined" ? "#6B7280" : localStorage.getItem("cfy.baseColor") || "#6B7280"));
  const [depth, setDepth] = useState<number>(() => (typeof window === "undefined" ? 0.6 : Number(localStorage.getItem("cfy.depth") || "0.6")));
  const [fade, setFade] = useState<number>(() => (typeof window === "undefined" ? 0.4 : Number(localStorage.getItem("cfy.fade") || "0.4")));
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.baseColor", baseColor);
      localStorage.setItem("cfy.depth", String(depth));
      localStorage.setItem("cfy.fade", String(fade));
    }
  }, [baseColor, depth, fade]);

  const accent = baseColor;
  const accentWeak = baseColor; // simplified; original rotated hues preserved via CSS vars
  const accentStrong = baseColor;
  const bgStyleNoWallpaper = (() => {
    return { background: `linear-gradient(to bottom, ${baseColor}, ${baseColor})` } as React.CSSProperties;
  })();
  const backgroundStyle: React.CSSProperties = wallpaper
    ? { backgroundImage: `url(${wallpaper})`, backgroundSize: "cover", backgroundPosition: "center" }
    : bgStyleNoWallpaper;
  const panelBg = resolved === "dark" ? "#202020" : "#f3f4f6";
  const chipBg = resolved === "dark" ? "#2f2f2f" : "#e5e7eb";
  const panelBorder = resolved === "dark" ? "#3f3f3f" : "#e5e7eb";
  const textColor = resolved === "dark" ? "#ffffff" : "#111827";
  const mutedColor = resolved === "dark" ? "rgba(255,255,255,0.88)" : "#374151";
  const styleVars = {
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,
    "--panel-bg": panelBg,
    "--chip-bg": chipBg,
    "--panel-border": panelBorder,
    "--text": textColor,
    "--muted": mutedColor,
  } as React.CSSProperties as any;

  const [extColors, setExtColors] = useState<ExtColors>(() => {
    if (typeof window === "undefined") return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
    try { const raw = localStorage.getItem("cfy.extColors"); return raw ? JSON.parse(raw) : { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" }; } catch { return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" }; }
  });
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.extColors", JSON.stringify(extColors)); }, [extColors]);
  const [gallery] = useState<GalleryItem[]>(() => {
    const def: GalleryItem[] = [
      { src: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop", prompt: "vibrant color gradient, smooth texture, abstract art, minimalist, 4k" },
      { src: "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=600&auto=format&fit=crop", prompt: "dramatic light, deep shadows, cinematic, moody, purple and blue tones" },
      { src: "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?q=80&w=600&auto=format&fit=crop", prompt: "ethereal smoke, liquid metal, iridescent, holographic, studio lighting, 8k" },
      { src: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=600&auto=format&fit=crop", prompt: "soft gradient, warm horizon fade, subtle grain, minimal" },
    ];
    if (typeof window === "undefined") return def;
    try { const raw = localStorage.getItem("cfy.gallery"); return raw ? JSON.parse(raw) : def; } catch { return def; }
  });
  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  function openChatWithPrompt(p: string) { setPrefill(p); setView("guardian"); }

  return (
    <div
      className={`h-dvh w-full flex flex-col px-4 pb-4 gap-4 ${resolved === "dark" ? "dark" : ""}`}
      style={{ ...backgroundStyle, ...styleVars }}
    >
      <div className="flex h-full w-full flex-col rounded-2xl">
        {/* Top Nav without seam */}
        <div className="flex items-center justify-between gap-2 p-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full px-2 py-1 text-xs font-semibold" style={{ background: "#000", color: "#fff" }}>Codexify</span>
            <Button variant={view === "dashboard" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("dashboard")}>Dashboard</Button>
            <Button variant={view === "guardian" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("guardian")}>Guardian</Button>
            <Button variant={view === "settings" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("settings")}>Settings</Button>
          </div>
          <div className="text-xs opacity-80" style={{ color: "var(--text)" }}>Mode: {resolved}</div>
        </div>

        {/* Main Content */}
        <div className="flex min-h-0 flex-1 p-3">
          {view === "guardian" && (
            <GuardianChat guardianName={guardianName} userName={userName} prefill={prefill} onPrefillConsumed={() => setPrefill(undefined)} />
          )}
          {view === "dashboard" && (
            <div className="flex min-h-0 w-full gap-3">
              <ReactiveGlassCard wallpaperUrl={wallpaper} className="flex min-w-0 flex-1 rounded-2xl overflow-hidden glass-surface">
                <DashboardView extColors={extColors} gallery={gallery} onImagePrompt={openChatWithPrompt} />
              </ReactiveGlassCard>
              <ReactiveGlassCard wallpaperUrl={wallpaper} className="glass-surface"><WorkspacePane /></ReactiveGlassCard>
            </div>
          )}
          {view === "settings" && (
            <div className="flex min-h-0 w-full gap-3">
              <div className="flex min-w-0 flex-1 rounded-2xl overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
                <SettingsView
                  mode={mode}
                  setMode={setMode}
                  guardianName={guardianName}
                  setGuardianName={setGuardianName}
                  userName={userName}
                  setUserName={setUserName}
                  role={role}
                  setRole={setRole}
                  notes={notes}
                  setNotes={setNotes}
                  baseColor={baseColor}
                  setBaseColor={setBaseColor}
                  depth={depth}
                  setDepth={setDepth}
                  fade={fade}
                  setFade={setFade}
                  resolved={resolved}
                  systemPrompt={systemPrompt}
                  setSystemPrompt={setSystemPrompt}
                  wallpaper={wallpaper}
                  setWallpaper={setWallpaper}
                  extColors={extColors}
                  setExtColors={setExtColors}
                />
              </div>
              <ReactiveGlassCard wallpaperUrl={wallpaper} className="glass-surface"><WorkspacePane /></ReactiveGlassCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AppShell
