---
recipe_id: codexify.networking.tailscale-tester-isolation.v1
title: Isolate Codexify tester access with a dedicated Tailscale identity
status: draft
risk_level: high
domain: networking
issue: 536
owner: Resonant-Jones
requires_human_approval: true
idempotency: partial
destructive_by_default: false
tool_candidate: true
---

# Isolate Codexify Tester Access with a Dedicated Tailscale Identity

## Intent

Give an external tester remote access to the Codexify tester application without adding them as a normal member of the operator's personal tailnet, exposing VaultNode host services, disrupting existing personal-device connectivity, or wiping tester application state.

Desired boundary:

```text
Tester
  |
  v
Shared Tailscale node: codexify-test
  |
  v
Single Codexify tester ingress
  |
  +--> frontend
  +--> backend API
```

## Use this recipe when

- exposing the tester runtime over Tailscale
- giving a friend access to Codexify without exposing VaultNode
- creating a dedicated Tailscale identity for Codexify
- implementing GitHub issue #536

Do not use it for public internet deployment, Tailscale Funnel, subnet routing, exit-node configuration, general VaultNode access, or production security certification.

## Current architecture anchors

The tester runtime currently uses:

- Compose project: `codexify_tester`
- environment file: `.env.tester`
- frontend host port: `5174`
- backend host port: `8889`
- supported profile: `v1-friends-family-web`
- separate Compose volumes for tester state
- remote session/JWT authentication

The frontend currently defaults its backend URL to `http://localhost:8889`. A remote tester's browser cannot use that address because it would refer to the tester's own computer. Prefer a single same-origin ingress that routes frontend and API requests through one Tailscale-reachable port.

## Required inputs

```yaml
tester_identity: tester@example.com
tailscale_hostname: codexify-test
tailscale_tag: tag:codexify-test
approved_port: 443-or-selected-port
compose_project: codexify_tester
env_file: .env.tester
share_method: email-or-single-use-link
```

Do not guess the tester identity, approved port, or existing Tailscale policy shape.

## Required permissions

The assistant may need repository write access, Docker access on VaultNode, permission to inspect Tailscale state, and Tailscale admin access.

Stop for explicit operator approval before:

- generating or revealing an auth key
- modifying live tailnet policy
- sharing the node with a tester
- changing host firewall rules
- deleting a Tailscale state volume

## Security invariants

1. Deny by default.
2. Permit only the selected tester identity.
3. Permit only the approved Codexify ingress port.
4. Do not use broad `*:*` grants.
5. Do not advertise subnet routes.
6. Do not advertise an exit node.
7. Do not enable Tailscale SSH.
8. Do not expose Docker, Postgres, Redis, Neo4j, SSH, dashboards, or unrelated host ports.
9. Do not commit auth keys, session secrets, JWT secrets, or share links.
10. Do not use host networking unless separately justified and approved.
11. Preserve the existing VaultNode Tailscale identity.
12. Preserve ordinary local access.
13. Preserve tester application volumes during restart and redeploy.
14. Never run `docker compose down -v` as part of this recipe.

## Preflight

### Repository state

```bash
git status --short
git branch --show-current
git rev-parse --show-toplevel
```

Do not overwrite or discard unrelated changes.

### Tester files and secret hygiene

```bash
test -f docker-compose.yml
test -f docker-compose.tester.yml
test -f .env.tester
git check-ignore .env.tester
```

### Render the effective topology

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  config
```

Record service names, networks, published ports, health checks, dependency relationships, stateful volumes, and any existing reverse proxy.

### Check the live tester runtime

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  ps

curl -I http://localhost:5174
curl -fsS http://localhost:8889/health
```

Do not continue until the ordinary tester runtime is understood and healthy.

## Architecture decision gate

Choose exactly one ingress pattern.

### Pattern A: existing reverse proxy

Attach the Tailscale identity to the existing tester-compatible gateway. Expose one Tailscale port and route internally:

```text
/        -> frontend:5173
/api/*   -> backend:8888
/auth/*  -> backend:8888
/media/* -> backend:8888
```

