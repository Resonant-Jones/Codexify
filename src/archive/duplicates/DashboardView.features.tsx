import { Button } from "@/components/ui/button";
import LayeredCard from "@/components/ui/LayeredCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { CardContent } from "@/components/ui/card";
import { DocumentTile, ext } from "./DocumentTile";
import { ExtColors, GalleryItem } from "@/types/ui";

export function DashboardView({ extColors, gallery, onImagePrompt }: { extColors: ExtColors; gallery: GalleryItem[]; onImagePrompt: (p: string) => void }) {
  const { wallpaperUrl } = useWallpaperUrl();
  const recentDocs = ["Covenant.pdf", "Roadmap.md", "Vision.txt"];
  const colorFor = (name: string) => extColors[ext(name)] || "#6366f1";
  return (
    <RefractiveGlassCard wallpaperUrl={wallpaperUrl} className="rounded-2xl h-full" style={{ border: 0 }}>
      <div className="grid h-full grid-cols-1 gap-4 p-4 lg:grid-cols-2">
      <LayeredCard bevel="chunky" glass className="rounded-2xl h-full">
        <CardContent className="p-[3px] h-full">
        <div className="p-3 space-y-4 h-full">
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Pinned
            </div>
            <div className="grid grid-cols-2 gap-3">
              {"Sovereign AI Principles,Health & Wellness,Novel Outline,Meeting Prep".split(",").map((t) => (
                <LayeredCard key={t} tone="base">
                  <CardContent className="p-[3px]">
                    <button className="inline-flex items-center rounded-xl border px-3 py-1.5 text-sm" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)", boxShadow: "var(--elevation-shadow-front)" }}>
                      {t}
                    </button>
                  </CardContent>
                </LayeredCard>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Recent Documents
            </div>
            <div className="grid grid-cols-3 gap-3">
              {recentDocs.map((d) => (
                <LayeredCard key={d} tone="base" className="h-full">
                  <CardContent className="p-[3px] h-full">
                    <div className="relative aspect-square w-full h-full rounded-xl overflow-hidden border" style={{ borderColor: "var(--panel-border)", boxShadow: "var(--elevation-shadow-front)" }}>
                      <div className="absolute inset-0 grid place-items-center">
                        <div className="w-6 h-6 rounded-md" style={{ background: colorFor(d) }} />
                      </div>
                      <div className="absolute inset-x-[3px] bottom-[3px] h-7 rounded-b-[10px] px-2 flex items-center justify-between text-xs font-medium" style={{ background: colorFor(d), color: "white", boxShadow: "var(--elevation-shadow-front)" }}>
                        <span className="truncate">{d.replace(/\.[^.]+$/, "")}</span>
                        <span className="opacity-90">.{d.split('.').pop()}</span>
                      </div>
                    </div>
                  </CardContent>
                </LayeredCard>
              ))}
            </div>
          </div>
        </div>
        </CardContent>
      </LayeredCard>
      <LayeredCard bevel="chunky" glass className="rounded-2xl h-full">
        <CardContent className="p-[3px] h-full">
        <div className="p-3 h-full">
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
        </div>
        </CardContent>
      </LayeredCard>
      </div>
    </RefractiveGlassCard>
  );
}

export default DashboardView;
