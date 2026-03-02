import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SegmentedThemeControl from "@/components/controls/SegmentedThemeControl";
import { ThemeMode, ExtColors } from "@/types/ui";
import { ImagePlus } from "lucide-react";
import { useConnectors } from "@/features/connectors/useConnectors";
import { ConnectorCard } from "@/features/connectors/ConnectorCard";
import { MemoryBrowser } from "@/features/settings/diagnostics";
import {
  ChatGPTImportModal,
  type MigrationStats,
} from "@/components/modals/ChatGPTImportModal";
import {
  getDesktopConnectionSettings,
  initRuntimeConfig,
  invokeTauriCommand,
  isTauriRuntime,
  openExternalUrl,
  resolveBackendUrl,
  saveDesktopConnectionSettings,
} from "@/lib/runtimeConfig";
import {
  clearRuntimeApiKey,
  readRuntimeApiKey,
  refreshApiBaseUrl,
  setRuntimeApiKey,
} from "@/lib/api";

export function SettingsView({
  mode,
  setMode,
  guardianName,
  setGuardianName,
  userName,
  setUserName,
  role,
  setRole,
  notes,
  setNotes,
  baseColor,
  setBaseColor,
  depth,
  setDepth,
  fade,
  setFade,
  resolved,
  systemPrompt,
  setSystemPrompt,
  wallpaper,
  setWallpaper,
  extColors,
  setExtColors,
  dashboardThreadRows,
  setDashboardThreadRows,
}: {
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  guardianName: string;
  setGuardianName: (s: string) => void;
  userName: string;
  setUserName: (s: string) => void;
  role: string;
  setRole: (s: string) => void;
  notes: string;
  setNotes: (s: string) => void;
  baseColor: string;
  setBaseColor: (s: string) => void;
  depth: number;
  setDepth: (n: number) => void;
  fade: number;
  setFade: (n: number) => void;
  resolved: "light" | "dark";
  systemPrompt: string;
  setSystemPrompt: (s: string) => void;
  wallpaper: string | null;
  setWallpaper: (s: string | null) => void;
  extColors: ExtColors;
  setExtColors: (m: ExtColors) => void;
  dashboardThreadRows: number;
  setDashboardThreadRows: (n: number) => void;
}) {
  const desktopMode = isTauriRuntime();
  const [tab, setTab] = useState<
    "appearance" | "system" | "connectors" | "data" | "connection" | "diagnostics"
  >("appearance");
  const [chatGPTModalOpen, setChatGPTModalOpen] = useState(false);
  const [migrationStepSkipped, setMigrationStepSkipped] = useState(false);
  const [migrationStats, setMigrationStats] = useState<MigrationStats | null>(
    null
  );
  const [name, setName] = useState(guardianName);
  const [uName, setUName] = useState(userName);
  const [uRole, setURole] = useState(role);
  const [prompt, setPrompt] = useState(systemPrompt);
  const [memo, setMemo] = useState(notes);
  const [desktopBackendBaseUrl, setDesktopBackendBaseUrl] = useState("");
  const [desktopShareBaseUrl, setDesktopShareBaseUrl] = useState("");
  const [desktopApiKeyInput, setDesktopApiKeyInput] = useState("");
  const [connectionBusy, setConnectionBusy] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  useEffect(() => setName(guardianName), [guardianName]);
  useEffect(() => setUName(userName), [userName]);
  useEffect(() => setURole(role), [role]);
  useEffect(() => setPrompt(systemPrompt), [systemPrompt]);
  useEffect(() => setMemo(notes), [notes]);
  useEffect(() => {
    if (!desktopMode) return;
    const settings = getDesktopConnectionSettings();
    setDesktopBackendBaseUrl(settings.backendBaseUrl);
    setDesktopShareBaseUrl(settings.sharePublicBaseUrl);
    setDesktopApiKeyInput(readRuntimeApiKey() ?? "");
  }, [desktopMode]);

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
      if (typeof window !== "undefined") {
        localStorage.setItem("cfy.wallpaper", url);
        // Mark that the user has uploaded a file at least once
        localStorage.setItem("cfy.hasUserUpload", "true");
      }
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

  const migrationComplete =
    migrationStepSkipped || migrationStats !== null;

  async function handleSaveConnectionSettings() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await saveDesktopConnectionSettings({
        backendBaseUrl: desktopBackendBaseUrl,
        sharePublicBaseUrl: desktopShareBaseUrl,
      });
      refreshApiBaseUrl();
      setConnectionMessage("Connection settings saved.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to save connection settings."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleSaveDesktopApiKey() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await invokeTauriCommand("desktop_set_api_key", {
        apiKey: desktopApiKeyInput,
      });
      setRuntimeApiKey(desktopApiKeyInput);
      setConnectionMessage("Desktop API key saved to secure keychain.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to save desktop API key."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleClearDesktopApiKey() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      await invokeTauriCommand("desktop_clear_api_key");
      setDesktopApiKeyInput("");
      clearRuntimeApiKey();
      setConnectionMessage("Desktop API key cleared.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Unable to clear desktop API key."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleTestConnection() {
    if (!desktopMode) return;
    setConnectionBusy(true);
    setConnectionError(null);
    setConnectionMessage(null);
    try {
      const config = await initRuntimeConfig({ force: true });
      refreshApiBaseUrl();
      const response = await fetch(resolveBackendUrl("/ping", config));
      if (!response.ok) {
        throw new Error(`Backend ping failed (${response.status})`);
      }
      setConnectionMessage("Connection test passed.");
    } catch (error) {
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Connection test failed."
      );
    } finally {
      setConnectionBusy(false);
    }
  }

  async function handleDownloadExport() {
    if (typeof window === "undefined") return;
    const exportUrl = resolveBackendUrl("/exports/chatgpt.zip");
    if (desktopMode) {
      const opened = await openExternalUrl(exportUrl);
      if (opened) return;
    }
    window.location.href = exportUrl;
  }

  const { connectors, updateConnector, loading, error, authorizeOAuth, testConnector, syncConnector } = useConnectors();

  return (
    <div className="w-full" style={{ color: "var(--text)" }}>
      <div className="mx-auto w-full max-w-[30rem] space-y-6 p-4">
        <div className="flex items-center gap-2">
          <Button type="button" variant={tab === "appearance" ? "default" : "ghost"} size="sm" className="rounded-[var(--tile-radius,19px)]" onClick={() => setTab("appearance")}>
            Appearance
          </Button>
          <Button type="button" variant={tab === "system" ? "default" : "ghost"} size="sm" className="rounded-[var(--tile-radius,19px)]" onClick={() => setTab("system")}>
            System Prompt
          </Button>
          <Button type="button" variant={tab === "connectors" ? "default" : "ghost"} size="sm" className="rounded-[var(--tile-radius,19px)]" onClick={() => setTab("connectors")}>
            Connectors
          </Button>
          <Button type="button" variant={tab === "data" ? "default" : "ghost"} size="sm" className="rounded-[var(--tile-radius,19px)]" onClick={() => setTab("data")}>
            Data
          </Button>
          {desktopMode && (
            <Button
              type="button"
              variant={tab === "connection" ? "default" : "ghost"}
              size="sm"
              className="rounded-[var(--tile-radius,19px)]"
              onClick={() => setTab("connection")}
            >
              Connection
            </Button>
          )}
          <Button type="button" variant={tab === "diagnostics" ? "default" : "ghost"} size="sm" className="rounded-[var(--tile-radius,19px)]" onClick={() => setTab("diagnostics")}>
            Diagnostics
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
              <Button type="button" onClick={handleSave} className="rounded-[var(--tile-radius,19px)]">
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

            <div className="space-y-2">
              <div className="text-sm font-semibold">Wallpaper</div>
              <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
                <Button type="button" variant="ghost" size="sm" className="rounded-[var(--tile-radius,19px)] flex items-center gap-2" onClick={triggerFile}>
                  <ImagePlus className="h-4 w-4" />
                  Choose Image
                </Button>
                {wallpaper && (
                  <Button type="button" variant="ghost" className="rounded-[var(--tile-radius,19px)]" onClick={clearWallpaper}>
                    Clear
                  </Button>
                )}
                <span className="text-xs opacity-70">{fileLabel}</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">Background Accents</div>
              <div className="text-xs opacity-80">Base color (used when no wallpaper)</div>
              <Input
                type="color"
                value={baseColor}
                onChange={(e) => setBaseColor(e.target.value)}
                aria-label="Base color"
                className="color-swatch"
              />
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">File Type Colors</div>
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-4 max-w-md">
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">PDF</span>
                  <Input id="color-pdf" type="color" value={extColors.pdf} onChange={(e) => setExtColors({ ...extColors, pdf: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">DOC</span>
                  <Input id="color-doc" type="color" value={extColors.doc} onChange={(e) => setExtColors({ ...extColors, doc: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">MD</span>
                  <Input id="color-md" type="color" value={extColors.md} onChange={(e) => setExtColors({ ...extColors, md: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">PNG</span>
                  <Input id="color-png" type="color" value={extColors.png} onChange={(e) => setExtColors({ ...extColors, png: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">SKETCH</span>
                  <Input id="color-sketch" type="color" value={extColors.sketch} onChange={(e) => setExtColors({ ...extColors, sketch: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">TXT</span>
                  <Input id="color-txt" type="color" value={extColors.txt} onChange={(e) => setExtColors({ ...extColors, txt: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">DOCX</span>
                  <Input id="color-docx" type="color" value={extColors.docx} onChange={(e) => setExtColors({ ...extColors, docx: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">JPEG</span>
                  <Input id="color-jpeg" type="color" value={extColors.jpeg} onChange={(e) => setExtColors({ ...extColors, jpeg: e.target.value })} className="color-swatch" />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs">CODEX</span>
                  <Input id="color-codex" type="color" value={extColors.codex} onChange={(e) => setExtColors({ ...extColors, codex: e.target.value })} className="color-swatch" />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-base font-semibold">Dashboard Layout</div>
              <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">Recent thread rows</div>
                    <div className="text-xs opacity-70">Controls the 2 × N grid for Recent Threads.</div>
                  </div>
                  <span className="text-xs font-semibold">
                    {dashboardThreadRows} {dashboardThreadRows === 1 ? "row" : "rows"}
                  </span>
                </div>
                <Input
                  type="range"
                  min={1}
                  max={4}
                  step={1}
                  value={dashboardThreadRows}
                  onChange={(e) => setDashboardThreadRows(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <div className="flex flex-col items-center space-y-4">
              <div className="space-y-2 text-center">
                <div className="text-sm font-semibold">Depth</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
                </div>
              </div>
              <div className="space-y-2 text-center">
                <div className="text-sm font-semibold">Fade</div>
                <div className="w-[300px] max-w-full mx-auto">
                  <Input type="range" min={0} max={1} step={0.01} value={fade} onChange={(e) => setFade(Number(e.target.value))} />
                </div>
              </div>
            </div>

          </div>
        )}

        {tab === "connectors" && (
          <div className="space-y-4">
            {loading && <div className="text-sm opacity-70">Loading connectors…</div>}
            {error && <div className="text-sm text-red-500">{error}</div>}
            {Array.isArray(connectors) && connectors.length > 0 ? (
              connectors.map((connector) => (
                <ConnectorCard
                  key={connector.id}
                  connector={connector}
                  onUpdate={updateConnector}
                  onAuthorize={authorizeOAuth}
                  onTest={testConnector}
                  onSync={syncConnector}
                />
              ))
            ) : (
              !loading && !error && (
                <div className="text-sm opacity-70">No connectors available</div>
              )
            )}
          </div>
        )}

        {tab === "data" && (
          <div className="space-y-4">
            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="text-sm font-semibold">
                    Migrate from ChatGPT
                  </div>
                  <p className="text-xs opacity-70 leading-relaxed">
                    Import your ChatGPT export. Codexify will preserve project
                    grouping and remove tool-output noise from the user-visible
                    transcript.
                  </p>
                </div>
                <div
                  className="shrink-0 rounded-full border px-2 py-1 text-[11px] font-medium"
                  style={{
                    borderColor: migrationComplete
                      ? "rgba(34, 197, 94, 0.35)"
                      : "var(--panel-border)",
                    color: migrationComplete
                      ? "rgb(134, 239, 172)"
                      : "var(--muted)",
                  }}
                >
                  {migrationComplete ? "Complete" : "Optional"}
                </div>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <Button
                  type="button"
                  onClick={() => setChatGPTModalOpen(true)}
                  className="rounded-[var(--tile-radius,19px)] w-full"
                >
                  Import ChatGPT history
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleDownloadExport}
                  className="rounded-[var(--tile-radius,19px)] w-full"
                >
                  Download Codexify ZIP export
                </Button>
              </div>

              {!migrationComplete && (
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setMigrationStepSkipped(true)}
                    className="rounded-[var(--tile-radius,19px)]"
                  >
                    Skip
                  </Button>
                </div>
              )}

              {migrationStats && (
                <div className="rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide opacity-70">
                    Import Summary
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    <div>Threads imported</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.threads_imported ?? 0}
                    </div>
                    <div>Messages imported</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.messages_imported ?? 0}
                    </div>
                    <div>Projects created</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.projects_created ?? 0}
                    </div>
                    <div>Projects reused</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.projects_reused ?? 0}
                    </div>
                    <div>Messages filtered</div>
                    <div className="text-right tabular-nums">
                      {migrationStats.messages_filtered ?? 0}
                    </div>
                  </div>
                </div>
              )}

              {migrationStepSkipped && !migrationStats && (
                <p className="text-xs opacity-70 leading-relaxed">
                  Migration step skipped for this session. You can come back to
                  import any time.
                </p>
              )}
            </div>
          </div>
        )}

        {tab === "connection" && desktopMode && (
          <div className="space-y-4">
            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="text-sm font-semibold">Desktop Connection</div>
              <p className="text-xs opacity-70">
                Configure backend routing and the public base URL used for copied share links.
              </p>
              <div className="space-y-2">
                <label className="text-xs opacity-80">Backend Base URL</label>
                <Input
                  value={desktopBackendBaseUrl}
                  onChange={(event) => setDesktopBackendBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:8888"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs opacity-80">Share Public Base URL</label>
                <Input
                  value={desktopShareBaseUrl}
                  onChange={(event) => setDesktopShareBaseUrl(event.target.value)}
                  placeholder="http://127.0.0.1:5173"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  onClick={handleSaveConnectionSettings}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Save Connection
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleTestConnection}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Test Connection
                </Button>
              </div>
            </div>

            <div className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-4">
              <div className="text-sm font-semibold">Local API Key (Secure Store)</div>
              <p className="text-xs opacity-70">
                Stored in macOS keychain for desktop local-safe auth.
              </p>
              <Input
                type="password"
                value={desktopApiKeyInput}
                onChange={(event) => setDesktopApiKeyInput(event.target.value)}
                placeholder="Enter Guardian API key"
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  onClick={handleSaveDesktopApiKey}
                  disabled={connectionBusy || !desktopApiKeyInput.trim()}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Save API Key
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleClearDesktopApiKey}
                  disabled={connectionBusy}
                  className="rounded-[var(--tile-radius,19px)]"
                >
                  Clear API Key
                </Button>
              </div>
            </div>

            {connectionMessage && (
              <div className="text-xs text-emerald-300">{connectionMessage}</div>
            )}
            {connectionError && (
              <div className="text-xs text-red-400">{connectionError}</div>
            )}
          </div>
        )}

        {tab === "diagnostics" && (
          <div className="space-y-4">
            <MemoryBrowser />
          </div>
        )}
      </div>

      <ChatGPTImportModal
        open={chatGPTModalOpen}
        onOpenChange={setChatGPTModalOpen}
        userName={userName}
        onImported={(stats) => {
          setMigrationStats(stats);
          setMigrationStepSkipped(false);
        }}
      />
    </div>
  );
}

export default SettingsView;
