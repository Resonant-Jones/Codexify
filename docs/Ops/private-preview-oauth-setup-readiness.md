# Private Preview OAuth setup readiness

Status: isolated source preparation; not deployment or activation evidence.
Release posture remains HOLD. No connector invocation is authorized by this patch.

## Decision and authority

Architecture-impact lane, aligned with ADR-005, ADR-071, ADR-075, ADR-092 and
ADR-112. The operator's bounded setup request selects admission of the existing
account-owned OAuth control plane. No new execution architecture is needed for
this slice. ADR-112's accepted in-process topology still requires its unimplemented
end-to-end accepted-attempt/Command Bus/provider authorization proof before any
Preview worker invocation. Immutable acceptance custody alone is insufficient.
ADR-072's local route promotion is not reused as a remote execution grant.

The authoritative setup actor remains the authenticated canonical account. Its
same-origin consent action starts server-owned, browser-bound, single-use state;
callback evidence alone does not select an account or grant execution. Encrypted
credentials and revocation generations remain under that account. The catalog
projects the provider-owned state; it creates no new authorization owner.
Imported-history consent, provenance and model-exposure exclusions are unchanged.

## Prepared source behavior

The `v1-whooshd-deepseek-web` manifest admits the read-only `connections` catalog
and `notion_setup` / `github_knowledge_setup` as internal-only. Setup additionally
requires `GUARDIAN_EXPOSURE_MODE=private_preview`, explicit
`CODEXIFY_ENABLE_KNOWLEDGE_OAUTH=1`, and the existing provider route flags.
Only OAuth routes mount there: legacy configure/validate/disconnect token routes
remain absent. Missing operator credentials make the catalog OAuth action
unavailable. Account, origin, browser nonce, revocation and consent checks remain
in the existing provider routes. No setup route enters model OpenAPI tools.

`notion_knowledge`, `github_knowledge` and generic `connectors` remain quarantined,
even with their flags enabled. `CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT` must remain
unset/false in deployment; existing remote/Preview denial also stays in force.
No provider allowlist, execution permission or resource grant is widened.
Other profiles retain their prior setup behavior. The catalog is read-only and
account authenticated; availability is not proof of a successful consent flow.

## Callback log boundary

Nginx's inherited combined log includes `$request` and Referer, both of which can
contain callback code/state. The prepared HTTP-level format logs only method,
normalized URI path, status, byte count and duration. It deliberately does not log
request headers, query strings, upstream URLs or Referer. Proxy traffic still
carries the original query to Guardian.

Nginx error messages cannot be reformatted reliably and can include the entire
request before location selection. The prepared config discards HTTP-context
error logs via `/dev/null`; access status/timing remain available. This is an
explicit diagnostic tradeoff to review in the final deployment candidate. Do not
restore raw error logging during real consent troubleshooting. Startup config
errors outside HTTP request processing remain operational diagnostics.

Backend log sanitization removes the entire known callback query, including
unknown/encoded parameter names and provider error text. Standalone `state`
parameters are also redacted. Preformatted callback URLs embedded in logging
templates cause a bounded event marker, preserving formatter safety. Existing
exception/body/credential suppression and Uvicorn argument structure remain.

The repository Edge Worker logs pathname rather than query and rejects callback
paths without proxying; a synthetic regression covers this. That worker is not
proven to be the Preview callback ingress. Its test does **not** prove Cloudflare
zone logs, Access logs, WAF events, Logpush, Workers platform observability,
cloudflared diagnostics, or third-party telemetry omit query strings.

## Synthetic sentinel verification plan (not executed live)

1. Establish a stable final serving candidate incorporating Preview-specific
   source and preserved local configuration. Use a disposable deployment with no
   real secrets, accounts or provider access. Never point its mounts/DB/volumes at
   the live project. Validate effective `nginx -T` inheritance, not just this
   source fragment, and confirm the backend logging entry point installs the
   sanitizer before serving requests.
