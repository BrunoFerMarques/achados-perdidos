# Etapa 05: registering a found item with its verification questions (RN20, RN23)
# Etapa 08: receiving it at a collection point (RN02, RN41) and its custody history (RN06, RN42)
# Etapa 09: the public listing, its filters and what it never shows (RN50, RN52)
# Etapa 11: the staff's queue of registered items (RN02) and the description on receipt (RN51)
from datetime import datetime, timedelta

import pytest

from domain.items import DOCUMENT_TEXT
from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "senha-forte"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "senha-forte"}
CARLOS = {"name": "Carlos Reis", "email": "carlos@example.com", "password": "senha-forte"}

URL = "/v1/items"


def questions(count: int) -> list[dict]:
    return [{"question": f"Pergunta {n}?", "answer": f"Resposta {n}"} for n in range(1, count + 1)]


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


def new_point(client, admin, name: str) -> int:
    response = client.post("/v1/collection-points", json={"name": name}, headers=admin.headers)
    return response.json()["id"]


def link(client, admin, point_id: int, account) -> None:
    client.post(
        f"/v1/collection-points/{point_id}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )


@pytest.fixture
def point(client, admin):
    return new_point(client, admin, "Biblioteca")


@pytest.fixture
def attendant(client, signup, admin, point):
    """An attendant who works at `point`."""
    account = signup(ANA, Role.ATENDENTE)
    link(client, admin, point, account)
    return account


@pytest.fixture
def new_item(client, point):
    """A valid body: the first category, location and color, at `point`."""

    def first(url: str) -> int:
        return client.get(url).json()[0]["id"]

    return {
        "category_id": first("/v1/categories"),
        "location_id": first("/v1/locations"),
        "color_id": first("/v1/colors"),
        "collection_point_id": point,
        "description": "Garrafa azul com adesivo",
        "found_date": "2026-11-14",
        "questions": questions(3),
    }


@pytest.fixture
def item(client, maria, new_item):
    """Maria's item, registered at `point` and not received yet."""
    return client.post(URL, json=new_item, headers=maria.headers).json()["id"]


def receive(client, account, item_id: int, point_id: int):
    return client.post(
        f"{URL}/{item_id}/receive", json={"collection_point_id": point_id}, headers=account.headers
    )


def history(client, account, item_id: int):
    return client.get(f"{URL}/{item_id}/history", headers=account.headers)


# --- registering ---


def test_register_item(client, maria, new_item):
    response = client.post(URL, json=new_item, headers=maria.headers)

    assert response.status_code == 201
    item = response.json()
    assert item["status"] == "registrado"
    assert item["finder_id"] == maria.id
    assert [q["position"] for q in item["questions"]] == [1, 2, 3]
    assert [q["question"] for q in item["questions"]] == [
        "Pergunta 1?",
        "Pergunta 2?",
        "Pergunta 3?",
    ]


# RN20: from 2 to 5 questions; the limits are what prove the rule
@pytest.mark.parametrize(("count", "status"), [(1, 422), (2, 201), (5, 201), (6, 422)])
def test_rn20_question_limits(client, maria, new_item, count, status):
    body = {**new_item, "questions": questions(count)}

    response = client.post(URL, json=body, headers=maria.headers)

    assert response.status_code == status


def test_requires_login(client, new_item):
    response = client.post(URL, json=new_item)

    assert response.status_code == 401


@pytest.mark.parametrize("field", ["category_id", "location_id", "color_id", "collection_point_id"])
def test_unknown_id_is_404(client, maria, new_item, field):
    response = client.post(URL, json={**new_item, field: 999}, headers=maria.headers)

    assert response.status_code == 404


def test_status_and_finder_in_body_are_ignored(client, maria, new_item):
    body = {**new_item, "status": "devolvido", "finder_id": 999}

    response = client.post(URL, json=body, headers=maria.headers)

    assert response.status_code == 201
    assert response.json()["status"] == "registrado"
    assert response.json()["finder_id"] == maria.id


# RN23: the expected answers never leave the API
def test_answers_are_not_returned(client, maria, new_item):
    response = client.post(URL, json=new_item, headers=maria.headers)

    assert response.status_code == 201
    assert "Resposta" not in response.text


# --- receiving ---


@pytest.mark.parametrize(
    ("method", "url"), [("POST", f"{URL}/1/receive"), ("GET", f"{URL}/1/history")]
)
def test_receive_and_history_require_login(client, method, url):
    response = client.request(method, url, json={"collection_point_id": 1})

    assert response.status_code == 401


def test_attendant_receives_an_item_at_their_point(client, attendant, item, point):
    response = receive(client, attendant, item, point)

    assert response.status_code == 200
    assert response.json()["status"] == "disponivel"
    assert response.json()["collection_point_id"] == point


def test_rn02_item_handed_in_at_another_point_belongs_to_that_point(
    client, signup, admin, item, point
):
    # Maria said she would leave it at the library, but handed it in at the restaurant
    restaurant = new_point(client, admin, "Restaurante")
    carlos = signup(CARLOS, Role.ATENDENTE)
    link(client, admin, restaurant, carlos)

    response = receive(client, carlos, item, restaurant)

    assert response.status_code == 200
    assert response.json()["collection_point_id"] == restaurant
    assert history(client, carlos, item).json()[-1]["collection_point_id"] == restaurant


def test_users_cannot_receive(client, maria, item, point):
    # not even the finder: receiving is the counter's job
    response = receive(client, maria, item, point)

    assert response.status_code == 403


def test_rn41_attendant_cannot_receive_at_a_point_they_dont_work_at(client, admin, attendant, item):
    restaurant = new_point(client, admin, "Restaurante")

    response = receive(client, attendant, item, restaurant)

    assert response.status_code == 403


def test_admin_receives_at_any_point(client, admin, item, point):
    # scope section 11: the admin operates every point without being linked to any
    response = receive(client, admin, item, point)

    assert response.status_code == 200


def test_receiving_an_unknown_item_is_404(client, attendant, point):
    response = receive(client, attendant, 999, point)

    assert response.status_code == 404


def test_receiving_at_an_unknown_point_is_404(client, admin, item):
    response = receive(client, admin, item, 999)

    assert response.status_code == 404


def test_receiving_twice_is_409_and_writes_nothing(client, attendant, item, point):
    receive(client, attendant, item, point)

    response = receive(client, attendant, item, point)

    assert response.status_code == 409
    assert len(history(client, attendant, item).json()) == 2


# RN51: the attendant may rewrite the public description when the object is handed in
def receive_with(client, account, item_id: int, point_id: int, description: str):
    body = {"collection_point_id": point_id, "description": description}
    return client.post(f"{URL}/{item_id}/receive", json=body, headers=account.headers)


def test_rn51_attendant_rewrites_the_description_on_receipt(client, attendant, item, point):
    response = receive_with(client, attendant, item, point, "  Garrafa azul  ")

    assert response.status_code == 200
    # stripped, like every text the API takes
    assert response.json()["description"] == "Garrafa azul"


def test_receipt_without_description_keeps_the_finders(client, attendant, item, point):
    response = receive(client, attendant, item, point)

    assert response.json()["description"] == "Garrafa azul com adesivo"


def test_blank_description_on_receipt_is_422_and_receives_nothing(client, attendant, item, point):
    response = receive_with(client, attendant, item, point, "   ")

    assert response.status_code == 422
    assert len(history(client, attendant, item).json()) == 1


def test_refused_receipt_keeps_the_description(client, attendant, item, point):
    receive(client, attendant, item, point)

    response = receive_with(client, attendant, item, point, "Outra descrição")

    assert response.status_code == 409
    # the item is on the shelf now, so the public listing shows its description
    assert client.get(URL).json()[0]["public_description"] == "Garrafa azul com adesivo"


# --- the staff's queue (RN02) ---


def registered(client, account):
    return client.get(f"{URL}/registered", headers=account.headers)


def test_registered_queue_requires_login(client):
    assert client.get(f"{URL}/registered").status_code == 401


def test_users_cannot_see_the_registered_queue(client, maria, item):
    # not even the finder: the queue is the counter's
    assert registered(client, maria).status_code == 403


def test_rn02_any_attendant_sees_items_registered_at_any_point(
    client, signup, admin, maria, new_item, item
):
    # Carlos works only at the restaurant, but Maria may hand the library's item in there
    restaurant = new_point(client, admin, "Restaurante")
    carlos = signup(CARLOS, Role.ATENDENTE)
    link(client, admin, restaurant, carlos)
    other = client.post(URL, json=new_item, headers=maria.headers).json()["id"]

    response = registered(client, carlos)

    assert response.status_code == 200
    # oldest first, with the raw description the attendant may rewrite
    assert [i["id"] for i in response.json()] == [item, other]
    assert response.json()[0]["description"] == "Garrafa azul com adesivo"


def test_received_item_leaves_the_registered_queue(client, attendant, item, point):
    receive(client, attendant, item, point)

    assert registered(client, attendant).json() == []


# --- the custody history ---


def test_rn42_history_has_the_registration_and_then_the_receipt(
    client, clock, maria, attendant, item, point
):
    registered_at = clock.now()
    clock.current += timedelta(hours=1)
    receive(client, attendant, item, point)

    response = history(client, attendant, item)

    assert response.status_code == 200
    assert response.json() == [
        {
            "event": "registro",
            "collection_point_id": point,
            "actor_id": maria.id,
            "at": iso(registered_at),
        },
        {
            "event": "recebimento",
            "collection_point_id": point,
            "actor_id": attendant.id,
            "at": iso(clock.now()),
        },
    ]


def test_rn06_approving_and_cancelling_a_claim_write_reserva_and_liberacao(
    client, clock, signup, attendant, item, point
):
    joao = signup(JOAO)
    receive(client, attendant, item, point)
    answers = ["Resposta 1", "Resposta 2", "Resposta 3"]
    claim = client.post(
        "/v1/claims", json={"item_id": item, "answers": answers}, headers=joao.headers
    ).json()
    client.post(f"/v1/claims/{claim['id']}/approve", headers=attendant.headers)
    client.post(f"/v1/claims/{claim['id']}/cancel", headers=joao.headers)

    lines = history(client, attendant, item).json()

    assert [line["event"] for line in lines] == ["registro", "recebimento", "reserva", "liberacao"]
    # each line says who acted: the attendant approved, João cancelled
    assert [line["actor_id"] for line in lines[2:]] == [attendant.id, joao.id]


def test_rn53_finder_cannot_see_the_history(client, maria, item):
    response = history(client, maria, item)

    assert response.status_code == 403


def test_admin_sees_the_history(client, admin, item):
    response = history(client, admin, item)

    assert response.status_code == 200
    assert [line["event"] for line in response.json()] == ["registro"]


def test_history_of_an_unknown_item_is_404(client, admin):
    response = history(client, admin, 999)

    assert response.status_code == 404


# --- the public listing ---


def category_id(client, name: str) -> int:
    for category in client.get("/v1/categories").json():
        if category["name"] == name:
            return category["id"]
    raise AssertionError(f"no category named {name}")


def on_shelf(client, maria, attendant, point, body: dict) -> int:
    """Registers the item and receives it, so it is on the public listing."""
    item_id = client.post(URL, json=body, headers=maria.headers).json()["id"]
    receive(client, attendant, item_id, point)
    return item_id


def listed(client, **params) -> list[int]:
    # no headers: the listing is asked for the way anyone would
    response = client.get(URL, params=params)
    assert response.status_code == 200
    return [found["id"] for found in response.json()]


# RN50: only what is at a collection point is public
def test_rn50_item_not_received_is_not_listed(client, item):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


def test_rn50_received_item_is_listed_without_private_fields(client, attendant, item, point):
    # the pair of the test above: without it, a route that always answers [] would pass
    receive(client, attendant, item, point)

    response = client.get(URL)

    [found] = response.json()
    assert found["id"] == item
    assert found["public_description"] == "Garrafa azul com adesivo"
    for private in ("questions", "finder_id", "description", "status", "created_at"):
        assert private not in found


def test_listing_shows_the_newest_first(client, maria, attendant, point, new_item):
    older = on_shelf(client, maria, attendant, point, {**new_item, "found_date": "2026-11-10"})
    newer = on_shelf(client, maria, attendant, point, {**new_item, "found_date": "2026-11-14"})

    assert listed(client) == [newer, older]


def test_filter_by_category(client, maria, attendant, point, new_item):
    bottle = on_shelf(client, maria, attendant, point, new_item)
    backpack = on_shelf(
        client,
        maria,
        attendant,
        point,
        {**new_item, "category_id": category_id(client, "Mochilas")},
    )

    assert listed(client, category_id=new_item["category_id"]) == [bottle]
    assert listed(client, category_id=category_id(client, "Mochilas")) == [backpack]


def test_filter_by_location(client, maria, attendant, point, new_item):
    second_location = client.get("/v1/locations").json()[1]["id"]
    here = on_shelf(client, maria, attendant, point, new_item)
    there = on_shelf(client, maria, attendant, point, {**new_item, "location_id": second_location})

    assert listed(client, location_id=new_item["location_id"]) == [here]
    assert listed(client, location_id=second_location) == [there]


def test_filter_by_dates_includes_both_ends(client, maria, attendant, point, new_item):
    older = on_shelf(client, maria, attendant, point, {**new_item, "found_date": "2026-11-10"})
    newer = on_shelf(client, maria, attendant, point, {**new_item, "found_date": "2026-11-14"})

    assert listed(client, found_from="2026-11-14") == [newer]
    assert listed(client, found_to="2026-11-10") == [older]
    assert listed(client, found_from="2026-11-11", found_to="2026-11-13") == []


def test_invalid_date_is_422(client):
    response = client.get(URL, params={"found_from": "ontem"})

    assert response.status_code == 422


def test_search_ignores_case(client, maria, attendant, point, new_item):
    bottle = on_shelf(client, maria, attendant, point, new_item)
    on_shelf(client, maria, attendant, point, {**new_item, "description": "Mochila cinza"})

    assert listed(client, q="garrafa") == [bottle]


# RN52: a document is listed, but never with its description
def test_rn52_a_document_is_listed_with_the_fixed_text(client, maria, attendant, point, new_item):
    body = {
        **new_item,
        "category_id": category_id(client, "Documentos"),
        "description": "RG de João Silva",
    }
    on_shelf(client, maria, attendant, point, body)

    response = client.get(URL)

    assert response.json()[0]["public_description"] == DOCUMENT_TEXT
    assert "João Silva" not in response.text


def test_rn52_search_does_not_find_a_document_by_the_name_in_it(
    client, maria, attendant, point, new_item
):
    documents = category_id(client, "Documentos")
    body = {**new_item, "category_id": documents, "description": "RG de João Silva"}
    document = on_shelf(client, maria, attendant, point, body)

    # finding it would confirm that someone named Silva lost a document
    assert listed(client, q="Silva") == []
    # it is still on the listing, through the category filter
    assert listed(client, category_id=documents) == [document]
