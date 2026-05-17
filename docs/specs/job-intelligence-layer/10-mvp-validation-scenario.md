# MVP Validation Scenario

This is a planning scenario.
It is synthetic.
It is not executable.
It is not a test fixture.
It is not a runtime promise.
It does not define API, prompt, schema, UI, persistence, transcription, consent, or retention behavior.

## Purpose

This document defines the first concrete validation scenario for the Job Intelligence Layer MVP.
It should answer:

- what input the system should eventually handle
- what structured draft it should eventually produce
- what a human should eventually review
- what proof would justify moving toward implementation

## Scenario Summary

Synthetic seed scenario:

- service-call intake
- plumbing-flavored example
- customer reports tub and shower fixture dripping while turned off
- fixture appears to be a three-handle tub and shower setup
- customer may not know the brand
- customer has an access panel behind the shower
- customer asks about diagnostic fee and general pricing expectations
- customer wants scheduling for a specific appointment window
- dispatcher or operator handles the human conversation
- system assists after or during the call by generating a draft Job Profile

This is a seed validation target, not a permanent domain boundary.

## Synthetic Source Interaction

```text
Operator: Thanks for calling. Can you describe what you are seeing?
Customer: The tub/shower faucet keeps dripping even when all handles are off.
Operator: Do you know what type of setup it is?
Customer: It looks like three handles, but I do not know the brand.
Operator: Any access to plumbing behind the wall?
Customer: There is an access panel behind the shower in the utility closet.
Customer: Also, do you charge a diagnostic fee, and what does repair usually cost?
Operator: We can review general pricing guidance after inspection. What appointment window works?
Customer: Tomorrow between 1 PM and 4 PM would be best.
```

## Expected Extraction Targets

A future extraction pass should identify target areas such as:

- interaction type
- service vertical
- issue summary
- raw customer description
- symptoms
- known fixture or system details
- brand known or unknown
- access notes
- urgency
- scheduling preference
- policy and pricing questions
- ambiguity and missing information
- risk and safety signals, if any
- review recommendations

These are expected target areas, not a canonical schema.

## Expected Job Profile Draft Shape

Illustrative planning-only draft shape:

```json
{
  "source": {
    "interaction_type": "service_call_transcript",
    "raw_description": "Tub/shower fixture keeps dripping while turned off; customer reports three-handle setup and unknown brand."
  },
  "customer": {
    "customer_reference": "customer_placeholder_001"
  },
  "site": {
    "site_reference": "site_placeholder_001",
    "access_notes": [
      "Access panel behind shower in utility closet."
    ]
  },
  "request": {
    "summary": "Intermittent or continuous drip from tub/shower fixture while handles are off.",
    "symptoms": [
      "Dripping while off"
    ],
    "fixture_details": {
      "configuration": "three_handle_tub_shower",
      "brand": "unknown"
    }
  },
  "classification": {
    "service_type": "plumbing",
    "category": "tub_shower_fixture_drip",
    "confidence": "medium"
  },
  "scheduling": {
    "preference": "tomorrow_1300_1600",
    "commitment_status": "not_committed"
  },
  "policy_questions": {
    "items": [
      "diagnostic_fee",
      "general_pricing_expectation"
    ]
  },
  "risk_and_safety": {
    "signals": [],
    "notes": "No immediate safety risk reported in source interaction."
  },
  "review": {
    "required": true,
    "confidence_notes": "Brand unknown; diagnosis requires inspection."
  },
  "lineage": {
    "source_interaction_id": "interaction_placeholder_001",
    "extraction_id": "extraction_placeholder_001"
  }
}
```

This JSON is illustrative only and not canonical.

## Review Expectations

A future human reviewer should verify:

- issue summary is accurate
- system type is not overstated
- brand remains unknown unless confirmed
- access notes are factual
- policy or pricing questions are not converted into price commitments
- scheduling preference is not converted into dispatch commitment
- risk and safety signals are factual and non-stigmatizing
- missing information remains visible
- corrected fields are captured in future revision history

## Lineage Expectations

Any future implementation should preserve links between:

- source interaction
- transcript or message text
- extraction result
- generated draft
- human corrections
- confirmation outcome
- superseded draft if a newer draft replaces it

This is a planning expectation only.

## MVP Proof Criteria

A future implementation should prove, for this scenario:

- source text can be submitted or loaded
- extraction output preserves raw description
- generated draft separates stated facts from inferred fields
- ambiguity and missing information remain visible
- policy and pricing questions stay separate from job symptoms
- human review can edit generated fields
- confirmation requires human action
- lineage and correction history is preserved or explicitly deferred in the implementation proof
- no customer subjective labels are generated
- no release promise is widened

## Explicit Non-Proof

This scenario does not prove:

- voice transcription
- real call recording
- consent compliance
- production customer messaging
- autonomous dispatch
- pricing automation
- route optimization
- billing automation
- multi-tenant SaaS readiness
- on-prem deployment readiness
- export and restore readiness

## Non-Goals

- no runtime implementation
- no API route
- no persistence model
- no JSON Schema file
- no prompt file
- no UI component
- no automated test
- no consent or retention policy
- no pricing policy
- no dispatch automation

## Open Questions

- Should the first executable proof use a plain text transcript input?
- Should the first executable proof use a CLI, backend helper, or dev-only route?
- Should the first review surface be a Markdown artifact, JSON artifact, or UI card?
- Which fields are required for the first proof?
- What correction-history proof is enough for MVP?
- Should validation fixtures live under docs first or tests first?
- What business vertical should be second after plumbing and service-call intake?
- What proof justifies moving from docs-only incubation to code?
