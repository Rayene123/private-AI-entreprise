from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.documents import get_document_service
from app.core.exceptions import (
    AppException,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.document import (
    DocumentCreate,
    DocumentFile,
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
        self.uploaded_by_user_id: UUID | None = None
        self.uploaded_document_id: UUID | None = None
        self.uploaded_content: bytes | None = None
        self.downloaded_by_user_id: UUID | None = None
        self.downloaded_document_id: UUID | None = None
        self.upload_count = 0

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

    def upload_document_file(
        self,
        user_id: UUID,
        document_id: UUID,
        *,
        filename: str | None,
        content_type: str | None,
        content: bytes,
    ) -> DocumentResponse:
        if self.fail_with:
            raise self.fail_with
        self.upload_count += 1
        self.uploaded_by_user_id = user_id
        self.uploaded_document_id = document_id
        self.uploaded_content = content
        return response_document(
            id=document_id,
            owner_id=USER_ID,
            storage_path=f"documents/{document_id}/generated-object-{self.upload_count}",
            original_filename=filename,
            mime_type=content_type,
            file_size_bytes=len(content),
        )

    def download_document_file(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> DocumentFile:
        if self.fail_with:
            raise self.fail_with
        self.downloaded_by_user_id = user_id
        self.downloaded_document_id = document_id
        return DocumentFile(
            content=b"%PDF-1.4\n%mock pdf content",
            mime_type="application/pdf",
            filename="policy.pdf",
        )


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


# --------------------------------------------------------------------------
# Module 6: authentication
# --------------------------------------------------------------------------


def test_upload_document_file_without_jwt_returns_401() -> None:
    client = build_client(FakeDocumentService())

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_download_document_file_without_jwt_returns_401() -> None:
    client = build_client(FakeDocumentService())

    response = client.get(f"/documents/{DOCUMENT_ID}/file")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


# --------------------------------------------------------------------------
# Module 6: RBAC
# --------------------------------------------------------------------------


def test_upload_without_documents_update_permission_returns_403() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to perform this action.",
                code="insufficient_permissions",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_download_still_requires_documents_read_permission() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to perform this action.",
                code="insufficient_permissions",
            )
        )
    )

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


# --------------------------------------------------------------------------
# Module 6: document-level authorization (reuses Module 5 behavior)
# --------------------------------------------------------------------------


def test_upload_denied_when_document_access_denied() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to access this document.",
                code="document_access_denied",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "document_access_denied"


def test_download_denied_when_document_access_denied() -> None:
    # Covers organization/department/private/explicit-access boundaries,
    # which are exercised in depth in the DocumentService unit tests; here
    # we confirm the endpoint surfaces that same authorization decision.
    client = build_client(
        FakeDocumentService(
            fail_with=AuthorizationError(
                "You do not have permission to access this document.",
                code="document_access_denied",
            )
        )
    )

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "document_access_denied"


def test_authorized_download_returns_file_content() -> None:
    service = FakeDocumentService()
    client = build_client(service)

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4\n%mock pdf content"
    assert response.headers["content-type"] == "application/pdf"
    assert "policy.pdf" in response.headers["content-disposition"]
    assert service.downloaded_by_user_id == USER_ID
    assert service.downloaded_document_id == DOCUMENT_ID


# --------------------------------------------------------------------------
# Module 6: ownership/spoofing
# --------------------------------------------------------------------------


def test_upload_uses_authenticated_user_not_client_supplied_owner() -> None:
    # There is no owner_id field on the upload endpoint at all; the
    # authenticated user from the JWT is always what's passed through,
    # regardless of anything else the client sends.
    service = FakeDocumentService()
    client = build_client(service)

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"owner_id": "22222222-2222-2222-2222-222222222222"},
    )

    assert response.status_code == 200
    assert response.json()["owner_id"] == str(USER_ID)
    assert service.uploaded_by_user_id == USER_ID


