import json
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from backend.config import Settings
from backend.main import create_app
from tests.mocks import TEST_TOKEN, TEST_USER, MockGemini


@pytest.fixture
def test_settings(tmp_path):
    """Fixture providing isolated temporary settings."""
    keys_json = json.dumps({TEST_TOKEN: TEST_USER})
    db_file = tmp_path / "test.db"
    return Settings(
        database_url=f"sqlite:///{db_file}",
        data_dir=tmp_path / "data",
        api_keys_json=keys_json,
        google_api_key="mock_google_api_key",
        qdrant_url="",  # Local mode
        redis_url="",   # Disabled for isolated test
    )


@pytest.fixture
def mock_gemini():
    return MockGemini()


@pytest.fixture
def in_memory_qdrant():
    return QdrantClient(":memory:")


@pytest.fixture
def app_and_client(test_settings, mock_gemini, in_memory_qdrant):
    """Provides a configured FastAPI test client with initialized lifespan."""
    application = create_app(
        settings=test_settings,
        ai=mock_gemini,
        vector_client=in_memory_qdrant,
    )
    with TestClient(application) as client:
        yield client, application