### Pattern B: new minimal tester gateway

Use when no suitable same-origin ingress exists. Add a small proxy service dedicated to the tester profile. It must listen on one internal port, route frontend and backend traffic, preserve required WebSocket behavior, and avoid changing the default development profile.

### Pattern C: direct service networking

Use only when the frontend can safely use a remote-reachable backend URL and the complete CORS/session posture has been verified. Document why Pattern A or B was rejected.

## Tailscale identity posture

Use a dedicated Tailscale container with:

```yaml
hostname: codexify-test
state_directory: /var/lib/tailscale
persistent_state: true
subnet_routes: none
exit_node: false
tailscale_ssh: false
```

Prefer a tagged one-off auth key for initial registration. Do not default to an ephemeral node, untagged server identity, or reusable key. Persisted state should retain the registered node identity after initial authentication.

## Compose deliverable

Create a dedicated override:

```text
docker-compose.tailscale-tester.yml
```

Illustrative shape only:

```yaml
services:
  tailscale-test:
    image: tailscale/tailscale:latest
    hostname: "${TAILSCALE_TESTER_HOSTNAME:-codexify-test}"
    environment:
      TS_AUTHKEY: "${TAILSCALE_AUTHKEY:?TAILSCALE_AUTHKEY is required for first registration}"
      TS_HOSTNAME: "${TAILSCALE_TESTER_HOSTNAME:-codexify-test}"
      TS_STATE_DIR: /var/lib/tailscale
      TS_USERSPACE: "false"
    volumes:
      - tailscale_tester_state:/var/lib/tailscale
    devices:
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped

volumes:
  tailscale_tester_state:
```

Adapt this to the actual Compose topology. Do not blindly combine `network_mode`, ordinary networks, and published ports.

## Environment template

Add placeholders to a safe committed template:

```dotenv
TAILSCALE_TESTER_HOSTNAME=codexify-test
TAILSCALE_TESTER_TAG=tag:codexify-test
TAILSCALE_TESTER_PORT=<selected-port>
TAILSCALE_AUTHKEY=<provide-at-runtime-never-commit>
```

The real key must live in a gitignored environment file, Docker secret, or approved secret store.

## Tailnet grant template

```json
{
  "tagOwners": {
    "tag:codexify-test": [
      "autogroup:admin"
    ]
  },
  "grants": [
    {
      "src": [
        "TESTER_EMAIL"
      ],
      "dst": [
        "tag:codexify-test"
      ],
      "ip": [
        "tcp:CODEXIFY_PORT"
      ]
    }
  ]
}
```

Reject the policy if it contains wildcard source, destination, or port access. Validate it in the Tailscale policy editor before applying it.

## Node registration

Start the dedicated identity first:

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  up -d tailscale-test
```

Inspect:

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  exec -T tailscale-test tailscale status

docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  exec -T tailscale-test tailscale ip -4
```

Confirm in the admin console:

- hostname is `codexify-test`
- expected tag is present
- subnet routes are absent
- exit-node behavior is disabled
- Tailscale SSH is disabled

## Start the complete ingress

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  up -d
```

Do not share the node until local health is green.

## Local verification

```bash
curl -I http://localhost:5174
curl -fsS http://localhost:8889/health
```

Verify authentication through the frontend and verify that the frontend reaches the backend through the final remote-compatible route.

## Share the node

After explicit operator approval:

1. Select `codexify-test` in the Tailscale Machines page.
2. Share it with the specific tester by email or single-use link.
3. Treat the invite link like a credential.
4. Record who received access and when.
5. Do not place the share link in source control, issues, logs, or receipts.

## Positive remote verification

From the tester's Tailscale-connected device:

```bash
curl -I http://codexify-test:CODEXIFY_PORT
```

Then verify:

- the login page loads
- the tester can authenticate
- only the tester's account data appears
- thread creation works
- restart does not erase the account

## Negative access verification

From the tester device, verify that unrelated ports fail unless one is intentionally selected as the single ingress:

```bash
nc -vz codexify-test 22
nc -vz codexify-test 5432
nc -vz codexify-test 5434
nc -vz codexify-test 6379
nc -vz codexify-test 7474
nc -vz codexify-test 7475
nc -vz codexify-test 7687
nc -vz codexify-test 7688
nc -vz codexify-test 8888
nc -vz codexify-test 8889
```

Also verify the tester cannot reach VaultNode SSH, VaultNode dashboards, VaultNode databases, AxisNode services, or other personal-tailnet devices.

## Restart persistence verification

Capture Tailscale state before restart:

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  exec -T tailscale-test tailscale status --json \
  > /tmp/codexify-tailscale-before.json
```

