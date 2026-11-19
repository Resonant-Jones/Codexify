"""Canonical metadata and discovery for user-facing chat slash commands."""

from __future__ import annotations

import hashlib
import json
from itertools import chain
from typing import Literal

from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = 1
MAX_SEARCH_QUERY_LENGTH = 128
MAX_SEARCH_RESULTS = 25

InteractionMode = Literal["chat_intent", "composer_control"]
Availability = Literal["available", "unavailable", "unknown"]
AvailabilityReason = Literal["eligibility_not_evaluated"]
SlashCommandIntentKind = Literal[
    "conversation",
    "knowledge",
    "workspace",
    "automation",
    "security",
    "integration",
    "codex",
    "help",
]
SlashCommandRetrievalHint = Literal[
    "none", "conversation", "project", "personal_knowledge"
]


class SlashCommandEffects(BaseModel):
    model_config = ConfigDict(frozen=True)

    intentKind: SlashCommandIntentKind
    retrievalHint: SlashCommandRetrievalHint


class SlashCommandDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    token: str
    label: str
    description: str
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    scaffold: str
    interactionModes: tuple[InteractionMode, ...]
    effects: SlashCommandEffects | None
    availability: Availability
    availabilityReason: AvailabilityReason | None


class SlashCommandCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    schemaVersion: int
    manifestRevision: str
    commands: tuple[SlashCommandDefinition, ...]


def _command(
    command_id: str,
    label: str,
    description: str,
    *,
    aliases: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    intent_kind: SlashCommandIntentKind | None = None,
    retrieval_hint: SlashCommandRetrievalHint = "none",
    composer_control: bool = False,
) -> SlashCommandDefinition:
    modes: list[InteractionMode] = []
    effects = None
    if intent_kind is not None:
        modes.append("chat_intent")
        effects = SlashCommandEffects(
            intentKind=intent_kind, retrievalHint=retrieval_hint
        )
    if composer_control:
        modes.append("composer_control")
    token = f"/{command_id}"
    return SlashCommandDefinition(
        id=command_id,
        token=token,
        label=label,
        description=description,
        aliases=aliases,
        keywords=keywords,
        scaffold=token,
        interactionModes=tuple(modes),
        effects=effects,
        availability="unknown",
        availabilityReason="eligibility_not_evaluated",
    )


_COMMANDS = tuple(
    sorted(
        (
            _command(
                "thread",
                "Thread",
                "Start or switch a conversation thread.",
                aliases=("chat", "conversation"),
                keywords=("reply", "turn"),
                intent_kind="conversation",
                retrieval_hint="conversation",
            ),
            _command(
                "doc",
                "Document",
                "Add or reference a document.",
                aliases=("do", "docs", "document"),
                keywords=("file", "note", "reference"),
                intent_kind="knowledge",
                retrieval_hint="personal_knowledge",
            ),
            _command(
                "project",
                "Project",
                "Scope the request to a project.",
                # /workspace owns its canonical token. /repo remains a project alias.
                aliases=("repo",),
                keywords=("scope", "context"),
                intent_kind="workspace",
                retrieval_hint="project",
                composer_control=True,
            ),
            _command(
                "workspace",
                "Workspace",
                "Work across the current workspace.",
                aliases=("root", "local"),
                keywords=("folder", "environment"),
                intent_kind="workspace",
                retrieval_hint="project",
            ),
            _command(
                "profile",
                "Profile",
                "Choose an identity or persona.",
                aliases=("identity", "persona", "account"),
                keywords=("user", "role"),
                intent_kind="conversation",
            ),
            _command(
                "flow",
                "Flow",
                "Switch to a workflow step.",
                aliases=("pipeline", "sequence"),
                keywords=("process", "mode"),
                intent_kind="automation",
            ),
            _command(
                "secure",
                "Secure",
                "Tighten access or permissions.",
                aliases=("permission", "lock"),
                keywords=("privacy", "acl"),
                intent_kind="security",
            ),
            _command(
                "connect",
                "Connect",
                "Link sources or peers.",
                aliases=("sync", "attach"),
                keywords=("bridge", "federate"),
                intent_kind="integration",
            ),
            _command(
                "obsidian",
                "Obsidian",
                "Pull relevant notes from an active Obsidian connector for this turn.",
                aliases=("obs", "vault", "notes"),
                keywords=("connector", "context", "knowledge", "markdown"),
                intent_kind="integration",
            ),
            _command(
                "codex_entry",
                "Codex Entry",
                "Generate a Codex Entry draft from the conversation.",
                aliases=("codex", "entry", "artifact"),
                keywords=("save", "draft", "note", "capture", "preserve"),
                intent_kind="codex",
            ),
            _command(
                "help",
                "Help",
                "Show command help.",
                aliases=("?", "commands"),
                keywords=("guide", "menu"),
                intent_kind="help",
            ),
            _command(
                "provider",
                "Provider",
                "Choose an available inference provider.",
                keywords=("inference", "backend"),
                composer_control=True,
            ),
            _command(
                "model",
                "Model",
                "Choose a compatible chat model.",
                keywords=("inference", "llm"),
                composer_control=True,
            ),
            _command(
                "mode",
                "Mode",
                "Choose the current inference mode.",
                keywords=("inference",),
                composer_control=True,
            ),
            _command(
                "retrieval",
                "Retrieval",
                "Choose the existing retrieval source.",
                keywords=("source", "context"),
                composer_control=True,
            ),
        ),
        key=lambda command: command.token,
    )
)


