import { useEffect, useSyncExternalStore } from "react";
import api from "@/lib/api";
import { useAuthState } from "@/lib/authState";
import { registerWallpaperWriter } from "@/lib/wallpaperPreference";

export type Appearance = {
  theme_mode: "system" | "light" | "dark";
  base_color: string;
  background_depth: number;
  background_fade: number;
  surface_depth: number;
  surface_warmth: number;
  glass_treatment: "refractive" | "frosted" | "solid";
};
export const DEFAULT_APPEARANCE: Appearance = {
  theme_mode: "system", base_color: "#6B7280", background_depth: 0.6,
  background_fade: 0.4, surface_depth: 50, surface_warmth: 0,
  glass_treatment: "refractive",
};
type Presentation = { settings: Appearance; workspace_unique: boolean; wallpaper_url: string | null };
export type AccountAppearanceState = {
  epoch: number; ready: boolean; saving: boolean; error: string | null;
  greetingName: string | null; settings: Appearance; workspaceUnique: boolean;
  wallpaperSrc: string | null;
};
const EMPTY: AccountAppearanceState = {
  epoch: 0, ready: false, saving: false, error: null, greetingName: null,
  settings: DEFAULT_APPEARANCE, workspaceUnique: false, wallpaperSrc: null,
};
const ROOT = "/api/auth/scout/profile";
const PRESENTATION = ROOT + "/presentation";

let transientWorkspace: string | undefined;
export function presentationWorkspaceId(): string {
  if (transientWorkspace) return transientWorkspace;
  try {
    const saved = localStorage.getItem("cfy.presentation.workspaceId");
    if (saved && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(saved)) return (transientWorkspace = saved);
  } catch { /* The identifier can still live for this document lifetime. */ }
  transientWorkspace = crypto.randomUUID();
  try { localStorage.setItem("cfy.presentation.workspaceId", transientWorkspace); } catch { /* No profile values are stored here. */ }
  return transientWorkspace;
}

