import React, { useEffect, useRef, useState, lazy, Suspense } from "react";
const ForceGraph2D = lazy(() => import("react-force-graph").then(m => ({ default: m.ForceGraph2D })));
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
  ingestionEnabled: boolean;
  setIngestionEnabled: (enabled: boolean) => void;
};

type SettingsTab = "appearance" | "system" | "data";

export function SettingsView({ mode, setMode, guardianName, setGuardianName, userName, setUserName, role, setRole, notes, setNotes, baseColor, setBaseColor, depth, setDepth, fade, setFade, resolved, systemPrompt, setSystemPrompt, wallpaper, setWallpaper, wallpaperBlur, setWallpaperBlur, extColors, setExtColors, ingestionEnabled, setIngestionEnabled }: SettingsProps) {
  // ——— Ingestion Endpoint Override State ———
  const [ingestEndpointOverride, setIngestEndpointOverride] = useState(() =>
    typeof window !== "undefined" ? localStorage.getItem("cfy.ingest.endpoint.override") || "" : ""
  );
  const [tab, setTab] = useState<SettingsTab>("appearance");
  const tabs: Array<{ key: SettingsTab; label: string }> = [
    { key: "appearance", label: "Appearance" },
    { key: "system", label: "System Prompt" },
    { key: "data", label: "Data" },
  ];
  const [name, setName] = useState(guardianName);
  const [uName, setUName] = useState(userName);
  const [uRole, setURole] = useState(role);
  const [prompt, setPrompt] = useState(systemPrompt);
  const [memo, setMemo] = useState(notes);

  // ——— Exocognitive Tuner State ———
  const [kTop, setKTop] = useState(4);
  const [wCos, setWCos] = useState(0.6);
  const [wRec, setWRec] = useState(0.25);
  const [wInt, setWInt] = useState(0.15);

  type WMNode = { id: string; type: "turn" | "doc" | "project" | "thread" | "note"; title: string; tags: string[]; recencyDays: number; cosine: number; interactions: number };
  const wmSample: WMNode[] = [
    { id: "t001", type: "turn", title: "Exocognition vs context windows", tags: ["codexify","retrieval","context"], recencyDays: 1, cosine: 0.88, interactions: 5 },
    { id: "d042", type: "doc", title: "Guardian Ethics Layer (PCXEP-002)", tags: ["guardian","ethics","protocol"], recencyDays: 12, cosine: 0.76, interactions: 9 },
    { id: "p007", type: "project", title: "UI polish (PreviewTile, bevel)", tags: ["ui","tiles","tailwind"], recencyDays: 30, cosine: 0.52, interactions: 12 },
    { id: "th011", type: "thread", title: "Builder’s Testament copy", tags: ["mythos","marketing"], recencyDays: 2, cosine: 0.61, interactions: 6 },
    { id: "d099", type: "doc", title: "Neo4j graph schema draft", tags: ["neo4j","graph","persona"], recencyDays: 5, cosine: 0.81, interactions: 4 },
    { id: "t055", type: "turn", title: "Glasses fit (Flexon B2000)", tags: ["life","glasses"], recencyDays: 0, cosine: 0.12, interactions: 2 },
  ];
  function wmScore(n: WMNode) {
    const rec = 1 - Math.min(n.recencyDays / 60, 1); // fade over ~2 months
    const inter = Math.min(n.interactions / 12, 1);
    return Number((n.cosine * wCos + rec * wRec + inter * wInt).toFixed(4));
  }
  const wmRanked = wmSample
    .map((n) => ({ ...n, score: wmScore(n) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, kTop);

  // ——— Lightweight Constellation (no proprietary graph data) ———
  const constellationNodes = wmSample.map((n, i) => {
    const angle = (i / wmSample.length) * Math.PI * 2;
    const r = 110 + (i % 3) * 30;
    return { id: n.id, label: n.title, type: n.type, x: 160 + r * Math.cos(angle), y: 140 + r * Math.sin(angle), tags: n.tags };
  });
  const constellationLinks: Array<{ a: string; b: string }> = [];
  for (let i = 0; i < wmSample.length; i++) {
    for (let j = i + 1; j < wmSample.length; j++) {
      const shared = wmSample[i].tags.some((t) => wmSample[j].tags.includes(t));
      if (shared) constellationLinks.push({ a: wmSample[i].id, b: wmSample[j].id });
    }
  }

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

  // ——— ChatGPT Migration State ———
  const [chatGPTFile, setChatGPTFile] = useState<File | null>(null);
  const [migrationStatus, setMigrationStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [migrationStats, setMigrationStats] = useState<{ threads: number; messages: number } | null>(null);
  const [migrationError, setMigrationError] = useState<string | null>(null);
  const chatGPTFileRef = useRef<HTMLInputElement | null>(null);

  function handleChatGPTFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setChatGPTFile(f);
    setMigrationStatus("idle");
    setMigrationError(null);
    setMigrationStats(null);
  }

  async function handleMigrate() {
    if (!chatGPTFile) return;
    setMigrationStatus("uploading");
    setMigrationError(null);

    const formData = new FormData();
    formData.append("file", chatGPTFile);

    try {
      const res = await fetch("/upload-chatgpt-export", {
        method: "POST",
        headers: {
          "X-User-Id": userName || "user",
        },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.details || data.error || "Migration failed");
      }

      setMigrationStats({
        threads: data.threads_imported,
        messages: data.messages_imported,
      });
      setMigrationStatus("success");
      setChatGPTFile(null); // Clear file after success
    } catch (err: any) {
      console.error("Migration error:", err);
      setMigrationStatus("error");
      setMigrationError(err.message || "Failed to migrate data");
    }
  }

  // Sliders remain interactive at all times; theme toggle sets defaults in AppShell

  return (
    <div className="flex h-full w-full items-start justify-center p-6" style={{ color: "var(--text)" }}>
      <div className="grid w-full max-w-[1600px] grid-cols-1 lg:grid-cols-[clamp(572px,60vw,858px)_minmax(0,1fr)] gap-6 items-start">
      <FrameCard
        refractiveFallback
        shimmerMode="subtle"
        className="flex h-[990px] w-full lg:w-[clamp(572px,60vw,858px)] max-w-full flex-col overflow-hidden p-6"
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
            ) : tab === "data" ? (
              <div className="flex h-full flex-col gap-6 overflow-y-auto pr-1">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="text-xs tracking-wide uppercase text-gray-400">ChatGPT Migration</div>
                    <div className="text-xs opacity-70 leading-relaxed">
                      Import your full conversation history from ChatGPT. This process ingests your data into both the Knowledge Graph (for relationships) and the Vector Store (for semantic recall).
                    </div>
                  </div>

                  <div className="rounded-[var(--tile-radius,19px)] border border-white/10 bg-white/5 p-4 space-y-4">
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center gap-3">
                        <input
                          ref={chatGPTFileRef}
                          type="file"
                          accept=".json"
                          className="hidden"
                          onChange={handleChatGPTFileSelect}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-[var(--tile-radius,19px)]"
                          onClick={() => chatGPTFileRef.current?.click()}
                        >
                          Choose Export File
                        </Button>
                        <span className="text-xs opacity-70 truncate max-w-[200px]">
                          {chatGPTFile ? chatGPTFile.name : "No file selected"}
                        </span>
                      </div>

                      <Button
                        type="button"
                        disabled={!chatGPTFile || migrationStatus === "uploading"}
                        onClick={handleMigrate}
                        className="w-full rounded-[var(--tile-radius,19px)]"
                      >
                        {migrationStatus === "uploading" ? "Migrating..." : "Upload & Migrate"}
                      </Button>
                    </div>

                    {migrationStatus === "uploading" && (
                      <div className="text-xs text-center opacity-70 animate-pulse">
                        Processing conversations... this may take a moment.
                      </div>
                    )}

                    {migrationStatus === "success" && migrationStats && (
                      <div className="rounded-lg bg-green-500/10 p-3 border border-green-500/20">
                        <div className="text-xs font-medium text-green-400 mb-1">Migration Successful</div>
                        <div className="text-[10px] opacity-80">
                          Imported {migrationStats.threads} threads and {migrationStats.messages} messages.
                        </div>
                      </div>
                    )}

                    {migrationStatus === "error" && migrationError && (
                      <div className="rounded-lg bg-red-500/10 p-3 border border-red-500/20">
                        <div className="text-xs font-medium text-red-400 mb-1">Migration Failed</div>
                        <div className="text-[10px] opacity-80">{migrationError}</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ——— Labs: Ingestion API toggle/override ——— */}
                <div className="space-y-2 pt-4 border-t border-white/5">
                  <div className="text-xs tracking-wide uppercase text-gray-400">Labs</div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="ingestion-api-toggle"
                      checked={ingestionEnabled}
                      onChange={e => setIngestionEnabled(e.target.checked)}
                      className="accent-primary"
                    />
                    <label htmlFor="ingestion-api-toggle" className="text-xs opacity-80 cursor-pointer select-none">
                      Enable Ingestion API
                    </label>
                  </div>
                  {ingestionEnabled && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs opacity-70">Custom Ingestion Endpoint</div>
                      <Input
                        value={ingestEndpointOverride}
                        onChange={(e) => {
                          const val = e.target.value;
                          setIngestEndpointOverride(val);
                          if (typeof window !== "undefined") localStorage.setItem("cfy.ingest.endpoint.override", val);
                        }}
                        placeholder="/api/ingest"
                        className="h-8 rounded-[var(--tile-radius,19px)] px-3 text-xs w-full"
                      />
                    </div>
                  )}
                  {ingestionEnabled && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs opacity-70">Ingestion Tags</div>
                      <div className="text-xs opacity-60">
                        Files uploaded may be auto-tagged with their source or context (e.g. "chat", "upload", "project").
                        This metadata enables better embeddings and graph enrichment.
                      </div>
                    </div>
                  )}
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
                    {(["pdf","md","txt","sketch","docx","png","jpeg"] as const).map((k) => {
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
        </div>
      </FrameCard>

        {/* ————————— New FrameCard: Exocognitive Systems ————————— */}
        <FrameCard
          refractiveFallback
          shimmerMode="subtle"
          className="flex h-[990px] w-full max-w-full flex-col overflow-hidden p-6"
        >
          <div className="flex items-center justify-between pb-4">
            <div>
              <div className="text-base tracking-wide uppercase opacity-70">Exocognitive Systems</div>
              <div className="text-sm opacity-60">Working Memory Selection • Knowledge Graph Constellation</div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Working Memory Tuner */}
            <div className="space-y-4">
              <div className="text-xs tracking-wide uppercase text-gray-400">Working Memory Selection</div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="text-xs opacity-80">Top‑K Chunks: {kTop}</div>
                  <input
                    type="range"
                    min={1}
                    max={6}
                    value={kTop}
                    onChange={(e) => setKTop(Number(e.target.value))}
                    className="settings-slider"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-xs opacity-80">Weight • Cosine ({wCos.toFixed(2)})</div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={Math.round(wCos * 100)}
                    onChange={(e) => setWCos(Number(e.target.value) / 100)}
                    className="settings-slider"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-xs opacity-80">Weight • Recency ({wRec.toFixed(2)})</div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={Math.round(wRec * 100)}
                    onChange={(e) => setWRec(Number(e.target.value) / 100)}
                    className="settings-slider"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-xs opacity-80">Weight • Interactions ({wInt.toFixed(2)})</div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={Math.round(wInt * 100)}
                    onChange={(e) => setWInt(Number(e.target.value) / 100)}
                    className="settings-slider"
                  />
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <div className="text-xs tracking-wide uppercase text-gray-400">Selected (Top‑{kTop})</div>
                <div className="grid grid-cols-1 gap-2 pr-1 overflow-y-auto max-h-64">
                  {wmRanked.map((n) => (
                    <div key={n.id} className="rounded-[var(--tile-radius,19px)] border border-white/10 bg-white/5 px-3 py-2">
                      <div className="text-sm font-medium opacity-90">{n.title}</div>
                      <div className="text-[10px] opacity-70">{n.type.toUpperCase()} • score {n.score}</div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {n.tags.map((t) => (
                          <span key={t} className="rounded-full bg-white/10 px-2 py-[2px] text-[10px] opacity-80">{t}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Knowledge Graph Constellation (non‑proprietary placeholder) */}
            <div className="space-y-2">
              <div className="text-xs tracking-wide uppercase text-gray-400">Knowledge Graph Constellation</div>
              <KnowledgeGraphConstellation />
              <div className="text-[11px] opacity-60">Visual only — uses Codexify graph API. Wire to Neo4j later.</div>
            </div>
          </div>
        </FrameCard>

      </div>
    </div>
  );
}

export default SettingsView;

// ——— KnowledgeGraphConstellation Component ———
function KnowledgeGraphConstellation() {
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(typeof window !== "undefined");
    setLoading(true);
    setError(null);
    fetch("/api/graph?scope=codexify")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch graph data");
        return res.json();
      })
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Error");
        setLoading(false);
      });
  }, []);

  return (
    <div className="relative rounded-[var(--tile-radius,19px)] border border-white/10 bg-white/5 p-3" style={{ minHeight: 330 }}>
      {!isClient && (
        <div className="flex items-center justify-center h-[320px] opacity-70 text-xs">Preparing constellation…</div>
      )}
      {isClient && loading && (
        <div className="flex items-center justify-center h-[320px] opacity-70 text-xs">Loading graph…</div>
      )}
      {isClient && error && (
        <div className="flex items-center justify-center h-[320px] text-red-400 text-xs">{error}</div>
      )}
      {isClient && graphData && (
        <div className="w-full h-[320px]">
          <Suspense fallback={<div className="p-4 text-xs opacity-70">Mounting canvas…</div>}>
            <ForceGraph2D
              graphData={graphData}
              width={undefined}
              height={320}
              backgroundColor="rgba(0,0,0,0)"
              nodeLabel="label"
              nodeAutoColorBy="type"
              linkColor={() => "rgba(255,255,255,0.13)"}
              linkDirectionalParticles={0}
              nodeCanvasObjectMode={() => "after"}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.label || node.id;
                const fontSize = 10 / globalScale;
                ctx.font = `${fontSize}px sans-serif`;
                ctx.fillStyle = "rgba(255,255,255,0.85)";
                ctx.fillText(label, node.x + 8, node.y + 4);
              }}
            />
          </Suspense>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 rounded-[var(--tile-radius,19px)] ring-1 ring-white/10" />
    </div>
  );
}
                {/* ——— Labs: Ingestion API toggle/override ——— */}
                <div className="space-y-2">
                  <div className="text-xs tracking-wide uppercase text-gray-400">Labs</div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="ingestion-api-toggle"
                      checked={ingestionEnabled}
                      onChange={e => setIngestionEnabled(e.target.checked)}
                      className="accent-primary"
                    />
                    <label htmlFor="ingestion-api-toggle" className="text-xs opacity-80 cursor-pointer select-none">
                      Enable Ingestion API
                    </label>
                  </div>
                  {ingestionEnabled && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs opacity-70">Custom Ingestion Endpoint</div>
                      <Input
                        value={ingestEndpointOverride}
                        onChange={(e) => {
                          const val = e.target.value;
                          setIngestEndpointOverride(val);
                          if (typeof window !== "undefined") localStorage.setItem("cfy.ingest.endpoint.override", val);
                        }}
                        placeholder="/api/ingest"
                        className="h-8 rounded-[var(--tile-radius,19px)] px-3 text-xs w-full"
                      />
                    </div>
                  )}
                  {ingestionEnabled && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs opacity-70">Ingestion Tags</div>
                      <div className="text-xs opacity-60">
                        Files uploaded may be auto-tagged with their source or context (e.g. "chat", "upload", "project").
                        This metadata enables better embeddings and graph enrichment.
                      </div>
                    </div>
                  )}
                </div>