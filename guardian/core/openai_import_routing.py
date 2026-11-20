"""Placement for an explicitly selected logical OpenAI import source."""

import re

_GROUP_ID = re.compile(r"g-p-[0-9a-f]{32}")
UNRESOLVED_RECORD_PREFIX = "codexify-openai-unresolved-"


class UnresolvedOpenAIGroup(ValueError):
    """The archive doesn't establish whether a conversation belongs in a Project."""


class OpenAIImportPlacementConflict(RuntimeError):
    """A scoped import would attach to a different or unavailable destination."""


def original_openai_conversation_id(conversation: dict) -> str:
    """Resolve an exact source key; reject fabricated diagnostic or conflicting IDs."""
    identities: set[str] = set()
    for field in ("id", "conversation_id"):
        value = conversation.get(field)
        if value is None or value == "":
            continue
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 255
            or value.startswith(UNRESOLVED_RECORD_PREFIX)
        ):
            raise UnresolvedOpenAIGroup("OpenAI source conversation identifier is invalid")
        identities.add(value)
    if len(identities) != 1:
        raise UnresolvedOpenAIGroup("OpenAI source conversation identity is missing or inconsistent")
    return next(iter(identities))


def classify_openai_group(conversation: dict) -> str | None:
    """Return an exact group ID, or None for explicitly ungrouped evidence."""
    original_openai_conversation_id(conversation)
    group = conversation.get("conversation_template_id")
    gizmo_id = conversation.get("gizmo_id")
    gizmo_type = conversation.get("gizmo_type")
    if (
        isinstance(group, str)
        and _GROUP_ID.fullmatch(group)
        and (gizmo_id is None or gizmo_id == group)
        and (gizmo_type is None or gizmo_type == "snorlax")
    ):
        return group
    if (
        "conversation_template_id" in conversation
        and group is None
        and gizmo_id is None
        and gizmo_type is None
    ):
        return None
    raise UnresolvedOpenAIGroup("OpenAI Project membership is unresolved")


def lock_openai_import_owner(chatlog_db, user_id: str, source_id: str | None) -> None:
    """Serialize creation and legacy/scoped collision checks for an owner."""
    with chatlog_db._connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id = %s FOR NO KEY UPDATE", (user_id,))
        if not cur.fetchone():
            raise OpenAIImportPlacementConflict("OpenAI import owner does not exist")
        if source_id is not None:
            cur.execute(
                "SELECT id FROM openai_import_sources WHERE id = %s AND user_id = %s",
                (source_id, user_id),
            )
            if not cur.fetchone():
                raise OpenAIImportPlacementConflict("OpenAI import source is unavailable")


def resolve_openai_fresh_project(
    chatlog_db, *, user_id: str, source_id: str, group_id: str | None
) -> tuple[int, bool]:
    """Called under the import owner's lock, inside the conversation transaction."""
    with chatlog_db._connect() as conn, conn.cursor() as cur:
        if group_id is None:
            cur.execute(
                """SELECT id FROM projects
                WHERE user_id = %s AND system_role = 'general'
                    AND archived_at IS NULL FOR UPDATE""",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise OpenAIImportPlacementConflict(
                    "Confirmed ungrouped conversation needs the account's active General"
                )
            return int(row["id"]), False
        cur.execute(
            """SELECT project_id FROM openai_import_project_groups
            WHERE user_id = %s AND source_id = %s AND group_id = %s""",
            (user_id, source_id, group_id),
        )
        existing = cur.fetchone()
        if existing is not None:
            cur.execute(
                """SELECT id FROM projects WHERE id = %s AND user_id = %s
                AND archived_at IS NULL AND system_role IS NULL FOR UPDATE""",
                (existing["project_id"], user_id),
            )
            row = cur.fetchone()
            if row is None:
                raise OpenAIImportPlacementConflict(
                    "Mapped OpenAI Project is archived or deleted; review it before importing"
                )
            return int(row["id"]), False
        # Labels deliberately carry no authority. Never adopt a same-name Project.
        stem = f"OpenAI Project {group_id[4:12]}"
        for suffix in range(1, 101):
            name = stem if suffix == 1 else f"{stem} ({suffix})"
            cur.execute(
                """INSERT INTO projects (user_id, name)
                VALUES (%s, %s) ON CONFLICT (user_id, name) DO NOTHING RETURNING id""",
                (user_id, name),
            )
            row = cur.fetchone()
            if row is not None:
                project_id = int(row["id"])
                cur.execute(
                    """INSERT INTO openai_import_project_groups
                    (user_id, source_id, group_id, project_id)
                    VALUES (%s, %s, %s, %s)""",
                    (user_id, source_id, group_id, project_id),
                )
                return project_id, True
        raise OpenAIImportPlacementConflict("Could not allocate an unused OpenAI Project name")
