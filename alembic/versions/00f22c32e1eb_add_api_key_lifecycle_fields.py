"""Add API key lifecycle fields

Revision ID: 00f22c32e1eb
Revises: 71d2ce7be718
Create Date: 2026-08-29 13:35:54.928966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00f22c32e1eb'
down_revision: Union[str, Sequence[str], None] = '71d2ce7be718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "api_key_created_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "api_key_expires_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "api_key_revoked_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    # Existing users need a creation timestamp before the ORM's
    # non-nullable model field can be used safely.
    users = sa.table(
        "users",
        sa.column("api_key_created_at", sa.DateTime()),
    )
    op.execute(
        users.update().where(
            users.c.api_key_created_at.is_(None)
        ).values(
            api_key_created_at=sa.func.current_timestamp()
        )
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "api_key_created_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("api_key_revoked_at")
        batch_op.drop_column("api_key_expires_at")
        batch_op.drop_column("api_key_created_at")
