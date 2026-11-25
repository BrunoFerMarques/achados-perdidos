# o caminho inteiro de um item, só pela API: registrar, receber, reivindicar, aprovar e retirar
import os
from datetime import datetime, timedelta

import psycopg
import pytest

from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "senha-forte"}
ANA = {"name": "Ana Lima", "email": "ana@example.com", "password": "senha-forte"}


def iso(at: datetime) -> str:
    # como a API escreve um horário UTC
    return at.isoformat().replace("+00:00", "Z")


def item_status(item_id: int) -> str:
    # o item devolvido sai do mural, então o status final é lido no banco
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        return conn.execute("SELECT status FROM items WHERE id = %s", (item_id,)).fetchone()[0]


def on_the_wall(client) -> list[int]:
    # o mural é público: nenhum login
    return [item["id"] for item in client.get("/v1/items").json()]


@pytest.fixture
def maria(signup):
    """Acha o item."""
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    """Dono do item."""
    return signup(JOAO)


@pytest.fixture
def ana(signup):
    """Atendente, ainda sem ponto."""
    return signup(ANA, Role.ATENDENTE)


@pytest.fixture
def point(client, signup, ana):
    """Um ponto de coleta criado pelo admin, com a Ana no balcão."""
    admin = signup(ADMIN, Role.ADMIN)
    response = client.post(
        "/v1/collection-points", json={"name": "Biblioteca"}, headers=admin.headers
    )
    point_id = response.json()["id"]
    client.post(
        f"/v1/collection-points/{point_id}/attendants",
        json={"user_id": ana.id},
        headers=admin.headers,
    )
    return point_id


def test_item_goes_from_the_finder_back_to_its_owner(client, maria, joao, ana, point, clock):
    def first(url: str) -> int:
        return client.get(url).json()[0]["id"]

    # 1. registrar: a Maria achou, mas o item ainda não chegou no balcão
    response = client.post(
        "/v1/items",
        json={
            "category_id": first("/v1/categories"),
            "location_id": first("/v1/locations"),
            "color_id": first("/v1/colors"),
            "collection_point_id": point,
            "description": "Garrafa azul com adesivo",
            "found_date": "2026-11-14",
            "questions": [
                {"question": "Qual a cor da tampa?", "answer": "Azul"},
                {"question": "De que banda é o adesivo?", "answer": "Queen"},
            ],
        },
        headers=maria.headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "registrado"
    item = response.json()["id"]
    registered_at = clock.now()
    assert on_the_wall(client) == []

    # 2. receber: a Ana confere o item no balcão, e ele entra no mural
    clock.current += timedelta(hours=1)
    response = client.post(
        f"/v1/items/{item}/receive", json={"collection_point_id": point}, headers=ana.headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "disponivel"
    received_at = clock.now()
    assert on_the_wall(client) == [item]

    # 3. reivindicar: o João responde às perguntas, e o pedido espera a análise
    clock.current += timedelta(hours=1)
    response = client.get(f"/v1/claims/items/{item}/questions", headers=joao.headers)
    assert [q["question"] for q in response.json()] == [
        "Qual a cor da tampa?",
        "De que banda é o adesivo?",
    ]
    response = client.post(
        "/v1/claims", json={"item_id": item, "answers": ["azul", "queen"]}, headers=joao.headers
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pendente"
    claim = response.json()["id"]
    # com o pedido em análise, o item continua no mural
    assert on_the_wall(client) == [item]

    # 4. aprovar: a Ana vê o pedido na fila e aprova; o item fica reservado para o João
    clock.current += timedelta(hours=1)
    [pending] = client.get("/v1/claims/pending", headers=ana.headers).json()
    assert pending["id"] == claim
    response = client.post(f"/v1/claims/{claim}/approve", headers=ana.headers)
    assert response.status_code == 200
    assert response.json()["status"] == "aprovada"
    reserved_at = clock.now()
    assert item_status(item) == "reservado"
    assert on_the_wall(client) == []

    # 5. retirar: o João mostra o código, e a Ana confere o código e o documento
    clock.current += timedelta(hours=1)
    [mine] = client.get("/v1/claims/me", headers=joao.headers).json()
    response = client.post(
        f"/v1/claims/{claim}/pickup",
        json={
            "collection_point_id": point,
            "pickup_code": mine["pickup_code"],
            "document_checked": True,
        },
        headers=ana.headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "concluida"
    returned_at = clock.now()

    # no fim, o item foi devolvido e não sobrou nada em nenhuma fila
    assert item_status(item) == "devolvido"
    assert on_the_wall(client) == []
    assert client.get("/v1/claims/pending", headers=ana.headers).json() == []
    assert client.get("/v1/claims/approved", headers=ana.headers).json() == []

    # RN06, RN42: o histórico conta o caminho todo, em ordem, com quem fez cada passo
    history = client.get(f"/v1/items/{item}/history", headers=ana.headers).json()
    assert [(line["event"], line["actor_id"], line["at"]) for line in history] == [
        ("registro", maria.id, iso(registered_at)),
        ("recebimento", ana.id, iso(received_at)),
        ("reserva", ana.id, iso(reserved_at)),
        ("devolucao", ana.id, iso(returned_at)),
    ]
    assert {line["collection_point_id"] for line in history} == {point}
