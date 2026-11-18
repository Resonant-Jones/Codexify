# Close account-import recovery review gaps

Workflow lane: architecture-impact, aligned with ADR-016 continuity governance and ADR-069 runtime support boundaries. This is a client recovery safety correction, not an immutable server export declaration or a release qualification.

The authenticated server job and staged manifest remain authoritative for ownership, phase, admitted bytes and commit. Browser selection metadata is continuity evidence only. No migration, canonical data rewrite, worker or provider change is authorized by this patch.

New browser imports hash all normalized paths, sizes and original file contents before job creation. Only the domain-separated SHA-256 aggregate, source, server origin/API path and ordinary job checkpoint are retained locally before upload. Resume compares this complete selection fingerprint before transmitting any missing file, then independently verifies the owner-scoped staged manifest. Same-size changes and renamed pending paths fail closed. The browser digest is not a server-enforced declaration, source-account certificate, account authority, full archive parity receipt or protection against modified clients.

Legacy receiving jobs have no historical declaration for unstaged bytes. No retrospective digest can prove that missing identity. Automatic continuation is blocked while the existing job and staged bytes remain retained for separately verified recovery; the UI does not instruct users to delete, abort or discard those jobs. This compatibility limit is explicit, and this change is not deployed by merging it.

The modal restores and pins the canonical receiving source. A known server mismatch blocks lookup/transfer and retains its checkpoint. A resume/status 404 archives the exact browser checkpoint under `cfy.accountImport:unavailable:v1` before clearing only its active reference. If archival fails, the reference is retained. No server deletion or automatic replacement import occurs. Older checkpoints without server metadata cannot retroactively identify their origin; owner-scoped server lookup remains required.

Validation: coordinator, modal and transport regression tests, production build, qualification projection/contracts, docs validation and diff check. Obtain review of the final patch and current-head CI before merging. Preserve all source exports, receiving jobs, original browser state and live Preview data. Live imports, PDF indexing, provider spend and serving rollout are outside this PR follow-up.
