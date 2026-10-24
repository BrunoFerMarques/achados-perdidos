import pytest
from sqlalchemy.orm import Session

from db import get_engine


@pytest.fixture
def db():
    # everything a test writes is rolled back, so the test database stays clean;
    # a commit inside the test only releases a savepoint
    with get_engine().connect() as conn:
        transaction = conn.begin()
        with Session(conn, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
