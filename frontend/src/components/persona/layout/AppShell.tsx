/**
 * TODO: TOKEN MIGRATION PLAN — Codexify UI Architecture
 *
 * Current state:
 *   - Inline CSS variables declared directly in AppShell serve as runtime design tokens.
 *   - Variables like `--bezel`, `--rim`, `--panel-bg`, etc., are effectively local tokens.
 *
 * Next phase:
 *   - Extract all static vars into `/src/theme/tokens.json`.
 *   - Create `/src/theme/index.ts` to import JSON and export `cssVars` for React + CSS injection.
 *   - Optional: Add Style Dictionary or a simple script to export Figma/Swift/React Native tokens.
 *
 * Goal:
 *   - Establish a universal token layer for Codexify and PulseOS.
 *   - Maintain parity across Web, Electron, and mobile builds.
 *
 * Notes:
 *   - Do NOT rename the existing CSS vars — their current names are the future token keys.
 *   - Migration should be trivial if naming consistency is preserved.
 */
import api from "@/lib/api";
import React, { PropsWithChildren, useCallback, useEffect, useMemo, useState } from "react";

// Global font injection for Apple system font
if (typeof window !== "undefined") {
  document.documentElement.style.fontFamily =
    'SF Pro Display, SF Pro Icons, Apple System, BlinkMacSystemFont, ".SFNSDisplay-Regular", "Helvetica Neue", Helvetica, Arial, sans-serif';
}
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import GuardianChat from "@/features/chat/GuardianChat";
import ProviderSwitchFAB from "@/components/ProviderSwitchFAB";
import WorkspacePane from "@/features/workspace/WorkspacePane";
import DashboardView from "@/components/dashboard/DashboardView";
import SettingsView from "@/features/settings/SettingsView";
import ErrorBoundary from "@/components/ErrorBoundary";
import DocumentsView from "@/components/documents/DocumentsView";
import Sidebar from "@/components/chat/Sidebar";
import GuardianChatWithSidebar from "@/components/persona/layout/GuardianChatWithSidebar";
import { useBreakpoint } from "./useBreakpoint";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { useLiveEvents } from "@/hooks/useLiveEvents";
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
   - Keep aberration off on glass: <FrameCard liquidBezel shimmer tone="base"… aberration={0} />
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

