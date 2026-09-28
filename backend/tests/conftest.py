import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

import migrate
from api import app


def pytest_configure(config):
    load_dotenv()
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    if not test_database_url:
        raise pytest.UsageError(
            "Defina TEST_DATABASE_URL com um banco só para testes (veja .env.example)."
        )
    if test_database_url == os.environ.get("DATABASE_URL"):
        raise pytest.UsageError("TEST_DATABASE_URL não pode ser o mesmo banco de DATABASE_URL.")

    # the API reads DATABASE_URL on every request; during tests it must hit the test database
    os.environ["DATABASE_URL"] = test_database_url


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    migrate.main()


@pytest.fixture
def client():
    return TestClient(app)
