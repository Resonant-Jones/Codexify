import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import FrameCard from "@/components/surface/FrameCard";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/settings/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { ImagePlus } from "lucide-react";

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

type SettingsTab = "appearance" | "system";

export function SettingsView({ mode, setMode, guardianName, setGuardianName, userName, setUserName, role, setRole, notes, setNotes, baseColor, setBaseColor, depth, setDepth, fade, setFade, resolved, systemPrompt, setSystemPrompt, wallpaper, setWallpaper, wallpaperBlur, setWallpaperBlur, extColors, setExtColors }: SettingsProps) {
  const [tab, setTab] = useState<SettingsTab>("appearance");
  const tabs: Array<{ key: SettingsTab; label: string }> = [
    { key: "appearance", label: "Appearance" },
    { key: "system", label: "System Prompt" },
  ];
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
  const [, setUploading] = useState(false);
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
    <div className="flex h-full w-full items-center justify-center p-6" style={{ color: "var(--text)" }}>
      <FrameCard
        refractiveFallback
        shimmerMode="subtle"
        className="flex h-[990px] w-[572px] max-w-full flex-col overflow-hidden p-6"
      >
        <div className="flex flex-1 flex-col gap-6 overflow-hidden">
          <div className="flex justify-center">
            <div className="glass-pill" role="tablist" aria-label="Settings sections">
              {tabs.map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  className="pill-tab"
                  data-state={tab === key ? "active" : undefined}
                  aria-selected={tab === key}
                  onClick={() => setTab(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {tab === "system" ? (
              <div className="flex h-full flex-col gap-5 overflow-y-auto pr-1">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-xs tracking-wide uppercase text-gray-400">Guardian Nickname</div>
                    <div className="w-48">
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="h-8 rounded-[var(--tile-radius,19px)] px-3 text-xs"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="text-xs tracking-wide uppercase text-gray-400">User Nickname</div>
                    <div className="w-48">
                      <Input
                        value={uName}
                        onChange={(e) => setUName(e.target.value)}
                        className="h-8 rounded-[var(--tile-radius,19px)] px-3 text-xs"
                      />
                    </div>
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <div className="text-xs tracking-wide uppercase text-gray-400">Occupation / Role</div>
                    <Input
                      value={uRole}
                      onChange={(e) => setURole(e.target.value)}
                      className="rounded-[var(--tile-radius,19px)] px-3"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs tracking-wide uppercase text-gray-400">System Prompt</div>
                  <Textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={6}
                    className="rounded-[var(--tile-radius,19px)] px-3"
                  />
                </div>
                <div className="space-y-2">
                  <div className="text-xs tracking-wide uppercase text-gray-400">Notes</div>
                  <Textarea
                    value={memo}
                    onChange={(e) => setMemo(e.target.value)}
                    rows={4}
                    className="rounded-[var(--tile-radius,19px)] px-3"
                  />
                </div>
                <div className="flex justify-end">
                  <Button type="button" onClick={handleSave} className="rounded-[var(--tile-radius,19px)] px-6">
                    Save
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex h-full flex-col gap-6 overflow-y-auto pr-1">
                <div className="space-y-2">
                  <div className="text-xs tracking-wide uppercase text-gray-400">Theme</div>
                  <SegmentedThemeControl mode={mode} onChange={setMode} />
                  <div className="text-xs opacity-80">Resolved: {resolved}</div>
                </div>

                <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="text-xs tracking-wide uppercase text-gray-400">Base Color</div>
                      <input
                        type="color"
                        value={baseColor}
                        onChange={(e) => setBaseColor(e.target.value)}
                        aria-label="Base color"
                        className="color-swatch"
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
                        className="settings-slider"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="text-xs tracking-wide uppercase text-gray-400">Fade</div>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={Math.round(fade * 100)}
                        onChange={(e) => setFade(Number(e.target.value) / 100)}
                        className="settings-slider"
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="text-xs tracking-wide uppercase text-gray-400">Wallpaper</div>
                      <div className="flex flex-wrap items-center gap-2">
                        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="flex items-center gap-2 rounded-[var(--tile-radius,19px)]"
                          onClick={triggerFile}
                        >
                          <ImagePlus className="h-4 w-4" />
                          Choose Image
                        </Button>
                        {wallpaper && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="rounded-[var(--tile-radius,19px)]"
                            onClick={clearWallpaper}
                          >
                            Clear
                          </Button>
                        )}
                        <span className="text-xs opacity-70">{fileLabel}</span>
                      </div>
                    </div>
                    {wallpaper && (
                      <div className="space-y-2">
                        <div className="text-xs tracking-wide uppercase text-gray-400">Wallpaper Blur</div>
                        <input
                          type="range"
                          min={0}
                          max={24}
                          value={wallpaperBlur}
                          onChange={(e) => setWallpaperBlur(Number(e.target.value))}
                          className="settings-slider"
                        />
                        <div className="text-xs opacity-80">{wallpaperBlur}px</div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs tracking-wide uppercase text-gray-400">File Type Colors</div>
                  <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
                    {(["pdf","md","txt","sketch","docx","png","jpg"] as const).map((k) => {
                      const swatch = extColors[k as keyof ExtColors] || "#6B7280";
                      return (
                        <div key={k} className="flex items-center gap-2">
                          <span className="w-10 text-xs uppercase opacity-70 text-center">{k}</span>
                          <input
                            type="color"
                            value={swatch}
                            onChange={(e) => setExtColors({ ...extColors, [k]: e.target.value } as any)}
                            className="color-swatch"
                            aria-label={`${k} color`}
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </FrameCard>
    </div>
  );
}

export default SettingsView;
