# Agent Instructions for Codexify.Space Source KB

Read `README.md` and `00-current-codexify-truth.md` first.

Core rules:
- Do not turn infrastructure internals into public promises.
- Do not claim roadmap or exploratory work as shipped.
- Do not update public copy without checking `08-public-claim-discipline.md`.
- Do not update visual or worldbuilding direction without checking `07-ui-visual-doctrine-transfer.md` and `10-image-and-worldbuilding-implications.md`.
- Do not treat Codexify backend architecture as Codexify.Space implementation architecture unless the Space repo explicitly implements it.
- Keep work atomic, source-backed, and validation-backed.

Working posture:
- Prefer the narrowest truthful claim.
- Separate `Current`, `In development`, `Exploration`, `Roadmap`, and `Philosophy`.
- Use `13-source-map.md` before relying on a capability statement.
- If a statement depends on live proof, say so.
- If a statement is only architecture context, do not market it as release truth.

Boundaries:
- No private credentials, local machine paths, unreleased secrets, or internal-only operational detail.
- No mythology presented as factual capability.
- No “black box magic” phrasing where inspectable system behavior is the stronger framing.

Execution rule:
- Make one coherent change at a time.
- Validate the exact surface changed.
- If a claim cannot be sourced cleanly from this KB, narrow it or leave it out.
