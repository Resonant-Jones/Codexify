# Request-Scoped Chronicle Interpretation Authorization

## Status

Implemented as an authenticated preflight contract at baseline `d0dabd159de0f322bcf9ed23728091f9bfc488ca`. This is local implementation evidence only; release posture remains HOLD.

## Request contract

`POST /api/imports/history/chronicle/authorization-check` is hosted by the existing migration router and remains subject to `CODEXIFY_ENABLE_MIGRATION_ROUTES`. It uses the same `_history_inspection_principal` dependency as imported-history inspection, preserving purpose-bound account sessions and rejection of guests, operator credentials, mixed principals, and client identity hints.

The request names one canonical Project, one to twenty unique thread IDs, explicit OpenAI and/or Anthropic origins, purpose `migration_chronicle_preview`, strict boolean `interpretation_consent: true`, an explicit import treatment, the existing bounded evidence limits, and a pagination offset. Extra fields are forbidden. The accepted treatment values are request-local typed choices: only `recallable_archive` can pass this preflight; `archive_only` and `continuity_scaffold` are denied. These values do not add a durable protocol vocabulary or persistence state.

The positive response confirms `authorized: true` and echoes the exact bounded scope. It returns no excerpt, grant, receipt, or bearer token. Rejected requests use content-free responses and the route sets `Cache-Control: no-store` on success and failure.

## Positive authorization requirements

The authenticated account must own the Project through `projects.user_id`; legacy ownership conflicts deny. Each selected thread must have the same canonical owner and Project, a selected imported origin, and ordinary thread-read authority. The explicit treatment and interpretation consent must be present in the same request. The evidence reader must independently find message-level imported provenance within the requested bounded page; a thread origin marker alone is insufficient.

The immutable internal decision binds the exact `RequestUserScope` object, canonical account, Project, ordered thread and origin selection, `InspectionLimits`, offset, purpose, treatment, exclusion decisions, and request-only lifetime. It is held only in the current call stack and is not serialized, stored, cached, queued, signed, or attached to inference work.

## Exclusions and unresolved limits

The service resolves canonical Project ownership and the persisted thread flags `is_diary`, `diary_mode`, `exclude_from_identity`, and `modeling_excluded`. Any true flag denies interpretation while leaving ordinary owner inspection as governed by the separate reader. `Project.identity_depth`, `UserSettings.allow_sensitive_modeling`, `UserSettings.memory_mode`, and `diary_requires_unlock` are not interpretation authority.

At this baseline there is no persisted Project import-treatment preference, complete continuity exclusion resolver, or message-level sensitivity classifier. The request's explicit recallable-archive selection applies only to this invocation and fills no missing durable preference. The preflight does not certify arbitrary messages as safe for model use. A future generator must resolve all required restrictions at consumption time and fail closed when a required state is unknown or ambiguous. It must obtain fresh authorization and independently recheck evidence; a prior preflight does not survive changes to ownership, exclusions, or evidence. No atomic revocation guarantee across model handoff is established here.

## No-model and no-write boundaries

This operation performs no inference, provider access, context assembly, continuity compilation, Chronicle generation, memory creation, activation, queueing, or external connector call. Canonical PostgreSQL reads use read-only transactions. The evidence reader may transiently assemble bounded excerpts to validate message-level provenance; the authorization service discards that result and sends no content to a provider or to the HTTP caller. There are no writes to permissions, preferences, Projects, threads, history, or derived state.

## Proof limits

The PostgreSQL-backed HTTP regression proves request authentication, exact account/Project/thread scope, thread-flag exclusions, treatment/consent denial, bounded response shape, no-store behavior, and unchanged database snapshots for the exercised fixtures. It does not prove production runtime qualification, a complete continuity exclusion resolver, safe model exposure, Chronicle quality, or atomic revocation during a later provider handoff.
