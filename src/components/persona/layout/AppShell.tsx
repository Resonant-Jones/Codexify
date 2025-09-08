import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import ReactiveGlassCard from "@/components/surface/ReactiveGlassCard";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import GuardianChat from "@/features/chat/GuardianChat";
import ProviderSwitchFAB from "@/components/ProviderSwitchFAB";
import WorkspacePane from "@/features/workspace/WorkspacePane";
import DashboardView from "@/components/dashboard/DashboardView";
import SettingsView from "@/features/settings/SettingsView";
import { ExtColors, GalleryItem, ThemeMode } from "@/types/ui";
/* ──────────────────────────────────────────────────────────────────────────
   TUNING PRIMER (safe knobs)
   - Per-VIEW overrides: add CSS vars on the wrapper just after `{view === "…"`:
       --radius, --frame, --bezel, --rim, --gutter, --card-pad,
       --workspace-w, --min-h/--max-h, --min-w/--max-w
   - Per-CARD overrides: add vars on the *placement wrapper* (the <div> with
     `style={{ padding: "var(--board-edge)", … }}`) using:
       --w/--min-w/--max-w, --h/--min-h/--max-h, --flex
     Examples:
       • Fixed height:         {"--h":"560px","--flex":"0 0 auto"}
       • Responsive floor:     {"--min-h":"clamp(520px,70vh,900px)"}
       • Share space (2:1):    {"--flex":"2 1 0%"}  vs  {"--flex":"1 1 0%"}
       • Workspace width:      {"--w":"clamp(16rem,22vw,28rem)","--flex":"0 0 var(--w)"}
   - Keep aberration off on glass: <RefractiveGlassCard … aberration={0} />
   ────────────────────────────────────────────────────────────────────────── */
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

