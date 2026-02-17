# CHUNK_CAMPAIGN_2026_02_17 Task Pack

This directory contains runnable, one-task-per-file execution units for the campaign.

## Campaign Index
- Source campaign index:
  - [`docs/Campaigns/CHUNK_CAMPAIGN_2026_02_17/CHUNK_CAMPAIGN_2026_02_17_CHUNKPAIGN.md`](../../../Campaigns/CHUNK_CAMPAIGN_2026_02_17/CHUNK_CAMPAIGN_2026_02_17_CHUNKPAIGN.md)

## How to Run Tasks
1. Pick one task file from this directory.
2. Execute the task exactly as written:
   - edit only files in that task's scope
   - run the explicit test commands in that task
   - run the explicit `git add` and `git commit` commands in that task
3. Finish and report:
   - changed files summary
   - test/check results
   - commit hash

## Run Order
1. `TASK-IR-000__incident-response-tooling.md`
2. `TASK-IR-001__precommit-secret-scanning.md`
3. `TASK-IR-002__forbidden-paths-guardrails.md`
4. `TASK-IR-003__require-secret-store-flag.md`
5. `TASK-BROKER-000__secret-broker-env.md`
6. `TASK-BROKER-001__secret-broker-keychain.md`
7. `TASK-CAP-000__capability-grant-model.md`
8. `TASK-CAP-001__capability-enforcement-vector.md`
9. `TASK-CAP-002__capability-issuance-endpoint.md`

## Notes
- Operational secret rotation/revocation is out-of-band and should be documented, not automated in code tasks.
- Keep tasks atomic: one commit per task when executed.
