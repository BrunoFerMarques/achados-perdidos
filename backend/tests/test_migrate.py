import os

import psycopg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import make_url

import migrate

SCHEMA = "legacy_migration_test"

# what the SQL runner used before Alembic left in the database
LEGACY_SQL = r"""
CREATE TABLE schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations (version) VALUES ('001_create_users.sql');

CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE users (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT        NOT NULL,
    email          TEXT        NOT NULL,
    password_hash  TEXT        NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_name_check CHECK (btrim(name) <> ''),
    CONSTRAINT users_email_check CHECK (email ~ '^[^@\s]+@[^@\s]+$')
);
CREATE UNIQUE INDEX users_email_key ON users (lower(email));
CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO users (name, email, password_hash) VALUES ('Maria Silva', 'maria@example.com', 'hash');
"""


@pytest.fixture
def legacy_database(monkeypatch):
    # a separate schema plays the old database, so the migrated test schema is left alone
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.execute(f"CREATE SCHEMA {SCHEMA}")
    url = make_url(os.environ["DATABASE_URL"]).update_query_dict(
        {"options": f"-csearch_path={SCHEMA}"}
    )
    legacy_url = url.render_as_string(hide_password=False)
    with psycopg.connect(legacy_url, autocommit=True) as conn:
        conn.execute(LEGACY_SQL)
    monkeypatch.setenv("DATABASE_URL", legacy_url)

    yield legacy_url

    with psycopg.connect(legacy_url, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def test_legacy_database_is_handed_over_to_alembic_keeping_its_data(legacy_database):
    migrate.main()

    head = ScriptDirectory.from_config(Config(migrate.ALEMBIC_INI)).get_current_head()
    with psycopg.connect(legacy_database) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [(head,)]
        assert conn.execute("SELECT to_regclass('schema_migrations')").fetchone() == (None,)
        assert conn.execute("SELECT email FROM users").fetchall() == [("maria@example.com",)]


def test_migrating_a_handed_over_database_again_changes_nothing(legacy_database):
    migrate.main()

    migrate.main()

    with psycopg.connect(legacy_database) as conn:
        assert conn.execute("SELECT count(*) FROM users").fetchone() == (1,)
