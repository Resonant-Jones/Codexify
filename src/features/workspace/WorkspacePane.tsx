import React, { useEffect, useState } from "react";
import LayeredCard from "@/components/ui/LayeredCard";

type Doc = { id?: string; name: string; ext?: string; updatedAt?: string };

export default function WorkspacePane() {
  const [documents, setDocuments] = useState<Doc[] | null>(null);

  useEffect(() => {
    try {
      // @ts-ignore
      if (window.__APP_DOCUMENTS__ && Array.isArray(window.__APP_DOCUMENTS__)) {
        // @ts-ignore
        setDocuments(window.__APP_DOCUMENTS__);
        console.debug("WorkspacePane: loaded documents from window.__APP_DOCUMENTS__");
        return;
      }
    } catch (e) {}

    try {
      const raw = localStorage.getItem("app:documents");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setDocuments(parsed);
          console.debug("WorkspacePane: loaded documents from localStorage app:documents");
          return;
        }
      }
    } catch (e) {}

    setDocuments([
      { id: "1", name: "Welcome", ext: "md", updatedAt: new Date().toISOString() },
      { id: "2", name: "Project Plan", ext: "md", updatedAt: new Date().toISOString() },
    ]);
    console.debug("WorkspacePane: using fallback mock documents");
  }, []);

  if (!documents) {
    return (
      <LayeredCard bevel="chunky" glass className="flex-1 p-4">
        <div className="text-sm opacity-80" style={{ color: "var(--muted)" }}>
          Loading workspace...
        </div>
      </LayeredCard>
    );
  }

  return (
    <LayeredCard bevel="chunky" glass className="flex-1 overflow-auto" style={{ display: "flex", flexDirection: "column" }}>
      <div style={{ padding: 12, borderBottom: "1px solid var(--panel-border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ color: "var(--text)", fontWeight: 600 }}>Workspace</div>
          <div style={{ color: "var(--muted)", fontSize: 12 }}>Threads & Projects</div>
        </div>
      </div>

      <div style={{ padding: 12, overflow: "auto", flex: 1 }}>
        {documents.length === 0 ? (
          <div style={{ color: "var(--muted)" }}>
            No documents found for this workspace. Create a document or open a thread to see files here.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {documents.map((d) => (
              <div key={(d.id || d.name) as string} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 10, borderRadius: 8, border: "1px solid var(--panel-border)", background: "var(--panel-bg)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: "rgba(0,0,0,0.06)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text)" }}>{(d.ext || "").toUpperCase()}</div>
                  <div>
                    <div style={{ color: "var(--text)", fontWeight: 600 }}>{d.name}</div>
                    <div style={{ color: "var(--muted)", fontSize: 12 }}>{d.ext ? `${d.name}.${d.ext}` : d.name}</div>
                  </div>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{d.updatedAt ? new Date(d.updatedAt).toLocaleString() : "—"}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </LayeredCard>
  );
}
