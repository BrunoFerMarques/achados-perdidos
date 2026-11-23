# reivindicação no banco: índices únicos, model Claim e as travas de linha que seguram dois
# pedidos simultâneos
import re
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text

from domain.claims import ClaimStatus, RejectionReason
from domain.custody import CustodyEvent
from domain.errors import InvalidTransition, ItemAlreadyClaimed, ItemNotAvailable
from domain.items import ItemStatus
from domain.roles import Role
from models import Category, Claim, CollectionPoint, Color, Item, ItemQuestion, Location, User
from repositories.unit_of_work import UnitOfWork
from services.claim import ClaimService

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
    """Acha os itens."""
    return add_user(db, "Maria Silva", "maria@example.com")


@pytest.fixture
def joao(db):
    """Reivindica os itens."""
    return add_user(db, "João Souza", "joao@example.com")


@pytest.fixture
def carlos(db):
    """Também reivindica."""
    return add_user(db, "Carlos Reis", "carlos@example.com")


def first_id(db, model) -> int:
    # categorias, locais e cores vêm das migrações
    return db.scalar(select(model.id).order_by(model.id).limit(1))


@pytest.fixture
def new_item(db, maria):
    """new_item(status="disponivel") -> Item: um item da Maria num ponto de coleta novo."""
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
    # direto no status, como as transições (ou uma tarefa agendada) o deixariam
    return Claim(item_id=item.id, claimant_id=claimant.id, status=status, score=1.0)


def reload(db, claim: Claim) -> Claim:
    # expira o que está carregado, para cada atributo lido abaixo ir ao banco
    db.expire_all()
    return claim


# --- índice de uma reivindicação por usuário e item (vira ItemAlreadyClaimed) ---


@pytest.mark.parametrize(
    "earlier", [ClaimStatus.PENDING, ClaimStatus.APPROVED, ClaimStatus.REJECTED]
)
def test_rn11_second_claim_of_the_same_user_on_an_item_is_item_already_claimed(
    uow, item, joao, earlier
):
    # o service checa antes; o índice pega dois pedidos que passaram juntos pela checagem
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

    # das mais antigas para as mais novas, na ordem em que o atendente analisa
    pending = uow.claims.list_pending(None, staff_id=maria.id)
    assert [c.claimant_id for c in pending] == [joao.id, carlos.id]


# --- índice de uma aprovada por item (vira ItemNotAvailable) ---


def test_rn13_second_approved_claim_on_an_item_is_item_not_available(uow, item, joao, carlos):
    # dois atendentes aprovando duas reivindicações juntos: os dois viram o item na prateleira
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


# --- o que conta como reivindicação ativa ---


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


# --- o model Claim ---


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
    # a hora vem do relógio injetável, não do banco, porque o blocking.py compara com clock.now()
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
    assert saved.pickup_deadline == NOW + timedelta(days=5)
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
    # rejeitada é final
    claim = Claim.submit(item, joao.id, WRONG, 0.0, at=NOW)
    uow.claims.add(claim)
    uow.commit()

    with pytest.raises(InvalidTransition):
        claim.approve(by=maria.id, at=NOW, pickup_code="AB12CD")

    assert claim.status == ClaimStatus.REJECTED
    assert item.status == ItemStatus.AVAILABLE


def test_completed_claim_cannot_be_cancelled(uow, new_item, joao):
    # o item foi retirado; cancelar não pode devolvê-lo à prateleira
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
    # a aprovação gravou a reserva, e a retirada grava a devolução depois
    assert [(r.event, r.collection_point_id, r.actor_id, r.at) for r in saved.item.history] == [
        (CustodyEvent.RESERVATION, point_id, maria.id, NOW),
        (CustodyEvent.RETURN, point_id, maria.id, NOW + timedelta(days=1)),
    ]


# --- travas de linha (usuário ao criar; reivindicação ao aprovar, cancelar e retirar) ---


