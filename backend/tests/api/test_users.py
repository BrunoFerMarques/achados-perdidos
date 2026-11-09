import os

import psycopg
import pytest
from argon2 import PasswordHasher

from domain.roles import Role

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "outra-senha"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "mais-uma-senha"}
ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}

NOT_AUTHENTICATED = {"detail": "Não autenticado"}
PERMISSION_DENIED = {"detail": "Sem permissão para esta operação"}
USER_NOT_FOUND = {"detail": "Usuário não encontrado"}


@pytest.fixture
def maria(signup):
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    return signup(JOAO)


@pytest.fixture
def admin(signup):
    return signup(ADMIN, Role.ADMIN)


# --- registering is public ---


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


def test_new_user_is_usuario(client):
    response = client.post("/v1/users", json=MARIA)

    assert response.json()["role"] == "usuario"


def test_cannot_register_as_admin(client):
    response = client.post("/v1/users", json={**MARIA, "role": "admin"})

    assert response.json()["role"] == "usuario"


def test_returns_503_when_database_is_down(client, monkeypatch):
    # nothing listens on port 1, so the connection is refused right away
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/none")

    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}


# --- every other route needs a login ---

PROTECTED_ROUTES = [
    ("GET", "/v1/users"),
    ("GET", "/v1/users/1"),
    ("PATCH", "/v1/users/1"),
    ("DELETE", "/v1/users/1"),
]


@pytest.mark.parametrize(("method", "url"), PROTECTED_ROUTES)
def test_protected_route_without_token_returns_401(client, method, url):
    response = client.request(method, url, json={"name": "Maria Souza"})

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED
    assert response.headers["WWW-Authenticate"] == "Bearer"


# --- a user manages their own account ---


def test_user_gets_own_account(client, maria):
    response = client.get(f"/v1/users/{maria.id}", headers=maria.headers)

    assert response.status_code == 200
    assert response.json() == maria.body


def test_update_user_changes_only_the_given_fields(client, maria):
    url = f"/v1/users/{maria.id}"

    response = client.patch(url, json={"name": "  Maria Souza  "}, headers=maria.headers)

    assert response.status_code == 200
    assert response.json() == {**maria.body, "name": "Maria Souza"}
    assert client.get(url, headers=maria.headers).json()["name"] == "Maria Souza"


def test_update_user_password_stores_new_hash(client, maria):
    response = client.patch(
        f"/v1/users/{maria.id}", json={"password": "nova-senha-forte"}, headers=maria.headers
    )

    assert response.status_code == 200
    assert "password_hash" not in response.json()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        (password_hash,) = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (maria.id,)
        ).fetchone()
    assert PasswordHasher().verify(password_hash, "nova-senha-forte")


def test_update_user_to_taken_email_returns_409(client, maria, joao):
    response = client.patch(
        f"/v1/users/{joao.id}", json={"email": "MARIA@example.com"}, headers=joao.headers
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "E-mail já cadastrado"}


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
def test_update_user_with_invalid_payload_returns_422(client, maria, payload):
    response = client.patch(f"/v1/users/{maria.id}", json=payload, headers=maria.headers)

    assert response.status_code == 422


def test_delete_user_returns_204_and_removes_user(client, maria, admin):
    response = client.delete(f"/v1/users/{maria.id}", headers=maria.headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/v1/users/{maria.id}", headers=admin.headers).status_code == 404


def test_deleted_user_email_can_be_used_again(client, maria):
    client.delete(f"/v1/users/{maria.id}", headers=maria.headers)

    response = client.post("/v1/users", json=MARIA)

    assert response.status_code == 201


# --- but not anyone else's ---


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_user_cannot_touch_another_account(client, maria, joao, method):
    response = client.request(
        method, f"/v1/users/{joao.id}", json={"name": "Invasora"}, headers=maria.headers
    )

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED
    assert client.get(f"/v1/users/{joao.id}", headers=joao.headers).json() == joao.body


def test_user_gets_403_not_404_for_an_unknown_account(client, maria):
    # the same answer for any id but your own, so nobody can probe which ids exist
    response = client.get("/v1/users/999", headers=maria.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


@pytest.mark.parametrize("role", [Role.USUARIO, Role.ATENDENTE])
def test_only_admin_lists_users(client, signup, role):
    account = signup(MARIA, role)

    response = client.get("/v1/users", headers=account.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


# --- an admin manages every account ---


def test_admin_lists_users_in_creation_order(client, admin, signup):
    others = [signup(user) for user in (MARIA, JOAO, ANA)]

    response = client.get("/v1/users", headers=admin.headers)

    assert response.status_code == 200
    assert response.json() == [admin.body] + [account.body for account in others]


def test_list_users_is_paginated(client, admin, signup):
    for user in (MARIA, JOAO, ANA):
        signup(user)

    response = client.get("/v1/users", params={"limit": 1, "offset": 2}, headers=admin.headers)

    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == ["joao@example.com"]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_users_with_invalid_pagination_returns_422(client, admin, params):
    response = client.get("/v1/users", params=params, headers=admin.headers)

    assert response.status_code == 422


def test_admin_gets_another_account(client, admin, maria):
    response = client.get(f"/v1/users/{maria.id}", headers=admin.headers)

    assert response.status_code == 200
    assert response.json() == maria.body


def test_admin_updates_another_account(client, admin, maria):
    response = client.patch(
        f"/v1/users/{maria.id}", json={"name": "Maria Souza"}, headers=admin.headers
    )

    assert response.status_code == 200
    assert response.json() == {**maria.body, "name": "Maria Souza"}


def test_admin_deletes_another_account(client, admin, maria):
    response = client.delete(f"/v1/users/{maria.id}", headers=admin.headers)

    assert response.status_code == 204
    assert client.get(f"/v1/users/{maria.id}", headers=admin.headers).status_code == 404


@pytest.mark.parametrize(
    ("method", "payload"), [("GET", None), ("PATCH", {"name": "Maria Souza"}), ("DELETE", None)]
)
def test_unknown_user_returns_404_to_admin(client, admin, method, payload):
    response = client.request(method, "/v1/users/999", json=payload, headers=admin.headers)

    assert response.status_code == 404
    assert response.json() == USER_NOT_FOUND
