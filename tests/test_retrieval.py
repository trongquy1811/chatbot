from unittest.mock import MagicMock
from redis.exceptions import RedisError
from backend.services.cache import RetrievalCache
from backend.services.vectors import Vectors
from tests.mocks import MockEmbeddings


def test_vectors_add_and_search(tmp_path, test_settings):
    embeddings = MockEmbeddings()
    from qdrant_client import QdrantClient
    client = QdrantClient(":memory:")

    vectors = Vectors(settings=test_settings, embeddings=embeddings, client=client)

    chunks = [
        {"page": 1, "text": "LangGraph is a library for building stateful, multi-actor applications."},
        {"page": 2, "text": "Qdrant provides high performance vector search and payload filtering."},
    ]

    owner = "user_alpha"
    doc_id = "doc_123"
    vectors.add(owner=owner, document_id=doc_id, name="guide.txt", chunks=chunks)

    # Search existing
    results = vectors.search(owner=owner, document_ids=[doc_id], question="What is Qdrant?", limit=2)
    assert len(results) == 2
    assert results[0]["document_id"] == doc_id
    assert results[0]["name"] == "guide.txt"

    # Search unauthorized owner
    unauth_results = vectors.search(owner="other_user", document_ids=[doc_id], question="What is Qdrant?")
    assert len(unauth_results) == 0

    # Search with empty document_ids
    empty_results = vectors.search(owner=owner, document_ids=[], question="Test")
    assert len(empty_results) == 0


def test_retrieval_cache_fallback():
    # Cache without Redis client (fallback to fetch)
    cache = RetrievalCache(url=None)
    fetch_counter = {"called": 0}

    def sample_fetch():
        fetch_counter["called"] += 1
        return [{"chunk_id": "1", "text": "Sample"}]

    result = cache.retrieve("user1", ["doc1"], "query", 5, sample_fetch)
    assert len(result) == 1
    assert fetch_counter["called"] == 1


def test_retrieval_cache_redis_error_resilience():
    # Mock Redis client that throws error on get and set
    cache = RetrievalCache(url=None)
    mock_redis = MagicMock()
    mock_redis.get.side_effect = RedisError("Connection refused")
    mock_redis.setex.side_effect = RedisError("Connection refused")
    cache.client = mock_redis

    fetch_called = False

    def fetch_fn():
        nonlocal fetch_called
        fetch_called = True
        return [{"chunk_id": "2", "text": "Resilience test"}]

    res = cache.retrieve("user1", ["doc1"], "query", 5, fetch_fn)
    assert fetch_called is True
    assert len(res) == 1
