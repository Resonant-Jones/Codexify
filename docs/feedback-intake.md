# Codexify Feedback Intake

This document turns casual tester notes into structured GitHub issues.

The goal is simple: testers should be able to tell their assistant what felt broken, confusing, or missing, and the assistant should package it into the right GitHub issue form.

## Where to submit

Open the repository issues page and choose one of the templates:

- **Bug report**: something is broken, inconsistent, or failing.
- **UX friction**: something technically works, but feels confusing, uncertain, or awkward.
- **Feature request**: a missing capability or workflow improvement.

Use **UX friction** when the behavior is not clearly wrong, but the interface does not explain itself well.

## Passive capture phrase

Testers can say this to their assistant:

```text
Log this as Codexify feedback.
Type: bug | ux friction | feature request | unsure
Observed:
Expected:
Actual:
Steps:
Impact:
Screenshot/logs:
Environment:
```

The assistant should ask at most one clarifying question if a required field is missing. Otherwise, it should create or draft a GitHub issue using the closest template.

## Assistant routing rules

Route the report like this:

| Signal | Template |
| --- | --- |
| Error, crash, failed request, missing data, broken flow | Bug report |
| Confusing label, unclear state, awkward click path, uncertain mental model | UX friction |
| New setting, new control, new capability, workflow improvement | Feature request |

When in doubt, use **UX friction**. A confusing interaction is still real product data.

## Severity / impact guide

### Bugs

- **S0 - Blocks core use**: Cannot use the main chat, documents, provider, auth, or project flow.
- **S1 - Major workflow break**: A key flow works only with a workaround.
- **S2 - Confusing but usable**: The feature works but causes wrong expectations or repeat mistakes.
- **S3 - Polish / papercut**: Small visual, copy, or interaction issue.

### UX friction

- **Blocks understanding**: User cannot infer what the system is doing.
- **Causes wrong action**: User clicks or changes something because the UI suggested the wrong model.
- **Slows me down**: User can recover but loses time.
- **Minor polish issue**: Annoying, but not workflow-breaking.

## Example: multi-tab chat confusion

```text
Type: ux friction
Observed: Multi-tab chat allows multiple tabs, but the labels 'My thread' and 'New thread' made it unclear whether these were tabs, conversations, copies, or unsaved drafts.
Expected: The UI should make it obvious which tab is active, whether a thread is new/empty, and whether a duplicate was intentionally created.
Actual: Clicking the + button could create multiple empty threads, making the feature feel like a bug even if multi-tab is intentional.
Steps:
1. Open a project chat.
2. Click + in the top-right chat area.
3. Click + again before typing.
4. Rename or switch between threads.
5. Notice it is unclear which thread owns which state.
Impact: Blocks understanding.
Suggestion: Disable + while an empty new thread already exists, rename labels to 'Current chat' / '+ New chat', and hide implementation labels unless Dev Mode is enabled.
```

## Good issue titles

- `ux: clarify multi-tab chat labels and empty-thread behavior`
- `bug: gallery receives image but chat attachment disappears`
- `feat: add setting to disable multi-tab chat`

## Intake contract

A useful issue should answer four questions:

1. What did the tester try to do?
2. What did they expect?
3. What actually happened?
4. What evidence or sequence lets us reproduce or reason about it?

Do not force testers to speak like engineers. Capture the uncertainty. The uncertainty is the artifact.
