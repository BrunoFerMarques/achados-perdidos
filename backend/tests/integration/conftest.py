import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from db import get_engine


@pytest.fixture(autouse=True)
def use_test_database(test_database):
    """Todo teste daqui usa um banco, então confere se é o de teste."""


@pytest.fixture
def db():
    # tudo que o teste grava é desfeito no fim, e um commit dentro do teste só libera um
    # savepoint
    with get_engine().connect() as conn:
        transaction = conn.begin()
        with Session(conn, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def sent_sql(db):
    """Os comandos SQL que a sessão envia daqui em diante."""
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    conn = db.connection()
    event.listen(conn, "before_cursor_execute", record)
    yield statements
    event.remove(conn, "before_cursor_execute", record)
