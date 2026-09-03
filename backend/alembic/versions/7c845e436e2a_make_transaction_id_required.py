"""make transaction id required

Revision ID: make_transaction_id_required
Revises: add_transaction_id
"""

from alembic import op


revision = "make_transaction_id_required"
down_revision = "add_transaction_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "payments",
        "transaction_id",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "payments",
        "transaction_id",
        nullable=True,
    )