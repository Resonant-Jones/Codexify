
🛠️ Codex CLI Prompt — “Fix vitest globals, glass exports, WebGL types, & tighten TagSelector tests”

Context / constraints
 • Keep runtime visuals the same.
 • Do not create new files; modify existing ones only.
 • Frontend lives in src/.
 • Tests are under src/components/persona/__tests__ and src/components/ui/__tests__.

⸻

1) Make TypeScript aware of Vitest globals

Edit src/tsconfig.json:
 • Inside "compilerOptions", add or replace:

"types": ["vitest/globals", "vite/client", "node"]

If types already exists, overwrite its value with the array above.

⸻

2) Normalize vitest config + alias

Replace the entire contents of src/vitest.config.ts with:

import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: resolve(__dirname, "src/test/setup.ts"),
    css: true,
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
});

⸻

3) Fix glass card exports to stop “Element type is invalid”

Replace the entire contents of src/components/surface/ReactiveGlassCard.tsx with:

// Surface adapter: ensure both default and named exports exist
export { default as ReactiveGlassCard } from "@/components/ui/RefractiveGlassCard";
export { default } from "@/components/ui/RefractiveGlassCard";

Update imports in AppShell:

Edit src/components/persona/layout/AppShell.tsx:
 • Find any import of the glass card like:
 • import ReactiveGlassCard from "@/components/ui/RefractiveGlassCard"; or
 • import { ReactiveGlassCard } from "@/components/ui/RefractiveGlassCard";
 • Replace with:

import ReactiveGlassCard from "@/components/surface/ReactiveGlassCard";

(Leave all <ReactiveGlassCard ... wallpaperUrl={wallpaper} /> usages as-is.)

⸻

4) Quiet TypeScript’s “possibly null” WebGL errors

Edit src/components/ui/RefractiveGlassCard.tsx:

A) Ensure it has a default export.
 • If it’s export function RefractiveGlassCard(...), change to:

export default function RefractiveGlassCard(props: Props) {

 • If it’s const RefractiveGlassCard = (...) => {}, make sure the bottom has:

export default RefractiveGlassCard;

B) Change compileShader to accept a non-null gl:
 • Find the helper that begins with function compileShader( and replace it with:

function compileShader(gl: WebGLRenderingContext, type: number, src: string) {
  const s = gl.createShader(type);
  if (!s) return null;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) return null;
  return s;
}

C) In the effect where you grab canvas, el, and gl, add early guards and pass gl explicitly:

Right after you have references like const el = ref.current and const canvas = canvasRef.current, add:

if (!el || !canvas) { setFailed(true); return; }
const gl = (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")) as WebGLRenderingContext | null;
if (!gl) { setFailed(true); return; }

Then replace later calls like:

const vs = compileShader(gl, gl.VERTEX_SHADER, VERT_SRC);
const fs = compileShader(gl, gl.FRAGMENT_SHADER, FRAG_SRC);
if (!vs || !fs) { setFailed(true); return; }

Before using any of these, ensure non-null:

if (!prog || !quad || !tex) { setFailed(true); return; }

And do not use ! non-null assertions on gl, canvas, or el. With the guards, TS will narrow types.

⸻

5) Tighten TagSelector tests to avoid counting the “Add alpha” suggestion

Edit src/components/persona/__tests__/tag-selector.normalize.test.tsx:
 • Replace:

const alphas = screen.getAllByText(/^alpha$/i);
expect(alphas).toHaveLength(1);

 • With:

const removeBtns = screen.getAllByRole("button", { name: /remove alpha/i });
expect(removeBtns).toHaveLength(1);

Edit src/components/persona/__tests__/tag-selector.test.tsx:
 • Replace the final assertion:

expect(screen.queryByText("alpha")).not.toBeInTheDocument();

 • With:

expect(screen.queryByRole("button", { name: /remove alpha/i })).not.toBeInTheDocument();

(This scopes assertions to selected chips, not the optional “Add alpha” action.)

⸻

6) Remove one unused ts-expect-error

Edit src/components/persona/__tests__/theme-toggle-and-storage.test.tsx:
 • Delete the single line:

// @ts-expect-error jsdom shim

⸻

7) Run & verify

# frontend only

pnpm -C ./src typecheck
pnpm -C ./src test

You should see:
 • ✅ tsc clean (vitest globals recognized; WebGL null errors gone)
 • ✅ AppShell tests no longer crash (glass import/export fixed)
 • ✅ TagSelector tests pass (no double “alpha”, no false failure after remove)

⸻

(Optional) Nice-to-have follow-ups
 • Consider clearing TagSelector’s input after “Add” (keeps UI tidy and would’ve also avoided the “Add alpha” false hit).
 • If you ever want to assert counts on chips precisely, adding data-testid="tag-chip" in TagSelector and filtering with within(...) is a clean pattern.

⸻
