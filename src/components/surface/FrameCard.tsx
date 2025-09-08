// src/components/persona/layout/AppShell.tsx
import { useState } from "react";
// Removed: import FrameCard from "@/components/surface/FrameCard";

export default function AppShell() {
  const [view, setView] = useState<"dashboard" | "documents">("dashboard");
  const documents = [
    /* some documents */
  ];

  return (
    <div>
      {view === "dashboard" && (
        <section>
          <h2>Recent</h2>
          {documents.map((d) => (
            <div
              key={d.id}
              className="rounded-[var(--radius)] overflow-hidden border"
              style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 p-3">
                  {/* document content */}
                </div>
              </div>
            </div>
          ))}
        </section>
      )}

      {view === "documents" && (
        <section>
          <h2>Documents</h2>
          {documents.map((d) => (
            <div
              key={d.id}
              className="rounded-[var(--radius)] overflow-hidden border"
              style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 p-3">
                  {/* document content */}
                </div>
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}