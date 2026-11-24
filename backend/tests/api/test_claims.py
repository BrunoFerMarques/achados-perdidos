# reivindicação pela API: criar, cancelar, analisar e retirar no balcão
import os
from datetime import timedelta

import psycopg
import pytest

from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "senha-forte"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "senha-forte"}
CARLOS = {"name": "Carlos Reis", "email": "carlos@example.com", "password": "senha-forte"}

URL = "/v1/claims"
RIGHT = ["azul", "banda queen", "8F3A"]
WRONG = ["verde", "nenhum", "0000"]


def set_item_status(item_id: int, status: str) -> None:
    # coloca o item direto no status, sem passar pelo recebimento ou pela transferência
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("UPDATE items SET status = %s WHERE id = %s", (status, item_id))


def item_status(item_id: int) -> str:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        return conn.execute("SELECT status FROM items WHERE id = %s", (item_id,)).fetchone()[0]


@pytest.fixture
def admin(signup):
    return signup(ADMIN, Role.ADMIN)


@pytest.fixture
def maria(signup):
    """Acha os itens."""
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    """Reivindica os itens."""
    return signup(JOAO)


def new_point(client, admin, name: str) -> int:
    return client.post("/v1/collection-points", json={"name": name}, headers=admin.headers).json()[
        "id"
    ]


@pytest.fixture
def point(client, admin):
    return new_point(client, admin, "Biblioteca")


