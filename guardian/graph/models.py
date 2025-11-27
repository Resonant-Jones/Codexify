"""Neo4j graph models for chat logging and RAG context."""
from __future__ import annotations

from datetime import datetime

from neomodel import (
    DateTimeProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    UniqueIdProperty,
)


class UserNode(StructuredNode):
    uuid = UniqueIdProperty()
    user_id = StringProperty(unique_index=True, required=True)
    name = StringProperty()
    created_at = DateTimeProperty(default_now=True)

    messages = RelationshipFrom("MessageNode", "SENT_BY")


class ThreadNode(StructuredNode):
    uuid = UniqueIdProperty()
    thread_id = StringProperty(unique_index=True, required=True)
    created_at = DateTimeProperty(default_now=True)

    messages = RelationshipFrom("MessageNode", "PART_OF")


class MessageNode(StructuredNode):
    uuid = UniqueIdProperty()
    message_id = StringProperty(unique_index=True, required=True)
    content = StringProperty()
    created_at = DateTimeProperty(default=datetime.utcnow)

    user = RelationshipTo(UserNode, "SENT_BY")
    thread = RelationshipTo(ThreadNode, "PART_OF")
