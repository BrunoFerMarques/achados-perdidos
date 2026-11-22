# RN05: an item sent from one collection point to another, and the claims waiting for it (RN41)
from datetime import datetime, timedelta

import pytest

from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "senha-forte"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "senha-forte"}
CARLOS = {"name": "Carlos Reis", "email": "carlos@example.com", "password": "senha-forte"}
BEATRIZ = {"name": "Beatriz Melo", "email": "beatriz@example.com", "password": "senha-forte"}

URL = "/v1/items"
ANSWERS = ["Azul", "Banda Queen", "8F3A"]


def iso(at: datetime) -> str:
    # how the API writes a UTC time
    return at.isoformat().replace("+00:00", "Z")


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
    response = client.post("/v1/collection-points", json={"name": name}, headers=admin.headers)
    return response.json()["id"]


def attendant_at(client, signup, admin, point_id: int, data: dict):
    account = signup(data, Role.ATENDENTE)
    client.post(
        f"/v1/collection-points/{point_id}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )
    return account


@pytest.fixture
def origin(client, admin):
    return new_point(client, admin, "Biblioteca")


@pytest.fixture
def destination(client, admin):
    return new_point(client, admin, "Restaurante")


@pytest.fixture
def ana(client, signup, admin, origin):
    """Works at the origin."""
    return attendant_at(client, signup, admin, origin, ANA)


@pytest.fixture
def carlos(client, signup, admin, destination):
    """Works at the destination."""
    return attendant_at(client, signup, admin, destination, CARLOS)


@pytest.fixture
def item_body(client, origin):
    """A valid body for POST /v1/items: the first category, location and color, at the origin."""

    def first(url: str) -> int:
        return client.get(url).json()[0]["id"]

    return {
        "category_id": first("/v1/categories"),
        "location_id": first("/v1/locations"),
        "color_id": first("/v1/colors"),
        "collection_point_id": origin,
        "description": "Garrafa azul com adesivo",
        "found_date": "2026-11-14",
        "questions": [
            {"question": "Qual a cor da capinha?", "answer": "Azul"},
            {"question": "Tem algum adesivo? Qual?", "answer": "Banda Queen"},
            {"question": "Últimos 4 dígitos do número de série?", "answer": "8F3A"},
        ],
    }


@pytest.fixture
def register(client, maria, item_body):
    """register() -> item id: Maria registers an item at the origin, not received yet."""

    def register() -> int:
        return client.post(URL, json=item_body, headers=maria.headers).json()["id"]

    return register


@pytest.fixture
def item(client, register, ana, origin, clock):
    """On the shelf at the origin: received by Ana."""
    item_id = register()
    client.post(
        f"{URL}/{item_id}/receive", json={"collection_point_id": origin}, headers=ana.headers
    )
    return item_id


def send(client, account, item_id: int, to: int):
    return client.post(
        f"{URL}/{item_id}/transfer", json={"transfer_to_id": to}, headers=account.headers
    )


def arrive(client, account, item_id: int):
    return client.post(f"{URL}/{item_id}/arrive", headers=account.headers)


def history(client, account, item_id: int) -> list[dict]:
    return client.get(f"{URL}/{item_id}/history", headers=account.headers).json()


def last_event(client, account, item_id: int) -> str:
    return history(client, account, item_id)[-1]["event"]


def claim(client, account, item_id: int):
    return client.post(
        "/v1/claims", json={"item_id": item_id, "answers": ANSWERS}, headers=account.headers
    )


# --- sending and confirming the arrival ---


@pytest.mark.parametrize(
    ("method", "url"),
    [("POST", f"{URL}/1/transfer"), ("POST", f"{URL}/1/arrive"), ("GET", f"{URL}/transfers")],
)
def test_transfer_routes_require_login(client, method, url):
    response = client.request(method, url, json={"transfer_to_id": 1})

    assert response.status_code == 401


def test_rn05_origin_attendant_sends_the_item(client, ana, item, origin, destination, clock):
    response = send(client, ana, item, destination)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "em_transferencia"
    # it belongs to the origin until it arrives
    assert body["collection_point_id"] == origin
    assert body["transfer_to_id"] == destination


def test_rn05_destination_attendant_confirms_the_arrival(
    client, ana, carlos, item, destination, clock
):
    send(client, ana, item, destination)

    response = arrive(client, carlos, item)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disponivel"
    assert body["collection_point_id"] == destination
    assert body["transfer_to_id"] is None


def test_rn06_transfer_writes_the_departure_at_the_origin_and_the_arrival_at_the_destination(
    client, ana, carlos, item, origin, destination, clock
):
    clock.current += timedelta(hours=1)
    send(client, ana, item, destination)
    sent_at = clock.now()
    clock.current += timedelta(hours=2)
    arrive(client, carlos, item)

    assert history(client, carlos, item)[-2:] == [
        {
            "event": "transferencia_saida",
            "collection_point_id": origin,
            "actor_id": ana.id,
            "at": iso(sent_at),
        },
        {
            "event": "transferencia_chegada",
            "collection_point_id": destination,
            "actor_id": carlos.id,
            "at": iso(clock.now()),
        },
    ]


def test_rn05_reserved_item_cannot_be_transferred(client, ana, joao, item, destination, clock):
    pending = claim(client, joao, item).json()
    client.post(f"/v1/claims/{pending['id']}/approve", headers=ana.headers)

    response = send(client, ana, item, destination)

    assert response.status_code == 409
    assert response.json() == {"detail": "O item não está disponível"}
    assert last_event(client, ana, item) == "reserva"


def test_item_not_received_yet_cannot_be_transferred(client, ana, register, destination, clock):
    response = send(client, ana, register(), destination)

    assert response.status_code == 409


def test_sending_twice_is_409_and_writes_nothing(client, ana, item, destination, clock):
    send(client, ana, item, destination)

    response = send(client, ana, item, destination)

    assert response.status_code == 409
    assert [line["event"] for line in history(client, ana, item)].count("transferencia_saida") == 1


def test_sending_to_the_point_it_is_at_is_422(client, ana, item, origin, clock):
    response = send(client, ana, item, origin)

    assert response.status_code == 422
    assert response.json() == {"detail": "O item já está neste ponto de coleta"}


def test_sending_to_an_unknown_point_is_404(client, ana, item, clock):
    response = send(client, ana, item, 999)

    assert response.status_code == 404


def test_transfer_needs_a_destination(client, ana, item):
    response = client.post(f"{URL}/{item}/transfer", json={}, headers=ana.headers)

    assert response.status_code == 422


@pytest.mark.parametrize("action", ["transfer", "arrive"])
def test_unknown_item_is_404(client, admin, destination, action):
    body = {"transfer_to_id": destination} if action == "transfer" else None
    response = client.post(f"{URL}/999/{action}", json=body, headers=admin.headers)

    assert response.status_code == 404


def test_arrival_of_an_item_not_in_transfer_is_409(client, carlos, item, clock):
    response = arrive(client, carlos, item)

    assert response.status_code == 409
    assert response.json() == {"detail": "O item não está em transferência"}


def test_confirming_the_arrival_twice_is_409(client, ana, carlos, item, destination, clock):
    send(client, ana, item, destination)
    arrive(client, carlos, item)

    response = arrive(client, carlos, item)

    assert response.status_code == 409


def test_rn02_reserved_item_is_not_received_again(client, ana, joao, item, origin, clock):
    # receiving it would put it back on the shelf with the approved claim still waiting for it
    pending = claim(client, joao, item).json()
    client.post(f"/v1/claims/{pending['id']}/approve", headers=ana.headers)

    response = client.post(
        f"{URL}/{item}/receive", json={"collection_point_id": origin}, headers=ana.headers
    )

    assert response.status_code == 409
    assert last_event(client, ana, item) == "reserva"


def test_item_in_transfer_is_not_received_at_any_counter(
    client, ana, carlos, item, destination, clock
):
    # it arrives through /arrive at its destination, not through a second receipt
    send(client, ana, item, destination)

    response = client.post(
        f"{URL}/{item}/receive", json={"collection_point_id": destination}, headers=carlos.headers
    )

    assert response.status_code == 409
    assert last_event(client, carlos, item) == "transferencia_saida"


# --- who may do it (RN41) ---


def test_rn41_destination_attendant_cannot_send_an_item_from_the_origin(
    client, carlos, item, destination, clock
):
    response = send(client, carlos, item, destination)

    assert response.status_code == 403


def test_rn41_origin_attendant_cannot_confirm_the_arrival(client, ana, item, destination, clock):
    send(client, ana, item, destination)

    response = arrive(client, ana, item)

    assert response.status_code == 403
    assert last_event(client, ana, item) == "transferencia_saida"


def test_users_cannot_send_or_confirm(client, maria, ana, item, destination, clock):
    # not even the finder: moving the object is the counter's job
    assert send(client, maria, item, destination).status_code == 403
    send(client, ana, item, destination)
    assert arrive(client, maria, item).status_code == 403


def test_admin_sends_and_confirms_at_any_point(client, admin, item, destination, clock):
    assert send(client, admin, item, destination).status_code == 200
    assert arrive(client, admin, item).status_code == 200


# --- the claims waiting for the item ---


def test_item_in_transfer_still_takes_claims(client, ana, joao, item, origin, destination, clock):
    # scope §5: on its way to a shelf, it still shows in the listing
    send(client, ana, item, destination)

    response = claim(client, joao, item)

    assert response.status_code == 201
    # the item still belongs to the origin until it arrives
    assert response.json()["collection_point_id"] == origin


def test_pending_claims_follow_the_item_to_the_destination(
    client, ana, carlos, joao, item, destination, clock
):
    pending = claim(client, joao, item).json()
    send(client, ana, item, destination)

    # on its way, nobody approves it: the item isn't on a shelf (RN13)
    response = client.post(f"/v1/claims/{pending['id']}/approve", headers=ana.headers)
    assert response.status_code == 409

    arrive(client, carlos, item)

    # once there, the claim is reviewed at the destination, and the claimant is told so (RN53)
    assert client.get("/v1/claims/pending", headers=ana.headers).json() == []
    assert [c["id"] for c in client.get("/v1/claims/pending", headers=carlos.headers).json()] == [
        pending["id"]
    ]
    [mine] = client.get("/v1/claims/me", headers=joao.headers).json()
    assert mine["collection_point_id"] == destination
    response = client.post(f"/v1/claims/{pending['id']}/approve", headers=carlos.headers)
    assert response.status_code == 200


def test_origin_may_still_reject_a_pending_claim_on_the_way(
    client, ana, joao, item, destination, clock
):
    # reviewing the answers doesn't need the object; approving does (RN13)
    pending = claim(client, joao, item).json()
    send(client, ana, item, destination)

    response = client.post(f"/v1/claims/{pending['id']}/reject", headers=ana.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "rejeitada"


def test_rn53_the_finders_item_does_not_carry_the_destination(client, maria, item_body, clock):
    # ItemOut, what the finder gets, has no transfer_to_id; only ItemTransferOut, for the staff
    response = client.post(URL, json=item_body, headers=maria.headers)

    assert response.status_code == 201
    assert "transfer_to_id" not in response.json()


# --- the list of items on their way ---


def test_both_ends_see_the_item_on_its_way(
    client, signup, admin, ana, carlos, item, origin, destination, clock
):
    elsewhere = attendant_at(client, signup, admin, new_point(client, admin, "Ginásio"), BEATRIZ)
    send(client, ana, item, destination)

    for account in (ana, carlos, admin):
        response = client.get(f"{URL}/transfers", headers=account.headers)
        assert response.status_code == 200
        [sent] = response.json()
        assert (sent["id"], sent["collection_point_id"], sent["transfer_to_id"]) == (
            item,
            origin,
            destination,
        )
    # RN41: an attendant of a third point doesn't follow it
    assert client.get(f"{URL}/transfers", headers=elsewhere.headers).json() == []


def test_arrived_items_leave_the_list(client, ana, carlos, item, destination, clock):
    send(client, ana, item, destination)
    arrive(client, carlos, item)

    assert client.get(f"{URL}/transfers", headers=carlos.headers).json() == []


def test_items_on_a_shelf_are_not_in_the_list(client, ana, item, clock):
    assert client.get(f"{URL}/transfers", headers=ana.headers).json() == []


def test_users_cannot_list_the_transfers(client, maria):
    assert client.get(f"{URL}/transfers", headers=maria.headers).status_code == 403
