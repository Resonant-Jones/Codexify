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

  // --- color helpers to generate gradient from base ---
  function hexToRgb(hex: string) {
    const n = hex.replace("#", "");
    const v = n.length === 3 ? n.split("").map((c) => c + c).join("") : n;
    const num = parseInt(v, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }
  function rgbToHsl(r: number, g: number, b: number) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0; const l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }
    return { h: h * 360, s: s * 100, l: l * 100 };
  }
  function hslToHex(h: number, s: number, l: number) {
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    let r = 0, g = 0, b = 0;
    if (0 <= h && h < 60) { r = c; g = x; }
    else if (60 <= h && h < 120) { r = x; g = c; }
    else if (120 <= h && h < 180) { g = c; b = x; }
    else if (180 <= h && h < 240) { g = x; b = c; }
    else if (240 <= h && h < 300) { r = x; b = c; }
    else { r = c; b = x; }
    const to255 = (v: number) => Math.round((v + m) * 255);
    const out = (n: number) => n.toString(16).padStart(2, "0");
    return `#${out(to255(r))}${out(to255(g))}${out(to255(b))}`;
  }
  function lighten(hex: string, amount: number) {
    const { r, g, b } = hexToRgb(hex);
    const { h, s, l } = rgbToHsl(r, g, b);
    const nl = Math.min(100, l + amount * 100);
    return hslToHex(h, s, nl);
  }
  function darken(hex: string, amount: number) {
    const { r, g, b } = hexToRgb(hex);
    const { h, s, l } = rgbToHsl(r, g, b);
    const nl = Math.max(0, l - amount * 100);
    return hslToHex(h, s, nl);
  }

  const accent = baseColor;
  const accentWeak = baseColor;
  const accentStrong = baseColor;
  const bgStyleNoWallpaper = (() => {
    const start = lighten(baseColor, fade * 0.6);
    const end = darken(baseColor, depth * 0.8);
    return { background: `linear-gradient(135deg, ${start}, ${end})` } as React.CSSProperties;
  })();
  // Build background styles: if wallpaper present, overlay a gradient so
  // light/dark flips are visually obvious beyond token changes.
  const backgroundStyle: React.CSSProperties = (() => {
    if (!wallpaper) return bgStyleNoWallpaper;
    // Overlay gradient with alpha to bias the scene per theme
    const clamp = (n: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, n));
    const f = clamp(fade);
    const d = clamp(depth);
    let start = "rgba(255,255,255,0.0)";
    let end = "rgba(255,255,255,0.0)";
    if (resolved === "dark") {
      // dark: emphasize depth (heavier overlay), minimal fade
      start = `rgba(0,0,0,${(d * 0.7).toFixed(3)})`;
      end = `rgba(0,0,0,${(f * 0.35).toFixed(3)})`;
    } else {
      // light: emphasize fade (brighter wash), low depth
      start = `rgba(255,255,255,${(f * 0.5).toFixed(3)})`;
      end = `rgba(255,255,255,${(d * 0.25).toFixed(3)})`;
    }
    return {
      backgroundImage: `linear-gradient(135deg, ${start}, ${end}), url(${wallpaper})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat",
    } as React.CSSProperties;
  })();
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

  // Drive dramatic background differences when no wallpaper is set
  useEffect(() => {
    if (wallpaper) return; // wallpaper drives the look instead
    if (resolved === "dark") {
      setDepth(0.92);
      setFade(0.1);
    } else {
      setDepth(0.1);
      setFade(0.9);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolved, wallpaper]);

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
