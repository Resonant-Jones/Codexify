# Operator control of models, prices, and inference limits

**Design draft for review · November 10, 2026**

The operator should be able to curate the models in Composer, update cost
assumptions, and set different limits for guests and registered users without
a code release. This proposal leaves all model IDs, rates, budgets, and
public launch decisions open. [PR #1054](https://github.com/Resonant-Jones/Codexify/pull/1054)
tracks the current OpenAI Private Preview rollout separately.

## Current starting point

Guardian's provider registry supplies Composer with model options and checks
requested model IDs. The existing OpenAI catalog combines built-in entries
with one optional configured model. The provider state projection and model
overrides are adjacent seams to review before adding storage. The current
metering design describes provider-reported usage and versioned cost estimates
for observation. Hard spend admission requires a separate enforcement path.
[Provider registry](../../guardian/core/provider_registry.py) ·
[Provider state projection](../../guardian/core/provider_state.py) ·
[Observe-only metering](../architecture/inference-metering-observe-only.md)

## What the operator controls

| Control | Proposed record | How Guardian uses it |
| --- | --- | --- |
| Model registry | Exact provider and API model ID, display name, adapter and endpoint capability, supported inputs and features, context and output bounds, and enabled state | Resolves a model to an executable route. Provider discovery can suggest entries and provide availability evidence. |
| Provider rate schedule | Provider, model, currency, billing units, covered usage classes, effective date, source, and immutable version | Estimates provider cost and determines how much to reserve. Input, cached input, output, and extra chargeable units are explicit where applicable. |
| Audience policy | Deployment and audience, enabled state, permitted models and default, allowed features, per-turn limits, usage windows, and spending ceilings | Determines who can use a model and under what limits. The effective limits are bounded by both the audience policy and the model's verified capabilities. |

The provider's invoice remains the authority for actual provider charges.
Operator rate schedules are versioned estimates. Store the selected version
on each reservation and settlement so updating rates preserves historical
estimates. If Codexify later charges users, give customer prices and free
allowances their own schedule and billing review. A free period can have a
zero customer price while the operator's provider spend remains capped.

Start with a versioned, reviewable configuration file and a validated
operator apply command. An apply should show the diff, check model and rate
references, validate adapter capabilities, and atomically activate one
coherent revision in the deployment's Postgres database. Track the actor
class, authenticated identity where available, time, previous revision, and
reason. An operator service credential identifies a deployment actor. A
change that requires human approval must record a separately verified human
principal. Store provider secrets in the existing credential boundary.
Rollback selects a reviewed prior configuration as a new activation and
preserves reservations, usage, and audit history.
[Credential purpose boundary](../architecture/adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)

Keep the supported profile and egress rules above the configuration. Adding
a registry entry cannot grant network access or advertise a capability the
adapter has yet to prove. Preserve current behavior during migration by
seeding equivalent choices and using shadow evaluation before activation.
When an operator retires a model, existing transcripts keep its recorded
identity. A new send on a thread pinned to a retired model should prompt
the user to select an eligible one.
[Provider capability contract](../architecture/provider-capability-contract.md) ·
[Tester configuration authority](../architecture/adr/074-tester-provider-model-configuration-authority.md)

## Guest and registered user boundaries

| Audience | Identity and authority | Controls to configure |
| --- | --- | --- |
| Unregistered guest, proposed | Short-lived, purpose-scoped guest session issued by Guardian for an enabled deployment and free period. It owns only its temporary conversation scope. | Curated lightweight chat options, input and output bounds, session request limits, and a shared guest spend ceiling. |
| Registered Private Preview user | Existing canonical account session and Preview admission. Account and thread ownership continue to govern access. | Separately curated models, account and deployment ceilings, and feature limits. |
| Registered Production user, future | Canonical account session under a separately activated Production policy. | Production model catalog and entitlements. A Preview grant carries no authority into Production. |

The guest credential needs its own purpose and route scope. It cannot be
exchanged for an account credential or reused as a Hosted Room invitation.
Use an opaque guest session ID and an expiring store for guest conversations.
Keep account history, memory, documents, connectors, and tools outside the
initial guest scope. Signing up starts an account session. Any later
conversion of a guest conversation into account history needs explicit
consent and an ownership contract.

The browser and edge are untrusted for entitlement and spend decisions.
Guardian verifies the session and ownership and derives the audience from
the active deployment policy. Treat guest session minting and inference
requests as abuse surfaces. Edge throttling can reduce load, while the
shared guest ceiling covers repeated session creation and parallel tabs.
When the free period expires, stop admitting guest requests independently of
registered account access. Keep budget metadata to the subject, scope,
request and attempt IDs, rate version, usage, and outcome. Guest retention
and deletion timing require an explicit policy.
[Runtime and account boundary](../architecture/adr/005-runtime-mode-and-account-boundary-invariants.md) ·
[Credential purpose boundary](../architecture/adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)

## How a paid inference request proceeds

1. **Resolve eligibility.** Guardian serves an audience-filtered catalog to
   the browser. On send, it independently resolves the principal and scope,
   validates the requested model and features, and applies the effective
   limits. A direct API caller gets the same decision as Composer. Record
   the request ID and the effective policy, model, and rate versions.
2. **Reserve before acceptance.** Use a single Postgres transaction to check
   and reserve against every applicable budget window and write the durable
   admission record. Reserve a conservative upper bound based on the final
   input ceiling, maximum billable output, and any allowed additional
   charges. Apply every budget check atomically across workers. Deduplicate
   repeated admissions by subject and request ID and reject conflicting
   replays. Commit the admission and its queue handoff intent together.
   Recover an unfinished handoff after a crash and make repeated queue
   delivery harmless by claiming the same durable attempt only once.
3. **Verify before dispatch.** The worker verifies the active reservation,
   subject, attempt identity, approved model, and actual dispatch bounds.
   An operator disable or expired grant blocks queued work that has yet to
   start. If a current rate or the final payload would exceed the authorized
   amount, reauthorize and reserve the difference before dispatch. The first
   enforced slice should use bounded text chat with one provider attempt. Later retries,
   fallbacks, and tool loops need a separately accounted reservation for
   each billable attempt.
4. **Settle by attempt.** Persist normalized provider-reported usage and
   settle each attempt once, releasing any unused reservation. Release the
   full reservation when durable evidence establishes that dispatch never
   happened. If dispatch may have happened and usage is missing, keep the
   reservation pending and flag it for reconciliation. A provider timeout,
   worker crash, or cancellation is insufficient evidence of zero cost.
   Avoid automatic paid retries after an ambiguous upstream outcome.

The node's database is the authority for reservations, settlements, and
active policy. A missing price, unknown billing unit, or unavailable ledger
blocks new spend under an enforced ceiling. Local inference and account
reads continue under their own policies. If several nodes later share one
provider account, a global ceiling needs a shared authority or disjoint
per-node allocations. Independently writable copies of the same global
balance cannot guarantee that ceiling under partition.
[Request and message identity](../architecture/adr/003-message-identity-vs-request-identity.md) ·
[Durable completion attempt authority](../architecture/adr/091-durable-chat-completion-attempt-authority.md)

## Review and delivery sequence

1. **Registry and projection.** Review the existing provider registry,
   provider state, and model overrides. Validate proposed revisions with an
   operator-controlled input and exercise catalog-to-dispatch consistency on
   an isolated stack, including model retirement and rollback.
2. **Observation.** Verify the selected adapters report the usage needed
   for each rate class, including partial and interrupted responses. Compare
   predicted reservations with observed settlements before enforcing a
   monetary ceiling.
3. **Registered account enforcement.** Prove that parallel requests cannot
   overspend the same window. Test rejected direct requests, retries, duplicate
   terminal events, disabled models while queued, and worker or provider
   failure during dispatch. Verify that one account hitting a limit leaves
   other accounts and existing history accessible.
4. **Guest proof and separate rollout decision.** Use an isolated Preview
   environment to prove session expiry, account isolation, temporary data
   deletion, and shared spending limits across newly minted guest sessions.
   Public access requires a separate activation and qualification decision.

Before implementation, review the new operator mutation and guest session
authorities against the existing read-only Configuration Inspector contract
and credential purpose ADR. Record the accepted design in a separate
architecture decision. Release claims continue to follow current-state
evidence.
[Configuration Inspector boundary](../architecture/adr/095-configuration-inspector-operator-control-plane-boundary.md) ·
[Current release state](../architecture/00-current-state.md)

## Decisions to leave open

- Models, adapters, defaults, and feature sets for each deployment and audience.
- Provider rate sources, update cadence, and which usage types qualify for a
  monetary ceiling. Any future customer price schedule.
- Per-turn, per-session, per-account, and shared limits, their windows, and the
  timing and scope of any free period.
- Guest issuance and abuse controls, retention and conversion policy, and who
  may activate, revoke, or reconcile an enforced policy.
