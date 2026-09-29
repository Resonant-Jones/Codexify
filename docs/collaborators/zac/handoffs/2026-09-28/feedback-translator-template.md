# Zac Feedback Translator Template

**Purpose:** let Zac speak naturally while Luna converts the useful parts into durable Codexify evidence.

This template is for Luna or another assistant. It is **not** a form Zac has to fill out.

## Operating Rule

Zac may complain informally.

He may:

- voice-dump;
- send fragments;
- swear;
- contradict himself and correct it later;
- paste screenshots without explanation;
- say "this is stupid" before he knows exactly why;
- notice something good without knowing what subsystem caused it.

The translator's job is to make the feedback legible **without replacing Zac's experience with the agent's interpretation**.

## Translator Constraints

Do:

- preserve the attempted user goal;
- separate observation from interpretation and hypothesis;
- keep uncertainty explicit;
- retain useful emotional language when it communicates user cost;
- connect screenshots/logs to the claim they actually support;
- mark missing information as unknown;
- split unrelated complaints into separate feedback records.

Do not:

- invent reproduction steps;
- infer a root cause from symptoms;
- assign severity merely because Zac sounded annoyed;
- turn a preference into a bug without identifying the user cost;
- "professionalize" the feedback until its meaning changes;
- claim a capability worked because a lower-level service responded;
- silently use repository/operator knowledge to explain away a product failure.

## Copy-Paste Prompt For Luna

Use this when translating Zac's raw notes:

> Translate my informal Codexify feedback into evidence records. Preserve what I meant, including frustration or praise when it explains the user experience. Do not make me restate things in a formal format. Separate facts I directly observed from my interpretation and from any technical hypothesis. Do not invent missing steps, causes, severity, or product intent. If a field is unknown, write "Unknown". If I describe multiple unrelated problems, create separate records. Use screenshots or logs only for claims they actually support. End with at most one clarification question, and only if the answer would materially change the record.

## Feedback Record

Create one record per distinct finding.

### Finding

- **Short title:** plain description of the experience.
- **Date/session:** when it happened, if known.
- **Lane/surface:** Preview Human Loop, Cross-Node Field Lab, or other named surface.
- **User goal:** what Zac was trying to accomplish.
- **Observed steps:** only steps Zac actually described or evidence establishes. Unknown if incomplete.
- **Expected:** what Zac expected. Unknown if he had no clear expectation.
- **Actual:** what visibly happened.
- **Why it mattered to Zac:** confusion, interruption, mistrust, extra work, delight, etc. Preserve the human point rather than translating it into architecture jargon.
- **Workaround used:** if any.
- **Did the workaround require operator/developer knowledge?** Yes / No / Unknown.
- **Classification:** Bug / Comprehension friction / Operator leakage / Missing path / Positive proof / Unknown.
- **Reproducibility:** Reproduced / One observation / Could not reproduce / Unknown.
- **Evidence:** screenshot, trace, message, command output, commit/ref observation, or "None captured".
- **Observed fact:** what the evidence directly supports.
- **Interpretation:** Zac's current reading of what it means.
- **Technical hypothesis:** optional; explicitly labeled as hypothesis, never fact.
- **Open ambiguity:** what remains unclear.
- **Stop boundary:** whether continuing would require repo/terminal rescue, credentials, architecture authority, remote mutation, or another out-of-scope action.
- **Candidate follow-up:** the smallest useful next check, not an implementation plan unless implementation was explicitly authorized.

## Example

Raw Zac feedback:

> I clicked Library because I assumed the thing I uploaded would be there. It's not there. I can probably go poke the backend and find it but that defeats the whole point. Maybe I'm misunderstanding what Library means, but if so the UI never told me.

Translated:

### Finding — Uploaded item is not discoverable from Library

- **Lane/surface:** Preview Human Loop / Library
- **User goal:** find a previously uploaded item.
- **Observed steps:** opened Library after uploading an item earlier in the session.
- **Expected:** the uploaded item would be visible or discoverable from Library.
- **Actual:** Zac did not find the item there.
- **Why it mattered to Zac:** the apparent recovery path failed; continuing seemed to require backend knowledge.
- **Workaround used:** none.
- **Did the workaround require operator/developer knowledge?** Not applicable; Zac stopped before using one.
- **Classification:** Missing path or comprehension friction — unresolved.
- **Reproducibility:** One observation.
- **Evidence:** screenshot if supplied; otherwise none captured.
- **Observed fact:** the item was not discoverable by Zac from the Library surface he used.
- **Interpretation:** either the Library does not expose the uploaded item or its organization is not legible.
- **Technical hypothesis:** Unknown.
- **Open ambiguity:** whether the item failed to persist, persisted outside Library, or was present but not recognizable.
- **Stop boundary:** using backend/repo tools would invalidate the normal-user test.
- **Candidate follow-up:** repeat once with a clearly named test item and capture the upload + Library states.

## Informal Checkpoint Translation

If Zac sends a progress dump rather than a product finding, translate it into:

- **Current truth** — what is known right now.
- **What changed** — what actually became different since the prior checkpoint.
- **Evidence** — what proves that change.
- **Blocker / ambiguity** — only genuine blockers or unresolved meaning.
- **Next move** — the next bounded action already inside the lane.

Do not interpret "I worked on it" as a state change without evidence.

## Raw Notes Preservation

When the original wording carries useful context, keep a short **Raw note excerpt** under the record.

Do not preserve secrets, credentials, private addresses, tokens, or sensitive personal data merely because they appeared in the raw message.
