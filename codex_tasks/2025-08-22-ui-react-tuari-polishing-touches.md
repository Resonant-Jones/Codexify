# PATCH 1 ───────────── ──  src/index.css

# 1A.  Add a robust CSS-only glass fallback that kicks in whenever the

# <FrameCard> sets .glass-surface but shader init fails

/*-----------------------------------------------
   GLASS SURFACE  (WebGL succeeds = shader canvas)
              OR  (WebGL fails    = CSS fallback)
   --------------------------------------------- */
.glass-surface {
  /* keep your existing rounded-xl etc. from Tailwind*/
  position: relative;
  isolation: isolate;
}
.glass-surface::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  z-index: -1;

  /*Fallback look: 8‒12 px blur, slight saturation pop,
     and a semi-opaque panel color driven by your CSS vars*/
  background: rgba(var(--panel-bg-rgb, 30 30 30), 0.55);
  backdrop-filter: saturate(140%) blur(12px);
  box-shadow: 0 0 0 1px rgba(var(--panel-border-rgb, 255 255 255), 0.08),
              0 4px 16px rgba(0 0 0 / 0.25);
}

/*When the shader *does* succeed, <canvas> sits on top of ::before,
   so we still see the fancy refraction. No change needed there.*/

/*-----------------------------------------------
   SAFE DEFAULTS so text isn’t hard-left
   --------------------------------------------- */
body,
html,
# root {
  height: 100%;
}
body {
  margin: 0;              /* Tailwind pre-flight sometimes skipped*/
  padding: 0;
}

* {
  box-sizing: border-box; /*stops weird scrollbars in tight grids*/
}

# PATCH 2 ───────────── ──  src/components/persona/layout/AppShell.tsx

# 2A.  Wrap the entire shell in a flex column with horizontal padding

# so content isn’t glued to the left edge on every screen size

# (No visual change to internals, just breathing room.)

* return (
* <div className={`h-dvh w-full p-[3px] ${resolved === "dark" ? "dark" : ""}`} …>

+ return (
* <div
*     className={`h-dvh w-full flex flex-col px-4 pb-4 gap-4 ${
*       resolved === "dark" ? "dark" : ""
*     }`}
*     …

# Nothing inside AppShell needs to change – the extra padding/spacing

# is handled by this wrapper

# PATCH 3 ───────────── ──  src/components/surface/FrameCard.tsx

# 3A.  If shader fails (setFailed(true)), add class 'fallback' so

# CSS can style the card (optional, but lets you test quickly)

@@
*      if (!gl) { setFailed(true); return; }

+      if (!gl) { setFailed(true); ref.current?.classList.add("fallback"); return; }
   …

-      if (!vs || !fs) return;

+      if (!vs || !fs) { setFailed(true); ref.current?.classList.add("fallback"); return; }

# 3B.  Export stays default & named as you already fixed

# PATCH 4 ───────────── ──  src/index.css  (end of file)

# 4A.  Style the WebGL-failed state a bit differently (bonus)

.glass-surface.fallback::before {
  /*ever-so-slightly less opacity when shader missing*/
  background: rgba(var(--panel-bg-rgb, 30 30 30), 0.45);
  backdrop-filter: saturate(120%) blur(10px);
}