Restart without deleting volumes:

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  restart tailscale-test tester-gateway
```

Capture state after restart and verify:

- the same machine remains in the admin console
- the tester share remains valid
- the approved port remains reachable
- no duplicate node was created
- Codexify accounts and threads remain present

## Personal-tailnet regression check

From an existing personal device:

```bash
tailscale ping VaultNode
tailscale ping AxisNode
```

Do not claim this passed without testing it from a personal-tailnet device.

## Success receipt

Write a receipt under:

```text
artifacts/recipe-runs/codexify.networking.tailscale-tester-isolation.v1/<timestamp>/receipt.json
```

Minimum shape:

```json
{
  "recipe_id": "codexify.networking.tailscale-tester-isolation.v1",
  "result": "pass",
  "tailscale_hostname": "codexify-test",
  "tailscale_ip": "<redacted-or-approved>",
  "approved_port": "<port>",
  "tester_identity": "<redacted-or-approved>",
  "local_access": "pass",
  "remote_access": "pass",
  "negative_port_checks": "pass",
  "account_persistence": "pass",
  "tailscale_identity_persistence": "pass",
  "personal_tailnet_regression": "pass",
  "secrets_committed": false,
  "subnet_routes_enabled": false,
  "exit_node_enabled": false,
  "tailscale_ssh_enabled": false,
  "evidence": []
}
```

Never place an auth key, JWT, session token, reusable invite link, or secret value in the receipt.

## Rollback

To revoke tester access immediately:

1. Revoke the node share.
2. Remove or disable the tester grant.
3. Stop the Tailscale tester service and gateway.

```bash
docker compose \
  --env-file .env.tester \
  -p codexify_tester \
  -f docker-compose.yml \
  -f docker-compose.tester.yml \
  -f docker-compose.tailscale-tester.yml \
  stop tailscale-test tester-gateway
```

Do not delete the Tailscale state volume during ordinary rollback. Permanently retiring the identity requires separate operator approval.

## Return `blocked` rather than improvising when

- the tester runtime is unhealthy
- the frontend still directs remote browsers to localhost
- the policy would require wildcard access
- a Tailscale auth key is tracked by Git
- unrelated host ports become reachable
- the tester can see another account's data
- the override changes the default development profile
- restart creates a duplicate Tailscale node
- verification cannot be performed from the tester's device
- personal-tailnet regression checks cannot be completed

## Expected implementation deliverables

```text
docker-compose.tailscale-tester.yml
.env.tailscale-tester.example
docs/Ops/tailscale-tester-access.md
docs/policy/tailscale-tester-grants.example.hujson
artifacts/recipe-runs/<recipe-id>/<timestamp>/receipt.json
```

## Tool-collapse candidate

After this recipe succeeds repeatedly, it may be wrapped as:

```text
guardian.networking.configure_tester_access
```

Suggested input:

```json
{
  "hostname": "codexify-test",
  "tester_identity": "tester@example.com",
  "port": 443,
  "share_method": "email",
  "apply_policy": false,
  "send_share": false,
  "dry_run": true
}
```

The tool must default to dry-run behavior. It may prepare patches and policy snippets, but must not autonomously create or expose auth keys, apply tailnet policy, invite a tester, enable routes, enable exit-node behavior, enable Tailscale SSH, remove persistent state, or widen access beyond the declared port.
