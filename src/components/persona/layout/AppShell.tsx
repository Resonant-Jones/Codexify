 // @ts-nocheck
import React, { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { X, ChevronLeft, ChevronRight, Menu } from "lucide-react";
import ReactiveGlassCard from "@/components/surface/ReactiveGlassCard";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import GuardianChat from "@/features/chat/GuardianChat";
import ProviderSwitchFAB from "@/components/ProviderSwitchFAB";
import WorkspacePane from "@/features/workspace/WorkspacePane";
import DashboardView from "@/components/dashboard/DashboardView";
import SettingsView from "@/features/settings/SettingsView";
import DocumentsView from "@/components/documents/DocumentsView";
import Sidebar from "@/components/chat/Sidebar";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { ExtColors, GalleryItem, ThemeMode, Thread, Message } from "@/types/ui";
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
/* ─────────────────────────────────────────────────────────────────────────────
   🧠 SECTION: Theme Mode Type
   We use a simple type alias for the resolved theme mode,
   which will always be either "light" or "dark".
   ───────────────────────────────────────────────────────────────────────────── */
type Resolved = "light" | "dark";

/* ─────────────────────────────────────────────────────────────────────────────
   🧠 SECTION: Theme Preference Handling
   This function takes in any value and ensures it matches one of our accepted
   theme modes: "light", "dark", or "system". If not, we default to "system".
   ───────────────────────────────────────────────────────────────────────────── */
function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

/* ─────────────────────────────────────────────────────────────────────────────
   🗝️ SECTION: Persistent Session Logic
   These helpers let us store a temporary theme override in localStorage,
   lasting until midnight. This is useful for one-day theme changes that
   shouldn't persist forever.
   ───────────────────────────────────────────────────────────────────────────── */
const SESSION_KEY = "cfy.sessionTheme"
const SESSION_UNTIL = "cfy.sessionThemeUntil"

// Returns the timestamp for the next local midnight.
function nextLocalMidnight() {
  const d = new Date()
  d.setHours(24, 0, 0, 0)
  return d.getTime()
}

// Checks if there's a valid theme override for this session in storage.
function readSessionOverride(): Resolved | null {
  if (typeof window === "undefined") return null
  try {
    const untilRaw = window.localStorage.getItem(SESSION_UNTIL)
    if (!untilRaw) return null
    const until = Number(untilRaw)
    // If expired, remove and ignore.
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

// Writes a session theme override, or clears it if null.
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

/* ─────────────────────────────────────────────────────────────────────────────
   🎨 SECTION: AppShell Main Function
   This is the root shell for the app, handling theme, persistent state,
   background visuals, modular design tokens, and view routing.
   ───────────────────────────────────────────────────────────────────────────── */
function useBreakpoint() {
  const get = () => {
    if (typeof window === "undefined") return "xl";
    const w = window.innerWidth;
    if (w < 768) return "sm";
    if (w < 1024) return "md";
    if (w < 1440) return "lg";
    if (w < 1920) return "xl";
    return "2xl";
  };
  const [bp, setBp] = useState(get);
  useEffect(() => {
    const on = () => setBp(get());
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return bp as "sm" | "md" | "lg" | "xl" | "2xl";
}

export default function AppShell({}: PropsWithChildren) {
  /* ─────────────────────────────────────────────────────────────────────────────
     🧠 Theme Mode Logic
     - `mode`: The user's chosen theme mode (light, dark, or system)
     - `systemPrefersDark`: Tracks the OS-level dark mode preference
     - `sessionOverride`: A one-day override for the theme
     We keep all three in sync and resolve to either "light" or "dark" for rendering.
     ───────────────────────────────────────────────────────────────────────────── */
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

  // Listen for OS-level theme changes and storage updates
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
    // Handle theme/session changes from other tabs/windows
    const onStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEY || e.key === SESSION_UNTIL) setSessionOverride(readSessionOverride())
      if (e.key === "cfy.themeMode") setMode(coerceMode(window.localStorage.getItem("cfy.themeMode")))
    }
    window.addEventListener("storage", onStorage)
    // Periodically check if the session override expired
    const t = window.setInterval(() => setSessionOverride(readSessionOverride()), 60_000)
    return () => {
      window.removeEventListener("storage", onStorage)
      window.clearInterval(t)
    }
  }, [])

  // Decide the final theme mode for this session
  const resolved: Resolved = useMemo(() => {
    if (sessionOverride) return sessionOverride;
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return systemPrefersDark ? "dark" : "light";
  }, [mode, systemPrefersDark, sessionOverride]);

  // Actually apply the theme class to the <html> element
  useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.classList.toggle("dark", resolved === "dark")
  }, [resolved])

  // Save user theme mode to localStorage when changed
  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem("cfy.themeMode", mode)
  }, [mode])

  /* ─────────────────────────────────────────────────────────────────────────────
     🗂️ Persistent User and App State
     These state variables track user names, role, notes, and system prompt.
     We sync them with localStorage so they persist across reloads.
     ───────────────────────────────────────────────────────────────────────────── */
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

  /* ─────────────────────────────────────────────────────────────────────────────
     🚦 SECTION: View Routing and UI Rendering
     - `view`: Tracks which main screen (dashboard, documents, etc.) is active.
     - `workspaceOpen`: Controls visibility of the workspace sidebar/pane.
     - `wallpaper`: Optional image for the background.
     - We persist the last view and wallpaper for a seamless return experience.
     ───────────────────────────────────────────────────────────────────────────── */
  const [view, setView] = useState<"dashboard" | "documents" | "gallery" | "guardian" | "settings">(() =>
    (typeof window === "undefined" ? "dashboard" : ((localStorage.getItem("cfy.lastView") as any) || "dashboard"))
  );
  const [workspaceOpen, setWorkspaceOpen] = useState<boolean>(false);
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view); }, [view]);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("cfy.wallpaper")));

  /* ─────────────────────────────────────────────────────────────────────────────
     📄 SECTION: Document and Gallery State
     - `documents`: List of available document items, with types and colors.
     - `gallery`: List of images for the gallery view.
     - `activeDoc`: Which document is open in the workspace.
     - `openDocInPlace`: Helper to open a doc and reveal the workspace pane.
     ───────────────────────────────────────────────────────────────────────────── */
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

  /* ─────────────────────────────────────────────────────────────────────────────
     🌈 SECTION: Color Helpers and Gradient Generators
     These little functions help convert between color formats and generate
     lightened/darkened versions for backgrounds and gradients.
     ───────────────────────────────────────────────────────────────────────────── */
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

  /* ─────────────────────────────────────────────────────────────────────────────
     🖼️ SECTION: App-wide Visual Background Handling
     - If no wallpaper is set, we use a smooth color gradient based on the base color.
     - If wallpaper is set, we overlay a subtle gradient to help the theme (light/dark)
       be visually obvious, regardless of the wallpaper image.
     ───────────────────────────────────────────────────────────────────────────── */
  const accent = baseColor;
  const accentWeak = baseColor;
  const accentStrong = baseColor;
  const bgStyleNoWallpaper = (() => {
    const start = lighten(baseColor, fade * 0.6);
    const end = darken(baseColor, depth * 0.8);
    return { background: `linear-gradient(to bottom, ${start}, ${end})` } as React.CSSProperties;
  })();
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

  /* ─────────────────────────────────────────────────────────────────────────────
     🏗️ SECTION: Modular Design Token Setup
     All main layout, color, and sizing tokens are set here, so the UI can
     consistently use them for spacing, shapes, and color across views.
     ───────────────────────────────────────────────────────────────────────────── */
  const styleVars = {
    /* === GENERAL LAYOUT TOKENS === */
    "--radius-micro": "12px",                 // chips, inputs, pills
    "--radius-tile": "19px",                  // cards, tiles, panels
    "--card-radius": "var(--radius-tile)",    // pointer used by components
    "--edge-chrome": "6px",                     // Outer padding (PWA safe zone)
    "--shell-gap": "16px",                      // Gap between cards or columns
    "--viewport-radius": "19px",                // Rounding for main window
    "--tile-radius": "var(--radius-tile)",      // Default internal card rounding
    "--page-pad": "0px",                        // Can be overridden per-view

    /* === CARD GEOMETRY === */
    "--card-pad": "12px",                       // Internal card padding
    "--frame": "1px",                           // Outer frame thickness
    "--bezel": "3px",                           // Bezel around cards
    "--rim": "1px",                             // Inner rim spacing

    /* === TILE / CHIP / ELEMENT SIZING === */
    "--project-tile-size": "72px",              // Project tile square size
    "--doc-chip-height": "48px",                // Height of document chips
    "--image-tile-size": "180px",               // Square preview image size

    /* === GRID CONTROL === */
    "--image-grid-gap": "var(--shell-gap)",     // Gap between images
    "--image-grid-cols": "auto-fit",            // Can be set to fixed or responsive

    /* === DIMENSION CONSTRAINTS === */
    "--workspace-w": "24rem",                   // Sidebar fixed width
    "--min-h": "clamp(520px, 70vh, 1000px)",    // Viewport vertical floor
    "--card-height": "clamp(480px, 70vh, 800px)", // Centralized card height

    /* === COLORS & SURFACE === */
    "--panel-bg": panelBg,
    "--chip-bg": chipBg,
    "--panel-border": panelBorder,
    "--panel-bezel": panelBezel,
    "--text": textColor,
    "--muted": mutedColor,
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,

    /* === SEMANTIC FALLBACKS (legacy) === */
    "--radius": "var(--tile-radius)",           // Used in old components
    "--board-edge": "var(--edge-chrome)",       // Used in spacing wrappers
    "--gutter": "var(--shell-gap)",             // Used in layout
  } as React.CSSProperties;

  /* ─────────────────────────────────────────────────────────────────────────────
     🎨 SECTION: Extension Colors and Gallery Defaults
     - We provide default colors for file extensions and allow user overrides.
     - Gallery images are seeded with a few examples but can be customized.
     ───────────────────────────────────────────────────────────────────────────── */
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
  // Helper to open a document and reveal the workspace
  const openDocInPlace = (name: string, ext: string) => {
    setActiveDoc(`${name}.${ext}`);
    setWorkspaceOpen(true);
  };
  // Use an active wallpaper for refractive glass; fall back to first gallery image if none chosen yet
  const activeWallpaper = useMemo(() => {
    return wallpaper ?? (gallery && gallery.length > 0 ? gallery[0].src : null);
  }, [wallpaper, gallery]);

  const bp = useBreakpoint();

  // Helper to jump to Guardian chat with a prefilled prompt
  function openChatWithPrompt(p: string) { setPrefill(p); setView("guardian"); }

  // Memoized layout helper for responsive document/workspace widths using breakpoints
  const docsLayout = useMemo(() => {
    if (!workspaceOpen) {
      return { listFlex: "1 1 0%", workspaceW: "calc(0% - var(--gutter))" };
    }
    switch (bp) {
      case "sm":
      case "md":
        // On small screens, keep documents full-width and collapse the workspace column
        return { listFlex: "1 1 0%", workspaceW: "0%" };
      case "lg":
        return { listFlex: "0 0 50%", workspaceW: "calc(50% - var(--gutter))" };
      case "xl":
        return { listFlex: "0 0 45%", workspaceW: "calc(55% - var(--gutter))" };
      case "2xl":
      default:
        return { listFlex: "0 0 40%", workspaceW: "calc(60% - var(--gutter))" };
    }
  }, [bp, workspaceOpen]);

  // Responsive layout helper for Settings view
  const settingsLayout = useMemo(() => {
    // On small (sm, md) breakpoints, let the settings card fill width
    if (bp === "sm" || bp === "md") {
      return { flex: "1 1 100%", maxWidth: "none" };
    }
    // On larger screens, enforce max width (18rem)
    return { flex: "1 1 0%", maxWidth: "18rem" };
  }, [bp]);

  /* ─────────────────────────────────────────────────────────────────────────────
     🎭 SECTION: Dynamic Background Dramatic Effects
     When no wallpaper is set, we dramatically adjust background depth/fade
     based on the current theme for a more expressive look.
     ───────────────────────────────────────────────────────────────────────────── */
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

  /* ─────────────────────────────────────────────────────────────────────────────
     🚪 SECTION: Main AppShell Render
     The outermost wrappers set up the background, safe area, and design tokens.
     Inside, we render the navigation menu and the main content area, which
     switches between views like Guardian, Dashboard, Gallery, Documents, and Settings.
     ───────────────────────────────────────────────────────────────────────────── */
  return (
    <div
      className="w-screen h-screen p-[6px] box-border flex flex-col bg-transparent rounded-[19px]"
      style={{
        background: "transparent",
        padding: "6px",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        minWidth: "608px",
        minHeight: "548px",
      }}
    >
      {/* ─────────────────────────────────────────────────────────────────────────────
          🧭 SECTION: Top Navigation Bar
          This pill-shaped menu lets you switch between the major app views.
          The active view is visually highlighted.
         ───────────────────────────────────────────────────────────────────────────── */}
      <div
        className={`relative h-dvh w-full flex flex-col overflow-hidden ${resolved === "dark" ? "dark" : ""}`}
        style={{ ...backgroundStyle, ...styleVars }}
      >
      {/* {view === "dashboard" && (
        <RefractiveGlassCard
          wallpaperUrl={activeWallpaper}
          className="w-full h-full rounded-[var(--radius)]"
          style={{ background: "transparent", border: "none" }}
          intensity={0.008}
          aberration={0}
        />
      )} */}
      {/* Glass Pill Menu Bar - Left Corner */}
      <div className="relative z-10 cap-width w-full flex justify-start pt-3 px-[var(--board-edge)]">
        <div className="flex items-center gap-3 rounded-full bg-white/20 dark:bg-neutral-800/20 shadow-lg px-3 py-2 backdrop-blur-md border border-white/30 dark:border-neutral-700/30">
          <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: "#000", color: "#fff" }}>Codexify</span>
          <button onClick={() => setView("guardian")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "guardian" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Guardian</button>
          <button onClick={() => setView("dashboard")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "dashboard" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Dashboard</button>
          <button onClick={() => setView("documents")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "documents" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Documents</button>
          <button onClick={() => setView("gallery")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "gallery" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Gallery</button>
          <button onClick={() => setView("settings")} className={`px-3 py-2 rounded-full text-sm font-medium transition ${view === "settings" ? "bg-white/90 dark:bg-neutral-700/90 text-black dark:text-white" : "text-white dark:text-neutral-300 hover:bg-white/20 dark:hover:bg-neutral-700/20"}`}>Settings</button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────────
          📺 SECTION: Main Content Area
          The main workspace area. Depending on the selected view, we show:
          - Guardian chat + workspace
          - Dashboard
          - Gallery
          - Documents
          - Settings
         ───────────────────────────────────────────────────────────────────────────── */}
      <div className="relative z-10 flex flex-col flex-1 h-full min-h-0 px-[var(--board-edge)] pt-[var(--gutter)] overflow-hidden">
        <div className="flex-1 h-full min-h-0 flex">
          {view === "documents" && (
            <div style={{ "--radius": "var(--card-radius)", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)" } as React.CSSProperties}>
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
                    "--flex": docsLayout.listFlex,
                    "--min-h": "clamp(520px, 70vh, 1000px)",
                  }}
                >
                  <DocumentsView
                    documents={documents}
                    extColors={extColors}
                    onDocumentClick={openDocInPlace}
                  />
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
                      "--w": docsLayout.workspaceW,
                      "--flex": "0 0 var(--w)",
                      "--min-h": "clamp(520px, 70vh, 1000px)",
                    }}
                  >
                    <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                      <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                        <div className="relative rounded-[var(--radius)]">
<div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
  {/* Glass removed for recent column */}
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
            <div style={{ "--radius": "var(--card-radius)", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)" } as React.CSSProperties}>
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
                      <div className="relative rounded-[var(--radius)] h-full">
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
                          <div className="p-[var(--card-pad)] min-h-0 h-full overflow-auto">
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
              </div>
            </div>
          )}
          {view === "guardian" && (
            // Guardian Chat + Sidebar, with sidebar toggle
            <GuardianChatWithSidebar
              guardianName={guardianName}
              userName={userName}
              prefill={prefill}
              onPrefillConsumed={() => setPrefill(undefined)}
              onWorkspaceToggle={() => setWorkspaceOpen(!workspaceOpen)}
            />
          )}
          {view === "dashboard" && (
            <div
              className="h-full w-full"
              style={{
                "--radius": "var(--card-radius)",
                "--frame": "5px",
                "--bezel": "4px",
                "--rim": "3px",
                "--gutter": "16px",
                "--card-pad": "10px",
              } as React.CSSProperties}
            >
              {/* Main row: left = dashboard, right = optional workspace */}
              <div className="flex h-full min-h-0 w-full gap-[var(--gutter)] items-stretch">
                {/* LEFT COLUMN : behaves like one big card that scales */}
                <div
                  className="min-h-0 flex-1 overflow-visible rounded-[var(--radius)]"
                  style={{
                    padding: "var(--board-edge)",
                    flex: workspaceOpen ? "1 1 0%" : "1 1 100%",
                    minWidth: "0",
                    maxWidth: "100%",
                    minHeight: "0",
                    maxHeight: "100%",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <div
                    className="relative rounded-[var(--radius)] h-full w-full flex-1 flex flex-col"
                    style={{ flex: 1 }}
                  >
                    <DashboardView
                      extColors={extColors}
                      gallery={gallery}
                      onImagePrompt={openChatWithPrompt}
                      workspaceOpen={workspaceOpen}
                    />
                  </div>
                </div>

                {/* RIGHT COLUMN : workspace drawer */}
                {workspaceOpen && (
                  <div
                    className="rounded-[var(--radius)] shrink-0 overflow-visible"
                    style={{
                      padding: "var(--board-edge)",
                      width: "var(--workspace-w)",
                      flex: "0 0 var(--workspace-w)",
                      minHeight: "0",
                      maxHeight: "100%",
                    }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{
                        background: "var(--chip-bg)",
                        padding: "var(--frame)",
                        border: "var(--bezel) solid var(--panel-bezel)",
                      }}
                    >
                      <div
                        className="rounded-[var(--radius)]"
                        style={{
                          background:
                            "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))",
                          padding: "var(--rim)",
                        }}
                      >
                        <div className="relative rounded-[var(--radius)] h-full">
                          <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                            <RefractiveGlassCard
                              wallpaperUrl={activeWallpaper}
                              className="w-full h-full rounded-[var(--radius)]"
                              style={{ background: "transparent", border: "none" }}
                              intensity={0.006}
                              aberration={0}
                            />
                          </div>
                          <div
                            className="rounded-[var(--radius)] overflow-hidden relative h-full"
                            style={{
                              background: "var(--panel-bg)",
                              border: "1px solid var(--panel-border)",
                              boxShadow:
                                "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)",
                              filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))",
                            }}
                          >
                            <button
                              onClick={() => setWorkspaceOpen(false)}
                              className="absolute top-2 right-2 h-6 w-6 rounded-full border text-xs flex items-center justify-center hover:opacity-90"
                              style={{
                                borderColor: "var(--panel-border)",
                                color: "var(--muted)",
                                background: "var(--panel-bg)",
                              }}
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
            <div
              className="flex-1 h-full"
              style={{ "--radius": "var(--card-radius)", "--frame": "5px", "--bezel": "4px", "--rim": "3px" } as React.CSSProperties}
            >
              <div className="flex-1 h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
                <div
                  className="min-w-0 flex-1 min-h-0 h-full flex flex-col overflow-visible rounded-[var(--radius)]"
                  style={{
                    padding: "var(--board-edge)",
                    flex: settingsLayout.flex,
                    maxWidth: settingsLayout.maxWidth,
                  }}
                >
                  <div className="rounded-[var(--radius)] flex-1 flex flex-col overflow-hidden" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel) solid var(--panel-bezel)" }}>
                    <div className="rounded-[var(--radius)] flex-1 flex flex-col overflow-hidden" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)" }}>
                      <div className="relative rounded-[var(--radius)] flex-1 flex flex-col overflow-hidden">
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.006}
                            aberration={0}
                          />
                        </div>
                        <div className="min-h-0 w-full rounded-[var(--radius)] overflow-hidden flex-1 flex flex-col" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))" }}>
                          <div className="min-h-0 h-full w-full overflow-auto p-[var(--card-pad)] flex-1 flex flex-col">
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
    </div>
  );
}

