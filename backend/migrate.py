"""Apply pending migrations from migrations/versions/ to DATABASE_URL.

Usage: python migrate.py  (same as `alembic upgrade head`)

Kept as the entry point so the Render start command and the tests don't depend on the Alembic CLI.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


def main():
    command.upgrade(Config(ALEMBIC_INI), "head")


if __name__ == "__main__":
    main()
