import { Card } from "@/components/ui/card";

export function WorkspacePane() {
  return (
    <aside className="hidden lg:flex w-[360px] shrink-0 flex-col ml-3">
      <Card className="flex-1 rounded-2xl border shadow-sm overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)", backdropFilter: "blur(12px) saturate(120%)", WebkitBackdropFilter: "blur(12px) saturate(120%)", borderColor: "var(--panel-border)", boxShadow: "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.25), 0 10px 22px rgba(0,0,0,0.25)" }}>
        <div className="p-3 border-b" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Workspace
          </div>
        </div>
        <div className="p-3 space-y-4" style={{ color: "var(--text)" }}>
          <div>
            <div className="text-xs font-semibold opacity-70">PROJECTS</div>
            <div className="mt-2 space-y-2">
              {["Sovereign AI Principles", "Health & Wellness"].map((p) => (
                <div key={p} className="rounded-md px-3 py-2" style={{ background: "var(--chip-bg)", border: "1px solid var(--panel-border)" }}>
                  {p}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold opacity-70">DOCS</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {["Covenant.pdf", "Roadmap.md", "Vision.txt", "Design.sketch"].map((d) => (
                <div key={d} className="rounded-md px-3 py-2 text-sm text-center" style={{ background: "var(--chip-bg)", border: "1px solid var(--panel-border)" }}>
                  {d}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </aside>
  );
}

export default WorkspacePane;

