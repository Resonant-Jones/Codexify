// Explicit account fixtures for controlled settings and shell-renderer tests.
// Transport, ownership and lifecycle use the real controller in its own suite.
import { useSyncExternalStore } from "react";
import type { AccountAppearanceState, Appearance } from "@/features/settings/accountPresentation";
import { registerWallpaperWriter } from "@/lib/wallpaperPreference";

export const DEFAULT_APPEARANCE: Appearance = {
  theme_mode: "system", base_color: "#6B7280", background_depth: 0.6,
  background_fade: 0.4, surface_depth: 50, surface_warmth: 0,
  glass_treatment: "refractive",
};
const listeners = new Set<() => void>();
const initial = (): AccountAppearanceState => ({
  epoch: 1, ready: true, saving: false, error: null, greetingName: null,
  settings: { ...DEFAULT_APPEARANCE }, workspaceUnique: false, wallpaperSrc: null,
});
let state = initial();
export const wallpaperSelections: Array<string | null> = [];
export function setAccountAppearanceFixture(
  patch: Partial<Omit<AccountAppearanceState, "settings">> & { settings?: Partial<Appearance> },
) {
  state = { ...state, ...patch, settings: { ...state.settings, ...patch.settings } };
  listeners.forEach((listener) => listener());
}
export function resetAccountAppearanceFixture() {
  state = initial();
  wallpaperSelections.length = 0;
  listeners.forEach((listener) => listener());
}
export const accountPresentation = {
  getSnapshot: () => state,
  update: (settings: Partial<Appearance>) => setAccountAppearanceFixture({ settings }),
  saveGreeting: async (greetingName: string | null) => {
    setAccountAppearanceFixture({ greetingName }); return true;
  },
  setWorkspaceUnique: async (workspaceUnique: boolean) => setAccountAppearanceFixture({ workspaceUnique }),
  uploadWallpaper: async (blob: Blob | null) => setAccountAppearanceFixture({ wallpaperSrc: blob ? "blob:account-wallpaper" : null }),
  wallpaperFromSource: (src: string | null, epoch?: number) => {
    if (epoch !== undefined && epoch !== state.epoch) return;
    wallpaperSelections.push(src);
    setAccountAppearanceFixture({ wallpaperSrc: src ? "blob:account-wallpaper" : null });
  },
  retry: () => {},
};
registerWallpaperWriter(accountPresentation.wallpaperFromSource);
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
export function useAccountPresentation() {
  return useSyncExternalStore(subscribe, accountPresentation.getSnapshot, accountPresentation.getSnapshot);
}
export const useAccountPresentationSession = useAccountPresentation;
