from datetime import datetime, timedelta

import pytest

from domain.items import DOCUMENT_TEXT
from domain.roles import Role

URL = "/v1/notifications"

MARIA = {
    "name": "Maria Silva",
    "email": "maria@example.com",
    "password": "senha-forte",
}
JOAO = {
    "name": "João Souza",
    "email": "joao@example.com",
    "password": "senha-forte",
}
CARLA = {
    "name": "Carla Lima",
    "email": "carla@example.com",
    "password": "senha-forte",
}
ADMIN = {
    "name": "Admin",
    "email": "admin@example.com",
    "password": "senha-do-admin",
}
ANA = {
    "name": "Ana Lima",
    "email": "ana@example.com",
    "password": "senha-forte",
}

NOT_AUTHENTICATED = {"detail": "Não autenticado"}
PERMISSION_DENIED = {"detail": "Sem permissão para esta operação"}


def read_url(notification_id: int) -> str:
    return f"{URL}/{notification_id}/read"


def category_id(client, name: str) -> int:
    response = client.get("/v1/categories")
    assert response.status_code == 200

    for category in response.json():
        if category["name"] == name:
            return category["id"]

    raise AssertionError(f"no category named {name}")


@pytest.fixture
def maria(signup):
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    return signup(JOAO)


@pytest.fixture
def carla(signup):
    return signup(CARLA)


@pytest.fixture
def admin(signup):
    return signup(ADMIN, Role.ADMIN)


