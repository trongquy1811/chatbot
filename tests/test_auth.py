from tests.mocks import TEST_TOKEN, TEST_USER


def test_auth_missing_token(app_and_client):
    client, _ = app_and_client
    response = client.get("/auth/verify")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_auth_invalid_token(app_and_client):
    client, _ = app_and_client
    response = client.get(
        "/auth/verify",
        headers={"Authorization": "Bearer invalid_token_1234567890abcdef"},
    )
    assert response.status_code == 401


def test_auth_valid_token(app_and_client):
    client, _ = app_and_client
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authenticated"
    assert data["owner"] == TEST_USER


def test_protected_routes_require_auth(app_and_client):
    client, _ = app_and_client
    # Test GET /documents
    res_docs = client.get("/documents")
    assert res_docs.status_code == 401

    # Test GET /conversations
    res_convs = client.get("/conversations")
    assert res_convs.status_code == 401

    # Test GET /memories
    res_mems = client.get("/memories")
    assert res_mems.status_code == 401
