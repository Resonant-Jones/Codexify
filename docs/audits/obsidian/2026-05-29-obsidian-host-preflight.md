# Obsidian Host Preflight

## Scope

This is a preflight note for the next Obsidian workspace-context proof. It records a host-machine setup dependency before that proof is run.

This note does not run the proof. It does not change Codexify runtime behavior, route behavior, prompt assembly, retrieval behavior, storage, UI, or release posture.

## Host Requirement

Before running the next Obsidian workspace-context proof tasks, download and install Obsidian on the host machine used for testing.

## Why This Is Required

The operator needs Obsidian installed to create or copy a local vault for proof setup.

The vault provides local markdown files for testing Codexify's `/obsidian` workspace-context flow, including slash-command activation, bounded context retrieval, and provider-visible local evidence.

This requirement is about proof setup only. Obsidian is not required for normal Codexify chat completion, and this note does not promote Obsidian integration as a new default release surface.

## Recommended Test Vault

Start with a tiny synthetic vault before using any real vault. The first proof vault should contain a few markdown files with obvious sentinel phrases that can be searched for and asserted in proof output.

Use sentinel phrases that are unique, harmless, and non-personal, such as `SENTINEL_OBSIDIAN_PREFLIGHT_ALPHA`.

Do not begin with a full personal vault. Avoid secrets, client or private material, personal journal content, sensitive attachments, credentials, API keys, and any files that should not be committed or surfaced in logs.

## Non-Goals

- Not release promotion.
- Not proof that Obsidian indexing works yet.
- Not MCP or arbitrary tool access.
- Not general command-bus activation.
- Not a runtime dependency for normal chat completion.
- Not ingestion of the user's full vault.

## Next Proof Dependency

The next proof task should verify:

- A synthetic local vault exists.
- Codexify can ingest or link the vault according to the current supported path.
- `/obsidian` activates the intended context mode.
- Injected context reaches Guardian.
- Guardian does not say it fails to recognize `/obsidian`.
- Guardian either answers from injected local evidence or honestly reports that no relevant local context was found.

## Validation

Validation for this docs-only task:

- `python3 scripts/validate_docs.py`
- `git diff --check`

No runtime tests apply because this note does not change runtime behavior.