@pytest.fixture
def attendant(client, signup, admin, point):
    """Atendente que trabalha em `point`."""
    account = signup(ANA, Role.ATENDENTE)
    client.post(
        f"/v1/collection-points/{point}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )
    return account


@pytest.fixture
def other_attendant(client, signup, admin):
    """Atendente que trabalha em outro ponto."""
    account = signup(CARLOS, Role.ATENDENTE)
    other = new_point(client, admin, "Restaurante")
    client.post(
        f"/v1/collection-points/{other}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )
    return account


@pytest.fixture
def register(client, maria, point):
    """register(status="disponivel") -> id do item registrado pela Maria em `point`."""

    def first(url: str) -> int:
        return client.get(url).json()[0]["id"]

    body = {
        "category_id": first("/v1/categories"),
        "location_id": first("/v1/locations"),
        "color_id": first("/v1/colors"),
        "collection_point_id": point,
        "description": "Garrafa azul com adesivo",
        "found_date": "2026-11-14",
        "questions": [
            {"question": "Qual a cor da capinha?", "answer": "Azul"},
            {"question": "Tem algum adesivo? Qual?", "answer": "Banda Queen"},
            {"question": "Últimos 4 dígitos do número de série?", "answer": "8F3A"},
        ],
    }

    def register(status: str = "disponivel") -> int:
        item_id = client.post("/v1/items", json=body, headers=maria.headers).json()["id"]
        set_item_status(item_id, status)
        return item_id

    return register


@pytest.fixture
def item(register):
    return register()


def claim(client, account, item_id: int, answers: list[str] = RIGHT):
    return client.post(URL, json={"item_id": item_id, "answers": answers}, headers=account.headers)


# --- criando reivindicação ---


def test_claim_with_enough_right_answers_goes_to_review(client, joao, item, point, clock):
    response = claim(client, joao, item)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pendente"
    assert body["item_id"] == item
    assert body["collection_point_id"] == point
    assert body["pickup_code"] is None


def test_claim_tolerates_case_accents_and_one_typo(client, joao, item, clock):
    # "banda quen" está a uma letra de "Banda Queen"
    response = claim(client, joao, item, ["AZUL", "banda quen", "8f3a"])

    assert response.json()["status"] == "pendente"


def test_claim_below_the_minimum_score_is_rejected_at_once(client, joao, item, clock):
    # 1 de 3 certas fica abaixo de 60%
    response = claim(client, joao, item, ["azul", "nenhum", "0000"])

    assert response.status_code == 201
    assert response.json()["status"] == "rejeitada"


def test_rn21_claimant_never_sees_the_score_or_the_reason(client, joao, item, clock):
    body = claim(client, joao, item, WRONG).json()

    assert "score" not in body
    assert "rejection_reason" not in body


def test_rn23_expected_answers_never_reach_the_claimant(client, joao, item, clock):
    response = claim(client, joao, item, WRONG)
    mine = client.get(f"{URL}/me", headers=joao.headers)

    for text in (response.text, mine.text):
        assert "Banda Queen" not in text
        assert "8F3A" not in text


def questions_of(client, account, item_id: int):
    return client.get(f"{URL}/items/{item_id}/questions", headers=account.headers)


def test_claimant_gets_the_questions_without_the_answers(client, joao, item):
    # o formulário mostra as perguntas em ordem e nunca a resposta esperada
    response = questions_of(client, joao, item)

    assert response.status_code == 200
    assert response.json() == [
        {"position": 1, "question": "Qual a cor da capinha?"},
        {"position": 2, "question": "Tem algum adesivo? Qual?"},
        {"position": 3, "question": "Últimos 4 dígitos do número de série?"},
    ]


def test_rn10_finder_gets_no_form_for_their_own_item(client, maria, item):
    assert questions_of(client, maria, item).status_code == 403


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_only_users_get_the_claim_form(client, signup, item, role):
    assert questions_of(client, signup(JOAO, role), item).status_code == 403


def test_item_that_takes_no_claim_has_no_form(client, joao, register):
    assert questions_of(client, joao, register("reservado")).status_code == 409


def test_form_of_an_unknown_item_is_404(client, joao):
    assert questions_of(client, joao, 999).status_code == 404


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_staff_get_403_not_404_for_the_form_of_an_unknown_item(client, signup, role):
    # o papel é checado antes de buscar o item
    response = questions_of(client, signup(JOAO, role), 999)

    assert response.status_code == 403
    assert response.json() == {"detail": "Sem permissão para esta operação"}


def test_requires_login(client, item):
    response = client.post(URL, json={"item_id": item, "answers": RIGHT})

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", f"{URL}/me"),
        ("GET", f"{URL}/pending"),
        ("POST", f"{URL}/1/cancel"),
        ("POST", f"{URL}/1/approve"),
        ("POST", f"{URL}/1/reject"),
        ("GET", f"{URL}/approved"),
        ("POST", f"{URL}/1/pickup"),
        ("GET", f"{URL}/items/1/questions"),
    ],
)
def test_every_claim_route_requires_login(client, method, url):
    response = client.request(method, url)

    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado"}


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_only_users_claim(client, signup, item, role, clock):
    account = signup(JOAO, role)

    response = claim(client, account, item)

    assert response.status_code == 403


def test_rn10_finder_cannot_claim_their_own_item(client, maria, item, clock):
    response = claim(client, maria, item)

    assert response.status_code == 403


def test_unknown_item_is_404(client, joao, clock):
    response = claim(client, joao, 999)

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("status", "code"),
    [
        ("registrado", 409),
        ("disponivel", 201),
        ("reservado", 409),
        ("devolvido", 409),
        ("expirado", 409),
        ("destinado", 409),
        ("cancelado", 409),
    ],
)
def test_only_items_on_a_shelf_or_on_their_way_accept_claims(
    client, joao, register, status, code, clock
):
    response = claim(client, joao, register(status))

    assert response.status_code == code


@pytest.mark.parametrize("count", [1, 6])
def test_answers_outside_2_to_5_are_422(client, joao, item, count, clock):
    response = claim(client, joao, item, ["azul"] * count)

    assert response.status_code == 422


def test_one_answer_per_question_or_422(client, joao, item, clock):
    # o item tem 3 perguntas
    response = claim(client, joao, item, ["azul", "banda queen"])

    assert response.status_code == 422
    assert client.get(f"{URL}/me", headers=joao.headers).json() == []


