"""merge lost_reports migration

Revision ID: 09a76496321b
Revises: 4767acacf5e3, a1e0ec4df065
Create Date: 2026-11-21 20:37:28.072196

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "09a76496321b"
down_revision: str | Sequence[str] | None = ("4767acacf5e3", "a1e0ec4df065")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
