"""Per-message source-origin classification for account-scoped history recall.

This module owns exactly one decision: given the *persisted* evidence attached
to one canonical message row, is that message native, imported, unknown, or
conflicting with respect to source origin?

Governing decisions
-------------------
- ADR-016 (authoritative chat message origin clarification): positive native
  proof is a message-associated origin assertion assigned by the trusted
  canonical backend at the creation of that native interaction, or ADR-016's
  narrower exact-message trusted assistant-completion witness. A native thread,
  an absent import marker, a role, an owner, a storage location, or a recall
  grant is never proof.
- ADR-016: a missing import marker is never positive native evidence. An
  unmarked legacy row stays ``unknown`` and ineligible. No backfill, no
  relabelling, and no inference from message text happens here.
- ADR-016: imported archive inspection is a human-only path, so an imported
  record is excluded from ordinary native recall regardless of placement.

Why the trust decision lives in the writer
-------------------------------------------
The trust decision is the *write authority*, not the JSON. The reserved
``extra_meta.message_origin`` member can only be written by the trusted
creation seam (``guardian/core/db.py``): every untrusted write path strips it,
the ordinary-chat route refuses it, and the generic restore refuses an archive
that carries it. This module therefore reads the persisted member as the
durable record of a creation-bound assertion. It never re-derives authority
from the shape of the JSON alone, it never writes anything, and it never
infers an origin from a message's content.

Labels
------
The four labels below are module-local implementation vocabulary. ADR-016
documents ``native`` / ``imported`` / ``unknown`` / ``conflicting`` as
documentation-only fixture vocabulary, so these strings deliberately do not
enter the canonical protocol-token registry and are never persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from guardian.core.db import (
    IMPORT_LINEAGE_METADATA_KEYS,
    NATIVE_ORIGIN_SYSTEM,
    RESERVED_MESSAGE_ORIGIN_KEY,
    RESERVED_MESSAGE_ORIGIN_VERSION,
)


# ---------------------------------------------------------------------------
# Module-local classification vocabulary
# ---------------------------------------------------------------------------

#: The message carries positive native creation evidence and no import claim.
LABEL_NATIVE = "native"

#: The message carries positive provider import evidence.
LABEL_IMPORTED = "imported"

#: The message carries no adequate positive proof either way.
LABEL_UNKNOWN = "unknown"

#: The message carries incompatible native and import claims.
LABEL_CONFLICTING = "conflicting"


#: The provider origin values written by the canonical importers.
IMPORT_ORIGIN_VALUES = frozenset({"chatgpt_import", "claude_import"})

#: Import lineage keys that assert provider source lineage.
#:
#: The ``origin`` key is included: any stored provider-origin claim is import
#: lineage evidence, and the known provider values are additionally treated as
#: positive import evidence. ``era`` is excluded because ADR-016 names it an
#: auxiliary field rather than independent proof.
IMPORT_LINEAGE_EVIDENCE_KEYS = frozenset(
    key for key in IMPORT_LINEAGE_METADATA_KEYS if key != "era"
)

#: Auxiliary import-side fields. They are not independent proof, so they never
#: establish import or conflict on their own, but ADR-016 says partial import
#: indicators prevent a native classification.
IMPORT_AUXILIARY_KEYS = frozenset({"era", "embedding_status"})


@dataclass(frozen=True)
class MessageOrigin:
    """One content-free message-origin verdict.

    ``label`` is one of :data:`LABEL_NATIVE`, :data:`LABEL_IMPORTED`,
    :data:`LABEL_UNKNOWN`, or :data:`LABEL_CONFLICTING`. ``origin_system`` is
    the established native origin for a native verdict and ``None`` otherwise;
    it is never inferred from placement.
    """

    label: str
    origin_system: str | None = None

    @property
    def is_native(self) -> bool:
        return self.label == LABEL_NATIVE


def _native_assertion_state(extra_meta: Mapping[str, Any]) -> str:
    """Return ``"absent"``, ``"valid"``, or ``"invalid"`` for the assertion.

    ``valid`` means the persisted member has the accepted shape of the reserved
    assertion: the supported version, the canonical native origin system, and
    a backend-asserted timestamp. The shape alone is not the trust decision —
    the write-side custody in ``guardian/core/db.py`` is — but a member that
    does not have the accepted shape is never positive proof.
    """

    if RESERVED_MESSAGE_ORIGIN_KEY not in extra_meta:
        return "absent"
    assertion = extra_meta.get(RESERVED_MESSAGE_ORIGIN_KEY)
    if not isinstance(assertion, Mapping):
        return "invalid"
    if assertion.get("version") != RESERVED_MESSAGE_ORIGIN_VERSION:
        return "invalid"
    if str(assertion.get("origin_system") or "") != NATIVE_ORIGIN_SYSTEM:
        return "invalid"
    if not str(assertion.get("asserted_at") or "").strip():
        return "invalid"
    return "valid"


def _import_evidence_state(
    extra_meta: Mapping[str, Any],
) -> tuple[bool, bool, bool]:
    """Return ``(positive_import, import_lineage, auxiliary_import)`` flags.

    ``positive_import`` means the record carries an explicit provider import
    marker (``origin`` of ``chatgpt_import`` or ``claude_import``).
    ``import_lineage`` means the record carries provider source lineage.
    ``auxiliary_import`` means the record carries only auxiliary import-side
    fields, which block a native classification but prove nothing themselves.
    """

    origin_value = str(extra_meta.get("origin") or "").strip().lower()
    positive = origin_value in IMPORT_ORIGIN_VALUES
    lineage = any(key in extra_meta for key in IMPORT_LINEAGE_EVIDENCE_KEYS)
    auxiliary = any(key in extra_meta for key in IMPORT_AUXILIARY_KEYS)
    return positive, lineage, auxiliary


def classify_message_origin(
    extra_meta: Any,
    *,
    trusted_native_witness: bool = False,
) -> MessageOrigin:
    """Classify one message's source origin from its persisted evidence.

    ``extra_meta`` is the stored metadata object of one canonical message row.
    It is only read; nothing here mutates it, and no importer metadata is
    stripped or rewritten.

    ``trusted_native_witness`` is set by the caller when ADR-016's narrower
    exact-message trusted assistant-completion witness independently proves
    this exact row: a persisted accepted attempt that names this exact message
    in this same thread, with a non-null ``accepted_at`` and no failure or
    cancellation terminal event.

    The rules are, in order:

    1. A malformed or unsupported native claim is ``unknown``. Such a record
       has no adequate positive proof in either direction, and it is never
       relabelled native or imported on the strength of a shape it did not
       earn. An unresolved malformed claim also blocks the trusted witness,
       because ADR-016 resolves an uncertainty only under a separately
       authorized process.
    2. Positive native evidence (a guarded creation assertion, or the exact
       trusted assistant witness) together with import evidence is
       ``conflicting``: incompatible native and import claims are never
       resolved in favour of the convenient one.
    3. Positive native evidence together with only auxiliary import fields is
       ``unknown``, because ADR-016 says partial import indicators prevent a
       native classification until the uncertainty is resolved under a
       separately authorized process.
    4. Positive native evidence alone is ``native``.
    5. A positive provider import marker is ``imported``.
    6. Everything else — an unmarked legacy row, generic metadata, or partial
       import lineage without a positive marker — is ``unknown``.
    """

    metadata: Mapping[str, Any] = (
        extra_meta if isinstance(extra_meta, Mapping) else {}
    )
    assertion_state = _native_assertion_state(metadata)
    positive_import, import_lineage, auxiliary_import = _import_evidence_state(
        metadata
    )
    has_import_evidence = positive_import or import_lineage

    if assertion_state == "invalid":
        return MessageOrigin(label=LABEL_UNKNOWN)

    native_evidence = assertion_state == "valid" or trusted_native_witness

    if native_evidence:
        if has_import_evidence:
            return MessageOrigin(label=LABEL_CONFLICTING)
        if auxiliary_import:
            return MessageOrigin(label=LABEL_UNKNOWN)
        return MessageOrigin(label=LABEL_NATIVE, origin_system=NATIVE_ORIGIN_SYSTEM)

    if positive_import:
        return MessageOrigin(label=LABEL_IMPORTED)

    return MessageOrigin(label=LABEL_UNKNOWN)