def test_rn10_own_item_is_403_before_the_answer_count(client, maria, item, clock):
    # o item é checado antes das respostas, igual no formulário (403 e não 422)
    response = claim(client, maria, item, ["azul", "banda queen"])

    assert response.status_code == 403
    assert response.json() == {"detail": "Você não pode reivindicar um item que registrou"}


def test_item_that_takes_no_claim_is_409_before_the_answer_count(client, joao, register, clock):
    response = claim(client, joao, register("reservado"), ["azul", "banda queen"])

    assert response.status_code == 409
    assert response.json() == {"detail": "Este item não aceita reivindicações"}


def test_blank_answer_is_allowed_and_counts_as_wrong(client, joao, item, clock):
    response = claim(client, joao, item, ["azul", "", "8F3A"])

    assert response.status_code == 201
    assert response.json()["status"] == "pendente"  # 2 de 3 bastam


@pytest.mark.parametrize(("length", "code"), [(500, 201), (501, 422)])
def test_answers_have_at_most_500_characters(client, joao, item, length, code, clock):
    response = claim(client, joao, item, ["azul", "banda queen", "x" * length])

    assert response.status_code == code


# --- quantas reivindicações dá pra ter ---


def test_rn11_one_active_claim_per_item(client, joao, item, clock):
    claim(client, joao, item)

    response = claim(client, joao, item)

    assert response.status_code == 409


def test_rn11_no_second_try_after_a_rejection(client, joao, item, clock):
    claim(client, joao, item, WRONG)

    response = claim(client, joao, item)

    assert response.status_code == 409


def test_rn11_claim_again_after_cancelling(client, joao, item, clock):
    first = claim(client, joao, item).json()
    client.post(f"{URL}/{first['id']}/cancel", headers=joao.headers)

    response = claim(client, joao, item)

    assert response.status_code == 201


def test_rn11_another_user_may_claim_an_item_already_claimed(client, signup, joao, item, clock):
    # o limite é por usuário e item, então quem responde certo ainda vai pra análise
    claim(client, joao, item)

    response = claim(client, signup(CARLOS), item)

    assert response.status_code == 201
    assert response.json()["status"] == "pendente"


def test_rn12_at_most_3_active_claims(client, joao, register, clock):
    for _ in range(3):
        assert claim(client, joao, register()).status_code == 201

    response = claim(client, joao, register())

    assert response.status_code == 409


def test_rn12_rejected_claims_dont_use_the_limit(client, joao, register, clock):
    claim(client, joao, register(), WRONG)
    for _ in range(3):
        assert claim(client, joao, register()).status_code == 201


def test_rn12_approved_claims_use_the_limit(client, joao, attendant, register, clock):
    approved = claim(client, joao, register()).json()
    client.post(f"{URL}/{approved['id']}/approve", headers=attendant.headers)
    claim(client, joao, register())
    claim(client, joao, register())

    response = claim(client, joao, register())

    assert response.status_code == 409
    assert response.json() == {"detail": "Você atingiu o limite de reivindicações ativas"}


def test_rn12_cancelling_a_claim_frees_a_slot(client, joao, register, clock):
    first = claim(client, joao, register()).json()
    claim(client, joao, register())
    claim(client, joao, register())
    client.post(f"{URL}/{first['id']}/cancel", headers=joao.headers)

    response = claim(client, joao, register())

    assert response.status_code == 201


def test_rn12_user_at_the_limit_still_gets_the_form(client, joao, register, clock):
    # o limite de ativas fica pra hora de enviar, já que dá pra cancelar outra antes
    for _ in range(3):
        claim(client, joao, register())

    response = questions_of(client, joao, register())

    assert response.status_code == 200
    assert [q["position"] for q in response.json()] == [1, 2, 3]


# --- bloqueio depois de falhas ---


def fail_three_times(client, joao, register):
    for _ in range(3):
        claim(client, joao, register(), WRONG)


def test_rn15_three_failures_block_claiming(client, joao, register, clock):
    fail_three_times(client, joao, register)

    response = claim(client, joao, register())

    assert response.status_code == 403


