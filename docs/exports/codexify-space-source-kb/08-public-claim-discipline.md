# 08 Public Claim Discipline

## Canonical labels

- `Current`: supported or otherwise safely claimable now
- `In development`: actively being built or hardened, not yet a shipped promise
- `Exploration`: a plausible direction or contract-bearing concept, not a product promise
- `Roadmap`: intentional future direction, still non-shipped
- `Philosophy`: worldview, design doctrine, or framing principle

## General rules

- Every public-facing capability statement should carry one of the labels above in working drafts.
- Only `Current` statements should be eligible for direct capability claims on high-visibility surfaces.
- `In development`, `Exploration`, and `Roadmap` may appear only when clearly labeled.
- `Philosophy` must never be mistaken for shipped functionality.

## Capability claim rules

- Do not claim a feature as `Current` just because code, routes, flags, ADRs, or schemas exist.
- Prefer proof-backed statements anchored in `00-current-codexify-truth.md`.
- If support is limited to the local Compose path, say so.

## Beta and download claim rules

- Do not imply general availability when the product is in beta hardening.
- Do not imply desktop packaging replaces the supported local Compose path unless current truth changes.
- Do not imply cloud-hosted onboarding or multi-environment support by default.

## Local-first claim rules

- Safe: "Current supported beta posture is local-first."
- Unsafe: "Codexify already supports every local and cloud deployment mode equally."

## AI and agent claim rules

- Safe: "Codexify coordinates chat, retrieval, and worker-backed execution on the supported path."
- Unsafe: "Codexify already ships autonomous delegation, federation, or open-ended agent orchestration as a public promise."

## Image and worldbuilding claim rules

- Images may communicate locality, continuity, provenance, and inspectability.
- Images must not imply shipped worlds, interfaces, or autonomous capabilities that do not exist.

## Safe and unsafe examples

- Safe `Current`: "Codexify's current supported path is a local Docker Compose stack."
- Safe `Philosophy`: "Codexify is designed as a continuity substrate for ongoing work."
- Unsafe: "Codexify beta already runs as a cloud-native distributed agent network."
- Unsafe: "Codexify.Space reflects the same runtime stack as the product itself."
