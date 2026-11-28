"""Add persistent model carts.

Revision ID: 6f3d9b2a1c8e
Revises: e5f6a7b8c9d0
"""

import sqlalchemy as sa
from alembic import op

revision = "6f3d9b2a1c8e"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_cart_item",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["hubfiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "file_id"),
    )


def downgrade():
    op.drop_table("model_cart_item")
