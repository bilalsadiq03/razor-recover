"""add transaction id to payments

Revision ID: add_transaction_id
Revises: YOUR_PREVIOUS_REVISION
Create Date: ...
"""

from alembic import op
import sqlalchemy as sa


revision = "add_transaction_id"
down_revision = "3574791cef6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "transaction_id",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_payments_transaction_id",
        "payments",
        ["transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payments_transaction_id",
        table_name="payments",
    )

    op.drop_column(
        "payments",
        "transaction_id",
    )