# OpenAI export Project routing for an explicitly selected source

Status: approved implementation scope, branch-validated candidate. This is
not release qualification or evidence that a Preview is running this path.

## Authority and scope

The signed-in Codexify account owns its logical OpenAI import sources. A
source is created and then explicitly selected in Settings before a new
OpenAI upload starts. One source is sufficient. Distinct histories (for
example Business and Pro) can use separate sources under the same account.
Source IDs are server-generated. Names, OpenAI profile metadata, archive
hashes, and filenames are not authority or proof of authentication to OpenAI.
The staged job stores its source ID at admission; retries and resumed uploads
retain it. Legacy jobs with no selected source and Anthropic jobs retain
the existing routing contract.

The archive supplies exact group membership, not permission to reuse another
user's Project. A full lowercase `g-p-` plus 32 hexadecimal characters in
`conversation_template_id`, with no contradictory gizmo evidence, identifies
a group within the selected source. An explicit null template with no gizmo
evidence is confirmed ungrouped. Missing, unsupported, or contradictory
evidence (including inconsistent grouping for a duplicate source conversation)
remains unresolved with a warning; it is not silently sent to
General. This path does not add an Imports Project.

## Atomic placement and replay

The first accepted fresh conversation in a group creates one ordinary owned
Project and one mapping keyed by (owner, logical source, exact group ID), in
the same PostgreSQL transaction as its canonical conversation write. The
owner lock and uniqueness constraints prevent races. Labels are deterministic
display hints and can be renamed; no Project is adopted by its display
name. General is identified by its structural role, not a label, under
ADR-076. Project ownership remains canonical under ADR-081.

Existing conversations in the same source retain their placement including
a human's later move. A legacy or different-source collision refuses rather
than adopting the row. The pre-existing global external message uniqueness
constraint still means equal external conversation/message pairs imported by
different accounts are rejected; this change does not redesign that index.
An archived mapped Project is not reactivated. A permanently deleted mapped
Project leaves a tombstone and does not reappear on later import. Historical
threads are not reassigned or backfilled.

Confirmed PNGs and PDFs derive placement from the accepted thread in the
selected source and its current owned active Project. Unlinked/ambiguous
attachments do not fall back to Imports. A replay does not clone an already
persisted attachment that remains in the previous Project after a manual
thread move. A scoped image cannot replace the thread pointer of a same-byte
asset already attached to a different conversation.

## Account-archive compatibility

Full-account export uses `account-export.v9` when logical OpenAI source
state exists. It includes the source, group mapping (including tombstones),
immutable thread source binding, and Project lifecycle data needed by the
routing contract. Explicit older export formats refuse this state rather
than silently dropping it; readers still validate and restore historical
formats under their existing semantics. Version 9 checks all owners and
references before writes and restores the state transactionally with its
canonical rows. Active import jobs and staged export bytes are not portable
source state. This does not expand binary blob restoration. There is no
dynamic migration of an OpenAI archive based on source-account profile data.
