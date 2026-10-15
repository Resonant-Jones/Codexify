# Codexify brand assets

The supplied October 2026 artwork replaces the previous mark and desktop placeholder.

- `codexify-mark.png`: original 256 px app icon, used by conversation-origin badges, mobile navigation, the header, and the local/default provider badge.
- `codexify-appicon-big.png`: original 1254 px app icon, retained as the desktop and large install-icon source.
- `codexify-mark.svg` and `codexify-mark-micro.svg`: the supplied `emblem-chunk.svg`, preserving its path, stroke width, and transparent `currentColor` treatment.
- `codexify-lockup-horizontal.svg`: the supplied emblem alongside the existing outlined wordmark.

Browser assets live in `frontend/src/public`, the configured Vite public directory. `icons/icon-{16,32,48,128,192}.png` and `icons/apple-touch-icon.png` derive from the small source; `icons/icon-512.png` derives from the big source. The Chrome extension emits the shared 16, 32, 48, and 128 px assets. The multi-resolution `favicon.ico` is also mirrored at the legacy `frontend/public/favicon.ico` path.

`src-tauri/icons` contains the configured desktop PNG, ICO, and ICNS assets. PNGs through 256 px and ICO derive from the small source; larger PNGs and ICNS derive from the big source. The Tauri browser-host candidate shares the 512 px desktop icon. No packaging, signing, or release qualification is implied by replacing these assets.

Generate sizes with the installed CLI, for example from the repository root:

```sh
pnpm exec tauri icon frontend/src/assets/brands/codexify/codexify-mark.png --output /tmp/codexify-small-icons
pnpm exec tauri icon frontend/src/assets/brands/codexify/codexify-appicon-big.png --output /tmp/codexify-big-icons
pnpm exec tauri icon frontend/src/assets/brands/codexify/codexify-mark.png --output /tmp/codexify-web-icons --png 16 --png 32 --png 48 --png 128 --png 180 --png 192
pnpm exec tauri icon frontend/src/assets/brands/codexify/codexify-appicon-big.png --output /tmp/codexify-install-icons --png 512
```

Copy only the required generated files into their existing destinations. Keep the supplied source images and emblem geometry intact.
