# Review Notes

- Demo account is fictional and isolated to `rowan`.
- Seed content is generic and does not claim long-term-memory retrieval.
- No avatar, portrait, biography, employer, location, relationships, social account, or profile metadata is seeded; the live tester surface does not currently mount the profile route.
- Empty sidebar threads are title-only to create visual density without unnecessary inference cost.
- Three fictional PNG assets are cached under `assets/images/` and reused by the existing Gallery fallback surface.
- Three fictional documents are uploaded through the supported media endpoint and listed by the existing Documents surface.
- The current Documents shell exposes cards but its Inspector still reports the Phase 1 shell placeholder; the video does not claim a working document preview.
- The backend must be live and `verify_demo_workspace.py` must pass before capture.
- Final MP4 is not complete until its dimensions, frame rate, duration, codec, and silent audio state are checked with `ffprobe`.
- Planned or unproven surfaces intentionally excluded: collaboration, connectors, scheduling, public cloud readiness, autonomy, and latency.
