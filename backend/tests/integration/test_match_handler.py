import logging
from datetime import date

import pytest
from sqlalchemy import select

from domain.items import ItemStatus
from domain.lost_reports import LostReportStatus
from domain.match import DEFAULT_CONFIG, calculate_match
from domain.roles import Role
from models import Category, CollectionPoint
from services.item import ItemService
from services.lost_report import LostReportService
from services.match_handler import MatchHandler


@pytest.fixture
def owner(new_user):
    return new_user("alice@example.com")


@pytest.fixture
def admin(new_user, uow):
    user = new_user("admin@example.com")
    user.role = Role.ADMIN
    uow.commit()
    return user


@pytest.fixture
def item_service(uow, stopped_clock):
    handler = MatchHandler(uow)
    return ItemService(uow, stopped_clock, handler.on_item_available)


@pytest.fixture
def report_service(uow):
    handler = MatchHandler(uow)
    return LostReportService(uow, handler.on_report_created)


# --- RN30: geração automática de notificações ---


def test_rn30_receiving_matching_item_creates_notification(
    uow, owner, admin, origin, new_item, new_report, item_service
):
    report = new_report(owner)
    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    notifications = uow.notifications.list_by_user(owner.id)

    assert item.status == ItemStatus.AVAILABLE
    assert len(notifications) == 1
    assert notifications[0].lost_report_id == report.id
    assert notifications[0].item_id == item.id


def test_rn30_creating_report_matches_available_item(uow, owner, refs, new_item, report_service):
    item = new_item(ItemStatus.AVAILABLE)
    category_id, location_id, color_id = refs

    report = report_service.create(
        owner,
        category_id,
        location_id,
        color_id,
        "Garrafa azul",
        date(2026, 11, 14),
    )

    notifications = uow.notifications.list_by_user(owner.id)

    assert len(notifications) == 1
    assert notifications[0].lost_report_id == report.id
    assert notifications[0].item_id == item.id


# --- RN30: filtros e pontuação ---


def test_rn30_different_category_does_not_notify(
    db, uow, owner, admin, origin, new_item, new_report, item_service
):
    report = new_report(owner)
    item = new_item(ItemStatus.REGISTERED)

    other_category = db.scalar(
        select(Category.id).where(Category.id != report.category_id).limit(1)
    )
    assert other_category is not None

    item.category_id = other_category
    uow.commit()

    item_service.receive(admin, item.id, origin.id)

    assert uow.notifications.list_by_user(owner.id) == []


def test_rn30_score_below_cutoff_does_not_notify(
    uow, owner, admin, origin, new_item, new_report, item_service
):
    report = new_report(owner)
    item = new_item(ItemStatus.REGISTERED)

    report.description = "Carteira vermelha"
    report.lost_date = date(2026, 11, 1)
    uow.commit()

    # A rejeição deve ocorrer pela pontuação,
    # não pelos filtros eliminatórios.
    result = calculate_match(report, item)

    assert result.rejected_reason is None
    assert result.score < DEFAULT_CONFIG.min_score
    assert not result.matched

    item_service.receive(admin, item.id, origin.id)

    assert uow.notifications.list_by_user(owner.id) == []


def test_rn30_incompatible_dates_do_not_notify(
    uow, owner, admin, origin, new_item, new_report, item_service
):
    new_report(
        owner,
        lost_date=date(2026, 11, 18),
    )
    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    assert uow.notifications.list_by_user(owner.id) == []


@pytest.mark.parametrize(
    "status",
    [
        LostReportStatus.ENCERRADO,
        LostReportStatus.EXPIRADO,
    ],
)
def test_rn30_inactive_reports_are_not_notified(
    uow, owner, admin, origin, new_item, new_report, item_service, status
):
    new_report(owner, status=status)
    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    assert uow.notifications.list_by_user(owner.id) == []


@pytest.mark.parametrize(
    "status",
    [
        ItemStatus.REGISTERED,
        ItemStatus.RESERVED,
        ItemStatus.RETURNED,
    ],
)
def test_rn30_unavailable_items_are_not_matched(uow, owner, refs, new_item, report_service, status):
    new_item(status)
    category_id, location_id, color_id = refs

    report_service.create(
        owner,
        category_id,
        location_id,
        color_id,
        "Garrafa azul",
        date(2026, 11, 14),
    )

    assert uow.notifications.list_by_user(owner.id) == []


# --- RN30: múltiplos matches ---


def test_rn30_matching_reports_from_different_users_are_notified(
    uow, owner, admin, origin, new_user, new_item, new_report, item_service
):
    second_owner = new_user("bob@example.com")

    first_report = new_report(owner)
    second_report = new_report(second_owner)

    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    first = uow.notifications.list_by_user(owner.id)
    second = uow.notifications.list_by_user(second_owner.id)

    assert len(first) == 1
    assert len(second) == 1

    assert first[0].lost_report_id == first_report.id
    assert second[0].lost_report_id == second_report.id

    assert first[0].item_id == item.id
    assert second[0].item_id == item.id


def test_rn31_same_user_with_two_reports_gets_two_notifications(
    uow, owner, admin, origin, new_item, new_report, item_service
):
    first_report = new_report(owner)
    second_report = new_report(owner)

    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    notifications = uow.notifications.list_by_user(owner.id)

    assert len(notifications) == 2

    assert {n.lost_report_id for n in notifications} == {
        first_report.id,
        second_report.id,
    }

    assert all(n.item_id == item.id for n in notifications)


