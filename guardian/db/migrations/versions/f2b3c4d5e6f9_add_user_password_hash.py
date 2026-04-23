"""add password hash to users

Revision ID: f2b3c4d5e6f9
Revises: f2b3c4d5e6f8
Create Date: 2026-04-20 00:00:00.000000
"""

import secrets
from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f9"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bootstrap_password_hash() -> str:
    bootstrap_password = secrets.token_urlsafe(32).encode("utf-8")
    return bcrypt.hashpw(
        bootstrap_password,
        bcrypt.gensalt(),
    ).decode("utf-8")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET password_hash = :password_hash WHERE password_hash IS NULL"
        ),
        {"password_hash": _bootstrap_password_hash()},
    )
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
