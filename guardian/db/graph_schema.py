# guardian/db/graph_schema.py


class NodeTypes:
    MESSAGE = "Message"
    THREAD = "Thread"
    PERSON = "Person"
    PROJECT = "Project"
    MEMORY = "MemoryEntry"


class RelTypes:
    IN_THREAD = "IN_THREAD"
    FROM_PERSON = "FROM_PERSON"
    TO_PERSON = "TO_PERSON"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    BELONGS_TO = "BELONGS_TO"


def make_node(label: str, id: str, **props) -> dict:
    return {
        "label": label,
        "id": id,
        "properties": props,
    }


def make_rel(from_id: str, to_id: str, rel_type: str, **props) -> dict:
    return {
        "from": from_id,
        "to": to_id,
        "type": rel_type,
        "properties": props,
    }