def test_rn30_new_report_matches_multiple_available_items(
    uow, owner, refs, new_item, report_service
):
    first = new_item(ItemStatus.AVAILABLE)
    second = new_item(ItemStatus.AVAILABLE)

    category_id, location_id, color_id = refs

    report = report_service.create(
        owner,
        category_id,
        location_id,
        color_id,
        "Garrafa azul",
        date(2026, 11, 14),
    )

    notifications = uow.notifications.list_by_user(owner.id)

    assert len(notifications) == 2

    assert {n.item_id for n in notifications} == {
        first.id,
        second.id,
    }

    assert all(n.lost_report_id == report.id for n in notifications)


# --- RN31: transferência e prevenção de duplicatas ---


def test_rn31_transfer_arrival_matches_without_duplicates(
    db,
    uow,
    owner,
    admin,
    origin,
    new_item,
    new_report,
    new_user,
    item_service,
    report_service,
    refs,
):
    first_report = new_report(owner)
    item = new_item(ItemStatus.REGISTERED)

    item_service.receive(admin, item.id, origin.id)

    assert len(uow.notifications.list_by_user(owner.id)) == 1

    destination = CollectionPoint(name="Restaurante")
    db.add(destination)
    uow.commit()

    item_service.transfer(admin, item.id, destination.id)

    assert item.status == ItemStatus.IN_TRANSFER

    second_owner = new_user("bob@example.com")
    category_id, location_id, color_id = refs

    second_report = report_service.create(
        second_owner,
        category_id,
        location_id,
        color_id,
        "Garrafa azul",
        date(2026, 11, 14),
    )

    # Enquanto estiver em trânsito, o item não participa do match.
    assert uow.notifications.list_by_user(second_owner.id) == []

    item_service.arrive(admin, item.id)

    first_notifications = uow.notifications.list_by_user(owner.id)
    second_notifications = uow.notifications.list_by_user(second_owner.id)

    assert item.status == ItemStatus.AVAILABLE

    # O relato antigo não recebe notificação duplicada.
    assert len(first_notifications) == 1
    assert first_notifications[0].lost_report_id == first_report.id
    assert first_notifications[0].item_id == item.id

    # O relato novo comprova que arrive disparou o match.
    assert len(second_notifications) == 1
    assert second_notifications[0].lost_report_id == second_report.id
    assert second_notifications[0].item_id == item.id


# --- Isolamento de falhas ---


def assert_match_error_logged(caplog):
    assert any(
        record.levelno == logging.ERROR
        and record.name == "services.match_handler"
        and record.exc_info is not None
        and isinstance(record.exc_info[1], RuntimeError)
        for record in caplog.records
    )


def test_match_failure_does_not_undo_item_receipt(
    db, uow, owner, admin, origin, new_item, new_report, item_service, monkeypatch, caplog
):
    new_report(owner)
    item = new_item(ItemStatus.REGISTERED)
    item_id = item.id

    original = uow.notifications.create_if_not_exists

    def fail_after_insert(report_id, item_id):
        original(report_id, item_id)
        raise RuntimeError("Falha simulada no match")

    monkeypatch.setattr(
        uow.notifications,
        "create_if_not_exists",
        fail_after_insert,
    )

    # O recebimento deve ser salvo antes de executar o handler.
    item_service.receive(admin, item_id, origin.id)

    db.expire_all()

    assert uow.items.get(item_id).status == ItemStatus.AVAILABLE
    assert uow.notifications.list_by_user(owner.id) == []

    assert_match_error_logged(caplog)


def test_match_failure_does_not_undo_report_creation(
    db, uow, owner, refs, new_item, report_service, monkeypatch, caplog
):
    new_item(ItemStatus.AVAILABLE)
    category_id, location_id, color_id = refs

    original = uow.notifications.create_if_not_exists

    def fail_after_insert(report_id, item_id):
        original(report_id, item_id)
        raise RuntimeError("Falha simulada no match")

    monkeypatch.setattr(
        uow.notifications,
        "create_if_not_exists",
        fail_after_insert,
    )

    # O relato deve ser salvo antes de executar o handler.
    report = report_service.create(
        owner,
        category_id,
        location_id,
        color_id,
        "Garrafa azul",
        date(2026, 11, 14),
    )

    report_id = report.id
    db.expire_all()

    assert uow.lost_reports.get(report_id) is not None
    assert uow.notifications.list_by_user(owner.id) == []

    assert_match_error_logged(caplog)


def test_match_failure_rolls_back_all_notifications_of_event(
    db, uow, owner, admin, origin, new_user, new_item, new_report, item_service, monkeypatch, caplog
):
    second_owner = new_user("bob@example.com")

    new_report(owner)
    new_report(second_owner)

    item = new_item(ItemStatus.REGISTERED)
    item_id = item.id

    original = uow.notifications.create_if_not_exists
    attempts = []

    def fail_on_second_insert(report_id, item_id):
        attempts.append(report_id)
        original(report_id, item_id)

        if len(attempts) == 2:
            raise RuntimeError("Falha simulada no segundo match")

    monkeypatch.setattr(
        uow.notifications,
        "create_if_not_exists",
        fail_on_second_insert,
    )

    item_service.receive(admin, item_id, origin.id)

    db.expire_all()

    assert len(attempts) == 2

    # A operação principal permanece salva.
    assert uow.items.get(item_id).status == ItemStatus.AVAILABLE

    # O rollback é por evento, não por par.
    assert uow.notifications.list_by_user(owner.id) == []
    assert uow.notifications.list_by_user(second_owner.id) == []

    assert_match_error_logged(caplog)