def test_upload_document_id_comes_only_from_url_path() -> None:
    # The client cannot redirect an upload to a different document by
    # supplying a document_id anywhere in the form body; only the URL path
    # segment (an authorized, server-resolved document) is used.
    service = FakeDocumentService()
    client = build_client(service)
    spoofed_id = "99999999-9999-9999-9999-999999999999"

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"document_id": spoofed_id, "storage_path": "documents/evil/x.pdf"},
    )

    assert response.status_code == 200
    assert service.uploaded_document_id == DOCUMENT_ID
    assert response.json()["id"] == str(DOCUMENT_ID)
    assert response.json()["storage_path"] != "documents/evil/x.pdf"


def test_download_document_id_comes_only_from_url_path() -> None:
    service = FakeDocumentService()
    client = build_client(service)
    spoofed_id = "99999999-9999-9999-9999-999999999999"

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        params={"document_id": spoofed_id},
    )

    assert response.status_code == 200
    assert service.downloaded_document_id == DOCUMENT_ID


# --------------------------------------------------------------------------
# Module 6: validation
# --------------------------------------------------------------------------


def test_upload_unsupported_mime_type_returns_400() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file type is not supported.",
                code="unsupported_mime_type",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("script.sh", b"#!/bin/sh", "application/x-sh")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_mime_type"


def test_upload_empty_file_returns_400() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file is empty.",
                code="empty_file",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_oversized_file_returns_400() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file exceeds the maximum allowed size.",
                code="file_too_large",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.pdf", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_unsafe_filename_returns_400() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The filename is not allowed.",
                code="unsafe_filename",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("../../etc/passwd", b"%PDF-1.4 mock", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsafe_filename"


def test_upload_signature_mismatch_returns_400() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file content signature does not match its declared type.",
                code="file_signature_mismatch",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_signature_mismatch"


# --------------------------------------------------------------------------
# Module 6: replacement
# --------------------------------------------------------------------------


def test_replacement_upload_points_metadata_at_new_object() -> None:
    service = FakeDocumentService()
    client = build_client(service)

    first = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy-v1.pdf", b"%PDF-1.4 v1", "application/pdf")},
    )
    second = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy-v2.pdf", b"%PDF-1.4 v2", "application/pdf")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["storage_path"] != second.json()["storage_path"]
    assert second.json()["original_filename"] == "policy-v2.pdf"


def test_failed_replacement_upload_returns_error_without_metadata_change() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file type is not supported.",
                code="unsupported_mime_type",
            )
        )
    )

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={"file": ("policy.exe", b"MZ", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_mime_type"


# --------------------------------------------------------------------------
# Module 6: archive
# --------------------------------------------------------------------------


def test_archived_document_file_download_denied() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ResourceNotFoundError(
                "Document was not found.",
                code="document_not_found",
            )
        )
    )

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


# --------------------------------------------------------------------------
# Module 6: secret-leak protection
# --------------------------------------------------------------------------


def test_storage_error_response_does_not_leak_provider_details() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=AppException(
                "The document could not be retrieved.",
                code="storage_download_failed",
            )
        )
    )

    response = client.get(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
    )

    body_text = response.text.lower()
    assert "supabase" not in body_text
    assert "bucket" not in body_text
    assert "eyj" not in body_text  # no JWT fragment
    assert "signed" not in body_text
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "storage_download_failed"


def test_upload_error_response_does_not_leak_file_contents() -> None:
    client = build_client(
        FakeDocumentService(
            fail_with=ValidationError(
                "The uploaded file content signature does not match its declared type.",
                code="file_signature_mismatch",
            )
        )
    )
    secret_marker = "SUPER-SECRET-FILE-BYTES"

    response = client.post(
        f"/documents/{DOCUMENT_ID}/file",
        headers={"Authorization": "Bearer verified-token"},
        files={
            "file": ("fake.pdf", secret_marker.encode(), "application/pdf"),
        },
    )

    assert response.status_code == 400
    assert secret_marker not in response.text