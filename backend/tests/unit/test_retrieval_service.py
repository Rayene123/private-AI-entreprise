from uuid import UUID, uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    AuthorizationError,
    IntegrationUnavailableError,
    ResourceNotFoundError,
)
from app.schemas.document import DocumentListItem, DocumentResponse
from app.services.retrieval_service import RetrievalService

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def settings() -> Settings:
    return Settings(
        embedding_model="test",
        embedding_dimension=2,
        embedding_url="http://embedding.test",
        qdrant_url="http://qdrant.test",
    )


def document(document_id: UUID = DOCUMENT_ID) -> DocumentResponse:
    return DocumentResponse(
        id=document_id,
        owner_id=USER_ID,
        title="Policy",
        original_filename="policy.txt",
        status="active",
        access_level="private",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class Authorization:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.permissions: list[str] = []

    def require_permission(self, user_id, permission_name) -> None:
        self.permissions.append(permission_name)
        if not self.allowed:
            raise AuthorizationError(code="insufficient_permissions")


class Documents:
    def __init__(self, result: DocumentResponse | None = None, error=None) -> None:
        self.result = result
        self.error = error
        self.verified: list[UUID] = []

    def list_documents(self, user_id):
        row = document().model_dump(exclude={"storage_path"})
        return [
            DocumentListItem(
                **row,
            )
        ] if self.result else []

    def get_document(self, user_id, document_id):
        self.verified.append(document_id)
        if self.error:
            raise self.error
        if document_id != DOCUMENT_ID:
            raise ResourceNotFoundError(code="document_not_found")
        return self.result


class Embeddings:
    model = "test"
    dimension = 2

    def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


class Vectors:
    def __init__(self, candidates) -> None:
        self.candidates = candidates
        self.calls = []

    def search(self, vector, **kwargs):
        self.calls.append((vector, kwargs))
        return self.candidates


def candidate(document_id=DOCUMENT_ID, content="authorized") -> dict:
    return {
        "score": 0.9,
        "payload": {
            "document_id": str(document_id),
            "chunk_id": "chunk-1",
            "content": content,
            "page_number": 3,
        },
    }


def service(documents, authorization, candidates):
    return RetrievalService(
        documents,
        authorization,
        embedding_provider=Embeddings(),
        vector_store=Vectors(candidates),
        settings=settings(),
    )


def test_retrieval_requires_chat_and_document_permissions() -> None:
    authorization = Authorization()
    result = service(Documents(document()), authorization, []).retrieve(
        USER_ID,
        "leave policy",
    )

    assert result.retrieved_count == 0
    assert authorization.permissions == ["chat.use", "documents.read"]


def test_retrieval_revalidates_each_candidate_against_documents() -> None:
    documents = Documents(document())
    unauthorized_document_id = uuid4()
    result = service(
        documents,
        Authorization(),
        [candidate(), candidate(unauthorized_document_id)],
    ).retrieve(USER_ID, "leave policy")

    assert result.retrieved_count == 1
    assert result.results[0].content == "authorized"
    assert documents.verified == [DOCUMENT_ID, unauthorized_document_id]


def test_unauthorized_candidate_is_not_returned() -> None:
    documents = Documents(
        document(),
        error=AuthorizationError(code="document_access_denied"),
    )

    result = service(documents, Authorization(), [candidate()]).retrieve(
        USER_ID,
        "leave policy",
    )

    assert result.results == []


def test_malformed_candidate_fails_closed() -> None:
    with pytest.raises(IntegrationUnavailableError) as error:
        service(
            Documents(document()),
            Authorization(),
            [{"score": 0.8, "payload": {"document_id": str(DOCUMENT_ID)}}],
        ).retrieve(USER_ID, "leave policy")
    assert error.value.code == "retrieval_response_invalid"
