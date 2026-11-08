from __future__ import annotations

import logging
from time import monotonic
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppException,
    IntegrationUnavailableError,
    ValidationError,
)
from app.integrations.ollama import EmbeddingProvider, OllamaEmbeddingProvider
from app.integrations.qdrant import QdrantVectorStore
from app.schemas.document import DocumentResponse
from app.schemas.retrieval import (
    RetrievedChunk,
    RetrievedChunkMetadata,
    RetrievalResponse,
)
from app.services.document_service import DocumentService
from app.services.permission_service import AuthorizationService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        document_service: DocumentService,
        authorization_service: AuthorizationService,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: QdrantVectorStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._documents = document_service
        self._authorization = authorization_service
        self._embeddings = embedding_provider or OllamaEmbeddingProvider()
        self._vectors = vector_store or QdrantVectorStore()
        self._settings = settings or get_settings()

    def retrieve(
        self,
        user_id: UUID,
        query: str,
        top_k: int | None = None,
    ) -> RetrievalResponse:
        started = monotonic()
        self._authorization.require_permission(user_id, "chat.use")
        self._authorization.require_permission(user_id, "documents.read")
        normalized_query = query.strip()
        if not normalized_query:
            raise ValidationError(
                "The query must not be empty.",
                code="invalid_retrieval_query",
            )
        if len(normalized_query) > self._settings.retrieval_max_query_length:
            raise ValidationError(
                "The query is too long.",
                code="retrieval_query_too_long",
            )

        authorized_documents = self._documents.list_documents(user_id)
        document_ids = [document.id for document in authorized_documents]
        effective_top_k = top_k or self._settings.retrieval_top_k
        vector = self._embeddings.embed([normalized_query])[0]
        candidates = self._vectors.search(
            vector,
            top_k=effective_top_k,
            min_score=self._settings.retrieval_min_score,
            document_ids=document_ids,
        )
        results: list[RetrievedChunk] = []
        for candidate in candidates:
            result = self._authorize_candidate(user_id, candidate)
            if result is not None:
                results.append(result)

        logger.info(
            "semantic_retrieval_completed",
            extra={
                "user_id": str(user_id),
                "candidate_count": len(candidates),
                "authorized_result_count": len(results),
                "retrieval_status": "success",
                "retrieval_duration_ms": round((monotonic() - started) * 1000, 2),
                "embedding_provider": self._settings.embedding_provider,
            },
        )
        return RetrievalResponse(
            query=normalized_query,
            results=results,
            retrieved_count=len(results),
        )

    def _authorize_candidate(
        self,
        user_id: UUID,
        candidate: dict,
    ) -> RetrievedChunk | None:
        payload = candidate.get("payload")
        if not isinstance(payload, dict):
            raise IntegrationUnavailableError(
                "Semantic retrieval returned invalid metadata.",
                code="retrieval_response_invalid",
            )
        try:
            document_id = UUID(str(payload["document_id"]))
            chunk_id = str(payload["chunk_id"])
            content = payload["content"]
            score = float(candidate["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrationUnavailableError(
                "Semantic retrieval returned invalid metadata.",
                code="retrieval_response_invalid",
            ) from exc
        if not isinstance(content, str) or not content:
            raise IntegrationUnavailableError(
                "Semantic retrieval returned invalid content.",
                code="retrieval_response_invalid",
            )
        try:
            document: DocumentResponse = self._documents.get_document(
                user_id,
                document_id,
            )
        except AppException as exc:
            if exc.code in {
                "document_access_denied",
                "document_not_found",
            }:
                return None
            raise
        if document.status != "active":
            return None
        return RetrievedChunk(
            document_id=document.id,
            chunk_id=chunk_id,
            content=content,
            score=score,
            metadata=RetrievedChunkMetadata(
                source_filename=document.original_filename,
                page_number=payload.get("page_number"),
                section_title=payload.get("section_title"),
                chunk_index=payload.get("chunk_index"),
                source_hash=payload.get("source_hash"),
            ),
        )


def get_retrieval_service(
    document_service: DocumentService,
    authorization_service: AuthorizationService,
) -> RetrievalService:
    return RetrievalService(document_service, authorization_service)
