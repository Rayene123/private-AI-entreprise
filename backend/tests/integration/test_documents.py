from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.documents import get_document_service
from app.core.exceptions import AuthorizationError
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.auth_service import get_authentication_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEPARTMENT_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
NOW = datetime(2026, 9, 23, tzinfo=UTC)


def response_document(**overrides) -> DocumentResponse:
    data = {
        "id": DOCUMENT_ID,
        "owner_id": USER_ID,
        "department_id": DEPARTMENT_ID,
        "title": "Policy",
        "description": "Internal policy",
        "original_filename": "policy.pdf",
        "storage_path": None,
        "mime_type": "application/pdf",
        "file_size_bytes": 100,
        "status": "active",
        "access_level": "department",
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return DocumentResponse(**data)


class SuccessfulAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=USER_ID,
            email="employee@example.com",
            role="authenticated",
            claims={"sub": str(USER_ID), "role": "authenticated"},
        )


class FakeDocumentService:
    def __init__(self, *, fail_with: AuthorizationError | None = None) -> None:
        self.fail_with = fail_with
        self.created_owner_id: UUID | None = None
        self.deleted_document_id: UUID | None = None

    def create_document(
        self,
        user_id: UUID,
        document_create: DocumentCreate,
    ) -> DocumentResponse:
        if self.fail_with:
            raise self.fail_with
        self.created_owner_id = user_id
        return response_document(
            owner_id=user_id,
            title=document_create.title,
            access_level=document_create.access_level,
            department_id=document_create.department_id,
        )

    def list_documents(self, user_id: UUID) -> list[DocumentListItem]:
        if self.fail_with:
            raise self.fail_with
        item = response_document().model_dump()
        item.pop("storage_path")
        return [
            DocumentListItem(**item),
        ]

    def get_document(self, user_id: UUID, document_id: UUID) -> DocumentResponse:
        if self.fail_with:
            raise self.fail_with
        return response_document(id=document_id)

    def update_document(
        self,
        user_id: UUID,
        document_id: UUID,
        document_update: DocumentUpdate,
    ) -> DocumentResponse:
        if self.fail_with:
            raise self.fail_with
        return response_document(
            id=document_id,
            title=document_update.title or "Policy",
        )

    def delete_document(self, user_id: UUID, document_id: UUID) -> None:
        if self.fail_with:
            raise self.fail_with
        self.deleted_document_id = document_id


def build_client(document_service: FakeDocumentService | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = lambda: (
        SuccessfulAuthService()
    )
    if document_service is not None:
        app.dependency_overrides[get_document_service] = lambda: document_service
    return TestClient(app)


def test_get_documents_without_jwt_returns_401() -> None:
    client = build_client(FakeDocumentService())

    response = client.get("/documents")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_get_documents_without_read_permission_returns_403() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to perform this action.",
                code="insufficient_permissions",
            )
        )
    )

    response = client.get(
        "/documents",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_create_document_uses_authenticated_user_as_owner() -> None:
    service = FakeDocumentService()
    client = build_client(service)

    response = client.post(
        "/documents",
        headers={"Authorization": "Bearer verified-token"},
        json={
            "title": "HR Policy",
            "department_id": str(DEPARTMENT_ID),
            "access_level": "department",
            "original_filename": "hr-policy.pdf",
            "mime_type": "application/pdf",
        },
    )

    assert response.status_code == 201
    assert response.json()["owner_id"] == str(USER_ID)
    assert service.created_owner_id == USER_ID


def test_create_document_rejects_owner_spoofing_payload() -> None:
    client = build_client(FakeDocumentService())

    response = client.post(
        "/documents",
        headers={"Authorization": "Bearer verified-token"},
        json={
            "title": "HR Policy",
            "owner_id": "22222222-2222-2222-2222-222222222222",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_patch_document_returns_updated_metadata() -> None:
    client = build_client(FakeDocumentService())

    response = client.patch(
        f"/documents/{DOCUMENT_ID}",
        headers={"Authorization": "Bearer verified-token"},
        json={"title": "Updated Policy"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Policy"
    assert response.json()["owner_id"] == str(USER_ID)


def test_unauthorized_patch_returns_403_without_metadata() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to access this document.",
                code="document_access_denied",
            )
        )
    )

    response = client.patch(
        f"/documents/{DOCUMENT_ID}",
        headers={"Authorization": "Bearer verified-token"},
        json={"title": "Updated Policy"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "document_access_denied"
    assert "Updated Policy" not in response.text


def test_delete_document_returns_204() -> None:
    service = FakeDocumentService()
    client = build_client(service)

    response = client.delete(
        f"/documents/{DOCUMENT_ID}",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 204
    assert service.deleted_document_id == DOCUMENT_ID


def test_document_access_mutation_route_does_not_exist() -> None:
    client = build_client(FakeDocumentService())

    response = client.post(
        "/document_user_access",
        headers={"Authorization": "Bearer verified-token"},
        json={
            "document_id": str(DOCUMENT_ID),
            "user_id": str(USER_ID),
        },
    )

    assert response.status_code == 404
