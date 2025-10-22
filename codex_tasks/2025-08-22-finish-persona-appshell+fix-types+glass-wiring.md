
Codex CLI Prompt — “Finish Persona AppShell + Fix Types + Glass wiring”

Repo root: guardian-backend_v2/src
Primary entry: src/components/persona/layout/AppShell.tsx
Constraints:
 • Keep PersonaProvider and TagSelector (we’ll just type-fix TagSelector).
 • Keep “Guardian Chat opaque / Dashboard + Workspace glass” design.
 • Do not blur the wallpaper; glass lives only behind Dashboard + Workspace.
 • No visual regressions to copy/layout.

Tasks (apply in order)
 1. Pass wallpaper into all ReactiveGlassCard usages (required prop)

 • File: components/persona/layout/AppShell.tsx
 • Replace each <ReactiveGlassCard className=...> with the same markup plus wallpaperUrl={wallpaper}. There are three instances (Dashboard left, Workspace next to it, Settings’ Workspace).
Example:

<ReactiveGlassCard wallpaperUrl={wallpaper} className="flex min-w-0 flex-1 rounded-2xl overflow-hidden glass-surface">
  <DashboardView ... />
</ReactiveGlassCard>

and

<ReactiveGlassCard wallpaperUrl={wallpaper} className="glass-surface">
  <WorkspacePane />
</ReactiveGlassCard>

 2. Fix TagSelector setter types so setState(prev => …) compiles

 • File: components/persona/TagSelector.tsx
 • Locate the props for setMemoryTags. Change its type to:

setMemoryTags: React.Dispatch<React.SetStateAction<string[]>>;

 • Keep the two call sites:

setMemoryTags(prev => Array.from(new Set([...prev, t])));
setMemoryTags(prev => prev.filter(x => x !== t));

 3. Harden WebGL types & null guards in FrameCard

 • File: components/surface/FrameCard.tsx
 • Ensure you gate all GL calls behind a non-null gl. Do this pattern once, then use gl safely:

const gl = canvas.getContext("webgl") as WebGLRenderingContext | null;
if (!gl) { setFailed(true); return; }

// define helpers that close over non-null gl
function compileShader(type: number, src: string): WebGLShader | null {
  const s = gl.createShader(type);
  if (!s) { setFailed(true); return null; }
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { setFailed(true); return null; }
  return s;
}

 • If helpers currently accept gl implicitly, either (a) move them below the guard so they close over non-null gl, or (b) pass gl: WebGLRenderingContext as a parameter to each helper.
 • Remove non-null assertions on GL calls and rely on the guard.

 4. Button variant mismatch (“outline”)

 • File: features/settings/SettingsView.tsx
 • Change the variant="outline" button to variant="ghost" (or remove the prop) to satisfy components/ui/button.tsx’s Variant union.
Example:

<Button type="button" variant="ghost" size="sm" onClick={triggerFile} className="rounded-xl flex items-center gap-2">

 5. Tauri invoke generics error

 • File: persona/PersonaEngine.ts
 • Remove the generic type parameters on invoke(...) and cast the result instead:

const out = (await invoke("generate_with_memory", { inputPrompt: input_prompt, personaId: persona_id, memoryTags: memory_tags })) as GenerationResult;
return out;

and

const tags = (await invoke("get_all_tags", { personaId: persona_id })) as TagStats[];
return tags;

 6. Tailwind v4 dark mode typing

 • File: tailwind.config.ts
 • Replace darkMode: ["class"], with the 2-tuple form:

darkMode: ["class", "dark"],

 • We toggle document.documentElement.classList.toggle("dark", …) already, so this matches.

 7. CSS tokens / glass helper (safety pass)

 • File: index.css (only if missing these pieces; otherwise skip)
 • Ensure it contains Tailwind v4 import, tokens, and the glass helper class:

@import "tailwindcss";

:root{
  --accent:#6B7280;
  --accent-weak:#7a8490;
  --accent-strong:#5a6270;
  --panel-bg:#f3f4f6;
  --panel-border:#e5e7eb;
  --chip-bg:#e5e7eb;
  --text:#111827;
  --muted:#374151;
}

.dark{
  --panel-bg:#202020;
  --panel-border:#3f3f3f;
  --chip-bg:#2f2f2f;
  --text:#ffffff;
  --muted:rgba(255,255,255,.88);
}

/*glossy card utility used only on Dashboard/Workspace containers*/
.glass-surface{
  backdrop-filter: blur(12px) saturate(120%);
  -webkit-backdrop-filter: blur(12px) saturate(120%);
  box-shadow:
    inset 0 1px rgba(255,255,255,.18),
    inset 0 -1px rgba(0,0,0,.25),
    0 10px 22px rgba(0,0,0,.25);
  background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.04)), rgba(255,255,255,.06);
}

html, body, #root{ height:100%; }
body{ margin:0; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }

⸻

Acceptance criteria
 • pnpm -C ./src typecheck passes with 0 errors.
 • Glass card compiles (no gl is possibly null warnings).
 • ReactiveGlassCard receives wallpaperUrl in AppShell at all call sites.
 • Tag adding/removing in TagSelector works and typechecks.
 • Settings’ “Choose Image” button compiles (no Variant error).
 • invoke(...) calls compile (no “Untyped function calls may not accept type arguments” errors).
 • Tailwind builds without darkMode type errors; dark mode toggles via the .dark class as before.
 • Visuals: Guardian Chat remains opaque; Dashboard + Workspace show refractive glass; wallpaper remains crisp behind them; header seam is gone.

Runbook (for Codex to execute)
 1. Apply all edits above.
 2. Run: pnpm -C ./src typecheck → expect 0 errors.
 3. Run: pnpm -C ./src dev and (in another terminal) pnpm tauri dev if needed.
 4. Verify the acceptance criteria checkboxes.
 5. Commit on current branch:

git add -A
git commit -m "ui: finish persona AppShell — glass wiring, type fixes, tailwind darkMode"