def test_user_lock_selects_the_row_for_update(uow, joao, sent_sql):
    uow.users.lock(joao.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_user_lock_reloads_a_row_changed_by_another_transaction(db, uow, joao):
    # lê do banco antes da mudança, senão um SELECT comum guardaria a cópia velha
    db.refresh(joao)
    assert joao.unblocked_at is None
    db.execute(
        text("UPDATE users SET unblocked_at = :at WHERE id = :id"), {"at": NOW, "id": joao.id}
    )

    locked = uow.users.lock(joao.id)

    # o mesmo objeto, agora com o que o banco tem; a checagem do bloqueio o lê logo depois
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
    # a aprovação que esperou o cancelamento tem que ver "cancelada", não o pendente que leu
    claim = claim_in(item, joao, ClaimStatus.PENDING)
    uow.claims.add(claim)
    uow.commit()
    # lê do banco antes da mudança, senão um SELECT comum guardaria a cópia velha
    db.refresh(claim)
    assert claim.status == ClaimStatus.PENDING
    db.execute(text("UPDATE claims SET status = 'cancelada' WHERE id = :id"), {"id": claim.id})

    locked = uow.claims.get_for_update(claim.id)

    assert locked is claim
    assert locked.status == ClaimStatus.CANCELLED


def test_active_claims_of_a_deleted_account_are_selected_for_update(uow, item, joao, sent_sql):
    # aprovação rodando junto com a exclusão espera, em vez de reservar o item pra ninguém
    uow.claims.add(claim_in(item, joao, ClaimStatus.PENDING))
    uow.commit()

    uow.claims.lock_active_by_claimant(joao.id)

    assert sent_sql[-1].rstrip().endswith("FOR UPDATE")


def test_claim_get_for_update_of_an_unknown_claim_is_none(uow):
    assert uow.claims.get_for_update(999_999_999) is None


def test_rn14_pending_claims_of_an_item_are_selected_for_update(uow, item, joao, sent_sql):
    # cancelamento rodando junto com a retirada espera, em vez de ser sobrescrito pela rejeição
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
    # pendente, mas em outro item: a retirada de `item` não mexe nela
    uow.claims.add(claim_in(other_item, carlos, ClaimStatus.PENDING))
    uow.commit()

    locked = uow.claims.lock_pending_by_item(item.id)

    assert sorted(c.id for c in locked) == [first.id, second.id]


# --- a análise também trava o item ---


class StoppedClock:
    """O relógio do service, parado em NOW."""

    def now(self) -> datetime:
        return NOW


@pytest.fixture
def admin(db):
    """Analisa em qualquer ponto, sem precisar de atendente vinculado ao ponto do item."""
    user = add_user(db, "Admin", "admin@example.com")
    user.role = Role.ADMIN
    db.flush()
    return user


def locked_tables(statements: list[str]) -> list[str]:
    # a tabela que cada SELECT ... FOR UPDATE lê, na ordem em que foram enviados
    return [
        re.search(r"\bFROM (\w+)", statement).group(1)
        for statement in statements
        if statement.rstrip().endswith("FOR UPDATE")
    ]


def test_approval_locks_the_claim_and_then_its_item(uow, item, joao, admin, sent_sql):
    # envio, chegada ou recebimento do mesmo item espera a aprovação, ou o contrário. A ordem
    # é sempre reivindicação primeiro e item depois
    claim = claim_in(item, joao, ClaimStatus.PENDING)
    uow.claims.add(claim)
    uow.commit()

    ClaimService(uow, StoppedClock()).approve(admin, claim.id)

    assert locked_tables(sent_sql) == ["claims", "items"]
    assert claim.status == ClaimStatus.APPROVED


def test_rn13_approval_that_waited_for_a_transfer_sees_the_item_on_its_way(
    db, uow, item, joao, admin
):
    # a transferência fez commit enquanto a aprovação esperava a trava. Reservar com a cópia
    # antiga tiraria o item de uma prateleira que ele já deixou
    claim = claim_in(item, joao, ClaimStatus.PENDING)
    uow.claims.add(claim)
    destination = CollectionPoint(name="Restaurante")
    db.add(destination)
    uow.commit()
    # lê do banco antes da mudança, senão um SELECT comum guardaria a cópia velha
    db.refresh(item)
    assert item.status == ItemStatus.AVAILABLE
    db.execute(
        text("UPDATE items SET status = 'em_transferencia', transfer_to_id = :to WHERE id = :id"),
        {"to": destination.id, "id": item.id},
    )

    with pytest.raises(ItemNotAvailable):
        ClaimService(uow, StoppedClock()).approve(admin, claim.id)

    assert (claim.status, item.status) == (ClaimStatus.PENDING, ItemStatus.IN_TRANSFER)
