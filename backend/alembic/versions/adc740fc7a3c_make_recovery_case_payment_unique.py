"""make recovery case payment unique

Revision ID: adc740fc7a3c
Revises: make_transaction_id_required
Create Date: 2026-09-03 14:37:17.680421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc740fc7a3c'
down_revision: Union[str, Sequence[str], None] = 'make_transaction_id_required'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_recovery_cases_payment_id",
        "recovery_cases",
        ["payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_recovery_cases_payment_id",
        "recovery_cases",
        type_="unique",
    )
