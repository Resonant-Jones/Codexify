# Prompt and Pipeline Contract

This is a planning contract.
It is not implemented.
It does not create runtime prompt files.
It does not define model behavior, API behavior, worker behavior, UI behavior, persistence behavior, or canonical token behavior.
It defines the intended decomposition of a future Job Intelligence Layer processing pipeline.

## Purpose

The future pipeline should transform raw intake text into a reviewable Job Profile draft through small, inspectable passes.

The pipeline should prioritize:

- preservation of raw customer language
- explicit uncertainty
- separation of stated facts from inferred fields
- human review before operational use
- lineage from source text to generated draft
- portability across intake-heavy business verticals

## Pipeline Shape

```text
source intake
-> intake sanitation/preflight
-> extraction pass
-> classification pass
-> ambiguity pass
-> policy-question pass
-> risk/safety pass
-> draft assembly pass
-> review-prep pass
-> human review gate
```

This is a planning sequence only.
No runtime processor exists.
Future implementation may combine or split passes if proof requires it, but it must preserve the same reviewable semantics.

## Pass Responsibilities

### Intake sanitation/preflight

- verifies input exists
- strips no meaning-bearing content
- identifies obvious empty or unusable input
- does not redact or retain data because retention and redaction policy is deferred

### Extraction pass

- extracts directly stated facts
- preserves raw descriptions
- marks unknowns

### Classification pass

- proposes service vertical and category
- includes confidence
- avoids overstating uncertain details

### Ambiguity pass

- identifies contradictions, missing fields, and unclear statements
- produces review recommendations

### Policy-question pass

- separates diagnostic fees, pricing, warranties, scheduling policy, and business-policy questions from job symptoms
- avoids price commitments

### Risk/safety pass

- identifies factual reported risks
- avoids stigmatizing language
- avoids subjective customer labels

### Draft assembly pass

- assembles a Job Profile draft from prior pass outputs
- preserves source and inference boundaries

### Review-prep pass

- highlights low-confidence fields, ambiguities, missing information, and fields needing explicit human attention

## Conceptual Pipeline Input

```json
{
  "interaction_id": "interaction_placeholder_001",
  "source_channel": "phone",
  "interaction_type": "service_call_transcript",
  "source_text": "The tub faucet keeps dripping after all handles are turned off.",
  "received_at": "2026-05-17T14:30:00Z",
  "known_context": {
    "business_vertical": "plumbing",
    "existing_customer_id": "customer_placeholder_001",
    "existing_site_id": "site_placeholder_001"
  },
  "operator_notes": "Customer asked about diagnostic fee and requested an afternoon window."
}
```

This is not an API contract.
This is not a schema.

## Conceptual Pipeline Output

```json
{
  "pipeline_run_id": "pipeline_run_placeholder_001",
  "source_interaction_id": "interaction_placeholder_001",
  "passes": {
    "preflight": {
      "status": "ok"
    },
    "extraction": {
      "stated_facts": {
        "raw_description": "The tub faucet keeps dripping after all handles are turned off."
      }
    },
    "classification": {
      "service_type": "plumbing",
      "category": "fixture_leak",
      "confidence": "medium"
    },
    "ambiguity": {
      "items": [
        "brand_unknown",
        "exact_internal_failure_unknown"
      ]
    },
    "policy_questions": {
      "items": [
        "diagnostic_fee",
        "general_pricing_expectation"
      ]
    },
    "risk_and_safety": {
      "signals": []
    },
    "draft_assembly": {
      "status": "assembled"
    },
    "review_prep": {
      "requires_attention": true
    }
  },
  "job_profile_draft": {
    "status": "needs_review",
    "source": {
      "raw_description": "The tub faucet keeps dripping after all handles are turned off."
    },
    "request": {
      "summary": "Reported tub fixture drip while off."
    }
  },
  "review_packet": {
    "requires_review": true,
    "attention_fields": [
      "classification.category",
      "request.summary"
    ],
    "missing_information": [
      "fixture_brand",
      "exact_access_constraints"
    ],
    "low_confidence_fields": [
      "classification.category"
    ],
    "policy_questions": [
      "diagnostic_fee",
      "general_pricing_expectation"
    ],
    "human_action_recommendation": "review_and_edit_before_confirmation"
  },
  "lineage": {
    "source_interaction_id": "interaction_placeholder_001",
    "extraction_reference": "extraction_placeholder_001",
    "draft_reference": "job_profile_draft_placeholder_001"
  },
  "metadata": {
    "created_at": "2026-05-17T14:31:00Z",
    "planning_contract_version": "draft_v1"
  }
}
```

