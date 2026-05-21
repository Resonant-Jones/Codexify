# Local-First and Ownership Doctrine

## Local-first supported path

- `Current`: The supported path is local Docker Compose with local-only provider posture.
- `Current`: Local-first is the release truth, not a fallback mode.

## Ownership boundary

- `Current`: User work, threads, documents, and continuity surfaces are meant to stay under user-visible control.
- `Philosophy`: Codexify's value proposition is not just model access. It is ownership of the surrounding memory and artifact layer.

## What local-first means here

- The supported runtime runs locally.
- Provider posture is explicitly local-only on the supported path.
- Storage, retrieval, and artifact continuity are described as user-bounded product surfaces.
- Inspectability matters as much as output quality.

## What local-first does not automatically mean

- It does not automatically mean offline under every condition.
- It does not automatically mean no network dependencies exist anywhere in the repo.
- It does not automatically mean every packaging path is equally supported.
- It does not automatically mean every future provider or sync concept is approved for release.

## Cloud-provider caution

- `Current`: Treat cloud-provider support as outside the safe default unless current truth changes.
- `Public rule`: If a public page mentions cloud options at all, it must be clearly labeled and non-default.

## Public claim guidance

- Safe: "Local-first is the supported product posture."
- Safe: "The current supported path is a local runtime."
- Unsafe: "Run anywhere with seamless cloud-provider support."
- Unsafe: "Desktop and Compose are identical supported paths."
