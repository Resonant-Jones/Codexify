import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DocumentTile, ext } from "./DocumentTile";
import { ExtColors, GalleryItem } from "@/types/ui";

export function DashboardView({ extColors, gallery, onImagePrompt }: { extColors: ExtColors; gallery: GalleryItem[]; onImagePrompt: (p: string) => void }) {
  const recentDocs = ["Covenant.pdf", "Roadmap.md", "Vision.txt"];
  const colorFor = (name: string) => extColors[ext(name)] || "#6366f1";
  return (
    <div className="grid h-full grid-cols-1 gap-4 p-4 lg:grid-cols-2">
      <Card className="rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
        <CardContent className="p-4 space-y-4">
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Pinned
            </div>
            <div className="grid grid-cols-2 gap-3">
              {"Sovereign AI Principles,Health & Wellness,Novel Outline,Meeting Prep".split(",").map((t) => (
                <div key={t} className="rounded-xl border p-3 text-sm" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                  {t}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Recent Documents
            </div>
            <div className="grid grid-cols-3 gap-3">
              {recentDocs.map((d) => (
                <DocumentTile key={d} name={d} color={colorFor(d)} />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
        <CardContent className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Generated Images
            </div>
            <Button size="sm" variant="ghost" className="rounded-xl" style={{ color: "var(--text)" }}>
              See all
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {gallery.map((item, i) => (
              <button
                key={i}
                className="aspect-square overflow-hidden rounded-2xl border"
                style={{ borderColor: "var(--panel-border)" }}
                onClick={() => onImagePrompt(item.prompt)}
                title="Open chat with prompt"
              >
                <img src={item.src} alt="Gallery" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default DashboardView;

