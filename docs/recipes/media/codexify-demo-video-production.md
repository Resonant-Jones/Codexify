# Codexify demo video production

This recipe produces two separate artifacts:

1. The factual Peekaboo proof master, rendered from real captures with the existing FFmpeg walkthrough.
2. The cinematic interpretation, rendered from the same captures through a deterministic shot manifest.

The proof master remains the authority for product behavior. The cinematic render may change framing, scale, depth, masks, lighting, transitions, and timing, but it must not invent collaboration, autonomy, document preview, or any other unsupported capability.

## Preflight and capture

Use the dedicated `codexify_tester` Compose project and `.env.tester`. Verify the intended tester frontend (`http://localhost:5174`) and backend (`http://localhost:8889`) before restarting anything. Keep credentials in the ignored `.env.demo`; never commit that file.

Run the scoped lane:

```bash
make demo-reset
make demo-seed
make demo-style
make demo-verify
make demo-capture
```

The reset/seed flow is scoped to Rowan. It must not wipe unrelated users or Compose volumes. Cached image and document fixtures are generated once and reused. Capture at 1920×1080, 30 fps, and explicitly restore that viewport after every browser reconnect. The style step authenticates Rowan, applies the real Settings controls, reloads, verifies persistence, and saves `captures/appearance-proof.png`.

The first Peekaboo build exposed these operational quirks:

- Multiple empty threads may reuse the latest empty thread; minimal support messages may be needed for title-only rows.
- The dedicated `codexify_tester` Compose project and `.env.tester` are required.
- Verify the correct tester backend/frontend before restarting services.
- Restore the capture viewport to 1920×1080 after browser reconnects.
- Generate cached image and document fixtures once and reuse them.
- Unsupported document preview remains explicitly unclaimed.
- Preserve unrelated working-tree changes.
- `.env.demo` stays ignored and uncommitted.

## Appearance and evidence

Use `Demo-Assets/peekaboo-demo/appearance-preset.json`. The current Rowan preset is dark, base color `#8174E8`, depth `0.68`, fade `0.32`, wallpaper blur `10px`, and `assets/wallpaper/rowan-night-field.png`. The controls are browser-local, including `cfy.wallpaper`; this is a capture setting, not account-scoped product state.

Every capture should have a receipt that records the exact commit, manifest, preset, viewport, runtime URLs, source paths, and whether the claim is seed/test/capture verified. Do not use a screenshot as proof of a capability it does not show.

## Cinematic render

Validate the declarative manifest, then render:

```bash
make demo-render-cinematic
```

The implementation in `scripts/demo/render_cinematic.py` uses FFmpeg `zoompan` over still captures. Every motion value comes from `cinematic-manifest.json` and is bounded by `references/shot-manifest.schema.json`; identical inputs produce identical output. The supported implementation subset is `WorkspaceReveal`, `FocusPush`, `MessageIsolation`, `SidebarDrift`, `ThreadDive`, `CardLift`, `DocumentUnfold`, `GallerySweep`, and `InterfacePullback`. The remaining grammar types are documented and recognized by the schema, but are deferred renderer implementations.

## Verification, rollback, cleanup

Run the full repeatable lane when the tester runtime is available:

```bash
make demo-cinematic-all
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration \
  -of default=noprint_wrappers=1 Demo-Assets/peekaboo-demo/renders/codexify-peekaboo-cinematic-16x9.mp4
```

The expected output is approximately 35 seconds, 1920×1080, 30 fps, H.264, silent. The factual master at `renders/codexify-peekaboo-16x9.mp4` must remain intact. If a run is interrupted, remove only generated cinematic output and temporary captures for Rowan; never remove unrelated users, volumes, or working-tree files. Re-run reset/seed/style/verify/capture rather than manually repairing a timeline.

## Claim and privacy gate

Use fictional Rowan data and cached fixtures only. The output may show persisted threads, messages, sidebar navigation, and cached fictional image/document surfaces when the matching captures are verified. Unsupported document preview, collaboration, autonomous agents, cloud readiness, and other unproven behavior must remain unclaimed. No real personal data or secrets belong in the packet.
