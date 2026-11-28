"""Add fakenodo deposition table.

Revision ID: a9b8c7d6e5f4
Revises: e5f6a7b8c9d0
"""

import sqlalchemy as sa
from alembic import op

revision = "a9b8c7d6e5f4"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deposition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doi", sa.String(length=50), nullable=True),
        sa.Column("conceptdoi", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("files_changed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("deposition")