2. Send unique synthetic `code`, `state`, `error_description` and unknown-parameter
   sentinels to both callback paths, with no account cookie and no OAuth nonce.
   Exercise parameter order, encoded names, callback trailing-slash rejection,
   Referer containing sentinels, oversized/invalid request refusal and upstream
   failure in the disposable deployment only. Verify bounded 4xx/5xx responses,
   no credential/flow/user rows created, and no provider egress. Verify a separate
   stub receives the original query, proving logging protection does not break
   callback exchange.
3. Capture only this disposable run's nginx access/error, backend access/error,
   process stdout/stderr, tunnel logs and telemetry. Assert zero occurrences of
   every raw and percent-encoded sentinel; retain counts and test IDs, not full
   logs from real traffic. Access records must still show status and timing.
   A passing application sanitizer test cannot replace effective logger testing.
4. Map the actual public callback ingress chain through DNS/tunnel/any Worker.
   Review enabled Cloudflare HTTP/Access/WAF/Logpush fields, retention, request-URL
   fields and platform request metadata. Verify query removal/omission at each
   enabled sink. No managed-edge policy is changed by this patch. Cloudflared's
   default log level alone is not a redaction guarantee: prove error-path behavior
   with synthetic traffic in the disposable path and use an approved omission or
   scrubbing boundary if it logs full URLs. Missing visibility is a blocker.
5. After the deployment owner approves a stable rollout, repeat only the harmless
   missing-nonce sentinel refusals through the final ingress and verify approved
   sink counters. Do not inject faults into live services, use real users, replay
   real callback tokens, or inspect unrelated user logs. Real consent remains a
   separate operator-controlled canary after all layers pass.

## Provisioning, migration and rollout handoff

- Reconcile with the live owner first. This patch is based on merged OAuth source
  `0e2374ff3b34f86dc6c4d8c33a291754ecc5c7f1`, not the separate serving branch.
  Preserve its export/library/Scout/security behavior, dirty nginx changes and
  untracked serving Compose overlay. Require full CI on the final integrated
  revision plus supported-path checks; these unit/contract tests are not rollout
  qualification. Do not blindly pull latest main.
- Provision both providers' client ID, secret and exact registered callback URI,
  plus `GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY`, only into backend. Use an external
  protected backend-only env file or reviewed secret-manager delivery. Current
  code reads env variables, not arbitrary `_FILE` mounts. Never add credentials to
  shared runtime `.env`, frontend/Vite, worker services, source control or chat.
  Check resolved service environments using presence booleans only. Encryption
  key custody/recovery must exist before storing consent tokens.
- Require a fresh backup/isolated restore proof and a reviewed rollback before
  live migration. From `ab71d5ce9604`, the chain is custody `c7e4a1b9d602`, GitHub
  credentials `c13f0713a901`, then OAuth store/flows `d8a90bf32107`. Read the actual
  database head; successful migrator exit is insufficient. Rehearse the complete
  final source chain and existing-data preservation on a disposable restore.
  Credential/custody downgrades destroy new state: choose forward-compatible app
  rollback or a controlled restore with an explicit post-snapshot write policy.
  Do not run a backup helper that freezes writers until the live owner coordinates
  it and clean-source/image-coherence preconditions are satisfied.
- Review provider registrations and minimal read permissions, callbacks, selected
  repository/page grants and secret delivery with the operator. An app's public
  ID is not installed credentials or consent proof. Use only an explicitly
  authorized canary account and resources for real consent; verify status,
  disconnect/revocation and account isolation. No provider writes, ambient service
  token fallback, imported-history exposure or background dispatch is admitted.
- Enable setup flags only after the complete candidate, migration, backup,
  backend-only secrets and effective logging proof are ready. Keep operation
  routes and Preview knowledge worker dispatch quarantined. Record separately:
  implemented, merged, deployed, configured, consent-tested and still disabled.
