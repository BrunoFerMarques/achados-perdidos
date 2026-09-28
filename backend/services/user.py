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
