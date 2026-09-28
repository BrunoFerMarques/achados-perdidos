"""Apply pending SQL migrations from migrations/, in filename order.

Usage: python migrate.py
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def main():
    load_dotenv()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     TEXT PRIMARY KEY,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        applied = {version for (version,) in conn.execute("SELECT version FROM schema_migrations")}

        pending = [f for f in sorted(MIGRATIONS_DIR.glob("*.sql")) if f.name not in applied]
        if not pending:
            print("No pending migrations.")
            return

        for file in pending:
            # one transaction per file: a failing migration leaves nothing behind
            with conn.transaction():
                conn.execute(file.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (file.name,))
            print(f"Applied: {file.name}")


if __name__ == "__main__":
    main()
