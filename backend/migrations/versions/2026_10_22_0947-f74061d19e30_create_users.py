"""create users

Revision ID: f74061d19e30
Revises:
Create Date: 2026-10-22 09:47:39.405313

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f74061d19e30"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # shared by every table that has updated_at; autogenerate doesn't see functions or triggers
    op.execute(
        """
        CREATE FUNCTION set_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
        """
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(name) <> ''", name=op.f("users_name_check")),
        sa.CheckConstraint("email ~ '^[^@\\s]+@[^@\\s]+$'", name=op.f("users_email_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("users_pkey")),
    )
    # one account per e-mail, regardless of case
    op.create_index("users_email_key", "users", [sa.literal_column("lower(email)")], unique=True)
    op.execute(
        """
        CREATE TRIGGER users_set_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    # dropping the table also drops its index and trigger
    op.drop_table("users")
    op.execute("DROP FUNCTION set_updated_at()")
