# UI Tune Rack (Playground)

A gated, dev-only playground for auditioning radius, glass, shadows, and tile layouts.
Lives at the route **`/dev/tune`** and **does not** affect production unless you enable it.

- **Folder (repo path):** `src/dev/ui-tune/`  
  (Shorthand in convo: `dev/ui-tune`)
- **Entry docs:** this README.

## Activate

1) Ensure these files exist:
   - `src/dev/ui-tune/UITunePad.tsx`
   - `src/dev/ui-tune/ui-tune.dev.css`

2) Run with the rack enabled:

```bash
VITE_TUNE=1 pnpm dev
# or add a script in package.json:
# "dev:tune": "VITE_TUNE=1 vite",
pnpm dev:tune
```

3) Visit in your browser:
```
/dev/tune
```

If the files are missing, the app shows a friendly “UI Tune Rack not found” message.

## How it’s gated

`src/App.tsx` checks two things:
- The environment: `import.meta.env.DEV` **or** `import.meta.env.VITE_TUNE === "1"`.
- The URL path starts with `/dev/tune`.

Only when both are true does it **lazy-load** these modules:
- `src/dev/ui-tune/UITunePad.tsx`
- `src/dev/ui-tune/ui-tune.dev.css`

No flag or wrong route ⇒ normal `<AppShell />` (production path).

## Scoping (no leaks)

- All CSS variables are set under **`.tune-sandbox { ... }`** (not `:root`).
- The sandbox is a standalone wrapper; production tokens remain authoritative.

## Mapping to real tokens

The rack “listens” to your AppShell tokens so tests feel realistic:

```css
/* ui-tune.dev.css */
.tune-sandbox{
  --radius: var(--card-radius, 19px);
  --panel:  var(--panel-bg, rgba(255,255,255,.78));
  --glass:  var(--chip-bg, rgba(255,255,255,.60));
  --border: var(--panel-border, rgba(20,23,28,.10));
}
```

## Promote a winning look

1) In the sandbox, tweak variables until it sings.  
2) Copy the **numbers only** into AppShell tokens (e.g., set `--radius-tile: 19px`, `--card-radius: var(--radius-tile)`).  
3) Commit. The rack is for experiments; **AppShell** is the source of truth.

## Optional scripts

```jsonc
// package.json
{
  "scripts": {
    "dev:tune": "VITE_TUNE=1 vite",
    "preview:tune": "VITE_TUNE=1 vite preview"
  }
}
```

## Audit checklist

- All rounded layers report the **same** computed `border-radius` (no corner ghosts).  
- Hover shadows don’t reveal squared edges at 200–300% zoom.  
- Rack styles are scoped; production pages unaffected.
