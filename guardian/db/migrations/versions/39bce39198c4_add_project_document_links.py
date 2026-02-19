"""add project_document_links

Revision ID: 39bce39198c4
Revises: 9f3d2b1a7c4e
Create Date: 2026-02-18 22:59:20.922860

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "39bce39198c4"
down_revision: Union[str, Sequence[str], None] = "9f3d2b1a7c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
