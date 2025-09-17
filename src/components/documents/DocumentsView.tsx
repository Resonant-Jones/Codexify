import React from "react";
import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import { ExtColors } from "@/types/ui";

interface DocumentsViewProps {
  documents: Array<{ name: string; ext: keyof ExtColors }>;
  extColors: ExtColors;
  onDocumentClick?: (name: string, ext: string) => void;
}

export default function DocumentsView({ 
  documents, 
  extColors, 
  onDocumentClick 
}: DocumentsViewProps) {
  const handleDocumentClick = (name: string, ext: string) => {
    if (onDocumentClick) {
      onDocumentClick(name, ext);
    }
  };

  return (
    <section className="w-full h-full min-h-0 flex flex-col overflow-hidden">
      <div className="flex-1 min-h-0 overflow-auto">
        <div 
          className="glass-surface rounded-2xl p-[3px] w-full h-full min-h-0 min-w-[520px] max-w-[800px] mx-auto"
          style={{ "--radius": "var(--card-radius)", "--frame": "5px", "--bezel": "4px", "--rim": "3px", "--gutter": "16px", "--card-pad": "10px", "--min-h": "clamp(520px, 70vh, 1000px)" } as React.CSSProperties}
        >
          <div
            className="rounded-xl border shadow-sm h-full flex flex-col"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
          >
            <div className="px-4 pt-3 pb-2 shrink-0">
              <div className="text-lg font-semibold">Documents</div>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-3 pt-0">
              <div className="grid gap-2 grid-cols-[repeat(auto-fit,minmax(112px,1fr))] justify-items-center">
                {documents.map((d) => (
                  <DocumentPreviewTile
                    key={`${d.name}.${d.ext}`}
                    file={{ name: `${d.name}.${d.ext}` }}
                    onClick={() => handleDocumentClick(d.name, d.ext)}
                    className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
