import psycopg

from security.passwords import hash_password

DEFAULT_ROLE = "user"


class EmailAlreadyRegisteredError(Exception):
    pass


def create_user(conn: psycopg.Connection, name: str, email: str, password: str) -> dict:
    # hash before opening the transaction: argon2 is deliberately slow
    password_hash = hash_password(password)
    try:
        with conn.transaction():
            user = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, created_at
                """,
                (name, email.lower(), password_hash),
            ).fetchone()
            granted = conn.execute(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT %s, id FROM roles WHERE name = %s
                """,
                (user["id"], DEFAULT_ROLE),
            )
            if granted.rowcount != 1:
                raise RuntimeError(f"default role '{DEFAULT_ROLE}' not found")
    except psycopg.errors.UniqueViolation:
        raise EmailAlreadyRegisteredError(email)
    return user
