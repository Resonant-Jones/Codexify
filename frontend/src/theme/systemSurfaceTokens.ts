/**
 * Shared presentation tokens for Codexify-authored System Surfaces.
 *
 * These values are deliberately independent of workspace accent and material
 * personalization. They describe UI presentation only; they are not runtime
 * or protocol state tokens.
 */
export type SystemSurfaceTheme = "dark" | "light";

type SystemSurfaceTokenMap = Record<string, string>;

const SYSTEM_SURFACE_TOKENS: Record<SystemSurfaceTheme, SystemSurfaceTokenMap> = {
  dark: {
    "--system-surface-blur": "8px",
    "--system-surface-action": "#5ab7ff",
    "--system-surface-action-hover": "#93c5fd",
    "--system-surface-action-foreground": "#111827",
    "--system-surface-success": "#86efac",
    "--system-surface-attention": "#fcd34d",
  },
  light: {
    "--system-surface-blur": "8px",
    "--system-surface-action": "#1d4ed8",
    "--system-surface-action-hover": "#1e40af",
    "--system-surface-action-foreground": "#ffffff",
    "--system-surface-success": "#166534",
    "--system-surface-attention": "#92400e",
  },
};

export function getSystemSurfaceTokens(
  theme: SystemSurfaceTheme = "dark"
): SystemSurfaceTokenMap {
  return { ...SYSTEM_SURFACE_TOKENS[theme] };
}
