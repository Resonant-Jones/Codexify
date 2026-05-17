# Human Review Gate Contract

This is a planning contract.
It is not implemented.
It does not define runtime UI behavior, API behavior, database behavior, or canonical token behavior.
It defines the intended boundary between generated draft data and confirmed operational record data.

## Purpose

The human review gate exists to prevent generated extraction output from becoming operational truth without operator confirmation.

It should protect:

- customer trust
- operational accuracy
- safety and access notes
- policy and pricing interpretation
- lineage and correction history
- future auditability

## Review Boundary

Conceptual boundary:

- Before review: Job Profile draft is generated, uncertain, and non-operational.
- During review: human can inspect, edit, reject, or confirm fields.
- After confirmation: confirmed record may become operationally usable in a future implementation.

This is a conceptual boundary only.
No runtime state machine is introduced in this task.
Status terms here are planning terms only.

## Conceptual Review States

- `pending_review`
- `in_review`
- `changes_requested`
- `confirmed`
- `rejected`
- `superseded`

These are not canonical runtime tokens.
If implemented later, canonicalization must follow runtime token discipline.

## Required Review Surface

At minimum, a future review surface should allow a human to inspect and edit:

- raw customer language
- generated summary
- extracted facts
- inferred fields
- ambiguities
- missing information
- risk and safety signals
- policy and pricing questions
- scheduling preferences
- lineage and source references
- confidence and uncertainty notes

## Field-Level Review Rules

- Every generated field must be editable before confirmation.
- Raw source text must remain visible or recoverable during review.
- Inferred fields must be visually distinguishable from directly stated facts in any future UI.
- Low-confidence fields must require explicit attention.
- Safety and access fields must remain factual and non-stigmatizing.
- Policy and pricing questions must not become price commitments.
- Scheduling preferences must not become dispatch commitments.
- Human corrections must supersede generated values.
- Confirmed records should preserve generated value, correction value, reviewer, and timestamp in a future revision model.

## Correction Record Planning Shape

Planning-only correction record shape:

```json
{
  "correction_id": "corr_0001",
  "job_profile_id": "jp_draft_0001",
  "field_path": "request.summary",
  "generated_value": "Possible leak under kitchen sink.",
  "corrected_value": "Confirmed drain backup with visible leak under sink cabinet.",
  "correction_reason": "Operator clarified issue after follow-up question.",
  "reviewed_by": "operator_01",
  "reviewed_at": "2026-05-17T13:20:00Z",
  "source_reference": {
    "interaction_id": "intake_0001",
    "source_message_id": "msg_789"
  }
}
```

This is not a schema and is not implemented.

## Review Outcomes

Planning-only outcomes:

- confirm draft as operationally usable
- reject draft
- request more customer information
- mark unresolved ambiguity
- supersede with a newer draft
- defer until human call-back

None of these outcomes trigger runtime automation yet.

## Safety and Memory Doctrine

- Store concrete events and facts, not opinions.
- Avoid subjective labels such as `difficult_customer`.
- Use factual review notes such as:
- `customer_disputed_fee`
- `access_blocked`
- `payment_follow_up_required`
- `safety_condition_reported`
- `customer_requested_callback`
- Do not infer sensitive traits.
- Do not convert tone or frustration into durable customer identity.
- Keep future customer-memory behavior explicitly consent and policy bound.

## Lineage and Audit Expectations

Any future implementation should preserve:

- source interaction reference
- extraction result reference
- generated draft values
- human corrections
- reviewer identity or operator identifier
- review timestamp
- final review outcome
- supersession relationship if a draft replaces an earlier draft

This is a future expectation and not current runtime behavior.

## Non-Goals

- No UI implementation
- No API route
- No persistence model
- No database migration
- No canonical status tokens
- No pricing automation
- No dispatch automation
- No transcription retention policy
- No customer-memory implementation
- No compliance claim

## Open Questions

- Which fields must be reviewed explicitly for the first MVP?
- What confidence threshold should require attention?
- Should review states become canonical tokens later?
- Should correction history be stored inline or as separate revision records?
- How should reviewer identity work in single-user vs multi-operator deployments?
- What review proof is required before persistence?
- What minimum UI is enough to validate the concept?
- How should rejected or superseded drafts be retained or purged?