export default function AppShell({}: PropsWithChildren) {
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

  const [view, setView] = useState<"dashboard" | "documents" | "gallery" | "guardian" | "settings">(() =>
    (typeof window === "undefined" ? "dashboard" : ((localStorage.getItem("cfy.lastView") as any) || "dashboard"))
  );
  const [workspaceOpen, setWorkspaceOpen] = useState<boolean>(false);
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view); }, [view]);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("cfy.wallpaper")));

  type DocItem = { name: string; ext: keyof ExtColors };
  const [documents] = useState<DocItem[]>(() => {
    const def: DocItem[] = [
      { name: "Covenant", ext: "pdf" },
      { name: "Roadmap", ext: "md" },
      { name: "Vision", ext: "txt" },
      { name: "Design", ext: "sketch" },
    ];
    if (typeof window === "undefined") return def;
    try {
      const raw = localStorage.getItem("cfy.documents");
      if (!raw) return def;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : def;
    } catch {
      return def;
    }
  });
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
    return { background: `linear-gradient(to bottom, ${start}, ${end})` } as React.CSSProperties;
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
  // Global: soften panel border
  const panelBorder = resolved === "dark" ? "rgba(255,255,255,0.08)" : "rgba(17,24,39,0.06)";
  const textColor = resolved === "dark" ? "#ffffff" : "#111827";
  const mutedColor = resolved === "dark" ? "rgba(255,255,255,0.88)" : "#374151";
  // Local-only: translucent bezel for Dashboard cards
  const panelBezel = resolved === "dark" ? "rgba(255,255,255,0.12)" : "rgba(17,24,39,0.10)";
  const styleVars = {
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,
    "--panel-bg": panelBg,
    "--chip-bg": chipBg,
    "--panel-border": panelBorder,
    "--panel-bezel": panelBezel,
    "--text": textColor,
    "--muted": mutedColor,
    /* layout tokens */
    "--page-pad": "0px",
    "--radius": "19px",
    "--card-pad": "10px",
    "--frame": "1px",
    "--rim": "1px",
    "--board-edge": "6px",
    "--gutter": "16px",
    "--bezel": "3px",
    "--workspace-w": "24rem",
  } as React.CSSProperties as any;

  const DEFAULT_EXT_COLORS: ExtColors = {
    pdf:   "#E23B3B", // red
    doc:   "#0EA5E9", // cyan-blue
    md:    "#6B7280", // slate gray
    png:   "#06B6D4", // teal
    sketch:"#F59E0B", // amber
    txt:   "#8B5CF6", // violet
    docx:  "#2563EB", // blue
    jpeg:  "#D946EF", // fuchsia
  };
  const [extColors, setExtColors] = useState<ExtColors>(() => {
    // Merge any saved colors with explicit defaults, so new keys get sensible values
    if (typeof window === "undefined") return DEFAULT_EXT_COLORS;
    try {
      const raw = localStorage.getItem("cfy.extColors");
      const saved = raw ? JSON.parse(raw) : {};
      return { ...DEFAULT_EXT_COLORS, ...saved } as ExtColors;
    } catch {
      return DEFAULT_EXT_COLORS;
    }
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
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const openDocInPlace = (name: string, ext: string) => {
    setActiveDoc(`${name}.${ext}`);
    setWorkspaceOpen(true);
  };
  // Use an active wallpaper for refractive glass; fall back to first gallery image if none chosen yet
  const activeWallpaper = useMemo(() => {
    return wallpaper ?? (gallery && gallery.length > 0 ? gallery[0].src : null);
  }, [wallpaper, gallery]);
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
      className={`relative h-dvh w-full flex flex-col overflow-hidden ${resolved === "dark" ? "dark" : ""}`}
      style={{ ...backgroundStyle, ...styleVars }}
    >
      {/* Full-window rounded glass sheet (final layer) */}
<div
  aria-hidden="true"
  className="absolute rounded-[var(--radius)] overflow-hidden pointer-events-none"
  style={{
    left: "1px",
    right: "1px",
    top: "1px",
    bottom: "1px",
    borderRadius: "var(--radius)",
    zIndex: 5,
    border: "1px solid var(--panel-border)",
    // combine subtle color softening with soft rim and outer feather
    filter: "saturate(0.85) contrast(0.9) brightness(0.9) drop-shadow(0 6px 18px rgba(0,0,0,0.25))",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)",
  }}
>
  <RefractiveGlassCard
    wallpaperUrl={activeWallpaper}
    className="w-full h-full rounded-[var(--radius)]"
    style={{ background: "transparent", border: "none" }}
    intensity={0.003}
    aberration={0}
  />
  {/* neutral scrim so text stays readable over bright wallpapers */}
  <div
    className="absolute inset-0"
    style={{
      background:
        "linear-gradient(180deg, rgba(0,0,0,0.18), rgba(0,0,0,0.28))",
    }}
  />
</div>
      {/* Glass Pill Menu Bar - Left Corner */}
      <div className="relative z-10 cap-width w-full flex justify-start pt-3 px-[var(--board-edge)]">
        <div className="flex items-center gap-3 rounded-full bg-white/20 dark:bg-neutral-800/20 shadow-lg px-3 py-2 backdrop-blur-md border border-white/30 dark:border-neutral-700/30">
          <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: "#000", color: "#fff" }}>Codexify</span>
          <button onClick={() => setView("dashboard")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "dashboard" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Dashboard</button>
          <button onClick={() => setView("documents")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "documents" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Documents</button>
          <button onClick={() => setView("gallery")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "gallery" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Gallery</button>
          <button onClick={() => setView("guardian")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "guardian" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Guardian</button>
          <button onClick={() => setView("settings")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "settings" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Settings</button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="relative z-10 flex-1 min-h-0 px-[var(--board-edge)] pb-[var(--board-edge)] pt-[var(--gutter)] overflow-hidden">
        <div className="h-full min-h-0 flex">
          {view === "documents" && (
            <div style={{ "--radius": "19px", "--frame": "250px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)" } as React.CSSProperties}>
              <div className="h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
              <div
                className="min-w-0 flex-1 min-h-0 overflow-visible rounded-[var(--radius)]"
                style={{
                  padding: "var(--board-edge)",
                  width: "var(--w, auto)",
                  maxWidth: "var(--max-w, none)",
                  minWidth: "var(--min-w, 0)",
                  height: "var(--h, auto)",
                  minHeight: "var(--min-h, 0)",
                  maxHeight: "var(--max-h, none)",
                  flex: "var(--flex, 1 1 0%)",
                  "--flex": "0 0 33.33%",
                  "--min-h": "clamp(520px, 70vh, 1000px)",
                }}
              >
                <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                  <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                    <div className="relative rounded-[var(--radius)]">
                      <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                        <RefractiveGlassCard
                          wallpaperUrl={activeWallpaper}
                          className="w-full h-full rounded-[var(--radius)]"
                          style={{ background: "transparent", border: "none" }}
                          intensity={0.008}
                          aberration={0}
                        />
                      </div>
                      <div className="min-h-0 w-full rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                        <div className="min-h-0 w-full px-[var(--card-pad)] pt-[var(--card-pad)] pb-0">
                          <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>DOCS</div>
                          <div className="flex flex-col gap-[calc(var(--gutter)/2)]">
                            {documents.map((d) => {
                              const color = (extColors as any)[d.ext] || "#6B7280";
                              return (
                                <FrameCard key={d.name + d.ext}>
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3 p-3">
                                      <div className="w-7 h-7 rounded-md" style={{ background: color }} />
                                      <div className="text-sm" style={{ color: "var(--text)" }}>{d.name}.{d.ext}</div>
                                    </div>
                                    <button
                                      className="text-xs pr-3 opacity-80 hover:opacity-100 underline-offset-2 hover:underline"
                                      style={{ color: "var(--muted)" }}
                                      onClick={() => openDocInPlace(d.name, d.ext)}
                                    >
                                      Open
                                    </button>
                                  </div>
                                </FrameCard>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              {workspaceOpen && (
                <div
                  className="rounded-[var(--radius)] shrink-0 overflow-visible"
                  style={{
                    padding: "var(--board-edge)",
                    width: "var(--w, var(--workspace-w))",
                    maxWidth: "var(--max-w, none)",
                    minWidth: "var(--min-w, 0)",
                    height: "var(--h, auto)",
                    minHeight: "var(--min-h, 0)",
                    maxHeight: "var(--max-h, none)",
                    flex: "var(--flex, 0 0 var(--workspace-w))",
                    "--w": "calc(66.67% - var(--gutter))",
                    "--flex": "0 0 var(--w)",
                    "--min-h": "clamp(520px, 70vh, 1000px)",
                  }}
                >
                  <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                    <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                      <div className="relative rounded-[var(--radius)]">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.008}
                            aberration={0}
                          />
                        </div>
                        <div className="rounded-[var(--radius)] overflow-hidden relative" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                          <button
                            onClick={() => setWorkspaceOpen(false)}
                            className="absolute top-2 right-2 h-6 w-6 rounded-full border text-xs flex items-center justify-center hover:opacity-90"
                            style={{ borderColor: "var(--panel-border)", color: "var(--muted)", background: "var(--panel-bg)" }}
                            aria-label="Close workspace"
                            title="Close"
                          >
                            ×
                          </button>
                          <WorkspacePane />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              </div>
            </div>
          )}
          {view === "gallery" && (
            <div style={{ "--radius": "16px", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)" } as React.CSSProperties}>
              <div className="h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
              <div
                className="min-w-0 flex-1 min-h-0 overflow-visible rounded-[var(--radius)]"
                style={{
                  padding: "var(--board-edge)",
                  width: "var(--w, auto)",
                  maxWidth: "var(--max-w, none)",
                  minWidth: "var(--min-w, 0)",
                  height: "var(--h, auto)",
                  minHeight: "var(--min-h, 0)",
                  maxHeight: "var(--max-h, none)",
                  flex: "var(--flex, 1 1 0%)",
                  "--flex": "1 1 0%",
                  "--min-h": "clamp(520px, 70vh, 1000px)",
                }}
              >
                <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                  <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                    <div className="relative rounded-[var(--radius)]">
                      <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                        <RefractiveGlassCard
                          wallpaperUrl={activeWallpaper}
                          className="w-full h-full rounded-[var(--radius)]"
                          style={{ background: "transparent", border: "none" }}
                          intensity={0.006}
                          aberration={0}
                        />
                      </div>
                      <div className="min-h-0 w-full rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                        <div className="min-h-0 w-full px-[var(--board-edge)] pt-[var(--card-pad)] pb-[var(--board-edge)]">
                          <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>GALLERY</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-[var(--gutter)]">
                            {gallery.map((g, i) => (
                              <div key={i} className="aspect-square rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                                <img src={g.src} alt={g.prompt} className="w-full h-full object-cover" />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              </div>
            </div>
          )}
          {view === "guardian" && (
            <div style={{ "--radius": "16px", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)", "--workspace-w": "clamp(16rem, 25vw, 28rem)" } as React.CSSProperties}>
              <div className="h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
                <div
                  className="min-w-0 flex-1 min-h-0 overflow-visible rounded-[var(--radius)]"
                  style={{
                    padding: "var(--board-edge)",
                    width: "var(--w, auto)",
                    maxWidth: "var(--max-w, none)",
                    minWidth: "var(--min-w, 0)",
                    height: "var(--h, auto)",
                    minHeight: "var(--min-h, 0)",
                    maxHeight: "var(--max-h, none)",
                    flex: "var(--flex, 1 1 0%)",
                    "--flex": "1 1 0%",
                    "--min-h": "clamp(520px, 70vh, 1000px)",
                  }}
                >
                  <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                    <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                      <div className="relative rounded-[var(--radius)]">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.008}
                            aberration={0}
                          />
                        </div>
                        {/* Chat panel with fully rounded corners (top & bottom) */}
                        <div
                          className="flex flex-col h-full min-h-0 w-full rounded-[var(--radius)] overflow-hidden"
                          style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}
                        >
                          <div className="flex-1 min-h-0 w-full px-[var(--board-edge)] pt-[var(--card-pad)] pb-[var(--board-edge)]">
                            <GuardianChat
                              guardianName={guardianName}
                              userName={userName}
                              prefill={prefill}
                              onPrefillConsumed={() => setPrefill(undefined)}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Optional right-side workspace when toggled, same pattern to keep rounded edges */}
                {workspaceOpen && (
                  <div
                    className="rounded-[var(--radius)] shrink-0 overflow-visible"
                    style={{
                      padding: "var(--board-edge)",
                      width: "var(--w, var(--workspace-w))",
                      maxWidth: "var(--max-w, none)",
                      minWidth: "var(--min-w, 0)",
                      height: "var(--h, auto)",
                      minHeight: "var(--min-h, 0)",
                      maxHeight: "var(--max-h, none)",
                      flex: "var(--flex, 0 0 var(--workspace-w))",
                      "--w": "var(--workspace-w)",
                      "--flex": "0 0 var(--w)",
                      "--min-h": "clamp(520px, 70vh, 1000px)",
                    }}
                  >
                    <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}>
                      <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                        <div className="relative rounded-[var(--radius)]">
                          <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                            <RefractiveGlassCard
                              wallpaperUrl={activeWallpaper}
                              className="w-full h-full rounded-[var(--radius)]"
                              style={{ background: "transparent", border: "none" }}
                              intensity={0.008}
                              aberration={0}
                            />
                          </div>
                          <div className="rounded-[var(--radius)] overflow-hidden relative" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                            <button
                              onClick={() => setWorkspaceOpen(false)}
                              className="absolute top-2 right-2 h-6 w-6 rounded-full border text-xs flex items-center justify-center hover:opacity-90"
                              style={{ borderColor: "var(--panel-border)", color: "var(--muted)", background: "var(--panel-bg)" }}
                              aria-label="Close workspace"
                              title="Close"
                            >
                              ×
                            </button>
                            <WorkspacePane />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Provider switch is only available in Chat view */}
              <ProviderSwitchFAB />
              <button
                onClick={() => setWorkspaceOpen(v => !v)}
                className="fixed bottom-6 right-6 z-20 rounded-full h-10 w-10 shadow-lg border backdrop-blur-md"
                style={{ background: "rgba(255,255,255,0.8)", borderColor: "var(--panel-border)" }}
                aria-label="Toggle workspace"
                title="Workspace"
              >
                🗂️
              </button>
            </div>
          )}
          {view === "dashboard" && (
            <div style={{ "--radius": "16px", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "100%" } as React.CSSProperties}>
              <div className="grid h-full min-h-0 w-full gap-[var(--gutter)] grid-cols-1 lg:grid-cols-2 grid-rows-1 content-stretch">
              <div className="min-h-0 h-full flex flex-col gap-[10px]">
                {/* LEFT COLUMN: stacked cards (top: DashboardView, bottom: Recent) */}
                <div
                  className="min-h-0 h-full overflow-visible rounded-[var(--radius)] basis-0"
                  style={{
                    padding: "var(--board-edge)",
                    width: "auto",
                    height: "auto",
                    minWidth: "0",
                    minHeight: "0",
                    maxWidth: "100%",
                    maxHeight: "100%",
                    // equal split in column
                    flex: "1 1 0%",
                  }}
                >
                  <div
                    className="rounded-[var(--radius)]"
                    style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}
                    >
                      <div className="relative rounded-[var(--radius)]">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.008}
                            aberration={0}
                          />
                        </div>
                        <div className="min-h-0 h-full overflow-hidden rounded-[var(--radius)]" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                          <div className="p-[var(--card-pad)] min-h-0 overflow-auto">
                            <DashboardView
                              extColors={extColors}
                              gallery={gallery}
                              onImagePrompt={openChatWithPrompt}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  className="min-h-0 h-full overflow-visible rounded-[var(--radius)] basis-0"
                  style={{
                    padding: "var(--board-edge)",
                    width: "auto",
                    height: "auto",
                    minWidth: "0",
                    minHeight: "0",
                    maxWidth: "100%",
                    maxHeight: "100%",
                    // equal split in column
                    flex: "1 1 0%",
                  }}
                >
                  <div
                    className="rounded-[var(--radius)]"
                    style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}
                    >
                      <div className="relative rounded-[var(--radius)]">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.008}
                            aberration={0}
                          />
                        </div>
                        <div className="min-h-0 h-full overflow-hidden rounded-[var(--radius)]" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                          <div className="p-[var(--card-pad)] min-h-0 overflow-auto">
                            <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>Recent</div>
                            <div className="flex flex-col gap-[calc(var(--gutter)/2)]">
                              {documents.map((d) => {
                                const color = (extColors as any)[d.ext] || "#6B7280";
                                return (
                                  <FrameCard key={d.name + d.ext}>
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-3 p-3">
                                        <div className="w-7 h-7 rounded-md" style={{ background: color }} />
                                        <div className="text-sm" style={{ color: "var(--text)" }}>{d.name}.{d.ext}</div>
                                      </div>
                                      <button
                                        className="text-xs pr-3 opacity-80 hover:opacity-100 underline-offset-2 hover:underline"
                                        style={{ color: "var(--muted)" }}
                                        onClick={() => openDocInPlace(d.name, d.ext)}
                                      >
                                        Open
                                      </button>
                                    </div>
                                  </FrameCard>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* CENTER COLUMN: Gallery as its own full-height layered card */}
             <div
               className="min-w-0 min-h-0 h-full overflow-visible rounded-[var(--radius)] lg:row-span-2"
               style={{
                 padding: "var(--board-edge)",
                 width: "var(--w, auto)",
                 maxWidth: "var(--max-w, none)",
                 minWidth: "var(--min-w, 0)",
                 height: "var(--h)",
                 minHeight: "var(--min-h, 0)",
                 maxHeight: "var(--max-h, none)",
                 flex: "var(--flex, 1 1 0%)",
                 "--min-h": "100%",
                 "--h": "100%",
               }}
            >
                <div
                  className="rounded-[var(--radius)]"
                  style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}
                >
                  <div
                    className="rounded-[var(--radius)]"
                    style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}
                  >
                    <div className="relative rounded-[var(--radius)]">
                      <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                        <RefractiveGlassCard
                          wallpaperUrl={activeWallpaper}
                          className="w-full h-full rounded-[var(--radius)]"
                          style={{ background: "transparent", border: "none" }}
                          intensity={0.008}
                          aberration={0}
                        />
                      </div>
                      <div className="min-w-0 min-h-0 overflow-hidden rounded-[var(--radius)]" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                        <div className="p-[var(--card-pad)] min-h-0 overflow-auto">
                          <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>Generated Images</div>
                          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-[var(--gutter)]">
                            {gallery.map((g, i) => (
                              <div key={i} className="aspect-square rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                                <img src={g.src} alt={g.prompt} className="w-full h-full object-cover" />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* RIGHT COLUMN: WorkspacePane, conditional on workspaceOpen */}
              {workspaceOpen && (
                <div
                  className="rounded-[var(--radius)] shrink-0 overflow-visible"
                  style={{
                    padding: "var(--board-edge)",
                    width: "var(--w, var(--workspace-w))",
                    maxWidth: "var(--max-w, none)",
                    minWidth: "var(--min-w, 0)",
                    height: "var(--h, auto)",
                    minHeight: "var(--min-h, 0)",
                    maxHeight: "var(--max-h, none)",
                    flex: "var(--flex, 0 0 var(--workspace-w))",
                  }}
                >
                  <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                    <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                      <div className="relative rounded-[var(--radius)]">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.006}
                            aberration={0}
                          />
                        </div>
                        <div className="rounded-[var(--radius)] overflow-hidden relative" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                          <button
                            onClick={() => setWorkspaceOpen(false)}
                            className="absolute top-2 right-2 h-6 w-6 rounded-full border text-xs flex items-center justify-center hover:opacity-90"
                            style={{ borderColor: "var(--panel-border)", color: "var(--muted)", background: "var(--panel-bg)" }}
                            aria-label="Close workspace"
                            title="Close"
                          >
                            ×
                          </button>
                          <WorkspacePane />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              </div>
            </div>
          )}
          {view === "settings" && (
            <div style={{ "--radius": "16px", "--frame": "5px", "--bezel": "4px", "--rim": "3px" } as React.CSSProperties}>
              <div className="h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
              <div
                className="min-w-0 flex-1 min-h-0 overflow-visible rounded-[var(--radius)]"
                style={{
                  padding: "var(--board-edge)",
                  width: "var(--w, auto)",
                  maxWidth: "var(--max-w, none)",
                  minWidth: "var(--min-w, 0)",
                  height: "var(--h, auto)",
                  minHeight: "var(--min-h, 0)",
                  maxHeight: "var(--max-h, none)",
                  flex: "var(--flex, 1 1 0%)",
                }}
              >
                <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                  <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                    <div className="relative rounded-[var(--radius)]">
                      <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                        <RefractiveGlassCard
                          wallpaperUrl={activeWallpaper}
                          className="w-full h-full rounded-[var(--radius)]"
                          style={{ background: "transparent", border: "none" }}
                          intensity={0.006}
                          aberration={0}
                        />
                      </div>
                      <div className="min-h-0 w-full rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                        <div className="min-h-0 w-full overflow-auto p-[var(--card-pad)]">
                          <div className="max-w-[18rem] mr-auto">
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
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
