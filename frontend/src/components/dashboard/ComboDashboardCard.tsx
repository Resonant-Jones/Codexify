import React from "react";
import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import FrameCard from "@/components/surface/FrameCard";
export default function ComboDashboardCard({
  pinned = [],
  recentDocs = [],
  onCreateProject,
  onCreateThread,
}: {
  pinned?: string[];
  recentDocs?: string[];
  onCreateProject: () => void;
  onCreateThread: () => void;
}) {
  const safePinned = Array.isArray(pinned) ? pinned : [];
  const safeRecent = Array.isArray(recentDocs) ? recentDocs : [];

  return (
    <FrameCard className="min-w-0 min-h-0 flex flex-col gap-[10px] p-[var(--card-pad)]">

      <div className="flex-1 min-h-0">
        <div
          className="rounded-xl border shadow-sm h-full flex flex-col"
          style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          <div className="px-4 pt-3 pb-2 shrink-0 flex items-center justify-between">
            <div className="text-lg font-semibold">Pinned</div>
            <div className="flex items-center gap-2">
              <button
                onClick={onCreateThread}
                className="px-3 py-1 bg-blue-600 text-white rounded-full text-sm"
              >
                New Thread
              </button>
              <button
                onClick={onCreateProject}
                className="px-3 py-1 bg-green-500 text-white rounded-full text-sm"
              >
                New Project
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-4 pt-0">
            <div className="grid grid-cols-2 gap-3">
              {safePinned.map((name) => (
                <button
                  key={name}
                  className="rounded-2xl border px-3 py-1.5 text-left min-h-[44px] flex items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                  style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
                >
                  <span className="truncate">{name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Documents */}
      <div className="flex-1 min-h-0">
        <div
          className="rounded-xl border shadow-sm h-full flex flex-col"
          style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          <div className="px-4 pt-3 pb-2 shrink-0">
            <div className="text-lg font-semibold">Recent Documents</div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-4 pt-0">
            <div className="grid gap-4 justify-start" style={{ gridTemplateColumns: "repeat(auto-fill, 112px)" }}>
              {safeRecent.map((d) => (
                <DocumentPreviewTile
                  key={d}
                  file={{ name: d }}
                  className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </FrameCard>
  );
}
