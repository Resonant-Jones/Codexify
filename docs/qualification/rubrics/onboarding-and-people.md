# Onboarding + People Human Qualification Rubric

## Qualification ID

`onboarding-and-people`

## Version

`1`

## Purpose

Evaluate whether a real Codexify user can:

1. enter Codexify;
2. understand the optional onboarding experience;
3. skip or resume it without penalty;
4. understand the basic application surfaces;
5. understand the distinction between account identity, social identity, username, and display presentation;
6. optionally claim a pseudonymous username;
7. locate People;
8. find another same-node user;
9. begin a Conversation;
10. exchange and later rediscover durable messages;
11. locate help again without relying on the founder/operator.

This rubric evaluates the **human product experience and live account path**.

It does not re-prove every backend invariant already covered by automated tests.

## Current scope

Target environment:

```text
authenticated private-preview / friends-and-family accounts
```

Messaging scope:

```text
same-node only
```

This rubric does not qualify:

- realtime delivery;
- read receipts;
- push notifications;
- cross-node messaging;
- federation;
- ThreadSpace;
- WhisperMesh;
- Hosted Rooms;
- global usernames;
- production/public support.

## Minimum qualification sample

For an initial Private Preview human qualification:

- minimum **2 distinct non-developer tester accounts**;
- each tester must use their own authenticated session;
- at least one tester must perform the critical path without synchronous operator guidance;
- at least one send/reply loop must occur between real accounts;
- evidence must be tied to the tested commit and runtime profile.

With a small sample, report raw counts. Do not report percentages such as `100% success` when `n=2` without also showing the sample size.

## Test posture

The operator should not teach the tester the UI before the first attempt.

Use this prompt:

> Use Codexify as you normally would. If something seems unclear, try what feels natural first. Tell me what you are thinking as you go. I am testing the software, not you.

Do not say:

> Click People in the top right, then click Inbox, then choose a username.

unless the run has already crossed into assisted testing.

Once direct guidance is given, record the new assistance level.

# Phase A — First entry

## A1. Initial application entry

### Goal

Tester reaches the normal Codexify workspace.

### Observe

- Does the application load normally?
- Does onboarding appear only after the authenticated shell is usable?
- Does it feel like part of Codexify rather than a blocking account gate?
- Can the tester visually identify that the tour is optional?

### Required behavior

- ordinary workspace remains underneath;
- no broken startup state;
- no forced username;
- `Skip for now` is immediately available.

### Blocking failure

- onboarding prevents access to Codexify;
- account is unusable until onboarding is completed;
- user is required to create a social identity.

# Phase B — Skip and resume

## B1. Skip onboarding

Ask the tester to stop onboarding whenever they naturally wish.

If they do not choose to skip, explicitly test Skip after the normal walkthrough.

### Required

- wizard closes;
- Codexify remains usable;
- skip state persists.

Record:

```text
Did tester understand that Skip was safe?
yes / no
```

## B2. Return after skip

Reload, reopen, or sign out/in as appropriate.

### Required

The skipped wizard does **not** automatically force itself open again.

### Observe

Can the tester find the passive setup reminder?

Record:

```text
setup_reminder_discovered_without_help:
yes / no
```

and assistance level.

## B3. Resume

Tester should be able to deliberately resume setup.

### Required

- resume returns to a sensible saved step;
- existing application state is unaffected.

# Phase C — Identity comprehension

After the identity card, ask:

> In your own words, what do you think the username is for?

Then:

> Do you think you need to use your real name here?

Then:

> If you changed your username later, what would you expect to happen to existing conversations?

Do not correct the tester until their answers are recorded.

## Expected understanding

The tester should broadly understand:

- username helps other people find them;
- username can be pseudonymous;
- username is not their account ownership identity;
- changing it should not destroy existing relationships/conversations.

Exact architecture vocabulary is not required.

They do not need to know the term `Profile_ID`.

### Critical privacy question

