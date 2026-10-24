import os

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import migrate
from api import app
from db import get_engine


def pytest_configure(config):
    load_dotenv()
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    if not test_database_url:
        raise pytest.UsageError(
            "Defina TEST_DATABASE_URL com um banco só para testes (veja .env.example)."
        )
    if test_database_url == os.environ.get("DATABASE_URL"):
        raise pytest.UsageError("TEST_DATABASE_URL não pode ser o mesmo banco de DATABASE_URL.")

    # CI has no .env; any secret works, since the tests sign and check their own tokens
    os.environ.setdefault("JWT_SECRET", "test-secret-only-for-the-pytest-run")

    # the API reads DATABASE_URL on every request; during tests it must hit the test database
    os.environ["DATABASE_URL"] = test_database_url


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    migrate.main()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    # everything a test writes is rolled back, so the test database stays clean;
    # a commit inside the test only releases a savepoint
    with get_engine().connect() as conn:
        transaction = conn.begin()
        with Session(conn, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def empty_users():
    # the API commits for real, so clear the table before and after each test
    def truncate():
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("TRUNCATE users RESTART IDENTITY")

    truncate()
    yield
    truncate()
