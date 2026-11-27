# Reconcile account presentation with main's published migration history

Lane: architecture-impact. Execution: isolated implementation and synthetic proof;
root review before merge or live operation.

This change belongs in `guardian/db/migrations/versions/` and the existing
Scout account presentation module. Chris requested removing the main/Private
Preview divergence. The onboarding tour remains paused. This task neither
transplants the serving branch nor activates held voice, private Bio, Lens or
other feature work.

Authoritative inputs are current main145e8cbf1, the reviewed profile commits
c143009f6/fe253f277/9bec5c9e6/bf36fa242, and their published migration bodies.
Main's e723 and Preview's f3 branches share ab71. Account/session authority and
explicit authored greeting remain unchanged; client identifiers and legacy
browser nicknames confer no profile authority.

Implement one no-DDL mergepoint a3f8c2d6e901 with parents e723ba9046cd and
f3a9c7d2b8e1. Preserve all existing revisions, parents, DDL and stored values.
Port only the already reviewed greeting/seven-field presentation code and its
Web/authentication tests. Preserve main's accepted-account custody column and
trigger. No new profile field, name fallback, permission scheme, settings scope
or provider activation. Do not include the separate private Bio candidate.

Acceptance requires full real PostgreSQL upgrades from empty, main e723 and
synthetic Preview f3 without stamps; authored greeting, shared/unique settings,
valid private wallpaper bytes, display data, accepted-account custody and
synthetic credential data must survive. Legacy Preview custody remains NULL,
and main custody stays immutable. Check published migration bytes, one145-file
head, focused auth/client checks and qualification projection. Synthetic proof
uses a new owned Unix-only PostgreSQL cluster with network denial/auditing and
no live rows, sessions, imports or provider calls.

Target scope: the existing Scout auth/transport and account presentation service,
models, two unchanged Preview migration files, one new mergepoint, existing Web
presentation wiring, relevant tests, narrow migration/current-state metadata,
this Task Spec and the proof record. Governing ADRs058/064/079/088/092 remain
unchanged. Release HOLD remains unchanged; qualification freshness cannot be
promoted from local tests.

Publish only a scoped draft after proof and overlap checks. No main merge,
Preview restart/migration/deployment, environment/key/access change or other
owner file mutation. Root owns ordering with any in-flight main migration and
subsequent live rollout. Report exact base/result/PR, tests and remaining gates.
