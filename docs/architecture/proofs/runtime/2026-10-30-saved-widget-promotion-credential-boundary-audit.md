# Saved Widget Promotion Credential Boundary Audit — 2026-10-30

**Result: the observed local API-key acceptance CONFORMS to the accepted local-user authority rule, with one documentation defect in a read-only file and one implicit contract reading the owner should make explicit. No runtime change is required, and none is authorized by this audit.**

- **Evaluated commit:** `a2547c5555391a28316f3d95cc79375cfe58a92e`
- **Branch:** `feat/saved-widget-promotion-20261029`
- **Base for comparison:** `origin/main` at `ba8be8dbccbebf6b973cf3d787066d427eda5c23`
- **Audit date:** 2026-10-30
- **Release posture:** HOLD — unchanged by this audit

> **Merge status at audit completion.** PR #962 was merged into `main` at **2026-10-30T19:15:33Z**, partway through this audit and by an action outside it. `main` is now `4cca5129f1ed4389359eb39e8d72959bf0f450b3`, whose only commit beyond the evaluated SHA is the merge commit itself. Every file this audit inspected was verified **byte-identical** between the evaluated SHA and current `main`, so every finding below transfers verbatim to what is now shipped. The recommended correction therefore targets `main` directly rather than the pull request, which is no longer open.

## The question

The promotion route declares `require_account_session` as its authentication dependency. `guardian/core/dependencies.py` implements `verify_account_session` with a local-mode fallback to `verify_api_key`, and the default supported profile enables the `saved_widgets` route. Does a local static API key therefore satisfy the promotion route's authentication dependency, and does that contradict the accepted explicit-human-promotion authority?

**The discrepancy is confirmed by measurement.** In local mode a static `GUARDIAN_API_KEY` *is* accepted by the promotion route's authentication dependency.

## Method and evidence classes

Every observation below is tagged:

- **[source]** — read from inspected source at the evaluated commit.
- **[test]** — produced by an executed existing test.
- **[probe]** — produced by an executed synthetic check against the *real* Guardian authentication functions, with no dependency overrides and no rejecting stubs.
- **[executor]** — previously reported by the implementing executor.

The probe exercised `verify_account_session` and `get_request_user_id` directly with real Starlette `Request` objects, real signed session tokens, real guest session tokens, and real environment configuration for each runtime mode. Only the session store's *storage backend* was the repository's own in-memory pytest fallback; no authentication behaviour was substituted.

## Layer 1 — credential authentication (measured matrix)

`verify_account_session` (`guardian/core/dependencies.py:1100`) branches before anything else:

```python
private_preview = is_private_preview()
remote_boundary = private_preview or _auth_mode() == "remote"
if not remote_boundary:
    return verify_api_key(request, x_api_key, authorization, gc_session)   # :1110
```

Outside the remote and private-preview boundary the route therefore authenticates by the **local static-key lane**, and `verify_api_key`'s local branch accepts `X-API-Key` or `Bearer` against the configured `GUARDIAN_API_KEY` / `GUARDIAN_API_KEYS` (`dependencies.py:169-170`, `:693-732`, `:778`). Inside that boundary a static key is refused and an account session is required.

| Runtime mode | No credential | Static API key (`X-API-Key` or `Bearer`) | Account session | Guest credential | Mixed account + operator session |
| --- | --- | --- | --- | --- | --- |
| **Local** (`GUARDIAN_AUTH_MODE=local`) | 401 `Missing API key` | **ACCEPTED** | ACCEPTED | 401 `Invalid API key` | 401 `Invalid API key` (not a mixed-principal rejection) |
| **Remote** (`GUARDIAN_AUTH_MODE=remote`) | 401 `Account session required` | **401 `Account session required`** | ACCEPTED | 401 `Account session required` | **400 `mixed_principal_credentials`** |
| **Private Preview** (`GUARDIAN_EXPOSURE_MODE=private_preview`) | 401 `Account session required` | **401 `Account session required`** | ACCEPTED | 401 `Account session required` | **400 `mixed_principal_credentials`** |

[probe] All eighteen cells above were executed. Supporting [source]: `is_private_preview` (`guardian/core/preview_access.py:27`), the remote static-key refusal (`dependencies.py:818-824`, `:852`), and the mixed-principal rule (`guardian/core/auth.py:90`, enabled only on the remote/preview branch).

