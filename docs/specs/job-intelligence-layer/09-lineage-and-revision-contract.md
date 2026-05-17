# Lineage and Revision Contract

This is a planning contract.
It is not implemented.
It does not define database tables, API behavior, UI behavior, export behavior, restore behavior, or canonical tokens.
It defines the intended traceability expectations for future Job Profile drafts, reviews, corrections, confirmations, and supersessions.

## Purpose

Job Intelligence Layer needs lineage and revision discipline so a future confirmed Job Profile can answer:

- where it came from
- what source interaction seeded it
- what the system extracted
- what the human changed
- what became confirmed
- what later superseded it, if anything

## Core Traceability Rule

- A confirmed operational record must never be disconnected from its source interaction and review history.
- Generated values, human corrections, and confirmed values must remain distinguishable.
- Silent loss of source, correction, or supersession context is not allowed in any future implementation.

This is a planning rule, not current runtime behavior.

## Conceptual Lineage Chain

```text
source interaction
-> transcript/message text
-> extraction result
-> Job Profile draft
-> human review corrections
-> confirmed operational record
-> later revision or supersession, if any
```

Not every step exists today.
This chain is the target conceptual sequence for future implementation planning.

## Lineage Reference Shape

Planning-only lineage reference shape:

```json
{
  "lineage_id": "lineage_0001",
  "job_profile_id": "jp_0001",
  "source": {
    "interaction_id": "intake_0001",
    "interaction_type": "phone_call_transcript",
    "source_thread_id": "thread_123",
    "source_message_id": "msg_456",
    "source_artifact_id": "artifact_789",
    "transcript_reference": "transcript_ref_001"
  },
  "extraction": {
    "extraction_id": "extract_0001",
    "extraction_version": "draft_v1"
  },
  "draft": {
    "draft_id": "draft_0001"
  },
  "review": {
    "review_id": "review_0001"
  },
  "confirmation": {
    "confirmed_record_id": "confirmed_0001"
  },
  "supersession": {
    "supersedes_job_profile_id": null,
    "superseded_by_job_profile_id": null
  },
  "metadata": {
    "created_at": "2026-05-17T14:00:00Z",
    "updated_at": "2026-05-17T14:30:00Z"
  }
}
```

This is not a schema and is not implemented.

## Revision Record Planning Shape

Planning-only revision record shape:

```json
{
  "revision_id": "rev_0002",
  "job_profile_id": "jp_0001",
  "revision_number": 2,
  "revision_type": "human_correction",
  "changed_fields": [
    "request.summary",
    "scheduling.preference"
  ],
  "reason": "Operator clarified customer intent and availability window.",
  "changed_by": "operator_01",
  "changed_at": "2026-05-17T14:35:00Z",
  "source_reference": {
    "interaction_id": "intake_0001",
    "review_id": "review_0001"
  }
}
```

Example `revision_type` values such as `human_correction`, `customer_update`, `operator_note`, `supersession`, and `system_reprocess` are planning labels only.
They are not canonical runtime tokens.

## Generated vs Corrected vs Confirmed Values

Required future distinction:

- `generated_value`: produced by extraction or inference
- `corrected_value`: changed by human reviewer
- `confirmed_value`: accepted for operational use
- `source_value`: raw customer language or source text when applicable

Future implementation should preserve enough value history to explain why the confirmed record says what it says.
Human corrections must supersede generated values for operational use.
Generated values should remain available for audit or evaluation where policy allows.

## Supersession Rules

Planning-only supersession doctrine:

- a newer draft or confirmed record may supersede an earlier one
- supersession must be explicit
- superseded records should not be silently deleted
- supersession should preserve a reason
- supersession should preserve source and reviewer context
- future cleanup or retention policy must be explicit before deletion behavior exists

## Source and Transcript Handling

- Source text should be referenced, not blindly duplicated everywhere.
- Raw customer language should remain recoverable during review when policy allows.
- Transcription and audio retention is deferred.
- Consent and retention policy is deferred.
- Redaction requirements are deferred.
- Future implementation should avoid retaining more sensitive data than necessary.

## Export and Restore Considerations

If Job Profiles become durable entities later, their source, revision, correction, and supersession relationships must be explicit enough to support export and restore reasoning.
This document does not add Job Profiles to the export or restore contract.
Any future inclusion in export or restore must be handled as a separate architecture-impact task.

## Identity and Memory Boundaries

- Job Profile lineage must not become durable personality judgment.
- Customer-related memory must remain event and fact based.
- Do not infer sensitive traits.
- Do not convert tone, frustration, or anxiety into customer identity.
- Business-operational events may be retained only as factual records under future policy.
- Examples of acceptable event references:
- `payment_follow_up_required`
- `customer_requested_callback`
- `access_blocked`
- `safety_condition_reported`
- `service_dispute_recorded`

## Non-Goals

- No database schema
- No migration
- No API contract
- No UI contract
- No JSON Schema file
- No prompt contract
- No export and restore update
- No retention policy
- No transcription consent policy
- No canonical token registry
- No runtime behavior

## Open Questions

- Should Job Profile lineage bind directly to Codexify thread and message lineage?
- Should Job Profile lineage have its own vertical-specific source model?
- Which lineage fields are required for the first MVP?
- Should revision records be append-only?
- How should rejected drafts be retained or purged?
- How should redaction work for source transcript text?
- What proof is required before lineage becomes a runtime contract?
- How would Job Profiles participate in account export and restore if implemented?
- What retention policy is acceptable for transcripts versus extracted structured fields?