def test_rn15_blocked_user_gets_no_claim_form(client, joao, register, clock):
    fail_three_times(client, joao, register)

    assert questions_of(client, joao, register()).status_code == 403


@pytest.mark.parametrize("answers", [RIGHT, WRONG], ids=["pending", "rejected"])
def test_rn11_no_form_after_claiming_the_same_item(client, joao, item, answers, clock):
    claim(client, joao, item, answers)

    response = questions_of(client, joao, item)

    assert response.status_code == 409
    assert response.json() == {"detail": "Você já reivindicou este item"}


def test_rn15_block_ends_after_7_days(client, joao, register, clock):
    fail_three_times(client, joao, register)
    item = register()

    clock.current += timedelta(days=7) - timedelta(seconds=1)
    assert claim(client, joao, item).status_code == 403
    clock.current += timedelta(seconds=1)
    assert claim(client, joao, item).status_code == 201


def test_rn15_attendant_rejection_counts_as_a_failure(client, joao, attendant, register, clock):
    claim(client, joao, register(), WRONG)
    claim(client, joao, register(), WRONG)
    pending = claim(client, joao, register()).json()
    client.post(f"{URL}/{pending['id']}/reject", headers=attendant.headers)

    response = claim(client, joao, register())

    assert response.status_code == 403


def test_rn15_cancelling_is_not_a_failure(client, joao, register, clock):
    claim(client, joao, register(), WRONG)
    claim(client, joao, register(), WRONG)
    pending = claim(client, joao, register()).json()
    client.post(f"{URL}/{pending['id']}/cancel", headers=joao.headers)

    response = claim(client, joao, register())

    assert response.status_code == 201


def test_rn16_admin_unblock_lets_the_user_claim_again(client, admin, joao, register, clock):
    fail_three_times(client, joao, register)
    clock.current += timedelta(minutes=1)

    client.post(f"/v1/users/{joao.id}/unblock", headers=admin.headers)

    assert claim(client, joao, register()).status_code == 201


@pytest.mark.parametrize(
    ("gap", "code"),
    [(timedelta(days=30) - timedelta(seconds=1), 403), (timedelta(days=30), 201)],
)
def test_rn15_only_failures_within_30_days_block(client, joao, register, gap, code, clock):
    # as datas vêm do relógio injetável, e uma falha de 30 dias atrás já saiu da janela
    claim(client, joao, register(), WRONG)
    claim(client, joao, register(), WRONG)
    clock.current += gap
    claim(client, joao, register(), WRONG)

    response = claim(client, joao, register())

    assert response.status_code == code


# --- minhas reivindicações e cancelamento ---


def test_my_claims_lists_only_mine_newest_first(client, signup, joao, register, clock):
    other = signup(CARLOS)
    first = claim(client, joao, register()).json()
    second = claim(client, joao, register()).json()
    claim(client, other, register())

    response = client.get(f"{URL}/me", headers=joao.headers)

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [second["id"], first["id"]]


