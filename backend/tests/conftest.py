import os

import pytest
from dotenv import load_dotenv

import migrate


def pytest_configure(config):
    load_dotenv()
    # no CI não tem .env, mas qualquer segredo serve porque os testes assinam os próprios tokens
    os.environ.setdefault("JWT_SECRET", "test-secret-only-for-the-pytest-run")


@pytest.fixture(scope="session")
def test_database():
    # usado por tests/integration e tests/api; tests/unit nunca pede, então roda sem banco
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

    # a API lê o DATABASE_URL a cada pedido, então aqui ele aponta pro banco de teste
    os.environ["DATABASE_URL"] = test_database_url
    migrate.main()
