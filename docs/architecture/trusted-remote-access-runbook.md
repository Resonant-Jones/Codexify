# Trusted Remote Access Runbook

> Classification: next-proof-needed
> Status: operator-facing proof gate
> Scope: docs/proof only

Last updated: 2026-06-30

## Purpose

This runbook is the operator-facing proof gate for trusted remote browser access over Tailnet/private LAN.

It separates implementation seams from live evidence. Do not claim trusted remote access is operational until a proof packet captures a real browser flow with network, storage, CORS, login/profile, logout, and redaction evidence.

## Proof Packet Index

- [Trusted Remote Browser Final Proof - 2026-06-23](./proofs/2026-06-23-trusted-remote-browser-final-proof.md) - classification `next-proof-needed`
- [Trusted Remote Browser Codex Proof - 2026-06-23](./proofs/2026-06-23-trusted-remote-browser-codex-proof.md) - classification `next-proof-needed`

## Codex Browser Proof Result

The Codex browser proof captured:

- frontend reachability for `http://100.109.4.57:5173/register`
- frontend reachability for `http://100.109.4.57:5173/login`
- frontend reachability for `http://100.109.4.57:5173/profile`
- throwaway account registration/login through browser UI
- metadata-only User Profile update for `display_name`, `avatar_url`, and `timezone`
- sanitized screenshots for register, login, and profile metadata pages
- backend health/catalog route reachability from the browser context

The classification remains `next-proof-needed` because the proof is missing:

- full browser network logs or HAR export
- browser storage inspection from DevTools/Application-equivalent tooling
- CORS response-header capture from browser network evidence
- logout plus post-logout `GET /api/user/profile` returning `401`
- an independently separable remote-client browser context

## Claim Boundaries

This runbook does not claim:

- public internet support
- SaaS support
- general multi-user release support
- Tailnet automation
- account-scoped thread/document/retrieval proof
- packaged desktop replacement of local Compose

If a future packet reaches `go`, the narrow allowed claim is:

- trusted remote browser access over private Tailnet/private-LAN path is proven for session login and metadata-only User Profile read/write under the opt-in overlay.

## Invariants

- Trusted remote posture remains opt-in.
- Default Compose behavior remains unchanged.
- User Profile remains separate from Persona Profile.
- Profile metadata is not canonical ownership identity.
- Tailnet/private-LAN does not replace application-layer auth.
- Browser storage is a risk surface, not a trust boundary.
- No raw passwords, session tokens, cookies, API keys, or secrets may be committed.

## Local Overlay (`config/trusted-remote.env`)

The trusted-remote overlay is **local-only and must never be committed**. It may carry local/dev session or JWT signing secrets.

- `config/trusted-remote.env` is gitignored and is removed from Git tracking.
- `config/trusted-remote.env.example` is the canonical source for the required variable names only. It contains placeholders, never real secrets.
- To create a local overlay, copy the example and fill in local values:

  ```bash
  cp config/trusted-remote.env.example config/trusted-remote.env
  # then edit config/trusted-remote.env with local-only values
  ```

- Secrets should be regenerated per environment. Treat any previously committed overlay values as expired local/dev material.
- The guardrail in `scripts/preflight.sh` fails if a real overlay (any trusted-remote env variant) is tracked or staged, if the `.example` is missing, or if the `.example` carries obvious secret-looking values.

### Verify the real overlay is ignored

```bash
git check-ignore -v config/trusted-remote.env
git ls-files config/trusted-remote.env   # must print nothing
```

The first command should print the `.gitignore` rule that matches; the second must print nothing (untracked).

### If a real overlay is accidentally staged

```bash
git restore --staged config/trusted-remote.env
git status   # confirm it is no longer staged
```

The file stays on disk; only its staged state is cleared.

### If a real overlay is accidentally committed

1. Remove it from tracking (keeps the local copy):

   ```bash
   git rm --cached config/trusted-remote.env
   git commit -m "chore(security): stop tracking trusted remote env overlay"
   ```
2. Treat any values that reached history as **expired** — regenerate `GUARDIAN_SESSION_SECRET` / `GUARDIAN_JWT_SECRET` per environment.
3. History rewriting (`git filter-repo` / BFG) is a separate, high-blast-radius decision and is not part of this runbook. Only consider it if the repo is shared beyond the local machine.

### Run the preflight check

```bash
bash scripts/preflight.sh
```

It exits non-zero if a trusted-remote env file is tracked or staged, the `.example` is missing, or the `.example` contains obvious secret-looking values. It passes when only the `.example` is present and the real overlay is ignored.