function GuardianChatWithSidebar({ guardianName, userName, prefill, onPrefillConsumed, onWorkspaceToggle }) {
  const [isSidebarVisible, setIsSidebarVisible] = React.useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = React.useState(false);
  const { wallpaperUrl } = useWallpaperUrl();
  const bp = useBreakpoint();
  const [threads, setThreads] = React.useState<Thread[]>([
    {
      id: "t1",
      title: "Design Sync",
      lastMessage: "Let's ship the new message bubbles today.",
      unread: 2,
      participants: [
        { id: "me", name: userName },
        { id: "bot", name: guardianName },
      ],
      messages: [
        { id: "m1", authorId: "bot", authorName: guardianName, content: "Morning! Did you see the updated chat bubble spec?", createdAt: Date.now() - 1000 * 60 * 60, status: "read" },
        { id: "m2", authorId: "me", authorName: userName, content: "Yep—looks great. The drop shadows feel a bit heavy though.", createdAt: Date.now() - 1000 * 60 * 58, status: "read" },
        { id: "m3", authorId: "bot", authorName: guardianName, content: "Agreed. I lightened them and added a subtle border.", createdAt: Date.now() - 1000 * 60 * 42, status: "read" },
      ],
    },
  ]);
  const [activeId, setActiveId] = React.useState<string>("t1");
  const activeThread = React.useMemo(() => threads.find((t) => t.id === activeId)!, [threads, activeId]);

  const handleHideSidebar = () => setIsSidebarVisible(false);
  const handleShowSidebar = () => setIsSidebarVisible(true);

  const handleNewChat = () => {
    const id = `t_${Date.now()}`;
    setThreads((prev) => [
      { id, title: "New Chat", lastMessage: "", unread: 0, participants: [{ id: "me", name: userName }, { id: "bot", name: guardianName }], messages: [] },
      ...prev,
    ]);
    setActiveId(id);
  };

  const handleSendMessage = (text: string) => {
    const newMsg: Message = { id: String(Math.random()), authorId: "me", authorName: userName, content: text, createdAt: Date.now(), status: "sending" };
    setThreads((prev) => prev.map((t) => (t.id === activeId ? { ...t, messages: [...t.messages, newMsg], lastMessage: text } : t)));
    setTimeout(() => {
      setThreads((prev) => prev.map((t) => (t.id === activeId ? { ...t, messages: t.messages.map((m) => (m.id === newMsg.id ? { ...m, status: "sent" } : m)) } : t)));
    }, 300);
  };

  return (
    <>
      

      

      <div
        className={`flex-1 min-h-0 h-full flex transition-all duration-300`}
      >
        {/* Backdrop (only < lg) */}
        <div
          className={`fixed inset-0 bg-black/50 z-40 transition-opacity lg:hidden ${
            isMobileSidebarOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          }`}
          onClick={() => setIsMobileSidebarOpen(false)}
        />

        {/* Slide-over drawer (only < lg) */}
        <aside
          className={`fixed inset-y-0 left-0 w-64 bg-[var(--chip-bg)] p-[var(--board-edge)] z-50 transform transition-transform duration-300 lg:hidden ${
            isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <Sidebar
            threads={threads}
            activeId={activeId}
            onSelect={setActiveId}
            onNewChat={handleNewChat}
          />
        </aside>

        {isSidebarVisible && (
          <div className={`hidden lg:flex h-full min-h-0 w-[360px] max-w-[360px] min-w-[280px]`}>
              <div className="h-full rounded-[var(--radius)] flex-1 min-h-0" style={{ padding: "var(--board-edge)" }}>
                  <div className="rounded-[var(--radius)] h-full min-h-0" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}>
                      <div className="rounded-[var(--radius)] h-full min-h-0" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))", padding: "var(--rim)" }}>
                          <div className="relative rounded-[var(--radius)] h-full min-h-0">
                              <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                                  <RefractiveGlassCard wallpaperUrl={wallpaperUrl} className="w-full h-full rounded-[var(--radius)]" style={{ background: "transparent", border: "none" }} intensity={0.008} />
                              </div>
                              <div className="min-h-0 h-full rounded-[var(--radius)] overflow-hidden flex flex-col" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
                                  <div className="min-h-0 flex-1 overflow-auto h-full">
                                      <Sidebar
                                          threads={threads}
                                          activeId={activeId}
                                          onSelect={setActiveId}
                                          onNewChat={handleNewChat}
                                      />
                                  </div>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
        )}
        <div className="relative flex flex-col flex-1 h-full min-h-0">
          {/* show sidebar when hidden */}
          {/* Removed conditional chevron toggle */}
          {activeThread && (
            <div
              className="flex-1 min-h-0 flex flex-col rounded-[var(--radius)] overflow-hidden w-full"
            >
              <GuardianChat
                guardianName={guardianName}
                userName={userName}
                prefill={prefill}
                onPrefillConsumed={onPrefillConsumed}
                onWorkspaceToggle={onWorkspaceToggle}
                isSidebarVisible={isSidebarVisible}
                onHideSidebar={handleHideSidebar}
                activeThread={activeThread}
                onSendMessage={handleSendMessage}
                onNewChat={handleNewChat}
              />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
