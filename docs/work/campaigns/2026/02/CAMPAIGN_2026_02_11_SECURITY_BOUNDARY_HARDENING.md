# Campaign Receipt Draft

Campaign ID: CAMPAIGN_2026_02_11_SECURITY-BOUNDARY-HARDENING
Campaign Slug: security-boundary-hardening
Campaign Type: security
Source Audit: AUDIT_2026_02_11
Source Findings: FINDING-2026-02-11-002, FINDING-2026-02-11-003, FINDING-2026-02-11-004

Objective:
- Remove exposed credentials from repository tracking.
- Enforce authenticated and ownership-scoped document and media access.

Execution Rules:
- Every task must begin with: Preflight: git status --porcelain -uall must be empty.
- Stop immediately on dirty tree or out-of-scope file changes.
- No git add or commit commands in any task.

Definition of Done:
- OAuth secret files are no longer tracked and rotation requirement is documented.
- Thread-document list endpoint requires API key auth and ownership checks.
- Media routes no longer trust caller-supplied user_id for authorization scope.