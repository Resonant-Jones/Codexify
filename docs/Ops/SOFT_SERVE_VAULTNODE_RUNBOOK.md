# VaultNode Soft Serve Local Forge Runbook

This runbook operates an optional Soft Serve Git forge on VaultNode. It is a
developer/operator substrate, not a Codexify application dependency. The
supported Codexify beta path remains the existing local Docker Compose stack;
Soft Serve may be stopped or absent without changing that claim.

## Boundaries and posture

- Soft Serve runs from `docker-compose.soft-serve.yml`, never from the default
  `docker-compose.yml` graph.
- The `soft-serve` service has its own Compose lifecycle and data root.
- The default host bind is loopback. For trusted remote access, set
  `CODEXIFY_SOFT_SERVE_BIND_HOST` to the VaultNode Tailscale IP. Do not use
  `0.0.0.0` as the default or assume public-internet exposure.
- SSH public-key authentication is the initial access path. The first admin
  key must be an Ed25519 public key. Anonymous access is `no-access`, keyless
  access is `false`, and Git daemon port 9418 is not published.
- The operator chooses what is published to GitHub. No task in this runbook
  edits remotes automatically or synchronizes repositories in the background.

## Install the operator configuration

From the repository root on VaultNode:

```bash
cp config/soft-serve.env.example config/soft-serve.env
ssh-keygen -t ed25519 -f ~/.ssh/codexify-soft-serve-admin -C codexify-soft-serve-admin
sed -i.bak "s|^SOFT_SERVE_INITIAL_ADMIN_KEYS=.*|SOFT_SERVE_INITIAL_ADMIN_KEYS=$(cat ~/.ssh/codexify-soft-serve-admin.pub)|" config/soft-serve.env
```

On macOS, replace the final `sed` command with an editor if the BSD `sed`
syntax or the public-key comment requires manual quoting. Keep the private
key out of the repository. The configured data directory defaults to
`~/.local/share/codexify/soft-serve`; set
`CODEXIFY_SOFT_SERVE_DATA_DIR` to an operator-managed path when VaultNode
storage policy requires it.

For loopback-only access, leave `CODEXIFY_SOFT_SERVE_BIND_HOST` empty. For a
tailnet-only operator surface, set it to the VaultNode Tailscale IP and set
the public SSH/HTTP URLs to the corresponding tailnet name or address. The
public URL fields are clone-display metadata; they do not grant access.

## Validate, start, and inspect

The operator script always selects the separate Compose file explicitly:

```bash
make soft-serve-config
make soft-serve-up
make soft-serve-status
make soft-serve-logs
```

`soft-serve-up` fails before startup when the initial admin key is absent or
still a template placeholder. `soft-serve-status` is successful only when the
container is actually running and not unhealthy; it reports `missing`,
`created`, `starting`, `running`, `exited`, `restarting`, or `unhealthy` as
applicable. `soft-serve-down` stops the service and preserves the data root:

```bash
make soft-serve-down
```

To authenticate over SSH after startup:

```bash
ssh -i ~/.ssh/codexify-soft-serve-admin \
  -o IdentitiesOnly=yes \
  -p "${CODEXIFY_SOFT_SERVE_SSH_PORT:-23231}" \
  git@127.0.0.1 help
```

Use the VaultNode Tailscale host/IP instead of `127.0.0.1` when the bind host
was explicitly configured for tailnet access. A successful SSH command proves
the live Soft Serve SSH path only; it does not prove GitHub publication,
Codexify runtime health, or backup completion.

## Phase A: safe introduction

Keep the existing GitHub `origin` unchanged while adding Soft Serve as a
temporary forge remote. These commands do not rename or delete any remote:

```bash
git remote -v
FORGE_HOST="REPLACE_WITH_VAULTNODE_TAILNET_HOST"
git remote add soft-serve "ssh://${FORGE_HOST}:23231/codexify"
git push soft-serve --all
git push soft-serve --tags
git ls-remote --heads --tags soft-serve
```

Verify clone, fetch, branch, and tag behavior before any canonical-name
transition. Use a disposable directory outside the repository:

```bash
VERIFY_DIR="$(mktemp -d)"
git clone "ssh://${FORGE_HOST}:23231/codexify" "$VERIFY_DIR/codexify"
git -C "$VERIFY_DIR/codexify" fetch --all --tags --prune
git -C "$VERIFY_DIR/codexify" branch --all
git -C "$VERIFY_DIR/codexify" tag --list
git -C "$VERIFY_DIR/codexify" remote -v
```

Confirm that the expected branch heads and tags match the source repository,
that the admin key can read and write the repository, and that the configured
Soft Serve data root is included in VaultNode backup. Do not proceed to Phase B
until the operator has reviewed those results.

## Phase B: explicit operator-approved transition

Only after Phase A verification, and only with explicit operator approval,
change the local remote names:

```bash
git remote -v
git remote rename origin github
git remote rename soft-serve origin
git remote -v
```

The intended posture is now:

```text
origin = Soft Serve on VaultNode
github = GitHub publication and off-node redundancy remote
```

Publication remains manual and visible:

```bash
git push origin HEAD
git push github HEAD
```

The second command is an explicit publication/redundancy action. Do not add a
`pushInsteadOf` rule, multi-push URL, Git hook, background synchronizer, or
automatic remote mutation as part of this workflow.

## Backup doctrine

Treat these as separate recovery surfaces:

1. **Git repository redundancy:** GitHub preserves only refs and objects that
   were explicitly pushed to it.
2. **Soft Serve service-state backup:** back up the configured
   `CODEXIFY_SOFT_SERVE_DATA_DIR` as a unit. It is the required backup root for
   repositories, unpublished repositories, the service database, users,
   collaborator configuration, SSH host/client keys, hooks, and generated
   configuration.
3. **VaultNode host backup:** preserve the host-level Docker/operator context,
   env/config management, filesystem permissions, and recovery instructions.

GitHub does not preserve unpublished Soft Serve repositories, Soft Serve users
or collaborator configuration, service database state, SSH host keys, server
hooks, or operator configuration. A GitHub mirror is not a complete backup of
the Soft Serve service. Test restoration of the data root separately from
testing a Git clone.

## Isolation and rollback

Soft Serve is not on the default Codexify Compose graph and has no dependency
edge to Codexify services. If the forge fails, use `make soft-serve-status`,
`make soft-serve-logs`, and `make soft-serve-down`; do not alter Codexify
Compose to compensate. The default Codexify stack should be checked separately
if needed.

To stop the optional forge while preserving its state:

```bash
make soft-serve-down
```

If Phase B was completed and the operator needs to return to GitHub-first
names, verify the URLs and run the reverse manual rename:

```bash
git remote rename origin soft-serve
git remote rename github origin
```

This preserves the local data directory and does not delete unpublished forge
history. Recovery of that history requires the data-root backup or another
verified Soft Serve copy.

## What this runbook does not prove

Local Compose config validation proves syntax and interpolation only. Starting
Soft Serve proves a live local service only after the operator observes the
container and SSH checks. Neither proves GitHub synchronization, Codexify
runtime health, complete backup coverage, publication acceptance, or a wider
supported beta release.
