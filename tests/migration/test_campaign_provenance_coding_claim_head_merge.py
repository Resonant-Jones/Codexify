"""Campaign provenance and coding-claim heads — reunification merge contract.

PR #958 (Guardian coding-worker claim schema) and PR #959 (campaign-continuation
authority provenance) each introduced a migration descending from the same
mainline parent, ``3a91d7c4e8b2``. Merged into one mainline they form two
independent heads, and Alembic cannot upgrade to ``head`` while that is true:
every database migration to the tip of the graph fails with "Multiple head
revisions are present".

PR #970 landed the mergepoint that reunifies them, ``a3115f64dda8``. This
contract is the graph-invariant coverage for that mergepoint.

This contract covers the **graph only**: that the two branches are joined by one
explicit mergepoint, that the graph has exactly one head, that both branches
remain reachable from it, and that the mergepoint carries no schema operation
of its own.

**What this contract deliberately does not claim.** The two branches touch
disjoint tables — ``agent_runs`` on the coding-claim side and
``campaign_continuation_authorities`` on the campaign side — so nothing here
claims that the merge reconciles any column, constraint, or index. It also
claims nothing about the behaviour of either feature. The branch-specific
contracts own that: ``test_guardian_coding_claim_schema_merge.py`` for the
coding-claim schema and
``test_campaign_continuation_authority_provenance_migration.py`` for the
campaign provenance columns.
"""

from __future__ import annotations

import pathlib

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The mergepoint that joins the two split heads back into one.
MERGE_REVISION = "a3115f64dda8"
#: The head the campaign-continuation branch carried.
CAMPAIGN_HEAD = "b7e2c4a1d903"
#: The head the Guardian coding-claim branch carried.
CODING_CLAIM_HEAD = "c8e42a91d307"
#: The shared parent both heads descended from.
SHARED_PARENT = "3a91d7c4e8b2"

MERGE_FILENAME = (
    "a3115f64dda8_merge_guardian_coding_claim_and_campaign_heads.py"
)


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )


def _lineage(head: str) -> set[str]:
    script = _script_directory()
    return {revision.revision for revision in script.walk_revisions(head=head)}


# ---------------------------------------------------------------------------
# Migration graph
# ---------------------------------------------------------------------------


def test_the_graph_has_exactly_one_head() -> None:
    """The graph carries exactly one head.

    Which revision is the head legitimately advances whenever a migration or a
    mergepoint is added above it, so the invariant under test is that the graph
    is single-headed -- not that it is still some particular revision.
    """
    heads = tuple(_script_directory().get_heads())
    assert len(heads) == 1, f"expected exactly one head, got {heads}"


def test_the_mergepoint_joins_both_split_heads() -> None:
    """The mergepoint has exactly the two heads as its parents."""
    merge = _script_directory().get_revision(MERGE_REVISION)
    assert merge is not None
    assert set(merge.down_revision) == {CAMPAIGN_HEAD, CODING_CLAIM_HEAD}


def test_both_split_heads_reach_the_mergepoint() -> None:
    """Neither branch was dropped or replaced by the merge."""
    lineage = _lineage(MERGE_REVISION)
    assert CAMPAIGN_HEAD in lineage, "campaign head is not an ancestor"
    assert CODING_CLAIM_HEAD in lineage, "coding-claim head is not an ancestor"
    assert SHARED_PARENT in lineage


def test_the_mergepoint_is_reachable_from_the_single_head() -> None:
    """The mergepoint stays inside the current head's ancestry."""
    heads = tuple(_script_directory().get_heads())
    assert len(heads) == 1, f"expected exactly one head, got {heads}"
    assert MERGE_REVISION in _lineage(heads[0])


def test_the_mergepoint_carries_no_schema_operation() -> None:
    """The mergepoint is graph-only: the branches touch disjoint tables.

    ``campaign_continuation_authorities`` is owned by the campaign branch and
    ``agent_runs`` by the coding-claim branch, so there is nothing for the
    mergepoint to reconcile and it must not issue any DDL of its own.
    """
    source = (
        REPO_ROOT / "guardian" / "db" / "migrations" / "versions" / MERGE_FILENAME
    )
    body = source.read_text()
    for operation in (
        "op.add_column",
        "op.create_table",
        "op.create_index",
        "op.create_check_constraint",
        "op.create_unique_constraint",
        "op.drop_column",
        "op.drop_table",
    ):
        assert operation not in body, f"merge revision contains {operation}"


def test_the_historical_migrations_keep_their_identities() -> None:
    """The two branch migrations are unchanged and keep their own parents.

    Reunifying the graph must not rewrite either branch's history: the campaign
    migration still descends from ``3a91d7c4e8b2`` and the coding-claim
    mergepoint still joins ``3a91d7c4e8b2`` with the coding-worker head.
    """
    script = _script_directory()

    campaign = script.get_revision(CAMPAIGN_HEAD)
    assert campaign is not None
    assert campaign.down_revision == SHARED_PARENT

    coding_claim = script.get_revision(CODING_CLAIM_HEAD)
    assert coding_claim is not None
    assert set(coding_claim.down_revision) == {SHARED_PARENT, "d86f2a4b1c90"}
