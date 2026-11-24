import os
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app
from dependencies import get_clock
from domain.roles import Role


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def empty_users(test_database):
    # the API commits for real, so every test starts and ends with empty tables;
    # CASCADE also empties collection_point_attendants, which points at both
    def truncate():
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("TRUNCATE users, collection_points RESTART IDENTITY CASCADE")

    truncate()
    yield
    truncate()


@dataclass
class Account:
    """Um usuário cadastrado, com uma sessão logada."""

    body: dict  # o usuário como a API devolve
    headers: dict[str, str]  # envie estes para agir como este usuário

    @property
    def id(self) -> int:
        return self.body["id"]


@pytest.fixture
def signup(client):
    """Cadastra pela API e faz login. Devolve signup(data, role=Role.USUARIO) -> Account."""

    def signup(data: dict, role: Role = Role.USUARIO) -> Account:
        body = client.post("/v1/users", json=data).json()
        if role != Role.USUARIO:
            # a API nunca cadastra ninguém acima de usuario, então o teste muda o papel direto
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                conn.execute("UPDATE users SET role = %s WHERE id = %s", (role, body["id"]))
            body = {**body, "role": role}
        login = {"email": data["email"], "password": data["password"]}
        token = client.post("/v1/auth/login", json=login).json()["access_token"]
        return Account(body, {"Authorization": f"Bearer {token}"})

    return signup


class FakeClock:
    """Um relógio que só anda quando o teste manda."""

    def __init__(self, now: datetime):
        self.current = now

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def clock():
    """Troca o relógio da API por um FakeClock; ande com `clock.current += timedelta(...)`."""
    fake = FakeClock(datetime(2026, 11, 16, 12, 0, tzinfo=UTC))
    app.dependency_overrides[get_clock] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_clock)
