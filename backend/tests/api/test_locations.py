def test_list_locations(client):
    response = client.get("/v1/locations")

    assert response.status_code == 200
    names = [location["name"] for location in response.json()]
    assert "Biblioteca" in names
    assert names == sorted(names)
