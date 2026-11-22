import os

import psycopg
import pytest

from domain.lost_reports import LostReportStatus
from domain.roles import Role

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}
JOAO = {"name": "João Souza", "email": "joao@example.com", "password": "senha-forte"}
CARLA = {"name": "Carla Lima", "email": "carla@example.com", "password": "senha-da-carla"}
ADMIN = {"name": "Admin", "email": "admin@example.com", "password": "senha-do-admin"}

URL = "/v1/lost-reports"
NOT_AUTHENTICATED = {"detail": "Não autenticado"}
PERMISSION_DENIED = {"detail": "Sem permissão para esta operação"}


def report_url(report_id: int) -> str:
    return f"{URL}/{report_id}"


def close_url(report_id: int) -> str:
    return f"{URL}/{report_id}/close"


@pytest.fixture
def maria(signup):
    return signup(MARIA)


@pytest.fixture
def joao(signup):
    return signup(JOAO)


@pytest.fixture
def carla(signup):
    return signup(CARLA, Role.ATENDENTE)


@pytest.fixture
def admin(signup):
    return signup(ADMIN, Role.ADMIN)


@pytest.fixture
def valid_payload(client) -> dict:
    category_id = client.get("/v1/categories").json()[0]["id"]
    location_id = client.get("/v1/locations").json()[0]["id"]
    color_id = client.get("/v1/colors").json()[0]["id"]
    return {
        "category_id": category_id,
        "location_id": location_id,
        "color_id": color_id,
        "description": "Garrafa térmica azul",
        "lost_date": "2026-11-15",
    }


def _get_db_status(report_id: int) -> str | None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute("SELECT status FROM lost_reports WHERE id = %s", (report_id,)).fetchone()
        return row[0] if row else None


# ==============================================================================
# POST /v1/lost-reports
# ==============================================================================