def _normalize_token(token: str) -> str:
    return token.strip().lstrip("/").strip().casefold()


def _build_token_index(
    commands: tuple[SlashCommandDefinition, ...],
) -> dict[str, SlashCommandDefinition]:
    if len({command.id for command in commands}) != len(commands):
        raise ValueError("duplicate slash command ID")

    index = {_normalize_token(command.token): command for command in commands}
    if len(index) != len(commands):
        raise ValueError("duplicate canonical slash command token")

    # Reserve every canonical token before registering aliases. A shadowing
    # or ambiguous alias must be resolved in the catalog before publication.
    for command in commands:
        for alias in command.aliases:
            key = _normalize_token(alias)
            if key in index:
                raise ValueError(
                    f"slash command alias {alias!r} for {command.id!r} "
                    f"collides with a token or alias of {index[key].id!r}"
                )
            index[key] = command
    return index


_TOKEN_INDEX = _build_token_index(_COMMANDS)
SLASH_INTENT_IDS = frozenset(
    command.id for command in _COMMANDS if command.effects is not None
)


def _manifest_revision(commands: tuple[SlashCommandDefinition, ...]) -> str:
    canonical_json = json.dumps(
        {
            "schemaVersion": SCHEMA_VERSION,
            "commands": [command.model_dump(mode="json") for command in commands],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"sha256:{hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()}"


SLASH_COMMAND_MANIFEST = SlashCommandCatalog(
    schemaVersion=SCHEMA_VERSION,
    manifestRevision=_manifest_revision(_COMMANDS),
    commands=_COMMANDS,
)


def resolve_slash_command(token: str) -> SlashCommandDefinition | None:
    """Resolve an exact canonical token or alias."""
    return _TOKEN_INDEX.get(_normalize_token(token))


def search_slash_commands(query: str, limit: int) -> SlashCommandCatalog:
    matches: tuple[SlashCommandDefinition, ...] = ()
    exact = resolve_slash_command(query)
    if exact is not None:
        matches = (exact,)
    elif normalized := _normalize_token(query):
        # The token index inserts canonical tokens before aliases, and each
        # group follows manifest order. Keep the first match for each command.
        token_matches = (
            command
            for key, command in _TOKEN_INDEX.items()
            if key.startswith(normalized)
        )
        keyword_matches = (
            command
            for command in _COMMANDS
            if any(
                keyword.casefold().startswith(normalized)
                for keyword in command.keywords
            )
        )
        matches = tuple(dict.fromkeys(chain(token_matches, keyword_matches)))

    return SlashCommandCatalog(
        schemaVersion=SLASH_COMMAND_MANIFEST.schemaVersion,
        manifestRevision=SLASH_COMMAND_MANIFEST.manifestRevision,
        commands=matches[:limit],
    )
