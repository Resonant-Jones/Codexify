# Extraction Pass Contract

This is a planning contract.
It is not a runtime prompt.
It is not a canonical schema.
It is not implemented.
It does not define API behavior, model behavior, worker behavior, or UI behavior.

## Purpose

The extraction pass is intended to convert raw intake text into a structured draft suitable for a future Job Profile review flow.

The pass should identify:

- customer-provided facts
- inferred job details
- unanswered questions
- uncertainty
- review needs

## Input

Conceptual planning input shape:

```json
{
  "interaction_id": "intake_0001",
  "interaction_type": "phone_call_transcript",
  "source_text": "My kitchen sink has been backing up for two days and water is leaking under the cabinet.",
  "transcript_available": true,
  "source_channel": "phone",
  "received_at": "2026-05-16T16:45:00Z",
  "known_context": {
    "business_vertical": "plumbing",
    "existing_customer_id": null,
    "existing_site_id": null,
    "operator_notes": "Caller asked if emergency after-hours response is possible."
  }
}
```

This shape is planning-only and is not an API contract.

## Output

Conceptual planning output shape:

```json
{
  "extraction_id": "extract_0001",
  "source_interaction_id": "intake_0001",
  "extracted_fields": {
    "raw_description": "My kitchen sink has been backing up for two days and water is leaking under the cabinet.",
    "symptoms": [
      "sink backing up",
      "water leaking under cabinet"
    ],
    "urgency_phrase": "two days"
  },
  "inferred_fields": {
    "service_type": "plumbing",
    "category": "drain_or_leak_issue",
    "possible_risk_flags": [
      "water_active"
    ]
  },
  "ambiguities": [
    {
      "field": "exact_leak_source",
      "reason": "caller reported leak area but not confirmed origin"
    }
  ],
  "missing_information": [
    "full_service_address",
    "site_access_constraints",
    "equipment_brand_or_model"
  ],
  "risk_signals": [
    "water_active",
    "after_hours_urgency"
  ],
  "policy_questions": [
    "after_hours_service_fee"
  ],
  "review_recommendations": [
    "confirm exact leak source",
    "confirm service address",
    "confirm urgency and scheduling window"
  ],
  "confidence": {
    "overall": "medium",
    "service_type": "high",
    "category": "medium",
    "urgency": "low"
  },
  "metadata": {
    "created_at": "2026-05-16T16:46:30Z",
    "planning_contract_version": "draft_v1"
  }
}
```

The output must distinguish directly stated facts, inferred fields, uncertain fields, missing fields, and review needs.

## Extraction Rules

- Preserve raw language when useful.
- Do not overwrite raw description with interpreted summary.
- Prefer `unknown` over guessing.
- Use confidence values only as review aids.
- Mark ambiguity explicitly.
- Do not make pricing commitments.
- Do not make scheduling commitments.
- Do not create subjective customer labels.
- Do not infer sensitive traits.
- Treat safety and access details as factual observations or customer reports.
- Surface policy questions separately from job symptoms.

## Ambiguity Handling

Ambiguity should be represented as explicit reviewable entries when intake details are unclear.

Examples:

- unclear service type
- unknown brand or equipment
- unclear urgency
- uncertain location or access
- customer asking policy or pricing questions
- contradictory details

Ambiguous fields should become review recommendations, and ambiguity should never be silently converted into confirmed truth.

## Confidence Guidance

Planning-only confidence bands:

- `high`
- `medium`
- `low`
- `unknown`

These are draft planning terms and are not canonical runtime tokens yet.

Guidance:

- `high`: directly stated or strongly supported by source text
- `medium`: likely interpretation but still reviewable
- `low`: weak inference or partial signal
- `unknown`: unavailable, missing, or unclear

## Risk Signal Guidance

Factual risk-signal examples:

- `active_leak_reported`
- `water_active`
- `electrical_risk_reported`
- `access_problem`
- `requires_ppe`
- `biohazard_reported`
- `aggressive_animal_reported`
- `after_hours_urgency`
- `payment_issue_reference`
- `prior_dispute_reference`

These are draft planning labels, not canonical runtime tokens. If implemented later, canonicalization must follow runtime token discipline.

## Human Review Requirements

- Every generated field must be editable.
- Low-confidence fields must be surfaced.
- Ambiguities must be visible.
- Corrections should be preserved in future revision history.
- Human confirmation is required before a Job Profile becomes operationally usable.

## Non-Goals

- No prompt implementation
- No model selection
- No transcript storage policy
- No transcription consent policy
- No pricing automation
- No scheduling automation
- No API route
- No persistence model
- No UI contract
- No canonical token registry

## Open Questions

- Should extraction become a reusable Flow Builder step later?
- Should extraction output map directly into Job Profile draft fields or through an intermediate normalization shape?
- Which fields are required for the first validation target?
- What threshold should require human review?
- Should confidence values become canonical tokens later?
- How should extraction corrections feed future evaluation?
- How should source text be retained, redacted, or excluded?