def test_user_creates_lost_report(client, maria, valid_payload):
    # §8 & §11: usuário comum cria relato que nasce como ATIVO e vinculado ao próprio user_id
    response = client.post(URL, json=valid_payload, headers=maria.headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == LostReportStatus.ATIVO
    assert body["user_id"] == maria.id
    assert body["description"] == valid_payload["description"]


def test_create_strips_whitespace_from_description(client, maria, valid_payload):
    # §8: espaços nas pontas são removidos pelo schema
    payload = {**valid_payload, "description": "   Chaveiro com fita vermelha   "}

    response = client.post(URL, json=payload, headers=maria.headers)

    assert response.status_code == 201
    assert response.json()["description"] == "Chaveiro com fita vermelha"


def test_create_accepts_500_chars_and_rejects_501(client, maria, valid_payload):
    # §8: limite máximo de 500 caracteres na descrição
    ok_resp = client.post(
        URL, json={**valid_payload, "description": "a" * 500}, headers=maria.headers
    )
    assert ok_resp.status_code == 201

    fail_resp = client.post(
        URL, json={**valid_payload, "description": "a" * 501}, headers=maria.headers
    )
    assert fail_resp.status_code == 422


def test_create_without_token_returns_401(client, valid_payload):
    # §11: endpoint exige autenticação
    response = client.post(URL, json=valid_payload)

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_non_regular_user_cannot_create_report(client, signup, valid_payload, role):
    # §11: apenas usuários comuns podem registrar relato de perda
    account = signup(CARLA if role == Role.ATENDENTE else ADMIN, role)

    response = client.post(URL, json=valid_payload, headers=account.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


def test_attendant_with_unknown_category_gets_403_not_404(client, carla, valid_payload):
    # §11: permissão é checada antes da existência das FKs no banco
    payload = {**valid_payload, "category_id": 999999}

    response = client.post(URL, json=payload, headers=carla.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


@pytest.mark.parametrize(
    ("reference_field", "expected_detail"),
    [
        ("category_id", "Categoria não encontrada"),
        ("location_id", "Local não encontrado"),
        ("color_id", "Cor não encontrada"),
    ],
)
def test_create_with_unknown_reference_returns_404(
    client, maria, valid_payload, reference_field, expected_detail
):
    # §8: cada referência inexistente retorna o 404 específico do domínio
    payload = {**valid_payload, reference_field: 999999}

    response = client.post(URL, json=payload, headers=maria.headers)

    assert response.status_code == 404
    assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize("blank", ["", "    ", "\t\n"])
def test_create_with_blank_description_returns_422(client, maria, valid_payload, blank):
    # §8: descrição vazia ou só com espaços é barrada no schema
    payload = {**valid_payload, "description": blank}

    response = client.post(URL, json=payload, headers=maria.headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty"),
        pytest.param(
            {
                "category_id": 1,
                "location_id": 1,
                "color_id": 1,
                "description": "Mochila azul",
                "lost_date": "data-invalida",
            },
            id="bad-date",
        ),
        pytest.param(
            {
                "category_id": "nao-eh-numero",
                "location_id": 1,
                "color_id": 1,
                "description": "Mochila azul",
                "lost_date": "2026-11-15",
            },
            id="bad-category",
        ),
    ],
)
def test_create_with_invalid_types_or_missing_fields_returns_422(client, maria, payload):
    # §8: validação de tipos e campos obrigatórios do payload
    response = client.post(URL, json=payload, headers=maria.headers)

    assert response.status_code == 422


# ==============================================================================
# GET /v1/lost-reports (meus relatos)
# ==============================================================================


def test_list_mine_returns_only_own_reports_including_closed(client, maria, joao, valid_payload):
    # §8 & §11: cada usuário vê apenas seus próprios relatos, inclusive os encerrados
    r_maria_1 = client.post(
        URL, json={**valid_payload, "description": "Relato Maria 1"}, headers=maria.headers
    ).json()
    r_maria_2 = client.post(
        URL, json={**valid_payload, "description": "Relato Maria 2"}, headers=maria.headers
    ).json()
    client.post(URL, json={**valid_payload, "description": "Relato João"}, headers=joao.headers)

    client.patch(close_url(r_maria_1["id"]), headers=maria.headers)

    maria_list = client.get(URL, headers=maria.headers)
    assert maria_list.status_code == 200
    assert [r["id"] for r in maria_list.json()] == [r_maria_2["id"], r_maria_1["id"]]

    joao_list = client.get(URL, headers=joao.headers)
    assert joao_list.status_code == 200
    assert [r["description"] for r in joao_list.json()] == ["Relato João"]


def test_list_mine_returns_empty_list_when_user_has_no_reports(client, maria):
    # §11: usuário sem relatos recebe lista vazia
    response = client.get(URL, headers=maria.headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_mine_without_token_returns_401(client):
    # §11: listagem exige autenticação
    response = client.get(URL)

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


@pytest.mark.parametrize("role", [Role.ATENDENTE, Role.ADMIN])
def test_non_regular_user_cannot_list_reports(client, signup, role):
    # §11: apenas usuários comuns possuem lista de relatos pessoais
    account = signup(CARLA if role == Role.ATENDENTE else ADMIN, role)

    response = client.get(URL, headers=account.headers)

    assert response.status_code == 403
    assert response.json() == PERMISSION_DENIED


# ==============================================================================
# GET /v1/lost-reports/{id}
# ==============================================================================


def test_owner_gets_own_report(client, maria, valid_payload):
    # §11: dono consegue visualizar o próprio relato
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    response = client.get(report_url(created["id"]), headers=maria.headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_other_user_and_unknown_id_return_identical_404(client, maria, joao, valid_payload):
    # §11: relato alheio e ID inexistente devolvem exatamente o mesmo 404 para não vazar existência
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    other_resp = client.get(report_url(created["id"]), headers=joao.headers)
    unknown_resp = client.get(report_url(999999), headers=joao.headers)

    assert other_resp.status_code == 404
    assert unknown_resp.status_code == 404
    assert other_resp.json() == unknown_resp.json()


def test_admin_and_attendant_get_404_on_any_report(client, maria, carla, admin, valid_payload):
    # §11: pela regra de acesso, nem admin nem atendente acessam relato individual (404)
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    assert client.get(report_url(created["id"]), headers=carla.headers).status_code == 404
    assert client.get(report_url(created["id"]), headers=admin.headers).status_code == 404


def test_get_report_without_token_returns_401(client, maria, valid_payload):
    # §11: visualização exige autenticação
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    response = client.get(report_url(created["id"]))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


def test_get_report_with_non_integer_id_returns_422(client, maria):
    # §11: validação de parâmetro de rota
    response = client.get(f"{URL}/nao-numerico", headers=maria.headers)

    assert response.status_code == 422


# ==============================================================================
# PATCH /v1/lost-reports/{id}/close
# ==============================================================================


def test_owner_closes_active_report(client, maria, valid_payload):
    # §8 & §11: dono encerra relato ATIVO -> ENCERRADO e GET posterior confirma persistência
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    close_resp = client.patch(close_url(created["id"]), headers=maria.headers)
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == LostReportStatus.ENCERRADO

    get_resp = client.get(report_url(created["id"]), headers=maria.headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == LostReportStatus.ENCERRADO


def test_closing_already_closed_report_returns_409(client, maria, valid_payload):
    # §8: ENCERRADO é estado final; encerrar novamente viola transição (409)
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()
    assert client.patch(close_url(created["id"]), headers=maria.headers).status_code == 200

    second_close = client.patch(close_url(created["id"]), headers=maria.headers)
    assert second_close.status_code == 409


def test_closing_expired_report_returns_409(client, maria, valid_payload):
    # §8: EXPIRADO é estado final; não pode transicionar para ENCERRADO (409)
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()
    report_id = created["id"]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            "UPDATE lost_reports SET status = %s WHERE id = %s",
            (LostReportStatus.EXPIRADO, report_id),
        )

    response = client.patch(close_url(report_id), headers=maria.headers)
    assert response.status_code == 409
    assert _get_db_status(report_id) == LostReportStatus.EXPIRADO


def test_closing_another_users_report_returns_404_and_keeps_it_active(
    client, maria, joao, valid_payload
):
    # §11: outro usuário recebe 404 e o relato permanece ATIVO no banco
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()
    report_id = created["id"]

    response = client.patch(close_url(report_id), headers=joao.headers)

    assert response.status_code == 404
    assert _get_db_status(report_id) == LostReportStatus.ATIVO


def test_closing_unknown_report_returns_404(client, maria):
    # §11: ID inexistente devolve 404
    response = client.patch(close_url(999999), headers=maria.headers)

    assert response.status_code == 404


def test_closing_report_without_token_returns_401(client, maria, valid_payload):
    # §11: encerramento exige autenticação
    created = client.post(URL, json=valid_payload, headers=maria.headers).json()

    response = client.patch(close_url(created["id"]))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED
