# Etapa 05: registering a found item with its verification questions (RN20, RN23)
import pytest

from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}

URL = "/v1/items"


def questions(count: int) -> list[dict]:
    return [{"question": f"Pergunta {n}?", "answer": f"Resposta {n}"} for n in range(1, count + 1)]


@pytest.fixture
def maria(signup):
    return signup(MARIA)


@pytest.fixture
def new_item(client, signup):
    """A valid body: the first category, location and color, and a new collection point."""
    admin = signup(ADMIN, Role.ADMIN)
    point = client.post(
        "/v1/collection-points", json={"name": "Biblioteca"}, headers=admin.headers
    ).json()

    def first(url: str) -> int:
        return client.get(url).json()[0]["id"]

    return {
        "category_id": first("/v1/categories"),
        "location_id": first("/v1/locations"),
        "color_id": first("/v1/colors"),
        "collection_point_id": point["id"],
        "description": "Garrafa azul com adesivo",
        "found_date": "2026-11-14",
        "questions": questions(3),
    }


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
