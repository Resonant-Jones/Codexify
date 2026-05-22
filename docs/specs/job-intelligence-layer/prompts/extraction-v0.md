# Extraction Prompt v0

- This is a docs-local prompt template.
- It is not registered in runtime.
- It is not executed automatically.
- It is not a production prompt.
- It is intended for synthetic fixture experimentation only.
- It does not define canonical schema, model behavior, API behavior, persistence behavior, or UI behavior.

## Purpose

This prompt template is intended to transform service-call intake text into an extraction-shaped JSON draft for human review.

For the first synthetic plumbing fixture, it should help surface:

- directly stated facts
- inferred fields
- ambiguity
- missing information
- policy and pricing questions
- risk and safety signals
- review recommendations
- confidence notes

The output is planning-only and must preserve the separation between raw source evidence and interpreted fields.

## Prompt Template

```text
You are producing a planning-only extraction draft for a synthetic Job Intelligence fixture.

Context:
- This prompt is docs-local, manual-only, and synthetic-only.
- It is not registered in runtime.
- It is not a production prompt.
- It is not allowed to define canonical schema, runtime behavior, API behavior, persistence behavior, or UI behavior.
- Human review is required before any operational use.

Task:
- Read the intake interaction and operator notes.
- Produce one JSON object only.
- Do not include markdown, commentary, prose outside JSON, or code fences.

Input fields:
- interaction_id: {{interaction_id}}
- interaction_type: {{interaction_type}}
- source_channel: {{source_channel}}
- business_vertical: {{business_vertical}}
- source_text:
{{source_text}}
- operator_notes:
{{operator_notes}}

Output requirements:
- Return JSON only.
- Preserve raw customer language where useful inside directly stated facts.
- Keep directly stated facts separate from inferred fields.
- Use `unknown` instead of guessing when the source does not support a value.
- Mark ambiguity explicitly rather than silently resolving it.
- Keep policy and pricing questions separate from symptoms and service facts.
- Never make pricing commitments.
- Never make scheduling commitments.
- Never claim dispatch has occurred.
- Never claim that a technician has been scheduled.
- Avoid subjective customer labels.
- Avoid inferring sensitive traits.
- Treat safety, access, animal, or hazard details as factual reports only.
- Preserve event-and-fact doctrine: store concrete reported facts, questions, and review needs, not opinions or identity judgments.
- Require human review before operational use.

Return a single JSON object with this top-level shape:
- fixture_id
- fixture_kind
- source_interaction_id
- interaction_type
- service_vertical
- directly_stated_facts
- inferred_fields
- ambiguities
- missing_information
- policy_questions
- risk_signals
- review_recommendations
- confidence
- metadata

Detailed field guidance:
- `fixture_id`: the synthetic fixture identifier if known from context, otherwise `unknown`
- `fixture_kind`: a short label for the fixture lane, such as `synthetic_service_call`
- `source_interaction_id`: copy from interaction_id
- `interaction_type`: copy from interaction_type
- `service_vertical`: copy from business_vertical when directly supplied; otherwise `unknown`
- `directly_stated_facts`: factual source-backed details only, including relevant raw phrases
- `inferred_fields`: interpretations that may help draft a job profile, clearly separated from direct facts
- `ambiguities`: explicit unresolved questions, contradictions, or unclear details
- `missing_information`: information still needed before operational use
- `policy_questions`: diagnostic fee, pricing, warranty, scheduling-policy, or similar business-policy questions only
- `risk_signals`: factual reported risk or access signals only; do not invent risk
- `review_recommendations`: concrete human-review actions
- `confidence`: confidence notes for the extraction, with `high`, `medium`, `low`, or `unknown` only as review aids
- `metadata`: planning-only metadata such as source_channel, whether operator_notes were present, and reminders that the result is manual-only and synthetic-only

If the source text is incomplete, still return JSON with partial content, visible ambiguity, visible missing information, and human review required.
```

## Expected JSON Shape

This illustrative example shows the expected extraction-shaped output.
It is not a canonical schema.
Future schema work must be a separate task.

```json
{
  "fixture_id": "plumbing-three-handle-drip",
  "fixture_kind": "synthetic_service_call",
  "source_interaction_id": "interaction_placeholder_001",
  "interaction_type": "service_call_transcript",
  "service_vertical": "plumbing",
  "directly_stated_facts": {
    "raw_customer_language": [
      "The tub/shower faucet keeps dripping even when all handles are off.",
      "It looks like three handles, but I do not know the brand.",
      "There is an access panel behind the shower in the utility closet."
    ],
    "reported_symptoms": [
      "fixture dripping while off"
    ],
    "reported_access_details": [
      "access panel behind shower in utility closet"
    ],
    "reported_policy_questions": [
      "diagnostic fee",
      "general repair pricing"
    ],
    "reported_scheduling_preference": [
      "tomorrow between 1 PM and 4 PM"
    ]
  },
  "inferred_fields": {
    "service_category": "tub_shower_fixture_drip",
    "fixture_configuration": "three_handle_tub_shower",
    "brand": "unknown"
  },
  "ambiguities": [
    {
      "field": "fixture_brand",
      "reason": "customer does not know the brand"
    },
    {
      "field": "internal_failure_cause",
      "reason": "drip symptom reported without confirmed diagnosis"
    }
  ],
  "missing_information": [
    "exact site address",
    "whether drip is constant or intermittent",
    "whether shutoff or access constraints exist beyond the access panel"
  ],
  "policy_questions": [
    "diagnostic_fee",
    "general_pricing_expectation"
  ],
  "risk_signals": [],
  "review_recommendations": [
    "confirm fixture brand if visible on site",
    "confirm whether the scheduling preference is a request only and not a commitment",
    "review policy questions separately from diagnosis"
  ],
  "confidence": {
    "overall": "medium",
    "service_vertical": "high",
    "fixture_configuration": "medium",
    "diagnosis": "unknown",
    "notes": "Source clearly reports the symptom and access detail, but diagnosis and brand remain unconfirmed."
  },
  "metadata": {
    "source_channel": "phone",
    "operator_notes_present": true,
    "manual_use_only": true,
    "synthetic_only": true,
    "human_review_required": true,
    "schema_status": "illustrative_only"
  }
}
```

## Guardrails

- No subjective durable customer labels.
- No sensitive trait inference.
- No pricing commitments.
- No dispatch commitments.
- No claim that a technician has been scheduled.
- No conversion of customer emotion into customer identity.
- No retention or consent claims.
- No production customer-data use.

## Manual Use Only

- This prompt may be manually tested against the synthetic fixture text.
- Any manual result must be treated as experimental.
- No result should be persisted as operational truth.
- No result should be used with real customer data.
- Model output must be compared against fixture expectations only in future explicit tasks.

## Non-Goals

- No runtime prompt registry.
- No model call.
- No automated prompt execution.
- No API route.
- No worker.
- No persistence model.
- No database migration.
- No UI.
- No transcription pipeline.
- No consent policy.
- No retention policy.
- No pricing automation.
- No dispatch automation.
- No canonical JSON Schema.
- No canonical runtime tokens.

## Open Questions

- Should extraction v0 become a registered prompt later?
- Should model output map directly to expected extraction or through a normalization step?
- What synthetic fixture set is enough before testing real-world anonymized examples?
- Should prompt output be validated by the existing fixture validator or a future dedicated output validator?
- Which provider/model boundary is acceptable for local-first experimentation?
- What proof justifies creating automated prompt execution?
