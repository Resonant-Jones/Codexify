"""Portable, non-sensitive account appearance preferences."""

ACCOUNT_PRESENTATION_SCOPE = "account"
MAX_PRESENTATION_WORKSPACES = 16
MAX_WALLPAPER_BYTES = 5 * 1024 * 1024
MAX_WALLPAPER_PIXELS = 16_000_000
PRESENTATION_DEFAULTS = {
    "theme_mode": "system",
    "base_color": "#6B7280",
    "background_depth": 0.6,
    "background_fade": 0.4,
    "surface_depth": 50,
    "surface_warmth": 0,
    "glass_treatment": "refractive",
}
WALLPAPER_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
