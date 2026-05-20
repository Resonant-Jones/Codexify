# Codexify.Space Source KB

This folder is a portable knowledge base distilled from the Codexify infrastructure repo. It is meant to be copied into the separate Codexify.Space repo so site agents, writers, and designers can explain Codexify truthfully without importing internal implementation assumptions into the website.

Generated from:
- `Codexify` infrastructure repo
- source path: `docs/architecture/` plus selected release, public-readiness, and identity-policy docs

Intended destination:
- `Codexify.Space` repo

Use this KB when work in Codexify.Space needs to answer four questions:
- What Codexify is
- What is currently true
- What may be said publicly
- What must remain bounded, provisional, or non-promissory

Reading order:
1. `README.md`
2. `00-current-codexify-truth.md`
3. `08-public-claim-discipline.md`
4. `09-codexify-space-content-map.md`
5. the topic-specific files for the task at hand

Doc map:
- `00-current-codexify-truth.md`: short-horizon product truth and current safe public posture
- `01-product-identity-and-public-story.md`: product framing and public language
- `02-runtime-architecture-for-public-explanation.md`: public-safe runtime explanation
- `03-local-first-and-ownership-doctrine.md`: local-first and ownership posture
- `04-memory-identity-and-sovereignty-boundaries.md`: memory and identity boundaries
- `05-retrieval-continuity-and-artifact-lineage.md`: continuity, retrieval, provenance, and artifacts
- `06-runtime-honesty-and-proof-surfaces.md`: inspectability and proof doctrine
- `07-ui-visual-doctrine-transfer.md`: visual doctrine transferable to the website
- `08-public-claim-discipline.md`: mandatory claim classification and safe/unsafe examples
- `09-codexify-space-content-map.md`: recommended public information architecture
- `10-image-and-worldbuilding-implications.md`: environmental/worldbuilding guidance
- `11-agent-operating-protocol.md`: execution protocol for future agents using this export
- `12-roadmap-boundaries-and-non-promises.md`: holdback and non-promise boundaries
- `13-source-map.md`: traceability back to Codexify source docs

Interpretation rule:
- Inside this exported KB, `00-current-codexify-truth.md` wins when a broader architectural description conflicts with current public-safe release truth.

Boundary rule:
- This KB explains Codexify the product and infrastructure so Codexify.Space can describe it accurately.
- This KB does not define Codexify.Space's own implementation architecture.
- Do not assume the website uses the same backend, worker, queue, or storage topology unless the Space repo explicitly implements it.

Agent usage rule:
- Start from current truth, then classify every capability statement before turning it into copy, layout, imagery, or implementation.
- Prefer distillation over quotation.
- When in doubt, keep claims narrower and cite `13-source-map.md`.
