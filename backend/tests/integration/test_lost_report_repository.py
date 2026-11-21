from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.lost_reports import LostReportStatus
from models import Category, Color, Location, User
from models.lost_report import LostReport
from repositories.unit_of_work import UnitOfWork


@pytest.fixture
def refs(db: Session) -> tuple[int, int, int]:
    category_id = db.scalars(select(Category.id).limit(1)).first()
    location_id = db.scalars(select(Location.id).limit(1)).first()
    color_id = db.scalars(select(Color.id).limit(1)).first()
    assert category_id and location_id and color_id
    return category_id, location_id, color_id


def _make_user(uow: UnitOfWork, email: str) -> User:
    user = User(name="Tester", email=email, password_hash="hash")
    uow.users.add(user)
    uow.commit()
    return user


def _make_report(
    uow: UnitOfWork,
    user_id: int,
    refs: tuple[int, int, int],
    description: str = "Mochila preta",
    status: LostReportStatus = LostReportStatus.ATIVO,
) -> LostReport:
    category_id, location_id, color_id = refs
    report = LostReport(
        user_id=user_id,
        category_id=category_id,
        location_id=location_id,
        color_id=color_id,
        description=description,
        lost_date=date(2026, 11, 10),
        status=status,
    )
    uow.lost_reports.add(report)
    uow.commit()
    return report


def test_list_active_returns_only_ativo_reports(db: Session, refs):
    uow = UnitOfWork(db)
    user = _make_user(uow, "u1@example.com")

    active = _make_report(uow, user.id, refs, "Ativo", LostReportStatus.ATIVO)
    _make_report(uow, user.id, refs, "Encerrado", LostReportStatus.ENCERRADO)
    _make_report(uow, user.id, refs, "Expirado", LostReportStatus.EXPIRADO)

    result = uow.lost_reports.list_active()
    assert [r.id for r in result] == [active.id]


def test_list_by_user_returns_only_owner_reports_newest_first(db: Session, refs):
    uow = UnitOfWork(db)
    alice = _make_user(uow, "alice@example.com")
    bob = _make_user(uow, "bob@example.com")

    r1 = _make_report(uow, alice.id, refs, "Primeiro")
    r2 = _make_report(uow, alice.id, refs, "Segundo")
    _make_report(uow, bob.id, refs, "Do Bob")

    alice_reports = uow.lost_reports.list_by_user(alice.id)
    assert [r.id for r in alice_reports] == [r2.id, r1.id]


def test_deleting_user_cascades_to_lost_reports(db: Session, refs):
    uow = UnitOfWork(db)
    alice = _make_user(uow, "alice@example.com")
    report = _make_report(uow, alice.id, refs, "Carteira")
    report_id = report.id

    uow.users.delete(alice)
    uow.commit()

    db.expire_all()
    assert uow.lost_reports.get(report_id) is None
