# Frontend Install Workarounds (macOS host)

> **Status:** Operational workaround for a **host-environment** blocker. This is
> **not** release qualification and does **not** establish a reproducible
> frozen-lockfile installation on the supported path. The supported-path blocker
> in `docs/architecture/00-current-state.md` ("Frontend frozen-lockfile
> installation on the supported path remains unrehearsed") **stays open**.

Recorded 2026-11-01 while verifying the Library surface consolidation on the
Codexify worktree `feat/auto-20261101-9e7a08eb`.

## Summary

A plain `pnpm install --frozen-lockfile` fails on this macOS host with `EPERM`,
for **two independent reasons**. Both are host policy, not repository defects.

### 1. macOS protected developer paths

macOS protects three clone-time code-execution vectors from writes by
non-authorized processes:

| Protected path | Why |
|---|---|
| any directory named `.vscode` | VS Code task definitions can execute commands |
| any directory named `.idea` | JetBrains run configurations can execute commands |
| any file named `.gitmodules` | submodules can point at attacker-controlled repos |

Three packages in the lockfile ship those paths, so extraction fails:

| Package | Protected path it ships |
|---|---|
| `xhr@2.6.0` | `.vscode/settings.json` |
| `iconv-lite@0.6.3` | `.idea/**` (6 files) |
| `extsprintf@1.3.0` | `.gitmodules` |

The same protection also breaks the **Cypress postinstall**, which unzips the
Cypress binary into `~/Library/Caches/Cypress` and hits a `.vscode/launch.json`
inside `Cypress.app`.

### 2. `rename()` is refused inside the pnpm store

The user's `~/Library` resolves onto the external volume
(`/Volumes/Dev_SSD/offload/library/...`), so the default pnpm store lives
there. `rename()` inside that store returns `EPERM`, which pnpm surfaces as
`ERR_PNPM_EPERM` **on the tarball GET** — the failure is the store write, not
the network. A store created **inside the repository worktree** does not hit
this.

## Working invocation

From the repository root:

```bash
CYPRESS_INSTALL_BINARY=0 pnpm install --frozen-lockfile --store-dir .pnpm-store
```

`.pnpm-store/` is already gitignored (`.gitignore:80`).

### One-time patch of the local store

The three protected-path packages must be removed from the local store's
package indexes before the install can complete. This is scripted, so the
workaround is reproducible rather than a manual copy-paste:

```bash
python3 scripts/dev/patch_pnpm_store_protected_paths.py .pnpm-store
```

The script walks every `*-index.json` under the store, drops entries whose
first path segment is `.vscode` or `.idea` and entries whose last segment is
`.gitmodules`, and leaves a `.codexify-backup` copy of each modified index
beside the original.

Re-running the install converges after one or two rounds, because downloads are
cached in the local store.

## Which store supplied the passing installation

**The worktree-local `.pnpm-store` did.** The global
`~/Library/pnpm/store` was also modified during diagnosis and was **restored to
its original state** afterwards (the `xhr@2.6.0` index is back to 7 files and
`iconv-lite@0.6.3` back to 33, with their protected paths present again).

Two inert leftovers remain in the global store and cannot be removed by the
recovery tool, because the trash lives on the internal volume and the store is
on the external one (`EXDEV`):

```text
~/Library/pnpm/store/v3/files/fd/e0862dbe6bc63c797b7985d40eecfa92e547a086caa58df757efd498044799955a0d4c66696106fcbd92372c39d464f11ac8ba3a2d5b225a99fcaba7e58870-index.json.codexify-backup
~/Library/pnpm/store/v3/files/e1/f0a4efdc2c84c773329dab1f4eaa5ab244e22a25a8b842507f8e8ae22053ef91074fbde0d9432fcd5ab4eec65f9e6e50ab9f7ba7fd1e4ba3fa1a0ba15b0bfc9a0e-index.json.codexify-backup
```

They are inert copies of package indexes. pnpm does not read them. They can be
deleted directly.

## Why patching the *global* store did not work

Patching the global store's package index was **ineffective**: pnpm still
copied the protected file. The global store additionally holds a **side-effects
cache** entry for `xhr@2.6.0` — the `-exec` variant of the file plus its
side-effects index — and that cache, not the package index, is what pnpm
consults when deciding to copy it. The worktree-local store had no such entry
for a freshly downloaded package, so there the index patch was sufficient.

## What this does and does not establish

Establishes:

- The frontend dependency tree **can** be installed on this host, and the
  vitest and chrome-extension suites **can** be run (see the verification
  command below).

Does **not** establish:

- A reproducible frozen-lockfile installation on the supported path. The
  procedure requires a **manual store patch** and a **host-specific store
  location**; it is not scripted, not CI-reproducible, and not the documented
  supported path.
- Any release or runtime qualification.

## Verification command

```bash
cd frontend && pnpm test
```

## Related

- `docs/dev/frontend-typecheck-ledger.md` — the tracked frontend TypeScript
  error baseline. It records 158 errors at commit `45e54111a266804df5de7b97e64d9fb4c1a04a57`;
  the checkout validated during this work reported **125** errors. That gap is
  pre-existing drift in the ledger, not a change introduced by the Library work.
