from __future__ import annotations

from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.documents import get_document_service
from app.core.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.document import DocumentFile
from app.services.auth_service import get_authentication_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

PDF_MIME = "application/pdf"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class SuccessfulAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=USER_ID,
            email="employee@example.com",
            role="authenticated",
            claims={"sub": str(USER_ID), "role": "authenticated"},
        )


class IngestionDocumentService:
    def __init__(
        self,
        document_file: DocumentFile | None = None,
        error: Exception | None = None,
    ) -> None:
        self.document_file = document_file
        self.error = error
        self.download_calls = 0

    def download_document_file(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> DocumentFile:
        if self.error is not None:
            raise self.error
        self.download_calls += 1
        assert self.document_file is not None
        return self.document_file


def build_client(service: IngestionDocumentService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = (
        lambda: SuccessfulAuthService()
    )
    app.dependency_overrides[get_document_service] = lambda: service
    return TestClient(app, headers={"Authorization": "Bearer test-token"})


def make_pdf() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length 50 >>\nstream\nBT /F1 12 Tf 50 200 Td (PDF policy text) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def make_docx() -> bytes:
    from docx import Document

    document = Document()
    document.add_heading("DOCX Policy", level=1)
    document.add_paragraph("DOCX policy text")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Role"
    table.cell(0, 1).text = "Access"
    table.cell(1, 0).text = "Employee"
    table.cell(1, 1).text = "Standard"
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def file_for(content: bytes, mime_type: str, filename: str) -> DocumentFile:
    return DocumentFile(content=content, mime_type=mime_type, filename=filename)


def test_authorized_employee_ingestion_returns_structured_markdown_and_chunks() -> None:
    service = IngestionDocumentService(
        file_for(b"Employee policy\r\n\r\nRead carefully.", "text/plain", "policy.txt")
    )

    response = build_client(service).post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == str(DOCUMENT_ID)
    assert body["file_type"] == "text/plain"
    assert body["markdown"] == "Employee policy\n\nRead carefully."
    assert body["chunk_count"] == 1
    assert body["chunks"][0]["document_id"] == str(DOCUMENT_ID)
    assert body["chunks"][0]["source_hash"]
    assert body["chunks"][0]["chunk_id"]
    assert service.download_calls == 1


@pytest.mark.parametrize(
    ("description", "error", "expected_status", "expected_code"),
    [
        (
            "department access",
            None,
            200,
            None,
        ),
        (
            "private unauthorized access",
            AuthorizationError("denied", code="document_access_denied"),
            403,
            "document_access_denied",
        ),
        (
            "department unauthorized access",
            AuthorizationError("denied", code="document_access_denied"),
            403,
            "document_access_denied",
        ),
        (
            "explicit share revoked",
            AuthorizationError("denied", code="document_access_denied"),
            403,
            "document_access_denied",
        ),
        (
            "archived document",
            ResourceNotFoundError("missing", code="document_not_found"),
            404,
            "document_not_found",
        ),
        (
            "nonexistent document",
            ResourceNotFoundError("missing", code="document_not_found"),
            404,
            "document_not_found",
        ),
        (
            "missing Storage object",
            ResourceNotFoundError("missing", code="document_file_not_found"),
            404,
            "document_file_not_found",
        ),
        (
            "unsupported file type",
            ValidationError("unsupported", code="unsupported_document_type"),
            400,
            "unsupported_document_type",
        ),
    ],
)
def test_authorization_and_safe_error_scenarios(
    description: str,
    error: Exception | None,
    expected_status: int,
    expected_code: str | None,
) -> None:
    del description
    service = IngestionDocumentService(
        file_for(b"content", "text/plain", "policy.txt")
        if error is None
        else None,
        error=error,
    )

    response = build_client(service).post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == expected_status
    if expected_code is not None:
        assert response.json()["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("fixture_name", "mime_type", "filename"),
    [
        ("pdf", PDF_MIME, "policy.pdf"),
        ("docx", DOCX_MIME, "policy.docx"),
        ("txt", "text/plain", "policy.txt"),
    ],
)
def test_supported_formats_ingest(
    fixture_name: str,
    mime_type: str,
    filename: str,
) -> None:
    content = {
        "pdf": make_pdf,
        "docx": make_docx,
        "txt": lambda: b"TXT policy",
    }[fixture_name]()
    service = IngestionDocumentService(file_for(content, mime_type, filename))

    response = build_client(service).post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 200
    assert response.json()["source_hash"]
    assert response.json()["chunk_count"] >= 1


def test_docx_table_preservation_through_endpoint() -> None:
    service = IngestionDocumentService(
        file_for(make_docx(), DOCX_MIME, "policy.docx")
    )

    response = build_client(service).post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 200
    assert "| Role | Access |" in response.json()["markdown"]
    assert "| Employee | Standard |" in response.json()["markdown"]


def test_unsupported_uploaded_mime_returns_safe_error() -> None:
    service = IngestionDocumentService(
        file_for(b"not a supported document", "application/octet-stream", "file.bin")
    )

    response = build_client(service).post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_mime_type"
    assert "content" not in response.json()["error"]["message"].lower()


def test_unauthorized_user_is_rejected_before_storage_parser_markdown_or_chunking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = IngestionDocumentService(
        error=AuthorizationError("denied", code="document_access_denied")
    )
    calls = {"parser": 0, "markdown": 0, "chunker": 0}

    def parser(*args, **kwargs):
        calls["parser"] += 1
        raise AssertionError("parser must not run")

    def markdown(*args, **kwargs):
        calls["markdown"] += 1
        raise AssertionError("Markdown conversion must not run")

    class Chunker:
        def chunk(self, *args, **kwargs):
            calls["chunker"] += 1
            raise AssertionError("chunking must not run")

    monkeypatch.setattr(
        "app.services.document_ingestion_service.parse_document",
        parser,
    )
    monkeypatch.setattr(
        "app.services.document_ingestion_service.blocks_to_markdown",
        markdown,
    )
    client = build_client(service)
    response = client.post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "document_access_denied"
    assert service.download_calls == 0
    assert calls == {"parser": 0, "markdown": 0, "chunker": 0}
