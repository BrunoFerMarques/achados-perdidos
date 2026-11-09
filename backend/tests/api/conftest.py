import os
from dataclasses import dataclass

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app
from domain.roles import Role


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def empty_users(test_database):
    # the API commits for real, so every test starts and ends with an empty users table
    def truncate():
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("TRUNCATE users RESTART IDENTITY")

    truncate()
    yield
    truncate()


@dataclass
class Account:
    """A registered user with a logged-in session."""

    body: dict  # the user as the API returns it
    headers: dict[str, str]  # send these to act as this user

    @property
    def id(self) -> int:
        return self.body["id"]


@pytest.fixture
def signup(client):
    """Register through the API and log in. Returns signup(data, role=Role.USUARIO) -> Account."""

    def signup(data: dict, role: Role = Role.USUARIO) -> Account:
        body = client.post("/v1/users", json=data).json()
        if role != Role.USUARIO:
            # the API never registers anyone above usuario, so the test sets the role directly
            with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
                conn.execute("UPDATE users SET role = %s WHERE id = %s", (role, body["id"]))
            body = {**body, "role": role}
        login = {"email": data["email"], "password": data["password"]}
        token = client.post("/v1/auth/login", json=login).json()["access_token"]
        return Account(body, {"Authorization": f"Bearer {token}"})

    return signup
