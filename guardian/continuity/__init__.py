"""Continuity Protocol Suite — pure backend contract seam.

This package defines inert, importable, deterministic contract types and a
pure compiler harness for candidate continuity structures. No persistence,
routes, workers, graph writes, browser capture, sync, or provider routing.

Modules
-------
``guardian.continuity.contracts`` — dataclasses, candidate token aliases,
    candidate value tuples, and pure validation helpers.
``guardian.continuity.compiler`` — pure deterministic compiler contract harness
    with ContinuityCompileResult and compile_reality_state.
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
