# Collaboration Protocol

This protocol is for trusted collaborators working inside Codexify.

The goal is not to rush to a fix. The goal is to understand the system well enough to make a narrow, safe, reviewable change.

## Working Principles

- Understand first.
- Explore freely.
- Ask questions at seams.
- Use branches and worktrees for changes.
- Keep each task narrow.
- Validate before committing.
- Do not merge directly to main without review.

Bug hunting is welcome as a natural result of exploration. If exploration turns up a defect, that is useful. The collaboration goal is still curiosity, inspiration, and craft, not obligation or dread.

## Expectations

- Do not assume ownership, business participation, responsibilities, or entitlement.
- If collaboration becomes business-shaped, agreements should be explicit.
- Shared work should be clear about scope, evidence, and review expectations.
- If a boundary feels ambiguous, pause at the seam instead of guessing.

## Practical Shape

- Read the relevant current-state and architecture docs before editing.
- Prefer the smallest reviewable change that solves the task.
- Keep unrelated work out of the task branch.
- Treat validation as proof of the surface you actually changed, not a blanket guarantee.
- Keep shared truth protected even while you experiment locally.

## Good Collaboration Habits

- Name the seam you are changing.
- Call out assumptions when they are not proven.
- Separate docs truth, code truth, and runtime proof.
- Leave room for follow-up tasks when the boundary is real.
- Favor plain language when you are explaining what changed and why.

## What Success Looks Like

- The task is understandable without hidden context.
- The change is narrow enough to review quickly.
- Validation is recorded clearly.
- Any uncertainty is stated plainly instead of being smoothed over.