function hexToRgbChannels(input: string): { r: number; g: number; b: number } | null {
  if (!input) return null;
  const value = input.trim();
  const match = value.match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!match) return null;
  let hex = match[1];
  if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
  const num = Number.parseInt(hex, 16);
  if (Number.isNaN(num)) return null;
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function relativeLuminanceFromHex(color: string): number {
  const rgb = hexToRgbChannels(color);
  if (!rgb) return 0;
  const srgb = (c: number) => {
    const channel = c / 255;
    return channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  };
  const R = srgb(rgb.r);
  const G = srgb(rgb.g);
  const B = srgb(rgb.b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function getReadableTextColor(base: string): string {
  const luminance = relativeLuminanceFromHex(base);
  return luminance > 0.55 ? "#111827" : "#F9FAFB";
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
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [projectModalSaving, setProjectModalSaving] = useState(false);
  const [projectModalName, setProjectModalName] = useState("");
  const [projectModalIcon, setProjectModalIcon] = useState("📁");
  const [projectModalError, setProjectModalError] = useState<string | null>(null);

  const openCreateProjectModal = React.useCallback(() => {
    setProjectModalError(null);
    setProjectModalName("");
    setProjectModalIcon("📁");
    setProjectModalOpen(true);
  }, []);

  const closeCreateProjectModal = React.useCallback(() => {
    if (projectModalSaving) return;
    setProjectModalOpen(false);
  }, [projectModalSaving]);

  React.useEffect(() => {
    if (!projectModalOpen) {
      setProjectModalName("");
      setProjectModalIcon("📁");
      setProjectModalError(null);
    }
  }, [projectModalOpen]);

  React.useEffect(() => {
    if (projectModalOpen && view !== "dashboard") {
      setProjectModalOpen(false);
    }
  }, [view, projectModalOpen]);

  const handleProjectSubmit = React.useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedName = projectModalName.trim();
      if (!trimmedName) {
        setProjectModalError("Project name is required.");
        return;
      }
      setProjectModalSaving(true);
      setProjectModalError(null);
      const iconValue = projectModalIcon.trim() || "📁";
      try {
        const response = await api.post("/projects", { name: trimmedName, icon: iconValue });
        try {
          window.dispatchEvent(
            new CustomEvent("cfy:projects:refresh", {
              detail: {
                id: response?.data?.id ?? response?.data?.project_id ?? null,
                name: trimmedName,
                icon: iconValue,
              },
            })
          );
        } catch {
          // Ignore DOM errors for non-browser environments
        }
        setProjectModalOpen(false);
      } catch (err: any) {
        const message =
          err?.response?.data?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to create project.";
        setProjectModalError(message);
      } finally {
        setProjectModalSaving(false);
      }
    },
    [projectModalIcon, projectModalName]
  );
  useEffect(() => { if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view); }, [view]);
  // Sync the main view with URL when landing directly on /chat/:id
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (window.location.pathname.startsWith("/chat/")) {
        setView("guardian");
      }
    }
  }, []);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop" : localStorage.getItem("cfy.wallpaper")));

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
  // Utility: parse a number from unknown input, fall back & clamp to [0,1]
  function safeNumber(val: unknown, fallback: number): number {
    const n = Number(val);
    return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : fallback;
  }
  const [depth, setDepth] = useState<number>(() => {
    if (typeof window === "undefined") return 0.6;
    return safeNumber(localStorage.getItem("cfy.depth"), 0.6);
  });
  const [fade, setFade] = useState<number>(() => {
    if (typeof window === "undefined") return 0.4;
    return safeNumber(localStorage.getItem("cfy.fade"), 0.4);
  });
  const [dashboardThreadRows, setDashboardThreadRows] = useState<number>(() => {
    if (typeof window === "undefined") return 2;
    const raw = Number(window.localStorage.getItem("cfy.dashboard.threadRows"));
    if (!Number.isFinite(raw)) return 2;
    return Math.max(1, Math.min(4, Math.round(raw)));
  });
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.baseColor", baseColor);
      localStorage.setItem("cfy.depth", String(depth));
      localStorage.setItem("cfy.fade", String(fade));
    }
  }, [baseColor, depth, fade]);
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("cfy.dashboard.threadRows", String(dashboardThreadRows));
    }
  }, [dashboardThreadRows]);

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
  const accentContrast = getReadableTextColor(accentStrong);
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
  const panelSheet = resolved === "dark" ? "#1b1b1d" : "#f1ede8";
  const panelBg = panelSheet;
  const chipBg = resolved === "dark" ? "#262629" : "#e9e4dc";
  // Global: soften panel border
  const panelBorder = resolved === "dark" ? "rgba(255,255,255,0.10)" : "rgba(17,24,39,0.08)";
  const panelSheetBorder = resolved === "dark" ? "rgba(255,255,255,0.18)" : "rgba(17,24,39,0.14)";
  const textColor = resolved === "dark" ? "#ffffff" : "#111827";
  const mutedColor = resolved === "dark" ? "rgba(255,255,255,0.88)" : "#374151";
  // Local-only: translucent bezel for Dashboard cards
  const panelBezel = resolved === "dark" ? "rgba(255,255,255,0.14)" : "rgba(17,24,39,0.12)";
  const panelBorderStrong = resolved === "dark" ? "rgba(255,255,255,0.22)" : "rgba(17,24,39,0.16)";

  /* ─────────────────────────────────────────────────────────────────────────────
     🏗️ SECTION: Modular Design Token Setup
     All main layout, color, and sizing tokens are set here, so the UI can
     consistently use them for spacing, shapes, and color across views.
     ───────────────────────────────────────────────────────────────────────────── */
  const styleVars = {
    /* === GENERAL LAYOUT TOKENS === */
    "--radius-micro": "12px",                 // chips, inputs, pills
    "--radius-tile": "19px",                  // cards, tiles, panels
    "--card-radius": "19px",    // pointer used by components (explicit for clarity)
    "--edge-chrome": "6px",                     // Outer padding (PWA safe zone)
    "--shell-gap": "16px",                      // Gap between cards or columns
    "--viewport-radius": "19px",                // Rounding for main window
    "--tile-radius": "var(--radius-tile)",      // Default internal card rounding
    "--page-pad": "0px",                        // Can be overridden per-view

    /* === CARD GEOMETRY === */
    "--card-pad": "12px",                       // Internal card padding
    "--frame": "1.5px",                         // Outer frame thickness
    // --bezel: Visual margin between the refractive glass and the opaque content surface.
    // Changing this variable tunes the glass thickness everywhere.
    "--bezel": "var(--bezel, 6px)",             // Bezel (margin) between glass and content (default 6px)
    "--rim": "1.5px",                           // Inner rim spacing

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
    "--panel-sheet": panelSheet,
    "--panel-sheet-border": panelSheetBorder,
    "--panel-border-strong": panelBorderStrong,
    "--chip-bg": chipBg,
    "--panel-border": panelBorder,
    "--panel-bezel": panelBezel,
    "--text": textColor,
    "--muted": mutedColor,
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,
    "--pill-active-text": accentContrast,

    /* === SEMANTIC FALLBACKS (legacy) === */
    "--radius": "var(--tile-radius)",           // Used in old components
    "--board-edge": "var(--edge-chrome)",       // Used in spacing wrappers
    "--gutter": "var(--shell-gap)",             // Used in layout
    // --bezel is also set at the main viewport for live tuning of glass thickness
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
  const openDocInThread = (name: string, ext: string) => {
    const fullName = `${name}.${ext}`;
    setActiveDoc(fullName);
    setWorkspaceOpen(true);
    setView("guardian");
    setPrefill(`Let's review "${fullName}".`);
  };
  const openDocFromWorkspace = (doc: string) => {
    if (!doc) return;
    const lastDot = doc.lastIndexOf(".");
    if (lastDot === -1) {
      setActiveDoc(doc);
      setWorkspaceOpen(true);
      setView("guardian");
      return;
    }
    const base = doc.slice(0, lastDot);
    const extension = doc.slice(lastDot + 1);
    openDocInThread(base, extension);
  };
  const createThreadFromDashboard = useCallback(async () => {
    const userId = userName || "default";
    try {
      const response = await api.post("/chat/threads", { title: "New Chat", user_id: userId });
      const payload = response?.data ?? {};
      const threadLike = payload.thread ?? payload;
      const newId = threadLike?.id ?? threadLike?.thread_id ?? payload?.id;
      if (!newId) {
        console.warn("[dashboard] create thread succeeded without id");
        return;
      }
      const idStr = String(newId);
      // Notify sidebar/guardian surfaces so the freshly-created thread appears immediately.
      if (typeof window !== "undefined") {
        try {
          window.dispatchEvent(new CustomEvent("cfy:threads:refresh", { detail: { kind: "create", id: idStr } }));
        } catch (eventErr) {
          console.warn("[dashboard] thread refresh event failed", eventErr);
        }
      }
      setPrefill(undefined);
      setWorkspaceOpen(false);
      setView("guardian");
      if (typeof window !== "undefined") {
        window.history.pushState({}, "", `/chat/${idStr}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
    } catch (err) {
      console.warn("[dashboard] failed to create thread", err);
    }
  }, [userName]);
  // Use an active wallpaper for refractive glass; fall back to first gallery image if none chosen yet
  const activeWallpaper = useMemo(() => {
    return wallpaper ?? (gallery && gallery.length > 0 ? gallery[0].src : "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop");
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
    <>
      {/* 
        --bezel: Visual margin between the refractive glass and the opaque content surface.
        Changing --bezel allows live tuning of the glass thickness throughout the UI without code edits.
      */}
      <div
        className="w-screen h-screen flex flex-col bg-transparent box-border overflow-hidden"
        style={{
          /* baseline viewport guardrails */
          minWidth: "608px",
          minHeight: "548px",
          padding: "6px",
          alignItems: "center",

          /* ✨ glossy‑glass overrides */
          "--tile-blur": "22px",                       // stronger backdrop blur
          "--bezel": "6px",                            // bezel (glass margin) can be tuned here
          "--lip-w": "6px",                            // deeper inner lip
          "--depth-scale": "1.35",                     // bolder drop‑shadow scale
          "--panel-bezel": "rgba(255,255,255,0.28)",   // brighter edge sparkle
          "--panel-bg": "rgba(17,24,39,0.72)",         // translucent dark fill

          /* merge global scene tokens & gradient/wallpaper */
          ...backgroundStyle,
          ...styleVars,

          // Apple system font at root layout level
          fontFamily:
            'SF Pro Display, SF Pro Icons, Apple System, BlinkMacSystemFont, ".SFNSDisplay-Regular", "Helvetica Neue", Helvetica, Arial, sans-serif',
        } as React.CSSProperties}
      >
      {/* Global outer glass skin */}
      <div className="absolute inset-0 -z-10 pointer-events-none rounded-[19px] overflow-hidden">
        <RefractiveGlassCard
          wallpaperUrl={activeWallpaper}
          className="w-full h-full rounded-[19px]"
          style={{ background: "transparent", border: "none" }}
          intensity={0.008}
          aberration={0}
        />
      </div>
      <div
        className={`relative h-full w-full isolate flex flex-col overflow-hidden py-[var(--edge-chrome)] mx-auto ${resolved === "dark" ? "dark" : ""}`}
        style={{
          ...backgroundStyle,
          ...styleVars,
          borderRadius: "19px",
          paddingLeft: "6px",
          paddingRight: "6px",
          boxSizing: "border-box",
        }}
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
      <div className="relative z-10 w-full flex justify-start">
        <div className="glass-pill isolate">
          {/* glass backdrop */}
          <div className="absolute inset-0 -z-10 overflow-hidden rounded-full pointer-events-none">
            <RefractiveGlassCard
              wallpaperUrl={activeWallpaper}
              className="w-full h-full rounded-full"
              style={{ background: "transparent", border: "none" }}
              intensity={0.006}
              aberration={0}
            />
          </div>

          {/* brand badge */}
          <span className="pill-tab brand-tab">Codexify</span>

          {/* nav tabs */}
          <button
            className="pill-tab"
            data-state={view === "guardian" ? "active" : "inactive"}
            onClick={() => setView("guardian")}
          >
            Guardian
          </button>
          <button
            className="pill-tab"
            data-state={view === "dashboard" ? "active" : "inactive"}
            onClick={() => setView("dashboard")}
          >
            Dashboard
          </button>
          <button
            className="pill-tab"
            data-state={view === "documents" ? "active" : "inactive"}
            onClick={() => setView("documents")}
          >
            Documents
          </button>
          <button
            className="pill-tab"
            data-state={view === "gallery" ? "active" : "inactive"}
            onClick={() => setView("gallery")}
          >
            Gallery
          </button>
          <button
            className="pill-tab"
            data-state={view === "settings" ? "active" : "inactive"}
            onClick={() => setView("settings")}
          >
            Settings
          </button>
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
      <div className="relative z-10 isolate flex flex-col flex-1 h-full min-h-0 overflow-hidden items-stretch justify-center">
        <div className="flex-1 h-full min-h-0 flex">
          {view === "documents" && (
            <div
              className="isolate"
              style={{
                "--radius": "var(--card-radius)",
                "--frame": "1px",
                "--bezel": "var(--bezel, 6px)",
                "--rim": "1px",
                "--gutter": "16px",
                "--card-pad": "10px",
                "--min-h": "clamp(520px, 70vh, 1000px)",
                borderRadius: "var(--card-radius)",
                padding: "var(--bezel, 6px)"
              } as React.CSSProperties}
            >
              <div className="h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
                {/* LIST COLUMN (left) */}
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
                    ["--flex"]: docsLayout.listFlex,
                    ["--min-h"]: "clamp(520px, 70vh, 1000px)",
                    borderRadius: "var(--card-radius)"
                  }}
                >
                  <div
                    className="rounded-[var(--radius)]"
                    style={{
                      background: "var(--chip-bg)",
                      padding: "var(--frame)",
                      border: "var(--bezel, 6px) solid var(--panel-bezel)",
                      borderRadius: "var(--card-radius)"
                    }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{
                        background:
                          "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))",
                        padding: "var(--rim)",
                        borderRadius: "var(--card-radius)"
                      }}
                    >
                      <div className="relative rounded-[var(--radius)] h-full">
                        {/* glass behind content */}
                        <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                          <RefractiveGlassCard
                            wallpaperUrl={activeWallpaper}
                            className="w-full h-full rounded-[var(--radius)]"
                            style={{ background: "transparent", border: "none" }}
                            intensity={0.006}
                            aberration={0}
                          />
                        </div>

                        {/* clipped panel surface */}
                        <div
                          className="rounded-[var(--radius)] overflow-hidden relative"
                          style={{
                            clipPath: "inset(0 round var(--radius))",
                            background: "var(--panel-bg)",
                          border: "1px solid var(--panel-border)",
                            boxShadow:
                              "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)",
                            filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))",
                            borderRadius: "var(--card-radius)"
                          }}
                        >
                          <div className="p-[var(--card-pad)]">
                            <DocumentsView
                              documents={documents}
                              extColors={extColors}
                              onDocumentClick={openDocInPlace}
                              onOpenInThread={openDocInThread}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* WORKSPACE COLUMN (right) */}
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
                      ["--w"]: docsLayout.workspaceW,
                      ["--flex"]: "0 0 var(--w)",
                      ["--min-h"]: "clamp(520px, 70vh, 1000px)",
                      borderRadius: "var(--card-radius)"
                    }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{
                        background: "var(--chip-bg)",
                      padding: "var(--frame)",
                      border: "var(--bezel, 6px) solid var(--panel-bezel)",
                        borderRadius: "var(--card-radius)"
                      }}
                    >
                      <div
                        className="rounded-[var(--radius)]"
                        style={{
                          background:
                            "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))",
                          padding: "var(--rim)",
                          borderRadius: "var(--card-radius)"
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
                              clipPath: "inset(0 round var(--radius))",
                              background: "var(--panel-bg)",
                            border: "1px solid var(--panel-border)",
                              boxShadow:
                                "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)",
                              filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))",
                              borderRadius: "var(--card-radius)"
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
                            <WorkspacePane activeDoc={activeDoc} onOpenInThread={openDocFromWorkspace} />
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
            <div className="isolate" style={{ "--radius": "var(--card-radius)", "--frame": "1px", "--bezel": "var(--bezel, 6px)", "--rim": "1px", "--gutter": "6px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)", borderRadius: "var(--card-radius)", padding: "var(--bezel, 6px)" } as React.CSSProperties}>
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
                    borderRadius: "var(--card-radius)"
                  }}
                >
                  <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel, 6px) solid var(--panel-bezel)", borderRadius: "var(--card-radius)" }}>
                    <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)", borderRadius: "var(--card-radius)" }}>
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
                        <div className="min-h-0 h-full overflow-hidden rounded-[var(--radius)]" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))", borderRadius: "var(--card-radius)" }}>
                          <div className="p-[var(--card-pad)] min-h-0 h-full overflow-auto">
                            <div className="text-sm opacity-80 mb-2" style={{ color: "var(--muted)" }}>Gallery</div>
                            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-[var(--gutter)]">
                              {gallery.map((g, i) => (
                                <div key={i} className="aspect-square rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))", borderRadius: "var(--card-radius)" }}>
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
            <div
              className="flex-1 h-full w-full min-h-0 isolate flex flex-col"
              style={{
                "--frame": "1px",
                "--bezel": "var(--bezel, 6px)",
                "--rim": "1px",
                height: "100%",
                width: "100%",
                display: "flex",
                flexDirection: "column",
              } as React.CSSProperties}
            >
              <ErrorBoundary>
                <GuardianChatWithSidebar
                  guardianName={guardianName}
                  userName={userName}
                  prefill={prefill}
                  onPrefillConsumed={() => setPrefill(undefined)}
                  onWorkspaceToggle={() => setWorkspaceOpen(!workspaceOpen)}
                />
              </ErrorBoundary>
            </div>
          )}
          {view === "dashboard" && (
            <div
              className="h-full w-full isolate"
              style={{ "--gutter": "16px", padding: "var(--bezel, 6px)" } as React.CSSProperties}
            >
              <div className="flex h-full min-h-0 w-full gap-[var(--gutter)] items-stretch">
                <div className="min-h-0 flex-1">
                  <DashboardView
                    extColors={extColors}
                    gallery={gallery}
                    onImagePrompt={openChatWithPrompt}
                    onRequestNewProject={openCreateProjectModal}
                    onRequestNewThread={createThreadFromDashboard}
                    onNavigateDocuments={() => setView("documents")}
                    onNavigateGallery={() => setView("gallery")}
                    threadGridRows={dashboardThreadRows}
                  />
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
                      borderRadius: "var(--card-radius)"
                    }}
                  >
                    <div
                      className="rounded-[var(--radius)]"
                      style={{
                        background: "var(--chip-bg)",
                        padding: "var(--frame)",
                        border: "var(--bezel, 6px) solid var(--panel-bezel)",
                        borderRadius: "var(--card-radius)"
                      }}
                    >
                      <div
                        className="rounded-[var(--radius)]"
                        style={{
                          background:
                            "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))",
                          padding: "var(--rim)",
                          borderRadius: "var(--card-radius)"
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
                              borderRadius: "var(--card-radius)"
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
                            <WorkspacePane activeDoc={activeDoc} onOpenInThread={openDocFromWorkspace} />
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
              className="flex-1 h-full isolate"
              style={{ "--radius": "var(--card-radius)", "--frame": "1px", "--bezel": "var(--bezel, 6px)", "--rim": "1px", borderRadius: "var(--card-radius)", padding: "var(--bezel, 6px)" } as React.CSSProperties}
            >
              <div className="flex-1 h-full min-h-0 w-full flex items-stretch gap-[var(--gutter)]">
                <div
                  className="min-w-0 flex-1 min-h-0 h-full flex flex-col overflow-visible rounded-[var(--radius)]"
                  style={{
                    padding: "var(--board-edge)",
                    flex: settingsLayout.flex,
                    maxWidth: settingsLayout.maxWidth,
                    borderRadius: "var(--card-radius)"
                  }}
                >
                  <div className="rounded-[var(--radius)] flex-1 flex flex-col overflow-hidden" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "var(--bezel, 6px) solid var(--panel-bezel)", borderRadius: "var(--card-radius)" }}>
                    <div className="rounded-[var(--radius)] flex-1 flex flex-col overflow-hidden" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00))", padding: "var(--rim)", borderRadius: "var(--card-radius)" }}>
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
                        <div className="min-h-0 w-full rounded-[var(--radius)] overflow-hidden flex-1 flex flex-col" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 17px rgba(0,0,0,0.18)", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.25))", borderRadius: "var(--card-radius)" }}>
                          <div className="min-h-0 h-full w-full overflow-auto p-[var(--card-pad)] flex-1 flex flex-col">
                            <div className="max-w-5xl mr-auto w-full">
                              <ErrorBoundary>
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
                                  dashboardThreadRows={dashboardThreadRows}
                                  setDashboardThreadRows={setDashboardThreadRows}
                                />
                              </ErrorBoundary>
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
      {projectModalOpen && (
        <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={closeCreateProjectModal}
          />
          <form
            onSubmit={handleProjectSubmit}
            className="relative z-[1201] w-[min(480px,90vw)] rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          >
            <div>
              <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
                Create Project
              </h2>
              <p className="text-sm mt-1 opacity-70" style={{ color: "var(--muted)" }}>
                Name your project and optionally pick an icon for quick recognition.
              </p>
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="projectName" style={{ color: "var(--text)" }}>
                  Project name
                </label>
                <Input
                  id="projectName"
                  value={projectModalName}
                  onChange={(event) => setProjectModalName(event.target.value)}
                  placeholder="e.g., Research, Launch Prep…"
                  className="rounded-xl"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                  disabled={projectModalSaving}
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="projectIcon" style={{ color: "var(--text)" }}>
                  Icon (optional)
                </label>
                <Input
                  id="projectIcon"
                  value={projectModalIcon}
                  onChange={(event) => setProjectModalIcon(event.target.value)}
                  placeholder="📁"
                  className="rounded-xl"
                  style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
                  disabled={projectModalSaving}
                />
              </div>
              {projectModalError && (
                <div className="text-sm font-medium text-red-400">
                  {projectModalError}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={closeCreateProjectModal}
                disabled={projectModalSaving}
                className="rounded-full px-4"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="rounded-full px-4"
                disabled={projectModalSaving}
              >
                {projectModalSaving ? "Creating…" : "Create Project"}
              </Button>
            </div>
          </form>
        </div>
      )}
      </div>
    </>
  );
}
