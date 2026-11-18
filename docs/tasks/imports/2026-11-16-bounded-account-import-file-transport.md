# Recover account-import files larger than public ingress requests

Workflow lane: architecture-impact, aligned with existing account-owned intake.
This change belongs in `guardian/services/account_import_chunks.py` and the existing account-import HTTP/client transport.

The authorized recovery task requires complete same-job intake of an original account export whose pending MP4 exceeds a confirmed 100 MB public ingress setting. It forbids skipping/replacing bytes, deleting staging, resetting a job, bypassing authentication, parallel recoveries or claiming full record parity. A newer export contains the same oversized file. This packet implements a bounded transport extension, not a new importer or export-identity ADR.

Authority and ADR alignment:

- The existing account-owned job and canonical staged manifest remain authoritative. Parts and client metadata are transport evidence only, never ownership, account scope, conversation origin or queue authority.
- The authenticated account requests the transfer and the current human recovery task authorizes the correction. Client fields cannot choose the account. Durable bytes remain under the existing private local staging root, fenced by resolved account and job.
- ADR-016 import/origin distinctions remain intact; this does not make imported text native or model-exposable. ADR-069 release boundaries remain unchanged. No new import status, database schema, worker, queue or completion semantics is introduced. A new ADR is not required for this aligned intake implementation; independent architecture/implementation review is required before deployment.
- Completion of parts means neither queue acceptance nor processing completion. Existing `stage_files` and ordinary commit remain the only logical-file admission and queue boundaries. Canonical record and attachment coverage require separate proof.

The new owner-authenticated POST `/api/imports/openai-account/{job_id}/file-chunks` accepts multipart `chunk`, `relative_path`, `file_size`, `file_sha256`, `chunk_sha256`, `offset`, and optional `content_type`. Each accepted part is exactly the next 8 MiB window or final remainder; body bytes are bounded to 8 MiB plus 64 KiB multipart overhead even without a trustworthy Content-Length. Metadata is bounded and validated; errors come from the canonical protocol registry.

A job may have one incomplete logical file. Its normalized path, size and whole SHA-256 are pinned in private metadata. Parts live in immutable path/whole-identity directories. The job row lock protects owner/phase checks and part writes; replay must match bytes. Interrupted pending writes may append only a matching missing suffix; no truncation or completed-part overwrite is allowed. Files and containing directories are fsynced before acknowledging progress. A subsequent file may replace the active pointer only once the previous file is admitted with matching identity; old parts remain retained.

Remaining declared file/byte capacity is checked before each write; this is admission checking, not a reservation against ordinary uploads. After all parts exist, streamed assembly verifies the whole original size/SHA-256. The chunk-write row lock is released before invoking existing `stage_files`, whose fresh ownership/phase/conflict/limits and transaction remain authoritative. Parts survive failed or ambiguous admission. Already-admitted replays compare the supplied range and whole stored hash and do not rewrite canonical bytes. Concurrent final replay may exercise existing staging duplicate accounting; it must never create a second logical file or inflate uploaded file/byte totals.

The browser uses the ordinary authenticated Axios client, its existing 120-second request deadline and caller cancellation. Files above 32 MiB are sent as one logical-file transfer with 8 MiB requests; smaller batches remain unchanged. Native whole-file hashing is bounded to 128 MiB and each read/hash step to 30 seconds. Abort, local failure and timeout never trigger automatic native hash retry or a late POST. This is sufficient for the recovery sources measured in this task; it does not claim browser support for arbitrary 2 GiB files.

Private parts are deliberately retained after admission, including on lost commit/response, and may consume additional disk space. This task adds no retention cleanup or deletion. Private local storage is required; unsupported staging providers fail closed. Multiple browser origins/profiles are not fenced by Web Locks, so one recovery owner remains an operational prerequisite.

Expected files: protocol-token registry, chunk helper, migration routes, existing frontend API helper, focused service/HTTP/PostgreSQL/frontend tests, and this packet/token-contract follow-through. Preserve mainline's existing ambiguous-commit staging preservation unchanged.

Acceptance proof:

- Matching chunk replay and interrupted-write recovery preserve bytes and exact logical identity.
- Wrong owner, conflicting path/whole identity, offset, length/hash, quota exhaustion, queued phase, symlinks and unsupported storage fail closed before new canonical admission.
- Wrong assembled size/hash and final-admission failure retain every confirmed part; no auto-reset/clear/commit occurs.
- Actual streaming request bounds clean temporary multipart files; unrelated malformed multipart retains its original classification.
- A disposable two-session PostgreSQL test observes a real row-lock wait and proves serialized same-job part replay. SQLite alone is insufficient.
- Browser tests prove bounded parts, original whole identity, receipt validation, local timeout/abort and prevention of late POSTs. Existing coordinator, transport, preflight, owner-manifest and stage-preservation tests remain passing.
- Before serving changes, obtain independent final patch review, frozen artifact checksums, appropriate tests, verified mount/base comparisons, a narrowly scoped rollback copy and unchanged live job readback. A reviewed backend restart may load the additive route; no database migration is needed.
- Runtime proof must show the normal authenticated original job accepts the original oversized logical file under its original path/hash, then complete ordinary intake/commit/processing and verify source coverage. Do not infer parity from these transport tests or health.

Validation runs from the repository root: focused `pytest` chunk/service/migration/manifest/staging suites, explicitly configured disposable PostgreSQL proofs, protocol-token contract tests, focused frontend Vitest coordinator/transport/chunk/preflight/modal tests, frontend build and `git diff --check`. Record full-TypeScript baseline limitations separately. Stage task-scoped files only and commit successful reviewed corrections; publish a draft PR if needed. Leave the private source archives, account, existing job and unrelated serving changes intact.


## November 18 review correction

Canonical staging provider failures include `StorageError`/`UploadError`, not only native `OSError`. Both map to the existing chunk-storage-unavailable 503. Tests inject failure through the real staging provider, retain and compare every uploaded part, then admit the exact original logical file on replay.

A local verification deadline rejects the API operation promptly and reports a local failure. It does not cancel native Blob/WebCrypto work. That work is quarantined until settlement: direct API upload retries fail before another read, and the coordinator retains its active transfer and cross-tab Web Lock while draining native cleanup. No late completion can POST. A browser operation that never settles can therefore keep recovery quarantined indefinitely; this is an explicit ownership limit, not an advertised bounded cancellation or permission to release the lock. Closing the owning browser context terminates its native work; do not tell users to discard their job or clear site data. Genuinely terminable worker execution is a separate improvement.

The request budget is finite and size-dependent, up to the existing 70-minute ceiling. Files above 128 MiB use 8 MiB incremental whole-file SHA-256 slices. These refinements supersede the earlier fixed-120-second and 128-MiB-ceiling description above. No schema, queue, provider, release or live rollout claim changes.
