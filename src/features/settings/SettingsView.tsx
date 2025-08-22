import { useEffect, useRef, useState } from "react";
import { CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/controls/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
import { ImagePlus, FolderOpen } from "lucide-react";

export function SettingsView({ mode, setMode, guardianName, setGuardianName, userName, setUserName, role, setRole, notes, setNotes, baseColor, setBaseColor, depth, setDepth, fade, setFade, resolved, systemPrompt, setSystemPrompt, wallpaper, setWallpaper, extColors, setExtColors }: { mode: ThemeMode; setMode: (m: ThemeMode) => void; guardianName: string; setGuardianName: (s: string) => void; userName: string; setUserName: (s: string) => void; role: string; setRole: (s: string) => void; notes: string; setNotes: (s: string) => void; baseColor: string; setBaseColor: (s: string) => void; depth: number; setDepth: (n: number) => void; fade: number; setFade: (n: number) => void; resolved: "light" | "dark"; systemPrompt: string; setSystemPrompt: (s: string) => void; wallpaper: string | null; setWallpaper: (s: string | null) => void; extColors: ExtColors; setExtColors: (m: ExtColors) => void }) {
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

  return (
    <div className="h-full p-4" style={{ color: "var(--text)" }}>
      <CardContent className="mx-auto w-full max-w-4xl space-y-6 p-4 rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
        <div className="flex items-center gap-2">
          <Button type="button" variant={tab === "appearance" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("appearance")}>
            Appearance
          </Button>
          <Button type="button" variant={tab === "system" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("system")}>
            System Prompt
          </Button>
        </div>

        {tab === "system" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <div className="text-sm font-medium">Guardian Nickname</div>
                <Input value={name} onChange={(e) => setName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-medium">User Nickname</div>
                <Input value={uName} onChange={(e) => setUName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <div className="text-sm font-medium">Occupation / Role</div>
                <Input value={uRole} onChange={(e) => setURole(e.target.value)} className="h-9" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium">System Prompt</div>
              <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium">Notes</div>
              <Textarea value={memo} onChange={(e) => setMemo(e.target.value)} rows={4} className="w-full" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" onClick={handleSave} className="rounded-xl">
                Save
              </Button>
            </div>
          </div>
        )}

        {tab === "appearance" && (
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="text-sm font-semibold">Theme</div>
              <SegmentedThemeControl mode={mode} onChange={setMode} />
              <div className="text-xs opacity-80">Resolved: {resolved}</div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <div className="text-sm font-semibold">Base Color</div>
                <Input type="color" value={baseColor} onChange={(e) => setBaseColor(e.target.value)} aria-label="Base color" />
              </div>
              <div className="space-y-2">
                <div className="text-sm font-semibold">Depth</div>
                <Input type="range" min={0} max={1} step={0.01} value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
              </div>
              <div className="space-y-2">
                <div className="text-sm font-semibold">Fade</div>
                <Input type="range" min={0} max={1} step={0.01} value={fade} onChange={(e) => setFade(Number(e.target.value))} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold">Wallpaper</div>
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
            </div>
          </div>
        )}
      </CardContent>
    </div>
  );
}

export default SettingsView;
