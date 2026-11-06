# Human qualification sessions — operator runbook

This runbook covers the **operator preparation** for the `onboarding-and-people` human
qualification. The session procedure, the metrics, the blocking criteria and the PASS gate are
defined by the rubric itself:

```text
docs/qualification/rubrics/onboarding-and-people.md
```

This document does not restate or weaken them. It answers the three questions the rubric
deliberately leaves to the operator: **which runtime**, **which accounts**, and **what to ask the
testers for**.

## 1. Preconditions

Do not start sessions until both are true.

- **A stable candidate revision is named.** The rubric requires the evidence to be tied to the
  tested commit and runtime profile. Record both before the first session starts. A candidate
  that changes mid-qualification invalidates the sessions: the evidence then describes a
  revision that is not the one it claims.
- **The runtime is up and healthy**, and the tester accounts are provisioned and can log in.

## 2. Which runtime

The `onboarding-and-people` rubric scopes itself to *authenticated private-preview /
friends-and-family accounts*, and the friends-and-family tester runtime is the vehicle for that:

```text
docs/Ops/friends-family-tester-runtime.md
```

That runtime is a **separate stack** from the Private Preview, with its own project name, its own
`.env.tester`, and its own lifecycle. Keep the two apart:

- the **tester runtime** is where humans are qualified;
- the **Private Preview** (`codexify_private_preview`) is a live surface and is **not** a
  qualification environment. Do not run human sessions against it, and do not treat a healthy
  Private Preview as evidence for this rubric.

### State of the tester runtime as of 2026-11-06

```text
codexify_tester containers running : 0
.env.tester last modified           : 2025-09-15
```

The runtime is **not currently running**, and its env file predates this candidate by months. Two
things need the operator's attention before a session can start, and neither is agent work:

1. **Bring the runtime up** with the documented lifecycle commands. The env file carries a
   Tailscale auth key and secrets from its last start; a key or secret that has since expired
   will fail the bring-up rather than the sessions, and the fix is a fresh
   `scripts/ops`-documented secret rotation.
2. **Confirm the testers can reach it.** Access is by tailnet FQDN from the tester's own Tailscale
   client:

   ```text
   https://codexify-test.<your-tailnet>.ts.net
   ```

   Verify the FQDN resolves and the page loads **before** the session window, not during it.

Two provisioning commands exist and they belong to different runtimes. Using the wrong one is a
real trap — the older command belongs to the allowlist-driven Private Preview contract and is
intentionally isolated from the tester runtime:

```sh
# friends-and-family tester runtime (the one human sessions use)
docker compose -p codexify_tester --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml -f docker-compose.whooshd-deepseek.yml \
  exec backend python -m guardian.cli.tester_account_provision --email '<tester-a>' --role admin

docker compose -p codexify_tester --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml -f docker-compose.whooshd-deepseek.yml \
  exec backend python -m guardian.cli.tester_account_provision --email '<tester-b>' --role guest
```

## 3. The two accounts

The rubric's minimum sample is **two distinct non-developer tester accounts**, each using their own
authenticated session, and it requires a real **A → B → A send/reply loop between the two real
accounts**. Two accounts that each talk to the operator do not satisfy it.

| Requirement | Where it comes from |
| --- | --- |
| 2 distinct non-developer accounts | rubric, *Minimum qualification sample* |
| each uses their own authenticated session | rubric, *Minimum qualification sample* |
| at least 1 completes the critical path with no synchronous guidance | rubric, *Minimum qualification sample* and *Test posture* |
| at least 1 real send/reply loop between the two accounts | rubric, *Minimum qualification sample* and PASS gate item 7 |
| evidence tied to the tested commit and runtime profile | rubric, *Minimum qualification sample* |

Each tester needs:

- an email address they control, for the account;
- a time window long enough to complete the session without rushing;
- agreement to talk to **the other tester**, not only to the operator;
- agreement that the session may be recorded as evidence.

Give each tester their own credentials directly. The operator holds credentials for the runtime,
not for the tester's account.

## 4. What to ask each tester for

Send this before the session. It sets the unassisted expectation without teaching the UI:

> Use Codexify as you normally would. If something seems unclear, try what feels natural first.
> Tell me what you are thinking as you go. I am testing the software, not you.

This is the rubric's own prompt. **Do not** add navigation instructions ("click People in the top
right…") before the first attempt. The moment you give a navigation hint you have crossed into
assisted testing, and the rubric requires you to record the new assistance level.

If you must intervene to keep the session moving, record it immediately. The rubric's
`assistance_level_peak` and `wrong_turns_total` metrics exist so that assisted and unassisted
passages are distinguishable in the evidence rather than blurred together.

## 5. What to collect

Per tester, collect the rubric's required metrics and freeform notes verbatim:

```text
docs/qualification/rubrics/onboarding-and-people.md
  → "Required metrics per tester"
  → "Required freeform" (tester_quotes, observed_confusion, positive_signals, operator_notes)
```

**Report raw counts.** With a sample of two, a percentage such as "100% success" is not a
defensible statement. The rubric says so explicitly: show the sample size next to the count.

If the product behaves correctly but independent usability stays unclear, the rubric's verdict is
`HOLD`, not `PASS`. Do not upgrade an ambiguous result to PASS because the two sessions were
enjoyable.

## 6. Where the result goes

The run conclusion follows the rubric's template, and the receipt lands with the other
qualification receipts:

```text
docs/qualification/runs/YYYY-MM-DD-onboarding-and-people-<revision>.md
```

The receipt must link to the exact commit and the supporting runtime evidence, and it must name
the rubric it was executed under. A receipt the registry cannot read does not qualify the
surface; the registry discovers receipts under `docs/qualification/runs/`.

## 7. Order of operations

The human lane and the machine lane are independent and should run in parallel, but **not** on a
moving candidate:

1. Name the candidate revision and freeze it for the duration of both lanes.
2. Run the eight-gate machine qualification against that revision.
3. Run the human sessions against that same revision.
4. Refresh any qualification the candidate's changes made stale.
5. Only then evaluate whether the release gate can move off `HOLD`.

If a defect is found in either lane, the candidate changes, and **both** lanes must be re-run at
the new revision. A defect found in one lane is evidence that the other lane's evidence describes
an older revision.
