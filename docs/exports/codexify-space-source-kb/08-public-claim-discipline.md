# Public Claim Discipline

## Required labels

- `Current`: supported and safe to describe as present reality
- `In development`: active work with meaningful implementation motion, but not safe to present as shipped
- `Exploration`: researched, drafted, or partially scaffolded, but not product promise
- `Roadmap`: directional future intent
- `Philosophy`: values, doctrine, and framing that guide the product without claiming a shipped feature

## General rules

- Every public-facing capability statement should carry one of the labels above.
- Choose the narrowest truthful label.
- `Current` must align with current-state docs and supported-path proof posture.
- Do not turn architecture presence into claim permission.

## Rules for capability claims

- Route presence is not enough.
- Catalog presence is not enough.
- Spec or ADR presence is not enough.
- A current claim should describe supported behavior, not just code existence.

## Rules for beta and download claims

- Beta claims must stay narrow and evidence-backed.
- Do not imply public launch readiness without dated evidence.
- Do not imply desktop packaging replaces the supported Compose path.

## Rules for local-first claims

- Local-first can be claimed as current posture.
- Do not silently widen that into cloud parity or universal offline guarantees.

## Rules for AI and agent claims

- Do not claim fully autonomous agents.
- Do not claim unsupervised delegation as a public promise.
- Do not claim command-bus, federation, or graph concepts as shipped product highlights unless current truth changes.

## Rules for image and worldbuilding claims

- Images may dramatize doctrine.
- Images must not imply unproven runtime behavior.
- Environmental storytelling must stay behind current product truth, not outrun it.

## Safe and unsafe examples

| Claim | Label | Safe? | Why |
|---|---|---:|---|
| "Codexify is currently being hardened around a supported local Docker Compose runtime." | `Current` | yes | Matches current-state truth. |
| "Codexify supports cloud-provider beta workflows." | `Current` | no | Current docs say not to assume that. |
| "Codexify is designed around user-owned continuity and inspectable runtime truth." | `Philosophy` | yes | Doctrine-backed and not overstated. |
| "Codexify has optional graph concepts in the repo, but graph writes remain default-off on the supported path." | `Exploration` | yes | Truthful and bounded. |
| "Codexify.Space runs the same architecture as Codexify." | `Current` | no | Cross-repo implementation claim without proof. |
