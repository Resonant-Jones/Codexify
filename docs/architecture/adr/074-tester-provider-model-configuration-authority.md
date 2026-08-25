# ADR-074 — Tester Provider / Model Configuration Authority

## Status

Accepted doctrine restored into the current architecture line on 2026-08-24.

The accepted source decision was created on 2026-08-18 as
`ec20badb4b04b1ea2676bf99f6ab7a582ff1cf54` under the historical identifier
ADR-072. That commit is not an ancestor of this line. The current canonical
ADR-072 already governs bounded Settings and Connections route promotion, and
ADR-073 governs the GitHub Watchdog control plane. This ADR assigns the Tester
decision the next free canonical identifier without changing its substance.

This is an integration identity reconciliation, not a new model-selection
decision and not current runtime proof.

## Relationship to ADR-052

ADR-074 partially supersedes ADR-052 only for:

1. exact local-chat-model pinning;
2. Tester provider/model configuration authority;
3. precedence between supported profile, operator environment, and Compose;
4. fail-closed behavior when configured model and live Whoosh'd inventory
   disagree.

All other ADR-052 decisions remain authoritative:

- global/default provider remains `local` / Whoosh'd;
- the approved cloud lane remains DeepSeek;
- `deepseek-v4-flash` remains unchanged;
- cloud selection remains bounded and per-thread;
- DeepSeek egress remains explicitly allowlisted as `deepseek`;
- bounded concurrent-startup proof remains an operator-controlled mechanism;
- Beta/release posture is unchanged.

## Context

ADR-052 recorded the Tester dual-provider topology while its tracked
configuration used a Gemma local-model literal. Historical source lineage then
reconciled the concrete local selection to Qwen and found that the Compose
overlay's independent literals could shadow the operator environment. The
source implementation removed that parallel model authority rather than merely
replacing one model name with another.

The current architecture line independently allocated ADR-072 to Connections
and ADR-073 to Watchdog. It retained the older Tester literals but not the
accepted configuration-authority doctrine. Reusing either occupied identifier
would give one canonical ADR number two meanings; dropping the historical
doctrine would retain a known configuration-drift seam.

## Decision

### Authority doctrine

1. The supported profile
   (`config/supported_profiles/v1-whooshd-deepseek-web.yaml`) owns the allowed
   and default Tester provider posture: local Whoosh'd, the bounded DeepSeek
   lane, egress policy, and local-runtime endpoint family. It may declare a
   default local model for clarity, but that declaration is not the concrete
   selection when an allowed operator environment supplies a different value.

2. The operator environment (`.env.tester`) owns the concrete local
   `LOCAL_CHAT_MODEL` selection for that Tester instance. It remains
   untracked and machine-local. Operator selection is valid only within the
   supported profile's allowed posture.

3. Compose (`docker-compose.whooshd-deepseek.yml`,
   `docker-compose.tester.yml`, and the base Compose file) is configuration
   transport and service assembly. It must forward the operator selection and
   must not carry an independent `LOCAL_CHAT_MODEL` literal that shadows it.
   The canonical chat aliases `LOCAL_CHAT_MODEL`, `LOCAL_LLM_MODEL`,
   `DEFAULT_LOCAL_MODEL`, and `LLM_MODEL` derive from the same
   `${LOCAL_CHAT_MODEL}` input. `LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL`
   are independent domains.

4. Guardian health and catalog surfaces own runtime availability truth. They
   report configured model, discovered inventory, and failure state without
   silently substituting a different model.

5. Live Whoosh'd `/v1/models` proves what the runtime can presently serve. It
   cannot rewrite Codexify configuration automatically.

### Prohibited behavior

This decision prohibits automatic selection of whichever model Whoosh'd happens
to advertise, Whoosh'd-driven configuration rewrites, replacing the operator
selection with Compose literals, and treating `.env.tester` as a bypassable
convenience override.

### Precedence and fail-closed behavior

Runtime inventory and Guardian catalog/health are availability truth. The
operator environment is the concrete selection authority, followed by the
supported profile's allowed posture; Compose is transport only.

When the configured local model is not advertised by live Whoosh'd inventory,
Guardian must remain fail closed: local availability is disabled with
`configured_model_not_advertised_by_whooshd`, and neither a Qwen-to-Gemma nor
Gemma-to-Qwen substitution is permitted. The supported profile remains valid;
the disagreement is a runtime condition to reconcile deliberately.

### Restored tracked default

The source implementation's tracked default is
`qwen3.8-27b-4bit`. It is restored here as historical configuration evidence
so that the authority mechanism is complete. This ADR does not assert that the
model is currently advertised, loaded, or selected by a running Tester. A
separate live reconciliation must compare it with current inventory and choose
any operator change explicitly.

## Implementation boundary

This restoration:

- updates the Tester profile's historical default;
- derives the four chat aliases from the operator selection in the Compose
  overlay;
- makes the startup script's historical Qwen expectation an overrideable
  assertion input rather than a Compose authority;
- locks the profile and Compose authority contract with focused tests; and
- records the doctrine in operator and architecture documentation.

It does not edit `.env.tester`, reconfigure or restart Whoosh'd, start or
recreate any service, invoke a provider, change routing, alter DeepSeek,
modify Watchdog, or widen release support.

## Consequences

- A Tester model change requires an explicit operator configuration decision
  and a live inventory reconciliation; it is never inferred from incidental
  serving state.
- Compose cannot create a second competing chat-model authority.
- Configuration/inventory drift remains visible and fail closed.
- Historical source lineage remains traceable without renumbering the current
  Connections or Watchdog ADRs.

## Non-goals

- no automatic model discovery or selection;
- no Whoosh'd mutation, restart, model installation, or model download;
- no cloud, DeepSeek, egress, provider-routing, queue, or worker change;
- no Watchdog policy, attempt, dispatch, execution, publication, or GitHub I/O;
- no change to Beta support or `00-current-state.md`.

## Evidence anchors

- Historical accepted source: `ec20badb4b04b1ea2676bf99f6ab7a582ff1cf54`
  (`Canonize tester model configuration authority`), parent
  `e146d9b5aa58e54d91fa2443db0278e1807a8041`.
- Historical runtime proof, not current-branch runtime proof:
  `docs/architecture/proofs/providers/2026-08-18-tester-whooshd-model-authority-proof.md`
  at the historical source commit.
- Current restoration record:
  `docs/architecture/proofs/providers/2026-08-24-tester-provider-model-authority-restoration.md`.
