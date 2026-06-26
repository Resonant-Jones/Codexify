"""Continuity Protocol Suite — pure backend contract seam.

This package defines inert, importable, deterministic contract types, a
pure compiler harness, an explicit persistence adapter, and an explicit
write-action service for the four Phase A continuity tables.

Modules
-------
``guardian.continuity.contracts`` — dataclasses, candidate token aliases,
    candidate value tuples, and pure validation helpers.
``guardian.continuity.compiler`` — pure deterministic compiler contract harness
    with ContinuityCompileResult and compile_reality_state.
``guardian.continuity.persistence`` — explicit persistence adapter requiring an
    explicit SQLAlchemy session.  Not wired into runtime.
``guardian.continuity.write_actions`` — explicit write-action service requiring
    an explicit ContinuityPersistenceAdapter.  Not wired into runtime.
"""

from guardian.continuity.compiler import (  # noqa: F401
    ContinuityCompileResult,
    compile_reality_state,
    dedupe_preserving_order,
    derive_compiled_at,
    derive_state_id,
    extract_string_sequence,
    packet_sort_key,
)
from guardian.continuity.contracts import *  # noqa: F401,F403
from guardian.continuity.persistence import (  # noqa: F401
    ContinuityPersistenceAdapter,
    ContinuityPersistenceError,
    ContinuityPersistenceResult,
    StoredContinuityRecord,
)
from guardian.continuity.write_actions import (  # noqa: F401
    ContinuityActionActor,
    ContinuityWriteActionKind,
    ContinuityWriteActionService,
    ContinuityWriteReceipt,
    RealityCommitWriteInput,
    RealityStampInput,
    RealityStateWriteInput,
    StatePacketLinkInput,
)
