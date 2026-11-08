from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.exceptions import IntegrationUnavailableError
from app.schemas.retrieval import (
    RetrievedChunk,
    RetrievedChunkMetadata,
    RetrievalResponse,
)
from app.services.generation_service import ContextBuilder, GenerationService

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def chunk(chunk_id: str, score: float, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=DOCUMENT_ID,
        chunk_id=chunk_id,
        content=content,
        score=score,
        metadata=RetrievedChunkMetadata(
            source_filename="policy.pdf",
            page_number=4,
            chunk_index=2,
        ),
    )


class Retrieval:
    def __init__(self, response):
        self.response = response

    def retrieve(self, user_id, query):
        return self.response


class Chat:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system, user):
        self.calls.append((system, user))
        return self.response


def test_context_is_bounded_and_deterministic() -> None:
    builder = ContextBuilder(250)
    result = builder.build(
        [chunk("low", 0.1, "low"), chunk("high", 0.9, "high")]
    )
    assert "chunk_id=high" in result
    assert "chunk_id=low" not in result


def test_empty_retrieval_never_calls_chat() -> None:
    chat = Chat("")
    service = GenerationService(
        Retrieval(RetrievalResponse(query="q", results=[], retrieved_count=0)),
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask(USER_ID, "q")

    assert response.has_sufficient_context is False
    assert chat.calls == []


def test_citations_are_server_allowlisted_and_deduplicated() -> None:
    chat = Chat(
        '{"answer":"Supported answer","chunk_ids":["good","fake","good"],'
        '"has_sufficient_context":true}'
    )
    service = GenerationService(
        Retrieval(
            RetrievalResponse(
                query="q",
                results=[chunk("good", 0.9, "evidence")],
                retrieved_count=1,
            )
        ),
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask(USER_ID, "q")

    assert response.answer == "Supported answer"
    assert [citation.chunk_id for citation in response.citations] == ["good"]
    assert response.citations[0].document_id == DOCUMENT_ID


def test_malformed_model_json_fails_safely() -> None:
    service = GenerationService(
        Retrieval(
            RetrievalResponse(
                query="q",
                results=[chunk("good", 0.9, "evidence")],
                retrieved_count=1,
            )
        ),
        chat_provider=Chat("not-json"),
        settings=Settings(generation_max_context_chars=1000),
    )

    with pytest.raises(IntegrationUnavailableError) as raised:
        service.ask(USER_ID, "q")
    assert raised.value.code == "answer_response_invalid"
