# RN40: only an admin registers collection points and links attendants to them
import pytest

from domain.roles import Role

ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}
CARLA = {"name": "Carla Lima", "email": "carla@example.com", "password": "senha-da-carla"}
MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}

URL = "/v1/collection-points"
NOT_AUTHENTICATED = {"detail": "Não autenticado"}
PERMISSION_DENIED = {"detail": "Sem permissão para esta operação"}


def attendants_url(point_id: int) -> str:
    return f"{URL}/{point_id}/attendants"


@pytest.fixture
def admin(signup):
    return signup(ADMIN, Role.ADMIN)


@pytest.fixture
def carla(signup):
    return signup(CARLA, Role.ATENDENTE)


@pytest.fixture
def maria(signup):
    return signup(MARIA)


@pytest.fixture
def create_point(client, admin):
    def create(name: str) -> dict:
        return client.post(URL, json={"name": name}, headers=admin.headers).json()

    return create


@pytest.fixture
def link(client, admin):
    def link(point_id: int, user_id: int):
        return client.post(
            attendants_url(point_id), json={"user_id": user_id}, headers=admin.headers
        )

    return link


# --- the list is public: the finder picks a point when registering an item ---


def test_list_is_public_and_sorted_by_name(client, create_point):
    create_point("Secretaria")
    create_point("Biblioteca")

    response = client.get(URL)

    assert response.status_code == 200
    assert [point["name"] for point in response.json()] == ["Biblioteca", "Secretaria"]


# --- creating ---


def test_admin_creates_point(client, admin):
    response = client.post(URL, json={"name": "  Biblioteca  "}, headers=admin.headers)

    assert response.status_code == 201
    assert response.json()["name"] == "Biblioteca"


@pytest.mark.parametrize("role", [Role.USUARIO, Role.ATENDENTE])
def test_only_admin_creates_point(client, signup, role):
    account = signup(MARIA, role)

    response = client.post(URL, json={"name": "Biblioteca"}, headers=account.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


def test_create_without_token_returns_401(client):
    response = client.post(URL, json={"name": "Biblioteca"})

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


def test_blank_name_returns_422(client, admin):
    response = client.post(URL, json={"name": "   "}, headers=admin.headers)

    assert response.status_code == 422


def test_duplicate_name_returns_409(client, admin, create_point):
    create_point("Biblioteca")

    response = client.post(URL, json={"name": "Biblioteca"}, headers=admin.headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Já existe um ponto de coleta com este nome"}


# --- linking ---


def test_admin_links_attendant(client, admin, carla, create_point, link):
    point = create_point("Biblioteca")

    response = link(point["id"], carla.id)

    assert response.status_code == 201
    assert response.json()["id"] == carla.id
    listed = client.get(attendants_url(point["id"]), headers=admin.headers).json()
    assert [user["id"] for user in listed] == [carla.id]


def test_attendant_works_at_two_points(carla, create_point, link):
    for name in ("Biblioteca", "Secretaria"):
        point = create_point(name)
        assert link(point["id"], carla.id).status_code == 201


def test_linking_twice_returns_409(carla, create_point, link):
    point = create_point("Biblioteca")
    link(point["id"], carla.id)

    response = link(point["id"], carla.id)

    assert response.status_code == 409
    assert response.json() == {"detail": "Atendente já vinculado a este ponto"}


def test_linking_a_non_attendant_returns_409(maria, create_point, link):
    point = create_point("Biblioteca")

    response = link(point["id"], maria.id)

    assert response.status_code == 409
    assert response.json() == {"detail": "O usuário não é atendente"}


def test_linking_to_unknown_point_returns_404(carla, link):
    response = link(999, carla.id)

    assert response.status_code == 404
    assert response.json() == {"detail": "Ponto de coleta não encontrado"}


def test_linking_unknown_user_returns_404(create_point, link):
    point = create_point("Biblioteca")

    response = link(point["id"], 999)

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado"}


def test_non_admin_gets_403_even_for_unknown_point(client, carla):
    # the permission comes first, so a non-admin learns nothing about which points exist
    response = client.post(attendants_url(999), json={"user_id": carla.id}, headers=carla.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


# --- unlinking ---


def test_admin_unlinks_attendant(client, admin, carla, create_point, link):
    point = create_point("Biblioteca")
    link(point["id"], carla.id)

    response = client.delete(f"{attendants_url(point['id'])}/{carla.id}", headers=admin.headers)

    assert response.status_code == 204
    assert client.get(attendants_url(point["id"]), headers=admin.headers).json() == []


def test_unlinking_unknown_link_returns_404(client, admin, carla, create_point):
    point = create_point("Biblioteca")

    response = client.delete(f"{attendants_url(point['id'])}/{carla.id}", headers=admin.headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Atendente não vinculado a este ponto"}


def test_deleting_the_attendant_removes_the_link(client, admin, carla, create_point, link):
    # ON DELETE CASCADE: the link goes with the user
    point = create_point("Biblioteca")
    link(point["id"], carla.id)

    assert client.delete(f"/v1/users/{carla.id}", headers=admin.headers).status_code == 204
    assert client.get(attendants_url(point["id"]), headers=admin.headers).json() == []
