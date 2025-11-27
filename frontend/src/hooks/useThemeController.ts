import { useEffect, useMemo, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

export function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

const SESSION_KEY = "cfy.sessionTheme";
const SESSION_UNTIL = "cfy.sessionThemeUntil";

function nextLocalMidnight() {
  const d = new Date();
  d.setHours(24, 0, 0, 0);
  return d.getTime();
}

function readSessionOverride(): "light" | "dark" | null {
  if (typeof window === "undefined") return null;
  try {
    const untilRaw = window.localStorage.getItem(SESSION_UNTIL);
    if (!untilRaw) return null;
    const until = Number(untilRaw);
    if (!Number.isFinite(until) || Date.now() > until) {
      window.localStorage.removeItem(SESSION_KEY);
      window.localStorage.removeItem(SESSION_UNTIL);
      return null;
    }
    const v = window.localStorage.getItem(SESSION_KEY);
    return v === "dark" || v === "light" ? v : null;
  } catch {
    return null;
  }
}

function writeSessionOverride(v: "light" | "dark" | null) {
  if (typeof window === "undefined") return;
  if (v == null) {
    window.localStorage.removeItem(SESSION_KEY);
    window.localStorage.removeItem(SESSION_UNTIL);
  } else {
    window.localStorage.setItem(SESSION_KEY, v);
    window.localStorage.setItem(SESSION_UNTIL, String(nextLocalMidnight()));
  }
}

export function useThemeController() {
  const [mode, setMode] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const raw = window.localStorage.getItem("cfy.themeMode");
    return coerceMode(raw);
  });
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [sessionOverride, setSessionOverride] = useState<"light" | "dark" | null>(() => readSessionOverride());

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mm = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setSystemPrefersDark(mm.matches);
    if (mm.addEventListener) mm.addEventListener("change", handler);
    else mm.addListener(handler);
    return () => {
      if (mm.removeEventListener) mm.removeEventListener("change", handler);
      else mm.removeListener(handler);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEY || e.key === SESSION_UNTIL) setSessionOverride(readSessionOverride());
      if (e.key === "cfy.themeMode") setMode(coerceMode(window.localStorage.getItem("cfy.themeMode")));
    };
    window.addEventListener("storage", onStorage);
    const t = window.setInterval(() => setSessionOverride(readSessionOverride()), 60_000);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.clearInterval(t);
    };
  }, []);

  const resolved: "light" | "dark" = useMemo(() => {
    if (sessionOverride) return sessionOverride;
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return systemPrefersDark ? "dark" : "light";
  }, [mode, systemPrefersDark, sessionOverride]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, [resolved]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cfy.themeMode", mode);
  }, [mode]);

  return { mode, setMode, resolved, setSessionOverride: writeSessionOverride } as const;
}
