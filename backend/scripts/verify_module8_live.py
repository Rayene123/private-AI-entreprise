"""Disposable live verification for real Ollama embeddings and Qdrant indexing."""

from __future__ import annotations

import logging
import secrets
import sys
from pathlib import Path
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.integrations.qdrant import QdrantVectorStore
from app.integrations.supabase.client import get_service_supabase_client, get_supabase_client
from app.main import create_app
from app.services.auth_service import get_authentication_service
from app.services.document_service import DocumentService
from app.services.permission_service import AuthorizationService

from verify_module7_live import (
    _assign_role,
    _create_user,
    _create_department,
    _sign_in,
)
from app.schemas.document import DocumentCreate


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = get_settings()
    service_client = get_service_supabase_client(settings)
    auth_client = get_supabase_client(settings)
    auth_admin = service_client.auth.admin
    prefix = f"module8-live-{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)
    users: list[str] = []
    documents: list[str] = []
    objects: list[str] = []
    department_id: str | None = None
    vector_store = None
    checks: list[str] = []

    try:
        manager_id = _create_user(
            auth_admin,
            f"{prefix}-manager@example.invalid",
            password,
            users,
        )
        department_id = _create_department(service_client, prefix)
        _assign_role(service_client, manager_id, "manager")
        manager_token = _sign_in(
            auth_client,
            f"{prefix}-manager@example.invalid",
            password,
        )

        service = DocumentService(
            AuthorizationService(),
            supabase_client=service_client,
        )
        document = service.create_document(
            UUID(manager_id),
            DocumentCreate(
                title="Module 8 synthetic indexing document",
                access_level="department",
                department_id=UUID(department_id),
            ),
        )
        document_id = str(document.id)
        documents.append(document_id)
        uploaded = service.upload_document_file(
            UUID(manager_id),
            document.id,
            filename="module8.txt",
            content_type="text/plain",
            content=(
                "Module 8 synthetic content.\n\n"
                "This document is disposable and used only for indexing."
            ).encode(),
        )
        if not uploaded.storage_path:
            raise RuntimeError("The live upload did not produce a storage path.")
        objects.append(uploaded.storage_path)
        checks.append("application-upload")

        app = create_app()
        client = TestClient(app)
        response = client.post(
            f"/documents/{document_id}/ingest",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        _assert_success(response)
        first = response.json()
        assert first["indexing_status"] == "indexed"
        assert first["indexed_count"] == first["chunk_count"] > 0
        assert first["embedding_model"] == settings.embedding_model
        checks.append("real-embedding-indexing")

        vector_store = QdrantVectorStore(settings)
        vector_store.ensure_collection()
        checks.append("collection-configuration")
        count_after_first = _count_document_points(settings, document_id)
        assert count_after_first == first["indexed_count"]

        response = client.post(
            f"/documents/{document_id}/ingest",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        _assert_success(response)
        second = response.json()
        count_after_second = _count_document_points(settings, document_id)
        assert second["indexed_count"] == first["indexed_count"]
        assert count_after_second == count_after_first
        checks.append("idempotent-reindex")

        vector_store.delete_document(document.id)
        assert _count_document_points(settings, document_id) == 0
        checks.append("vector-cleanup")
        print(f"PASS: {len(checks)} live Module 8 checks")
        return 0
    finally:
        if vector_store and documents:
            for document_id in documents:
                try:
                    vector_store.delete_document(UUID(document_id))
                except Exception:
                    pass
        bucket = service_client.storage.from_(settings.document_storage_bucket)
        for path in objects:
            bucket.remove([path])
        for document_id in documents:
            service_client.table("documents").delete().eq("id", document_id).execute()
        if department_id:
            service_client.table("departments").delete().eq("id", department_id).execute()
        for user_id in users:
            auth_admin.delete_user(user_id)


def _assert_success(response) -> None:
    if response.status_code != 200:
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise RuntimeError(
            "Live Module 8 indexing failed: "
            f"http={response.status_code}, code={error.get('code', 'unknown')}"
        )


def _count_document_points(settings, document_id: str) -> int:
    headers = (
        {"api-key": settings.qdrant_api_key.get_secret_value()}
        if settings.qdrant_api_key
        else {}
    )
    response = httpx.post(
        f"{settings.qdrant_url.rstrip('/')}/collections/"
        f"{settings.qdrant_collection_name}/points/count",
        headers=headers,
        json={
            "exact": True,
            "filter": {
                "must": [
                    {"key": "document_id", "match": {"value": document_id}}
                ]
            },
        },
        timeout=settings.qdrant_timeout_seconds,
    )
    response.raise_for_status()
    return int(response.json()["result"]["count"])


if __name__ == "__main__":
    raise SystemExit(main())