@pytest.fixture
def point(client, admin):
    response = client.post(
        "/v1/collection-points",
        json={"name": "Biblioteca"},
        headers=admin.headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def attendant(client, signup, admin, point):
    account = signup(ANA, Role.ATENDENTE)

    response = client.post(
        f"/v1/collection-points/{point}/attendants",
        json={"user_id": account.id},
        headers=admin.headers,
    )
    assert response.status_code in (200, 201, 204)

    return account


@pytest.fixture
def item_payload(client, point):
    return {
        "category_id": category_id(client, "Mochilas"),
        "location_id": client.get("/v1/locations").json()[0]["id"],
        "color_id": client.get("/v1/colors").json()[0]["id"],
        "collection_point_id": point,
        "description": "Mochila azul com adesivo",
        "found_date": "2026-11-14",
        "questions": [
            {
                "question": "Qual a marca?",
                "answer": "Marca secreta",
            },
            {
                "question": "Qual o número de série?",
                "answer": "SERIE-1234",
            },
        ],
    }


def create_report(client, account, item_payload):
    payload = {
        "category_id": item_payload["category_id"],
        "location_id": item_payload["location_id"],
        "color_id": item_payload["color_id"],
        "description": item_payload["description"],
        "lost_date": item_payload["found_date"],
    }

    response = client.post(
        "/v1/lost-reports",
        json=payload,
        headers=account.headers,
    )

    assert response.status_code == 201
    return response.json()


def register_item(client, finder, payload):
    response = client.post(
        "/v1/items",
        json=payload,
        headers=finder.headers,
    )

    assert response.status_code == 201
    return response.json()["id"]


def receive_item(client, attendant, item_id, point):
    response = client.post(
        f"/v1/items/{item_id}/receive",
        json={"collection_point_id": point},
        headers=attendant.headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disponivel"


def list_notifications(client, account):
    response = client.get(URL, headers=account.headers)

    assert response.status_code == 200
    return response.json()


@pytest.fixture
def notification(client, clock, maria, joao, attendant, point, item_payload):
    report = create_report(client, joao, item_payload)
    item_id = register_item(client, maria, item_payload)

    receive_item(client, attendant, item_id, point)

    notifications = list_notifications(client, joao)

    assert len(notifications) == 1
    assert notifications[0]["lost_report_id"] == report["id"]
    assert notifications[0]["item_id"] == item_id

    return notifications[0]


# ==============================================================================
# RN30: automatic matching through the API
# ==============================================================================


def test_rn30_receiving_item_generates_notification(
    client, clock, maria, joao, attendant, point, item_payload
):
    report = create_report(client, joao, item_payload)
    item_id = register_item(client, maria, item_payload)

    # Notifications must only be created after receipt.
    assert list_notifications(client, joao) == []

    receive_item(client, attendant, item_id, point)

    [notification] = list_notifications(client, joao)

    assert notification["lost_report_id"] == report["id"]
    assert notification["item_id"] == item_id
    assert notification["read_at"] is None
    assert notification["created_at"] is not None
    assert notification["item_available"] is True


def test_rn30_creating_report_matches_available_item(
    client, clock, maria, joao, attendant, point, item_payload
):
    item_id = register_item(client, maria, item_payload)
    receive_item(client, attendant, item_id, point)

    assert list_notifications(client, joao) == []

    report = create_report(client, joao, item_payload)

    [notification] = list_notifications(client, joao)

    assert notification["lost_report_id"] == report["id"]
    assert notification["item_id"] == item_id
    assert notification["item_available"] is True


# ==============================================================================
# GET /v1/notifications
# ==============================================================================


def test_list_without_notifications_returns_empty_list(client, joao):
    assert list_notifications(client, joao) == []


def test_list_returns_only_own_notifications(
    client, clock, maria, joao, carla, attendant, point, item_payload
):
    joao_report = create_report(client, joao, item_payload)
    carla_report = create_report(client, carla, item_payload)

    item_id = register_item(client, maria, item_payload)
    receive_item(client, attendant, item_id, point)

    [joao_notification] = list_notifications(client, joao)
    [carla_notification] = list_notifications(client, carla)

    assert joao_notification["lost_report_id"] == joao_report["id"]
    assert carla_notification["lost_report_id"] == carla_report["id"]

    assert joao_notification["id"] != carla_notification["id"]

    assert joao_notification["item_id"] == item_id
    assert carla_notification["item_id"] == item_id

    assert list_notifications(client, maria) == []


def test_notifications_are_listed_newest_first(
    client, clock, maria, joao, attendant, point, item_payload
):
    create_report(client, joao, item_payload)

    first = register_item(client, maria, item_payload)
    receive_item(client, attendant, first, point)

    second = register_item(client, maria, item_payload)
    receive_item(client, attendant, second, point)

    notifications = list_notifications(client, joao)

    assert [n["item_id"] for n in notifications] == [second, first]

    first_created = datetime.fromisoformat(notifications[1]["created_at"])
    second_created = datetime.fromisoformat(notifications[0]["created_at"])

    assert second_created >= first_created


def test_list_without_token_returns_401(client):
    response = client.get(URL)

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


@pytest.mark.parametrize("role", [Role.ADMIN, Role.ATENDENTE])
def test_non_regular_user_cannot_list_notifications(client, signup, role):
    account = signup(ADMIN if role == Role.ADMIN else ANA, role)

    response = client.get(URL, headers=account.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


# ==============================================================================
# RN32 and RN52: privacy
# ==============================================================================


def test_rn32_notification_exposes_only_public_item(client, notification, item_payload):
    public_response = client.get("/v1/items")
    assert public_response.status_code == 200

    public_item = next(
        item for item in public_response.json() if item["id"] == notification["item_id"]
    )

    item = notification["item"]

    # RN32: notifications reuse the public item DTO.
    assert item == public_item
    assert item["public_description"] == item_payload["description"]

    for private in (
        "questions",
        "answers",
        "finder_id",
        "description",
        "status",
        "created_at",
        "history",
    ):
        assert private not in item

    assert "Marca secreta" not in str(notification)
    assert "SERIE-1234" not in str(notification)
    assert "Qual a marca?" not in str(notification)
    assert "Qual o número de série?" not in str(notification)


def test_rn32_rn52_document_notification_hides_private_description(
    client, clock, maria, joao, attendant, point, item_payload
):
    payload = {
        **item_payload,
        "category_id": category_id(client, "Documentos"),
        "description": "RG de João Silva",
    }

    create_report(client, joao, payload)

    item_id = register_item(client, maria, payload)
    receive_item(client, attendant, item_id, point)

    response = client.get(URL, headers=joao.headers)

    assert response.status_code == 200

    [notification] = response.json()

    assert notification["item_id"] == item_id
    assert notification["item"]["public_description"] == DOCUMENT_TEXT
    assert "João Silva" not in response.text


# ==============================================================================
# Current item availability
# ==============================================================================


def test_notification_remains_after_item_is_reserved(client, joao, attendant, notification):
    assert notification["item_available"] is True

    response = client.post(
        "/v1/claims",
        json={
            "item_id": notification["item_id"],
            "answers": [
                "Marca secreta",
                "SERIE-1234",
            ],
        },
        headers=joao.headers,
    )

    assert response.status_code == 201
    claim_id = response.json()["id"]

    response = client.post(
        f"/v1/claims/{claim_id}/approve",
        headers=attendant.headers,
    )

    assert response.status_code == 200

    [saved] = list_notifications(client, joao)

    # The notification remains, but the item is no longer available.
    assert saved["id"] == notification["id"]
    assert saved["item_id"] == notification["item_id"]
    assert saved["item_available"] is False
    assert "status" not in saved["item"]

    public_response = client.get("/v1/items")
    assert public_response.status_code == 200

    assert notification["item_id"] not in [item["id"] for item in public_response.json()]


# ==============================================================================
# PATCH /v1/notifications/{id}/read
# ==============================================================================


def test_owner_marks_notification_as_read(client, clock, joao, notification):
    assert notification["read_at"] is None

    response = client.patch(
        read_url(notification["id"]),
        headers=joao.headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == notification["id"]
    assert body["read_at"] is not None
    assert datetime.fromisoformat(body["read_at"]) == clock.now()

    # A new request confirms that the change was persisted.
    [saved] = list_notifications(client, joao)

    assert datetime.fromisoformat(saved["read_at"]) == datetime.fromisoformat(body["read_at"])


def test_marking_notification_twice_preserves_first_read_at(client, clock, joao, notification):
    url = read_url(notification["id"])

    first = client.patch(url, headers=joao.headers)
    assert first.status_code == 200

    first_read_at = first.json()["read_at"]
    assert first_read_at is not None

    clock.current += timedelta(hours=2)

    second = client.patch(url, headers=joao.headers)
    assert second.status_code == 200

    assert datetime.fromisoformat(second.json()["read_at"]) == datetime.fromisoformat(first_read_at)

    [saved] = list_notifications(client, joao)

    assert datetime.fromisoformat(saved["read_at"]) == datetime.fromisoformat(first_read_at)


def test_reading_notification_does_not_affect_other_user(
    client, clock, maria, joao, carla, attendant, point, item_payload
):
    create_report(client, joao, item_payload)
    create_report(client, carla, item_payload)

    item_id = register_item(client, maria, item_payload)
    receive_item(client, attendant, item_id, point)

    [joao_notification] = list_notifications(client, joao)
    [carla_notification] = list_notifications(client, carla)

    assert joao_notification["item_id"] == item_id
    assert carla_notification["item_id"] == item_id

    assert joao_notification["id"] != carla_notification["id"]
    assert joao_notification["read_at"] is None
    assert carla_notification["read_at"] is None

    response = client.patch(
        read_url(joao_notification["id"]),
        headers=joao.headers,
    )

    assert response.status_code == 200
    assert response.json()["read_at"] is not None

    [saved_joao] = list_notifications(client, joao)
    [saved_carla] = list_notifications(client, carla)

    assert saved_joao["read_at"] is not None
    assert saved_carla["read_at"] is None


def test_other_user_and_unknown_notification_return_same_404(client, joao, carla, notification):
    other_response = client.patch(
        read_url(notification["id"]),
        headers=carla.headers,
    )

    unknown_response = client.patch(
        read_url(999999),
        headers=carla.headers,
    )

    assert other_response.status_code == 404
    assert unknown_response.status_code == 404
    assert other_response.json() == unknown_response.json()

    # Unauthorized attempts must not modify the notification.
    [saved] = list_notifications(client, joao)

    assert saved["read_at"] is None


def test_marking_unknown_notification_returns_404(client, joao):
    response = client.patch(
        read_url(999999),
        headers=joao.headers,
    )

    assert response.status_code == 404


def test_marking_notification_without_token_returns_401(client, notification):
    response = client.patch(read_url(notification["id"]))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


@pytest.mark.parametrize("role", [Role.ADMIN, Role.ATENDENTE])
def test_non_regular_user_cannot_mark_notification(client, signup, notification, role):
    account = signup(
        {
            "name": "Outro funcionário",
            "email": "staff@example.com",
            "password": "senha-forte",
        },
        role,
    )

    response = client.patch(
        read_url(notification["id"]),
        headers=account.headers,
    )

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


def test_invalid_notification_id_returns_422(client, joao):
    response = client.patch(
        f"{URL}/nao-numerico/read",
        headers=joao.headers,
    )

    assert response.status_code == 422
