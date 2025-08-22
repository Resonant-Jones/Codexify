import { PropsWithChildren, useEffect, useMemo, useState } from "react"
import { Sun, Moon } from "lucide-react"

type ThemeMode = "light" | "dark" | "system"

type Resolved = "light" | "dark"

function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system"
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

export function AppShell({ children }: PropsWithChildren) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system"
    const raw = window.localStorage.getItem("cfy.themeMode")
    return coerceMode(raw)
  })
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true
    return window.matchMedia("(prefers-color-scheme: dark)").matches
  })
  const [sessionOverride, setSessionOverride] = useState<Resolved | null>(() => readSessionOverride())

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
    if (sessionOverride) return sessionOverride
    if (mode === "dark") return "dark"
    if (mode === "light") return "light"
    return systemPrefersDark ? "dark" : "light"
  }, [mode, systemPrefersDark, sessionOverride])

  useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.classList.toggle("dark", resolved === "dark")
  }, [resolved])

  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem("cfy.themeMode", mode)
  }, [mode])

  const toggleLightDark = () => {
    const next: Resolved = resolved === "dark" ? "light" : "dark"
    setSessionOverride(next)
    writeSessionOverride(next)
  }

  return (
    <div className="min-h-screen grid grid-cols-[264px_1fr]">
      <aside className="bg-surface p-4">
        <div className="font-semibold mb-4">ThreadSpace</div>
        <nav className="space-y-2 text-sm opacity-80">
          <a href="#" className="block hover:opacity-100">Dashboard</a>
          <a href="#" className="block hover:opacity-100">Threads</a>
          <a href="#" className="block hover:opacity-100">Memory</a>
          <a href="#" className="block hover:opacity-100">Research</a>
          <a href="#" className="block hover:opacity-100">Settings</a>
        </nav>
      </aside>

      <div className="grid grid-rows-[56px_1fr]">
        <header className="bg-surface px-4 flex items-center justify-between">
          <div className="opacity-90">Codexify</div>
          <button
            className="h-8 w-8 grid place-items-center rounded-md border border-muted/50 hover:bg-muted/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ outlineColor: "var(--accent-weak)" }}
            onClick={toggleLightDark}
            aria-label={`Theme: ${resolved}`}
            title={`Theme: ${resolved}`}
          >
            {resolved === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </header>

        <main className="p-4">{children}</main>
      </div>
    </div>
  )
}

export default AppShell