import psycopg
import pytest

INSERT_USER = "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id"


def test_user_is_created(db):
    (user_id,) = db.execute(INSERT_USER, ("Maria Silva", "maria@example.com", "hash")).fetchone()

    row = db.execute("SELECT name, email FROM users WHERE id = %s", (user_id,)).fetchone()
    assert row == ("Maria Silva", "maria@example.com")


def test_email_is_unique_ignoring_case(db):
    db.execute(INSERT_USER, ("Maria Silva", "maria@example.com", "hash"))

    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(INSERT_USER, ("Maria Souza", "MARIA@example.com", "hash"))


def test_invalid_email_is_rejected(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(INSERT_USER, ("Maria Silva", "maria.example.com", "hash"))
