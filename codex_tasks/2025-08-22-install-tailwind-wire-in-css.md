Repo: guardian-backend_v2/src  (Vite + React)

TASK 1 – Install and wire Tailwind CSS

- If not already in package.json devDependencies add: tailwindcss ^4, postcss ^8, autoprefixer ^10
- Create or patch ./src/tailwind.config.ts:
      export default {
        content: ["./index.html", "./**/*.{ts,tsx}"],
        darkMode: ["class","dark"],
        theme: { extend: {} },
        plugins: [],
      }
- Create or patch ./src/postcss.config.cjs with:
      module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } }
- Ensure ./src/index.css starts with:
      @tailwind base;
      @tailwind components;
      @tailwind utilities;
    and keeps the existing custom CSS (root variables, .glass-surface etc.) below.

TASK 2 – Clean up stray CSS variables

- After Tailwind imports, leave :root { --accent: … } block intact.
- No change to React components.

TASK 3 – Verify

- Run `pnpm -C ./src typecheck` (should stay green).
- Run `pnpm -C ./src dev` and confirm:
      • Dashboard/Workspace cards show frosted blur
      • Buttons/inputs are rounded (Tailwind styles visible)
      • Top nav has proper spacing, not glued to edges.

Commit as: “style(ui): enable Tailwind preflight + utilities”