Record:

```text
Did the tester feel pressured to reveal their real identity?

yes / no
```

If yes, capture why.

Any repeated perception that Codexify requires real-name identity should trigger product review even if the backend preserves privacy correctly.

# Phase D — Username setup

Only execute this section when the direct-messaging capability is available.

## D1. Optionality

Observe whether the tester understands username setup can be skipped.

### Required

Username is not required to complete onboarding.

## D2. Claim a username

Allow the tester to choose their own test username.

Do not suggest using their legal name.

### Required

- valid username can be claimed;
- stored username is presented correctly;
- successful claim removes the unset-username setup prompt.

## D3. Validation

Where practical, test one invalid value.

Examples:

```text
two characters
contains spaces
reserved name
```

### Observe

Can the tester understand what needs correcting from the error?

Record:

```text
username_error_self_explanatory:
yes / no
```

# Phase E — Navigation comprehension

Do not tell the tester where each surface is before testing this section.

Ask:

> If you wanted to talk to Guardian, where would you go?

> If you wanted to find a document, where would you look?

> If you wanted to message another person, where would you look?

> Where would you go if you wanted to change Codexify's settings?

Record first choice before correction.

## Expected concepts

Tester can distinguish:

```text
Guardian
Documents
Gallery
Dashboard
Settings
People
```

They should understand that People is separate from Guardian conversation.

They do not need perfect recall of every surface.

# Phase F — Guardian versus People

This is a high-value comprehension test.

Ask:

> Send another Codexify user a message.

Do not mention People.

### Record first action

Examples:

```text
opened People
opened Guardian
opened Contacts
searched Settings
asked operator
```

If the tester opens Guardian, ask what they expected to happen before giving guidance.

### Qualification signal

Independent selection of People is strong evidence the conceptual separation works.

Opening Guardian is not merely a tester mistake. It is UX evidence.

# Phase G — Find another user

Tester searches for another known same-node test account by username.

### Required

- search is discoverable;
- intended peer appears;
- no email or private account data appears;
- username/display presentation is understandable.

Record:

```text
wrong_turns:
assistance_level:
time_to_peer_found:
```

Do not treat time as a hard gate in V1.

# Phase H — Start a Conversation

Tester initiates a new Conversation with the peer.

### Required

- Conversation opens;
- tester understands they are communicating with another person;
- no Guardian framing is accidentally implied;
- no unrelated Project/Thread authority is granted.

Ask:

> Who do you think will receive what you type here?

Record the answer before continuing.

# Phase I — Live send

Tester A sends a unique test message.

Suggested safe form:

```text
Qualification message from <tester alias> — <timestamp or short marker>
```

### Required

- sender sees the message;
- message persists;
- exactly one intended Conversation receives it.

This rubric does **not** require realtime notification.

# Phase J — Recipient discovery

Tester B opens or returns to Codexify naturally.

Prompt:

> See whether you have anything from the other tester.

Do not say where to look.

### Observe

- Can the recipient locate People?
- Can they recognize the Conversation?
- Do they understand who sent it?
- Is manual reopen/reload required?
- Did they incorrectly expect Guardian to surface the message?

Record:

```text
recipient_discovered_message:
yes / no

assistance_level:
wrong_turns:
```

If a reload/reopen is required, record that as actual product behavior rather than hiding it.

# Phase K — Reply loop

Tester B replies.

Tester A then attempts to find the reply.

### Required

- reply persists;
- sender can later read it;
- correct peer and Conversation remain associated;
- no duplicate Conversation is silently created.

The completed human loop is:

```text
A finds B
   ↓
A creates Conversation
   ↓
A sends
   ↓
B finds Conversation
   ↓
B reads
   ↓
B replies
   ↓
A reads reply
```

This is the primary People qualification path.

# Phase L — Persistence

After successful messaging:

- close People;
- navigate elsewhere in Codexify;
- reopen People.

