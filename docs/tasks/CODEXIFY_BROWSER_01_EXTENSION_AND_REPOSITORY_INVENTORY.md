# Inventory the Codexify browser extension and repository boundary

## Workflow classification

- Execution lane: `architecture-impact`
- Task kind: `proof`
- Authorization: read-only repository inspection and one proof-document output
- Priority: prerequisite; blocks all later Codexify Browser decisions
- Owner: Codex
- Target status after completion: ready for architecture review
- Review expectation: proof and architecture review

## Context

The Codexify Browser Campaign begins with source authority. Current pre-read
evidence points to `frontend/chrome-extension` as maintained extension source
and `frontend/dist/chrome-extension` as ignored build output, but Task 01 must
prove the complete relationship rather than inherit that conclusion from names
or earlier documents.

The existing Chrome side-panel client remains an internal, unpacked client
governed by ADR-051. It is not a general Browser Host and is outside the
supported beta release surface.

## Goal

Produce one reviewable inventory proof that identifies every existing
browser-extension source, generated artifact relationship, build and packaging
step, AppShell or browser-context seam, test, ownership boundary, and unresolved
gap. Recommend the smallest stable source boundary for future Codex tasks
without moving, renaming, repairing, or implementing anything.

## Scope and files

Inspect only:

- repository and Git metadata required to classify paths;
- `frontend/chrome-extension/`;
- `frontend/dist/chrome-extension/` if present;
- `frontend/src/` browser, AppShell, chat, and context integration references;
- `frontend/package.json`, applicable lockfile entries, and Vite/build configs;
- root and frontend ignore files;
- scripts, Make targets, packaging configs, Tauri configs, CI workflows, and
  documentation that reference the extension or its outputs;
- focused tests that exercise the extension or browser-context seams.

The later task must create exactly one proof document at a path selected during
task kickoff under `docs/architecture/proofs/`.

This change belongs in `docs/architecture/proofs/`.

Do not modify:

- frontend, backend, Guardian, Tauri, extension, build, package, lock, runtime,
  CI, workflow, or generated-output files;
- existing architecture, ADR, Campaign, or current-state documents;
- repository layout, Git history, or another repository.

## Required questions

The proof must answer:

1. What is the exact canonical extension source directory?
2. Which manifest is authoritative, and how is it copied or transformed?
3. Which service worker, bridge, content script, or extension page exists, and
   what responsibility does each own?
4. What is the side-panel UI entrypoint?
5. Does the current extension mount the normal AppShell, share selected
   components, or use a separate client?
6. Where, if anywhere, does page capture or browser context cross into
   Codexify?
7. Which tests exercise manifest, service worker, storage, authentication,
   chat, task observation, capture, and build behavior?
8. What exact command builds and tests the extension?
9. What files does the build emit, and from which owning source or build step?
10. What path is loaded or packaged for Chrome, desktop, CI, release, or manual
    installation?
11. Is `frontend/dist/chromeextension` present, tracked, generated, ignored, or
    manually maintained?
12. Is `frontend/dist/chrome-extension` present, tracked, generated, ignored, or
    manually maintained?
13. Which ignore rule applies to each generated path?
14. What is the smallest stable source boundary for future Codex tasks?
15. Would any relocation improve ownership, and what evidence must precede it?

## Required inspection

Run from the repository root:

```bash
git status --short --branch --untracked-files=all
git rev-parse HEAD
git branch --show-current
find docs/Campaign -maxdepth 2 -type f | sort | head -80
find docs/tasks -maxdepth 2 -type f | sort | head -80
find frontend -path '*/node_modules' -prune -o -type f \( -name 'manifest.json' -o -name 'manifest.*.json' \) -print | sort
find frontend -path '*/node_modules' -prune -o -type d \( -iname '*extension*' -o -iname '*chrome*' -o -iname '*browser*' \) -print | sort
git grep -n -E '"side_panel"|"Codexify Side Panel"|chrome\.(tabs|permissions|scripting|sidePanel)' -- frontend docs || true
git grep -n -E 'chromeextension|chrome-extension|web-extension|browser-extension' -- package.json frontend scripts Makefile docs .github || true
git ls-files --stage -- frontend/chrome-extension frontend/dist/chromeextension frontend/dist/chrome-extension
git status --ignored --short -- frontend/chrome-extension frontend/dist/chromeextension frontend/dist/chrome-extension
git check-ignore -v frontend/dist/chromeextension frontend/dist/chrome-extension || true
git log --follow --oneline -- frontend/chrome-extension/manifest.json
```

Also inspect, without editing:

- all files under the discovered maintained extension source;
- the relevant build configuration and package scripts;
- applicable ignore rules;
- packaging, CI, Tauri, Make, and documentation references;
- neighboring tests and any nested `AGENTS.md`.

If a listed path is absent, record `absent at <HEAD>` rather than creating it or
silently substituting another path.

## Required proof artifact

