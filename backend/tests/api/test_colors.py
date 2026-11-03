def test_list_colors(client):
    response = client.get("/v1/colors")

    assert response.status_code == 200
    names = [color["name"] for color in response.json()]
    assert "Preto" in names
    assert names == sorted(names)
