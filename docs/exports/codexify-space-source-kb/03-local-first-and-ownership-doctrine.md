# 03 Local First and Ownership Doctrine

## Supported path

`Current`: The supported path today is local Docker Compose with a local-only provider posture.

## Ownership boundary

`Current`:
- User projects, threads, documents, and identity-sensitive materials are meant to stay under user-controlled runtime boundaries.
- Local-first is the primary trust posture, not a marketing accent.

## What local-first means here

`Current`:
- The supported runtime starts from the user's own machine and local stack.
- Provider posture is intentionally local-only on the supported profile.
- System truth is inspectable through health and runtime surfaces.

## What local-first does not automatically mean

`Current`:
- It does not mean zero operational complexity.
- It does not mean no queues, no workers, or no background services.
- It does not mean every possible deployment mode is equally supported.
- It does not mean packaged desktop has replaced the supported Compose path.

## Cloud-provider caution

`Current`:
- Architecture and config surfaces may reference cloud-capable lanes.
- Public claims must not convert that into "cloud beta support" unless current truth explicitly changes.

## Public claim guidance

Safe:
- "Codexify's current supported beta path is local-first and user-run."
- "The product is designed around user-owned runtime boundaries."

Unsafe:
- "Codexify is already a hosted cloud service."
- "Any runtime mode shown in docs is equally supported today."
