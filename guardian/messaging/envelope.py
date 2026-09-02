"""Transport-neutral direct-message envelope.

The envelope is the logical message shape that survives future transport
adapters.  For today's same-node implementation ``source.node_id ==
destination.node_id == local_node_id`` and no remote network call occurs.

Future transport adapters may add endpoint, signature, relay, session,
receipt, or transport metadata fields.  Those additions MUST NOT redefine
``message_id``, ``conversation_id``, ``profile_id``, ``node_id``,
participant authority, or message authorship.

The envelope carries social addressing only.  Account-private state
(``user_id``, email, credentials, recovery information) never appears in it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from guardian.messaging.tokens import DM_PROTOCOL_VERSION


class EnvelopeAddress(BaseModel):
    """One participant's protocol social address: Node_ID + Profile_ID."""

    node_id: str = Field(min_length=1, max_length=64)
    profile_id: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class EnvelopeContent(BaseModel):
    """Canonical message content."""

    type: str = Field(min_length=1, max_length=64)
    body: str

    model_config = ConfigDict(extra="forbid")


class DirectMessageEnvelope(BaseModel):
    """The canonical transport-neutral direct-message envelope."""

    protocol_version: str
    message_id: str = Field(min_length=1, max_length=64)
    conversation_id: str = Field(min_length=1, max_length=64)
    source: EnvelopeAddress
    destination: EnvelopeAddress
    content: EnvelopeContent
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


def build_message_envelope(
    *,
    message_id: str,
    conversation_id: str,
    source_node_id: str,
    source_profile_id: str,
    destination_node_id: str,
    destination_profile_id: str,
    content_type: str,
    body: str,
    created_at: datetime,
) -> DirectMessageEnvelope:
    """Assemble the canonical envelope for one persisted direct message."""
    return DirectMessageEnvelope(
        protocol_version=DM_PROTOCOL_VERSION,
        message_id=message_id,
        conversation_id=conversation_id,
        source=EnvelopeAddress(
            node_id=source_node_id,
            profile_id=source_profile_id,
        ),
        destination=EnvelopeAddress(
            node_id=destination_node_id,
            profile_id=destination_profile_id,
        ),
        content=EnvelopeContent(type=content_type, body=body),
        created_at=created_at,
    )


def envelope_payload(envelope: DirectMessageEnvelope) -> dict:
    """Serialize an envelope to its peer-facing JSON payload."""
    return envelope.model_dump(mode="json")


__all__ = [
    "DM_PROTOCOL_VERSION",
    "DirectMessageEnvelope",
    "EnvelopeAddress",
    "EnvelopeContent",
    "build_message_envelope",
    "envelope_payload",
]
