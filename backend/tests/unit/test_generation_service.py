import json
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
        self.calls = 0

    def retrieve(self, user_id, query):
        self.calls += 1
        return self.response


class Chat:
    def __init__(self, response):
        self.responses = response if isinstance(response, list) else [response]
        self.response = response
        self.calls = []

    def generate(self, system, user, **kwargs):
        self.calls.append((system, user, kwargs))
        return self.responses.pop(0)


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
    assert service._retrieval.calls == 1
    assert chat.calls == []


def test_supplied_retrieval_is_used_without_retrieving_again() -> None:
    retrieval = Retrieval(
        RetrievalResponse(
            query="q",
            results=[chunk("good", 0.9, "evidence")],
            retrieved_count=1,
        )
    )
    chat = Chat(
        '{"answer":"Supported answer","chunk_ids":["good"],'
        '"has_sufficient_context":true}'
    )
    service = GenerationService(
        retrieval,
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask_with_retrieval(
        USER_ID,
        "q",
        retrieval.response,
    )

    assert response.citations[0].chunk_id == "good"
    assert retrieval.calls == 0


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


@pytest.mark.parametrize(
    "chunk_ids",
    [[], ["fake"], ["fake", "also-fake"]],
)
def test_sufficient_context_requires_a_valid_citation(chunk_ids) -> None:
    response = json.dumps(
        {
            "answer": "Supported answer",
            "chunk_ids": chunk_ids,
            "has_sufficient_context": True,
        }
    )
    chat = Chat([response, response])
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

    with pytest.raises(IntegrationUnavailableError) as raised:
        service.ask(USER_ID, "q")

    assert raised.value.code == "answer_response_invalid"
    assert len(chat.calls) == 2


def test_sufficient_context_accepts_valid_and_ignores_fabricated_citations() -> None:
    chat = Chat(
        '{"answer":"Supported answer","chunk_ids":["good","fake","good2"],'
        '"has_sufficient_context":true}'
    )
    service = GenerationService(
        Retrieval(
            RetrievalResponse(
                query="q",
                results=[
                    chunk("good", 0.9, "evidence"),
                    chunk("good2", 0.8, "more evidence"),
                ],
                retrieved_count=2,
            )
        ),
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask(USER_ID, "q")

    assert [citation.chunk_id for citation in response.citations] == [
        "good",
        "good2",
    ]


def test_insufficient_context_allows_empty_citations() -> None:
    chat = Chat(
        '{"answer":"Not enough information","chunk_ids":[],'
        '"has_sufficient_context":false}'
    )
    service = GenerationService(
        Retrieval(
            RetrievalResponse(
                query="q",
                results=[chunk("good", 0.9, "weak evidence")],
                retrieved_count=1,
            )
        ),
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask(USER_ID, "q")

    assert response.has_sufficient_context is False
    assert response.citations == []


def test_missing_citation_is_repaired_once_with_same_retrieval() -> None:
    retrieval = Retrieval(
        RetrievalResponse(
            query="q",
            results=[chunk("good", 0.9, "evidence")],
            retrieved_count=1,
        )
    )
    chat = Chat(
        [
            '{"answer":"Supported answer","chunk_ids":[],"has_sufficient_context":true}',
            '{"answer":"Supported answer","chunk_ids":["good"],'
            '"has_sufficient_context":true}',
        ]
    )
    service = GenerationService(
        retrieval,
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    response = service.ask(USER_ID, "q")

    assert [citation.chunk_id for citation in response.citations] == ["good"]
    assert retrieval.calls == 1
    assert len(chat.calls) == 2
    assert "at least one exact supporting chunk_id" in chat.calls[1][1]


def test_invalid_response_is_retried_once_and_valid_response_is_parsed() -> None:
    chat = Chat(
        [
            '{"answer":"incomplete","chunk_ids":[]}',
            '{"answer":"Supported answer","chunk_ids":["good"],'
            '"has_sufficient_context":true}',
        ]
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
    assert len(chat.calls) == 2
    assert "REPAIR" in chat.calls[1][1]


@pytest.mark.parametrize(
    "response",
    [
        '{"answer":"missing ids","has_sufficient_context":true}',
        '{"answer":"missing flag","chunk_ids":[]}',
        '{"answer":7,"chunk_ids":[],"has_sufficient_context":true}',
        '{"answer":"alternative","sources":[],"source_context":"x"}',
    ],
)
def test_invalid_structured_responses_are_rejected_after_one_retry(response) -> None:
    chat = Chat([response, response])
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

    with pytest.raises(IntegrationUnavailableError) as raised:
        service.ask(USER_ID, "q")

    assert raised.value.code == "answer_response_invalid"
    assert len(chat.calls) == 2


def test_provider_failure_is_not_retried() -> None:
    class FailingChat(Chat):
        def generate(self, system, user, **kwargs):
            self.calls.append((system, user, kwargs))
            raise IntegrationUnavailableError(code="chat_provider_unavailable")

    chat = FailingChat("")
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

    with pytest.raises(IntegrationUnavailableError) as raised:
        service.ask(USER_ID, "q")

    assert raised.value.code == "chat_provider_unavailable"
    assert len(chat.calls) == 1


def test_malformed_model_json_fails_safely() -> None:
    chat = Chat(["not-json", "not-json"])
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

    with pytest.raises(IntegrationUnavailableError) as raised:
        service.ask(USER_ID, "q")
    assert raised.value.code == "answer_response_invalid"
    assert len(chat.calls) == 2
    assert service.last_diagnostics.attempts[0]["validation_reason"] == (
        "malformed_json"
    )
    assert service.last_diagnostics.attempts[1]["validation_reason"] == (
        "malformed_json"
    )


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (
            '{"answer":"x","chunk_ids":[]}',
            "missing_required_fields",
        ),
        (
            '{"answer":"x","chunk_ids":[],"has_sufficient_context":false,'
            '"extra":1}',
            "unexpected_fields",
        ),
        (
            '{"answer":7,"chunk_ids":[],"has_sufficient_context":false}',
            "invalid_field_types",
        ),
        (
            '{"answer":"x","chunk_ids":[],"has_sufficient_context":true}',
            "missing_citation",
        ),
        (
            '{"answer":"x","chunk_ids":["fake"],"has_sufficient_context":true}',
            "no_valid_allowlisted_citations",
        ),
    ],
)
def test_validation_diagnostics_are_safe_and_stable(response, reason) -> None:
    chat = Chat([response, response])
    service = GenerationService(
        Retrieval(
            RetrievalResponse(
                query="q",
                results=[chunk("good", 0.9, "private evidence")],
                retrieved_count=1,
            )
        ),
        chat_provider=chat,
        settings=Settings(generation_max_context_chars=1000),
    )

    with pytest.raises(IntegrationUnavailableError):
        service.ask(USER_ID, "q")

    assert [
        attempt["validation_reason"]
        for attempt in service.last_diagnostics.attempts
    ] == [reason, reason]
    assert "private evidence" not in str(service.last_diagnostics)
    assert "fake" not in str(service.last_diagnostics)
