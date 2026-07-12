# Appearance presets

Appearance is applied through the real Settings UI so the demo lane follows the supported product seam. The Rowan preset is stored in `Demo-Assets/peekaboo-demo/appearance-preset.json` and is applied by `make demo-style`.

The current controls are browser-local: theme, base color, depth, fade, wallpaper, and wallpaper blur. Wallpaper is persisted as `cfy.wallpaper`; it is not an account preference or backend API. Each style run must reload the app and verify the values before capturing `captures/appearance-proof.png`.

The wallpaper is a generated, cached project asset. It contains no people, text, logos, or product claims and is used only as atmosphere behind captured UI.