def test_claimant_cancels_a_pending_claim(client, joao, item, clock):
    pending = claim(client, joao, item).json()

    response = client.post(f"{URL}/{pending['id']}/cancel", headers=joao.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelada"
    assert item_status(item) == "disponivel"


def test_cancelling_an_approved_claim_puts_the_item_back(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    response = client.post(f"{URL}/{pending['id']}/cancel", headers=joao.headers)

    assert response.json()["status"] == "cancelada"
    # código de reivindicação cancelada não vale mais, então nem aparece
    assert response.json()["pickup_code"] is None
    assert item_status(item) == "disponivel"


def test_deleting_the_account_gives_the_reserved_item_back(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    response = client.delete(f"/v1/users/{joao.id}", headers=joao.headers)

    assert response.status_code == 204
    assert item_status(item) == "disponivel"


def test_rn21_rn53_claimant_sees_only_the_status_the_point_and_the_code(
    client, joao, attendant, item, point, clock
):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/reject", headers=attendant.headers)

    [mine] = client.get(f"{URL}/me", headers=joao.headers).json()

    # sem nota, sem motivo, sem respostas e nada do achador
    assert mine == {
        "id": pending["id"],
        "item_id": item,
        "status": "rejeitada",
        "collection_point_id": point,
        "pickup_code": None,
        "pickup_deadline": None,
        "created_at": pending["created_at"],
    }


def test_cancelling_twice_is_409(client, joao, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/cancel", headers=joao.headers)

    response = client.post(f"{URL}/{pending['id']}/cancel", headers=joao.headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Mudança de estado não permitida"}


def test_someone_elses_claim_looks_missing(client, signup, joao, item, clock):
    pending = claim(client, joao, item).json()
    other = signup(CARLOS)

    response = client.post(f"{URL}/{pending['id']}/cancel", headers=other.headers)

    assert response.status_code == 404


def test_cancelling_a_rejected_claim_is_409(client, joao, item, clock):
    rejected = claim(client, joao, item, WRONG).json()

    response = client.post(f"{URL}/{rejected['id']}/cancel", headers=joao.headers)

    assert response.status_code == 409


# --- análise do atendente ---


def test_rn22_attendant_sees_score_and_answers_next_to_the_expected(
    client, joao, attendant, item, clock
):
    pending = claim(client, joao, item, ["azul", "banda quen", "1111"]).json()

    response = client.get(f"{URL}/pending", headers=attendant.headers)

    assert response.status_code == 200
    [review] = response.json()
    assert review["id"] == pending["id"]
    assert review["claimant_id"] == joao.id
    assert review["score"] == pytest.approx(2 / 3)
    assert review["answers"][1] == {
        "position": 2,
        "question": "Tem algum adesivo? Qual?",
        "expected": "Banda Queen",
        "given": "banda quen",
    }


def test_rn41_pending_list_only_has_claims_at_the_attendants_points(
    client, joao, other_attendant, attendant, item, clock
):
    claim(client, joao, item)

    assert len(client.get(f"{URL}/pending", headers=attendant.headers).json()) == 1
    assert client.get(f"{URL}/pending", headers=other_attendant.headers).json() == []


def test_admin_sees_pending_claims_at_every_point(client, admin, joao, item, clock):
    claim(client, joao, item)

    assert len(client.get(f"{URL}/pending", headers=admin.headers).json()) == 1


def test_rn41_attendant_without_points_sees_no_pending_claims(client, signup, joao, item, clock):
    claim(client, joao, item)
    unlinked = signup(CARLOS, Role.ATENDENTE)

    response = client.get(f"{URL}/pending", headers=unlinked.headers)

    assert response.status_code == 200
    assert response.json() == []


def test_admin_approves_a_claim_at_any_point(client, admin, joao, item, clock):
    # o admin analisa em qualquer ponto sem estar vinculado
    pending = claim(client, joao, item).json()

    response = client.post(f"{URL}/{pending['id']}/approve", headers=admin.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "aprovada"
    assert item_status(item) == "reservado"


def test_pending_list_leaves_out_rejected_claims(client, joao, attendant, item, clock):
    claim(client, joao, item, WRONG)

    assert client.get(f"{URL}/pending", headers=attendant.headers).json() == []


def test_attendant_never_reviews_their_own_claim(client, signup, admin, point, item, clock):
    # reivindicou como usuário, depois foi promovido e vinculado ao ponto do item
    account = signup(CARLOS)
    pending = claim(client, account, item).json()
    client.patch(f"/v1/users/{account.id}/role", json={"role": "atendente"}, headers=admin.headers)
    client.post(
        f"/v1/collection-points/{point}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )

    assert client.get(f"{URL}/pending", headers=account.headers).json() == []
    response = client.post(f"{URL}/{pending['id']}/approve", headers=account.headers)
    assert response.status_code == 403


def test_users_cannot_review(client, joao, item, clock):
    pending = claim(client, joao, item).json()

    assert client.get(f"{URL}/pending", headers=joao.headers).status_code == 403
    assert client.post(f"{URL}/{pending['id']}/approve", headers=joao.headers).status_code == 403


def test_rn13_approval_reserves_the_item_and_gives_a_pickup_code(
    client, joao, attendant, item, clock
):
    pending = claim(client, joao, item).json()

    response = client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "aprovada"
    assert "pickup_code" not in response.json()
    assert item_status(item) == "reservado"
    [mine] = client.get(f"{URL}/me", headers=joao.headers).json()
    # 6 letras ou números, válido por 5 dias depois da aprovação
    assert len(mine["pickup_code"]) == 6
    assert mine["pickup_code"].isalnum()
    assert mine["pickup_deadline"] == (clock.now() + timedelta(days=5)).isoformat().replace(
        "+00:00", "Z"
    )


def test_rn13_only_one_approved_claim_per_item(client, signup, joao, attendant, item, clock):
    other = signup(CARLOS)
    first = claim(client, joao, item).json()
    second = claim(client, other, item).json()
    client.post(f"{URL}/{first['id']}/approve", headers=attendant.headers)

    response = client.post(f"{URL}/{second['id']}/approve", headers=attendant.headers)

    assert response.status_code == 409


def test_rn13_once_the_approved_claim_is_cancelled_another_can_be_approved(
    client, signup, joao, attendant, item, clock
):
    other = signup(CARLOS)
    first = claim(client, joao, item).json()
    second = claim(client, other, item).json()
    client.post(f"{URL}/{first['id']}/approve", headers=attendant.headers)
    client.post(f"{URL}/{first['id']}/cancel", headers=joao.headers)

    response = client.post(f"{URL}/{second['id']}/approve", headers=attendant.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "aprovada"
    assert item_status(item) == "reservado"


def test_approving_twice_is_409_and_keeps_the_pickup_code(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)
    [before] = client.get(f"{URL}/me", headers=joao.headers).json()

    response = client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "O item não está disponível"}
    [after] = client.get(f"{URL}/me", headers=joao.headers).json()
    assert after["pickup_code"] == before["pickup_code"]


def test_approved_claim_cannot_be_rejected(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    response = client.post(f"{URL}/{pending['id']}/reject", headers=attendant.headers)

    assert response.status_code == 409
    assert item_status(item) == "reservado"


def test_rn41_attendant_from_another_point_gets_403(client, joao, other_attendant, item, clock):
    pending = claim(client, joao, item).json()

    for action in ("approve", "reject"):
        response = client.post(f"{URL}/{pending['id']}/{action}", headers=other_attendant.headers)
        assert response.status_code == 403
    assert item_status(item) == "disponivel"


def test_attendant_rejects_a_claim(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()

    response = client.post(f"{URL}/{pending['id']}/reject", headers=attendant.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "rejeitada"
    assert item_status(item) == "disponivel"


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_only_pending_claims_are_reviewed(client, joao, attendant, item, action, clock):
    rejected = claim(client, joao, item, WRONG).json()

    response = client.post(f"{URL}/{rejected['id']}/{action}", headers=attendant.headers)

    assert response.status_code == 409


@pytest.mark.parametrize("action", ["approve", "reject", "cancel"])
def test_unknown_claim_is_404(client, admin, action):
    response = client.post(f"{URL}/999/{action}", headers=admin.headers)

    assert response.status_code == 404


# --- retirada no balcão ---


def approved(client, account, attendant, item_id: int) -> tuple[int, str]:
    """`account` reivindica o item e o atendente aprova: o id e o código de retirada."""
    claim_id = claim(client, account, item_id).json()["id"]
    assert client.post(f"{URL}/{claim_id}/approve", headers=attendant.headers).status_code == 200
    mine = client.get(f"{URL}/me", headers=account.headers).json()
    return claim_id, next(c["pickup_code"] for c in mine if c["id"] == claim_id)


def pick_up(client, account, claim_id: int, point: int, code: str, document_checked: bool = True):
    body = {"collection_point_id": point, "pickup_code": code, "document_checked": document_checked}
    return client.post(f"{URL}/{claim_id}/pickup", json=body, headers=account.headers)


def other_code(code: str) -> str:
    return "ZZZZZZ" if code != "ZZZZZZ" else "YYYYYY"


def test_pickup_returns_the_item_and_completes_the_claim(
    client, joao, attendant, item, point, clock
):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 200
    assert response.json()["status"] == "concluida"
    assert item_status(item) == "devolvido"
    [mine] = client.get(f"{URL}/me", headers=joao.headers).json()
    assert mine["status"] == "concluida"
    # código usado não vale mais, então some da tela do reivindicante
    assert mine["pickup_code"] is None


def test_rn06_pickup_writes_the_return_in_the_history(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)

    pick_up(client, attendant, claim_id, point, code)

    history = client.get(f"/v1/items/{item}/history", headers=attendant.headers).json()
    assert history[-1] == {
        "event": "devolucao",
        "collection_point_id": point,
        "actor_id": attendant.id,
        "at": clock.now().isoformat().replace("+00:00", "Z"),
    }


def test_rn44_code_is_single_use(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)
    pick_up(client, attendant, claim_id, point, code)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 409
    assert response.json() == {"detail": "Código de retirada já usado"}


def test_rn44_wrong_code_is_422_and_the_item_stays_reserved(
    client, joao, attendant, item, point, clock
):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, point, other_code(code))

    assert response.status_code == 422
    assert response.json() == {"detail": "Código de retirada inválido"}
    assert item_status(item) == "reservado"


def test_rn44_typed_code_ignores_case_and_surrounding_spaces(
    client, joao, attendant, item, point, clock
):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, point, f" {code.lower()} ")

    assert response.status_code == 200


@pytest.mark.parametrize("code", ["", "ABC", "ABC12345"])
def test_rn44_code_with_another_length_is_422(client, joao, attendant, item, point, code, clock):
    claim_id, _ = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 422


def test_rn44_code_still_works_just_before_the_5_days(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)
    clock.current += timedelta(days=5, seconds=-1)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 200


def test_rn44_code_expires_5_days_after_the_approval(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)
    clock.current += timedelta(days=5)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 409
    assert response.json() == {"detail": "Código de retirada vencido"}
    assert item_status(item) == "reservado"


def test_rn45_code_is_only_accepted_at_the_point_where_the_item_is(
    client, admin, joao, attendant, item, point, clock
):
    # o atendente trabalha em dois pontos; o item está no primeiro
    second = new_point(client, admin, "Ginásio")
    client.post(
        f"/v1/collection-points/{second}/attendants",
        json={"user_id": attendant.id},
        headers=admin.headers,
    )
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, second, code)

    assert response.status_code == 409
    assert response.json() == {"detail": "O item não está neste ponto de coleta"}
    assert item_status(item) == "reservado"


def test_rn46_photo_id_must_be_checked(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, attendant, claim_id, point, code, document_checked=False)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Confira o documento com foto antes de concluir a retirada"
    }
    assert item_status(item) == "reservado"


def test_rn46_photo_id_check_has_no_default(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)
    body = {"collection_point_id": point, "pickup_code": code}

    response = client.post(f"{URL}/{claim_id}/pickup", json=body, headers=attendant.headers)

    assert response.status_code == 422


def test_rn41_attendant_from_another_point_cannot_validate_the_pickup(
    client, joao, attendant, other_attendant, item, point, clock
):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, other_attendant, claim_id, point, code)

    assert response.status_code == 403
    assert item_status(item) == "reservado"


def test_claimant_cannot_validate_their_own_pickup(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, joao, claim_id, point, code)

    assert response.status_code == 403
    assert item_status(item) == "reservado"


def test_attendant_never_hands_over_their_own_claim(
    client, signup, admin, attendant, item, point, clock
):
    # aprovado como usuário, depois virou atendente do ponto do item
    account = signup(CARLOS)
    claim_id, code = approved(client, account, attendant, item)
    client.patch(f"/v1/users/{account.id}/role", json={"role": "atendente"}, headers=admin.headers)
    client.post(
        f"/v1/collection-points/{point}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )

    assert client.get(f"{URL}/approved", headers=account.headers).json() == []
    response = pick_up(client, account, claim_id, point, code)
    assert response.status_code == 403
    assert response.json() == {"detail": "Sem permissão para esta operação"}
    assert item_status(item) == "reservado"


def test_admin_validates_a_pickup_at_any_point(client, admin, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)

    response = pick_up(client, admin, claim_id, point, code)

    assert response.status_code == 200
    assert item_status(item) == "devolvido"


def test_pending_claim_has_no_pickup_code(client, joao, attendant, item, point, clock):
    pending = claim(client, joao, item).json()

    response = pick_up(client, attendant, pending["id"], point, "AB12CD")

    assert response.status_code == 422


def test_rn44_code_of_a_cancelled_claim_no_longer_works(
    client, joao, attendant, item, point, clock
):
    claim_id, code = approved(client, joao, attendant, item)
    client.post(f"{URL}/{claim_id}/cancel", headers=joao.headers)

    response = pick_up(client, attendant, claim_id, point, code)

    assert response.status_code == 422
    assert item_status(item) == "disponivel"


def test_unknown_claim_pickup_is_404(client, admin, point):
    response = pick_up(client, admin, 999, point, "AB12CD")

    assert response.status_code == 404


def test_rn14_pickup_turns_down_the_other_pending_claims(
    client, signup, joao, attendant, item, point, clock
):
    other = signup(CARLOS)
    claim(client, other, item)
    claim_id, code = approved(client, joao, attendant, item)

    pick_up(client, attendant, claim_id, point, code)

    [theirs] = client.get(f"{URL}/me", headers=other.headers).json()
    assert theirs["status"] == "rejeitada"
    assert client.get(f"{URL}/pending", headers=attendant.headers).json() == []


def test_rn14_rn15_losing_an_item_to_its_owner_is_not_a_failed_attempt(
    client, signup, joao, attendant, register, point, clock
):
    other = signup(CARLOS)
    for _ in range(3):
        item = register()
        claim(client, other, item)
        claim_id, code = approved(client, joao, attendant, item)
        pick_up(client, attendant, claim_id, point, code)

    # três rejeições, mas nenhuma conta como falha, então o Carlos ainda pode reivindicar
    response = claim(client, other, register())

    assert response.status_code == 201


def test_awaiting_pickup_lists_approved_claims_with_the_claimant_name(
    client, joao, attendant, register, point, clock
):
    item = register()
    claim_id, _ = approved(client, joao, attendant, item)
    claim(client, joao, register())  # ainda pendente: não está esperando retirada

    response = client.get(f"{URL}/approved", headers=attendant.headers)

    assert response.status_code == 200
    # tem o nome pra conferir o documento, mas não o código (quem mostra é a pessoa)
    assert response.json() == [
        {
            "id": claim_id,
            "item_id": item,
            "item_description": "Garrafa azul com adesivo",
            "claimant_id": joao.id,
            "claimant_name": "João Souza",
            "status": "aprovada",
            "collection_point_id": point,
            "pickup_deadline": (clock.now() + timedelta(days=5)).isoformat().replace("+00:00", "Z"),
        }
    ]


def test_picked_up_claims_leave_the_pickup_list(client, joao, attendant, item, point, clock):
    claim_id, code = approved(client, joao, attendant, item)
    pick_up(client, attendant, claim_id, point, code)

    assert client.get(f"{URL}/approved", headers=attendant.headers).json() == []


def test_rn41_pickup_list_only_has_claims_at_the_attendants_points(
    client, joao, attendant, other_attendant, item, clock
):
    approved(client, joao, attendant, item)

    assert client.get(f"{URL}/approved", headers=other_attendant.headers).json() == []


def test_users_cannot_see_the_pickup_list(client, joao):
    assert client.get(f"{URL}/approved", headers=joao.headers).status_code == 403
