"""Aplica as migrações pendentes no DATABASE_URL.

Uso: python migrate.py  (mesma coisa que `alembic upgrade head`)

Existe pra o start do Render e os testes não dependerem da CLI do Alembic.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, pool, text

from db import database_url

ALEMBIC_INI = Path(__file__).parent / "alembic.ini"

# antes do Alembic, um script simples registrava os .sql aplicados em schema_migrations,
# e o 001_create_users.sql criava o mesmo que a revisão f74061d19e30
LEGACY_FILE = "001_create_users.sql"
LEGACY_REVISION = "f74061d19e30"


def main():
    load_dotenv()
    config = Config(ALEMBIC_INI)
    _adopt_legacy_database(config)
    command.upgrade(config, "head")


def _adopt_legacy_database(config: Config) -> None:
    """Passa pro Alembic um banco criado pelo script antigo, sem perder os dados."""
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        tables = inspect(conn).get_table_names()
        if "schema_migrations" not in tables or "alembic_version" in tables:
            return
        applied = set(conn.scalars(text("SELECT version FROM schema_migrations")))

    if LEGACY_FILE in applied:
        # as tabelas já existem, então só marca a revisão como aplicada
        command.stamp(config, LEGACY_REVISION)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE schema_migrations"))


if __name__ == "__main__":
    main()