Where practical, also perform a fresh browser session or service restart as a separate qualification step.

### Required

Tester can rediscover the same Conversation and messages.

Record the actual persistence boundary tested:

```text
UI close/reopen
page reload
new login session
backend restart
full deployment restart
```

Do not mark untested persistence boundaries PASS.

# Phase M — Tips rediscovery

After onboarding has ended, ask:

> Where would you look if you forgot what one of these parts of Codexify does?

Observe first action.

### Required

Tester can eventually find:

```text
Settings → Help & Learning
```

or another intentional Tips entry point if added later.

Then ask the tester to find one explanation using Tips.

Record:

```text
tips_discovered_without_help:
yes / no

tip_successfully_used:
yes / no
```

# Phase N — End-of-session questions

Ask without suggesting desired answers.

1. What do you think Guardian is for?
2. What do you think People is for?
3. What is a Project?
4. What is a Thread?
5. What information do you think another user can see about you?
6. Could you find this onboarding information again tomorrow?
7. What was the most confusing thing you encountered?
8. What felt obvious?
9. Is there anything you expected Codexify to do that it did not do?
10. How confident are you that you could send somebody another message without help?

Confidence score:

```text
1 2 3 4 5
```

Preserve the tester's answer verbatim where practical.

# Required metrics per tester

```text
tester_alias
commit
runtime_profile
device_class
browser_client
prior_familiarity

onboarding_completed
onboarding_skipped
resume_discovered

username_claimed
username_claim_assistance_level
felt_real_name_pressure

guardian_people_first_choice

people_found
peer_found
conversation_created
message_sent
message_received
reply_sent
reply_received

assistance_level_peak
wrong_turns_total
self_recovered

tips_discovered
tips_used

repeat_task_confidence_1_to_5
```

Also retain freeform:

```text
tester_quotes
observed_confusion
positive_signals
operator_notes
```

# Blocking qualification criteria

A human qualification run cannot receive PASS if any of these occur:

- onboarding blocks normal Codexify use;
- username is effectively mandatory;
- UI encourages or requires real-name disclosure;
- another user's private account/email information appears in discovery;
- messaging goes to the wrong account;
- a message cannot be durably recovered after the persistence boundary being claimed;
- sender/recipient identity is ambiguous enough to risk messaging the wrong person;
- skip state repeatedly ignores deliberate dismissal;
- unsupported messaging capability is presented as available;
- operator must perform the task on behalf of the tester;
- recorded evidence cannot identify the tested commit/profile.

# Initial Private Preview PASS gate

For the initial onboarding + People Private Preview qualification:

1. **Two distinct non-developer accounts** complete the test.
2. Both can enter Codexify without being forced through onboarding.
3. Both demonstrate that skip/resume behaves correctly.
4. Neither reports that a legal/real name appears required.
5. Both can successfully establish or intentionally decline a username.
6. At least one tester identifies People for human messaging without a direct navigation hint.
7. A real A → B → A send/reply loop succeeds.
8. Both testers can later rediscover the Conversation.
9. No blocking privacy, identity, account-isolation, or wrong-recipient defect is observed.
10. The qualification receipt links to the exact commit and supporting runtime evidence.

If the product behavior works but independent usability remains unclear:

```text
HOLD
```

not PASS.

# Run conclusion template

End every human run with:

## Verdict

```text
PASS | HOLD | FAIL
```

## Proven

List only what this run directly establishes.

## Failed

List reproduced contract failures.

## Unproven

List anything not actually exercised.

## Human friction

Record usability findings separately from functional defects.

## Highest-priority follow-up

Name one concrete next product or qualification seam.

## Evidence

Link:

- commit;
- relevant automated qualification;
- screenshots/traces if retained;
- detailed runtime proof where applicable.

# Qualification principle

The tester is not being graded.

Codexify is.

A user choosing the "wrong" surface, misunderstanding a label, asking for help, or abandoning a task is not noise to correct away.

It is product evidence.
