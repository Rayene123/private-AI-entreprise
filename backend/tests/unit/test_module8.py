from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import IntegrationUnavailableError, ValidationError
from app.integrations.ollama import OllamaEmbeddingProvider
from app.integrations.qdrant import QdrantVectorStore


def settings(**overrides) -> Settings:
    values = {
        "embedding_model": "test-embed",
        "embedding_dimension": 3,
        "embedding_batch_size": 2,
        "embedding_url": "http://embedding.test",
        "qdrant_url": "http://qdrant.test",
        "qdrant_collection_name": "test_collection",
    }
    values.update(overrides)
    return Settings(**values)


class EmbeddingClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def post(self, url, json):
        self.calls.append(json)
        return httpx.Response(
            200,
            json=self.response,
            request=httpx.Request("POST", url),
        )


def test_ollama_embeddings_batch_and_validate_dimensions() -> None:
    client = EmbeddingClient({"embeddings": [[1.0, 2.0, 3.0]] * 2})
    provider = OllamaEmbeddingProvider(settings(), client=client)

    vectors = provider.embed(["one", "two"])

    assert vectors == [[1.0, 2.0, 3.0]] * 2
    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "test-embed"


def test_ollama_rejects_empty_input_and_invalid_vectors() -> None:
    provider = OllamaEmbeddingProvider(settings(), client=EmbeddingClient({}))
    with pytest.raises(ValidationError) as empty:
        provider.embed([""])
    assert empty.value.code == "invalid_embedding_input"

    invalid = OllamaEmbeddingProvider(
        settings(),
        client=EmbeddingClient({"embeddings": [[1.0, 2.0]]}),
    )
    with pytest.raises(ValidationError) as dimension:
        invalid.embed(["text"])
    assert dimension.value.code == "embedding_dimension_mismatch"


def test_ollama_provider_failure_is_safe() -> None:
    class FailingClient:
        def post(self, url, json):
            raise httpx.TimeoutException("timeout")

    with pytest.raises(IntegrationUnavailableError) as error:
        OllamaEmbeddingProvider(settings(), client=FailingClient()).embed(["text"])
    assert error.value.code == "embedding_provider_unavailable"


class QdrantClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(
        status,
        json=body,
        request=httpx.Request("GET", "http://qdrant.test"),
    )


def test_qdrant_creates_missing_collection_and_upserts_points() -> None:
    client = QdrantClient(
        [
            response(404, {}),
            response(200, {"result": {"status": "ok"}}),
            response(200, {"result": {"status": "ok"}}),
            response(200, {"result": {"status": "ok"}}),
            response(200, {"result": {"status": "ok"}}),
        ]
    )
    store = QdrantVectorStore(settings(), client=client)

    store.ensure_collection()
    store.upsert([{"id": str(uuid4()), "vector": [1.0, 2.0, 3.0], "payload": {}}])

    assert client.calls[0][0] == "GET"
    assert client.calls[1][0] == "PUT"
    assert client.calls[2][0] == "PUT"


def test_qdrant_rejects_incompatible_collection() -> None:
    client = QdrantClient(
        [
            response(
                200,
                {
                    "result": {
                        "config": {
                            "params": {
                                "vectors": {"size": 99, "distance": "Cosine"}
                            }
                        }
                    }
                },
            ),
        ]
    )
    with pytest.raises(ValidationError) as error:
        QdrantVectorStore(settings(), client=client).ensure_collection()
    assert error.value.code == "qdrant_collection_mismatch"
