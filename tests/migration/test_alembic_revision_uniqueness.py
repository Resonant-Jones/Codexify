"""Regression tests for the canonical Alembic revision graph."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MESSAGE_REQUEST_REVISION = "9e52b1d3c8fa"

#: The merge revision that unified the chat-deadline and campaign-authority
#: lineages. It is a historical revision inside the graph rather than the
#: current head, so it is named explicitly instead of being read off the
#: head.
CHAT_DEADLINE_CAMPAIGN_MERGE = "2e865c4a9b10"

#: The merge revision that joined the unified main lineage with the read-cursor
#: lineage. Like ``CHAT_DEADLINE_CAMPAIGN_MERGE`` it is a mergepoint rather than
#: the permanent head, so it is named explicitly and asserted to stay inside the
#: current head's ancestry.
READ_STATE_CAMPAIGN_MERGE = "3a91d7c4e8b2"

#: The merge revision that joined the Campaign Continuation Authority provenance
#: branch with the Guardian coding-claim branch. It is a mergepoint rather than
#: a permanent head, so it is named explicitly and asserted to stay inside the
#: current head's ancestry.
CAMPAIGN_CODING_CLAIM_MERGE = "a3115f64dda8"

#: The two lineages that ``CAMPAIGN_CODING_CLAIM_MERGE`` joins. The campaign
#: provenance revision was rooted at the pre-merge main head instead of at the
#: merge above it, which left the graph with two heads.
CAMPAIGN_PROVENANCE_REVISION = "b7e2c4a1d903"
CODING_CLAIM_MERGE_REVISION = "c8e42a91d307"


def _literal_assignment(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            target = node.target
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        else:
            continue

        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)

    raise AssertionError(f"{name} assignment missing")


def _migration_metadata() -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text())
        revision = _literal_assignment(tree, "revision")
        down_revision = _literal_assignment(tree, "down_revision")
        assert isinstance(revision, str)
        metadata[path.name] = {
            "revision": revision,
            "down_revision": down_revision,
        }
    return metadata


def test_alembic_revision_ids_are_unique_and_hosted_room_lineage_is_preserved():
    metadata = _migration_metadata()
    by_revision: defaultdict[str, list[str]] = defaultdict(list)
    for filename, values in metadata.items():
        by_revision[values["revision"]].append(filename)

    duplicates = {
        revision: filenames
        for revision, filenames in by_revision.items()
        if len(filenames) > 1
    }
    assert duplicates == {}

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    hosted_provenance = script.get_revision("7a91c4e2f6b8")
    hosted_actor = script.get_revision("8b02d5f3a7c9")
    browser_audit = script.get_revision("c3d4e5f6a7b8")
    delegation = script.get_revision("d4e5f6a7b8c9")
    email_login_alias = script.get_revision("c1a2b3c4d5e6")
    repository_bindings = script.get_revision("6e2b9c4a7d1f")
    origin_system = script.get_revision("1c0a2b3c4d5e")

    hosted_foundation = script.get_revision("b2c3d4e5f6a8")

    assert hosted_foundation.down_revision == "b2c3d4e5f6a7"
    assert hosted_provenance.down_revision == "b2c3d4e5f6a8"
    assert hosted_actor.down_revision == "7a91c4e2f6b8"
    assert (
        Path(browser_audit.path).name
        == "c3d4e5f6a7b8_add_browser_audit_log_table.py"
    )
    assert (
        Path(delegation.path).name
        == "d4e5f6a7b8c9_add_delegation_tables.py"
    )

    assert metadata["f4e7c1a2b3d4_add_channel_tables.py"]["down_revision"] == (
        "c3d4e5f6a7b8"
    )
    assert metadata[
        "e3f2a1b4c5d6_add_authenticated_principals_table.py"
    ]["down_revision"] == ("4c9d1e2f3a5b", "d4e5f6a7b8c9")
    assert email_login_alias.down_revision == "d0e1f2a3b4c6"

    assert repository_bindings is not None
    assert repository_bindings.down_revision == "c1a2b3c4d5e6"
    assert isinstance(repository_bindings.down_revision, str)

    assert origin_system is not None
    assert (
        Path(origin_system.path).name
        == "1c0a2b3c4d5e_add_chat_threads_origin_system.py"
    )
    assert origin_system.down_revision == "9d4c2a7e1b6f"
    assert isinstance(origin_system.down_revision, str)

    watchdog_successors = (
        ("2a6b7c8d9e0f", "1c0a2b3c4d5e"),
        ("3b7c8d9e0f1a", "2a6b7c8d9e0f"),
        ("4c7d8e9f0a1b", "3b7c8d9e0f1a"),
        ("5d8e9f0a1b2c", "4c7d8e9f0a1b"),
        ("6e9f0a1b2c3", "5d8e9f0a1b2c"),
    )
    for revision, expected_down_revision in watchdog_successors:
        migration = script.get_revision(revision)
        assert migration is not None
        assert migration.down_revision == expected_down_revision

    # The additive consent migration must extend onboarding, preserving all
    # existing branches rather than introducing another independent head.
    message_requests = script.get_revision(MESSAGE_REQUEST_REVISION)
    assert message_requests is not None
    assert message_requests.down_revision == "8d41a0c2b7ef"
    assert Path(message_requests.path).name == "9e52b1d3c8fa_add_message_request_consent.py"

    heads = script.get_heads()
    assert len(heads) == 1
    assert script.get_revision("d0e1f2a3b4c6").down_revision == (
        "8c4d2e7f1a9b",
        "c8d9e0f1a2b3",
    )


def test_chat_deadline_campaign_merge_preserves_both_installed_lineages():
    script = ScriptDirectory.from_config(Config(str(REPO_ROOT / "backend" / "alembic.ini")))
    merge = script.get_revision(CHAT_DEADLINE_CAMPAIGN_MERGE)
    assert merge.down_revision == ("f1a6d83b9024", "17b23052da6a")
    for installed_head in merge.down_revision:
        pending = list(script.iterate_revisions(CHAT_DEADLINE_CAMPAIGN_MERGE, installed_head, implicit_base=True))
        assert pending[0].revision == CHAT_DEADLINE_CAMPAIGN_MERGE
        assert installed_head not in {revision.revision for revision in pending}
        other_head = next(head for head in merge.down_revision if head != installed_head)
        assert other_head in {revision.revision for revision in pending}


def test_read_state_merge_joins_its_lineages_inside_the_current_head():
    """The read-state merge must join both branches, not replace or split them.

    Which revision is the head legitimately advances whenever a migration or a
    mergepoint is added above it, so the invariant under test is that this
    mergepoint still joins its two original parents and remains reachable from
    the single current head -- not that it is still the head itself.
    """
    script = ScriptDirectory.from_config(Config(str(REPO_ROOT / "backend" / "alembic.ini")))
    merge = script.get_revision(READ_STATE_CAMPAIGN_MERGE)
    assert merge.down_revision == ("7f2c9e1a4b63", "b3c8d1e5f7a2")
    for branch in merge.down_revision:
        pending = list(
            script.iterate_revisions(
                READ_STATE_CAMPAIGN_MERGE, branch, implicit_base=True
            )
        )
        assert pending[0].revision == READ_STATE_CAMPAIGN_MERGE
        assert branch not in {revision.revision for revision in pending}

    heads = script.get_heads()
    assert len(heads) == 1, f"expected exactly one head, got {heads}"
    head_lineage = {
        revision.revision
        for revision in script.iterate_revisions(heads[0], None, implicit_base=True)
    }
    # Both historical mergepoints stay ancestors of the head, so every
    # installed lineage they preserved remains preserved.
    assert READ_STATE_CAMPAIGN_MERGE in head_lineage
    assert CHAT_DEADLINE_CAMPAIGN_MERGE in head_lineage


def test_campaign_coding_claim_merge_joins_its_lineages_inside_the_current_head():
    """The campaign/coding-claim merge must join both branches, not replace them.

    The campaign provenance revision was rooted at the pre-merge main head
    rather than at the merge above it, so the graph carried two heads and
    ``alembic upgrade head`` failed with "Multiple head revisions are
    present".  The repair is a graph-only mergepoint.

    Which revision is the head legitimately advances whenever a migration or a
    mergepoint is added above it, so the invariant under test is that this
    mergepoint still joins its two original parents, that the graph has
    exactly one head, and that this mergepoint stays reachable from that head
    -- not that it is still the head itself.
    """
    script = ScriptDirectory.from_config(Config(str(REPO_ROOT / "backend" / "alembic.ini")))

    # 1. The mergepoint exists and is a revision of this repository.
    merge = script.get_revision(CAMPAIGN_CODING_CLAIM_MERGE)
    assert merge is not None

    # 2. It joins exactly the two expected parents.
    assert merge.down_revision == (
        CAMPAIGN_PROVENANCE_REVISION,
        CODING_CLAIM_MERGE_REVISION,
    )

    # 3. The graph has exactly one current head.
    heads = script.get_heads()
    assert len(heads) == 1, f"expected exactly one head, got {heads}"

    # 4. The mergepoint is reachable from that head, and both of its former
    #    heads remain in the head's ancestry.
    head_lineage = {
        revision.revision
        for revision in script.iterate_revisions(heads[0], None, implicit_base=True)
    }
    assert CAMPAIGN_CODING_CLAIM_MERGE in head_lineage
    for former_head in merge.down_revision:
        assert former_head in head_lineage

    # Neither parent lineage was rewritten: walking down from the mergepoint
    # reaches the other parent, and stops at the named one without containing
    # it.
    for installed_head in merge.down_revision:
        pending = list(
            script.iterate_revisions(
                CAMPAIGN_CODING_CLAIM_MERGE, installed_head, implicit_base=True
            )
        )
        assert pending[0].revision == CAMPAIGN_CODING_CLAIM_MERGE
        assert installed_head not in {revision.revision for revision in pending}
        other_head = next(head for head in merge.down_revision if head != installed_head)
        assert other_head in {revision.revision for revision in pending}

    # 5. Earlier historical mergepoints stay reachable, so the lineages they
    #    preserved remain preserved.
    assert READ_STATE_CAMPAIGN_MERGE in head_lineage
    assert CHAT_DEADLINE_CAMPAIGN_MERGE in head_lineage

    # 6. Revision IDs remain unique, including this mergepoint's.
    metadata = _migration_metadata()
    matching = [
        filename
        for filename, values in metadata.items()
        if values["revision"] == CAMPAIGN_CODING_CLAIM_MERGE
    ]
    assert len(matching) == 1, (
        f"{CAMPAIGN_CODING_CLAIM_MERGE} must be hosted by exactly one file, got {matching}"
    )
