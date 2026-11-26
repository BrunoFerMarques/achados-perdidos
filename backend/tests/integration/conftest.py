from datetime import UTC, date, datetime

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from db import get_engine
from domain.items import ItemStatus
from domain.lost_reports import LostReportStatus
from models import (
    Category,
    CollectionPoint,
    Color,
    Item,
    ItemQuestion,
    Location,
    User,
)
from models.lost_report import LostReport
from repositories.unit_of_work import UnitOfWork


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


# --- Fixtures compartilhadas para match e notificações ---


NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


class StoppedClock:
    def now(self) -> datetime:
        return NOW


@pytest.fixture
def stopped_clock():
    return StoppedClock()


@pytest.fixture
def uow(db):
    return UnitOfWork(db)


@pytest.fixture
def refs(db):
    category_id = db.scalar(select(Category.id).limit(1))
    location_id = db.scalar(select(Location.id).limit(1))
    color_id = db.scalar(select(Color.id).limit(1))

    assert category_id is not None
    assert location_id is not None
    assert color_id is not None

    return category_id, location_id, color_id


@pytest.fixture
def new_user(uow):
    def create(email):
        user = User(
            name="Tester",
            email=email,
            password_hash="hash",
        )
        uow.users.add(user)
        uow.commit()
        return user

    return create


@pytest.fixture
def origin(db):
    point = CollectionPoint(name="Biblioteca")
    db.add(point)
    db.flush()
    return point


@pytest.fixture
def new_report(uow, refs):
    def create(
        user,
        status=LostReportStatus.ATIVO,
        description="Garrafa azul",
        lost_date=date(2026, 11, 14),
    ):
        category_id, location_id, color_id = refs

        report = LostReport(
            user_id=user.id,
            category_id=category_id,
            location_id=location_id,
            color_id=color_id,
            description=description,
            lost_date=lost_date,
            status=status,
        )

        uow.lost_reports.add(report)
        uow.commit()
        return report

    return create


@pytest.fixture
def new_item(uow, refs, origin):
    def create(status=ItemStatus.AVAILABLE):
        category_id, location_id, color_id = refs

        item = Item(
            category_id=category_id,
            location_id=location_id,
            color_id=color_id,
            collection_point_id=origin.id,
            description="Garrafa azul",
            found_date=date(2026, 11, 14),
            status=status,
            questions=[
                ItemQuestion(position=1, question="Cor?", answer="Azul"),
                ItemQuestion(position=2, question="Marca?", answer="Stanley"),
            ],
        )

        uow.items.add(item)
        uow.commit()
        return item

    return create
