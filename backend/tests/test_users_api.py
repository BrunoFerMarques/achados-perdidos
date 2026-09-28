import os

import psycopg
import pytest

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}


@pytest.fixture(autouse=True)
def empty_users():
    # the API commits for real, so clear the table before and after each test
    def truncate():
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("TRUNCATE users RESTART IDENTITY")

    truncate()
    yield
    truncate()


def test_create_user_returns_201_without_password(client):
    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Maria Silva"
    assert body["email"] == "maria@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_password_is_stored_hashed(client):
    user_id = client.post("/v1/users", json=MARIA).json()["id"]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        (password_hash,) = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    assert password_hash.startswith("$argon2")


def test_duplicate_email_returns_409(client):
    client.post("/v1/users", json=MARIA)

    response = client.post("/v1/users", json={**MARIA, "email": "MARIA@example.com"})

    assert response.status_code == 409
    assert response.json() == {"detail": "E-mail já cadastrado"}


@pytest.mark.parametrize(
    "override",
    [
        {"email": "maria.example.com"},
        {"name": "   "},
        {"password": "curta"},
    ],
)
def test_invalid_payload_returns_422(client, override):
    response = client.post("/v1/users", json={**MARIA, **override})

    assert response.status_code == 422


def test_returns_503_when_database_is_down(client, monkeypatch):
    # nothing listens on port 1, so the connection is refused right away
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/none")

    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}
