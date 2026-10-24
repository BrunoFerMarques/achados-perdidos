"""Apply pending migrations from migrations/versions/ to DATABASE_URL.

Usage: python migrate.py  (same as `alembic upgrade head`)

Kept as the entry point so the Render start command and the tests don't depend on the Alembic CLI.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, pool, text

from db import database_url

ALEMBIC_INI = Path(__file__).parent / "alembic.ini"

# before Alembic, a plain SQL runner recorded each applied file in schema_migrations;
# 001_create_users.sql created exactly what revision f74061d19e30 creates
LEGACY_FILE = "001_create_users.sql"
LEGACY_REVISION = "f74061d19e30"


def main():
    load_dotenv()
    config = Config(ALEMBIC_INI)
    _adopt_legacy_database(config)
    command.upgrade(config, "head")


def _adopt_legacy_database(config: Config) -> None:
    """Hand a database created by the old SQL runner over to Alembic, keeping its data."""
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        tables = inspect(conn).get_table_names()
        if "schema_migrations" not in tables or "alembic_version" in tables:
            return
        applied = set(conn.scalars(text("SELECT version FROM schema_migrations")))

    if LEGACY_FILE in applied:
        # the tables already exist: record the revision as applied instead of running it
        command.stamp(config, LEGACY_REVISION)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE schema_migrations"))


if __name__ == "__main__":
    main()