Two consequences deserve to be stated plainly:

1. **The mixed-credential guard is local-mode-inert.** In local mode the mixed case is not rejected as `mixed_principal_credentials`; it falls through to the static-key lane and fails as an invalid API key. The guard is a remote/preview boundary control, not a local one. [probe]
2. **Guest credentials are refused in every mode.** A guest Hosted-Room token is not an account-session purpose, so it never satisfies the route. [probe]

## Layer 2 — account identity resolution

Authentication and identity are separate steps, and the distinction matters here. `get_request_user_id` (`dependencies.py:452`) resolves the account:

| Credential accepted in | Resolved account identity | Mechanism |
| --- | --- | --- |
| Local static API key | `local` — the deployment's configured single user | `get_single_user_id()` (`dependencies.py:262`), via the `dependencies.py:513` fall-through |
| Local account session | the session's own account id | session subject |
| Remote account session | the session's own account id | `_verified_account_identity` |
| Private Preview account session | the approved preview email bound to the signed session | `require_preview_principal` (`preview_access.py:67`) |

[probe] The decisive observation: **the local static API key resolves to the same principal as the local user, not to a distinct one.** The key is the local operator's own credential. It does not create a second identity, and it does not widen the account set.

`get_account_user_id` (`dependencies.py:1272`) adds only the remote/preview account-scope gate on top of this; it does not change which credential is acceptable. An `X-User-Id` header is honoured only under explicit `DEBUG`/`LOCAL_DEV` flags (`dependencies.py:258`, `:507-511`) and is ignored otherwise. [source]

## Layer 3 — authorization to access the source artifact

Independent of the credential, the route calls the existing store, which resolves the source artifact through server-owned E5 provenance and applies the existing eligibility policy. A cross-account source produces one uniform reason (`source_not_authorized`) so a caller cannot distinguish another account's artifact from a missing one; ownership is resolved from the authenticated transport and is never client-supplied. [source]

The existing suite covers this: 30 revision-store tests, 16 E5-provenance tests, 6 consent-merge tests and 75 eligibility tests all pass against a disposable PostgreSQL 16.15 instance. [test]

## Layer 4 — explicit promotion intent

The request model forbids unknown fields, so there is no client-supplied artifact, provenance, approval flag, or account assertion. The *act* is the authenticated request itself. The route records `actor="user"` (`guardian/routes/saved_widgets.py:87`, `:314`) into the revision's creation context, so the persisted record states that the promotion was user-originated.

## Model-facing authority

Assessed separately, because the contract's "the model cannot cause a promotion to occur" clause is about *model* authority, not about which credential a human holds.

| Path | Result | Evidence |
| --- | --- | --- |
| Ordinary-chat tool rail | The model tool set is a **fixed allowlist** — the health command, and conditionally the repository-search command. A promotion command can never enter it. | [source] `guardian/tools/chat_exposure.py:182-233`; [test] `tests/core/test_chat_tool_exposure.py` passes |
| Generic HTTP / shell from the model surface | No generic HTTP client exists in the model-facing tool surface; no `requests`/`httpx`/`urlopen` use under `guardian/tools/` or `guardian/agent_tools/` | [source] |
| Command bus | `approval_mode = "none" if effect == "read" else "blocked_phase1"` (`manifest.py:137`), so the promotion POST is `blocked_phase1`; `requires_confirmation = approval_mode != "none"` (`invoke.py:711`); the loopback adapter raises `policy_blocked` without a granted confirmation (`loopback_http_adapter.py:105-130`) | [source]; [test] 130 command-bus tests pass |
| Codex runner bridge | Exactly five bounded internal operations, none an arbitrary HTTP proxy or shell executor | [source] `guardian/codex_runner_bridge/contracts.py:41-47` |
| Default profile route posture | `command_bus` is `internal_only`; `tools` and `api_tools` are `quarantined` | [source] ADR-069 §"Supported Runtime Profile Relationship" |

**Conclusion: no model-facing surface can present the local static key or invoke the promotion route unattended.** The static key is ambient in the deployment's `.env` — its presence is confirmed, its value was never read or printed — and is readable by any process with host filesystem access. ADR-069 explicitly declines to promote "generic shell / filesystem execution" in Beta, so those surfaces are outside the supported envelope rather than inside the promotion authority chain.

