import os
from datetime import timedelta

import jwt
import pytest

from services.token import TokenService

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
MARIA_LOGIN = {"email": MARIA["email"], "password": MARIA["password"]}


@pytest.fixture
def maria(client):
    return client.post("/v1/users", json=MARIA).json()


def test_login_returns_bearer_token_for_the_user(client, maria):
    response = client.post("/v1/auth/login", json=MARIA_LOGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], os.environ["JWT_SECRET"], algorithms=["HS256"])
    assert claims["sub"] == str(maria["id"])


def test_login_ignores_email_case(client, maria):
    response = client.post("/v1/auth/login", json={**MARIA_LOGIN, "email": "MARIA@example.com"})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {**MARIA_LOGIN, "password": "senha-errada"},
        {**MARIA_LOGIN, "email": "ninguem@example.com"},
    ],
)
def test_login_with_wrong_credentials_returns_401(client, maria, credentials):
    response = client.post("/v1/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json() == {"detail": "E-mail ou senha inválidos"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "payload",
    [{"email": "maria@example.com"}, {"email": "maria.example.com", "password": "senha-forte"}],
)
def test_login_with_invalid_payload_returns_422(client, payload):
    response = client.post("/v1/auth/login", json=payload)

    assert response.status_code == 422


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_returns_the_logged_in_user(client, maria):
    token = client.post("/v1/auth/login", json=MARIA_LOGIN).json()["access_token"]

    response = client.get("/v1/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == maria


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic bWFyaWE6c2VuaGE="}])
def test_me_without_bearer_token_returns_401(client, headers):
    response = client.get("/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_with_invalid_token_returns_401(client):
    response = client.get("/v1/auth/me", headers=bearer("nao-e-um-jwt"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido ou expirado"}


def test_me_with_expired_token_returns_401(client, maria):
    token = TokenService(os.environ["JWT_SECRET"], timedelta(seconds=-1)).issue(maria["id"])

    response = client.get("/v1/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido ou expirado"}


def test_token_of_deleted_user_returns_401(client, maria):
    token = client.post("/v1/auth/login", json=MARIA_LOGIN).json()["access_token"]
    client.delete(f"/v1/users/{maria['id']}")

    response = client.get("/v1/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido ou expirado"}
