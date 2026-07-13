# Cinematic V2 review notes

- Source of truth: real Peekaboo UI captures and the scoped Rowan seed.
- Factual master remains separate at `renders/codexify-peekaboo-16x9.mp4`.
- Cinematic render is a deterministic interpretation, not additional product proof.
- Implemented motion registry: `WorkspaceReveal`, `FocusPush`, `MessageIsolation`, `SidebarDrift`, `ThreadDive`, `CardLift`, `DocumentUnfold`, `GallerySweep`, and `InterfacePullback`.
- Deferred registry entries: `ContextSwitch`, `ParallaxWorkspace`, `GlassRefractionPass`, `GeometryMatch`, `ColorBridge`, `OcclusionWipe`, `ArtifactPortal`, and `BreathingHold` remain documented/schema-recognized; their specialized compositing is deferred.
- No music, voiceover, random timing, fake notifications, collaboration, or unsupported document preview.
- Visual limitation: the first renderer uses deterministic whole-frame scale/translation over captures; true layer-aware parallax and artifact occlusion are the smallest useful next iteration.
