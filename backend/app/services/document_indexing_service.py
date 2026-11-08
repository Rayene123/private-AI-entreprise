from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.exceptions import ValidationError
from app.integrations.ollama import EmbeddingProvider, OllamaEmbeddingProvider
from app.integrations.qdrant import QdrantVectorStore
from app.schemas.ingestion import IngestionResponse
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.document_service import DocumentService


class DocumentIndexingService:
    def __init__(
        self,
        document_service: DocumentService,
        ingestion_service: DocumentIngestionService,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self._documents = document_service
        self._ingestion = ingestion_service
        self._embeddings = embedding_provider or OllamaEmbeddingProvider()
        self._vectors = vector_store or QdrantVectorStore()

    def index(self, user_id: UUID, document_id: UUID) -> IngestionResponse:
        document = self._documents.get_document(user_id, document_id)
        ingestion = self._ingestion.ingest(user_id, document_id)
        self._vectors.ensure_collection()
        vectors = self._embeddings.embed([chunk.text for chunk in ingestion.chunks])
        if len(vectors) != len(ingestion.chunks):
            raise ValidationError(
                "The embedding provider returned an incomplete response.",
                code="embedding_response_incomplete",
            )
        points = []
        for chunk, vector in zip(ingestion.chunks, vectors):
            points.append(
                {
                    "id": str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                    "vector": vector,
                    "payload": {
                        "document_id": str(document.id),
                        "chunk_id": chunk.chunk_id,
                        "owner_id": str(document.owner_id),
                        "department_id": (
                            str(document.department_id)
                            if document.department_id
                            else None
                        ),
                        "access_level": document.access_level,
                        "document_status": document.status,
                        "chunk_index": chunk.chunk_index,
                        "source_hash": chunk.source_hash,
                        "source_filename": document.original_filename,
                        "page_number": chunk.page_number,
                        "content": chunk.text,
                        "embedding_model": self._embeddings.model,
                        "embedding_dimension": self._embeddings.dimension,
                    },
                }
            )
        self._vectors.upsert(points)
        self._vectors.delete_obsolete(document.id, ingestion.source_hash)
        return ingestion.model_copy(
            update={
                "indexed_count": len(points),
                "embedding_model": self._embeddings.model,
                "indexing_status": "indexed",
            }
        )

    def cleanup_created_index(self, document_id: UUID) -> None:
        self._vectors.delete_document(document_id)
