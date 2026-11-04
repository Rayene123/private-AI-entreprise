from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    IntegrationConfigurationError,
    IntegrationUnavailableError,
    ValidationError,
)


class EmbeddingProvider(Protocol):
    model: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class OllamaEmbeddingProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        settings = settings or get_settings()
        if settings.embedding_provider.lower() != "ollama":
            raise IntegrationConfigurationError(
                "The configured embedding provider is not supported."
            )
        if settings.embedding_dimension <= 0 or settings.embedding_batch_size <= 0:
            raise ValidationError(
                "Embedding configuration is invalid.",
                code="invalid_embedding_configuration",
            )
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size
        self._url = settings.embedding_url.rstrip("/")
        self._client = client
        self._timeout = settings.embedding_timeout_seconds

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValidationError(
                "Embedding input must contain non-empty text.",
                code="invalid_embedding_input",
            )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            try:
                response = self._request(batch)
                batch_vectors = response.get("embeddings")
                if not isinstance(batch_vectors, list):
                    raise ValueError("Ollama returned no embeddings.")
                vectors.extend(batch_vectors)
            except ValidationError:
                raise
            except (httpx.HTTPError, TimeoutError) as exc:
                raise IntegrationUnavailableError(
                    "The embedding provider is unavailable.",
                    code="embedding_provider_unavailable",
                ) from exc
            except Exception as exc:
                raise IntegrationUnavailableError(
                    "The embedding provider returned an invalid response.",
                    code="embedding_response_invalid",
                ) from exc
        if len(vectors) != len(texts):
            raise IntegrationUnavailableError(
                "The embedding provider returned an incomplete response.",
                code="embedding_response_incomplete",
            )
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != self.dimension:
                raise ValidationError(
                    "The embedding dimension does not match configuration.",
                    code="embedding_dimension_mismatch",
                )
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
                raise ValidationError(
                    "The embedding provider returned invalid vector values.",
                    code="invalid_embedding_vector",
                )
        return vectors

    def _request(self, batch: list[str]) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self._timeout)
        owns_client = self._client is None
        try:
            response = client.post(
                f"{self._url}/api/embed",
                json={"model": self.model, "input": batch},
            )
            response.raise_for_status()
            return response.json()
        finally:
            if owns_client:
                client.close()
