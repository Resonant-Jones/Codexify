# Codexify Interface Closeups

## Purpose

This packet defines a short Remotion-based interface study for Codexify. The goal is not a launch trailer or feature-claim reel. It is a calm, cinematic closeup sequence focused on shell styling, glass geometry, workspace behavior, and Persona Studio style configuration surfaces.

Target output:

- Title: `Codexify Interface Closeups`
- Duration: `45-60s`
- Format: `1920x1080`
- Aspect ratio: `16:9`
- Framerate: `30fps`

## Source Truth Boundaries

Keep the video anchored to visible UI behavior and current documented posture in this repo.

Safe present-tense focus:

- Codexify has a shell with token-driven glass styling surfaces.
- Guardian is conversation-first and should be framed as a clean chat surface.
- Workspace exists as a persistent side surface.
- Persona Studio is a real named configuration surface with tabs such as `Identity`, `Model`, `Voice`, `Tools`, `Retrieval`, and `Truth Matrix`.
- Dashboard, Documents, and Gallery can appear as supporting interface fragments when represented as cards or screenshots.

Do not widen beyond visible or documented UI truth.

## Shot List

1. `0:00-0:05` — `The Shell`
   Establish the full interface as a floating glass object with a slow push-in.
   Caption: `A local-first workspace, built around the interface.`

2. `0:05-0:12` — `Glass Geometry`
   Macro crop across edges, bevel, rim, and layered panels.
   Token chips: `radius`, `bezel`, `rim`, `surface`
   Caption: `Every surface follows the same visual law.`

3. `0:12-0:20` — `Guardian`
   Close on the chat lane and composer region.
   Keep diagnostic clutter out of the message lane.
   Caption: `Conversation stays primary.`

4. `0:20-0:30` — `Workspace`
   Reveal the side surface as a layered drawer with `Shelf`, `Scratchpad`, and `Inspector`.
   Caption: `A side surface for what you're actively holding.`

5. `0:30-0:42` — `Personalization`
   Persona Studio closeups centered on profile identity, model, retrieval, tools, permissions, or voice.
   Caption: `Profiles configure behavior without owning identity.`

6. `0:42-0:52` — `Continuity`
   Glide across Dashboard, Documents, and Gallery-like fragments as one continuous environment.
   Caption: `Your materials stay within reach.`

7. `0:52-0:60` — `End Frame`
   Return to the full shell with tiny end text only.
   Text: `Codexify`
   Optional subtitle: `Interface study`

## Screenshot Checklist

Preferred screenshots:

- `dashboard.png`
- `guardian.png`
- `workspace.png`
- `persona-studio.png`
- `documents.png`

Helpful capture guidance:

- Capture at full UI resolution with clean shell chrome.
- Avoid debug overlays, browser chrome, terminal windows, and notification noise.
- Favor balanced states with realistic content density.
- Keep Guardian captures clean and conversation-first.
- Capture Workspace with layered side-surface presence if possible.
- Capture Persona Studio with visible profile/config controls, not marketing copy.

## Asset Naming Convention

Use these local placeholder paths unless real assets replace them:

- `/public/demo/codexify/dashboard.png`
- `/public/demo/codexify/guardian.png`
- `/public/demo/codexify/workspace.png`
- `/public/demo/codexify/persona-studio.png`
- `/public/demo/codexify/documents.png`

If alternate screenshots are generated, keep the same semantic names so the scene file can swap assets without code edits.

## Render Instructions

Scene component:

- `CodexifyInterfaceCloseups`

Expected Remotion composition settings:

- Width: `1920`
- Height: `1080`
- FPS: `30`
- Duration: `1800` frames for a full `60s` cut, or trim slightly shorter in composition registration if desired.

Visual behavior:

- Slow camera drift
- Soft zooms
- Macro screenshot crops
- Shallow parallax between screenshot planes and token chips
- Soft border glow
- Light sweep accents
- Graceful fallback panels when screenshots are absent

## Claim-Safety Notes

- Keep captions minimal and interface-oriented.
- Treat this as a surface study, not a capabilities reel.
- Do not turn the sequence into a feature checklist.
- Do not imply runtime guarantees that the UI alone does not prove.
- Do not imply public-cloud posture from shell polish.
- Do not imply hidden autonomous behavior from calm motion language.

## Do Not Say

- Do not say `fully autonomous`
- Do not say `cloud-ready`
- Do not say `self-healing` as a current shipped feature
- Do not say `federated graph memory` as current release behavior
- Do not say `desktop app replaces Compose` as current supported path

## Future Polish Ideas

- Replace placeholder fallbacks with exact same-day screenshots from the supported local path.
- Add very light depth-mask transitions derived from screenshot alpha mattes.
- Introduce a subtle cursor-focus shimmer for Guardian composer moments.
- Use route-specific accent grading so Guardian, Workspace, and Persona Studio each carry a slightly different surface temperature.
- Add a restrained ambient bed and micro-interface sound design if the edit later gains audio.