## Route-posture assessment

`saved_widgets` is **enabled** in the default supported profile `v1-local-core-web-mcp` (`config/supported_profiles/v1-local-core-web-mcp.yaml:37`), and in all five profiles. ADR-069 §"Supported Runtime Profile Relationship" identifies that profile as the one that defines the supported Beta, with `CODEXIFY_LOCAL_ONLY_MODE=true`.

Route availability is **not** release qualification, and this audit does not treat it as such. The Saved Widget lifecycle remains HOLD: listing, cross-thread invocation, conversational editing, deletion, export/restore, Library integration, and browser qualification are unimplemented or unproven. What enabled posture changes is precisely the exposure question audited here: in the default local profile the route is reachable, and in that profile the local static key is an acceptable credential.

Note also that the profile's `LOCAL_API_KEY: local` is the **LLM provider** key for Whoosh'd local inference, not Guardian's own `GUARDIAN_API_KEY`. [source] The default profile does not configure a Guardian static key; a local deployment that follows `.env.example` (`GUARDIAN_API_KEY=dev-local-only-change-me`) does.

## Classification

**Conforms to an explicitly accepted local-user authority rule — with two qualifications, neither of which is a runtime defect.**

1. *The static key is the local user.* It resolves to `local`, the deployment's single configured account. It is the local operator's own credential, not a second principal, and it does not satisfy any promotion condition that an account session satisfies in a different way: the account that owns the source thread, the server-resolved Widget Candidate, the explicit save action, and the server-persisted snapshot all behave identically.
2. *The contract is silent on this case, and the silence is load-bearing.* The contract's condition 3 reads "The user performs an explicit save action on that specific artifact." It does not say "through an account session." In the local single-user runtime the local operator presenting their own credential *is* the user performing the explicit action. That reading is consistent with ADR-069's supported local single-user path, but the contract never states it, so the conformance conclusion rests on an implicit reading rather than an explicit accepted rule. **This is the interpretive gap the owner should close.**

It is **not** a contradiction of an accepted Saved Widget invariant: no contract clause requires a *session*, the model-authority clause holds (§Model-facing authority), and the remote and private-preview lanes — the multi-user boundaries — correctly refuse the static key outright.

**It is not an unresolved architectural interpretation** of the kind that would block work, because no contract clause is contradicted and no authority concept needs to be invented. It is a documentation-precision gap plus a contract-clarity gap.

## The one defect found (read-only file; reported, not fixed)

`guardian/routes/saved_widgets.py:19-26` — the route's own module docstring — states:

> This route is reachable only by an authenticated **account session**, which is the credential a signed-in person holds. Guardian's *service* credentials are deliberately not accepted in its place…

The first clause is **false in local mode**: a configured static `GUARDIAN_API_KEY` satisfies the route's authentication dependency, as measured above. The second clause is true but easy to over-read: Guardian's *service* credential (`require_service_api_key`, "without accepting session auth") is a genuinely separate lane and is not accepted here, but the prose reads as though no static credential can satisfy the route.

Severity: **moderate for review integrity, nil for runtime behaviour.** The prose would mislead a later reviewer into believing local API-key promotion is impossible, which is precisely the question this audit exists to answer. The same overstatement appears in the PR #962 description.

This file is read-only for this task, so the wording was **not** changed. Because PR #962 merged before this audit completed, the overstated prose is now **shipped on `main`**, which raises the correction from cosmetic to something the next change should carry.

## The one interpretive gap (owner decision)

The contract's "Promotion is explicit" clause (`docs/architecture/saved-widget-contract.md:174-181`) does not state what satisfies condition 3 in the local single-user runtime. The smallest possible next action, in order of preference:

1. **One sentence in `guardian/routes/saved_widgets.py`** (implementation-owned, not available in this task): state that in the local single-user runtime the route accepts the deployment's configured static API key as the local user's own credential, and that the remote and private-preview lanes require an account session and refuse static keys.
2. **Optionally one clause in the contract's "Promotion is explicit" list**: record that in the supported local single-user runtime the user's own credential, session or configured static key, constitutes the explicit save action, while remote and private-preview promotion requires an account session.

Neither step changes runtime behaviour, and neither is required for the promotion operation to be correct.

