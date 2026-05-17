# Job Profile Draft Contract

This is a planning contract draft.
It is not a canonical schema.
It is not implemented.
It does not define database tables, API responses, prompt outputs, or UI behavior yet.

## Purpose

The Job Profile is the central structured artifact produced from an intake interaction.
It is intended to represent:

- what the customer said
- what the system inferred
- what the human reviewed
- what was confirmed for operational use

## Lifecycle

Conceptual draft lifecycle states:

- `draft_created`
- `needs_review`
- `reviewed`
- `confirmed`
- `rejected`
- `superseded`

These are planning terms only for this draft contract and are not canonical runtime tokens.

## Contract Shape

```json
{
  "job_profile_id": "jp_draft_0001",
  "version": 1,
  "status": "needs_review",
  "source": {
    "interaction_type": "phone_call",
    "transcript_available": true,
    "raw_description": "Customer reports water around the base of the water heater and asks if emergency service is available."
  },
  "customer": {
    "name": "Alex Rivera",
    "phone": "+1-555-0100",
    "email": "alex.rivera@example.com"
  },
  "site": {
    "address": "123 Maple Ave, Springfield, NY 10001",
    "access_notes": "Gate code required after 6 PM; dog in backyard."
  },
  "request": {
    "summary": "Possible water heater leak with active water accumulation.",
    "symptoms": [
      "Water pooling near heater",
      "Dripping sound reported"
    ],
    "known_equipment": [
      "Gas water heater"
    ]
  },
  "classification": {
    "service_type": "plumbing",
    "category": "water_heater_leak",
    "confidence": 0.74
  },
  "scheduling": {
    "preference": "same_day_if_possible",
    "constraints": [
      "Customer available after 4 PM"
    ]
  },
  "policy_questions": {
    "items": [
      "Diagnostic fee amount",
      "Warranty coverage for replacement parts"
    ]
  },
  "risk_and_safety": {
    "flags": [
      "water_active",
      "requires_ppe"
    ],
    "notes": "Customer reports active water near appliance."
  },
  "events": [
    {
      "event_type": "follow_up_required",
      "details": "Customer requested callback with ETA options.",
      "recorded_at": "2026-05-16T14:10:00Z"
    }
  ],
  "review": {
    "required": true,
    "reviewed_by": null,
    "reviewed_at": null,
    "corrections": []
  },
  "lineage": {
    "source_thread_id": "thread_123",
    "source_message_id": "msg_456"
  },
  "metadata": {
    "created_at": "2026-05-16T14:08:00Z",
    "updated_at": "2026-05-16T14:10:00Z"
  }
}
```

## Field Groups

### Source

- Captures raw intake origin and interaction context.
- Tracks transcript or message source context.
- Original customer language should be preserved when available.

### Customer

- Captures contact identity for the job.
- Must avoid durable personality judgments or subjective labels.

### Site

- Captures job location and access context.
- Safety and access notes should remain factual and concrete.

### Request

- Captures issue summary and concrete symptoms.
- Must preserve separation between raw customer description and interpreted summary.

### Classification

- Captures service type, category, and confidence as planning fields.
- Confidence is advisory and must remain human-reviewable.

### Scheduling

- Captures preferences and constraints only.
- Does not imply autonomous dispatch behavior.

### Policy Questions

- Captures questions about fees, diagnostics, pricing, warranties, or related business policy.
- Does not imply automated pricing commitments.

### Risk and Safety

- Captures factual safety or access flags.
- Must avoid stigmatizing language.
- Example flags: `access_problem`, `biohazard_observed`, `aggressive_animal_reported`, `requires_ppe`, `water_active`, `electrical_risk_reported`.

### Events

- Captures concrete event records only.
- Example events include payment issue, dispute, cancellation, follow-up requirement, access problem, and safety flag.

### Review

- Captures human confirmation state and readiness for operational use.
- Includes corrections and reviewer metadata.

### Lineage

- Captures source thread, message, or related artifact references.
- Preserves traceability from intake interaction to Job Profile.

### Metadata

- Captures timestamps and versioning surfaces for the draft artifact.

## Event and Fact Doctrine

- Store concrete events and facts, not opinions.
- Do not store subjective labels such as `difficult_customer`.
- Prefer event records like:
- `payment_issue`
- `service_dispute`
- `access_problem`
- `safety_flag`
- `follow_up_required`
- `customer_correction`
- Derived actions should be computed from evidence, not stored as personality judgments.

## Review Doctrine

- The system drafts.
- The human confirms.
- Every generated field must be editable before confirmation.
- Low-confidence classification must remain visibly reviewable in any future UI.
- Confirmed records should preserve correction history.

## Non-Goals

- No database schema
- No migration
- No API contract
- No JSON Schema file
- No prompt contract
- No UI contract
- No autonomous dispatch semantics
- No transcription retention policy
- No pricing automation

## Open Questions

- Which fields are required for first MVP?
- Which fields should be optional?
- Should draft lifecycle terms become canonical tokens later?
- Should Job Profile lineage bind to Codexify thread and message lineage or a new vertical-specific source model?
- How should revisions be represented?
- How much customer and contact data is necessary for validation without creating avoidable privacy risk?
- What proof would justify moving this from draft contract to canonical schema?
