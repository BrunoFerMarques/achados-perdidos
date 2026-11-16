# Claims (scope §6, §7) and the attendant's review (RN22, RN41)
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
    # receiving an item (Parte 1) has no route yet, so the test puts it on the shelf directly
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
    """Finds the items."""
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    """Claims them."""
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
    """An attendant who works at `point`."""
    account = signup(ANA, Role.ATENDENTE)
    client.post(
        f"/v1/collection-points/{point}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )
    return account


@pytest.fixture
def other_attendant(client, signup, admin):
    """An attendant who works at another point."""
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
    """register(status="disponivel") -> item id: Maria registers an item at `point`."""

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


# --- making a claim ---


def test_claim_with_enough_right_answers_goes_to_review(client, joao, item, point, clock):
    response = claim(client, joao, item)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pendente"
    assert body["item_id"] == item
    assert body["collection_point_id"] == point
    assert body["pickup_code"] is None


def test_claim_tolerates_case_accents_and_one_typo(client, joao, item, clock):
    # §7: "banda quen" is one character away from "Banda Queen"
    response = claim(client, joao, item, ["AZUL", "banda quen", "8f3a"])

    assert response.json()["status"] == "pendente"


def test_claim_below_the_minimum_score_is_rejected_at_once(client, joao, item, clock):
    # 1 of 3 right is below 60%
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


def test_requires_login(client, item):
    response = client.post(URL, json={"item_id": item, "answers": RIGHT})

    assert response.status_code == 401


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_only_users_claim(client, signup, item, role, clock):
    # scope §11
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
        ("em_transferencia", 201),
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
    # the item has 3 questions
    response = claim(client, joao, item, ["azul", "banda queen"])

    assert response.status_code == 422
    assert client.get(f"{URL}/me", headers=joao.headers).json() == []


def test_blank_answer_is_allowed_and_counts_as_wrong(client, joao, item, clock):
    response = claim(client, joao, item, ["azul", "", "8F3A"])

    assert response.status_code == 201
    assert response.json()["status"] == "pendente"  # 2 of 3 is enough


# --- RN11 and RN12: how many claims ---


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


def test_rn12_at_most_3_active_claims(client, joao, register, clock):
    for _ in range(3):
        assert claim(client, joao, register()).status_code == 201

    response = claim(client, joao, register())

    assert response.status_code == 409


def test_rn12_rejected_claims_dont_use_the_limit(client, joao, register, clock):
    claim(client, joao, register(), WRONG)
    for _ in range(3):
        assert claim(client, joao, register()).status_code == 201


# --- RN15 and RN16: blocking after failed claims ---


def fail_three_times(client, joao, register):
    for _ in range(3):
        claim(client, joao, register(), WRONG)


def test_rn15_three_failures_block_claiming(client, joao, register, clock):
    fail_three_times(client, joao, register)

    response = claim(client, joao, register())

    assert response.status_code == 403


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


# --- my claims and cancelling ---


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
    # RN44: the code of a cancelled claim no longer opens anything, so it isn't shown
    assert response.json()["pickup_code"] is None
    assert item_status(item) == "disponivel"


def test_deleting_the_account_gives_the_reserved_item_back(client, joao, attendant, item, clock):
    pending = claim(client, joao, item).json()
    client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    response = client.delete(f"/v1/users/{joao.id}", headers=joao.headers)

    assert response.status_code == 204
    assert item_status(item) == "disponivel"


def test_someone_elses_claim_looks_missing(client, signup, joao, item, clock):
    pending = claim(client, joao, item).json()
    other = signup(CARLOS)

    response = client.post(f"{URL}/{pending['id']}/cancel", headers=other.headers)

    assert response.status_code == 404


def test_cancelling_a_rejected_claim_is_409(client, joao, item, clock):
    rejected = claim(client, joao, item, WRONG).json()

    response = client.post(f"{URL}/{rejected['id']}/cancel", headers=joao.headers)

    assert response.status_code == 409


# --- the attendant's review ---


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


def test_pending_list_leaves_out_rejected_claims(client, joao, attendant, item, clock):
    claim(client, joao, item, WRONG)

    assert client.get(f"{URL}/pending", headers=attendant.headers).json() == []


def test_attendant_never_reviews_their_own_claim(client, signup, admin, point, item, clock):
    # claimed as a user, then promoted and linked to the item's point
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
    # RN44: 6 alphanumeric characters, valid for 5 days from the approval
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


def test_rn13_item_in_transfer_cannot_be_approved_yet(client, joao, attendant, register, clock):
    pending = claim(client, joao, register("em_transferencia")).json()

    response = client.post(f"{URL}/{pending['id']}/approve", headers=attendant.headers)

    assert response.status_code == 409


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
