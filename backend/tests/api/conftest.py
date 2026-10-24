import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app


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
