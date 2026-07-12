# Camera grammar

The cinematic lane is an interpretation of captured Codexify surfaces. It never creates a new UI state. A shot is a named registry entry with a source capture, frame duration, bounded camera values, and a named transition.

| Shot | Purpose | Required input | Safe behavior |
| --- | --- | --- | --- |
| `WorkspaceReveal` | Establish the complete workspace | full workspace capture | scale 0.95–1.10, no rotation |
| `InterfacePullback` | Reconnect a detail to the whole | detail or workspace capture | scale down to 0.85 minimum |
| `FocusPush` | Direct attention into a real message or title | focus region | scale up to 1.35, translation ±240/±180 |
| `MessageIsolation` | Hold one message with context retained | message region | restrained scale and dim only |
| `SidebarDrift` | Make sidebar history a designed movement | populated sidebar capture | horizontal drift only |
| `ThreadDive` | Bridge sidebar title to conversation | sidebar + conversation capture | bounded push toward content |
| `ContextSwitch` | Move between real conversations | two captured states | geometry or color anchor |
| `CardLift` | Give a real card restrained 2.5D emphasis | image/document capture | scale and shadow, no detached UI |
| `DocumentUnfold` | Expand supported document content | supported document capture | never implies unsupported preview |
| `GallerySweep` | Traverse real gallery images | gallery capture | slow lateral drift |
| `ArtifactPortal` | Use an artifact edge as a transition surface | image/document capture | occlusion only |
| `ParallaxWorkspace` | Separate captured depth layers | layered capture | optional, low amplitude |
| `GlassRefractionPass` | Material punctuation | captured glass surface | sparse; no lens flare |

`GeometryMatch`, `ColorBridge`, `OcclusionWipe`, `BreathingHold`, and `ArtifactPortal` are transitions. The renderer uses deterministic defaults; the manifest can only override values within the schema bounds. Random timing, rotation, particles, holograms, fake notifications, and detached floating UI are not part of the grammar.
