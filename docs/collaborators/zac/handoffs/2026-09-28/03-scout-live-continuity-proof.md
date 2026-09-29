# Lane 3 — Scout Live Continuity Proof

## Outcome

Execute the first live authenticated Scout proof defined by GitHub #815 using the actual Scout app and an operator-approved Guardian endpoint.

This lane is deliberately narrow. It proves one client/auth/runtime boundary; it does not attempt the whole iOS roadmap.

## Governing Issue

GitHub #815 — Scout iOS Phase 1: prove live Vault continuity loop.

Phase 0 (#814) and the explicit authentication-mode prerequisite (#822) are already complete. Do not repeat them.

## Prerequisites

Before sending any credential:

- use a Scout build containing the #822 authentication-mode work;
- use Xcode + an iOS Simulator or approved device;
- identify the operator-approved Guardian endpoint;
- verify that the endpoint supports the existing local/operator API-key contract;
- use `localAPIKey` mode only for this slice;
- enter the key through Scout's secure field / Keychain path.

The credential must not appear in chat, screenshots, shell history, logs, commits, or the proof report.

## First Bounded Slice

1. Make a protected thread-list request without authentication and record that it is rejected.
2. Configure the approved endpoint and local API key through Scout.
3. Make a fresh request from the actual Scout app.
4. Confirm that the protected thread list is now readable.
5. If a suitable existing thread is present, open it and observe persisted messages.
6. Record reachability, authentication, and provider readiness as separate facts. Do not infer one from another.

Do not move into thread creation, message sending, Guardian completion, or task SSE until this first proof is clean.

## Evidence Artifact

Create:

`docs/collaborators/zac/reports/YYYY-MM-DD-scout-live-auth-read-proof.md`

Record:

- Scout branch/commit used;
- simulator/device class;
- endpoint classification without embedding secrets;
- explicit auth mode exercised;
- unauthenticated protected-route result;
- authenticated Scout result;
- thread-list observation;
- whether an existing thread opened;
- screenshots/log excerpts with credentials and sensitive values removed;
- any blocker exactly as observed.

## Proof Gate

Pass only when:

- the unauthenticated protected request is rejected;
- a fresh request from Scout using the approved local API-key mode succeeds;
- the result is observed in the actual Scout UI/service path;
- no silent auth-mode fallback occurs;
- no credential leaks into evidence.

A blocked result is still useful if the block is genuine and precisely evidenced.

## Non-Goals

- No remote-session implementation.
- No Cloudflare Access bypass.
- No Guardian auth changes.
- No hosted-readiness claim.
- No App Intents or Siri work.
- No desktop parity work.
- No weakening server policy to make the client pass.

## Next Step

After the first proof passes, return the evidence. The remaining #815 continuity sequence can then be split into the next bounded slice.
