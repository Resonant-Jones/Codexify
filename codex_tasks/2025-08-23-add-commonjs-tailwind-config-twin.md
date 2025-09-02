# ────────────────────────────────────────────────────────────────────

# Codex CLI prompt – Add CommonJS Tailwind config twin (CLI will see it)

# ────────────────────────────────────────────────────────────────────

TITLE: Add tailwind.config.cjs so Tailwind CLI reads our config

GOAL

- The Tailwind CLI (and any Node‐tooling) must load our Tailwind config.
- We currently have it only in TypeScript (src/tailwind.config.ts).  
  The CLI ignores .ts files unless extra loaders are added.
- Fix this by adding a CommonJS twin: src/tailwind.config.cjs.

CONSTRAINTS

- Do **NOT** remove or edit src/tailwind.config.ts – Vite still uses it.
- Do **NOT** touch any other files or change runtime behaviour.
- Keep the config values identical (content, darkMode, theme, plugins).

TASKS

1. **Create** a new file:  
   `src/tailwind.config.cjs`

2. **File contents** (exact):  

   ```js
   // Duplicate of tailwind.config.ts for tools that expect CommonJS.
   // Keep this in sync with the .ts version.
   module.exports = {
     content: ["./index.html", "./**/*.{ts,tsx}"],
     darkMode: ["class", "dark"],
     theme: { extend: {} },
     plugins: [],
   };
