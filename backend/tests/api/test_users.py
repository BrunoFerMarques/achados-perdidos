import os

import psycopg
import pytest
from argon2 import PasswordHasher

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "outra-senha"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "mais-uma-senha"}


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


def test_get_user_returns_user(client):
    created = client.post("/v1/users", json=MARIA).json()

    response = client.get(f"/v1/users/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_user_returns_404(client):
    response = client.get("/v1/users/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado"}


def test_list_users_returns_users_in_creation_order(client):
    created = [client.post("/v1/users", json=user).json() for user in (MARIA, JOAO, ANA)]

    response = client.get("/v1/users")

    assert response.status_code == 200
    assert response.json() == created


def test_list_users_is_paginated(client):
    for user in (MARIA, JOAO, ANA):
        client.post("/v1/users", json=user)

    response = client.get("/v1/users", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == ["joao@example.com"]


def test_list_users_returns_empty_list_when_there_are_no_users(client):
    response = client.get("/v1/users")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_users_with_invalid_pagination_returns_422(client, params):
    response = client.get("/v1/users", params=params)

    assert response.status_code == 422


def test_update_user_changes_only_the_given_fields(client):
    created = client.post("/v1/users", json=MARIA).json()

    response = client.patch(f"/v1/users/{created['id']}", json={"name": "  Maria Souza  "})

    assert response.status_code == 200
    assert response.json() == {**created, "name": "Maria Souza"}
    assert client.get(f"/v1/users/{created['id']}").json()["name"] == "Maria Souza"


def test_update_user_password_stores_new_hash(client):
    user_id = client.post("/v1/users", json=MARIA).json()["id"]

    response = client.patch(f"/v1/users/{user_id}", json={"password": "nova-senha-forte"})

    assert response.status_code == 200
    assert "password_hash" not in response.json()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        (password_hash,) = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    assert PasswordHasher().verify(password_hash, "nova-senha-forte")


def test_update_user_to_taken_email_returns_409(client):
    client.post("/v1/users", json=MARIA)
    joao_id = client.post("/v1/users", json=JOAO).json()["id"]

    response = client.patch(f"/v1/users/{joao_id}", json={"email": "MARIA@example.com"})

    assert response.status_code == 409
    assert response.json() == {"detail": "E-mail já cadastrado"}


def test_update_unknown_user_returns_404(client):
    response = client.patch("/v1/users/999", json={"name": "Maria Souza"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": "   "},
        {"email": "maria.example.com"},
        {"password": "curta"},
    ],
)
def test_update_user_with_invalid_payload_returns_422(client, payload):
    user_id = client.post("/v1/users", json=MARIA).json()["id"]

    response = client.patch(f"/v1/users/{user_id}", json=payload)

    assert response.status_code == 422


def test_delete_user_returns_204_and_removes_user(client):
    user_id = client.post("/v1/users", json=MARIA).json()["id"]

    response = client.delete(f"/v1/users/{user_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/v1/users/{user_id}").status_code == 404


def test_deleted_user_email_can_be_used_again(client):
    user_id = client.post("/v1/users", json=MARIA).json()["id"]
    client.delete(f"/v1/users/{user_id}")

    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 201


def test_delete_unknown_user_returns_404(client):
    response = client.delete("/v1/users/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado"}


def test_returns_503_when_database_is_down(client, monkeypatch):
    # nothing listens on port 1, so the connection is refused right away
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/none")

    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}


def test_new_user_is_usuario(client):
    response = client.post("/v1/users", json=MARIA)

    assert response.json()["role"] == "usuario"


def test_cannot_register_as_admin(client):
    response = client.post("/v1/users", json={**MARIA, "role": "admin"})

    assert response.json()["role"] == "usuario"
