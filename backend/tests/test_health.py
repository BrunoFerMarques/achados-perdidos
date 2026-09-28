def test_root_returns_status_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"mensagem": "API Achados e Perdidos no ar"}


def test_health_returns_ok_when_database_is_up(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "banco": "ok"}


def test_health_returns_503_when_database_is_down(client, monkeypatch):
    # nothing listens on port 1, so the connection is refused right away
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/none")

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}