## ADR impact

**No new ADR is required, and none is created or modified by this audit.**

The behaviour is aligned with accepted ADR-102 (Saved Widget identity, classification, and revision boundary) and with the existing Guardian authentication doctrine recorded in ADR-069's "Supported Runtime Profile Relationship". The local static-key lane is pre-existing authentication doctrine; the promotion route inherits it rather than extending it. No architectural decision is reopened, and the finding is a documentation-precision and contract-clarity matter, not an architecture question.

This is a **narrow implementation correction under existing decisions** (the route's own prose), not a new architecture decision.

## Commands executed and results

| Command | Result |
| --- | --- |
| `git status --short --branch --untracked-files=all` | Branch `feat/saved-widget-promotion-20261029`, clean tracked tree, four pre-existing untracked `.sandbox_probe_*` artifacts preserved untouched |
| `git rev-parse HEAD` | `a2547c5555391a28316f3d95cc79375cfe58a92e` |
| `git diff --check` | No whitespace errors |
| `rg`/`grep` over `guardian/core/dependencies.py` for the auth symbols | Mapped `verify_api_key` `:778`, `verify_account_session` `:1100`, `require_account_session` `:1155`, `get_account_user_id` `:1272`, `get_request_user_id` `:452`, `_auth_mode` `:229`, `_allow_user_header_override` `:258` |
| `grep` over `guardian/routes/saved_widgets.py` | `require_account_session` at `:276`, `:368`, `:402`, `:434`; `get_account_user_id` at `:280`, `:372`, `:406`, `:439`; `PROMOTION_ACTOR_USER` `:87`; `persist_saved_widget` `:307` |
| `grep` over `config/supported_profiles/` | `saved_widgets` enabled in all five profiles; default profile line 37 |
| Credential acceptance probe (18 cells, 3 modes × 6 credential classes) | All cells measured; matrix recorded above |
| Focused existing tests: `tests/identity/test_mixed_principal_boundary.py`, `test_identity_boundary_contract.py`, `test_account_user_jwt_identity.py`, `test_account_purpose_strict_migration.py`, `test_request_user_scope_contract.py`, `test_operator_session_boundary.py`, `tests/core/test_chat_tool_exposure.py`, `tests/command_bus`, `tests/routes/test_saved_widget_promotion.py` | **320 passed, 25 skipped, 0 failed**, 23.71 s |
| `python scripts/validate_docs.py` | Required for this receipt; result recorded below |

## Limitations

- Every credential used was synthetic: a probe-local static key, a signed account-session token for a synthetic `owner@example.com`, a signed operator token, and a synthetic Hosted-Room guest token. No real account credential was used, and no promotion was performed against real account data.
- The real local `.env` value of `GUARDIAN_API_KEY` was **not read or printed**; only its presence and the local auth mode were confirmed.
- The remote and private-preview lanes were exercised by environment configuration with synthetic tokens, not against the deployed private-preview stack, whose principal must be an approved email bound to a stored session.
- The audit is static-plus-synthetic. It does not observe a live remote or private-preview deployment.
- The four pre-existing untracked `.sandbox_probe_*` artifacts were left in place untouched.

## Release posture

**HOLD**, unchanged. This audit produces no release-readiness claim, changes no runtime behaviour, and asserts no new capability. The promotion operation is now integrated on `main` as a consequence of the external merge of PR #962; integrating the operation is not a release-readiness claim, and the Saved Widget lifecycle remains HOLD.

## Merge recommendation

**HOLD — not GO, and not an architectural decision.**

The promotion operation's authorization boundary is sound in every runtime mode that matters, the model has no path to it, and the one defect is documentation prose. PR #962 merged at 19:15:33Z before this audit completed, so the recommendation no longer concerns the pull request; it concerns `main`, which now ships the route together with the overstated prose.

The recommendation is a **narrow documentation correction on `main`** — one sentence in the `guardian/routes/saved_widgets.py` module docstring (and, optionally, one clarifying clause in the contract's "Promotion is explicit" list) — recording that in the local single-user runtime the route accepts the deployment's configured static API key as the local user's own credential, while the remote and private-preview lanes require an account session and refuse static keys.

No runtime change, no schema change, and no authentication-doctrine change is required or recommended.

**Files changed by this audit:** this receipt only.
