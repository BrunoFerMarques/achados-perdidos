"""add transfer_to to items

Revision ID: 9c41d27e5b18
Revises: 4767acacf5e3
Create Date: 2026-11-20 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c41d27e5b18"
down_revision: str | Sequence[str] | None = "4767acacf5e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("items", sa.Column("transfer_to_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("items_transfer_to_id_fkey"),
        "items",
        "collection_points",
        ["transfer_to_id"],
        ["id"],
    )
    # RN05: a destination exactly while the item is on its way, and never the point it left
    op.create_check_constraint(
        op.f("items_transfer_to_id_check"),
        "items",
        "(status = 'em_transferencia') = (transfer_to_id IS NOT NULL) "
        "AND (transfer_to_id IS NULL OR transfer_to_id <> collection_point_id)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("items_transfer_to_id_check"), "items", type_="check")
    op.drop_constraint(op.f("items_transfer_to_id_fkey"), "items", type_="foreignkey")
    op.drop_column("items", "transfer_to_id")
