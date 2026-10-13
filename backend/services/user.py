import psycopg
from argon2 import PasswordHasher

_hasher = PasswordHasher()


class EmailAlreadyExists(Exception):
    pass


def create_user(conn: psycopg.Connection, name: str, email: str, password: str) -> dict:
    try:
        # commits on a fresh connection, becomes a savepoint inside an open transaction
        with conn.transaction():
            return conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, created_at
                """,
                (name, email, _hasher.hash(password)),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise EmailAlreadyExists(email) from None


def get_user(conn: psycopg.Connection, user_id: int) -> dict | None:
    return conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = %s", (user_id,)
    ).fetchone()


def list_users(conn: psycopg.Connection, limit: int, offset: int) -> list[dict]:
    return conn.execute(
        "SELECT id, name, email, created_at FROM users ORDER BY id LIMIT %s OFFSET %s",
        (limit, offset),
    ).fetchall()


def update_user(
    conn: psycopg.Connection,
    user_id: int,
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> dict | None:
    password_hash = _hasher.hash(password) if password is not None else None
    try:
        with conn.transaction():
            # a NULL parameter keeps the column as it is
            return conn.execute(
                """
                UPDATE users
                SET name = COALESCE(%s, name),
                    email = COALESCE(%s, email),
                    password_hash = COALESCE(%s, password_hash)
                WHERE id = %s
                RETURNING id, name, email, created_at
                """,
                (name, email, password_hash, user_id),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise EmailAlreadyExists(email) from None
