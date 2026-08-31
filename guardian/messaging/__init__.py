"""Bounded direct-messaging domain package.

Owns the durable same-node profile-to-profile private-messaging substrate:

* ``tokens``   — canonical contract-bearing token domains.
* ``envelope`` — transport-neutral message envelope.
* ``service``  — persistence, identity, authorization, and payload logic.

No Guardian inference, retrieval, memory, Hosted Room, or federation code
lives in this package.
"""

from __future__ import annotations

__all__ = ["envelope", "service", "tokens"]
