# Public Portal Snapshot Workflow

This document defines the snapshot-based release flow for Codexify's public
Publishing Portal.

The goal is to keep the private Source Vault as the canonical development
repository while publishing only curated, stable snapshots into a separate
public repo.

## Intent

- Keep private work private.
- Publish only stable snapshots.
- Avoid broadcasting every edit to the public repository.
- Avoid copying internal branches, experiments, or unfinished work.

## Repo Roles

### Source Vault

The Source Vault is the private development repository.

It contains:

- active feature work
- unfinished experiments
- private notes
- internal branches
- sensitive artifacts
- history that should not be exposed publicly

### Publishing Portal

The Publishing Portal is the public repository.

It contains:

- a curated public README
- security and contribution guidance
- public install and release documentation
- the public handoff bundle
- release artifacts that are safe to publish

## Directory Strategy

The Source Vault maintains a `Public-Directory/` staging tree.

That tree is:

- ignored by git in the private repo
- rebuilt on demand
- designed to be copied into a fresh public repo
- limited to public-safe release material

This means the public repo is a snapshot, not a mirror of the live working tree.

## Workflow

### 1) Rebuild the public staging tree

Run:

```bash
make public-export
```

This regenerates `Public-Directory/` from the current private repo using the
public-safe allowlist.

### 2) Sync the snapshot into the public repo

Run:

```bash
make public-sync target=/path/to/Publishing-Portal
```

This copies the full staged tree into the fresh public repository in one step.

### 2b) Publish and push in one step

Run:

```bash
make public-publish target=/path/to/Publishing-Portal
```

This refreshes `Public-Directory/`, updates the public repo from its tracked
`origin/main`, syncs the snapshot, commits any changes, and pushes them.

### 3) Commit the public snapshot

Inside the public repo:

- review the snapshot
- commit the change
- tag or release it if desired

## What Gets Copied

The current public staging tree includes:

- `README.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `.gitignore`
- `.env.example`
- `docs/public/`
- `releases/Codexify-Beta/`
- `docker/`
- `dist/`

The public handoff bundle currently lives at:

```text
releases/Codexify-Beta/
```

That bundle includes:

- `README.md`
- `AUTHORIZATION.md`
- `.env.example`
- `docker-compose.yml`

## What Does Not Get Copied

The public sync intentionally excludes:

- private branches
- unfinished experiments
- personal or sensitive data
- internal debug artifacts
- source-vault-only notes
- local runtime state
- any other non-release work that is not explicitly curated

## Release Rhythm

The public repo is intended to be updated on a controlled cadence, such as:

- weekly when velocity is high
- monthly when changes are slower

The key requirement is that publication is intentional, not automatic.

## Operational Notes

- `Public-Directory/` is ignored in the private repo.
- The export step rebuilds the directory from source each time.
- The sync step is a simple file copy into the public repo.
- This is a snapshot workflow, not a live bidirectional mirror.
- Git history and branches are not copied by the export/sync flow.

## Safety Boundary

If a file is not safe to publish, it should stay in the Source Vault.

If a file is safe but not useful to a public reader, it should probably stay in
the Source Vault as well.

The Publishing Portal should feel complete enough to use, but not reveal the
unfinished development process behind it.
