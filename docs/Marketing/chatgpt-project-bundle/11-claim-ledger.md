# Claim Ledger

Use this ledger as a pre-publish claim gate.
Status values:
- `safe`
- `caution`
- `future`
- `reject`

| Claim | Status | Evidence needed | Source docs to check | Notes |
|---|---|---|---|---|
| Codexify is local-first by default on the supported path. | safe | Current-state + supported profile alignment | `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Core safe posture |
| Codexify supports project/thread continuity for chat workflows. | safe | Current runtime docs + route behavior | `docs/architecture/00-current-state.md`, `docs/architecture/system-overview.md` | Phrase as continuity, not omniscience |
| Document upload is part of supported product behavior. | safe | Supported-path proof references | `docs/architecture/00-current-state.md`, `docs/architecture/flows.md` | Keep wording specific |
| Embedding and retrieval are available on supported paths. | safe | Supported-path proof + flow docs | `docs/architecture/00-current-state.md`, `docs/architecture/flows.md` | Avoid universal guarantee language |
| Runtime truth surfaces are inspectable. | safe | Health/catalog/events surfaces documented | `docs/architecture/config-and-ops.md`, `docs/architecture/system-overview.md` | Good operator-facing claim |
| Command Center exists as a release-proven non-dispatch worker-control seam. | caution | Current-state wording and latest proof notes | `docs/architecture/00-current-state.md` | Do not claim autonomous dispatch |
| Codexify provides autonomous agents that run unsupervised end to end. | reject | N/A | `docs/architecture/00-current-state.md` | Conflicts with current claim boundaries |
| Broad cloud support is part of the default supported posture. | reject | N/A | `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Current posture is local-first |
| Graph context is core supported behavior on default path. | caution | Flag and path proof for current release | `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Default-off caveat matters |
| Export/restore is contract-defined with provenance requirements. | caution | Contract maturity and implementation evidence | `docs/architecture/account-export-restore-contract.md` | Contract exists; market carefully |
| Identity boundaries are explicit and enforceable by design doctrine. | caution | Route/contract evidence in current branch | `docs/architecture/system-overview.md`, `docs/architecture/config-and-ops.md` | Avoid compliance overreach |
| Codexify includes production-ready marketing automation out of the box. | reject | N/A | `docs/architecture/00-current-state.md` | Unsupported release claim |
| Codexify delivers full workflow orchestration with no human supervision. | reject | N/A | `docs/architecture/00-current-state.md`, `docs/Marketing/brand/constitution.md` | Conflicts with supervision posture |
| Codexify helps teams build institutional memory. | safe | Continuity + capture + retrieval evidence | `docs/architecture/00-current-state.md`, `docs/architecture/system-overview.md` | Keep as directional value claim |
| Local model support is part of the supported profile. | safe | Supported profile + config docs | `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Strong safe claim |
| Provider routing exists with explicit governance categories. | caution | Provider registry + ops docs | `docs/architecture/system-overview.md`, `docs/architecture/config-and-ops.md` | Avoid implying equal maturity across providers |
| Event streams provide lifecycle visibility. | caution | Task/event route docs + caveats | `docs/architecture/flows.md`, `docs/architecture/config-and-ops.md` | Visibility != guaranteed delivery |
| Command bus is part of public core release messaging. | caution | Supported profile and current-state boundary | `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Treat as bounded/internal where applicable |
| Federation is currently a core release promise. | future | Fresh live proof + release posture inclusion | `docs/architecture/00-current-state.md`, `docs/architecture/system-overview.md` | Keep roadmap framing only |
| Connector ecosystem is mature and broad today. | future | Connector support matrix + live proof | `docs/architecture/00-current-state.md` | Avoid current-tense maturity claims |
| Hosted deployment is a standard supported product lane. | future | Explicit current-state support claim | `docs/architecture/00-current-state.md` | Do not imply today |
| Codexify webUI bundle exists for runtime surface access. | caution | Current runtime topology and packaging docs | `docs/architecture/system-overview.md`, `docs/architecture/config-and-ops.md` | Phrase as runtime surface, not hosted SaaS |
| Desktop shell is the same supported release path as local Compose. | reject | N/A | `docs/architecture/00-current-state.md` | Current-state distinguishes paths |
| Proof artifacts are part of release truth governance. | safe | Current-state and proof docs | `docs/architecture/00-current-state.md`, `docs/architecture/README.md` | Strong differentiator |
| Claim discipline is a first-class marketing rule. | safe | Marketing contracts + architecture truth model | `docs/Marketing/contracts/claim-truth-model.md`, `docs/Marketing/README.md` | Core doctrine |
| Codexify replaces all existing knowledge tools automatically. | reject | N/A | `docs/Marketing/brand/constitution.md` | Hype/overclaim |
| Codexify guarantees zero context loss forever. | reject | N/A | `docs/Marketing/brand/constitution.md` | Absolute guarantee not allowed |
| Codexify offers inspectable provenance for workflow knowledge artifacts. | caution | Provenance surfaces and proof references | `docs/architecture/account-export-restore-contract.md`, `docs/architecture/00-current-state.md` | Keep scope explicit |
| Codexify can be marketed as an operator-first AI workspace. | safe | Positioning + architecture truth alignment | `docs/Marketing/messaging/pillars.md`, `docs/architecture/00-current-state.md` | Good core narrative |
| Codexify currently supports broad enterprise compliance guarantees. | reject | N/A | `docs/architecture/00-current-state.md`, `docs/Marketing/brand/constitution.md` | Unsupported and risky |
