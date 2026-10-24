import os

import jwt
import pytest

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
MARIA_LOGIN = {"email": MARIA["email"], "password": MARIA["password"]}

pytestmark = pytest.mark.usefixtures("empty_users")


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