export class AccountPresentationController {
  private state: AccountAppearanceState = EMPTY;
  private listeners = new Set<() => void>();
  private token: string | null = null;
  private epoch = 0;
  private abort = new AbortController();
  private workspace = "";
  private confirmed = DEFAULT_APPEARANCE;
  private pending: Partial<Appearance> = {};
  private retryPatch: Partial<Appearance> | null = null;
  private retryAction: (() => void) | null = null;
  private revision = 0;
  private refreshSequence = 0;
  private draining = false;
  private writes = 0;
  private wallpaperPath: string | null = null;
  constructor(private client = api, private makeWorkspace = presentationWorkspaceId) {}

  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  getSnapshot = () => this.state;
  matches = (token: string | null) => this.token === token;
  private emit(patch: Partial<AccountAppearanceState>) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((listener) => listener());
  }
  private headers() { return { Authorization: `Bearer ${this.token}` }; }
  private busy() { this.emit({ saving: this.writes > 0 || this.draining }); }
  private revokeWallpaper() {
    if (this.state.wallpaperSrc) URL.revokeObjectURL(this.state.wallpaperSrc);
    this.wallpaperPath = null;
  }

  connect(token: string | null) {
    if (token === this.token) return;
    this.abort.abort(); this.abort = new AbortController();
    this.token = token; this.epoch += 1;
    this.revokeWallpaper(); this.pending = {}; this.retryPatch = null; this.retryAction = null; this.revision += 1;
    this.draining = false; this.writes = 0; this.confirmed = DEFAULT_APPEARANCE;
    this.state = { ...EMPTY, epoch: this.epoch };
    this.listeners.forEach((listener) => listener());
    if (token) { this.workspace = this.makeWorkspace(); void this.refresh(); }
  }

  private async adopt(data: Presentation, epoch: number, revision?: number) {
    if (epoch !== this.epoch || (revision !== undefined && revision !== this.revision)) return;
    this.confirmed = { ...DEFAULT_APPEARANCE, ...data.settings };
    this.emit({ settings: { ...this.confirmed, ...this.pending }, workspaceUnique: data.workspace_unique });
    if (data.wallpaper_url === this.wallpaperPath) return;
    this.revokeWallpaper(); this.emit({ wallpaperSrc: null });
    if (data.wallpaper_url) {
      const response = await this.client.get<Blob>(data.wallpaper_url, { responseType: "blob", signal: this.abort.signal, headers: this.headers() });
      if (epoch !== this.epoch || (revision !== undefined && revision !== this.revision)) return;
      this.wallpaperPath = data.wallpaper_url;
      this.emit({ wallpaperSrc: URL.createObjectURL(response.data) });
    }
  }

  async refresh() {
    if (!this.token || this.draining || this.writes) return;
    const epoch = this.epoch, revision = this.revision, sequence = ++this.refreshSequence;
    try {
      const [name, presentation] = await Promise.all([
        this.client.get<{ greeting_name: string | null }>(ROOT, { signal: this.abort.signal, headers: this.headers() }),
        this.client.get<Presentation>(PRESENTATION, { params: { workspace_id: this.workspace }, signal: this.abort.signal, headers: this.headers() }),
      ]);
      if (epoch !== this.epoch || revision !== this.revision || sequence !== this.refreshSequence) return;
      await this.adopt(presentation.data, epoch, revision);
      if (epoch === this.epoch && revision === this.revision && sequence === this.refreshSequence) this.emit({ ready: true, greetingName: name.data.greeting_name?.trim() || null, error: this.retryPatch ? this.state.error : null });
    } catch {
      if (epoch === this.epoch && revision === this.revision && sequence === this.refreshSequence) this.emit({ error: "Couldn’t load account appearance. Try again." });
    }
  }

  update(settings: Partial<Appearance>, expectedEpoch = this.epoch) {
    if (expectedEpoch !== this.epoch) return;
    if (!this.state.ready || !this.token) return;
    this.revision += 1; this.retryAction = null;
    this.pending = { ...this.pending, ...settings }; this.retryPatch = null;
    this.emit({ settings: { ...this.state.settings, ...settings }, error: null });
    if (!this.draining) void this.drain();
  }
  private async drain() {
    const epoch = this.epoch;
    this.draining = true; this.busy();
    try {
      while (Object.keys(this.pending).length && epoch === this.epoch) {
        const settings = this.pending; this.pending = {};
        try {
          const response = await this.client.patch<Presentation>(PRESENTATION, { workspace_id: this.workspace, settings }, { signal: this.abort.signal, headers: this.headers() });
          if (epoch !== this.epoch) return;
          await this.adopt(response.data, epoch);
        } catch {
          if (epoch !== this.epoch) return;
          this.retryPatch = { ...settings, ...this.pending }; this.pending = {};
          this.emit({ settings: this.confirmed, error: "Couldn’t save appearance. Try again." });
          break;
        }
      }
    } finally {
      if (epoch === this.epoch) { this.draining = false; this.busy(); }
    }
  }

  async saveGreeting(greetingName: string | null, expectedEpoch = this.epoch): Promise<boolean> {
    if (expectedEpoch !== this.epoch) return false;
    if (!this.token || !this.state.ready) return false;
    const epoch = this.epoch; this.revision += 1; this.retryAction = null; this.writes += 1; this.busy();
    try {
      const response = await this.client.patch<{ greeting_name: string | null }>(ROOT, { greeting_name: greetingName }, { signal: this.abort.signal, headers: this.headers() });
      if (epoch !== this.epoch) return false;
      this.emit({ greetingName: response.data.greeting_name, error: null });
      return true;
    } catch {
      if (epoch === this.epoch) { this.retryAction = () => { void this.saveGreeting(greetingName, epoch); }; this.emit({ error: "Couldn’t save your greeting name. Try again." }); }
      return false;
    } finally { if (epoch === this.epoch) { this.writes -= 1; this.busy(); } }
  }

  async setWorkspaceUnique(unique: boolean, expectedEpoch = this.epoch) {
    if (expectedEpoch !== this.epoch) return;
    if (!this.token || !this.state.ready || this.state.saving) return;
    const epoch = this.epoch; this.revision += 1; this.retryAction = null; this.writes += 1; this.busy();
    try {
      const response = await this.client.patch<Presentation>(PRESENTATION, { workspace_id: this.workspace, workspace_unique: unique }, { signal: this.abort.signal, headers: this.headers() });
      await this.adopt(response.data, epoch);
      if (epoch === this.epoch) this.emit({ error: null });
    } catch { if (epoch === this.epoch) { this.retryAction = () => { void this.setWorkspaceUnique(unique, epoch); }; this.emit({ error: "Couldn’t change appearance sync. Try again." }); } }
    finally { if (epoch === this.epoch) { this.writes -= 1; this.busy(); } }
  }

  async uploadWallpaper(blob: Blob | null, expectedEpoch = this.epoch) {
    if (expectedEpoch !== this.epoch) return;
    if (!this.token || !this.state.ready || this.state.saving) return;
    if (blob && blob.size > 5 * 1024 * 1024) { this.emit({ error: "Choose an image up to 5 MB." }); return; }
    const epoch = this.epoch; this.revision += 1; this.retryAction = null; this.writes += 1; this.busy();
    try {
      const response = blob
        ? await this.client.put<Presentation>(PRESENTATION + "/wallpaper", blob, { params: { workspace_id: this.workspace }, signal: this.abort.signal, headers: { ...this.headers(), "Content-Type": blob.type || "application/octet-stream" } })
        : await this.client.patch<Presentation>(PRESENTATION, { workspace_id: this.workspace, clear_wallpaper: true }, { signal: this.abort.signal, headers: this.headers() });
      await this.adopt(response.data, epoch);
      if (epoch === this.epoch) this.emit({ error: null });
    } catch { if (epoch === this.epoch) { this.retryAction = () => { void this.uploadWallpaper(blob, epoch); }; this.emit({ error: "Couldn’t save wallpaper. Choose a still PNG, JPEG or WebP up to 5 MB." }); } }
    finally { if (epoch === this.epoch) { this.writes -= 1; this.busy(); } }
  }

  async wallpaperFromSource(src: string | null, expectedEpoch = this.epoch) {
    if (expectedEpoch !== this.epoch) return;
    if (src === null) return this.uploadWallpaper(null, expectedEpoch);
    if (!this.token || !this.state.ready) return;
    const epoch = this.epoch;
    try {
      const url = new URL(src, window.location.href);
      // Never attach credentials to arbitrary image hosts or persist signed URLs.
      const apiOrigin = new URL(this.client.defaults.baseURL || "/", window.location.href).origin;
      if (![window.location.origin, apiOrigin].includes(url.origin) || !/^\/(?:api\/)?media\//.test(url.pathname)) throw new Error("Unsupported image source");
      const response = await this.client.get<Blob>(url.pathname + url.search, { responseType: "blob", signal: this.abort.signal, headers: this.headers() });
      if (epoch === this.epoch) await this.uploadWallpaper(response.data);
    } catch { if (epoch === this.epoch) this.emit({ error: "Choose a wallpaper from your images or upload a file." }); }
  }

  retry() {
    if (this.retryPatch) { const patch = this.retryPatch; this.retryPatch = null; this.update(patch); }
    else if (this.retryAction) { const retry = this.retryAction; this.retryAction = null; retry(); }
    else void this.refresh();
  }
}

export const accountPresentation = new AccountPresentationController();
registerWallpaperWriter((src, epoch) => { void accountPresentation.wallpaperFromSource(src, epoch); });

export function useAccountPresentation() {
  const auth = useAuthState();
  const state = useSyncExternalStore(accountPresentation.subscribe, accountPresentation.getSnapshot, () => EMPTY);
  const token = auth.ready && auth.status === "authenticated" ? auth.token ?? null : null;
  return accountPresentation.matches(token) ? state : EMPTY;
}

export function useAccountPresentationSession() {
  const auth = useAuthState();
  const token = auth.ready && auth.status === "authenticated" ? auth.token ?? null : null;
  useEffect(() => { accountPresentation.connect(token); }, [token]);
  useEffect(() => {
    const refresh = () => { if (document.visibilityState !== "hidden") void accountPresentation.refresh(); };
    window.addEventListener("focus", refresh); document.addEventListener("visibilitychange", refresh);
    const interval = window.setInterval(refresh, 30000);
    return () => { window.clearInterval(interval); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, []);
  return useAccountPresentation();
}
