"""Disposable live verification for Module 9 semantic retrieval."""

from __future__ import annotations

import logging
import secrets
import sys
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.integrations.qdrant import QdrantVectorStore
from app.integrations.supabase.client import (
    get_service_supabase_client,
    get_supabase_client,
)
from app.main import create_app
from app.schemas.document import DocumentCreate
from app.services.auth_service import AuthenticationService
from app.services.document_service import DocumentService
from app.services.permission_service import AuthorizationService
from scripts.verify_module7_live import (
    _assign_department,
    _assign_role,
    _cleanup,
    _create_and_upload,
    _create_department,
    _create_user,
    _grant_access,
    _sign_in,
)


TXT_MIME = "text/plain"
BUCKET = "enterprise-documents"


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = get_settings()
    service_client = get_service_supabase_client(settings)
    user_client = get_supabase_client(settings)
    _verify_connectivity(service_client)
    auth_admin = service_client.auth.admin
    prefix = f"module9-live-{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)
    created_users: list[str] = []
    created_documents: list[str] = []
    created_objects: list[str] = []
    explicit_grants: list[tuple[str, str]] = []
    department_id: str | None = None
    indexed_ids: list[UUID] = []
    checks: list[str] = []

    try:
        manager_id = _create_user(
            auth_admin,
            f"{prefix}-manager@example.invalid",
            password,
            created_users,
        )
        employee_id = _create_user(
            auth_admin,
            f"{prefix}-employee@example.invalid",
            password,
            created_users,
        )
        outsider_id = _create_user(
            auth_admin,
            f"{prefix}-outsider@example.invalid",
            password,
            created_users,
        )
        department_id = _create_department(service_client, prefix)
        _assign_department(service_client, manager_id, department_id)
        _assign_department(service_client, employee_id, department_id)
        _assign_role(service_client, manager_id, "manager")
        _assign_role(service_client, manager_id, "admin")

        manager_token = _sign_in(
            user_client,
            f"{prefix}-manager@example.invalid",
            password,
        )
        employee_token = _sign_in(
            user_client,
            f"{prefix}-employee@example.invalid",
            password,
        )
        outsider_token = _sign_in(
            user_client,
            f"{prefix}-outsider@example.invalid",
            password,
        )
        client = TestClient(create_app())
        manager_service = DocumentService(
            AuthorizationService(),
            supabase_client=service_client,
        )
        manager_uuid = UUID(manager_id)

        private_id = _create_document(
            manager_service,
            manager_uuid,
            "Private retrieval sentinel",
            "private.txt",
            b"module nine private retrieval sentinel",
            created_documents,
            created_objects,
            access_level="private",
        )
        department_doc_id = _create_document(
            manager_service,
            manager_uuid,
            "Department retrieval sentinel",
            "department.txt",
            b"module nine department retrieval sentinel",
            created_documents,
            created_objects,
            access_level="department",
            department_id=department_id,
        )
        shared_id = _create_document(
            manager_service,
            manager_uuid,
            "Shared retrieval sentinel",
            "shared.txt",
            b"module nine explicitly shared retrieval sentinel",
            created_documents,
            created_objects,
            access_level="private",
        )
        organization_id = _create_document(
            manager_service,
            manager_uuid,
            "Organization retrieval sentinel",
            "organization.txt",
            b"module nine organization retrieval sentinel",
            created_documents,
            created_objects,
            access_level="organization",
        )
        archived_id = _create_document(
            manager_service,
            manager_uuid,
            "Archived retrieval sentinel",
            "archived.txt",
            b"module nine archived retrieval sentinel",
            created_documents,
            created_objects,
            access_level="organization",
        )
        _grant_access(service_client, shared_id, employee_id)
        explicit_grants.append((shared_id, employee_id))

        for document_id in (
            private_id,
            department_doc_id,
            shared_id,
            organization_id,
            archived_id,
        ):
            _ingest(client, manager_token, document_id)
            indexed_ids.append(UUID(document_id))
        checks.append("real indexing and query embedding")

        manager_result = _retrieve(
            client,
            manager_token,
            "module nine private retrieval sentinel",
        )
        _require_document(manager_result, private_id)
        checks.append("private owner retrieval")

        employee_department = _retrieve(
            client,
            employee_token,
            "module nine department retrieval sentinel",
        )
        _require_document(employee_department, department_doc_id)
        checks.append("department retrieval")

        employee_shared = _retrieve(
            client,
            employee_token,
            "module nine explicitly shared retrieval sentinel",
        )
        _require_document(employee_shared, shared_id)
        checks.append("explicit share retrieval")

        employee_private = _retrieve(
            client,
            employee_token,
            "module nine private retrieval sentinel",
        )
        _forbid_document(employee_private, private_id)
        checks.append("private isolation")

        outsider_department = _retrieve(
            client,
            outsider_token,
            "module nine department retrieval sentinel",
        )
        _forbid_document(outsider_department, department_doc_id)
        checks.append("cross-department isolation")

        outsider_organization = _retrieve(
            client,
            outsider_token,
            "module nine organization retrieval sentinel",
        )
        _require_document(outsider_organization, organization_id)
        checks.append("organization retrieval")

        manager_service.delete_document(manager_uuid, UUID(archived_id))
        archived_result = _retrieve(
            client,
            manager_token,
            "module nine archived retrieval sentinel",
        )
        _forbid_document(archived_result, archived_id)
        checks.append("archived exclusion")

        print(f"PASS: {len(checks)} live Module 9 checks")
        return 0
    finally:
        try:
            vector_store = QdrantVectorStore(settings)
            for document_id in indexed_ids:
                vector_store.delete_document(document_id)
        finally:
            _cleanup(
                service_client,
                auth_admin,
                created_documents,
                created_objects,
                explicit_grants,
                department_id,
                created_users,
            )


def _verify_connectivity(service_client) -> None:
    response = service_client.table("roles").select("name").limit(1).execute()
    rows = response.data if hasattr(response, "data") else response.get("data")
    if not isinstance(rows, list):
        raise RuntimeError("Supabase service connectivity failed.")


def _create_document(
    service: DocumentService,
    owner_id: UUID,
    title: str,
    filename: str,
    content: bytes,
    documents: list[str],
    objects: list[str],
    *,
    access_level: str,
    department_id: str | None = None,
) -> str:
    return _create_and_upload(
        service,
        owner_id,
        title,
        filename,
        TXT_MIME,
        content,
        documents,
        objects,
        access_level=access_level,
        department_id=department_id,
    )


def _ingest(client: TestClient, token: str, document_id: str) -> dict:
    response = client.post(
        f"/documents/{document_id}/ingest",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Live indexing failed with HTTP {response.status_code}.")
    return response.json()


def _retrieve(client: TestClient, token: str, query: str) -> dict:
    response = client.post(
        "/chat/retrieve",
        json={"query": query, "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise RuntimeError(
            "Live retrieval failed: "
            f"http={response.status_code}, code={error.get('code', 'unknown')}."
        )
    return response.json()


def _require_document(result: dict, document_id: str) -> None:
    if not any(item["document_id"] == document_id for item in result["results"]):
        raise RuntimeError("Expected authorized document was not retrieved.")


def _forbid_document(result: dict, document_id: str) -> None:
    if any(item["document_id"] == document_id for item in result["results"]):
        raise RuntimeError("Unauthorized or archived document was retrieved.")


if __name__ == "__main__":
    raise SystemExit(main())
