# Knowledge pilots: Preview transport decision

Date: 2026-11-13. **Investigation/proposal only; neither option is approved or implemented.**

## Confirmed boundary

The scoped worker tools intentionally fail closed in Preview/remote/multi-user
posture. `account-history-recall-contract.md` §9.2 explicitly identifies account-
subject transport or an approved alternative as the missing decision. The same
existing local guard protects this Knowledge pilot.

Code anchors:

- `guardian/tasks/types.py`: accepted task identity, not a retained browser
  account-session credential.
- `guardian/core/chat_completion_service.py`: accepted-attempt checkpoint,
  trusted task account, local transport eligibility, Command Bus invocation.
- `guardian/command_bus/loopback_http_adapter.py`: HTTP command dispatch with
  forwarded inbound authorization/API key/user/cookie headers. A task account
  string is not a remote account credential.
- `guardian/core/dependencies.py::verify_account_session`: remote account routes
  require exact-purpose account credentials; Preview additionally requires its
  stored approved account and edge/account principal checks.
- `guardian/core/capability_tokens.py`: the existing capability-grant foundation
  represents account entitlements, not a worker transport credential.

ADR-092 preserves separate account, operator and guest lanes; raw operator keys
must not become account principals. Its exact-purpose rule also prevents
minting a worker token and silently treating it as a normal account session.
ADR-094 offers a useful **coding-credential** precedent for secret-free,
attempt-bound references and execution-time reauthorization; it does not itself
approve a Knowledge credential transport.

## Option A: narrow worker transport capability

Approve a new, registered worker-purpose capability, bound to an authenticated
account, accepted request/attempt, exact command, arguments or scope, audience,
expiry, and revocable connection reference. An internal endpoint must validate
that capability and current account/attempt/connection eligibility before the
provider adapter executes. Queue state carries only a non-bearer reference;
redemption happens in the trusted control path. The capability must not be
accepted on arbitrary account routes, forwarded to external hosts, or logged.

Benefit: a genuine boundary works across separate worker/API processes.
Cost: new credential purpose/issuer/validator, replay and revocation handling,
internal endpoint topology, and transport tests. Edge/browser authentication
cannot simply be bypassed on existing routes.

## Option B: account-bound in-process Command Bus adapter

Approve a provider-specific internal read-command dispatch using the existing
Command Bus internal execution family rather than HTTP loopback. It must bind
and recheck the canonical accepted account/request/attempt and current connection
scope, retain Command Bus policy, audit and source evidence, and resolve secrets
only inside the trusted provider adapter. The model still chooses no identity,
headers, credential, or endpoint.

Benefit: avoids minting a broad account-session token or carrying browser auth
through queues for a same-process operation; simplest topology for this pilot.
Cost: changes the current HTTP execution boundary, requires explicit internal
command identity and network-policy decisions, and must prove that untrusted
queue fields or direct callers cannot supply the account authority. Existing
`native::fs::read_file` dispatch is a mechanical example, not approval for
external Knowledge reads. No new universal execution owner is needed.

**Recommendation: B for the same-process pilot**, if the owner approves that
architecture direction; choose A if remote/API-separated worker boundaries are
a requirement now. Neither can be called a safe wiring-only fix under the
currently documented contract.

## Required proof for either option

- Two accounts using the same worker cannot resolve each other's connections.
- Forged task/account, changed scope, revoked connection/account, cancelled or
  expired attempt, duplicate/replayed execution and missing approval fail closed.
- No browser/edge credential, PAT or integration token appears in queue records,
  model inputs, command events, traces, errors, or another invocation's state.
- Only the exact read operation reaches its fixed provider host; no redirect,
  arbitrary URL, mutation, implicit ingestion or memory authority is gained.
- The chosen Preview route/profile posture is separately approved and qualified;
  default Beta and current live Preview remain unchanged until deployment.

No authentication guard was relaxed during this investigation. Setup UI work
can proceed independently while this architecture decision remains open.
