import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/settings/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { ImagePlus, FolderOpen } from "lucide-react";

type SettingsProps = {
  mode: "light" | "dark" | "system";
  setMode: (m: "light" | "dark" | "system") => void;
  guardianName: string; setGuardianName: (s: string) => void;
  userName: string; setUserName: (s: string) => void;
  role: string; setRole: (s: string) => void;
  notes: string; setNotes: (s: string) => void;
  baseColor: string; setBaseColor: (c: string) => void;
  depth: number; setDepth: (v: number) => void;        // 0..1
  fade: number; setFade: (v: number) => void;          // 0..1
  resolved: "light" | "dark";
  systemPrompt: string; setSystemPrompt: (s: string) => void;
  wallpaper: string | null; setWallpaper: (u: string | null) => void;
  wallpaperBlur: number; setWallpaperBlur: (px: number) => void;
  extColors: ExtColors; setExtColors: (m: ExtColors) => void;
};

function getComputedStyleVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function SettingsView({ mode, setMode, guardianName, setGuardianName, userName, setUserName, role, setRole, notes, setNotes, baseColor, setBaseColor, depth, setDepth, fade, setFade, resolved, systemPrompt, setSystemPrompt, wallpaper, setWallpaper, wallpaperBlur, setWallpaperBlur, extColors, setExtColors }: SettingsProps) {
  const [tab, setTab] = useState<"appearance" | "system">("appearance");
  const [name, setName] = useState(guardianName);
  const [uName, setUName] = useState(userName);
  const [uRole, setURole] = useState(role);
  const [prompt, setPrompt] = useState(systemPrompt);
  const [memo, setMemo] = useState(notes);
  useEffect(() => setName(guardianName), [guardianName]);
  useEffect(() => setUName(userName), [userName]);
  useEffect(() => setURole(role), [role]);
  useEffect(() => setPrompt(systemPrompt), [systemPrompt]);
  useEffect(() => setMemo(notes), [notes]);

  function handleSave() {
    setGuardianName(name);
    setUserName(uName);
    setRole(uRole);
    setSystemPrompt(prompt);
    setNotes(memo);
  }

  const [fileLabel, setFileLabel] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);
  function triggerFile() {
    fileRef.current?.click();
  }
  function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setUploading(true);
    setFileLabel(f.name);
    const rd = new FileReader();
    rd.onload = () => {
      const url = String(rd.result || "");
      setWallpaper(url);
      if (typeof window !== "undefined") localStorage.setItem("cfy.wallpaper", url);
      setUploading(false);
    };
    rd.onerror = () => setUploading(false);
    rd.readAsDataURL(f);
  }
  function clearWallpaper() {
    setWallpaper(null);
    setFileLabel("");
    if (typeof window !== "undefined") localStorage.removeItem("cfy.wallpaper");
    if (fileRef.current) fileRef.current.value = "";
  }

  // Sliders remain interactive at all times; theme toggle sets defaults in AppShell

  return (
    <div className="h-full p-4" style={{ color: "var(--text)" }}>
      <Card
        className="rounded-2xl border shadow-sm h-full w-full"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
          boxShadow:
            "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.22), 0 8px 18px rgba(0,0,0,0.16)",
        }}
      >
        <CardContent className="p-4 pt-6 space-y-6">
        <div className="flex items-center gap-2">
          <Button type="button" variant={tab === "appearance" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("appearance")}>
            Appearance
          </Button>
          <Button type="button" variant={tab === "system" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("system")}>
            System Prompt
          </Button>
        </div>

        {tab === "system" && (
          <div className="space-y-4 not-prose">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <div className="text-xs tracking-wide uppercase text-gray-400">Guardian Nickname</div>
                <Input value={name} onChange={(e) => setName(e.target.value)} className="w-48 h-8 text-xs rounded-lg bg-white/5 ring-1 ring-white/10 focus-visible:ring-[var(--accent)]" style={{ color: "var(--text)" }} />
              </div>
              <div className="space-y-1">
                <div className="text-xs tracking-wide uppercase text-gray-400">User Nickname</div>
                <Input value={uName} onChange={(e) => setUName(e.target.value)} className="w-48 h-8 text-xs rounded-lg bg-white/5 ring-1 ring-white/10 focus-visible:ring-[var(--accent)]" style={{ color: "var(--text)" }} />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <div className="text-xs tracking-wide uppercase text-gray-400">Occupation / Role</div>
                <Input value={uRole} onChange={(e) => setURole(e.target.value)} className="h-9 rounded-lg bg-white/5 ring-1 ring-white/10 focus-visible:ring-[var(--accent)]" style={{ color: "var(--text)" }} />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs tracking-wide uppercase text-gray-400">System Prompt</div>
              <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} className="w-full rounded-lg bg-white/5 ring-1 ring-white/10 focus-visible:ring-[var(--accent)]" style={{ color: "var(--text)" }} />
            </div>
            <div className="space-y-1">
              <div className="text-xs tracking-wide uppercase text-gray-400">Notes</div>
              <Textarea value={memo} onChange={(e) => setMemo(e.target.value)} rows={4} className="w-full rounded-lg bg-white/5 ring-1 ring-white/10 focus-visible:ring-[var(--accent)]" style={{ color: "var(--text)" }} />
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" onClick={handleSave} className="btn-primary">
                Save
              </Button>
            </div>
          </div>
        )}

        {tab === "appearance" && (
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="text-xs tracking-wide uppercase text-gray-400">Theme</div>
              <SegmentedThemeControl mode={mode} onChange={setMode} />
              <div className="text-xs opacity-80">Resolved: {resolved}</div>
            </div>

            <div className="space-y-3">
              <div className="space-y-1">
                <div className="text-xs tracking-wide uppercase text-gray-400">Base Color</div>
                <input
                  type="color"
                  value={baseColor}
                  onChange={(e) => setBaseColor(e.target.value)}
                  aria-label="Base color"
                  className="h-8 w-8 p-0 rounded-md border"
                />
              </div>
              <div className="space-y-2">
                <div className="text-xs tracking-wide uppercase text-gray-400">Depth</div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(depth * 100)}
                  onChange={(e) => setDepth(Number(e.target.value) / 100)}
                  className="accent-[var(--accent)] w-full"
                  
                />
                
              </div>
              <div className="space-y-2 -mt-1">
                <div className="text-xs tracking-wide uppercase text-gray-400">Fade</div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(fade * 100)}
                  onChange={(e) => setFade(Number(e.target.value) / 100)}
                  className="accent-[var(--accent)] w-full"
                  
                />
                
              </div>
            </div>

              <div className="space-y-2">
                <div className="text-xs tracking-wide uppercase text-gray-400">Wallpaper</div>
                <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
                <Button type="button" variant="ghost" size="sm" className="rounded-xl flex items-center gap-2" onClick={triggerFile}>
                  <ImagePlus className="h-4 w-4" />
                  Choose Image
                </Button>
                {wallpaper && (
                  <Button type="button" variant="ghost" className="rounded-xl" onClick={clearWallpaper}>
                    Clear
                  </Button>
                )}
                <span className="text-xs opacity-70">{fileLabel}</span>
              </div>
              {wallpaper && (
                <div className="mt-3">
                  <div className="mb-1 text-sm">Wallpaper Blur</div>
                  <input type="range" min={0} max={24} value={wallpaperBlur} onChange={(e) => setWallpaperBlur(Number(e.target.value))} className="w-full" />
                  <div className="text-xs opacity-80 mt-1">{wallpaperBlur}px</div>
                </div>
              )}

              <div className="space-y-3 pt-2">
                <div className="text-xs tracking-wide uppercase text-gray-400">File Type Colors</div>
                <div className="grid grid-cols-4 gap-3">
                  {(["pdf","md","txt","sketch","docx","png","jpg"] as const).map((k) => {
                    const swatch = extColors[k as keyof ExtColors] || "#6B7280";
                    return (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-10 text-xs uppercase opacity-70 text-center">{k}</span>
                        <input
                          type="color"
                          value={swatch}
                          onChange={(e) => setExtColors({ ...extColors, [k]: e.target.value } as any)}
                          className="h-7 w-7 rounded-md border"
                          aria-label={`${k} color`}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
        </CardContent>
      </Card>
    </div>
  );
}

export default SettingsView;
