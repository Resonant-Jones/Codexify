# Campaign Runner MVP Spine

## Purpose
Define the first durable Campaign Runner control-plane slice that turns a user-authored goal into campaign/work-order state, records execution attempts, and exposes recommendation-only next-step guidance.

## Implemented MVP Surface
- `CampaignGoal` durable entity (`campaign_goals` table).
- `Campaign` durable entity (`campaigns` table) linked to `CampaignGoal`.
- Existing `CodingWorkOrder` durable entity remains the atomic work-order contract.
- `CampaignExecutionAttempt` durable ledger entity (`campaign_execution_attempts` table) with attempt identity separate from work-order identity.
- Campaign Runner API surface:
  - `POST /api/coding/campaign-runner/goals`
  - `GET /api/coding/campaign-runner/goals/{goal_id}`
  - `POST /api/coding/campaign-runner/campaigns`
  - `GET /api/coding/campaign-runner/campaigns/{campaign_id}`

## Execution Evidence Contract
- Execution attempts are keyed by `(run_id, attempt_id)` and can bind to `campaign_id` and `work_order_id`.
- Attempt records persist:
  - terminal status (`succeeded` / `failed` / `cancelled`)
  - validation summary payload
  - commit hash when present
  - delivery evidence (`delivery_ok`, `delivered_message_id`, `delivery_reason`)
  - source-thread lineage identifiers when available
- Worker result persistence updates work-order latest run markers when `work_order_id` is present.

## Recommendation Contract
- Next-work recommendation remains deterministic and non-dispatch:
  - `GET /api/coding/orchestrator/next`
  - Campaign detail route includes `next_recommended_work_order` derived from the same policy.
- This slice does not introduce autonomous recursive execution or silent dispatch.

## Bounded Truth Claim
- Campaign Runner MVP is a governed backend spine for:
  - campaign representation
  - attempt ledger durability
  - operator-visible recommendation inputs
- It is not a full autonomous scheduler, and it does not widen release claims beyond local supported posture.