This is illustrative only.
This is not canonical.
This is not implemented.

## Docs-Local Prompt Template Note

A docs-local extraction prompt template now exists at `prompts/extraction-v0.md`.
It is manual-only, synthetic-only, and not registered in runtime.
It does not call a model and does not define canonical schema or runtime behavior.

A docs-local manual extraction-output sample now exists at
`fixtures/plumbing-three-handle-drip/manual-extraction-output-v0.json`.
It can be validated by the extraction-output validator, but it is not automated
prompt execution, not model-quality proof, and does not define canonical schema
or runtime behavior.

## Prompt Design Rules

- prompts must be narrow and pass-specific
- prompts must prefer `unknown` over guessing
- prompts must not convert customer emotion into durable customer identity
- prompts must not infer sensitive traits
- prompts must not make pricing commitments
- prompts must not make scheduling commitments
- prompts must not claim dispatch has occurred
- prompts must preserve policy questions separately
- prompts must expose uncertainty for review
- prompts must return structured output suitable for validation
- prompts must be testable against synthetic scenarios before real customer data

## Output Validation Expectations

The deterministic extraction-output validator now exists at
`scripts/job_intelligence/validate_extraction_output.py`.
It validates extraction-shaped JSON artifacts for shape and safety invariants
and can be used against docs-local expected extraction artifacts or future
manual prompt-output artifacts.

The deterministic extraction-output comparison helper now exists at
`scripts/job_intelligence/compare_extraction_outputs.py`.
It validates both artifacts before comparison and compares docs-local expected
extraction artifacts against manual extraction samples at field level.

These helpers do not execute prompts, call a model, perform semantic scoring,
define a canonical schema, prove extraction quality, or prove production
readiness.

At planning level, future output validation should check:

- required planning fields are present
- raw description is preserved
- inferred fields are marked separately from stated facts
- confidence and uncertainty is present for inferred fields
- missing information is visible
- policy questions are not mixed into job symptoms
- risk and safety flags are factual and non-stigmatizing
- no subjective customer labels are generated
- review is required before confirmation

No canonical schema is created by this document.

## Failure and Degraded Output Handling

Planning expectations:

- empty input should fail closed as unusable
- low-quality input should produce a partial draft plus review needs
- contradictory input should produce ambiguity notes
- model-invalid output should not become a Job Profile draft
- if a pass fails, downstream assembly should not silently invent missing fields
- failed or partial passes should remain visible in future proof surfaces

## Provider and Model Boundary

- no provider or model is selected by this contract
- local vs cloud model boundary remains deferred
- voice and transcription model selection remains deferred
- latency requirements are not proven
- future provider decisions must respect current Codexify local-first supported reality unless a separate architecture-impact task changes that posture

## Relationship to Flow Builder

- this pipeline resembles an elicitation and extraction workflow
- future implementation may reuse or inform Flow Builder concepts
- this document does not claim Flow Builder runtime support
- any binding to Flow Builder must be a separate architecture-impact task

## Non-Goals

- no prompt files
- no model selection
- no prompt registry
- no API route
- no worker
- no persistence model
- no database migration
- no UI implementation
- no executable fixture
- no automated test
- no canonical JSON Schema
- no canonical runtime tokens
- no transcription consent policy
- no retention and redaction policy
- no pricing automation
- no dispatch automation

## Open Questions

- Which pass should be implemented first for a proof?
- Should the first proof use one prompt or multiple pass-specific prompts?
- Should draft assembly be model-generated, deterministic, or hybrid?
- Should validation occur after every pass or only after draft assembly?
- Should extraction output map directly into Job Profile draft fields or through an intermediate normalized shape?
- What synthetic fixture set is enough before using real examples?
- What model and provider boundary is acceptable for a local-first proof?
- Should this become a Flow Builder-compatible workflow later?
- What proof justifies creating actual prompt files?