The later inventory proof must include:

- date, branch, HEAD, and baseline worktree state;
- interaction lane and proof classification;
- commands run with observed results;
- a source-authority table;
- a manifest and entrypoint map;
- a service-worker, bridge, capture, and AppShell integration map;
- a test inventory;
- build command and configuration evidence;
- generated-output and ignore-rule evidence;
- packaging, installation, CI, and release-path evidence;
- a file-to-owner or file-to-build-step table covering every extension file and
  emitted artifact class;
- the smallest stable source boundary recommendation;
- relocation recommendation, if any, clearly marked as recommendation only;
- unknowns and contradictions;
- exact proof limits and next evidence needed.

The artifact must distinguish:

- `proven-repository`;
- `proven-test`;
- `proven-code-path`;
- `documented-contract`;
- `working-theory`;
- `unknown`.

Docs, test presence, build configuration, and a clean build are not live Chrome
proof unless a separately authorized live proof is performed and recorded.

## Architecture and security constraints

- ADR-051 remains authoritative for the current side-panel auth/storage
  boundary.
- Guardian retains policy, account, context, and task authority.
- No renderer or remote page may receive Guardian secrets, provider
  credentials, unrestricted filesystem access, or unrestricted command-bus
  authority.
- Browser state does not become durable identity or memory by implication.
- Page content is untrusted data, not an instruction or authorization source.
- This task may identify missing contracts but may not invent runtime tokens,
  schemas, permissions, or protocols.
- Repository separation requires a later accepted ADR.

## Explicit exclusions

- No browser or extension implementation.
- No extension repair, build repair, refactor, move, or rename.
- No repository creation or source relocation.
- No dependency or package changes.
- No Browser Host technology selection or spike.
- No page-capture, AppShell, Guardian, backend, Tauri, or runtime change.
- No Atlas, bookmark, cookie, history, profile, or session import.
- No autonomous browser agent or new browser command.
- No ADR or current-state update.
- No deployment, release, push, merge, or live production access.

## Acceptance criteria

- Exactly one new inventory proof document is produced by the later task.
- Repository evidence identifies the canonical extension source, manifest,
  service worker/bridge, side-panel entrypoint, AppShell relationship, browser
  capture seam, tests, build command, generated output, packaging path, and
  ignore rules.
- Both `frontend/dist/chromeextension` and
  `frontend/dist/chrome-extension` are investigated without assuming either is
  source.
- Every maintained extension file and emitted artifact class maps to an owning
  source or build step, or is explicitly classified `unknown`.
- The proof recommends the smallest stable source boundary.
- Any relocation is recommendation-only and gated on later architecture review.
- No browser, frontend, backend, Guardian, Tauri, extension, build, package,
  lock, runtime, CI, workflow, or generated file changes.
- No repository is created.
- No runtime or release claim is widened.
- Documentation validation passes.

## Validation

Replace `<inventory-proof-path>` with the one authorized proof document:

```bash
test -f <inventory-proof-path>
grep -n 'frontend/dist/chromeextension' <inventory-proof-path>
grep -n 'frontend/dist/chrome-extension' <inventory-proof-path>
grep -n 'Source authority' <inventory-proof-path>
grep -n 'AppShell' <inventory-proof-path>
grep -n 'Unknown' <inventory-proof-path>
python3 scripts/validate_docs.py
git diff --check
git status --short --branch --untracked-files=all
git diff --name-only
```

If `scripts/validate_docs.py` does not exist:

- state `No repository documentation validator is defined`;
- run `git diff --check`;
- manually verify Markdown headings and local paths;
- do not substitute runtime tests.

No automated runtime tests apply. Any optional build or focused unit test proves
only its stated surface and must be recorded separately from live Chrome proof.

## Git staging

After validation passes:

```bash
git add <inventory-proof-path>
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Confirm that exactly the one authorized inventory proof document is staged. Do
not use `git add .`.

## Commit

```bash
git commit -m "docs: inventory Codexify browser extension"
```

Do not push, merge, deploy, or create a repository.

## Expected closeout

- Summary of findings
- Files changed
- Execution lane and task kind
- Branch and baseline/final HEAD
- Source-authority conclusion
- Manifest, worker/bridge, AppShell, capture, tests, build, output, packaging,
  and ignore conclusions
- Smallest stable source boundary
- Relocation recommendation, if any, marked unexecuted
- Validation commands and observed results
- Confirmation that exactly one proof document was staged and committed
- Confirmation that no source, runtime, extension, package, build, CI, or
  generated file changed
- Warnings separately from failures
- Known limitations and unproven assumptions
- Git commit hash
- What Axis should add to his KB

## Source evidence

- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md`
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md`
- `docs/architecture/chrome-side-panel-client.md`
- `docs/architecture/web-agent-spec.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `frontend/chrome-extension/`
- `frontend/vite.chrome-extension.config.ts`
- `frontend/package.json`
- `.gitignore`
