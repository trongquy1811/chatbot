import logging
from typing import Any
from uuid import uuid4
from qdrant_client import QdrantClient, models
from backend.config import Settings

logger = logging.getLogger("docanalyzer.vectors")


class Vectors:
    """Manages Qdrant vector database indexing, filtering, and semantic search."""

    def __init__(self, settings: Settings, embeddings: Any, client: QdrantClient | None = None):
        self.embeddings = embeddings
        self.collection = settings.qdrant_collection
        self.memory_collection = settings.qdrant_memory_collection
        self.remote = bool(settings.qdrant_url)

        if client is not None:
            self.client = client
        elif settings.qdrant_url:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
                timeout=30,
            )
        else:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(settings.data_dir / "qdrant"))

    def _scope_documents(self, owner: str, document_ids: list[str]) -> models.Filter:
        return models.Filter(must=[
            models.FieldCondition(
                key="owner",
                match=models.MatchValue(value=owner),
            ),
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=document_ids),
            ),
        ])

    def _ensure_collection(self, collection_name: str, vector_size: int, payload_indices: list[str]) -> None:
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            if self.remote:
                for field in payload_indices:
                    self.client.create_payload_index(
                        collection_name,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                        wait=True,
                    )

    def add(self, owner: str, document_id: str, name: str, chunks: list[dict[str, Any]]) -> None:
        """Embed and upsert document chunks into Qdrant."""
        if not chunks:
            return

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embeddings.embed_documents(texts)

        self._ensure_collection(
            collection_name=self.collection,
            vector_size=len(embeddings[0]),
            payload_indices=["owner", "document_id"],
        )

        # Batch upsert in chunks of 64
        for start in range(0, len(chunks), 64):
            batch = [
                models.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        **chunk,
                        "owner": owner,
                        "document_id": document_id,
                        "name": name,
                    },
                )
                for chunk, vector in zip(
                    chunks[start:start + 64],
                    embeddings[start:start + 64],
                )
            ]

            self.client.upsert(
                collection_name=self.collection,
                points=batch,
                wait=True,
            )

    def search(
        self,
        owner: str,
        document_ids: list[str],
        question: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform semantic search over authorized document chunks."""
        if not document_ids or not self.client.collection_exists(self.collection):
            return []

        query_vector = self.embeddings.embed_query(question)
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=self._scope_documents(owner, document_ids),
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "chunk_id": str(point.id),
                **point.payload,
                "score": point.score,
            }
            for point in response.points
        ]

    def delete(self, owner: str, document_id: str) -> None:
        """Delete all vector points belonging to a specific document."""
        if self.client.collection_exists(self.collection):
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.FilterSelector(
                    filter=self._scope_documents(owner, [document_id])
                ),
                wait=True,
            )

    # Memory Vector Sync
    def index_memory(self, owner: str, memory_id: str, key: str, value: str) -> None:
        """Index accepted memory into Qdrant."""
        vector = self.embeddings.embed_query(f"{key}: {value}")
        self._ensure_collection(
            collection_name=self.memory_collection,
            vector_size=len(vector),
            payload_indices=["owner", "memory_id", "key"],
        )

        self.client.upsert(
            collection_name=self.memory_collection,
            points=[
                models.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "owner": owner,
                        "memory_id": memory_id,
                        "key": key,
                        "value": value,
                    },
                )
            ],
            wait=True,
        )

    def delete_memory(self, owner: str, memory_id: str) -> None:
        """Remove memory from Qdrant vector index."""
        if self.client.collection_exists(self.memory_collection):
            filter_condition = models.Filter(must=[
                models.FieldCondition(key="owner", match=models.MatchValue(value=owner)),
                models.FieldCondition(key="memory_id", match=models.MatchValue(value=memory_id)),
            ])
            self.client.delete(
                collection_name=self.memory_collection,
                points_selector=models.FilterSelector(filter=filter_condition),
                wait=True,
            )

    def search_memories(self, owner: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve semantic memories accepted for user."""
        if not self.client.collection_exists(self.memory_collection):
            return []

        query_vector = self.embeddings.embed_query(query)
        filter_condition = models.Filter(must=[
            models.FieldCondition(key="owner", match=models.MatchValue(value=owner)),
        ])

        response = self.client.query_points(
            collection_name=self.memory_collection,
            query=query_vector,
            query_filter=filter_condition,
            limit=limit,
            with_payload=True,
        )

        return [point.payload for point in response.points if point.payload]
