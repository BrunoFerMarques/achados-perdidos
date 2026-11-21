# Claims in the database (scope §6): the indexes behind RN11 and RN13, the Claim model and the
# row locks that keep two requests at once from racing past the service checks
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event, select, text

from domain.claims import ClaimStatus, RejectionReason
from domain.custody import CustodyEvent
from domain.errors import InvalidTransition, ItemAlreadyClaimed, ItemNotAvailable
from domain.items import ItemStatus
from models import Category, Claim, CollectionPoint, Color, Item, ItemQuestion, Location, User
from repositories.unit_of_work import UnitOfWork

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
RIGHT = ["azul", "banda queen", "8F3A"]
WRONG = ["verde", "nenhum", "0000"]


def add_user(db, name: str, email: str) -> User:
    user = User(name=name, email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def uow(db):
    return UnitOfWork(db)


@pytest.fixture
def maria(db):
    """Finds the items."""
    return add_user(db, "Maria Silva", "maria@example.com")


@pytest.fixture
def joao(db):
    """Claims them."""
    return add_user(db, "João Souza", "joao@example.com")


@pytest.fixture
def carlos(db):
    """Claims them too."""
    return add_user(db, "Carlos Reis", "carlos@example.com")


def first_id(db, model) -> int:
    # categories, locations and colors are seeded by the migrations
    return db.scalar(select(model.id).order_by(model.id).limit(1))


@pytest.fixture
def new_item(db, maria):
    """new_item(status="disponivel") -> Item: Maria's item at a new collection point."""
    point = CollectionPoint(name="Biblioteca")
    db.add(point)
    db.flush()

    def new_item(status: ItemStatus = ItemStatus.AVAILABLE) -> Item:
        item = Item(
            category_id=first_id(db, Category),
            location_id=first_id(db, Location),
            color_id=first_id(db, Color),
            collection_point_id=point.id,
            finder_id=maria.id,
            description="Garrafa azul com adesivo",
            found_date=date(2026, 11, 14),
            status=status,
            questions=[
                ItemQuestion(position=1, question="Qual a cor da capinha?", answer="Azul"),
                ItemQuestion(position=2, question="Tem algum adesivo? Qual?", answer="Banda Queen"),
                ItemQuestion(
                    position=3, question="Últimos 4 dígitos do número de série?", answer="8F3A"
                ),
            ],
        )
        db.add(item)
        db.flush()
        return item

    return new_item


@pytest.fixture
def item(new_item):
    return new_item()


def claim_in(item: Item, claimant: User, status: ClaimStatus) -> Claim:
    # straight to the status, as the transitions (or a scheduled task) would leave it
    return Claim(item_id=item.id, claimant_id=claimant.id, status=status, score=1.0)


def reload(db, claim: Claim) -> Claim:
    # expire what is loaded, so every attribute read below hits the database
    db.expire_all()
    return claim


# --- RN11: claims_claimant_item_key becomes ItemAlreadyClaimed ---


@pytest.mark.parametrize(
    "earlier", [ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.REJECTED]
)
def test_rn11_second_claim_of_the_same_user_on_an_item_is_item_already_claimed(
    uow, item, joao, earlier
):
    # the service checks it first; the index catches two requests that passed the check together
    uow.claims.add(claim_in(item, joao, earlier))
    uow.commit()

    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    with pytest.raises(ItemAlreadyClaimed):
        uow.commit()


@pytest.mark.parametrize(
    "earlier", [ClaimStatus.CANCELLED, ClaimStatus.COMPLETED, ClaimStatus.EXPIRED]
)
def test_rn11_closed_claim_lets_the_same_user_claim_the_item_again(uow, item, joao, earlier):
    uow.claims.add(claim_in(item, joao, earlier))
    uow.commit()

    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    uow.commit()

    assert [c.status for c in uow.claims.list_by_claimant(joao.id)] == [
        ClaimStatus.PENDING,
        earlier,
    ]


def test_rn11_other_users_claim_the_same_item(uow, item, joao, carlos, maria):
    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    uow.claims.add(claim_in(item, carlos, ClaimStatus.PENDING))
    uow.commit()

    # oldest first, the order the attendant reviews them in
    pending = uow.claims.list_pending(None, staff_id=maria.id)
    assert [c.claimant_id for c in pending] == [joao.id, carlos.id]


# --- RN13: claims_approved_item_key becomes ItemNotAvailable ---


def test_rn13_second_approved_claim_on_an_item_is_item_not_available(uow, item, joao, carlos):
    # two attendants approving two claims at once: both saw the item on the shelf
    first = claim_in(item, joao, ClaimStatus.PENDING)
    second = claim_in(item, carlos, ClaimStatus.PENDING)
    uow.claims.add(first)
    uow.claims.add(second)
    uow.commit()
    first.status = ClaimStatus.APPROVED
    uow.commit()

    second.status = ClaimStatus.APPROVED
    with pytest.raises(ItemNotAvailable):
        uow.commit()


@pytest.mark.parametrize(
    "earlier",
    [ClaimStatus.PENDING, ClaimStatus.REJECTED, ClaimStatus.CANCELLED, ClaimStatus.EXPIRED],
)
def test_rn13_only_an_approved_claim_keeps_another_from_being_approved(
    uow, item, joao, carlos, earlier
):
    uow.claims.add(claim_in(item, joao, earlier))
    uow.claims.add(claim_in(item, carlos, ClaimStatus.APPROVED))
    uow.commit()

    assert [c.status for c in uow.claims.list_by_claimant(carlos.id)] == [ClaimStatus.APPROVED]


# --- RN12: what counts as an active claim ---


@pytest.mark.parametrize(
    ("status", "active"),
    [
        (ClaimStatus.PENDING, 1),
        (ClaimStatus.APPROVED, 1),
        (ClaimStatus.REJECTED, 0),
        (ClaimStatus.CANCELLED, 0),
        (ClaimStatus.COMPLETED, 0),
        (ClaimStatus.EXPIRED, 0),
    ],
)
def test_rn12_only_pending_and_approved_claims_are_counted_as_active(
    uow, item, joao, status, active
):
    uow.claims.add(claim_in(item, joao, status))
    uow.commit()

    assert uow.claims.count_active(joao.id) == active
    assert len(uow.claims.lock_active_by_claimant(joao.id)) == active


# --- the Claim model ---


def test_submit_saves_each_answer_at_its_questions_position(db, uow, item, joao):
    claim = Claim.submit(item, joao.id, ["azul", "", "8F3A"], 2 / 3, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    saved = reload(db, claim)

    assert [(a.position, a.answer) for a in saved.answers] == [(1, "azul"), (2, ""), (3, "8F3A")]
    assert saved.score == pytest.approx(2 / 3)


def test_submit_that_passes_starts_pending_with_no_rejection(db, uow, item, joao):
    claim = Claim.submit(item, joao.id, RIGHT, 1.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    saved = reload(db, claim)

    assert (saved.status, saved.rejection_reason, saved.rejected_at) == (
        ClaimStatus.PENDING,
        None,
        None,
    )
    assert uow.claims.rejections_of(joao.id) == []


def test_rn15_submit_below_the_minimum_saves_a_failure_at_the_given_time(db, uow, item, joao):
    # the time comes from the injected clock, not from the database: blocking.py compares it
    # with clock.now()
    claim = Claim.submit(item, joao.id, WRONG, 0.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    saved = reload(db, claim)

    assert saved.status == ClaimStatus.REJECTED
    assert uow.claims.rejections_of(joao.id) == [(NOW, RejectionReason.LOW_SCORE)]


def test_submit_needs_one_answer_per_question(item, joao):
    with pytest.raises(ValueError):
        Claim.submit(item, joao.id, RIGHT[:2], 1.0, at=NOW)


def test_rn13_approve_saves_the_code_and_time_and_reserves_the_item(db, uow, item, joao, maria):
    claim = Claim.submit(item, joao.id, RIGHT, 1.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    claim.approve(by=maria.id, at=NOW, pickup_code="AB12CD")
    uow.commit()
    saved = reload(db, claim)

    assert (saved.status, saved.approved_at, saved.pickup_code) == (
        ClaimStatus.APPROVED,
        NOW,
        "AB12CD",
    )
    assert saved.pickup_deadline == NOW + timedelta(days=5)  # RN44
    assert saved.item.status == ItemStatus.RESERVED


def test_rn15_attendant_rejection_saves_a_failure_and_leaves_the_item(db, uow, item, joao):
    claim = Claim.submit(item, joao.id, RIGHT, 1.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    claim.reject(RejectionReason.ATTENDANT, at=NOW + timedelta(hours=1))
    uow.commit()
    saved = reload(db, claim)

    assert saved.status == ClaimStatus.REJECTED
    assert uow.claims.rejections_of(joao.id) == [
        (NOW + timedelta(hours=1), RejectionReason.ATTENDANT)
    ]
    assert saved.item.status == ItemStatus.AVAILABLE


def test_approving_a_rejected_claim_raises_and_leaves_the_item_on_the_shelf(uow, item, joao, maria):
    # RN01: rejected is final
    claim = Claim.submit(item, joao.id, WRONG, 0.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    with pytest.raises(InvalidTransition):
        claim.approve(by=maria.id, at=NOW, pickup_code="AB12CD")

    assert claim.status == ClaimStatus.REJECTED
    assert item.status == ItemStatus.AVAILABLE


def test_completed_claim_cannot_be_cancelled(uow, new_item, joao):
    # the item was picked up; cancelling must not put it back on the shelf
    item = new_item(ItemStatus.RETURNED)
    claim = claim_in(item, joao, ClaimStatus.COMPLETED)
    uow.claims.add(claim)
    uow.commit()

    with pytest.raises(InvalidTransition):
        claim.cancel(by=joao.id, at=NOW)

    assert claim.status == ClaimStatus.COMPLETED
    assert claim.item.status == ItemStatus.RETURNED


def test_rn06_pick_up_completes_the_claim_and_writes_devolucao(db, uow, item, joao, maria):
    point_id = item.collection_point_id
    claim = Claim.submit(item, joao.id, RIGHT, 1.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()
    claim.approve(by=maria.id, at=NOW, pickup_code="AB12CD")
    uow.commit()

    claim.pick_up(
        "AB12CD", point_id=point_id, document_checked=True, by=maria.id, at=NOW + timedelta(days=1)
    )
    uow.commit()
    saved = reload(db, claim)

    assert saved.status == ClaimStatus.COMPLETED
    assert saved.item.status == ItemStatus.RETURNED
    # RN06: the approval wrote the reservation, the pickup writes the return after it
    assert [(r.event, r.collection_point_id, r.actor_id, r.at) for r in saved.item.history] == [
        (CustodyEvent.RESERVATION, point_id, maria.id, NOW),
        (CustodyEvent.RETURN, point_id, maria.id, NOW + timedelta(days=1)),
    ]


# --- row locks (RN11, RN12, RN15 counted under the user's lock; cancel vs. approve or pickup) ---


@pytest.fixture
def sent_sql(db):
    """The SQL statements the session sends from here on."""
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    conn = db.connection()
    event.listen(conn, "before_cursor_execute", record)
    yield statements
    event.remove(conn, "before_cursor_execute", record)


def test_user_lock_selects_the_row_for_update(uow, joao, sent_sql):
    uow.users.lock(joao.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_user_lock_reloads_a_row_changed_by_another_transaction(db, uow, joao):
    # read from the database before the change below; a plain SELECT would keep this stale copy
    db.refresh(joao)
    assert joao.unblocked_at is None
    db.execute(
        text("UPDATE users SET unblocked_at = :at WHERE id = :id"), {"at": NOW, "id": joao.id}
    )

    locked = uow.users.lock(joao.id)

    # the same object, now with what the database holds; the block check reads it right after
    assert locked is joao
    assert locked.unblocked_at == NOW


def test_user_lock_of_an_unknown_user_is_none(uow):
    assert uow.users.lock(999_999_999) is None


def test_claim_get_for_update_selects_the_row_for_update(uow, item, joao, sent_sql):
    claim = claim_in(item, joao, ClaimStatus.PENDING)
    uow.claims.add(claim)
    uow.commit()

    uow.claims.get_for_update(claim.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_claim_get_for_update_reloads_a_row_changed_by_another_transaction(db, uow, item, joao):
    # an approval that waited for a cancellation must see "cancelada", not the pending it read
    claim = claim_in(item, joao, ClaimStatus.PENDING)
    uow.claims.add(claim)
    uow.commit()
    # read from the database before the change below; a plain SELECT would keep this stale copy
    db.refresh(claim)
    assert claim.status == ClaimStatus.PENDING
    db.execute(text("UPDATE claims SET status = 'cancelada' WHERE id = :id"), {"id": claim.id})

    locked = uow.claims.get_for_update(claim.id)

    assert locked is claim
    assert locked.status == ClaimStatus.CANCELLED


def test_active_claims_of_a_deleted_account_are_selected_for_update(uow, item, joao, sent_sql):
    # an approval racing the deletion waits for it, instead of reserving the item for nobody
    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    uow.commit()

    uow.claims.lock_active_by_claimant(joao.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_claim_get_for_update_of_an_unknown_claim_is_none(uow):
    assert uow.claims.get_for_update(999_999_999) is None


def test_rn14_pending_claims_of_an_item_are_selected_for_update(uow, item, joao, sent_sql):
    # a cancellation racing the pickup waits for it, instead of being overwritten by the rejection
    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    uow.commit()

    uow.claims.lock_pending_by_item(item.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


@pytest.mark.parametrize(
    "status",
    [
        ClaimStatus.APPROVED,
        ClaimStatus.REJECTED,
        ClaimStatus.CANCELLED,
        ClaimStatus.COMPLETED,
        ClaimStatus.EXPIRED,
    ],
)
def test_rn14_only_the_pending_claims_of_that_item_are_locked(
    db, uow, item, new_item, joao, carlos, status
):
    other_item = new_item()
    ana = add_user(db, "Ana Lima", "ana@example.com")
    first = claim_in(item, joao, ClaimStatus.PENDING)
    second = claim_in(item, ana, ClaimStatus.PENDING)
    uow.claims.add(first)
    uow.claims.add(second)
    uow.claims.add(claim_in(item, carlos, status))
    # pending, but on another item: the pickup of `item` leaves it alone
    uow.claims.add(claim_in(other_item, carlos, ClaimStatus.PENDING))
    uow.commit()

    locked = uow.claims.lock_pending_by_item(item.id)

    assert sorted(c.id for c in locked) == [first.id, second.id]
