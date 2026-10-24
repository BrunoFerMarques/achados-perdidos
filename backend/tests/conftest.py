import os

import pytest
from dotenv import load_dotenv

import migrate


def pytest_configure(config):
    load_dotenv()
    # CI has no .env; any secret works, since the tests sign and check their own tokens
    os.environ.setdefault("JWT_SECRET", "test-secret-only-for-the-pytest-run")


@pytest.fixture(scope="session")
def test_database():
    # used by tests/integration and tests/api; tests/unit never asks for it, so it runs without one
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.exit(
            "Defina TEST_DATABASE_URL com um banco só para testes (veja .env.example).",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
    if test_database_url == os.environ.get("DATABASE_URL"):
        pytest.exit(
            "TEST_DATABASE_URL não pode ser o mesmo banco de DATABASE_URL.",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )

    # the API reads DATABASE_URL on every request; during tests it must hit the test database
    os.environ["DATABASE_URL"] = test_database_url
    migrate.main()
