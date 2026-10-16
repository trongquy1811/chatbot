import pytest
from backend.config import Settings
from backend.main import create_app
from fastapi.testclient import TestClient
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
    res_docs = client.get("/documents")
    assert res_docs.status_code == 401

    res_convs = client.get("/conversations")
    assert res_convs.status_code == 401

    res_mems = client.get("/memories")
    assert res_mems.status_code == 401


def test_startup_fails_on_missing_or_invalid_api_keys(tmp_path):
    # Empty API_KEYS_JSON raises ValueError on keys()
    settings_empty = Settings(
        database_url=f"sqlite:///{tmp_path / 't1.db'}",
        data_dir=tmp_path / "data1",
        api_keys_json="",
    )
    with pytest.raises(ValueError, match="API_KEYS_JSON chưa được thiết lập"):
        settings_empty.keys()

    # Short token raises ValueError
    settings_short = Settings(
        database_url=f"sqlite:///{tmp_path / 't2.db'}",
        data_dir=tmp_path / "data2",
        api_keys_json='{"short_tok": "admin"}',
    )
    with pytest.raises(ValueError, match="24 ký tự trở lên"):
        settings_short.keys()

    # Lifespan startup fails with RuntimeError
    app = create_app(settings=settings_empty)
    with pytest.raises(RuntimeError, match="Khởi động thất bại do cấu hình"):
        with TestClient(app):
            pass
