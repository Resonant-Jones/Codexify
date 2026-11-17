"""Private metadata never promotes HTTP operations or public manifest entries."""

from fastapi import FastAPI
import pytest

from guardian.command_bus.accepted_knowledge_manifest import (
    private_knowledge_commands,
    with_private_knowledge_commands,
)
from guardian.command_bus.manifest import build_command_index
from guardian.connections import chat_pilot
from guardian.connections.github.router import operations_router as github
from guardian.connections.notion.router import operations_router as notion
from guardian.core.chat_account_custody import (
    AcceptedChatCatalogBinding,
    ChatAccountCustodyUnavailable,
    resolve_accepted_chat_catalog_account,
    resolve_accepted_chat_account,
)
from guardian.db.models import ChatCompletionAttempt
from tests.core import test_chat_account_custody as custody
from tests.core.test_chat_account_custody import seed, COMMAND, HASH

store = custody.store


def test_private_specs_match_provider_routes_without_mounting_or_public_projection():
    quarantined = FastAPI()
    original = quarantined.openapi()
    public, _ = build_command_index(quarantined)
    private = with_private_knowledge_commands(public)
    assert not set(chat_pilot.COMMANDS) & set(public)
    assert set(chat_pilot.COMMANDS) <= set(private)
    assert quarantined.openapi() is original and original["paths"] == {}
    foreground = FastAPI()
    foreground.include_router(github)
    foreground.include_router(notion)
    routed, _ = build_command_index(foreground)
    for command in private_knowledge_commands():
        assert command == routed[command.command_id]


def test_private_alias_collision_is_not_overwritten():
    commands = private_knowledge_commands()
    with pytest.raises(ValueError, match="collision"):
        with_private_knowledge_commands({commands[0].aliases[0]: commands[1]})


def test_catalog_binding_never_substitutes_for_frozen_execution(store):
    task = seed(store)
    with store._sa_session() as session:
        attempt = session.get(ChatCompletionAttempt, task.request_id)
        attempt.tool_turn_id = attempt.tool_command_id = attempt.tool_args_hash = None
        attempt.tool_checkpoint_at = None
    binding = resolve_accepted_chat_catalog_account(store, task)
    assert type(binding) is AcceptedChatCatalogBinding
    assert not hasattr(binding, "command_id")
    for command in (COMMAND, None, ""):
        with pytest.raises(ChatAccountCustodyUnavailable):
            resolve_accepted_chat_account(
                store, task, command_id=command, args_hash=HASH
            )
    task.user_id = "b@example.com"
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_catalog_account(store, task)
