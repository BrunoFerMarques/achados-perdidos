def test_preflight_from_the_frontend_is_allowed(client):
    response = client.options(
        "/v1/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_gets_no_permission(client):
    response = client.get("/", headers={"Origin": "http://site-estranho.com"})

    assert "access-control-allow-origin" not in response.headers
