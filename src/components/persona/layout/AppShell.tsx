import { PropsWithChildren, useEffect, useState } from "react"

export function AppShell({ children }: PropsWithChildren) {
  const [dark, setDark] = useState(true)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])

  return (
    <div className="min-h-screen grid grid-cols-[264px_1fr]">
      <aside className="border-r border-muted/50 bg-surface p-4">
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
        <header className="border-b border-muted/50 bg-surface px-4 flex items-center justify-between">
          <div className="opacity-90">Codexify</div>
          <button
            className="text-sm px-2 py-1 rounded border border-muted/50 hover:bg-muted/30"
            onClick={() => setDark(!dark)}
          >
            {dark ? "Light" : "Dark"}
          </button>
        </header>

        <main className="p-4">{children}</main>
      </div>
    </div>
  )
}

export default AppShell