"""merge campaign provenance and coding claim heads

Revision ID: f4e8b2c6d103
Revises: b7e2c4a1d903, c8e42a91d307
Create Date: 2026-10-30 17:05:00.000000

The Guardian coding-claim integration (PR #958) and the campaign-continuation
provenance work (PR #959) each introduced a migration descending from the same
mainline parent, ``3a91d7c4e8b2``. Merged into one mainline, they form two
independent heads:

* ``c8e42a91d307`` -- the Guardian coding-claim mergepoint
* ``b7e2c4a1d903`` -- the campaign-continuation provenance migration

A graph with two heads cannot be upgraded with Alembic's ``head`` target, so
``alembic upgrade head`` fails with "Multiple head revisions are present" and
every test that migrates a database to the tip of the graph breaks.

This revision is the same explicit mergepoint the repository has used twice
before to reunify split lineages (``2e865c4a9b10`` and ``3a91d7c4e8b2``). It
joins both heads and restores a single head, and it carries no schema
operation of its own: the two branches touch disjoint tables, so no column,
constraint, or index needs reconciling. ``campaign_continuation_authorities``
is owned by the campaign branch and ``agent_runs`` by the coding-claim
branch, and nothing in either branch depends on the other.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4e8b2c6d103'
down_revision: Union[str, Sequence[str], None] = ('b7e2c4a1d903', 'c8e42a91d307')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
