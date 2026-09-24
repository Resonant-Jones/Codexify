# ADR-074 — Tester Provider / Model Configuration Authority

## Status

Accepted doctrine restored into the current architecture line on 2026-08-24.
Amended on 2026-09-15 to remove Codexify-owned physical local-model defaults
and place normal physical-model resolution behind Whoosh'd's `local-chat`
registry route.

The accepted source decision was created on 2026-08-18 as
`ec20badb4b04b1ea2676bf99f6ab7a582ff1cf54` under the historical identifier
ADR-072. That commit is not an ancestor of this line. The current canonical
ADR-072 already governs bounded Settings and Connections route promotion, and
ADR-073 governs the GitHub Watchdog control plane. This ADR assigns the Tester
decision the next free canonical identifier without changing its substance.

The original restoration was an integration identity reconciliation. The
2026-09-15 amendment changes configuration authority; neither entry is current
runtime proof.

## Relationship to ADR-052

ADR-074 partially supersedes ADR-052 only for:

1. local-chat route selection and exact-model override behavior;
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
   lane, egress policy, and local-runtime endpoint family. It declares the
   logical `local-chat` route, never a physical local-model default.

2. Whoosh'd owns the physical model behind `local-chat`. Its authoritative
   registry maps that stable client route to the operator-selected runtime.
   Changing the mapping does not require a Codexify source change.

3. The operator environment (`.env.tester`) may replace `local-chat` with an
   exact `LOCAL_CHAT_MODEL` selection for that Tester instance. It remains
   untracked and machine-local. Exact selection is valid only within the
   supported profile's allowed posture and live advertised inventory.

4. Compose (`docker-compose.whooshd-deepseek.yml`,
   `docker-compose.tester.yml`, and the base Compose file) is configuration
   transport and service assembly. It must forward the operator selection and
   must not carry an independent `LOCAL_CHAT_MODEL` literal that shadows it.
   The canonical chat aliases `LOCAL_CHAT_MODEL`, `LOCAL_LLM_MODEL`,
   `DEFAULT_LOCAL_MODEL`, and `LLM_MODEL` derive from the same
   `${LOCAL_CHAT_MODEL}` input. `LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL`
   are independent domains.

5. Guardian health and catalog surfaces own runtime availability truth. They
   report configured model, discovered inventory, and failure state without
   silently substituting a different model.

6. Live Whoosh'd `/v1/models` proves what routes the runtime can presently
   resolve. Runtime provenance proves which physical model served a request. It
   cannot rewrite Codexify configuration automatically.

### Prohibited behavior

This decision prohibits automatic selection of an arbitrary inventory member,
Whoosh'd-driven Codexify configuration rewrites, physical-model Compose
literals, and treating `.env.tester` as a bypassable convenience override.
Resolution of the explicit `local-chat` route by Whoosh'd is not arbitrary
inventory fallback.

### Precedence and fail-closed behavior

Runtime inventory and Guardian catalog/health are availability truth. Whoosh'd
owns the normal physical selection, an explicit operator exact-model setting
overrides the logical route, the supported profile owns allowed posture, and
Compose is transport only.

When the configured logical route or exact local model is not advertised by
live Whoosh'd inventory,
Guardian must remain fail closed: local availability is disabled with
`configured_model_not_advertised_by_whooshd`, and neither a Qwen-to-Gemma nor
Gemma-to-Qwen substitution is permitted. The supported profile remains valid;
the disagreement is a runtime condition to reconcile deliberately.

### Historical restored default, now superseded

The 2026-08-24 source restoration used `qwen3.8-27b-4bit` as a tracked default.
That fact remains historical configuration evidence, but the 2026-09-15
amendment supersedes it as runtime policy. Codexify now uses `local-chat`; the
physical mapping belongs to Whoosh'd.

## Implementation boundary

The amended implementation:

- replaces the Tester profile's physical default with `local-chat`;
- derives the four chat aliases from the operator selection in the Compose
  overlay;
- makes startup and validation assert the configured route rather than a
  physical-model literal;
- locks the profile and Compose authority contract with focused tests; and
- records the doctrine in operator and architecture documentation.

It does not change provider authorization, DeepSeek, Watchdog, or release
support. Live runtime reconciliation is separate execution evidence.

## Consequences

- A normal Tester physical-model change is a Whoosh'd configuration decision
  and does not require a Codexify source edit.
- An exact-model override remains explicit and fails closed on inventory drift.
- Compose cannot create a second competing chat-model authority.
- Configuration/inventory drift remains visible and fail closed.
- Historical source lineage remains traceable without renumbering the current
  Connections or Watchdog ADRs.

## Non-goals

- no arbitrary inventory-member selection;
- no model installation or model download;
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
