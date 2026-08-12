# Cloudflare public private-preview tunnel proof

## Scope

This receipt records the Phase 1 prerequisite gate for the existing
Codexify private-preview Cloudflare publication path:

```text
Internet -> preview.codexify.space -> Cloudflare Access -> existing Cloudflare Tunnel
  -> http://127.0.0.1:8081 -> private-preview-origin -> Codexify frontend / Guardian
```

It authorizes no new public-exposure architecture. The only repository change
in this task is this receipt. Cloudflare, DNS, connector, Access, Render, and
Tailscale were not inspected or changed after the static gate failed.

## Workflow classification

- Execution lane: architecture-impact.
- Task kind: implementation plus live proof.
- Evidence posture: the private-preview Compose topology and origin contract
  are repository- and test-backed; local runtime, Cloudflare Tunnel,
  Cloudflare Access, DNS, public-host, and authenticated public application
  behavior remain unproven in this receipt.

## ADR impact

Aligned with existing contracts; no ADR changed.

- ADR-039 Operator / User Access Boundary keeps infrastructure authority
  separate from application users.
- ADR-040 Network Profile Topology Resolution Contract keeps transport
  selection from bypassing authentication or exposure policy.
- ADR-052 Whoosh'd Gemma and Approved DeepSeek Startup Profile confines this
  opt-in profile to its named provider posture.
- The task packet named ADR-061 Capability-Oriented Mesh Architecture. That
  path is absent in this checkout; the related checked-in document is
  `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`.
  This filename/identifier provenance discrepancy did not contradict the
  specified single-origin topology.

## Repository branch and HEAD

- Branch: `codex/audit-reports-2026-08-07`.
- Pre-task HEAD: `5c73a0d4b4980272e2129814d23ae034aae95cc9`.
- Initial working tree: clean.
- Initial `git diff --check`: passed.

## Current-truth anchors

`docs/architecture/00-current-state.md` keeps the supported release posture
local-first and local-only. It describes the private-preview lane as bounded
and opt-in, and requires authenticated provider-specific persisted-turn proof
before any private-preview release claim. This receipt does not change that
truth.

The reviewed private-preview operations and Compose contracts specify
`preview.codexify.space` as the intended hostname and
`http://127.0.0.1:8081` as its sole host-facing application origin.

## Local private-preview topology

Repository inspection established the intended topology only:

- `private-preview-origin` publishes
  `127.0.0.1:${CODEXIFY_PREVIEW_PORT:-8081}:8080`.
- The overlay clears host port publications for backend, frontend, database,
  Redis/Neo4j-related services, and other private runtime surfaces.
- Nginx proxies `/`, `/api`, `/ws`, `/health`, and `/health/*` through the
  one origin; backend resolution remains on the Compose network.
- Whoosh'd remains a loopback host process accessed from Docker through
  `host.docker.internal:8000/v1`; it is not a Cloudflare origin.

## Local origin validation

Not run. The required static validator stopped before any runtime or origin
reachability attempt because the active checkout lacks its untracked
`.env.private-preview` file.

Command and sanitized result:

```text
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh static
-> failed: private-preview env file is missing
```

## Host-port isolation proof

Not run against containers because the static gate failed. Repository static
tests prove the intended host-port contract only, not live process state.

## Cloudflared version

Not inspected after the static gate failure.

## Existing tunnel identity

Not inspected after the static gate failure. No tunnel was created.

## Tunnel management mode

Unknown. It was not inspected after the static gate failure.

## Existing connector state

Not inspected or restarted after the static gate failure.

## preview.codexify.space DNS result

Not inspected or changed after the static gate failure.

## Public-hostname origin mapping

Repository intent is exactly:

```text
preview.codexify.space -> existing Cloudflare Tunnel -> http://127.0.0.1:8081
```

The live configuration was not inspected, so this mapping is not proven.

## Cloudflare Access boundary result

Not inspected or exercised after the static gate failure.

## Authenticated Access result

Not exercised. No Access login, service token, account creation, or policy
change was attempted.

## Public Codexify root result

Not exercised through `https://preview.codexify.space/`.

## Public health-path results

Not exercised through the public hostname. No public checks of `/health`,
`/health/chat`, or `/api/health/llm` were performed.

## Sensitive-route policy results

Public policy was not exercised. The focused private-preview contract tests
passed from the repository virtual environment, but this is static contract
evidence and not a public-route result.

## Guardian authentication-boundary result

Static evidence only: the focused suite passed 10 tests, including private
preview registration denial and server-mapped admin/guest access boundaries.
No tunnel, Access, or Guardian authentication semantics were changed; an
authenticated public session remains unproven.

## codexify.space apex preservation result

Not probed after the static gate failure. No DNS or routing command targeted
`codexify.space`, `www.codexify.space`, or any Render service.

## Bounded log observations

No Compose, cloudflared, Render, or Tailscale logs were read after the static
gate failure. There is therefore no live connector/origin log evidence in this
receipt.

## Secret/exposure review

- No untracked preview environment contents were read or printed.
- No Cloudflare credentials, tunnel credentials, Access cookies, Guardian
  sessions, API keys, passwords, or full response bodies were requested or
  recorded.
- No Cloudflare, DNS, Render, Tailscale, or application-source mutation was
  attempted.

## What this proves

- The checked-in private-preview topology intends one loopback-only
  application origin at `127.0.0.1:8081`.
- The focused static private-preview test suite passes with the repository
  virtual environment: 10 passed.
- The active checkout does not provide the untracked environment file required
  for safe private-preview configuration rendering and static validation.

## What this does not prove

This receipt does not prove a running origin, host-port isolation of running
containers, an existing tunnel, connector health, DNS attachment, Cloudflare
Access, authenticated application behavior, public health paths, sensitive
route behavior, Guardian session continuity, or marketing-apex preservation.
It does not make a private-preview or release-support claim.

## Final classification: NEXT_PROOF_NEEDED

Failing seam: the active host checkout has no untracked
`.env.private-preview`, so the canonical private-preview static validation
cannot render the authorized profile.

## Exact next gate

As one atomic host-configuration task, provision the existing operator-owned
`.env.private-preview` in the checkout that hosts the preview runtime from the
committed template, without exposing or committing its secret values; then
rerun Phase 1 static validation before any Cloudflare inspection or mutation.

## Validation record

- Requested `pytest -v` command: blocked during collection because the global
  Python environment lacks `fastapi`; this was an environment issue, not a
  test assertion result.
- Equivalent focused suite using `.venv/bin/python -m pytest -v`: 10 passed,
  2 warnings.
- Canonical static validator: failed only because
  `.env.private-preview` is absent.
- `git diff --check` before this receipt: passed.
