def test_list_categories(client):
    response = client.get("/v1/categories")

    assert response.status_code == 200
    names = [category["name"] for category in response.json()]
    assert "Documentos" in names
    assert names == sorted(names)
