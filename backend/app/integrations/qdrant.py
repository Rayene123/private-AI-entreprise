from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    IntegrationConfigurationError,
    IntegrationUnavailableError,
    ValidationError,
)


class QdrantVectorStore:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        settings = settings or get_settings()
        if not settings.qdrant_url:
            raise IntegrationConfigurationError(
                "Qdrant integration is not configured."
            )
        if settings.embedding_dimension <= 0:
            raise ValidationError(
                "The configured vector dimension is invalid.",
                code="invalid_embedding_configuration",
            )
        self.collection = settings.qdrant_collection_name
        self.dimension = settings.embedding_dimension
        self._base_url = settings.qdrant_url.rstrip("/")
        self._api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        self._client = client
        self._timeout = settings.qdrant_timeout_seconds

    def ensure_collection(self) -> None:
        try:
            response = self._request("GET", f"/collections/{self.collection}")
            if response.status_code == 404:
                created = self._request(
                    "PUT",
                    f"/collections/{self.collection}",
                    json={
                        "vectors": {
                            "size": self.dimension,
                            "distance": "Cosine",
                        }
                    },
                )
                created.raise_for_status()
                self._ensure_payload_indexes()
                return
            response.raise_for_status()
            vectors = (
                response.json()
                .get("result", {})
                .get("config", {})
                .get("params", {})
                .get("vectors", {})
            )
            size = vectors.get("size") if isinstance(vectors, dict) else None
            distance = vectors.get("distance") if isinstance(vectors, dict) else None
            if size != self.dimension or str(distance).lower() != "cosine":
                raise ValidationError(
                    "The existing Qdrant collection configuration is incompatible.",
                    code="qdrant_collection_mismatch",
                )
            self._ensure_payload_indexes()
        except ValidationError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise IntegrationUnavailableError(
                "Qdrant is unavailable.",
                code="qdrant_unavailable",
            ) from exc

    def _ensure_payload_indexes(self) -> None:
        for field_name in ("document_id", "source_hash"):
            response = self._request(
                "PUT",
                f"/collections/{self.collection}/index",
                json={"field_name": field_name, "field_schema": "keyword"},
            )
            response.raise_for_status()

    def upsert(self, points: Iterable[dict[str, Any]]) -> None:
        points = list(points)
        if not points:
            return
        for point in points:
            vector = point.get("vector")
            if not isinstance(vector, list) or len(vector) != self.dimension:
                raise ValidationError(
                    "A vector does not match the configured dimension.",
                    code="embedding_dimension_mismatch",
                )
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
                raise ValidationError(
                    "A vector contains invalid values.",
                    code="invalid_embedding_vector",
                )
        try:
            response = self._request(
                "PUT",
                f"/collections/{self.collection}/points",
                json={"wait": True, "points": points},
            )
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise IntegrationUnavailableError(
                "Qdrant indexing failed.",
                code="qdrant_upsert_failed",
            ) from exc

    def delete_document(self, document_id: UUID) -> None:
        try:
            response = self._request(
                "POST",
                f"/collections/{self.collection}/points/delete",
                json={
                    "wait": True,
                    "filter": {
                        "must": [
                            {
                                "key": "document_id",
                                "match": {"value": str(document_id)},
                            }
                        ]
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IntegrationUnavailableError(
                "Qdrant cleanup failed.",
                code="qdrant_delete_failed",
            ) from exc

    def delete_obsolete(self, document_id: UUID, source_hash: str) -> None:
        try:
            response = self._request(
                "POST",
                f"/collections/{self.collection}/points/delete",
                json={
                    "wait": True,
                    "filter": {
                        "must": [
                            {"key": "document_id", "match": {"value": str(document_id)}}
                        ],
                        "must_not": [
                            {"key": "source_hash", "match": {"value": source_hash}}
                        ],
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IntegrationUnavailableError(
                "Qdrant cleanup failed.",
                code="qdrant_delete_failed",
            ) from exc

    def search(
        self,
        vector: list[float],
        *,
        top_k: int,
        min_score: float,
        document_ids: list[UUID],
    ) -> list[dict[str, Any]]:
        if not document_ids:
            return []
        if len(vector) != self.dimension or any(
            not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in vector
        ):
            raise ValidationError(
                "The query embedding does not match the configured dimension.",
                code="embedding_dimension_mismatch",
            )
        try:
            response = self._request(
                "POST",
                f"/collections/{self.collection}/points/search",
                json={
                    "vector": vector,
                    "limit": top_k,
                    "score_threshold": min_score,
                    "with_payload": True,
                    "filter": {
                        "should": [
                            {
                                "key": "document_id",
                                "match": {"value": str(document_id)},
                            }
                            for document_id in document_ids
                        ],
                    },
                },
            )
            response.raise_for_status()
            results = response.json().get("result", [])
            if not isinstance(results, list):
                raise ValueError("Qdrant returned an invalid search result.")
            return [result for result in results if isinstance(result, dict)]
        except ValidationError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise IntegrationUnavailableError(
                "Semantic retrieval is unavailable.",
                code="qdrant_search_failed",
            ) from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        if self._api_key:
            headers["api-key"] = self._api_key
        client = self._client or httpx.Client(timeout=self._timeout, headers=headers)
        owns_client = self._client is None
        try:
            return client.request(
                method,
                f"{self._base_url}{path}",
                headers=headers if self._client else None,
                **kwargs,
            )
        finally:
            if owns_client:
                client.close()
