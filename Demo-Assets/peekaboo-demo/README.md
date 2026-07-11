# Peekaboo demo packet

This packet contains the fictional Rowan workspace seed, cached image/document fixtures, browser proof frames, and the rendered silent MP4.

## Repeat the local flow

1. Copy `.env.demo.example` to `.env.demo` and set a local password.
2. Run `make demo-reset-and-seed` against the tester runtime.
3. Run `make demo-verify`.
4. Capture the five 1920×1080 frames into `Demo-Assets/peekaboo-demo/work/` using the tester UI at `http://localhost:5174`.
5. Run `make demo-render`.

The renderer is isolated in `scripts/demo/render_peekaboo.sh`; it does not add dependencies to the production frontend. The ignored `.env.demo` file is the only place for the real demo password.

The current Documents shell shows the seeded cards but its Inspector still reports the Phase 1 placeholder, so the video does not claim a working document preview.
